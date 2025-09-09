"""
Authentication endpoints
"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from typing import Optional
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.sql import func
import pyotp
import qrcode
import io
import base64
import logging

from app.core.database import get_db
from app.services.session_service import SessionService
from app.core.security import (
    hash_password, verify_password, create_access_token, create_refresh_token,
    verify_token, generate_2fa_secret, verify_2fa_token,
    generate_email_verification_token, generate_password_reset_token
)
from app.core.exceptions import (
    AuthenticationError, ValidationError, DuplicateResourceError, ResourceNotFoundError
)
from app.models.user import User
from app.models.organization import Organization, OrganizationMember
from app.models.registration import Registration
from app.schemas.auth import (
    UserRegister, UserLogin, AuthResponse, TokenResponse, UserResponse, OrganizationInfo,
    RefreshTokenRequest, ForgotPasswordRequest, ResetPasswordRequest,
    VerifyEmailRequest, Enable2FAResponse, Verify2FARequest, ChangePasswordRequest
)
from app.core.deps import get_current_active_user
from app.config import settings
from app.services.email_service import email_service

router = APIRouter()
security = HTTPBearer(auto_error=False)
logger = logging.getLogger(__name__)


@router.post("/register", response_model=AuthResponse, status_code=201)
async def register(
    user_data: UserRegister,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Register a new user"""
    try:
        # Check if user already exists
        result = await db.execute(select(User).where(User.email == user_data.email))
        if result.scalar_one_or_none():
            raise DuplicateResourceError("User with this email already exists")

        # Create registration record first
        # Handle optional organization name with safe default
        default_org_name = f"{user_data.first_name}'s Organization" if user_data.first_name else "My Organization"
        org_name = user_data.organization_name if user_data.organization_name else default_org_name

        registration = Registration(
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            email=user_data.email,
            organization_name=org_name,
            organization_domain=user_data.organization_domain,
            requested_role='owner',
            assigned_role='owner',
            terms_accepted=True,
            privacy_policy_accepted=True,
            status='completed',
            registration_source='web'
        )

        db.add(registration)
        await db.commit()
        await db.refresh(registration)

        # Create new user
        hashed_password = hash_password(user_data.password)
        user = User(
            email=user_data.email,
            password_hash=hashed_password,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            email_verified=False  # Will be verified via email
        )

        db.add(user)
        await db.commit()
        await db.refresh(user)

        # Create default organization for the user using registration data
        organization = Organization(
            name=registration.organization_name,
            description=f"Default organization for {user.full_name}",
            domain=registration.organization_domain,
            created_by=user.id
        )

        db.add(organization)
        await db.commit()
        await db.refresh(organization)

        # Add user as owner of the organization
        org_member = OrganizationMember(
            organization_id=organization.id,
            user_id=user.id,
            role="owner",
            invited_by=user.id  # Self-invited as the creator
        )

        db.add(org_member)
        await db.commit()

        # Update registration record with created user and organization
        registration.user_id = user.id
        registration.organization_id = organization.id
        registration.processed_at = func.now()
        await db.commit()

        # Create database session instead of JWT tokens (consistent with login)
        session_service = SessionService(db)

        # Create session in database
        session = await session_service.create_session(
            user_id=user.id,
            ip_address=None,  # Could extract from request if needed
            user_agent=None,  # Could extract from request if needed
            session_duration_hours=24
        )

        # Send welcome email in background
        background_tasks.add_task(
            email_service.send_welcome_email,
            user.email,
            f"{user.first_name} {user.last_name}",
            organization.name,
            "http://localhost:3000/login"
        )

        return AuthResponse(
            user=UserResponse.model_validate(user),
            tokens=TokenResponse(
                access_token=session.session_token,  # Use session token as access token
                refresh_token=session.refresh_token,
                expires_in=24 * 60 * 60  # 24 hours in seconds
            ),
            organization=OrganizationInfo(
                id=organization.id,
                name=organization.name,
                role="owner"
            )
        )

    except Exception as e:
        # Rollback any database changes
        await db.rollback()
        logger.error(f"Registration failed for {user_data.email}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Registration failed: {str(e)}"
        )


