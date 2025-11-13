"""
Cache service for RF-04
Implements cache-first with TTL and stale-while-revalidate
"""

from typing import Optional, Dict, Any, Callable
from datetime import datetime, timedelta
import json
import hashlib

class CacheService:
    """
    Servicio de caché en memoria con TTL y stale-while-revalidate
    Para producción, se puede reemplazar con Redis
    """
    
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._prefix_index: Dict[str, set] = {}  # Índice de prefijos a claves
        self.default_ttl_seconds = 300  # 5 minutos por defecto
        self.default_stale_ttl_seconds = 600  # 10 minutos para stale
    
    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """Generar clave de caché única"""
        key_data = {
            "prefix": prefix,
            "args": args,
            "kwargs": sorted(kwargs.items())
        }
        key_str = json.dumps(key_data, sort_keys=True, default=str)
        key_hash = hashlib.md5(key_str.encode()).hexdigest()
        
        # Indexar la clave por prefijo para invalidación
        if prefix not in self._prefix_index:
            self._prefix_index[prefix] = set()
        self._prefix_index[prefix].add(key_hash)
        
        return key_hash
    
    def get(
        self,
        key: str,
        allow_stale: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Obtener valor del caché
        Si allow_stale=True, retorna valores stale mientras se revalida
        """
        if key not in self._cache:
            return None
        
        cache_entry = self._cache[key]
        now = datetime.utcnow()
        
        # Verificar si está fresco
        if cache_entry["expires_at"] > now:
            return {
                "data": cache_entry["data"],
                "fresh": True,
                "cached_at": cache_entry["cached_at"].isoformat()
            }
        
        # Si está expirado pero allow_stale y no pasó el stale_ttl
        if allow_stale and cache_entry.get("stale_expires_at"):
            if cache_entry["stale_expires_at"] > now:
                return {
                    "data": cache_entry["data"],
                    "fresh": False,
                    "stale": True,
                    "cached_at": cache_entry["cached_at"].isoformat()
                }
        
        # Expiró completamente
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
        now = datetime.utcnow()
        ttl = ttl_seconds or self.default_ttl_seconds
        stale_ttl = stale_ttl_seconds or self.default_stale_ttl_seconds
        
        self._cache[key] = {
            "data": data,
            "cached_at": now,
            "expires_at": now + timedelta(seconds=ttl),
            "stale_expires_at": now + timedelta(seconds=stale_ttl)
        }
    
    def delete(self, key: str) -> bool:
        """Eliminar clave del caché"""
        if key in self._cache:
            del self._cache[key]
            # Remover del índice de prefijos
            for prefix, keys in self._prefix_index.items():
                keys.discard(key)
            return True
        return False
    
    def clear(self) -> int:
        """Limpiar todo el caché, retorna número de entradas eliminadas"""
        count = len(self._cache)
        self._cache.clear()
        self._prefix_index.clear()
        return count
    
    def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidar todas las claves que correspondan al prefijo
        Retorna el número de entradas eliminadas
        """
        if pattern not in self._prefix_index:
            return 0
        
        keys_to_delete = list(self._prefix_index[pattern])
        count = 0
        
        for key in keys_to_delete:
            if key in self._cache:
                del self._cache[key]
                count += 1
        
        # Limpiar el índice del prefijo
        del self._prefix_index[pattern]
        
        return count
    
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
        # Intentar obtener del caché
        cached = self.get(key, allow_stale=allow_stale)
        
        if cached and cached.get("fresh"):
            # Cache fresco, retornar directamente
            return cached["data"]
        
        if cached and cached.get("stale") and allow_stale:
            # Cache stale, retornar stale y revalidar en background
            # En producción, esto se haría en un task/worker
            # Por ahora, revalidamos síncronamente pero retornamos stale primero
            try:
                fresh_data = await fetch_func()
                self.set(key, fresh_data, ttl_seconds, stale_ttl_seconds)
            except:
                pass  # Si falla la revalidación, usar stale
            
            return cached["data"]
        
        # No hay caché o expiró, obtener datos frescos
        fresh_data = await fetch_func()
        self.set(key, fresh_data, ttl_seconds, stale_ttl_seconds)
        return fresh_data
    
    def cleanup_expired(self) -> int:
        """Limpiar entradas expiradas completamente"""
        now = datetime.utcnow()
        expired_keys = [
            key for key, entry in self._cache.items()
            if entry.get("stale_expires_at") and entry["stale_expires_at"] < now
        ]
        
        for key in expired_keys:
            del self._cache[key]
        
        return len(expired_keys)
    
    async def get_status(self) -> Dict[str, Any]:
        """Obtener estado del caché para métricas"""
        now = datetime.utcnow()
        total_entries = len(self._cache)
        active_entries = 0
        stale_entries = 0
        expired_entries = 0
        
        for entry in self._cache.values():
            if entry["expires_at"] > now:
                active_entries += 1
            elif entry.get("stale_expires_at") and entry["stale_expires_at"] > now:
                stale_entries += 1
            else:
                expired_entries += 1
        
        return {
            "total_entries": total_entries,
            "active_entries": active_entries,
            "stale_entries": stale_entries,
            "expired_entries": expired_entries,
            "last_cleaned": None  # Se puede agregar tracking de última limpieza
        }

# Instancia global del servicio de caché
cache_service = CacheService()

