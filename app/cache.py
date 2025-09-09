#!/usr/bin/env python3
"""
Advanced Redis Caching System
Provides intelligent caching with TTL management, cache invalidation, and performance optimization
"""
import json
import time
import hashlib
from typing import Any, Dict, List, Optional, Union, Callable
from functools import wraps
import redis.asyncio as redis
import structlog
from app.config import settings

logger = structlog.get_logger()

class CacheManager:
    """Advanced Redis cache manager with intelligent caching strategies"""
    
    def __init__(self):
        self.redis: Optional[redis.Redis] = None
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "errors": 0,
            "total_time_saved": 0.0
        }
        self.default_ttl = settings.cache_ttl
        
    async def initialize(self) -> None:
        """Initialize Redis connection with optimized settings"""
        try:
            self.redis = redis.from_url(
                settings.redis_url,
                max_connections=settings.redis_max_connections,
                retry_on_timeout=True,
                retry_on_error=[redis.ConnectionError, redis.TimeoutError],
                health_check_interval=30,
                decode_responses=True,
                socket_keepalive=True,
                socket_keepalive_options={}
            )
            
            # Test connection
            await self.redis.ping()
            
            # Set up Redis configurations for optimal performance
            try:
                await self.redis.config_set("maxmemory-policy", "allkeys-lru")
                await self.redis.config_set("timeout", "300")
            except redis.ResponseError:
                # Config commands might not be available in all Redis setups
                pass
            
            logger.info(
                "Redis cache initialized successfully",
                url=settings.redis_url,
                max_connections=settings.redis_max_connections
            )
            
        except Exception as e:
            logger.warning("Redis initialization failed, caching disabled", error=str(e))
            self.redis = None
    
    async def close(self) -> None:
        """Close Redis connection"""
        if self.redis:
            await self.redis.close()
            logger.info("Redis connection closed", stats=self.stats)
    
    def _generate_cache_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate a consistent cache key from arguments"""
        key_data = f"{prefix}:{args}:{sorted(kwargs.items())}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    async def get(self, key: str, default: Any = None) -> Any:
        """Get value from cache with statistics tracking"""
        if not self.redis:
            self.stats["misses"] += 1
            return default
        
        try:
            start_time = time.time()
            value = await self.redis.get(key)
            
            if value is not None:
                self.stats["hits"] += 1
                self.stats["total_time_saved"] += time.time() - start_time
                
                # Try to deserialize JSON
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    return value
            else:
                self.stats["misses"] += 1
                return default
                
        except Exception as e:
            self.stats["errors"] += 1
            logger.warning("Cache get failed", key=key, error=str(e))
            return default
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with TTL"""
        if not self.redis:
            return False
        
        try:
            # Serialize complex objects to JSON
            if isinstance(value, (dict, list, tuple)):
                serialized_value = json.dumps(value, default=str)
            else:
                serialized_value = str(value)
            
            ttl = ttl or self.default_ttl
            await self.redis.setex(key, ttl, serialized_value)
            
            self.stats["sets"] += 1
            return True
            
        except Exception as e:
            self.stats["errors"] += 1
            logger.warning("Cache set failed", key=key, error=str(e))
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache"""
        if not self.redis:
            return False
        
        try:
            result = await self.redis.delete(key)
            self.stats["deletes"] += 1
            return bool(result)
            
        except Exception as e:
            self.stats["errors"] += 1
            logger.warning("Cache delete failed", key=key, error=str(e))
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching a pattern"""
        if not self.redis:
            return 0
        
        try:
            keys = await self.redis.keys(pattern)
            if keys:
                deleted = await self.redis.delete(*keys)
                self.stats["deletes"] += deleted
                return deleted
            return 0
            
        except Exception as e:
            self.stats["errors"] += 1
            logger.warning("Cache pattern delete failed", pattern=pattern, error=str(e))
            return 0
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        if not self.redis:
            return False
        
        try:
            return bool(await self.redis.exists(key))
        except Exception as e:
            self.stats["errors"] += 1
            logger.warning("Cache exists check failed", key=key, error=str(e))
            return False
    
    async def increment(self, key: str, amount: int = 1, ttl: Optional[int] = None) -> int:
        """Increment a counter in cache"""
        if not self.redis:
            return 0
        
        try:
            # Use pipeline for atomic operations
            pipe = self.redis.pipeline()
            pipe.incr(key, amount)
            if ttl:
                pipe.expire(key, ttl)
            results = await pipe.execute()
            return results[0]
            
        except Exception as e:
            self.stats["errors"] += 1
            logger.warning("Cache increment failed", key=key, error=str(e))
            return 0
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        cache_stats = self.stats.copy()
        
        # Calculate hit rate
        total_requests = cache_stats["hits"] + cache_stats["misses"]
        cache_stats["hit_rate"] = (
            cache_stats["hits"] / total_requests * 100
            if total_requests > 0 else 0
        )
        
        # Add Redis info if available
        if self.redis:
            try:
                redis_info = await self.redis.info()
                cache_stats["redis_info"] = {
                    "used_memory": redis_info.get("used_memory_human"),
                    "connected_clients": redis_info.get("connected_clients"),
                    "total_commands_processed": redis_info.get("total_commands_processed"),
                    "keyspace_hits": redis_info.get("keyspace_hits"),
                    "keyspace_misses": redis_info.get("keyspace_misses")
                }
            except Exception as e:
                cache_stats["redis_error"] = str(e)
        
        return cache_stats
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform cache health check"""
        if not self.redis:
            return {"status": "disabled", "reason": "redis_not_initialized"}
        
        try:
            start_time = time.time()
            
            # Test basic operations
            test_key = "health_check_test"
            await self.redis.set(test_key, "test_value", ex=10)
            value = await self.redis.get(test_key)
            await self.redis.delete(test_key)
            
            response_time = time.time() - start_time
            
            if value != "test_value":
                return {"status": "unhealthy", "reason": "test_operation_failed"}
            
            return {
                "status": "healthy",
                "response_time": f"{response_time:.3f}s",
                "stats": await self.get_stats()
            }
            
        except Exception as e:
            return {"status": "unhealthy", "reason": str(e)}

# Cache decorators for automatic caching
def cache_result(ttl: int = None, key_prefix: str = "func"):
    """Decorator to automatically cache function results"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache = cache_manager
            
            # Generate cache key
            cache_key = cache._generate_cache_key(
                f"{key_prefix}:{func.__name__}", *args, **kwargs
            )
            
            # Try to get from cache first
            cached_result = await cache.get(cache_key)
            if cached_result is not None:
                logger.debug("Cache hit", function=func.__name__, key=cache_key)
                return cached_result
            
            # Execute function and cache result
            start_time = time.time()
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            # Cache the result
            cache_ttl = ttl or cache.default_ttl
            await cache.set(cache_key, result, cache_ttl)
            
            logger.debug(
                "Function executed and cached",
                function=func.__name__,
                execution_time=f"{execution_time:.3f}s",
                cache_key=cache_key
            )
            
            return result
        return wrapper
    return decorator

