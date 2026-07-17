"""Simple SQLite-backed response cache."""
from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from pathlib import Path
from typing import Optional


class ResponseCache:
    def __init__(self, db_path: Optional[str] = None, ttl_seconds: int = 3600):
        self.db_path = str(db_path or (Path.home() / ".eazzu" / "cache.db"))
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.ttl_seconds = ttl_seconds
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as db:
            db.execute(
                """CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    response TEXT NOT NULL,
                    created_at REAL NOT NULL
                )"""
            )

    @staticmethod
    def _make_key(provider: str, model: str, messages, extra: dict) -> str:
        payload = json.dumps(
            {"p": provider, "m": model, "msgs": messages, "x": extra},
            sort_keys=True, default=str,
        )
        return hashlib.sha256(payload.encode()).hexdigest()

    def get(self, provider: str, model: str, messages, extra: dict | None = None):
        key = self._make_key(provider, model, messages, extra or {})
        with sqlite3.connect(self.db_path) as db:
            row = db.execute(
                "SELECT response, created_at FROM cache WHERE key = ?", (key,)
            ).fetchone()
        if not row:
            return None
        response, created_at = row
        if self.ttl_seconds and time.time() - created_at > self.ttl_seconds:
            return None
        return json.loads(response)

    def set(self, provider: str, model: str, messages, response_dict: dict, extra: dict | None = None):
        key = self._make_key(provider, model, messages, extra or {})
        with sqlite3.connect(self.db_path) as db:
            db.execute(
                "INSERT OR REPLACE INTO cache VALUES (?, ?, ?)",
                (key, json.dumps(response_dict), time.time()),
            )

    def clear(self):
        with sqlite3.connect(self.db_path) as db:
            db.execute("DELETE FROM cache")
