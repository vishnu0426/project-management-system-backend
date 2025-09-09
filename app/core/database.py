"""
Database configuration and session management
"""
import asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import MetaData, text

from app.config import settings


# Database engine with minimal, safe configuration
engine = create_async_engine(
    settings.database_url,
    echo=False,  # Disable SQL logging for performance
    pool_pre_ping=True,
    pool_recycle=3600,  # 1 hour
    pool_size=5,  # Conservative pool size
    max_overflow=10,  # Conservative overflow
    pool_timeout=30,
    # Minimal connect_args to avoid PostgreSQL parameter issues
    connect_args={}
)

# Session factory
async_session_factory = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Base class for models
Base = declarative_base(
    metadata=MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s"
        }
    )
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get database session
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """
    Initialize database tables with robust error handling
    """
    try:
        # Import all models to ensure they are registered with SQLAlchemy
        from app.models import user, organization, project, board, column, card, comment, attachment, activity_log

        print("🔄 Initializing database...")

        # Test connection first
        async with engine.begin() as conn:
            # Test basic connectivity
            await conn.execute(text("SELECT 1"))
            print("✅ Database connection successful")

            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
            print("✅ Database tables initialized")

    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        print("🔧 Troubleshooting tips:")
        print("   1. Ensure PostgreSQL is running")
        print("   2. Check database credentials in config")
        print("   3. Verify database exists")
        print("   4. Check network connectivity")
        raise


async def close_db():
    """
    Close database connections
    """
    await engine.dispose()
