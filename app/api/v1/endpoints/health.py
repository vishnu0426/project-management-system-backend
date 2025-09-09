"""
Health and readiness endpoints for production monitoring
"""
import time
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from pydantic import BaseModel

from app.core.database import get_db
from app.config import settings

router = APIRouter()

class HealthResponse(BaseModel):
    """Health check response model"""
    status: str
    version: str
    environment: str
    uptime: float
    timestamp: str

class ReadinessResponse(BaseModel):
    """Readiness check response model"""
    status: str
    version: str
    environment: str
    database: dict
    timestamp: str

# Track app start time for uptime calculation
app_start_time = time.time()

@router.get("/healthz", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint - returns app version and uptime
    Used by load balancers and monitoring systems
    """
    uptime = time.time() - app_start_time
    
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        environment=settings.environment,
        uptime=uptime,
        timestamp=datetime.utcnow().isoformat()
    )

@router.get("/readyz", response_model=ReadinessResponse)
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """
    Readiness check endpoint - pings database and returns 200 only if successful
    Used by Kubernetes and orchestration systems
    """
    db_status = "unknown"
    db_error = None
    db_response_time = None
    
    try:
        start_time = time.time()
        await db.execute(text("SELECT 1"))
        db_response_time = time.time() - start_time
        db_status = "healthy"
    except Exception as e:
        db_status = "unhealthy"
        db_error = str(e)
        # Return 503 Service Unavailable if database is down
        raise HTTPException(
            status_code=503,
            detail={
                "status": "not_ready",
                "version": settings.app_version,
                "environment": settings.environment,
                "database": {
                    "status": db_status,
                    "error": db_error,
                    "response_time": db_response_time
                },
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    return ReadinessResponse(
        status="ready",
        version=settings.app_version,
        environment=settings.environment,
        database={
            "status": db_status,
            "response_time": db_response_time,
            "error": db_error
        },
        timestamp=datetime.utcnow().isoformat()
    )
