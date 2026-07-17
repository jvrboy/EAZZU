"""Usage / cost tracker (SQLite)."""
from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Optional


class UsageTracker:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = str(db_path or (Path.home() / ".eazzu" / "usage.db"))
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as db:
            db.execute(
                """CREATE TABLE IF NOT EXISTS usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts REAL NOT NULL,
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    prompt_tokens INTEGER,
                    completion_tokens INTEGER,
                    total_tokens INTEGER,
                    cost_usd REAL,
                    latency_ms REAL,
                    success INTEGER
                )"""
            )

    def record(self, response, success: bool = True) -> None:
        with sqlite3.connect(self.db_path) as db:
            db.execute(
                "INSERT INTO usage (ts, provider, model, prompt_tokens, completion_tokens, total_tokens, cost_usd, latency_ms, success) VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    time.time(),
                    getattr(response, "provider", "unknown"),
                    getattr(response, "model", "unknown"),
                    getattr(response, "prompt_tokens", 0),
                    getattr(response, "completion_tokens", 0),
                    getattr(response, "total_tokens", 0),
                    getattr(response, "cost_usd", 0.0),
                    getattr(response, "latency_ms", 0.0),
                    1 if success else 0,
                ),
            )

    def summary(self, provider: str | None = None) -> dict:
        q = "SELECT provider, COUNT(*), SUM(total_tokens), SUM(cost_usd) FROM usage"
        params = ()
        if provider:
            q += " WHERE provider = ?"
            params = (provider,)
        q += " GROUP BY provider"
        with sqlite3.connect(self.db_path) as db:
            rows = db.execute(q, params).fetchall()
        return {
            r[0]: {"calls": r[1], "tokens": r[2] or 0, "cost_usd": round(r[3] or 0, 6)}
            for r in rows
        }

    def recent(self, limit: int = 20) -> list[dict]:
        with sqlite3.connect(self.db_path) as db:
            rows = db.execute(
                "SELECT ts, provider, model, total_tokens, cost_usd, latency_ms, success FROM usage ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            {
                "ts": r[0], "provider": r[1], "model": r[2],
                "tokens": r[3], "cost_usd": r[4], "latency_ms": r[5], "success": bool(r[6]),
            }
            for r in rows
        ]

    def clear(self):
        with sqlite3.connect(self.db_path) as db:
            db.execute("DELETE FROM usage")
