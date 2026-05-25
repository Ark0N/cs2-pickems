"""Tiny on-disk JSON cache with TTL.

Used to be polite to data sources (especially HLTV, which is Cloudflare-protected
and will ban aggressive scrapers) and to keep the free odds-API request budget low.
"""

from __future__ import annotations

import json
import re
import time
from typing import Any

from app.config import settings


def _safe(key: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", key)[:120]


class JsonCache:
    def __init__(self, namespace: str, ttl_seconds: int = 3600):
        self.dir = settings.cache_dir / namespace
        self.ttl = ttl_seconds

    def _path(self, key: str):
        return self.dir / f"{_safe(key)}.json"

    def get(self, key: str) -> Any | None:
        path = self._path(key)
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            return None
        if time.time() - payload.get("_ts", 0) > self.ttl:
            return None
        return payload.get("data")

    def set(self, key: str, value: Any) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        self._path(key).write_text(json.dumps({"_ts": time.time(), "data": value}))
