from typing import Any

from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend


class CacheService:
    _instance: "CacheService" = None

    def __init__(self):
        pass

    @classmethod
    def get_instance(cls) -> "CacheService":
        if CacheService._instance is None:
            CacheService._instance = cls()
        return CacheService._instance

    def _get_backend(self) -> RedisBackend | None:
        try:
            return FastAPICache.get_backend()
        except (RuntimeError, ValueError):
            return None

    def _build_key(self, namespace: str, key: str) -> str:
        return f"{namespace}:{key}"

    async def get(self, namespace: str, key: str) -> Any | None:
        cache_backend = self._get_backend()
        if cache_backend is None:
            return None

        cache_key = self._build_key(namespace, key)
        return await cache_backend.get(cache_key)

    async def set(self, namespace: str, key: str, value: Any, *, expire: int | None = None) -> None:
        cache_backend = self._get_backend()
        if cache_backend is None:
            return

        cache_key = self._build_key(namespace, key)
        await cache_backend.set(cache_key, value, expire=expire)

    async def delete(self, namespace: str, key: str) -> None:
        cache_backend = self._get_backend()
        if cache_backend is None:
            return

        cache_key = self._build_key(namespace, key)
        print(f"Deleting cache key: {cache_key}")
        await cache_backend.clear(key=cache_key)


cache_service = CacheService.get_instance()
