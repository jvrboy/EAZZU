"""Telegram bot interface for EAZZU.

Features
--------
* Long-polling based (no webhooks needed — works from Windows CMD, any shell, iSH).
* Per-user agent sessions (history, working directory).
* Inline keyboards for:
    - `/menu`  — main menu: Chat / Desktop / Screenshot / Files / Shell / Status / Router
    - Files browser — navigable directory tree with buttons for Open / Info / Run
    - Desktop shortcut — list desktop + take screenshot
* **Human-language control** — you can say "take a screenshot of my desktop and
  list every file" or "run `ipconfig` in cmd" and the agent routes to the right tools.
* **Keep-alive pings** while the agent is thinking: edits a "typing…" message every
  few seconds so Telegram shows neat "still working" status instead of silence.
* Sends photos (screenshots) and documents (artifacts, zipped apps) inline.
* Router health shown via `/router`; keys list via `/keys`.
* `allowed_users` whitelist; every command/auth failure is logged.
* Works with the auto multi-provider router (provider="auto").

Pure-stdlib HTTP (urllib) — no third-party bot library required.
"""
from __future__ import annotations

import io
import json
import mimetypes
import os
import sys
import time
import urllib.request
import urllib.parse
import urllib.error
import threading
from pathlib import Path
from typing import Any, Callable, Optional

_API = "https://api.telegram.org/bot{token}/{method}"


