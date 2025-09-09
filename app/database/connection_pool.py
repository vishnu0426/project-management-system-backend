"""
Database Connection Pool for Agno WorkSphere
Implements asyncpg connection pooling for high-concurrency scenarios
"""

import asyncio
import asyncpg
import os
from typing import Optional
import logging
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

class DatabasePool:
    """Database connection pool manager"""
    
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        self.database_url = os.getenv(
            "DATABASE_URL", 
            "postgresql://postgres:admin@localhost:5432/agno_worksphere"
        )
        
    async def initialize(self):
        """Initialize the connection pool"""
        try:
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=5,          # Minimum connections in pool
                max_size=20,         # Maximum connections in pool
                max_queries=50000,   # Max queries per connection
                max_inactive_connection_lifetime=300,  # 5 minutes
                timeout=30,          # Connection timeout
                command_timeout=60,  # Command timeout
                server_settings={
                    'jit': 'off',    # Disable JIT for faster startup
                    'application_name': 'agno_worksphere'
                }
            )
            logger.info(f"Database pool initialized with {self.pool.get_size()} connections")
            
        except Exception as e:
            logger.error(f"Failed to initialize database pool: {e}")
            raise
    
    async def close(self):
        """Close the connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("Database pool closed")
    
    @asynccontextmanager
    async def get_connection(self):
        """Get a connection from the pool"""
        if not self.pool:
            raise RuntimeError("Database pool not initialized")
        
        async with self.pool.acquire() as connection:
            yield connection
    
    async def execute(self, query: str, *args):
        """Execute a query using pool connection"""
        async with self.get_connection() as conn:
            return await conn.execute(query, *args)
    
    async def fetch(self, query: str, *args):
        """Fetch multiple rows using pool connection"""
        async with self.get_connection() as conn:
            return await conn.fetch(query, *args)
    
    async def fetchrow(self, query: str, *args):
        """Fetch single row using pool connection"""
        async with self.get_connection() as conn:
            return await conn.fetchrow(query, *args)
    
    async def fetchval(self, query: str, *args):
        """Fetch single value using pool connection"""
        async with self.get_connection() as conn:
            return await conn.fetchval(query, *args)
    
    async def transaction(self):
        """Get a transaction context"""
        if not self.pool:
            raise RuntimeError("Database pool not initialized")
        
        return self.pool.acquire()
    
    def get_pool_stats(self):
        """Get connection pool statistics"""
        if not self.pool:
            return {"status": "not_initialized"}
        
        return {
            "size": self.pool.get_size(),
            "min_size": self.pool.get_min_size(),
            "max_size": self.pool.get_max_size(),
            "idle_size": self.pool.get_idle_size(),
            "status": "active"
        }

# Global database pool instance
db_pool = DatabasePool()

async def init_database():
    """Initialize database connection pool"""
    await db_pool.initialize()

async def close_database():
    """Close database connection pool"""
    await db_pool.close()

# Convenience functions for database operations
async def execute_query(query: str, *args):
    """Execute a query"""
    return await db_pool.execute(query, *args)

async def fetch_all(query: str, *args):
    """Fetch all rows"""
    return await db_pool.fetch(query, *args)

async def fetch_one(query: str, *args):
    """Fetch one row"""
    return await db_pool.fetchrow(query, *args)

async def fetch_value(query: str, *args):
    """Fetch single value"""
    return await db_pool.fetchval(query, *args)

@asynccontextmanager
async def get_db_connection():
    """Get database connection context manager"""
    async with db_pool.get_connection() as conn:
        yield conn

@asynccontextmanager
async def get_db_transaction():
    """Get database transaction context manager"""
    async with db_pool.transaction() as conn:
        async with conn.transaction():
            yield conn
