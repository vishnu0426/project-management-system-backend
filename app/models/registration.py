"""
Registration model to store all registration form data
"""
from sqlalchemy import Column, String, Text, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class Registration(Base):
    __tablename__ = "registrations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Personal Information
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    phone_number = Column(String(20), nullable=True)
    
    # Organization Information
    organization_name = Column(String(255), nullable=False)
    organization_domain = Column(String(255), nullable=True)
    organization_size = Column(String(50), nullable=True)  # e.g., "1-10", "11-50", "51-200", "200+"
    industry = Column(String(100), nullable=True)
    
    # Role and Access
    requested_role = Column(String(50), default='owner', nullable=False)  # Role requested during registration
    assigned_role = Column(String(50), nullable=True)  # Actual role assigned after approval
    
    # Additional Information
    job_title = Column(String(100), nullable=True)
    department = Column(String(100), nullable=True)
    company_website = Column(String(255), nullable=True)
    
    # Registration Context
    registration_source = Column(String(50), default='web', nullable=False)  # web, mobile, api, invitation
    referral_source = Column(String(100), nullable=True)  # How they heard about us
    marketing_consent = Column(Boolean, default=False, nullable=False)
    terms_accepted = Column(Boolean, default=False, nullable=False)
    privacy_policy_accepted = Column(Boolean, default=False, nullable=False)
    
    # System Information
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    user_agent = Column(Text, nullable=True)
    browser_info = Column(JSON, nullable=True)  # Browser details, screen resolution, etc.
    
    # Status and Processing
    status = Column(String(50), default='pending', nullable=False)  # pending, approved, rejected, completed
    approval_notes = Column(Text, nullable=True)
    processed_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Linked Records
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)  # Created user after approval
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id'), nullable=True)  # Created/joined org
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Additional metadata
    form_metadata = Column(JSON, nullable=True)  # Store any additional form data
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="registration")
    organization = relationship("Organization", foreign_keys=[organization_id])
    processor = relationship("User", foreign_keys=[processed_by])

    def __repr__(self):
        return f"<Registration(id={self.id}, email={self.email}, organization={self.organization_name}, status={self.status})>"
