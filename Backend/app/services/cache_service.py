"""
Cache service for RF-04
Implements cache-first with TTL and stale-while-revalidate.
Uses Redis when configured, falls back to in-memory automatically.
"""

from typing import Optional, Dict, Any, Callable
from datetime import datetime, timedelta
import json
import hashlib

try:
    import redis as _redis_lib
    _REDIS_AVAILABLE = True
except ImportError:
    _REDIS_AVAILABLE = False


class CacheService:
    """
    Servicio de caché con TTL y stale-while-revalidate.
    Si USE_REDIS=true y Redis está disponible, usa Redis; si no, usa memoria.
    """

    def __init__(self):
        self.default_ttl_seconds = 300        # 5 min
        self.default_stale_ttl_seconds = 600  # 10 min

        # In-memory fallback
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._prefix_index: Dict[str, set] = {}

        # Redis (optional)
        self._redis_client = None
        self._connected = False

        try:
            from app.core.config import settings
            if getattr(settings, 'USE_REDIS', False) and _REDIS_AVAILABLE:
                self._init_redis(settings)
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    # Redis init                                                           #
    # ------------------------------------------------------------------ #

    def _init_redis(self, settings) -> None:
        try:
            redis_url = getattr(settings, 'REDIS_URL', None)
            if redis_url:
                self._redis_client = _redis_lib.from_url(redis_url, decode_responses=False)
            else:
                self._redis_client = _redis_lib.Redis(
                    host=getattr(settings, 'REDIS_HOST', 'localhost'),
                    port=getattr(settings, 'REDIS_PORT', 6379),
                    password=getattr(settings, 'REDIS_PASSWORD', None),
                    db=getattr(settings, 'REDIS_DB', 0),
                    decode_responses=False,
                )
            self._redis_client.ping()
            self._connected = True
            print("✅ Redis cache connected successfully")
        except Exception as e:
            print(f"⚠️  Redis not available: {e}, falling back to in-memory cache")
            self._connected = False
            self._redis_client = None

    # ------------------------------------------------------------------ #
    # Key generation                                                       #
    # ------------------------------------------------------------------ #

    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        key_data = {"prefix": prefix, "args": args, "kwargs": sorted(kwargs.items())}
        key_str = json.dumps(key_data, sort_keys=True, default=str)
        key_hash = hashlib.md5(key_str.encode()).hexdigest()
        self._prefix_index.setdefault(prefix, set()).add(key_hash)
        return key_hash

    # ------------------------------------------------------------------ #
    # Redis helpers                                                        #
    # ------------------------------------------------------------------ #

    def _serialize(self, data: Any) -> bytes:
        return json.dumps(data, default=str).encode('utf-8')

    def _deserialize(self, data: bytes) -> Any:
        return json.loads(data.decode('utf-8'))

    # ------------------------------------------------------------------ #
    # Public API — all methods route to Redis or memory automatically     #
    # ------------------------------------------------------------------ #

    def get(self, key: str, allow_stale: bool = True) -> Optional[Dict[str, Any]]:
        return self._redis_get(key, allow_stale) if self._connected else self._mem_get(key, allow_stale)

    def set(
        self,
        key: str,
        data: Any,
        ttl_seconds: Optional[int] = None,
        stale_ttl_seconds: Optional[int] = None,
    ) -> None:
        if self._connected:
            self._redis_set(key, data, ttl_seconds, stale_ttl_seconds)
        else:
            self._mem_set(key, data, ttl_seconds, stale_ttl_seconds)

    def delete(self, key: str) -> bool:
        return self._redis_delete(key) if self._connected else self._mem_delete(key)

    def clear(self) -> int:
        return self._redis_clear() if self._connected else self._mem_clear()

    def invalidate_pattern(self, pattern: str) -> int:
        return self._redis_invalidate(pattern) if self._connected else self._mem_invalidate(pattern)

    async def get_or_set(
        self,
        key: str,
        fetch_func: Callable,
        ttl_seconds: Optional[int] = None,
        stale_ttl_seconds: Optional[int] = None,
        allow_stale: bool = True,
    ) -> Any:
        cached = self.get(key, allow_stale=allow_stale)

        if cached and cached.get("fresh"):
            return cached["data"]

        if cached and cached.get("stale") and allow_stale:
            try:
                fresh_data = await fetch_func()
                self.set(key, fresh_data, ttl_seconds, stale_ttl_seconds)
            except Exception:
                pass
            return cached["data"]

        fresh_data = await fetch_func()
        self.set(key, fresh_data, ttl_seconds, stale_ttl_seconds)
        return fresh_data

    def cleanup_expired(self) -> int:
        return self._redis_cleanup() if self._connected else self._mem_cleanup()

    async def get_status(self) -> Dict[str, Any]:
        return await self._redis_status() if self._connected else await self._mem_status()

    # ------------------------------------------------------------------ #
    # In-memory implementation                                            #
    # ------------------------------------------------------------------ #

    def _mem_get(self, key: str, allow_stale: bool) -> Optional[Dict[str, Any]]:
        entry = self._cache.get(key)
        if not entry:
            return None
        now = datetime.utcnow()
        if entry["expires_at"] > now:
            return {"data": entry["data"], "fresh": True, "cached_at": entry["cached_at"].isoformat()}
        if allow_stale and entry.get("stale_expires_at") and entry["stale_expires_at"] > now:
            return {"data": entry["data"], "fresh": False, "stale": True, "cached_at": entry["cached_at"].isoformat()}
        return None

    def _mem_set(self, key: str, data: Any, ttl_seconds=None, stale_ttl_seconds=None) -> None:
        now = datetime.utcnow()
        ttl = ttl_seconds or self.default_ttl_seconds
        stale = stale_ttl_seconds or self.default_stale_ttl_seconds
        self._cache[key] = {
            "data": data,
            "cached_at": now,
            "expires_at": now + timedelta(seconds=ttl),
            "stale_expires_at": now + timedelta(seconds=stale),
        }

    def _mem_delete(self, key: str) -> bool:
        if key in self._cache:
            del self._cache[key]
            for keys in self._prefix_index.values():
                keys.discard(key)
            return True
        return False

    def _mem_clear(self) -> int:
        count = len(self._cache)
        self._cache.clear()
        self._prefix_index.clear()
        return count

    def _mem_invalidate(self, pattern: str) -> int:
        keys_to_delete = list(self._prefix_index.pop(pattern, []))
        count = sum(1 for k in keys_to_delete if self._cache.pop(k, None) is not None)
        return count

    def _mem_cleanup(self) -> int:
        now = datetime.utcnow()
        expired = [
            k for k, e in self._cache.items()
            if e.get("stale_expires_at") and e["stale_expires_at"] < now
        ]
        for k in expired:
            del self._cache[k]
        return len(expired)

    async def _mem_status(self) -> Dict[str, Any]:
        now = datetime.utcnow()
        active = stale = expired = 0
        for e in self._cache.values():
            if e["expires_at"] > now:
                active += 1
            elif e.get("stale_expires_at") and e["stale_expires_at"] > now:
                stale += 1
            else:
                expired += 1
        return {
            "total_entries": len(self._cache),
            "active_entries": active,
            "stale_entries": stale,
            "expired_entries": expired,
            "last_cleaned": None,
        }

    # ------------------------------------------------------------------ #
    # Redis implementation                                                 #
    # ------------------------------------------------------------------ #

    def _redis_get(self, key: str, allow_stale: bool) -> Optional[Dict[str, Any]]:
        try:
            raw = self._redis_client.get(f"cache:{key}")
            if not raw:
                return None
            entry = self._deserialize(raw)
            now = datetime.utcnow()
            expires_at = datetime.fromisoformat(entry["expires_at"])
            if expires_at > now:
                return {"data": entry["data"], "fresh": True, "cached_at": entry["cached_at"]}
            if allow_stale and entry.get("stale_expires_at"):
                if datetime.fromisoformat(entry["stale_expires_at"]) > now:
                    return {"data": entry["data"], "fresh": False, "stale": True, "cached_at": entry["cached_at"]}
            return None
        except Exception as e:
            print(f"⚠️  Redis get error: {e}")
            return None

    def _redis_set(self, key: str, data: Any, ttl_seconds=None, stale_ttl_seconds=None) -> None:
        try:
            now = datetime.utcnow()
            ttl = ttl_seconds or self.default_ttl_seconds
            stale = stale_ttl_seconds or self.default_stale_ttl_seconds
            entry = {
                "data": data,
                "cached_at": now.isoformat(),
                "expires_at": (now + timedelta(seconds=ttl)).isoformat(),
                "stale_expires_at": (now + timedelta(seconds=stale)).isoformat(),
            }
            self._redis_client.setex(f"cache:{key}", stale, self._serialize(entry))
        except Exception as e:
            print(f"⚠️  Redis set error: {e}")

    def _redis_delete(self, key: str) -> bool:
        try:
            return self._redis_client.delete(f"cache:{key}") > 0
        except Exception as e:
            print(f"⚠️  Redis delete error: {e}")
            return False

    def _redis_clear(self) -> int:
        try:
            keys = self._redis_client.keys("cache:*")
            return self._redis_client.delete(*keys) if keys else 0
        except Exception as e:
            print(f"⚠️  Redis clear error: {e}")
            return 0

    def _redis_invalidate(self, pattern: str) -> int:
        try:
            keys = self._redis_client.keys(f"cache:*{pattern}*")
            return self._redis_client.delete(*keys) if keys else 0
        except Exception as e:
            print(f"⚠️  Redis invalidate error: {e}")
            return 0

    def _redis_cleanup(self) -> int:
        try:
            count = 0
            now = datetime.utcnow()
            for key in self._redis_client.keys("cache:*"):
                try:
                    raw = self._redis_client.get(key)
                    if raw:
                        entry = self._deserialize(raw)
                        stale_exp = datetime.fromisoformat(entry.get("stale_expires_at", entry["expires_at"]))
                        if stale_exp < now:
                            self._redis_client.delete(key)
                            count += 1
                except Exception:
                    continue
            return count
        except Exception as e:
            print(f"⚠️  Redis cleanup error: {e}")
            return 0

    async def _redis_status(self) -> Dict[str, Any]:
        try:
            keys = self._redis_client.keys("cache:*")
            active = stale = expired = 0
            now = datetime.utcnow()
            for key in keys:
                try:
                    raw = self._redis_client.get(key)
                    if raw:
                        entry = self._deserialize(raw)
                        exp = datetime.fromisoformat(entry["expires_at"])
                        stale_exp = datetime.fromisoformat(entry.get("stale_expires_at", entry["expires_at"]))
                        if exp > now:
                            active += 1
                        elif stale_exp > now:
                            stale += 1
                        else:
                            expired += 1
                except Exception:
                    expired += 1
            return {
                "total_entries": len(keys),
                "active_entries": active,
                "stale_entries": stale,
                "expired_entries": expired,
                "last_cleaned": None,
                "redis_connected": True,
            }
        except Exception as e:
            print(f"⚠️  Redis status error: {e}")
            return {
                "total_entries": 0,
                "active_entries": 0,
                "stale_entries": 0,
                "expired_entries": 0,
                "last_cleaned": None,
                "redis_connected": False,
            }


cache_service = CacheService()
