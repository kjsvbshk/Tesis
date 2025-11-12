"""
Circuit Breaker pattern for RF-05
Implements circuit breaker for provider resilience
"""

from enum import Enum
from datetime import datetime, timedelta
from typing import Optional, Callable, Any, Dict
import asyncio

class CircuitState(Enum):
    """Estados del circuit breaker"""
    CLOSED = "closed"  # Funcionando normalmente
    OPEN = "open"  # Fallando, no permite requests
    HALF_OPEN = "half_open"  # Probando si se recuperó

class CircuitBreaker:
    """
    Circuit Breaker para proveedores externos
    Implementa el patrón circuit breaker para evitar sobrecarga cuando un proveedor falla
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout_seconds: int = 60,
        half_open_max_calls: int = 3
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout_seconds = recovery_timeout_seconds
        self.half_open_max_calls = half_open_max_calls
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.half_open_calls = 0
    
    def record_success(self):
        """Registrar éxito"""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.half_open_max_calls:
                # Se recuperó, cerrar el circuito
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.success_count = 0
                self.half_open_calls = 0
        elif self.state == CircuitState.CLOSED:
            # Resetear contador de fallos en estado cerrado
            self.failure_count = 0
    
    def record_failure(self):
        """Registrar fallo"""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.state == CircuitState.HALF_OPEN:
            # Falló en half-open, abrir de nuevo
            self.state = CircuitState.OPEN
            self.half_open_calls = 0
            self.success_count = 0
        elif self.state == CircuitState.CLOSED:
            # Verificar si supera el umbral
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
    
    def can_attempt(self) -> bool:
        """Verificar si se puede intentar una llamada"""
        if self.state == CircuitState.CLOSED:
            return True
        
        if self.state == CircuitState.OPEN:
            # Verificar si pasó el tiempo de recuperación
            if self.last_failure_time:
                elapsed = (datetime.utcnow() - self.last_failure_time).total_seconds()
                if elapsed >= self.recovery_timeout_seconds:
                    # Cambiar a half-open para probar
                    self.state = CircuitState.HALF_OPEN
                    self.half_open_calls = 0
                    self.success_count = 0
                    return True
            return False
        
        if self.state == CircuitState.HALF_OPEN:
            # Permitir un número limitado de llamadas en half-open
            if self.half_open_calls < self.half_open_max_calls:
                self.half_open_calls += 1
                return True
            return False
        
        return False
    
    async def call(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        Ejecutar función con circuit breaker
        """
        if not self.can_attempt():
            raise CircuitBreakerOpenError(
                f"Circuit breaker is {self.state.value}. Cannot make request."
            )
        
        try:
            result = await func(*args, **kwargs)
            self.record_success()
            return result
        except Exception as e:
            self.record_failure()
            raise
    
    def get_state(self) -> Dict[str, Any]:
        """Obtener estado actual del circuit breaker"""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "half_open_calls": self.half_open_calls
        }

class CircuitBreakerOpenError(Exception):
    """Excepción cuando el circuit breaker está abierto"""
    pass

