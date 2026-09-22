from __future__ import annotations

import hashlib
import json
import threading
import time
from typing import Any


class ResearchCache:
    """
    Thread-safe in-memory cache for research results.

    Results expire automatically after the configured TTL.
    """

    def __init__(self, ttl_seconds: int = 3600) -> None:
        self.ttl_seconds = ttl_seconds
        self._cache: dict[str, tuple[float, Any]] = {}
        self._lock = threading.Lock()

    @staticmethod
    def make_key(task_description: str, session_id: str = "", user_id: str = "") -> str:
        """
        Create a stable cache key from a research task description, session ID, and user ID.
        """
        normalized = " ".join(task_description.lower().split())
        prefix_parts = []
        if user_id:
            prefix_parts.append(f"u:{user_id.strip()}")
        if session_id:
            prefix_parts.append(f"s:{session_id.strip()}")

        if prefix_parts:
            normalized = f"{':'.join(prefix_parts)}:{normalized}"

        return hashlib.sha256(
            normalized.encode("utf-8")
        ).hexdigest()

    def get(self, task_description: str, session_id: str = "", user_id: str = "") -> Any | None:
        """
        Return cached result if present and not expired.
        """
        key = self.make_key(task_description, session_id=session_id, user_id=user_id)

        with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                return None

            created_at, value = entry

            if time.time() - created_at >= self.ttl_seconds:
                del self._cache[key]
                return None

            return value

    def set(self, task_description: str, value: Any, session_id: str = "", user_id: str = "") -> None:
        """
        Store a research result in the cache.
        """
        key = self.make_key(task_description, session_id=session_id, user_id=user_id)

        with self._lock:
            self._cache[key] = (time.time(), value)

    def clear(self) -> None:
        """
        Clear all cached results.
        """
        with self._lock:
            self._cache.clear()

    def size(self) -> int:
        """
        Return the number of currently stored cache entries.
        """
        with self._lock:
            return len(self._cache)