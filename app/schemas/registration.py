"""
Registration schemas
"""
from pydantic import BaseModel, EmailStr, validator
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID


class RegistrationCreate(BaseModel):
    # Personal Information
    first_name: str
    last_name: str
    email: EmailStr
    phone_number: Optional[str] = None
    
    # Organization Information
    organization_name: str
    organization_domain: Optional[str] = None
    organization_size: Optional[str] = None
    industry: Optional[str] = None
    
    # Role and Access
    requested_role: str = 'owner'
    
    # Additional Information
    job_title: Optional[str] = None
    department: Optional[str] = None
    company_website: Optional[str] = None
    
    # Registration Context
    registration_source: str = 'web'
    referral_source: Optional[str] = None
    marketing_consent: bool = False
    terms_accepted: bool = True
    privacy_policy_accepted: bool = True
    
    # System Information (will be populated by backend)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    browser_info: Optional[Dict[str, Any]] = None
    
    # Additional metadata
    form_metadata: Optional[Dict[str, Any]] = None
    
    @validator('first_name', 'last_name')
    def validate_names(cls, v):
        if not v or not v.strip():
            raise ValueError('Name cannot be empty')
        if len(v.strip()) < 2:
            raise ValueError('Name must be at least 2 characters long')
        return v.strip()
    
    @validator('organization_name')
    def validate_organization_name(cls, v):
        if not v or not v.strip():
            raise ValueError('Organization name cannot be empty')
        if len(v.strip()) < 2:
            raise ValueError('Organization name must be at least 2 characters long')
        return v.strip()
    
    @validator('terms_accepted', 'privacy_policy_accepted')
    def validate_required_acceptance(cls, v):
        if not v:
            raise ValueError('Terms and privacy policy must be accepted')
        return v


class RegistrationUpdate(BaseModel):
    # Status and Processing
    status: Optional[str] = None
    assigned_role: Optional[str] = None
    approval_notes: Optional[str] = None
    processed_by: Optional[UUID] = None
    
    # Allow updating any field
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None
    organization_domain: Optional[str] = None
    organization_size: Optional[str] = None
    industry: Optional[str] = None
    job_title: Optional[str] = None
    department: Optional[str] = None
    company_website: Optional[str] = None
    referral_source: Optional[str] = None
    marketing_consent: Optional[bool] = None
    form_metadata: Optional[Dict[str, Any]] = None


class RegistrationResponse(BaseModel):
    id: UUID
    
    # Personal Information
    first_name: str
    last_name: str
    email: str
    phone_number: Optional[str] = None
    
    # Organization Information
    organization_name: str
    organization_domain: Optional[str] = None
    organization_size: Optional[str] = None
    industry: Optional[str] = None
    
    # Role and Access
    requested_role: str
    assigned_role: Optional[str] = None
    
    # Additional Information
    job_title: Optional[str] = None
    department: Optional[str] = None
    company_website: Optional[str] = None
    
    # Registration Context
    registration_source: str
    referral_source: Optional[str] = None
    marketing_consent: bool
    terms_accepted: bool
    privacy_policy_accepted: bool
    
    # System Information
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    browser_info: Optional[Dict[str, Any]] = None
    
    # Status and Processing
    status: str
    approval_notes: Optional[str] = None
    processed_by: Optional[UUID] = None
    processed_at: Optional[datetime] = None
    
    # Linked Records
    user_id: Optional[UUID] = None
    organization_id: Optional[UUID] = None
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    
    # Additional metadata
    form_metadata: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True


class RegistrationListResponse(BaseModel):
    registrations: list[RegistrationResponse]
    total: int
    page: int
    per_page: int
    total_pages: int
