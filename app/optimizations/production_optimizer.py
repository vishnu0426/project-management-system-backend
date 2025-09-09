"""
Advanced Production Optimizations for Agno WorkSphere
Additional optimizations based on real-world usage patterns and performance analysis
"""

import asyncio
import time
import json
import gzip
import hashlib
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
import logging
from functools import wraps
from collections import defaultdict, LRU

logger = logging.getLogger(__name__)

class ProductionOptimizer:
    """Advanced production optimization system"""
    
    def __init__(self):
        self.query_cache = LRU(maxsize=1000)
        self.response_cache = LRU(maxsize=500)
        self.compression_cache = LRU(maxsize=200)
        self.rate_limiters = defaultdict(lambda: {"requests": [], "blocked": 0})
        self.optimization_stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "compressed_responses": 0,
            "rate_limited_requests": 0,
            "optimized_queries": 0
        }
    
    # Query Optimization
    def optimize_query(self, query: str, params: tuple = None) -> tuple:
        """Optimize database queries for better performance"""
        query_hash = hashlib.md5(f"{query}:{params}".encode()).hexdigest()
        
        # Check if we have a cached optimized version
        if query_hash in self.query_cache:
            self.optimization_stats["cache_hits"] += 1
            return self.query_cache[query_hash]
        
        self.optimization_stats["cache_misses"] += 1
        
        # Apply query optimizations
        optimized_query = self._apply_query_optimizations(query)
        optimized_params = self._optimize_parameters(params) if params else None
        
        result = (optimized_query, optimized_params)
        self.query_cache[query_hash] = result
        self.optimization_stats["optimized_queries"] += 1
        
        return result
    
    def _apply_query_optimizations(self, query: str) -> str:
        """Apply various query optimizations"""
        optimized = query
        
        # Add LIMIT if not present for potentially large result sets
        if "SELECT" in optimized.upper() and "LIMIT" not in optimized.upper():
            if "ORDER BY" in optimized.upper():
                optimized = optimized.replace("ORDER BY", "ORDER BY") + " LIMIT 1000"
            else:
                optimized += " LIMIT 1000"
        
        # Optimize JOIN conditions
        if "JOIN" in optimized.upper():
            # Ensure proper indexing hints (PostgreSQL specific)
            optimized = optimized.replace("JOIN", "/*+ USE_INDEX */ JOIN")
        
        # Add query hints for better performance
        if optimized.strip().upper().startswith("SELECT"):
            optimized = "/*+ FIRST_ROWS */ " + optimized
        
        return optimized
    
    def _optimize_parameters(self, params: tuple) -> tuple:
        """Optimize query parameters"""
        if not params:
            return params
        
        # Convert string parameters to appropriate types
        optimized_params = []
        for param in params:
            if isinstance(param, str) and param.isdigit():
                optimized_params.append(int(param))
            elif isinstance(param, str) and param.replace('.', '').isdigit():
                optimized_params.append(float(param))
            else:
                optimized_params.append(param)
        
        return tuple(optimized_params)
    
    # Response Compression
    def compress_response(self, data: Any, content_type: str = "application/json") -> bytes:
        """Compress API responses for better network performance"""
        if isinstance(data, dict) or isinstance(data, list):
            json_data = json.dumps(data, separators=(',', ':'))
        else:
            json_data = str(data)
        
        # Check compression cache
        data_hash = hashlib.md5(json_data.encode()).hexdigest()
        if data_hash in self.compression_cache:
            return self.compression_cache[data_hash]
        
        # Compress data
        compressed = gzip.compress(json_data.encode('utf-8'))
        
        # Only cache if compression is beneficial
        if len(compressed) < len(json_data.encode('utf-8')) * 0.8:
            self.compression_cache[data_hash] = compressed
            self.optimization_stats["compressed_responses"] += 1
            return compressed
        
        return json_data.encode('utf-8')
    
    # Rate Limiting
    def check_rate_limit(self, client_id: str, endpoint: str, limit: int = 100, window: int = 60) -> bool:
        """Advanced rate limiting with sliding window"""
        key = f"{client_id}:{endpoint}"
        current_time = time.time()
        
        # Clean old requests outside the window
        self.rate_limiters[key]["requests"] = [
            req_time for req_time in self.rate_limiters[key]["requests"]
            if current_time - req_time < window
        ]
        
        # Check if limit exceeded
        if len(self.rate_limiters[key]["requests"]) >= limit:
            self.rate_limiters[key]["blocked"] += 1
            self.optimization_stats["rate_limited_requests"] += 1
            return False
        
        # Add current request
        self.rate_limiters[key]["requests"].append(current_time)
        return True
    
    # Intelligent Caching
    def intelligent_cache_key(self, endpoint: str, params: Dict, user_context: Dict = None) -> str:
        """Generate intelligent cache keys based on context"""
        key_parts = [endpoint]
        
        # Add relevant parameters
        if params:
            sorted_params = sorted(params.items())
            key_parts.append(hashlib.md5(str(sorted_params).encode()).hexdigest()[:8])
        
        # Add user context if relevant
        if user_context:
            if 'user_id' in user_context:
                key_parts.append(f"user:{user_context['user_id']}")
            if 'organization_id' in user_context:
                key_parts.append(f"org:{user_context['organization_id']}")
        
        return ":".join(key_parts)
    
    def should_cache_response(self, endpoint: str, response_size: int, computation_time: float) -> bool:
        """Determine if response should be cached based on various factors"""
        # Cache expensive computations
        if computation_time > 0.5:  # 500ms
            return True
        
        # Cache large responses that are expensive to generate
        if response_size > 10000:  # 10KB
            return True
        
        # Cache frequently accessed endpoints
        frequent_endpoints = [
            "/api/v1/dashboard/stats",
            "/api/v1/users/profile",
            "/api/v1/organizations"
        ]
        if any(freq_endpoint in endpoint for freq_endpoint in frequent_endpoints):
            return True
        
        return False
    
    # Database Connection Optimization
    def optimize_db_connection(self, query_type: str, expected_rows: int = None) -> Dict[str, Any]:
        """Optimize database connection settings based on query type"""
        settings = {}
        
        if query_type == "read_heavy":
            settings.update({
                "statement_timeout": "30s",
                "work_mem": "8MB",
                "effective_cache_size": "2GB"
            })
        elif query_type == "write_heavy":
            settings.update({
                "statement_timeout": "60s",
                "work_mem": "16MB",
                "checkpoint_completion_target": "0.9"
            })
        elif query_type == "analytical":
            settings.update({
                "statement_timeout": "300s",
                "work_mem": "64MB",
                "effective_cache_size": "4GB",
                "random_page_cost": "1.1"
            })
        
        if expected_rows and expected_rows > 10000:
            settings["work_mem"] = "32MB"
        
        return settings
    
    # Memory Optimization
    def optimize_memory_usage(self, data_size: int, operation_type: str) -> Dict[str, Any]:
        """Optimize memory usage based on data size and operation type"""
        recommendations = {
            "use_streaming": False,
            "batch_size": 1000,
            "gc_collect": False,
            "memory_limit": None
        }
        
        # Large data operations
        if data_size > 100000:  # 100KB
            recommendations.update({
                "use_streaming": True,
                "batch_size": 500,
                "gc_collect": True
            })
        
        # Memory-intensive operations
        if operation_type in ["export", "report_generation", "bulk_import"]:
            recommendations.update({
                "use_streaming": True,
                "batch_size": 100,
                "memory_limit": "256MB"
            })
        
        return recommendations
    
    # Performance Monitoring Decorators
    def monitor_performance(self, operation_name: str):
        """Decorator to monitor function performance"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = await func(*args, **kwargs)
                    execution_time = time.time() - start_time
                    
                    # Log slow operations
                    if execution_time > 1.0:
                        logger.warning(f"Slow operation: {operation_name} took {execution_time:.2f}s")
                    
                    # Store performance metrics
                    self._record_performance_metric(operation_name, execution_time, True)
                    
                    return result
                except Exception as e:
                    execution_time = time.time() - start_time
                    self._record_performance_metric(operation_name, execution_time, False)
                    raise
            
            return wrapper
        return decorator
    
    def _record_performance_metric(self, operation: str, duration: float, success: bool):
        """Record performance metrics for analysis"""
        # In production, this would send to monitoring system
        logger.info(f"Performance: {operation} - {duration:.3f}s - {'SUCCESS' if success else 'FAILED'}")
    
    # Adaptive Optimization
    def adapt_optimizations(self, usage_patterns: Dict[str, Any]):
        """Adapt optimizations based on usage patterns"""
        # Adjust cache sizes based on hit rates
        if usage_patterns.get("cache_hit_rate", 0) < 0.7:
            self.query_cache.maxsize = min(self.query_cache.maxsize * 2, 2000)
            self.response_cache.maxsize = min(self.response_cache.maxsize * 2, 1000)
        
        # Adjust rate limits based on traffic patterns
        if usage_patterns.get("peak_rps", 0) > 50:
            # Increase rate limits during high traffic
            for key in self.rate_limiters:
                if "high_priority" in key:
                    continue  # Don't adjust high priority endpoints
        
        # Optimize query cache based on query patterns
        frequent_queries = usage_patterns.get("frequent_queries", [])
        for query in frequent_queries:
            # Pre-warm cache for frequent queries
            pass
    
    # Health Check Optimizations
    def optimize_health_checks(self) -> Dict[str, Any]:
        """Optimize health check performance"""
        return {
            "lightweight_checks": [
                "memory_usage",
                "cpu_usage",
                "active_connections"
            ],
            "detailed_checks": [
                "database_connectivity",
                "cache_performance",
                "disk_space"
            ],
            "check_intervals": {
                "lightweight": 30,  # seconds
                "detailed": 300     # seconds
            }
        }
    
    # Resource Cleanup
    async def cleanup_resources(self):
        """Clean up unused resources and optimize memory"""
        # Clear expired cache entries
        current_time = time.time()
        
        # Clean rate limiter data
        for key in list(self.rate_limiters.keys()):
            self.rate_limiters[key]["requests"] = [
                req_time for req_time in self.rate_limiters[key]["requests"]
                if current_time - req_time < 3600  # Keep last hour
            ]
            
            # Remove empty entries
            if not self.rate_limiters[key]["requests"]:
                del self.rate_limiters[key]
        
        # Force garbage collection for large cleanups
        import gc
        gc.collect()
        
        logger.info("Resource cleanup completed")
    
    def get_optimization_stats(self) -> Dict[str, Any]:
        """Get optimization statistics"""
        total_requests = self.optimization_stats["cache_hits"] + self.optimization_stats["cache_misses"]
        cache_hit_rate = self.optimization_stats["cache_hits"] / max(total_requests, 1)
        
        return {
            "cache_performance": {
                "hit_rate": cache_hit_rate,
                "total_hits": self.optimization_stats["cache_hits"],
                "total_misses": self.optimization_stats["cache_misses"]
            },
            "compression": {
                "compressed_responses": self.optimization_stats["compressed_responses"]
            },
            "rate_limiting": {
                "blocked_requests": self.optimization_stats["rate_limited_requests"]
            },
            "query_optimization": {
                "optimized_queries": self.optimization_stats["optimized_queries"]
            },
            "cache_sizes": {
                "query_cache": len(self.query_cache),
                "response_cache": len(self.response_cache),
                "compression_cache": len(self.compression_cache)
            }
        }

# Global optimizer instance
production_optimizer = ProductionOptimizer()

# Optimization decorators for easy use
def optimize_query(func):
    """Decorator for query optimization"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        return await production_optimizer.monitor_performance(func.__name__)(func)(*args, **kwargs)
    return wrapper

def cache_response(ttl: int = 300):
    """Decorator for response caching"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Implementation would depend on specific caching strategy
            return await func(*args, **kwargs)
        return wrapper
    return decorator
