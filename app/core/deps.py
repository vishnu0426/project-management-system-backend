"""
Dependency injection utilities
"""
from typing import Optional, Generator
from fastapi import Depends, HTTPException, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import verify_token
from app.core.exceptions import AuthenticationError, InsufficientPermissionsError
from app.models.user import User
from app.models.organization import OrganizationMember
from app.services.session_service import SessionService
from app.config import settings


security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    x_mock_user_id: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Get current authenticated user using database sessions
    For development, supports mock user ID header
    """
    # Development mode: use mock user ID if provided
    if x_mock_user_id:
        result = await db.execute(select(User).where(User.id == x_mock_user_id))
        user = result.scalar_one_or_none()
        if user:
            return user
        # If mock user doesn't exist, create one
        mock_user = User(
            id=x_mock_user_id,
            email="demo@example.com",
            password_hash="mock_hash",
            first_name="Demo",
            last_name="User",
            email_verified=True
        )
        db.add(mock_user)
        await db.commit()
        await db.refresh(mock_user)
        return mock_user
    
    # Production mode: require valid session token
    if not credentials:
        raise AuthenticationError("Authentication required")

    try:
        # Use session service to validate session token
        session_service = SessionService(db)
        session = await session_service.validate_session(credentials.credentials)

        if not session or not session.user:
            raise AuthenticationError("Invalid or expired session")

        return session.user

    except Exception as e:
        raise AuthenticationError(str(e))


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current active user"""
    # In development mode, skip email verification requirement
    if settings.environment == "development" or settings.debug:
        return current_user

    if not current_user.email_verified:
        raise AuthenticationError("Email not verified")
    return current_user


async def get_organization_member(
    organization_id: str = Header(None, alias="X-Organization-ID"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Optional[OrganizationMember]:
    """Get organization member for current user"""
    if not organization_id:
        return None

    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == current_user.id
        )
    )
    return result.scalar_one_or_none()


async def get_organization_member_by_path(
    organization_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Optional[OrganizationMember]:
    """Get organization member for current user using path parameter"""
    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == current_user.id
        )
    )
    return result.scalar_one_or_none()


def require_organization_role(required_roles: list[str]):
    """Dependency factory to require specific organization roles"""
    async def check_role(
        org_member: Optional[OrganizationMember] = Depends(get_organization_member)
    ):
        if not org_member:
            raise InsufficientPermissionsError("Organization membership required")

        if org_member.role not in required_roles:
            raise InsufficientPermissionsError(
                f"Required role: {' or '.join(required_roles)}, current role: {org_member.role}"
            )

        return org_member

    return check_role


def require_organization_role_by_path(required_roles: list[str]):
    """Dependency factory to require specific organization roles using path parameter"""
    async def check_role(
        organization_id: str,
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db)
    ):
        org_member = await get_organization_member_by_path(organization_id, current_user, db)
        if not org_member:
            raise InsufficientPermissionsError("Organization membership required")

        if org_member.role not in required_roles:
            raise InsufficientPermissionsError(
                f"Required role: {' or '.join(required_roles)}, current role: {org_member.role}"
            )

        return org_member

    return check_role


# Common role dependencies
require_admin = require_organization_role(["admin", "owner"])
require_member = require_organization_role(["member", "admin", "owner"])
require_viewer = require_organization_role(["viewer", "member", "admin", "owner"])

# Path-based role dependencies
require_admin_by_path = require_organization_role_by_path(["admin", "owner"])
require_member_by_path = require_organization_role_by_path(["member", "admin", "owner"])
require_viewer_by_path = require_organization_role_by_path(["viewer", "member", "admin", "owner"])
