"""Telegram bot interface for EAZZU.

Provides a lightweight Telegram bot that exposes the EAZZU agent and tools
through Telegram chat. Uses the Telegram Bot API (HTTP long polling).

Setup:
  1. Create a bot via @BotFather → get the token
  2. Set TELEGRAM_BOT_TOKEN env var (or use `eazzu keys set telegram_bot <token>`)
  3. Run: ``eazzu telegram``

No third-party dependencies — uses stdlib urllib for the Telegram API.
"""
from __future__ import annotations

import json
import os
import time
import urllib.request
import urllib.parse
import urllib.error
from typing import Optional

_API = "https://api.telegram.org/bot{token}/{method}"


def _tg_request(token: str, method: str, data: Optional[dict] = None, timeout: float = 30) -> dict:
    url = _API.format(token=token, method=method)
    if data:
        post_data = urllib.parse.urlencode(data).encode("utf-8")
        req = urllib.request.Request(url, data=post_data, method="POST")
    else:
        req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return {"ok": False, "error": f"HTTP {exc.code}", "detail": exc.read().decode("utf-8", errors="replace")[:500]}
    except urllib.error.URLError as exc:
        return {"ok": False, "error": str(exc)}


def get_me(token: str) -> dict:
    """Get bot info."""
    return _tg_request(token, "getMe")


def send_message(token: str, chat_id: str, text: str, parse_mode: str = "Markdown") -> dict:
    """Send a message to a chat."""
    return _tg_request(token, "sendMessage", {"chat_id": chat_id, "text": text[:4096], "parse_mode": parse_mode})


def get_updates(token: str, offset: Optional[int] = None, timeout: int = 30) -> dict:
    """Get updates (messages) from Telegram via long polling."""
    params = {"timeout": timeout}
    if offset:
        params["offset"] = offset
    return _tg_request(token, "getUpdates", params, timeout=timeout + 10)


def set_webhook(token: str, url: str) -> dict:
    """Set a webhook URL for receiving updates."""
    return _tg_request(token, "setWebhook", {"url": url})


def delete_webhook(token: str) -> dict:
    """Delete the current webhook."""
    return _tg_request(token, "deleteWebhook")


def send_document(token: str, chat_id: str, file_path: str) -> dict:
    """Send a document/file to a chat."""
    import mimetypes
    boundary = f"----eazzu{int(time.time())}"
    filename = os.path.basename(file_path)
    mime = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
    with open(file_path, "rb") as f:
        file_data = f.read()
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="chat_id"\r\n\r\n{chat_id}\r\n'
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="document"; filename="{filename}"\r\n'
        f"Content-Type: {mime}\r\n\r\n"
    ).encode("utf-8") + file_data + f"\r\n--{boundary}--\r\n".encode("utf-8")
    url = _API.format(token=token, method="sendDocument")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return {"ok": False, "error": f"HTTP {exc.code}"}


def run_bot(token: str, provider: str = "openai", model: Optional[str] = None, allowed_users: Optional[list[str]] = None) -> None:
    """Run the Telegram bot with long polling. Blocks until interrupted.

    Parameters
    ----------
    token:
        Telegram bot token from BotFather.
    provider / model:
        LLM provider and model for the agent.
    allowed_users:
        Optional list of Telegram user IDs allowed to use the bot. If None,
        anyone who can message the bot can use it.
    """
    from eazzu.agent.core import Agent

    me = get_me(token)
    if not me.get("ok"):
        print(f"Failed to connect to Telegram: {me.get('description', me)}")
        return

    bot_name = me["result"]["username"]
    print(f"EAZZU Telegram bot @{bot_name} is running...")
    print("Press Ctrl-C to stop.\n")

    agent = Agent(provider=provider, model=model)
    offset = None
    user_contexts: dict[str, Agent] = {}

    while True:
        try:
            updates = get_updates(token, offset)
            if not updates.get("ok"):
                print(f"Telegram error: {updates}")
                time.sleep(5)
                continue

            for update in updates.get("result", []):
                offset = update["update_id"] + 1
                message = update.get("message") or update.get("edited_message")
                if not message:
                    continue

                chat_id = str(message["chat"]["id"])
                user_id = str(message.get("from", {}).get("id", ""))
                text = message.get("text", "").strip()

                if not text:
                    continue

                if allowed_users and user_id not in allowed_users:
                    send_message(token, chat_id, "You are not authorized to use this bot.")
                    continue

                if text == "/start":
                    send_message(token, chat_id, f"*EAZZU Bot* — your AI agent is ready!\n\nJust send me a message and I'll help you with code, trading, research, and more.\n\nCommands:\n/reset — clear conversation\n/tools — list available tools\n/help — show help")
                    continue
                if text == "/reset":
                    user_contexts.pop(chat_id, None)
                    send_message(token, chat_id, "Conversation cleared.")
                    continue
                if text == "/help":
                    send_message(token, chat_id, "Send any message to chat with the EAZZU AI agent. It can use tools like web search, code execution, trading analysis, and more.\n\n/reset — clear conversation\n/tools — list tools")
                    continue
                if text == "/tools":
                    tool_list = "\n".join(f"- `{t['name']}` — {t['description'][:60]}" for t in agent.tools[:20])
                    send_message(token, chat_id, f"*Tools available ({len(agent.tools)} total):*\n{tool_list}")
                    continue

                if chat_id not in user_contexts:
                    user_contexts[chat_id] = Agent(provider=provider, model=model)
                user_agent = user_contexts[chat_id]

                _tg_request(token, "sendChatAction", {"chat_id": chat_id, "action": "typing"})

                try:
                    turn = user_agent.ask(text)
                    reply = turn.reply or "(no response)"
                    if len(reply) > 4096:
                        for i in range(0, len(reply), 4096):
                            send_message(token, chat_id, reply[i : i + 4096])
                    else:
                        send_message(token, chat_id, reply)
                    for tc in turn.tool_calls:
                        send_message(token, chat_id, f"Tool: `{tc['name']}`")
                except Exception as exc:  # noqa: BLE001
                    send_message(token, chat_id, f"Error: {exc}")

        except KeyboardInterrupt:
            print("\nBot stopped.")
            break
        except Exception as exc:  # noqa: BLE001
            print(f"Error: {exc}")
            time.sleep(5)