def _tg_request(token: str, method: str, data: Optional[dict] = None, timeout: float = 30,
                files: Optional[dict] = None) -> dict:
    url = _API.format(token=token, method=method)
    if files:
        # multipart/form-data
        boundary = f"----eazzuboundary{int(time.time()*1000)}"
        body = bytearray()
        if data:
            for k, v in data.items():
                if v is None: continue
                body += f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode("utf-8")
        for field, (fname, fpath, mime) in files.items():
            body += f"--{boundary}\r\nContent-Disposition: form-data; name=\"{field}\"; filename=\"{fname}\"\r\nContent-Type: {mime}\r\n\r\n".encode("utf-8")
            with open(fpath, "rb") as fh:
                body += fh.read()
            body += b"\r\n"
        body += f"--{boundary}--\r\n".encode("utf-8")
        req = urllib.request.Request(
            url, data=bytes(body),
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}",
                     "Content-Length": str(len(body))},
            method="POST",
        )
    else:
        if data is None:
            req = urllib.request.Request(url)
        else:
            enc = urllib.parse.urlencode({k: v for k, v in data.items() if v is not None}).encode()
            req = urllib.request.Request(url, data=enc, method="POST",
                                         headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        return {"ok": False, "error": f"HTTP {exc.code}", "detail": detail}
    except urllib.error.URLError as exc:
        return {"ok": False, "error": str(exc)}


def get_me(token: str) -> dict:
    return _tg_request(token, "getMe")


def send_message(token: str, chat_id: str, text: str, parse_mode: str = "HTML",
                 reply_markup: Optional[dict] = None) -> dict:
    return _tg_request(token, "sendMessage", {
        "chat_id": chat_id, "text": text[:4096], "parse_mode": parse_mode,
        "reply_markup": json.dumps(reply_markup) if reply_markup else None,
    })


def edit_message(token: str, chat_id: str, message_id: int, text: str,
                 parse_mode: str = "HTML", reply_markup: Optional[dict] = None) -> dict:
    return _tg_request(token, "editMessageText", {
        "chat_id": chat_id, "message_id": message_id, "text": text[:4096],
        "parse_mode": parse_mode,
        "reply_markup": json.dumps(reply_markup) if reply_markup else None,
    })


def send_chat_action(token: str, chat_id: str, action: str = "typing") -> dict:
    return _tg_request(token, "sendChatAction", {"chat_id": chat_id, "action": action})


def send_photo(token: str, chat_id: str, photo_path: str, caption: str = "") -> dict:
    mime = mimetypes.guess_type(photo_path)[0] or "image/png"
    return _tg_request(token, "sendPhoto",
                       data={"chat_id": chat_id, "caption": caption[:1024]},
                       files={"photo": (os.path.basename(photo_path), photo_path, mime)})


def send_document(token: str, chat_id: str, doc_path: str, caption: str = "") -> dict:
    mime = mimetypes.guess_type(doc_path)[0] or "application/octet-stream"
    return _tg_request(token, "sendDocument",
                       data={"chat_id": chat_id, "caption": caption[:1024]},
                       files={"document": (os.path.basename(doc_path), doc_path, mime)})


def answer_callback(token: str, qid: str, text: Optional[str] = None, show_alert: bool = False) -> dict:
    return _tg_request(token, "answerCallbackQuery",
                       {"callback_query_id": qid, "text": text, "show_alert": show_alert})


# ----------------------------------------------- Keyboards ---------------- #
def _menu_kb() -> dict:
    return {"inline_keyboard": [[
        {"text": "💬 Chat", "callback_data": "menu:chat"},
        {"text": "🖥️ Desktop", "callback_data": "menu:desktop"},
        {"text": "📸 Screenshot", "callback_data": "menu:screenshot"},
    ], [
        {"text": "📁 Files", "callback_data": "menu:files"},
        {"text": "💻 Shell", "callback_data": "menu:shell"},
        {"text": "📊 Status", "callback_data": "menu:status"},
    ], [
        {"text": "🔀 Router", "callback_data": "menu:router"},
        {"text": "🛠️ Tools", "callback_data": "menu:tools"},
        {"text": "ℹ️ Help", "callback_data": "menu:help"},
    ]]}


def _files_kb(path: str, entries: list[dict]) -> dict:
    rows = []
    parent = str(Path(path).parent) if Path(path) != Path(path).anchor else None
    if parent is not None:
        rows.append([{"text": "⬆️ ..", "callback_data": f"files:cd:{parent}"}])
    for e in entries[:48]:  # Telegram 64-byte cap per button; cap entries
        name = e["name"]
        icon = "📁" if e["type"] == "dir" else "📄"
        rows.append([{"text": f"{icon} {name[:38]}", "callback_data": f"files:open:{os.path.join(path,name)}"}])
    rows.append([{"text": "🔄 Refresh", "callback_data": f"files:cd:{path}"}])
    rows.append([{"text": "« Back to menu", "callback_data": "menu:open"}])
    return {"inline_keyboard": rows}


def _file_actions_kb(path: str) -> dict:
    return {"inline_keyboard": [[
        {"text": "▶️ Open/Run", "callback_data": f"file:run:{path}"},
        {"text": "ℹ️ Info", "callback_data": f"file:info:{path}"},
    ], [
        {"text": "📂 Containing folder", "callback_data": f"files:cd:{Path(path).parent}"},
        {"text": "« Menu", "callback_data": "menu:open"},
    ]]}


# ---------------------------------------------------- desktop helpers ---- #
def _desktop_listing() -> str:
    from eazzu.tools.computer_tools import list_desktop, active_window
    d = list_desktop()
    if not d.get("ok"):
        return f"Could not list desktop: {d.get('error')}"
    aw = active_window()
    lines = [f"<b>🖥️ Desktop</b> ({d['count']} items)"]
    if aw.get("ok"):
        lines.append(f"<i>Active window:</i> {aw.get('title','')}")
    lines.append("")
    for e in d["entries"][:60]:
        icon = "📁" if e["type"] == "dir" else "📄"
        lines.append(f"{icon} {_escape(e['name'])}")
    return "\n".join(lines)


def _human(n: int) -> str:
    for u in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f}{u}"
        n /= 1024
    return f"{n:.0f}TB"


def _escape(s: str) -> str:
    import html
    return html.escape(str(s))


def _thinking_thread(token: str, chat_id: str, stop_event: threading.Event, start_msg_id_holder: dict):
    """Edit an in-flight message every few seconds to show progress."""
    msg = send_message(token, chat_id, "⏳ thinking…")
    if not msg.get("ok"):
        return
    mid = msg["result"]["message_id"]
    start_msg_id_holder["id"] = mid
    dots = 0
    while not stop_event.is_set():
        dots = (dots + 1) % 4
        try:
            edit_message(token, chat_id, mid, "⏳ working" + "." * dots)
        except Exception:
            pass
        # Pings in 2.5s intervals
        stop_event.wait(2.5)
    try:
        edit_message(token, chat_id, mid, "✅")
    except Exception:
        pass


