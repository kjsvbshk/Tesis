"""
Provider Orchestrator service for RF-05
Handles provider orchestration with timeouts, retries, and circuit breakers
"""

from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
import asyncio
import httpx

from app.models import Provider, ProviderEndpoint
from app.services.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError

class ProviderOrchestrator:
    """
    Orquestador de proveedores externos
    Maneja timeouts, reintentos y circuit breakers
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.circuit_breakers: Dict[int, CircuitBreaker] = {}
        self.default_timeout_seconds = 30
        self.default_max_retries = 3
        self.default_retry_delay_seconds = 1
    
    def _get_circuit_breaker(self, provider_id: int, provider: Provider) -> CircuitBreaker:
        """Obtener o crear circuit breaker para un proveedor"""
        if provider_id not in self.circuit_breakers:
            self.circuit_breakers[provider_id] = CircuitBreaker(
                failure_threshold=provider.circuit_breaker_threshold,
                recovery_timeout_seconds=60,
                half_open_max_calls=3
            )
        return self.circuit_breakers[provider_id]
    
    async def _call_provider_endpoint(
        self,
        endpoint: ProviderEndpoint,
        timeout_seconds: int,
        max_retries: int,
        retry_delay_seconds: float
    ) -> Dict[str, Any]:
        """
        Llamar a un endpoint de proveedor con reintentos
        """
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                    # Parsear headers si existen
                    headers = {}
                    if endpoint.headers:
                        import json
                        try:
                            headers = json.loads(endpoint.headers)
                        except:
                            pass
                    
                    # Determinar método HTTP
                    method = getattr(endpoint, 'method', 'GET').upper()
                    
                    if method == 'GET':
                        response = await client.get(endpoint.url, headers=headers)
                    elif method == 'POST':
                        response = await client.post(endpoint.url, headers=headers)
                    else:
                        response = await client.request(method, endpoint.url, headers=headers)
                    
                    response.raise_for_status()
                    
                    return {
                        "success": True,
                        "data": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text,
                        "status_code": response.status_code,
                        "provider_id": endpoint.provider_id,
                        "endpoint_id": endpoint.id
                    }
            
            except httpx.TimeoutException as e:
                last_error = f"Timeout after {timeout_seconds}s"
                if attempt < max_retries:
                    await asyncio.sleep(retry_delay_seconds * (attempt + 1))
                    continue
                raise
            
            except httpx.HTTPStatusError as e:
                last_error = f"HTTP {e.response.status_code}: {e.response.text}"
                # No reintentar errores 4xx (excepto 429)
                if 400 <= e.response.status_code < 500 and e.response.status_code != 429:
                    raise
                if attempt < max_retries:
                    await asyncio.sleep(retry_delay_seconds * (attempt + 1))
                    continue
                raise
            
            except Exception as e:
                last_error = str(e)
                if attempt < max_retries:
                    await asyncio.sleep(retry_delay_seconds * (attempt + 1))
                    continue
                raise
        
        # Si llegamos aquí, todos los reintentos fallaron
        raise Exception(f"All retries failed. Last error: {last_error}")
    
    async def call_provider(
        self,
        provider_code: str,
        purpose: str,
        timeout_seconds: Optional[int] = None,
        max_retries: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Llamar a un proveedor específico por código y propósito
        """
        # Obtener proveedor
        provider = self.db.query(Provider).filter(
            Provider.code == provider_code,
            Provider.is_active == True
        ).first()
        
        if not provider:
            raise ValueError(f"Provider '{provider_code}' not found or inactive")
        
        # Obtener endpoint
        endpoint = self.db.query(ProviderEndpoint).filter(
            ProviderEndpoint.provider_id == provider.id,
            ProviderEndpoint.purpose == purpose
        ).first()
        
        if not endpoint:
            raise ValueError(f"Endpoint '{purpose}' not found for provider '{provider_code}'")
        
        # Obtener circuit breaker
        circuit_breaker = self._get_circuit_breaker(provider.id, provider)
        
        # Configurar timeouts y reintentos
        timeout = timeout_seconds or provider.timeout_seconds or self.default_timeout_seconds
        max_retries_val = max_retries or provider.max_retries or self.default_max_retries
        retry_delay = self.default_retry_delay_seconds
        
        try:
            # Llamar con circuit breaker
            result = await circuit_breaker.call(
                self._call_provider_endpoint,
                endpoint,
                timeout,
                max_retries_val,
                retry_delay
            )
            
            return result
        
        except CircuitBreakerOpenError:
            return {
                "success": False,
                "error": "Circuit breaker is open",
                "provider_id": provider.id,
                "provider_code": provider_code,
                "circuit_breaker_state": circuit_breaker.get_state()
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "provider_id": provider.id,
                "provider_code": provider_code
            }
    
    async def call_multiple_providers(
        self,
        provider_codes: List[str],
        purpose: str,
        timeout_seconds: Optional[int] = None,
        max_retries: Optional[int] = None,
        require_all: bool = False
    ) -> Dict[str, Any]:
        """
        Llamar a múltiples proveedores en paralelo
        Si require_all=True, todos deben tener éxito
        Si require_all=False, retorna los que tengan éxito
        """
        tasks = [
            self.call_provider(code, purpose, timeout_seconds, max_retries)
            for code in provider_codes
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successful = []
        failed = []
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                failed.append({
                    "provider_code": provider_codes[i],
                    "error": str(result)
                })
            elif result.get("success"):
                successful.append(result)
            else:
                failed.append({
                    "provider_code": provider_codes[i],
                    "error": result.get("error", "Unknown error")
                })
        
        if require_all and len(failed) > 0:
            raise Exception(f"Some providers failed: {failed}")
        
        return {
            "successful": successful,
            "failed": failed,
            "total_requested": len(provider_codes),
            "total_successful": len(successful),
            "total_failed": len(failed)
        }
    
    def get_provider_status(self, provider_code: str) -> Dict[str, Any]:
        """Obtener estado de un proveedor (circuit breaker, etc.)"""
        provider = self.db.query(Provider).filter(
            Provider.code == provider_code
        ).first()
        
        if not provider:
            return {"error": "Provider not found"}
        
        circuit_breaker = self._get_circuit_breaker(provider.id, provider)
        
        return {
            "provider_code": provider_code,
            "provider_id": provider.id,
            "is_active": provider.is_active,
            "circuit_breaker": circuit_breaker.get_state()
        }

