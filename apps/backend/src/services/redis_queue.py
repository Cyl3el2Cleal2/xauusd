import json
import asyncio
import time
from typing import Dict, Any, Optional, Callable
from datetime import datetime
import redis.asyncio as redis
import logging

logger = logging.getLogger(__name__)


class RedisQueueManager:
    """Redis queue manager for async task processing"""

    def __init__(self, host: str = "localhost", port: int = 6379, password: str = "example", db: int = 0):
        self.host = host
        self.port = port
        self.password = password
        self.db = db
        self.redis_client: Optional[redis.Redis] = None
        self.is_connected = False

    async def connect(self):
        """Connect to Redis"""
        try:
            self.redis_client = redis.Redis(
                host=self.host,
                port=self.port,
                password=self.password,
                db=self.db,
                decode_responses=True
            )

            # Test connection
            await self.redis_client.ping()
            self.is_connected = True
            logger.info(f"Connected to Redis at {self.host}:{self.port}")

        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.is_connected = False
            raise

    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis_client:
            await self.redis_client.close()
            self.is_connected = False
            logger.info("Disconnected from Redis")

    async def enqueue_task(
        self,
        queue_name: str,
        task_data: Dict[str, Any],
        priority: int = 0
    ) -> str:
        """
        Enqueue a task to Redis queue

        Args:
            queue_name: Name of the queue
            task_data: Task data to process
            priority: Priority level (higher = more priority)

        Returns:
            Task ID
        """
        if not self.is_connected:
            await self.connect()

        task_id = task_data.get("processing_id")
        if not task_id:
            import uuid
            task_id = str(uuid.uuid4())
            task_data["processing_id"] = task_id

        # Add timestamp and priority
        task_data["queued_at"] = datetime.utcnow().isoformat()
        task_data["priority"] = priority

        # Serialize task data
        serialized_data = json.dumps(task_data)

        # Use Redis list with priority (zset for priority queue)
        if priority > 0:
            # High priority tasks go to priority queue
            await self.redis_client.zadd(
                f"{queue_name}_priority",
                {serialized_data: priority + time.time()}  # Use priority + timestamp for ordering
            )
        else:
            # Normal tasks go to regular queue
            await self.redis_client.lpush(queue_name, serialized_data)

        logger.info(f"Task {task_id} enqueued to {queue_name}")
        return task_id

    async def dequeue_task(
        self,
        queue_name: str,
        timeout: int = 10
    ) -> Optional[Dict[str, Any]]:
        """
        Dequeue a task from Redis queue

        Args:
            queue_name: Name of the queue
            timeout: Timeout in seconds

        Returns:
            Task data or None if timeout
        """
        if not self.is_connected:
            await self.connect()

        try:
            # First try priority queue
            priority_result = await self.redis_client.zpopmin(f"{queue_name}_priority", 1)
            if priority_result:
                serialized_data = priority_result[0][0]
                task_data = json.loads(serialized_data)
                logger.info(f"Dequeued priority task {task_data.get('processing_id')} from {queue_name}")
                return task_data

            # Then try normal queue
            result = await self.redis_client.brpop(queue_name, timeout=timeout)
            if result:
                _, serialized_data = result
                task_data = json.loads(serialized_data)
                logger.info(f"Dequeued task {task_data.get('processing_id')} from {queue_name}")
                return task_data

        except Exception as e:
            logger.error(f"Error dequeuing task from {queue_name}: {e}")

        return None

    async def get_queue_size(self, queue_name: str) -> Dict[str, int]:
        """Get queue sizes for both normal and priority queues"""
        if not self.is_connected:
            await self.connect()

        try:
            normal_size = await self.redis_client.llen(queue_name)
            priority_size = await self.redis_client.zcard(f"{queue_name}_priority")

            return {
                "normal": normal_size,
                "priority": priority_size,
                "total": normal_size + priority_size
            }
        except Exception as e:
            logger.error(f"Error getting queue size for {queue_name}: {e}")
            return {"normal": 0, "priority": 0, "total": 0}

    async def set_task_status(
        self,
        task_id: str,
        status: str,
        result_data: Optional[Dict[str, Any]] = None
    ):
        """Set task status and result in Redis"""
        if not self.is_connected:
            await self.connect()

        status_key = f"task_status:{task_id}"
        status_data = {
            "task_id": task_id,
            "status": status,
            "updated_at": datetime.utcnow().isoformat()
        }

        if result_data:
            status_data["result"] = result_data

        await self.redis_client.setex(
            status_key,
            3600,  # Expire after 1 hour
            json.dumps(status_data)
        )

        logger.info(f"Task {task_id} status set to {status}")

    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task status from Redis"""
        if not self.is_connected:
            await self.connect()

        try:
            status_key = f"task_status:{task_id}"
            status_data = await self.redis_client.get(status_key)

            if status_data:
                return json.loads(status_data)
        except Exception as e:
            logger.error(f"Error getting task status for {task_id}: {e}")

        return None

    async def clear_queue(self, queue_name: str):
        """Clear all tasks from a queue"""
        if not self.is_connected:
            await self.connect()

        try:
            await self.redis_client.delete(queue_name)
            await self.redis_client.delete(f"{queue_name}_priority")
            logger.info(f"Cleared queue {queue_name}")
        except Exception as e:
            logger.error(f"Error clearing queue {queue_name}: {e}")

    async def get_health(self) -> Dict[str, Any]:
        """Get Redis health status"""
        if not self.is_connected:
            return {"connected": False, "error": "Not connected"}

        try:
            info = await self.redis_client.info()
            return {
                "connected": True,
                "redis_version": info.get("redis_version"),
                "used_memory": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "uptime_seconds": info.get("uptime_in_seconds")
            }
        except Exception as e:
            return {"connected": False, "error": str(e)}


# Global queue manager instance
queue_manager = RedisQueueManager()

# Task processor decorator
def task_processor(queue_name: str):
    """Decorator for task processing functions"""
    def decorator(func: Callable):
        async def wrapper(*args, **kwargs):
            try:
                # Get task data from queue
                task_data = await queue_manager.dequeue_task(queue_name)
                if not task_data:
                    return None

                task_id = task_data.get("processing_id")

                # Update task status to processing
                await queue_manager.set_task_status(task_id, "processing")

                # Process the task
                try:
                    result = await func(task_data, *args, **kwargs)

                    # Update task status to completed
                    await queue_manager.set_task_status(
                        task_id,
                        "completed",
                        result
                    )

                    return result

                except Exception as e:
                    # Update task status to failed
                    await queue_manager.set_task_status(
                        task_id,
                        "failed",
                        {"error": str(e)}
                    )

                    logger.error(f"Task {task_id} failed: {e}")
                    raise

            except Exception as e:
                logger.error(f"Task processor error: {e}")
                return None

        return wrapper
    return decorator


# Trading specific queues
TRADING_QUEUE = "trading_tasks"
HIGH_PRIORITY_QUEUE = "trading_high_priority"


async def enqueue_trading_task(
    transaction_data: Dict[str, Any],
    high_priority: bool = False
) -> str:
    """Enqueue a trading task"""
    queue_name = HIGH_PRIORITY_QUEUE if high_priority else TRADING_QUEUE
    priority = 1 if high_priority else 0

    return await queue_manager.enqueue_task(
        queue_name=queue_name,
        task_data=transaction_data,
        priority=priority
    )


async def get_trading_task_status(task_id: str) -> Optional[Dict[str, Any]]:
    """Get trading task status from Redis"""
    return await queue_manager.get_task_status(task_id)
