"""Alert dispatcher — sends formatted messages to configured destinations.

Converted from infinite-loop-sound's alert-dispatcher.ts. Supports console,
webhook, and in-app channels. Telegram is supported but requires botToken
and chatId. Uses urllib from stdlib — no external dependencies.
"""
from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional
from urllib.request import Request, urlopen
from urllib.error import URLError


def dispatch_alert(
    targets: List[Dict[str, Any]],
    title: str,
    body: str,
    level: str = "info",
    meta: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Dispatch an alert to every target. Each target is independent."""
    payload = {"title": title, "body": body, "level": level, "meta": meta or {}}
    results: List[Dict[str, Any]] = []

    for target in targets:
        channel = target.get("channel", "console")
        try:
            if channel == "console":
                print(f"[ALERT {level}] {title} — {body}")
                results.append({"channel": "console", "ok": True, "ts": time.time() * 1000})

            elif channel == "webhook":
                url = target.get("url")
                if not url:
                    results.append({"channel": "webhook", "ok": False, "error": "missing url", "ts": time.time() * 1000})
                    continue
                headers = {"Content-Type": "application/json"}
                if target.get("secret"):
                    headers["Authorization"] = f"Bearer {target['secret']}"
                req = Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
                try:
                    with urlopen(req, timeout=10) as resp:
                        results.append({"channel": "webhook", "ok": resp.status < 400, "status": resp.status, "ts": time.time() * 1000})
                except URLError as e:
                    results.append({"channel": "webhook", "ok": False, "error": str(e), "ts": time.time() * 1000})

            elif channel == "telegram":
                bot_token = target.get("botToken")
                chat_id = target.get("chatId")
                if not bot_token or not chat_id:
                    results.append({"channel": "telegram", "ok": False, "error": "missing botToken or chatId", "ts": time.time() * 1000})
                    continue
                text = f"*{title}*\n{body}"
                url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                data = json.dumps({"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}).encode("utf-8")
                req = Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
                try:
                    with urlopen(req, timeout=10) as resp:
                        results.append({"channel": "telegram", "ok": resp.status < 400, "status": resp.status, "ts": time.time() * 1000})
                except URLError as e:
                    results.append({"channel": "telegram", "ok": False, "error": str(e), "ts": time.time() * 1000})

            else:
                results.append({"channel": channel, "ok": False, "error": f"unknown channel: {channel}", "ts": time.time() * 1000})

        except Exception as exc:
            results.append({"channel": channel, "ok": False, "error": str(exc), "ts": time.time() * 1000})

    return results


TOOLS = [
    {
        "name": "dispatch_alert",
        "description": "Send an alert to configured destinations (console, webhook, telegram). Each target is independent.",
        "params": {
            "targets": "array[object]",
            "title": "string",
            "body": "string",
            "level": "string(optional: info|warning|critical)",
            "meta": "object(optional)",
        },
        "run": lambda targets, title, body, level="info", meta=None: {"results": dispatch_alert(targets, title, body, level, meta)},
    },
]
