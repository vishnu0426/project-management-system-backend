"""
Authentication schemas
"""
from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List
from datetime import datetime
from uuid import UUID

from app.config import settings
from app.core.security import validate_password_strength


class UserRegister(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    organization_name: Optional[str] = None
    organization_domain: Optional[str] = None
    
    @validator('password')
    def validate_password(cls, v):
        if not validate_password_strength(v):
            raise ValueError(
                f'Password must be at least {settings.password_min_length} characters long '
                'and contain uppercase, lowercase, digit, and special character'
            )
        return v
    
    @validator('first_name', 'last_name')
    def validate_names(cls, v):
        if not v.strip():
            raise ValueError('Name cannot be empty')
        if len(v.strip()) < 2:
            raise ValueError('Name must be at least 2 characters long')
        return v.strip()


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    id: UUID
    email: str
    first_name: str
    last_name: str
    avatar_url: Optional[str] = None
    email_verified: bool
    two_factor_enabled: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class OrganizationInfo(BaseModel):
    id: UUID
    name: str
    role: str

    class Config:
        from_attributes = True


class AuthResponse(BaseModel):
    user: UserResponse
    tokens: TokenResponse
    organization: Optional[OrganizationInfo] = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str
    
    @validator('new_password')
    def validate_password(cls, v):
        if not validate_password_strength(v):
            raise ValueError(
                f'Password must be at least {settings.password_min_length} characters long '
                'and contain uppercase, lowercase, digit, and special character'
            )
        return v


class VerifyEmailRequest(BaseModel):
    token: str


class Enable2FAResponse(BaseModel):
    secret: str
    qr_code_url: str


class Verify2FARequest(BaseModel):
    token: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
    
    @validator('new_password')
    def validate_password(cls, v):
        if not validate_password_strength(v):
            raise ValueError(
                f'Password must be at least {settings.password_min_length} characters long '
                'and contain uppercase, lowercase, digit, and special character'
            )
        return v
