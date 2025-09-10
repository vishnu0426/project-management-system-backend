"""
Main FastAPI application for Agno WorkSphere
"""
import os
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.core.exceptions import APIException
from app.api.v1.router import api_router
from app.core.database import init_db
from app.core.logging import setup_logging, get_logger
from app.core.rate_limiting import rate_limit_middleware

# Configure structured logging
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting Agno WorkSphere API...")
    try:
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        logger.error("Server will continue but database operations may fail")
        logger.error("Please run: python setup_postgres.py to setup the database")

    yield

    # Shutdown
    logger.info("Shutting down Agno WorkSphere API...")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="A comprehensive project management platform with role-based access control",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan,
)

# Add HTTPS redirect middleware only in production
if settings.environment == "production":
    app.add_middleware(HTTPSRedirectMiddleware)

# Add CORS middleware with proper dev/prod configuration
app.add_middleware(
    CORSMiddleware,
    #allow_origins=settings.allowed_origins,  # From config: dev includes localhost:3002
    allow_origins=["*"],
    allow_credentials=True,  # Allow credentials for authentication
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],  # or explicit: ["Content-Type", "Authorization"]
)

# Add trusted host middleware
trusted_hosts = os.getenv("TRUSTED_HOSTS", "").split(",")
if trusted_hosts and trusted_hosts[0]:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=trusted_hosts)
else:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])  # Allow all in dev

# Add rate limiting middleware (after CORS)
app.middleware("http")(rate_limit_middleware)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time header to responses"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


@app.exception_handler(APIException)
async def api_exception_handler(request: Request, exc: APIException):
    """Handle custom API exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "details": exc.details
            },
            "timestamp": time.time()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    import traceback
    error_details = {
        "exception_type": type(exc).__name__,
        "exception_message": str(exc),
        "traceback": traceback.format_exc(),
        "request_path": str(request.url.path),
        "request_method": request.method
    }

    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    print(f"🚨 UNHANDLED EXCEPTION: {type(exc).__name__}: {str(exc)}")
    print(f"📍 Request: {request.method} {request.url.path}")
    print(f"📋 Traceback:\n{traceback.format_exc()}")

    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": "SYS_001",
                "message": "Internal server error",
                "details": error_details if settings.debug else None
            },
            "timestamp": time.time()
        }
    )


# Lifespan events are now handled by the lifespan context manager above


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "success": True,
        "data": {
            "message": "Welcome to Agno WorkSphere API",
            "version": settings.app_version,
            "environment": settings.environment
        },
        "timestamp": time.time()
    }


@app.get("/health")
async def health_check():
    """Health check endpoint with database status"""
    from app.core.database import get_db
    from sqlalchemy import text

    db_status = "unknown"
    db_error = None

    try:
        async for db in get_db():
            await db.execute(text("SELECT 1"))
            db_status = "healthy"
            break
    except Exception as e:
        db_status = "unhealthy"
        db_error = str(e)

    return {
        "success": True,
        "data": {
            "status": "healthy" if db_status == "healthy" else "degraded",
            "version": settings.app_version,
            "environment": settings.environment,
            "database": {
                "status": db_status,
                "error": db_error
            }
        },
        "timestamp": time.time()
    }


# Include API routes
app.include_router(api_router, prefix="/api")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=3001,
        reload=settings.debug,
        log_level="info"
    )
