"""
Custom exceptions for the Agno WorkSphere API
"""
from typing import Optional, Dict, Any


class APIException(Exception):
    """Base API exception class"""
    
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: str = "SYS_001",
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details
        super().__init__(self.message)


class AuthenticationError(APIException):
    """Authentication related errors"""
    
    def __init__(self, message: str = "Authentication failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=401,
            error_code="AUTH_001",
            details=details
        )


class TokenExpiredError(APIException):
    """Token expired error"""
    
    def __init__(self, message: str = "Token has expired", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=401,
            error_code="AUTH_002",
            details=details
        )


class InsufficientPermissionsError(APIException):
    """Insufficient permissions error"""
    
    def __init__(self, message: str = "Insufficient permissions", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=403,
            error_code="AUTH_003",
            details=details
        )


class ValidationError(APIException):
    """Validation error"""
    
    def __init__(self, message: str = "Validation failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=400,
            error_code="VAL_001",
            details=details
        )


class RequiredFieldError(APIException):
    """Required field missing error"""
    
    def __init__(self, field: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Required field '{field}' is missing",
            status_code=400,
            error_code="VAL_002",
            details=details
        )


class InvalidFormatError(APIException):
    """Invalid format error"""
    
    def __init__(self, message: str = "Invalid format", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=400,
            error_code="VAL_003",
            details=details
        )


class ResourceNotFoundError(APIException):
    """Resource not found error"""
    
    def __init__(self, resource: str = "Resource", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"{resource} not found",
            status_code=404,
            error_code="BIZ_001",
            details=details
        )


class DuplicateResourceError(APIException):
    """Duplicate resource error"""
    
    def __init__(self, resource: str = "Resource", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"{resource} already exists",
            status_code=409,
            error_code="BIZ_002",
            details=details
        )


class OperationNotAllowedError(APIException):
    """Operation not allowed error"""
    
    def __init__(self, message: str = "Operation not allowed", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=403,
            error_code="BIZ_003",
            details=details
        )


class RateLimitExceededError(APIException):
    """Rate limit exceeded error"""
    
    def __init__(self, message: str = "Rate limit exceeded", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=429,
            error_code="SYS_003",
            details=details
        )