def invalidate_cache_pattern(pattern: str):
    """Decorator to invalidate cache patterns after function execution"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            
            # Invalidate cache pattern
            deleted_count = await cache_manager.delete_pattern(pattern)
            if deleted_count > 0:
                logger.info(
                    "Cache invalidated",
                    function=func.__name__,
                    pattern=pattern,
                    deleted_keys=deleted_count
                )
            
            return result
        return wrapper
    return decorator

# Specialized cache functions for common use cases
class UserCache:
    """User-specific caching operations"""
    
    @staticmethod
    async def get_user_profile(user_id: str) -> Optional[Dict[str, Any]]:
        """Get cached user profile"""
        return await cache_manager.get(f"user:profile:{user_id}")
    
    @staticmethod
    async def set_user_profile(user_id: str, profile: Dict[str, Any], ttl: int = 1800) -> bool:
        """Cache user profile"""
        return await cache_manager.set(f"user:profile:{user_id}", profile, ttl)
    
    @staticmethod
    async def invalidate_user_cache(user_id: str) -> int:
        """Invalidate all user-related cache"""
        return await cache_manager.delete_pattern(f"user:*:{user_id}")

class OrganizationCache:
    """Organization-specific caching operations"""
    
    @staticmethod
    async def get_organization_data(org_id: str) -> Optional[Dict[str, Any]]:
        """Get cached organization data"""
        return await cache_manager.get(f"org:data:{org_id}")
    
    @staticmethod
    async def set_organization_data(org_id: str, data: Dict[str, Any], ttl: int = 600) -> bool:
        """Cache organization data"""
        return await cache_manager.set(f"org:data:{org_id}", data, ttl)
    
    @staticmethod
    async def invalidate_organization_cache(org_id: str) -> int:
        """Invalidate all organization-related cache"""
        return await cache_manager.delete_pattern(f"org:*:{org_id}")

class ProjectCache:
    """Project-specific caching operations"""
    
    @staticmethod
    async def get_project_data(project_id: str) -> Optional[Dict[str, Any]]:
        """Get cached project data"""
        return await cache_manager.get(f"project:data:{project_id}")
    
    @staticmethod
    async def set_project_data(project_id: str, data: Dict[str, Any], ttl: int = 300) -> bool:
        """Cache project data"""
        return await cache_manager.set(f"project:data:{project_id}", data, ttl)
    
    @staticmethod
    async def invalidate_project_cache(project_id: str) -> int:
        """Invalidate all project-related cache"""
        return await cache_manager.delete_pattern(f"project:*:{project_id}")

# Global cache manager instance
cache_manager = CacheManager()
