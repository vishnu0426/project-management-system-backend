#!/usr/bin/env python3
"""
Enhanced Database Connection Pool Manager
Provides optimized database operations with connection pooling, query optimization, and monitoring
"""
import asyncio
import time
from contextlib import asynccontextmanager
from typing import Dict, List, Optional, Any, Union
import asyncpg
import structlog
from app.config import settings

logger = structlog.get_logger()

class DatabasePool:
    """Enhanced database connection pool with monitoring and optimization"""
    
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        self.stats = {
            "connections_created": 0,
            "connections_closed": 0,
            "queries_executed": 0,
            "total_query_time": 0.0,
            "slow_queries": 0,
            "errors": 0
        }
        self.slow_query_threshold = 1.0  # seconds
    
    async def initialize(self) -> None:
        """Initialize the database connection pool with optimized settings"""
        try:
            # Connection pool configuration
            pool_config = {
                "dsn": settings.database_url,
                "min_size": settings.db_pool_min_size,
                "max_size": settings.db_pool_max_size,
                "max_queries": settings.db_pool_max_queries,
                "max_inactive_connection_lifetime": settings.db_pool_max_inactive_time,
                "command_timeout": 60,
                "server_settings": {
                    "application_name": "agno_worksphere_api",
                    "tcp_keepalives_idle": "600",
                    "tcp_keepalives_interval": "30",
                    "tcp_keepalives_count": "3",
                }
            }
            
            self.pool = await asyncpg.create_pool(**pool_config)
            
            # Test the pool
            async with self.pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            
            logger.info(
                "Database pool initialized successfully",
                min_size=settings.db_pool_min_size,
                max_size=settings.db_pool_max_size,
                max_queries=settings.db_pool_max_queries
            )
            
        except Exception as e:
            logger.error("Failed to initialize database pool", error=str(e))
            raise
    
    async def close(self) -> None:
        """Close the database connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("Database pool closed", stats=self.stats)
    
    @asynccontextmanager
    async def acquire(self):
        """Acquire a database connection with monitoring"""
        if not self.pool:
            raise RuntimeError("Database pool not initialized")
        
        start_time = time.time()
        try:
            async with self.pool.acquire() as connection:
                self.stats["connections_created"] += 1
                yield connection
        except Exception as e:
            self.stats["errors"] += 1
            logger.error("Database connection error", error=str(e))
            raise
        finally:
            self.stats["connections_closed"] += 1
            connection_time = time.time() - start_time
            if connection_time > 5.0:  # Log slow connection acquisitions
                logger.warning("Slow connection acquisition", duration=f"{connection_time:.3f}s")
    
    async def execute_query(self, query: str, *args, fetch_type: str = "fetchval") -> Any:
        """Execute a query with monitoring and optimization"""
        start_time = time.time()
        
        try:
            async with self.acquire() as conn:
                if fetch_type == "fetchval":
                    result = await conn.fetchval(query, *args)
                elif fetch_type == "fetchrow":
                    result = await conn.fetchrow(query, *args)
                elif fetch_type == "fetch":
                    result = await conn.fetch(query, *args)
                elif fetch_type == "execute":
                    result = await conn.execute(query, *args)
                else:
                    raise ValueError(f"Invalid fetch_type: {fetch_type}")
                
                query_time = time.time() - start_time
                self.stats["queries_executed"] += 1
                self.stats["total_query_time"] += query_time
                
                if query_time > self.slow_query_threshold:
                    self.stats["slow_queries"] += 1
                    logger.warning(
                        "Slow query detected",
                        query=query[:100] + "..." if len(query) > 100 else query,
                        duration=f"{query_time:.3f}s",
                        args=args[:5] if len(args) > 5 else args
                    )
                
                return result
                
        except Exception as e:
            self.stats["errors"] += 1
            logger.error(
                "Query execution failed",
                query=query[:100] + "..." if len(query) > 100 else query,
                error=str(e),
                args=args[:5] if len(args) > 5 else args
            )
            raise
    
    async def execute_transaction(self, queries: List[Dict[str, Any]]) -> List[Any]:
        """Execute multiple queries in a transaction"""
        start_time = time.time()
        results = []
        
        try:
            async with self.acquire() as conn:
                async with conn.transaction():
                    for query_info in queries:
                        query = query_info["query"]
                        args = query_info.get("args", [])
                        fetch_type = query_info.get("fetch_type", "execute")
                        
                        if fetch_type == "fetchval":
                            result = await conn.fetchval(query, *args)
                        elif fetch_type == "fetchrow":
                            result = await conn.fetchrow(query, *args)
                        elif fetch_type == "fetch":
                            result = await conn.fetch(query, *args)
                        else:
                            result = await conn.execute(query, *args)
                        
                        results.append(result)
                
                transaction_time = time.time() - start_time
                self.stats["queries_executed"] += len(queries)
                self.stats["total_query_time"] += transaction_time
                
                logger.info(
                    "Transaction completed",
                    query_count=len(queries),
                    duration=f"{transaction_time:.3f}s"
                )
                
                return results
                
        except Exception as e:
            self.stats["errors"] += 1
            logger.error(
                "Transaction failed",
                query_count=len(queries),
                error=str(e)
            )
            raise
    
    async def get_pool_stats(self) -> Dict[str, Any]:
        """Get detailed pool statistics"""
        if not self.pool:
            return {"status": "not_initialized"}
        
        pool_stats = {
            "size": self.pool.get_size(),
            "min_size": self.pool.get_min_size(),
            "max_size": self.pool.get_max_size(),
            "idle_size": self.pool.get_idle_size(),
            "queries_executed": self.stats["queries_executed"],
            "total_query_time": self.stats["total_query_time"],
            "avg_query_time": (
                self.stats["total_query_time"] / self.stats["queries_executed"]
                if self.stats["queries_executed"] > 0 else 0
            ),
            "slow_queries": self.stats["slow_queries"],
            "errors": self.stats["errors"],
            "connections_created": self.stats["connections_created"],
            "connections_closed": self.stats["connections_closed"]
        }
        
        return pool_stats
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform a comprehensive health check"""
        if not self.pool:
            return {"status": "unhealthy", "reason": "pool_not_initialized"}
        
        try:
            start_time = time.time()
            
            # Test basic connectivity
            async with self.acquire() as conn:
                await conn.fetchval("SELECT 1")
                
                # Test database responsiveness
                await conn.fetchval("SELECT COUNT(*) FROM users")
                
                # Check for long-running queries
                long_queries = await conn.fetch("""
                    SELECT query, state, query_start, now() - query_start as duration
                    FROM pg_stat_activity 
                    WHERE state = 'active' 
                    AND now() - query_start > interval '30 seconds'
                    AND query NOT LIKE '%pg_stat_activity%'
                """)
            
            health_time = time.time() - start_time
            
            return {
                "status": "healthy",
                "response_time": f"{health_time:.3f}s",
                "pool_stats": await self.get_pool_stats(),
                "long_running_queries": len(long_queries),
                "warnings": [
                    f"Long running query detected: {query['query'][:50]}..."
                    for query in long_queries
                ]
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "reason": str(e),
                "pool_stats": await self.get_pool_stats()
            }

