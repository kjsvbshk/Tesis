"""
RQ Worker for processing background tasks
Run this as a separate process: python -m app.workers.rq_worker
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from rq import Worker, Queue, Connection
from redis import Redis
from app.core.config import settings
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)


def get_redis_connection():
    """Get Redis connection for RQ"""
    redis_url = getattr(settings, 'REDIS_URL', None)
    redis_host = getattr(settings, 'REDIS_HOST', 'localhost')
    redis_port = getattr(settings, 'REDIS_PORT', 6379)
    redis_password = getattr(settings, 'REDIS_PASSWORD', None)
    redis_db = getattr(settings, 'REDIS_DB', 0)
    
    if redis_url:
        return Redis.from_url(redis_url)
    else:
        return Redis(
            host=redis_host,
            port=redis_port,
            password=redis_password,
            db=redis_db
        )


def main():
    """Main function to start RQ worker"""
    try:
        redis_conn = get_redis_connection()
        
        # Test connection
        redis_conn.ping()
        logger.info("✅ Connected to Redis")
        
        # Define queues (default, high priority, low priority)
        queues = [
            Queue('high', connection=redis_conn),    # High priority tasks
            Queue('default', connection=redis_conn), # Default tasks
            Queue('low', connection=redis_conn)      # Low priority tasks
        ]
        
        logger.info("🚀 Starting RQ worker...")
        logger.info(f"   Listening to queues: high, default, low")
        
        # Start worker
        with Connection(redis_conn):
            worker = Worker(queues)
            worker.work()
            
    except Exception as e:
        logger.error(f"❌ Error starting RQ worker: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
