"""Failover / retry logic."""
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class FailoverPolicy:
    """Try providers in order, with retries per provider."""
    providers: list[str] = field(default_factory=list)  # e.g. ["openai","anthropic","groq"]
    max_retries: int = 2
    retry_backoff: float = 1.5  # seconds; exponential

    def iterate(self):
        """Yield (provider, attempt_number). Caller catches exceptions and moves on."""
        for provider in self.providers:
            for attempt in range(self.max_retries + 1):
                yield provider, attempt
                # caller breaks out on success

    def sleep(self, attempt: int):
        time.sleep(self.retry_backoff ** attempt)
