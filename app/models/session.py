"""
Session model for database-based authentication
"""
import uuid
from datetime import datetime, timedelta
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class UserSession(Base):
    """User session stored in database"""
    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    session_token = Column(String(255), nullable=False, unique=True, index=True)
    refresh_token = Column(String(255), nullable=True, unique=True, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Session metadata
    ip_address = Column(String(45), nullable=True)  # IPv6 support
    user_agent = Column(Text, nullable=True)
    device_info = Column(Text, nullable=True)
    last_activity = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="sessions")

    @classmethod
    def create_session(cls, user_id: uuid.UUID, session_duration_hours: int = 24, 
                      ip_address: str = None, user_agent: str = None) -> 'UserSession':
        """Create a new user session"""
        import secrets
        
        session_token = secrets.token_urlsafe(32)
        refresh_token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=session_duration_hours)
        
        return cls(
            user_id=user_id,
            session_token=session_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
            last_activity=datetime.utcnow()
        )
    
    def is_expired(self) -> bool:
        """Check if session is expired"""
        return datetime.utcnow() > self.expires_at
    
    def is_valid(self) -> bool:
        """Check if session is valid (active and not expired)"""
        return self.is_active and not self.is_expired()
    
    def refresh_session(self, extend_hours: int = 24) -> None:
        """Refresh session expiration"""
        self.expires_at = datetime.utcnow() + timedelta(hours=extend_hours)
        self.last_activity = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def deactivate(self) -> None:
        """Deactivate session (logout)"""
        self.is_active = False
        self.updated_at = datetime.utcnow()
    
    def update_activity(self, ip_address: str = None, user_agent: str = None) -> None:
        """Update last activity and optional metadata"""
        self.last_activity = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        
        if ip_address:
            self.ip_address = ip_address
        if user_agent:
            self.user_agent = user_agent

    def to_dict(self) -> dict:
        """Convert session to dictionary"""
        return {
            'id': str(self.id),
            'user_id': str(self.user_id),
            'session_token': self.session_token,
            'is_active': self.is_active,
            'expires_at': self.expires_at.isoformat(),
            'created_at': self.created_at.isoformat(),
            'last_activity': self.last_activity.isoformat(),
            'ip_address': self.ip_address,
            'user_agent': self.user_agent
        }
