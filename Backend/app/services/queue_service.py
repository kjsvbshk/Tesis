"""
Queue Service for Redis + RQ
Handles background task queuing using Redis Queue
"""

from typing import Optional, Callable, Any
from app.core.config import settings

# Try to import RQ
try:
    from rq import Queue
    from redis import Redis
    RQ_AVAILABLE = True
except ImportError:
    RQ_AVAILABLE = False
    Queue = None
    Redis = None


class QueueService:
    """
    Service for managing background tasks with Redis Queue
    Falls back gracefully if Redis is not available
    """
    
    def __init__(self):
        self._redis_conn: Optional[Redis] = None
        self._queues: dict[str, Queue] = {}
        self._available = False
        
        if RQ_AVAILABLE and settings.USE_REDIS:
            self._init_redis()
    
    def _init_redis(self):
        """Initialize Redis connection for RQ"""
        try:
            redis_url = getattr(settings, 'REDIS_URL', None)
            redis_host = getattr(settings, 'REDIS_HOST', 'localhost')
            redis_port = getattr(settings, 'REDIS_PORT', 6379)
            redis_password = getattr(settings, 'REDIS_PASSWORD', None)
            redis_db = getattr(settings, 'REDIS_DB', 0)
            
            if redis_url:
                self._redis_conn = Redis.from_url(redis_url)
            else:
                self._redis_conn = Redis(
                    host=redis_host,
                    port=redis_port,
                    password=redis_password,
                    db=redis_db
                )
            
            # Test connection
            self._redis_conn.ping()
            self._available = True
            
            # Create default queue
            self._queues['default'] = Queue('default', connection=self._redis_conn)
            self._queues['high'] = Queue('high', connection=self._redis_conn)  # Prioridad alta
            self._queues['low'] = Queue('low', connection=self._redis_conn)    # Prioridad baja
            
            print("✅ Redis Queue service initialized successfully")
        except Exception as e:
            print(f"⚠️  Redis Queue not available: {e}, tasks will execute synchronously")
            self._available = False
            self._redis_conn = None
    
    def enqueue(
        self,
        func: Callable,
        *args,
        queue_name: str = 'default',
        timeout: int = 300,
        **kwargs
    ) -> Optional[Any]:
        """
        Enqueue a task to be executed asynchronously
        
        Args:
            func: Function to execute
            *args: Arguments for the function
            queue_name: Queue name ('default', 'high', 'low')
            timeout: Task timeout in seconds
            **kwargs: Keyword arguments for the function
        
        Returns:
            Job object if queued, None if executed synchronously
        """
        if not self._available or not self._redis_conn:
            # Fallback: execute synchronously
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"⚠️  Redis Queue not available, executing {func.__name__} synchronously")
            print(f"⚠️  Redis Queue not available, executing {func.__name__} synchronously")
            try:
                result = func(*args, **kwargs)
                logger.info(f"✅ Task {func.__name__} executed synchronously (fallback mode)")
                return result
            except Exception as e:
                logger.error(f"❌ Error executing {func.__name__} synchronously: {e}", exc_info=True)
                print(f"❌ Error executing {func.__name__} synchronously: {e}")
                raise
        
        try:
            queue = self._queues.get(queue_name, self._queues['default'])
            job = queue.enqueue(
                func,
                *args,
                job_timeout=timeout,
                **kwargs
            )
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"✅ Task {func.__name__} queued (Job ID: {job.id})")
            print(f"✅ Task {func.__name__} queued (Job ID: {job.id})")
            return job
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"❌ Error enqueueing task {func.__name__}: {e}, falling back to synchronous execution")
            print(f"❌ Error enqueueing task {func.__name__}: {e}")
            # Fallback: execute synchronously
            try:
                result = func(*args, **kwargs)
                logger.info(f"✅ Task {func.__name__} executed synchronously (fallback after enqueue error)")
                return result
            except Exception as e2:
                logger.error(f"❌ Error executing {func.__name__} synchronously: {e2}", exc_info=True)
                print(f"❌ Error executing {func.__name__} synchronously: {e2}")
                raise
    
    def get_queue(self, queue_name: str = 'default') -> Optional[Queue]:
        """Get a specific queue"""
        if not self._available:
            return None
        return self._queues.get(queue_name, self._queues['default'])
    
    def is_available(self) -> bool:
        """Check if Redis Queue is available"""
        return self._available
    
    def get_queue_stats(self) -> dict:
        """Get statistics about queues"""
        if not self._available:
            return {
                "available": False,
                "queues": {}
            }
        
        stats = {
            "available": True,
            "queues": {}
        }
        
        for name, queue in self._queues.items():
            stats["queues"][name] = {
                "name": name,
                "count": len(queue),
                "failed": len(queue.failed_job_registry)
            }
        
        return stats


# Global instance
queue_service = QueueService()