@router.post("/login", response_model=AuthResponse)
async def login(
    user_data: UserLogin,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Login user with database session"""
    # Find user by email
    result = await db.execute(select(User).where(User.email == user_data.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(user_data.password, user.password_hash):
        raise AuthenticationError("Invalid email or password")

    # Get user's primary organization (first one they're a member of)
    org_member_result = await db.execute(
        select(OrganizationMember, Organization)
        .join(Organization, OrganizationMember.organization_id == Organization.id)
        .where(OrganizationMember.user_id == user.id)
        .order_by(OrganizationMember.joined_at.asc())
        .limit(1)
    )
    org_member_data = org_member_result.first()

    organization_info = None
    if org_member_data:
        org_member, organization = org_member_data
        organization_info = OrganizationInfo(
            id=organization.id,
            name=organization.name,
            role=org_member.role
        )

    # Update last login
    user.last_login_at = datetime.utcnow()
    await db.commit()

    # Create database session instead of JWT tokens
    session_service = SessionService(db)

    # Get client info
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    # Create session in database
    session = await session_service.create_session(
        user_id=user.id,
        ip_address=ip_address,
        user_agent=user_agent,
        session_duration_hours=24
    )

    return AuthResponse(
        user=UserResponse.model_validate(user),
        tokens=TokenResponse(
            access_token=session.session_token,  # Use session token as access token
            refresh_token=session.refresh_token,
            expires_in=24 * 60 * 60  # 24 hours in seconds
        ),
        organization=organization_info
    )


@router.post("/refresh-token", response_model=TokenResponse)
async def refresh_token(
    token_data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """Refresh access token"""
    try:
        payload = verify_token(token_data.refresh_token, token_type="refresh")
        user_id = payload.get("sub")
        
        # Verify user still exists
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise AuthenticationError("User not found")
        
        # Generate new tokens
        access_token = create_access_token({"sub": str(user.id)})
        new_refresh_token = create_refresh_token({"sub": str(user.id)})
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            expires_in=settings.jwt_expires_in * 60
        )
        
    except Exception as e:
        raise AuthenticationError("Invalid refresh token")


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_active_user)):
    """Return current authenticated user (auth alias for /users/me)."""
    # User is already loaded from the dependency, no additional DB queries needed
    return UserResponse.model_validate(current_user)


@router.post("/logout")
async def logout(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """Logout user by deactivating the current session token, if provided."""
    if credentials and credentials.credentials:
        session_service = SessionService(db)
        await session_service.logout_session(credentials.credentials)
    return {"success": True, "message": "Logged out successfully"}


@router.post("/forgot-password")
async def forgot_password(
    request_data: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Request password reset"""
    result = await db.execute(select(User).where(User.email == request_data.email))
    user = result.scalar_one_or_none()
    
    if user:
        reset_token = generate_password_reset_token()
        # TODO: Store reset token in database with expiration
        # TODO: Send reset email in background
        # background_tasks.add_task(send_password_reset_email, user.email, reset_token)
    
    # Always return success to prevent email enumeration
    return {"success": True, "message": "If the email exists, a reset link has been sent"}


@router.post("/reset-password")
async def reset_password(
    request_data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db)
):
    """Reset password with token"""
    # TODO: Verify reset token from database
    # For now, just return success
    return {"success": True, "message": "Password reset successfully"}


@router.post("/verify-email")
async def verify_email(
    request_data: VerifyEmailRequest,
    db: AsyncSession = Depends(get_db)
):
    """Verify email address"""
    # TODO: Verify email token from database
    # For now, just return success
    return {"success": True, "message": "Email verified successfully"}


@router.post("/enable-2fa", response_model=Enable2FAResponse)
async def enable_2fa(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Enable two-factor authentication"""
    if current_user.two_factor_enabled:
        raise ValidationError("Two-factor authentication is already enabled")

    # Generate secret
    secret = generate_2fa_secret()

    # Generate QR code
    totp = pyotp.TOTP(secret)
    qr_url = totp.provisioning_uri(
        name=current_user.email,
        issuer_name=settings.app_name
    )

    # Create QR code image
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(qr_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    img_buffer = io.BytesIO()
    img.save(img_buffer, format='PNG')
    img_str = base64.b64encode(img_buffer.getvalue()).decode()
    qr_code_url = f"data:image/png;base64,{img_str}"

    # Store secret (not enabled until verified)
    current_user.two_factor_secret = secret
    await db.commit()

    return Enable2FAResponse(
        secret=secret,
        qr_code_url=qr_code_url
    )


@router.post("/verify-2fa")
async def verify_2fa(
    request_data: Verify2FARequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Verify and enable 2FA"""
    if not current_user.two_factor_secret:
        raise ValidationError("Two-factor authentication setup not started")

    if not verify_2fa_token(current_user.two_factor_secret, request_data.token):
        raise ValidationError("Invalid 2FA token")

    # Enable 2FA
    current_user.two_factor_enabled = True
    await db.commit()

    return {"success": True, "message": "Two-factor authentication enabled successfully"}


@router.post("/change-password")
async def change_password(
    request_data: ChangePasswordRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Change user password"""
    if not verify_password(request_data.current_password, current_user.password_hash):
        raise AuthenticationError("Current password is incorrect")

    # Update password
    current_user.password_hash = hash_password(request_data.new_password)
    await db.commit()

    return {"success": True, "message": "Password changed successfully"}


@router.get("/registration-details")
async def get_registration_details(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user registration details from database"""
    # Get registration record for current user
    result = await db.execute(
        select(Registration).where(Registration.user_id == current_user.id)
    )
    registration = result.scalar_one_or_none()

    if not registration:
        raise HTTPException(status_code=404, detail="Registration details not found")

    # Get organization details
    org_result = await db.execute(
        select(OrganizationMember, Organization)
        .join(Organization, OrganizationMember.organization_id == Organization.id)
        .where(OrganizationMember.user_id == current_user.id)
    )
    org_member, organization = org_result.first() or (None, None)

    return {
        "success": True,
        "data": {
            "user": {
                "id": str(current_user.id),
                "email": current_user.email,
                "first_name": current_user.first_name,
                "last_name": current_user.last_name,
                "full_name": f"{current_user.first_name} {current_user.last_name}".strip(),
                "email_verified": current_user.email_verified,
                "role": org_member.role if org_member else "owner"
            },
            "organization": {
                "id": str(organization.id) if organization else None,
                "name": organization.name if organization else registration.organization_name,
                "domain": organization.domain if organization else registration.organization_domain,
                "role": org_member.role if org_member else "owner"
            },
            "registration": {
                "id": str(registration.id),
                "organization_name": registration.organization_name,
                "organization_domain": registration.organization_domain,
                "requested_role": registration.requested_role,
                "assigned_role": registration.assigned_role,
                "status": registration.status,
                "created_at": registration.created_at.isoformat(),
                "terms_accepted": registration.terms_accepted,
                "privacy_policy_accepted": registration.privacy_policy_accepted
            }
        }
    }