# ----------------------------------------------------- bot main loop ----- #
def run_bot(
    token: str,
    provider: str = "auto",
    model: Optional[str] = None,
    allowed_users: Optional[list[str]] = None,
    router_strategy: str = "random",
) -> None:
    from eazzu.agent.core import Agent
    from eazzu.tools.computer_tools import (
        desktop_screenshot, list_directory, open_file, run_shell_cmd, file_info,
        list_desktop, clipboard_read, clipboard_write, list_processes,
        active_window, _desktop_path,
    )
    screenshot = desktop_screenshot  # alias used below in callbacks
    from eazzu.tools.files import read_text_tool  # may be used later
    from eazzu.providers.router import ProviderRouter

    me = get_me(token)
    if not me.get("ok"):
        print(f"Failed to connect to Telegram: {me.get('description', me)}")
        return
    bot_name = me["result"]["username"]
    print(f"EAZZU Telegram bot @{bot_name} is running (provider={provider})...")
    print("Press Ctrl-C to stop.\n")

    user_sessions: dict[str, dict] = {}
    offset: Optional[int] = None

    def get_session(uid: str) -> dict:
        if uid not in user_sessions:
            agent = Agent(provider=provider, model=model, router_strategy=router_strategy)
            user_sessions[uid] = {"agent": agent, "cwd": str(Path.home()), "last": time.time()}
        return user_sessions[uid]

    def reply_text(chat_id: str, text: str, markup=None) -> None:
        # Split long replies
        for i in range(0, len(text), 3500):
            chunk = text[i:i + 3500]
            send_message(token, chat_id, chunk, reply_markup=markup if i == 0 else None)

    def run_agent(chat_id: str, uid: str, text: str) -> None:
        sess = get_session(uid)
        agent: Agent = sess["agent"]
        stop = threading.Event()
        holder: dict = {}
        t = threading.Thread(target=_thinking_thread, args=(token, chat_id, stop, holder), daemon=True)
        t.start()
        try:
            turn = agent.ask(text)
            reply = turn.reply or "(no response)"
            route_tag = ""
            if getattr(agent, "last_route", None):
                lr = agent.last_route
                route_tag = f"\n<i>via {lr.get('endpoint','')} · {lr.get('attempts',1)} attempt(s)</i>"
            stop.set()
            t.join(timeout=3)
            reply_text(chat_id, f"{_escape(reply)}{route_tag}")
            if turn.tool_calls:
                # If the agent produced screenshots, send them as photos.
                for tc in turn.tool_calls:
                    res = tc.get("result") or {}
                    if isinstance(res, dict) and res.get("ok"):
                        p = res.get("path") or res.get("screenshot", {}).get("path") if isinstance(res.get("screenshot"), dict) else None
                        if p and Path(p).exists() and str(p).lower().endswith((".png", ".jpg", ".jpeg")):
                            send_photo(token, chat_id, p)
                        pkg = res.get("package") if isinstance(res.get("package"), dict) else None
                        if pkg and pkg.get("ok") and Path(pkg["path"]).exists():
                            send_document(token, chat_id, pkg["path"], caption="Packaged app")
        except Exception as e:
            stop.set()
            t.join(timeout=3)
            reply_text(chat_id, f"❌ <b>Error:</b> {_escape(str(e))}")

    def handle_text(chat_id: str, uid: str, text: str) -> None:
        t = text.strip()
        low = t.lower()
        # Slash commands
        if t.startswith("/start"):
            send_message(token, chat_id,
                         f"<b>EAZZU Bot</b> @{bot_name} 🚀\n\n"
                         "Send me anything in human language and I'll act on your computer. "
                         "Use <code>/menu</code> for the control panel, or just ask.",
                         reply_markup=_menu_kb())
            return
        if t.startswith("/menu"):
            send_message(token, chat_id, "🎛️ <b>Main menu</b>", reply_markup=_menu_kb())
            return
        if t.startswith("/reset"):
            if uid in user_sessions:
                user_sessions.pop(uid, None)
            reply_text(chat_id, "✅ Conversation reset.")
            return
        if t.startswith("/screenshot") or low in {"screenshot", "screen", "pic", "photo"}:
            shot = desktop_screenshot()
            if shot.get("ok") and Path(shot["path"]).exists():
                send_photo(token, chat_id, shot["path"], caption=f"screenshot ({shot['method']})")
            else:
                reply_text(chat_id, f"❌ {shot.get('error','failed')}")
            return
        if t.startswith("/desktop") or low in {"desktop", "desktop files", "list desktop"}:
            reply_text(chat_id, _desktop_listing())
            return
        if t.startswith("/files") or low == "files":
            d = list_directory(str(_desktop_path()))
            if d.get("ok"):
                send_message(token, chat_id,
                             f"📁 <b>{_escape(d['path'])}</b>",
                             reply_markup=_files_kb(d["path"], d["entries"]))
            else:
                reply_text(chat_id, f"❌ {d.get('error')}")
            return
        if t.startswith("/router"):
            try:
                from eazzu.providers.router import ProviderRouter
                r = ProviderRouter()
                st = r.status()
                rows = [f"🔀 Router: {st['strategy']} · healthy {st['healthy']}/{st['total_endpoints']}"]
                for e in st["endpoints"][:30]:
                    mk = "✅" if e["ready"] else f"⏳{e['cooldown_remaining_s']}s"
                    rows.append(f"{mk} {_escape(e['label'])} — ok {e['successes']}/fail {e['failures']}")
                reply_text(chat_id, "\n".join(rows))
            except Exception as e:
                reply_text(chat_id, f"❌ {e}")
            return
        if t.startswith("/status") or low == "status":
            import eazzu
            reply_text(chat_id,
                       f"<b>EAZZU v{eazzu.__version__}</b>\n"
                       f"Platform: {sys.platform}\n"
                       f"Python: {sys.version.split()[0]}\n"
                       f"Provider: {provider}\n"
                       f"PID: {os.getpid()}")
            return
        if t.startswith("/shell") or t.startswith("/cmd") or t.startswith("/powershell") or t.startswith("/ps"):
            cmd = t.split(None, 1)[1] if " " in t else ""
            if not cmd:
                reply_text(chat_id, "Usage: <code>/shell &lt;command&gt;</code>\nOr just say: 'run ipconfig in cmd'")
                return
            shell = "cmd" if t.startswith("/cmd") else ("powershell" if t.startswith(("/powershell","/ps")) else "auto")
            r = run_shell_cmd(cmd, shell=shell, timeout=60)
            out = (r.get("stdout","") + r.get("stderr","")).strip() or "(no output)"
            reply_text(chat_id, f"<code>{_escape(out[:3500])}</code>\nexit={r.get('exit_code')}")
            return
        if t.startswith("/help"):
            send_message(token, chat_id,
                         "<b>EAZZU Bot commands</b>\n"
                         "/menu — control panel\n"
                         "/screenshot — take a screenshot\n"
                         "/desktop — list desktop files\n"
                         "/files — file browser\n"
                         "/shell <cmd> — run shell command (or /cmd /powershell)\n"
                         "/router — routing health\n"
                         "/status — bot status\n"
                         "/reset — clear conversation\n"
                         "/help — this message\n\n"
                         "Human language works too — try \"list my desktop and screenshot it\" or \"run ipconfig\".",
                         reply_markup=_menu_kb())
            return

        # Natural-language → dispatch to agent (full tool use)
        threading.Thread(target=run_agent, args=(chat_id, uid, t), daemon=True).start()

    def handle_callback(qid: str, chat_id: str, uid: str, data: str) -> None:
        answer_callback(token, qid)  # dismiss loading spinner
        try:
            if data == "menu:open" or data == "menu:chat":
                send_message(token, chat_id,
                             "💬 Send me any message (human language) and I'll act on it — "
                             "run commands, browse files, take screenshots, build apps.",
                             reply_markup=_menu_kb())
                return
            if data == "menu:desktop":
                reply_text(chat_id, _desktop_listing())
                return
            if data == "menu:screenshot":
                shot = screenshot()
                if shot.get("ok") and Path(shot["path"]).exists():
                    send_photo(token, chat_id, shot["path"], caption=f"🖥️ screenshot ({shot['method']})")
                else:
                    reply_text(chat_id, f"❌ {shot.get('error','failed')}")
                return
            if data == "menu:files":
                d = list_directory(str(_desktop_path()))
                send_message(token, chat_id, f"📁 <b>{_escape(d['path'])}</b>",
                             reply_markup=_files_kb(d["path"], d["entries"]) if d.get("ok") else None)
                if not d.get("ok"):
                    reply_text(chat_id, f"❌ {d.get('error')}")
                return
            if data == "menu:shell":
                send_message(token, chat_id,
                             "💻 Send <code>/shell &lt;your command&gt;</code>, <code>/cmd ...</code>, "
                             "or <code>/powershell ...</code> — or just say \"run ipconfig\" in chat.")
                return
            if data == "menu:status":
                handle_text(chat_id, uid, "/status")
                return
            if data == "menu:router":
                handle_text(chat_id, uid, "/router")
                return
            if data == "menu:tools":
                reply_text(chat_id,
                           "🛠️ Tools you can invoke by name (just ask):\n"
                           "• screenshot, list_desktop, list_directory, file_info, open_file\n"
                           "• run_shell, run_cmd, run_powershell, list_processes, active_window\n"
                           "• clipboard_read, clipboard_write, dialog_alert, keyboard_type, mouse_click\n"
                           "• create_app, run_app, build_app, package_app, screenshot_app\n"
                           "• self_status, self_clone, self_test, self_apply")
                return
            if data == "menu:help":
                handle_text(chat_id, uid, "/help")
                return
            if data.startswith("files:cd:"):
                path = data.split(":", 2)[2]
                d = list_directory(path)
                if d.get("ok"):
                    send_message(token, chat_id, f"📁 <b>{_escape(d['path'])}</b>",
                                 reply_markup=_files_kb(d["path"], d["entries"]))
                else:
                    reply_text(chat_id, f"❌ {d.get('error')}")
                return
            if data.startswith("files:open:") or data.startswith("file:run:") or data.startswith("file:info:"):
                path = data.split(":", 2)[2]
                if data.startswith("file:info:"):
                    info = file_info(path)
                    if info.get("ok"):
                        reply_text(chat_id,
                                   f"<b>{_escape(info['name'])}</b>\n"
                                   f"path: {_escape(info['path'])}\n"
                                   f"type: {info['type']}\n"
                                   f"size: {_human(info['size'])}\n"
                                   f"modified: {info['modified']}\n"
                                   f"perms: r={info['readable']} w={info['writable']} x={info['executable']}",
                                   reply_markup=_file_actions_kb(path))
                    else:
                        reply_text(chat_id, f"❌ {info.get('error')}")
                    return
                # open or run
                if Path(path).is_dir():
                    d = list_directory(path)
                    if d.get("ok"):
                        send_message(token, chat_id, f"📁 <b>{_escape(d['path'])}</b>",
                                     reply_markup=_files_kb(d["path"], d["entries"]))
                    return
                if Path(path).suffix.lower() in (".exe", ".bat", ".cmd", ".ps1", ".py", ".sh", ".app"):
                    r = run_shell_cmd(f'"{path}"', shell="auto", timeout=10)
                    reply_text(chat_id, f"▶️ launched {_escape(Path(path).name)}\n<code>{_escape((r.get('stdout','')+r.get('stderr',''))[:1500])}</code>",
                               reply_markup=_file_actions_kb(path))
                else:
                    r = open_file(path)
                    reply_text(chat_id, f"▶️ opened {_escape(Path(path).name)}" if r.get("ok") else f"❌ {r.get('error')}",
                               reply_markup=_file_actions_kb(path))
                return
        except Exception as e:
            reply_text(chat_id, f"❌ callback error: {_escape(str(e))}")

    while True:
        try:
            updates = _tg_request(token, "getUpdates",
                                  data={"offset": offset, "timeout": 30}, timeout=35)
        except Exception as e:
            print(f"[warn] getUpdates error: {e}; sleeping 5s")
            time.sleep(5)
            continue
        if not updates.get("ok"):
            print(f"[warn] telegram: {updates}")
            time.sleep(3)
            continue
        for u in updates.get("result", []):
            offset = u["update_id"] + 1
            try:
                msg = u.get("message") or u.get("edited_message") or {}
                cb = u.get("callback_query")
                if cb:
                    msg = cb.get("message") or {}
                    chat_id = str(msg.get("chat", {}).get("id", ""))
                    uid = str(cb.get("from", {}).get("id", ""))
                    if allowed_users and uid not in allowed_users:
                        answer_callback(token, cb["id"], "Not authorized", show_alert=True)
                        continue
                    handle_callback(cb["id"], chat_id, uid, cb.get("data", ""))
                    continue
                if not msg:
                    continue
                chat_id = str(msg.get("chat", {}).get("id", ""))
                uid = str(msg.get("from", {}).get("id", ""))
                text = msg.get("text", "") or ""
                if allowed_users and uid not in allowed_users:
                    send_message(token, chat_id, "You are not authorized to use this bot.")
                    continue
                if not text:
                    continue
                handle_text(chat_id, uid, text)
            except Exception as e:
                print(f"[error] update: {e}")
