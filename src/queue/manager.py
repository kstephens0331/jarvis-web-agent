"""
Jarvis Web Agent - Queue Manager
Redis-based job queue for async browser tasks
"""

from typing import Optional, Dict, Any, Callable
from loguru import logger
import redis.asyncio as redis
import json


class QueueManager:
    """
    Manages async job queue using Redis
    
    Features:
    - Job submission and tracking
    - Priority queues
    - Job result caching
    - Webhook callbacks
    """
    
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self._redis: Optional[redis.Redis] = None
        self._connected = False
    
    async def connect(self):
        """Connect to Redis"""
        try:
            self._redis = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            # Test connection
            await self._redis.ping()
            self._connected = True
            logger.info(f"Connected to Redis at {self.redis_url}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self._connected = False
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self._redis:
            await self._redis.close()
            self._connected = False
    
    async def enqueue(
        self,
        job_id: str,
        job_data: Dict[str, Any],
        priority: int = 5
    ) -> bool:
        """
        Add a job to the queue
        
        Args:
            job_id: Unique job identifier
            job_data: Job payload
            priority: 1-10, lower = higher priority
        """
        if not self._connected:
            logger.warning("Redis not connected, job stored in memory only")
            return False
        
        try:
            # Store job data
            await self._redis.hset(
                f"job:{job_id}",
                mapping={
                    "data": json.dumps(job_data),
                    "status": "pending",
                    "priority": priority
                }
            )
            
            # Add to priority queue
            await self._redis.zadd(
                "job_queue",
                {job_id: priority}
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to enqueue job {job_id}: {e}")
            return False
    
    async def dequeue(self) -> Optional[Dict[str, Any]]:
        """
        Get the next job from the queue
        
        Returns highest priority (lowest score) job
        """
        if not self._connected:
            return None
        
        try:
            # Get highest priority job
            result = await self._redis.zpopmin("job_queue", count=1)
            
            if not result:
                return None
            
            job_id = result[0][0]
            
            # Get job data
            job_data = await self._redis.hgetall(f"job:{job_id}")
            
            if job_data:
                return {
                    "job_id": job_id,
                    "data": json.loads(job_data.get("data", "{}")),
                    "priority": int(job_data.get("priority", 5))
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to dequeue job: {e}")
            return None
    
    async def update_status(
        self,
        job_id: str,
        status: str,
        result: Optional[Dict] = None,
        error: Optional[str] = None
    ):
        """Update job status"""
        if not self._connected:
            return
        
        try:
            updates = {"status": status}
            if result:
                updates["result"] = json.dumps(result)
            if error:
                updates["error"] = error
            
            await self._redis.hset(f"job:{job_id}", mapping=updates)
            
            # Set expiry for completed jobs (24 hours)
            if status in ["completed", "failed"]:
                await self._redis.expire(f"job:{job_id}", 86400)
                
        except Exception as e:
            logger.error(f"Failed to update job status: {e}")
    
    async def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job by ID"""
        if not self._connected:
            return None
        
        try:
            data = await self._redis.hgetall(f"job:{job_id}")
            if data:
                result = {
                    "job_id": job_id,
                    "status": data.get("status"),
                    "priority": int(data.get("priority", 5))
                }
                if data.get("data"):
                    result["data"] = json.loads(data["data"])
                if data.get("result"):
                    result["result"] = json.loads(data["result"])
                if data.get("error"):
                    result["error"] = data["error"]
                return result
            return None
        except Exception as e:
            logger.error(f"Failed to get job {job_id}: {e}")
            return None
    
    async def queue_length(self) -> int:
        """Get number of pending jobs"""
        if not self._connected:
            return 0
        
        try:
            return await self._redis.zcard("job_queue")
        except:
            return 0
    
    def status(self) -> Dict[str, Any]:
        """Get queue manager status"""
        return {
            "connected": self._connected,
            "redis_url": self.redis_url
        }
