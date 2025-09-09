"""
Redis Caching System for Agno WorkSphere
Implements caching for frequently accessed data to improve API response times
"""

import json
import pickle
import asyncio
from typing import Any, Optional, Union, Dict
import logging
from datetime import timedelta
import hashlib

# For development, we'll use a simple in-memory cache
# In production, this would use Redis
class InMemoryCache:
    """In-memory cache implementation for development"""
    
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._ttl: Dict[str, float] = {}
        
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if key in self._cache:
            # Check TTL
            if key in self._ttl:
                import time
                if time.time() > self._ttl[key]:
                    # Expired
                    del self._cache[key]
                    del self._ttl[key]
                    return None
            
            return self._cache[key]['value']
        return None
    
    async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Set value in cache with TTL"""
        import time
        self._cache[key] = {'value': value}
        if ttl > 0:
            self._ttl[key] = time.time() + ttl
        return True
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if key in self._cache:
            del self._cache[key]
            if key in self._ttl:
                del self._ttl[key]
            return True
        return False
    
    async def clear(self) -> bool:
        """Clear all cache"""
        self._cache.clear()
        self._ttl.clear()
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        import time
        current_time = time.time()
        active_keys = 0
        expired_keys = 0
        
        for key in self._cache:
            if key in self._ttl and current_time > self._ttl[key]:
                expired_keys += 1
            else:
                active_keys += 1
        
        return {
            "total_keys": len(self._cache),
            "active_keys": active_keys,
            "expired_keys": expired_keys,
            "cache_type": "in_memory"
        }

logger = logging.getLogger(__name__)

class CacheManager:
    """Cache manager for frequently accessed data"""
    
    def __init__(self):
        # Use in-memory cache for development
        # In production, replace with Redis client
        self.cache = InMemoryCache()
        
    async def initialize(self):
        """Initialize cache connection"""
        logger.info("Cache manager initialized (in-memory)")
        
    async def close(self):
        """Close cache connection"""
        await self.cache.clear()
        logger.info("Cache manager closed")
    
    def _generate_key(self, prefix: str, identifier: str) -> str:
        """Generate cache key"""
        return f"agno:{prefix}:{identifier}"
    
    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user from cache"""
        key = self._generate_key("user", user_id)
        return await self.cache.get(key)
    
    async def set_user(self, user_id: str, user_data: Dict[str, Any], ttl: int = 300) -> bool:
        """Cache user data"""
        key = self._generate_key("user", user_id)
        return await self.cache.set(key, user_data, ttl)
    
    async def get_organization(self, org_id: str) -> Optional[Dict[str, Any]]:
        """Get organization from cache"""
        key = self._generate_key("org", org_id)
        return await self.cache.get(key)
    
    async def set_organization(self, org_id: str, org_data: Dict[str, Any], ttl: int = 600) -> bool:
        """Cache organization data"""
        key = self._generate_key("org", org_id)
        return await self.cache.set(key, org_data, ttl)
    
    async def get_user_organizations(self, user_id: str) -> Optional[list]:
        """Get user's organizations from cache"""
        key = self._generate_key("user_orgs", user_id)
        return await self.cache.get(key)
    
    async def set_user_organizations(self, user_id: str, orgs: list, ttl: int = 300) -> bool:
        """Cache user's organizations"""
        key = self._generate_key("user_orgs", user_id)
        return await self.cache.set(key, orgs, ttl)
    
    async def get_organization_members(self, org_id: str) -> Optional[list]:
        """Get organization members from cache"""
        key = self._generate_key("org_members", org_id)
        return await self.cache.get(key)
    
    async def set_organization_members(self, org_id: str, members: list, ttl: int = 300) -> bool:
        """Cache organization members"""
        key = self._generate_key("org_members", org_id)
        return await self.cache.set(key, members, ttl)
    
    async def get_projects(self, org_id: str) -> Optional[list]:
        """Get organization projects from cache"""
        key = self._generate_key("projects", org_id)
        return await self.cache.get(key)
    
    async def set_projects(self, org_id: str, projects: list, ttl: int = 300) -> bool:
        """Cache organization projects"""
        key = self._generate_key("projects", org_id)
        return await self.cache.set(key, projects, ttl)
    
    async def get_boards(self, project_id: str) -> Optional[list]:
        """Get project boards from cache"""
        key = self._generate_key("boards", project_id)
        return await self.cache.get(key)
    
    async def set_boards(self, project_id: str, boards: list, ttl: int = 300) -> bool:
        """Cache project boards"""
        key = self._generate_key("boards", project_id)
        return await self.cache.set(key, boards, ttl)
    
    async def get_dashboard_stats(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get dashboard statistics from cache"""
        key = self._generate_key("dashboard", user_id)
        return await self.cache.get(key)
    
    async def set_dashboard_stats(self, user_id: str, stats: Dict[str, Any], ttl: int = 180) -> bool:
        """Cache dashboard statistics"""
        key = self._generate_key("dashboard", user_id)
        return await self.cache.set(key, stats, ttl)
    
    async def invalidate_user_cache(self, user_id: str):
        """Invalidate all cache entries for a user"""
        keys_to_delete = [
            self._generate_key("user", user_id),
            self._generate_key("user_orgs", user_id),
            self._generate_key("dashboard", user_id)
        ]
        
        for key in keys_to_delete:
            await self.cache.delete(key)
    
    async def invalidate_organization_cache(self, org_id: str):
        """Invalidate all cache entries for an organization"""
        keys_to_delete = [
            self._generate_key("org", org_id),
            self._generate_key("org_members", org_id),
            self._generate_key("projects", org_id)
        ]
        
        for key in keys_to_delete:
            await self.cache.delete(key)
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return self.cache.get_stats()

# Global cache manager instance
cache_manager = CacheManager()

async def init_cache():
    """Initialize cache manager"""
    await cache_manager.initialize()

async def close_cache():
    """Close cache manager"""
    await cache_manager.close()

# Decorator for caching function results
def cache_result(prefix: str, ttl: int = 300):
    """Decorator to cache function results"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            key_data = f"{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"
            cache_key = f"agno:{prefix}:{hashlib.md5(key_data.encode()).hexdigest()}"
            
            # Try to get from cache
            cached_result = await cache_manager.cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache_manager.cache.set(cache_key, result, ttl)
            return result
        
        return wrapper
    return decorator
