import time
from typing import Any, Callable

from django.core.cache import cache

DEFAULT_TTL = 5 * 60 * 60
LOCK_TTL = 10
MAX_WAIT = 2


class EntityCache:
    @staticmethod
    def _cache_key(entity_id: str) -> str:
        return f"student:{entity_id}"

    @staticmethod
    def _lock_key(entity_id: str) -> str:
        return f"lock:student:{entity_id}"

    @staticmethod
    def _normalize(value: Any) -> Any:
        if value is None:
            return None
        if hasattr(value, "__iter__") and not isinstance(value, (dict, str)):
            return next(iter(value), None)
        return value

    @classmethod
    def get_or_set(
            cls,
            *,
            entity_id: str,
            fetch_func: Callable[..., Any],
            fetch_kwargs: dict | None = None,
            ttl: int = DEFAULT_TTL,
    ) -> Any:
        fetch_kwargs = fetch_kwargs or {}
        cache_key = cls._cache_key(entity_id)
        lock_key = cls._lock_key(entity_id)

        value = cache.get(cache_key)
        if value is not None:
            return value
        got_lock = cache.add(lock_key, 1, LOCK_TTL)
        if not got_lock:
            delay = 0.05
            waited = 0
            while waited < MAX_WAIT:
                time.sleep(delay)
                waited += delay
                value = cache.get(cache_key)
                if value is not None:
                    return value
                delay = min(delay * 2, 0.5)
            return None
        try:
            raw = fetch_func(**fetch_kwargs)
            value = cls._normalize(raw)

            if value is not None:
                cache.set(cache_key, value, ttl)

            return value
        finally:
            cache.delete(lock_key)
