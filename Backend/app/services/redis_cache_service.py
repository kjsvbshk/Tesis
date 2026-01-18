"""
Redis Cache Service for RF-04
Implements cache-first with TTL and stale-while-revalidate using Redis
Falls back to in-memory cache if Redis is not available
"""

from typing import Optional, Dict, Any, Callable
from datetime import datetime, timedelta
import json
import hashlib

# Try to import Redis
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from app.core.config import settings

class RedisCacheService:
    """
    Servicio de caché con Redis
    Implementa la misma interfaz que CacheService para compatibilidad
    """
    
    def __init__(self):
        self.default_ttl_seconds = 300  # 5 minutos por defecto
        self.default_stale_ttl_seconds = 600  # 10 minutos para stale
        self._redis_client: Optional[redis.Redis] = None
        self._connected = False
        
        if REDIS_AVAILABLE:
            self._init_redis()
    
    def _init_redis(self):
        """Initialize Redis connection"""
        try:
            redis_url = getattr(settings, 'REDIS_URL', None)
            redis_host = getattr(settings, 'REDIS_HOST', 'localhost')
            redis_port = getattr(settings, 'REDIS_PORT', 6379)
            redis_password = getattr(settings, 'REDIS_PASSWORD', None)
            redis_db = getattr(settings, 'REDIS_DB', 0)
            
            if redis_url:
                self._redis_client = redis.from_url(redis_url, decode_responses=False)
            else:
                self._redis_client = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    password=redis_password,
                    db=redis_db,
                    decode_responses=False
                )
            
            # Test connection
            self._redis_client.ping()
            self._connected = True
            print("✅ Redis cache connected successfully")
        except Exception as e:
            print(f"⚠️  Redis not available: {e}, falling back to in-memory cache")
            self._connected = False
            self._redis_client = None
    
    def _serialize(self, data: Any) -> bytes:
        """Serialize data to JSON bytes"""
        return json.dumps(data, default=str).encode('utf-8')
    
    def _deserialize(self, data: bytes) -> Any:
        """Deserialize data from JSON bytes"""
        return json.loads(data.decode('utf-8'))
    
    def get(
        self,
        key: str,
        allow_stale: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Obtener valor del caché
        Si allow_stale=True, retorna valores stale mientras se revalida
        """
        if not self._connected or not self._redis_client:
            return None
        
        try:
            # Get main cache entry
            cache_data = self._redis_client.get(f"cache:{key}")
            if not cache_data:
                return None
            
            entry = self._deserialize(cache_data)
            now = datetime.utcnow()
            expires_at = datetime.fromisoformat(entry["expires_at"])
            
            # Check if fresh
            if expires_at > now:
                return {
                    "data": entry["data"],
                    "fresh": True,
                    "cached_at": entry["cached_at"]
                }
            
            # Check if stale
            if allow_stale and entry.get("stale_expires_at"):
                stale_expires_at = datetime.fromisoformat(entry["stale_expires_at"])
                if stale_expires_at > now:
                    return {
                        "data": entry["data"],
                        "fresh": False,
                        "stale": True,
                        "cached_at": entry["cached_at"]
                    }
            
            # Expired
            return None
        except Exception as e:
            print(f"⚠️  Error reading from Redis: {e}")
            return None
    
    def set(
        self,
        key: str,
        data: Any,
        ttl_seconds: Optional[int] = None,
        stale_ttl_seconds: Optional[int] = None
    ) -> None:
        """
        Almacenar valor en caché con TTL
        """
        if not self._connected or not self._redis_client:
            return
        
        try:
            now = datetime.utcnow()
            ttl = ttl_seconds or self.default_ttl_seconds
            stale_ttl = stale_ttl_seconds or self.default_stale_ttl_seconds
            
            entry = {
                "data": data,
                "cached_at": now.isoformat(),
                "expires_at": (now + timedelta(seconds=ttl)).isoformat(),
                "stale_expires_at": (now + timedelta(seconds=stale_ttl)).isoformat()
            }
            
            # Store with TTL (use stale_ttl for Redis expiration)
            self._redis_client.setex(
                f"cache:{key}",
                stale_ttl,
                self._serialize(entry)
            )
        except Exception as e:
            print(f"⚠️  Error writing to Redis: {e}")
    
    def delete(self, key: str) -> bool:
        """Eliminar clave del caché"""
        if not self._connected or not self._redis_client:
            return False
        
        try:
            deleted = self._redis_client.delete(f"cache:{key}")
            return deleted > 0
        except Exception as e:
            print(f"⚠️  Error deleting from Redis: {e}")
            return False
    
    def clear(self) -> int:
        """Limpiar todo el caché, retorna número de entradas eliminadas"""
        if not self._connected or not self._redis_client:
            return 0
        
        try:
            keys = self._redis_client.keys("cache:*")
            if keys:
                count = self._redis_client.delete(*keys)
                return count
            return 0
        except Exception as e:
            print(f"⚠️  Error clearing Redis: {e}")
            return 0
    
    def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidar todas las claves que correspondan al patrón
        Retorna el número de entradas eliminadas
        """
        if not self._connected or not self._redis_client:
            return 0
        
        try:
            # Redis pattern matching
            keys = self._redis_client.keys(f"cache:*{pattern}*")
            if keys:
                count = self._redis_client.delete(*keys)
                return count
            return 0
        except Exception as e:
            print(f"⚠️  Error invalidating pattern in Redis: {e}")
            return 0
    
    async def get_or_set(
        self,
        key: str,
        fetch_func: Callable,
        ttl_seconds: Optional[int] = None,
        stale_ttl_seconds: Optional[int] = None,
        allow_stale: bool = True
    ) -> Dict[str, Any]:
        """
        Obtener del caché o ejecutar función y almacenar
        Implementa stale-while-revalidate: retorna stale mientras revalida en background
        """
        # Try to get from cache
        cached = self.get(key, allow_stale=allow_stale)
        
        if cached and cached.get("fresh"):
            return cached["data"]
        
        if cached and cached.get("stale") and allow_stale:
            # Return stale and revalidate in background
            try:
                fresh_data = await fetch_func()
                self.set(key, fresh_data, ttl_seconds, stale_ttl_seconds)
            except:
                pass
            
            return cached["data"]
        
        # No cache or expired, fetch fresh data
        fresh_data = await fetch_func()
        self.set(key, fresh_data, ttl_seconds, stale_ttl_seconds)
        return fresh_data
    
    def cleanup_expired(self) -> int:
        """Limpiar entradas expiradas completamente (Redis handles this automatically)"""
        # Redis automatically expires keys, but we can check for expired entries
        if not self._connected or not self._redis_client:
            return 0
        
        try:
            keys = self._redis_client.keys("cache:*")
            count = 0
            now = datetime.utcnow()
            
            for key in keys:
                try:
                    data = self._redis_client.get(key)
                    if data:
                        entry = self._deserialize(data)
                        stale_expires_at = datetime.fromisoformat(entry.get("stale_expires_at", entry["expires_at"]))
                        if stale_expires_at < now:
                            self._redis_client.delete(key)
                            count += 1
                except:
                    continue
            
            return count
        except Exception as e:
            print(f"⚠️  Error cleaning up Redis: {e}")
            return 0
    
    async def get_status(self) -> Dict[str, Any]:
        """Obtener estado del caché para métricas"""
        if not self._connected or not self._redis_client:
            return {
                "total_entries": 0,
                "active_entries": 0,
                "stale_entries": 0,
                "expired_entries": 0,
                "last_cleaned": None,
                "redis_connected": False
            }
        
        try:
            keys = self._redis_client.keys("cache:*")
            total_entries = len(keys)
            active_entries = 0
            stale_entries = 0
            expired_entries = 0
            now = datetime.utcnow()
            
            for key in keys:
                try:
                    data = self._redis_client.get(key)
                    if data:
                        entry = self._deserialize(data)
                        expires_at = datetime.fromisoformat(entry["expires_at"])
                        stale_expires_at = datetime.fromisoformat(entry.get("stale_expires_at", entry["expires_at"]))
                        
                        if expires_at > now:
                            active_entries += 1
                        elif stale_expires_at > now:
                            stale_entries += 1
                        else:
                            expired_entries += 1
                except:
                    expired_entries += 1
            
            return {
                "total_entries": total_entries,
                "active_entries": active_entries,
                "stale_entries": stale_entries,
                "expired_entries": expired_entries,
                "last_cleaned": None,
                "redis_connected": True
            }
        except Exception as e:
            print(f"⚠️  Error getting Redis status: {e}")
            return {
                "total_entries": 0,
                "active_entries": 0,
                "stale_entries": 0,
                "expired_entries": 0,
                "last_cleaned": None,
                "redis_connected": False
            }
