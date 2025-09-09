"""
Structured logging configuration for production
"""
import json
import logging
import sys
from datetime import datetime
from typing import Any, Dict
from pythonjsonlogger import jsonlogger

from app.config import settings


class SecurityFilter(logging.Filter):
    """Filter to remove sensitive information from logs"""
    
    SENSITIVE_KEYS = {
        'password', 'token', 'secret', 'key', 'authorization', 
        'cookie', 'session', 'csrf', 'api_key', 'access_token',
        'refresh_token', 'jwt', 'bearer'
    }
    
    def filter(self, record):
        """Remove sensitive data from log records"""
        if hasattr(record, 'msg') and isinstance(record.msg, dict):
            record.msg = self._sanitize_dict(record.msg)
        
        if hasattr(record, 'args') and record.args:
            record.args = tuple(
                self._sanitize_dict(arg) if isinstance(arg, dict) else arg 
                for arg in record.args
            )
        
        return True
    
    def _sanitize_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively sanitize dictionary data"""
        if not isinstance(data, dict):
            return data
            
        sanitized = {}
        for key, value in data.items():
            key_lower = key.lower()
            if any(sensitive in key_lower for sensitive in self.SENSITIVE_KEYS):
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_dict(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    self._sanitize_dict(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                sanitized[key] = value
        return sanitized


class CustomJSONFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional fields"""
    
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        
        # Add standard fields
        log_record['timestamp'] = datetime.utcnow().isoformat()
        log_record['level'] = record.levelname
        log_record['logger'] = record.name
        log_record['service'] = settings.app_name
        log_record['version'] = settings.app_version
        log_record['environment'] = settings.environment
        
        # Add request context if available
        if hasattr(record, 'request_id'):
            log_record['request_id'] = record.request_id
        if hasattr(record, 'user_id'):
            log_record['user_id'] = record.user_id
        if hasattr(record, 'organization_id'):
            log_record['organization_id'] = record.organization_id


def setup_logging():
    """Configure structured logging for the application"""
    
    # Determine log level
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    # Configure formatter based on environment
    if settings.environment == "production" and settings.log_format == "json":
        # JSON formatter for production
        formatter = CustomJSONFormatter(
            fmt='%(timestamp)s %(level)s %(logger)s %(message)s'
        )
    else:
        # Human-readable formatter for development
        formatter = logging.Formatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    console_handler.setFormatter(formatter)
    
    # Add security filter to prevent sensitive data leakage
    security_filter = SecurityFilter()
    console_handler.addFilter(security_filter)
    
    # Add handler to root logger
    root_logger.addHandler(console_handler)
    
    # Configure specific loggers
    configure_third_party_loggers()
    
    # Log configuration
    logger = logging.getLogger(__name__)
    logger.info(
        "Logging configured",
        extra={
            "log_level": settings.log_level,
            "log_format": settings.log_format,
            "environment": settings.environment
        }
    )


def configure_third_party_loggers():
    """Configure third-party library loggers"""
    
    # SQLAlchemy - reduce verbosity in production
    sqlalchemy_level = logging.WARNING if settings.environment == "production" else logging.INFO
    logging.getLogger("sqlalchemy.engine").setLevel(sqlalchemy_level)
    logging.getLogger("sqlalchemy.pool").setLevel(sqlalchemy_level)
    
    # Uvicorn - structured logging
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    
    # FastAPI - reduce debug noise
    logging.getLogger("fastapi").setLevel(logging.INFO)
    
    # Alembic - only show important messages
    logging.getLogger("alembic").setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name"""
    return logging.getLogger(name)


class LoggerAdapter(logging.LoggerAdapter):
    """Logger adapter to add context to log messages"""
    
    def __init__(self, logger, extra=None):
        super().__init__(logger, extra or {})
    
    def process(self, msg, kwargs):
        """Add extra context to log messages"""
        if 'extra' not in kwargs:
            kwargs['extra'] = {}
        kwargs['extra'].update(self.extra)
        return msg, kwargs


def get_context_logger(name: str, **context) -> LoggerAdapter:
    """Get a logger with additional context"""
    logger = get_logger(name)
    return LoggerAdapter(logger, context)


# Request logging utilities
def log_request_start(logger: logging.Logger, method: str, path: str, **context):
    """Log request start"""
    logger.info(
        f"Request started: {method} {path}",
        extra={
            "event": "request_start",
            "method": method,
            "path": path,
            **context
        }
    )


def log_request_end(logger: logging.Logger, method: str, path: str, status_code: int, 
                   duration: float, **context):
    """Log request completion"""
    level = logging.WARNING if status_code >= 400 else logging.INFO
    logger.log(
        level,
        f"Request completed: {method} {path} - {status_code} ({duration:.3f}s)",
        extra={
            "event": "request_end",
            "method": method,
            "path": path,
            "status_code": status_code,
            "duration": duration,
            **context
        }
    )


def log_database_query(logger: logging.Logger, query: str, duration: float, **context):
    """Log database query performance"""
    level = logging.WARNING if duration > 1.0 else logging.DEBUG
    logger.log(
        level,
        f"Database query executed ({duration:.3f}s)",
        extra={
            "event": "database_query",
            "query": query[:200] + "..." if len(query) > 200 else query,
            "duration": duration,
            **context
        }
    )


def log_security_event(logger: logging.Logger, event: str, **context):
    """Log security-related events"""
    logger.warning(
        f"Security event: {event}",
        extra={
            "event": "security",
            "security_event": event,
            **context
        }
    )
