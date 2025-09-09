"""
Session service for database-based authentication
"""
import uuid
from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload

from app.models.session import UserSession
from app.models.user import User
from app.core.exceptions import AuthenticationError
from app.core.cache import cache


class SessionService:
    """Service for managing user sessions in database"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_session(
        self, 
        user_id: uuid.UUID, 
        ip_address: str = None, 
        user_agent: str = None,
        session_duration_hours: int = 24
    ) -> UserSession:
        """Create a new user session"""
        
        # Clean up expired sessions for this user first
        await self.cleanup_expired_sessions(user_id)
        
        # Create new session
        session = UserSession.create_session(
            user_id=user_id,
            session_duration_hours=session_duration_hours,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        
        return session
    
    async def get_session_by_token(self, session_token: str) -> Optional[UserSession]:
        """Get session by session token (cached)"""
        # Try cache first
        cache_key = f"session:{session_token}"
        cached_session = cache.get(cache_key)
        if cached_session:
            return cached_session

        # Query database
        result = await self.db.execute(
            select(UserSession)
            .options(selectinload(UserSession.user))
            .where(
                and_(
                    UserSession.session_token == session_token,
                    UserSession.is_active == True
                )
            )
        )
        session = result.scalar_one_or_none()

        # Cache valid sessions for 5 minutes
        if session and session.is_valid():
            cache.set(cache_key, session, ttl=300)

        return session
    
    async def get_session_by_refresh_token(self, refresh_token: str) -> Optional[UserSession]:
        """Get session by refresh token"""
        result = await self.db.execute(
            select(UserSession)
            .options(selectinload(UserSession.user))
            .where(
                and_(
                    UserSession.refresh_token == refresh_token,
                    UserSession.is_active == True
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def validate_session(self, session_token: str) -> Optional[UserSession]:
        """Validate session and return if valid (optimized)"""
        session = await self.get_session_by_token(session_token)

        if not session:
            return None

        if not session.is_valid():
            # Session is expired or inactive, deactivate it
            session.deactivate()
            await self.db.commit()
            return None

        # Only update activity if it's been more than 5 minutes since last update
        # This reduces database writes significantly
        import datetime
        if (datetime.datetime.utcnow() - session.last_activity).total_seconds() > 300:
            session.update_activity()
            await self.db.commit()

        return session
    
    async def refresh_session(self, refresh_token: str) -> Optional[UserSession]:
        """Refresh session using refresh token"""
        session = await self.get_session_by_refresh_token(refresh_token)
        
        if not session or not session.is_valid():
            return None
        
        # Extend session
        session.refresh_session(extend_hours=24)
        await self.db.commit()
        
        return session
    
    async def logout_session(self, session_token: str) -> bool:
        """Logout specific session"""
        session = await self.get_session_by_token(session_token)
        
        if not session:
            return False
        
        session.deactivate()
        await self.db.commit()
        
        return True
    
    async def logout_all_sessions(self, user_id: uuid.UUID) -> int:
        """Logout all sessions for a user"""
        result = await self.db.execute(
            select(UserSession).where(
                and_(
                    UserSession.user_id == user_id,
                    UserSession.is_active == True
                )
            )
        )
        sessions = result.scalars().all()
        
        count = 0
        for session in sessions:
            session.deactivate()
            count += 1
        
        await self.db.commit()
        return count
    
    async def get_user_sessions(self, user_id: uuid.UUID, active_only: bool = True) -> List[UserSession]:
        """Get all sessions for a user"""
        query = select(UserSession).where(UserSession.user_id == user_id)
        
        if active_only:
            query = query.where(UserSession.is_active == True)
        
        result = await self.db.execute(query.order_by(UserSession.last_activity.desc()))
        return result.scalars().all()
    
    async def cleanup_expired_sessions(self, user_id: uuid.UUID = None) -> int:
        """Clean up expired sessions"""
        query = select(UserSession).where(
            or_(
                UserSession.expires_at < datetime.utcnow(),
                UserSession.is_active == False
            )
        )
        
        if user_id:
            query = query.where(UserSession.user_id == user_id)
        
        result = await self.db.execute(query)
        expired_sessions = result.scalars().all()
        
        count = 0
        for session in expired_sessions:
            await self.db.delete(session)
            count += 1
        
        await self.db.commit()
        return count
    
    async def get_session_info(self, session_token: str) -> Optional[dict]:
        """Get session information"""
        session = await self.get_session_by_token(session_token)
        
        if not session:
            return None
        
        return {
            'session_id': str(session.id),
            'user_id': str(session.user_id),
            'user_email': session.user.email if session.user else None,
            'user_name': session.user.full_name if session.user else None,
            'is_active': session.is_active,
            'expires_at': session.expires_at.isoformat(),
            'last_activity': session.last_activity.isoformat(),
            'ip_address': session.ip_address,
            'user_agent': session.user_agent,
            'created_at': session.created_at.isoformat()
        }
