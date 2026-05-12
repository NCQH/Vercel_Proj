import threading
import time
from collections import defaultdict
from typing import Any, Callable, Optional


class TTLCache:
    """Very small TTL cache for backend data.
    Stores values in a dict with expiration timestamps.
    Thread-safe for concurrent backend requests.
    """

    def __init__(self, default_ttl: int = 30):
        self.default_ttl = default_ttl
        self._store: dict[str, tuple[float, Any]] = {}
        self._lock = threading.RLock()
        self._key_locks: dict[str, threading.Lock] = defaultdict(threading.Lock)
        self._hits = 0
        self._misses = 0

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        expire = time.time() + (ttl if ttl is not None else self.default_ttl)
        with self._lock:
            self._store[key] = (expire, value)

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            item = self._store.get(key)
            if not item:
                self._misses += 1
                return None
            expire, value = item
            if expire < time.time():
                self._store.pop(key, None)
                self._misses += 1
                return None
            self._hits += 1
            return value

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
            self._hits = 0
            self._misses = 0

    def stats(self) -> dict[str, int]:
        with self._lock:
            return {
                "size": len(self._store),
                "hits": self._hits,
                "misses": self._misses,
            }

    def get_or_set(self, key: str, loader: Callable[[], Any], ttl: Optional[int] = None) -> Any:
        """Return cached value or compute with loader and cache it."""
        val = self.get(key)
        if val is not None:
            return val
        val = loader()
        self.set(key, val, ttl)
        return val

    def get_or_set_threadsafe(self, key: str, loader: Callable[[], Any], ttl: Optional[int] = None) -> Any:
        """Return cached value with anti-stampede per-key lock around loader."""
        val = self.get(key)
        if val is not None:
            return val

        lock = self._key_locks[key]
        with lock:
            val = self.get(key)
            if val is not None:
                return val
            val = loader()
            self.set(key, val, ttl)
            return val