# Global database pool instance
db_pool = DatabasePool()

# Convenience functions for common operations
async def get_user_by_email(email: str) -> Optional[asyncpg.Record]:
    """Get user by email with optimized query"""
    return await db_pool.execute_query(
        "SELECT id, email, first_name, last_name, email_verified FROM users WHERE email = $1",
        email,
        fetch_type="fetchrow"
    )

async def get_organizations() -> List[asyncpg.Record]:
    """Get all organizations with optimized query"""
    return await db_pool.execute_query(
        "SELECT id, name, description, created_at FROM organizations ORDER BY created_at DESC",
        fetch_type="fetch"
    )

async def get_projects_by_organization(org_id: str) -> List[asyncpg.Record]:
    """Get projects by organization with optimized query"""
    return await db_pool.execute_query(
        """
        SELECT p.id, p.name, p.description, p.status, p.priority, p.created_at,
               COUNT(c.id) as task_count
        FROM projects p
        LEFT JOIN boards b ON p.id = b.project_id
        LEFT JOIN columns col ON b.id = col.board_id
        LEFT JOIN cards c ON col.id = c.column_id
        WHERE p.organization_id = $1
        GROUP BY p.id, p.name, p.description, p.status, p.priority, p.created_at
        ORDER BY p.created_at DESC
        """,
        org_id,
        fetch_type="fetch"
    )

async def create_user_with_organization(user_data: Dict[str, Any]) -> str:
    """Create user and organization in a transaction"""
    import uuid
    
    user_id = str(uuid.uuid4())
    org_id = str(uuid.uuid4())
    
    queries = [
        {
            "query": """
                INSERT INTO users (id, email, password_hash, first_name, last_name, 
                                 email_verified, two_factor_enabled, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, NOW(), NOW())
                RETURNING id
            """,
            "args": [
                user_id, user_data["email"], user_data["password_hash"],
                user_data["first_name"], user_data["last_name"], False, False
            ],
            "fetch_type": "fetchval"
        }
    ]
    
    if user_data.get("organization_name"):
        queries.extend([
            {
                "query": """
                    INSERT INTO organizations (id, name, description, created_by, 
                                             organization_type, language, timezone, 
                                             allow_cross_org_collaboration, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW(), NOW())
                    RETURNING id
                """,
                "args": [
                    org_id, user_data["organization_name"], 
                    f"Organization created by {user_data['first_name']} {user_data['last_name']}",
                    user_id, "business", "en", "UTC", True
                ],
                "fetch_type": "fetchval"
            },
            {
                "query": """
                    INSERT INTO organization_members (organization_id, user_id, role, created_at, updated_at)
                    VALUES ($1, $2, $3, NOW(), NOW())
                """,
                "args": [org_id, user_id, "owner"]
            }
        ])
    
    results = await db_pool.execute_transaction(queries)
    return results[0]  # Return user_id
