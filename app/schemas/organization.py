"""
Organization schemas
"""
from pydantic import BaseModel, validator
from typing import Optional, List
from datetime import datetime
from uuid import UUID


class OrganizationCreate(BaseModel):
    name: str
    description: Optional[str] = None
    domain: Optional[str] = None  # Changed from website to domain
    allowed_domains: Optional[List[str]] = None

    # Contact information
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None

    # Address details
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None

    # Organization type/category
    organization_category: Optional[str] = None

    # Language preference
    language: Optional[str] = None

    @validator('name')
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError('Organization name cannot be empty')
        if len(v.strip()) < 2:
            raise ValueError('Organization name must be at least 2 characters long')
        return v.strip()

    @validator('contact_email')
    def validate_contact_email(cls, v):
        if v is not None and v.strip():
            # Basic email validation
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, v.strip()):
                raise ValueError('Invalid email format')
            return v.strip()
        return v


class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    domain: Optional[str] = None  # Changed from website to domain
    allowed_domains: Optional[List[str]] = None

    # Contact information
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None

    # Address details
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None

    # Organization type/category
    organization_category: Optional[str] = None

    # Language preference
    language: Optional[str] = None

    @validator('name')
    def validate_name(cls, v):
        if v is not None:
            if not v.strip():
                raise ValueError('Organization name cannot be empty')
            if len(v.strip()) < 2:
                raise ValueError('Organization name must be at least 2 characters long')
            return v.strip()
        return v

    @validator('contact_email')
    def validate_contact_email(cls, v):
        if v is not None and v.strip():
            # Basic email validation
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, v.strip()):
                raise ValueError('Invalid email format')
            return v.strip()
        return v


class OrganizationMemberResponse(BaseModel):
    id: str
    user_id: str
    role: str
    joined_at: datetime
    user: dict  # Will contain user details
    
    class Config:
        from_attributes = True


class OrganizationResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    logo_url: Optional[str] = None
    domain: Optional[str] = None  # Changed from website to domain
    allowed_domains: Optional[List[str]] = None

    # Contact information
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None

    # Address details
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None

    # Organization type/category
    organization_category: Optional[str] = None

    # Language preference
    language: Optional[str] = None

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MemberInvite(BaseModel):
    email: str
    role: str = "member"
    
    @validator('role')
    def validate_role(cls, v):
        if v not in ['viewer', 'member', 'admin']:
            raise ValueError('Role must be viewer, member, or admin')
        return v


class MemberRoleUpdate(BaseModel):
    role: str
    
    @validator('role')
    def validate_role(cls, v):
        if v not in ['viewer', 'member', 'admin', 'owner']:
            raise ValueError('Role must be viewer, member, admin, or owner')
        return v


class BillingInfo(BaseModel):
    company_name: Optional[str] = None
    billing_email: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    tax_id: Optional[str] = None


class SubscriptionInfo(BaseModel):
    plan: str = "free"
    status: str = "active"
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    cancel_at_period_end: bool = False


class OrganizationHierarchy(BaseModel):
    """Organization hierarchy response schema"""
    id: str
    name: str
    parent_id: Optional[str] = None
    parent: Optional['OrganizationResponse'] = None
    children: List['OrganizationResponse'] = []
    level: int = 0

    class Config:
        from_attributes = True


class OrganizationCollaborationCreate(BaseModel):
    """Schema for creating organization collaboration"""
    partner_organization_id: str
    collaboration_type: str = "partnership"  # partnership, client, vendor, etc.
    description: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    terms: Optional[dict] = None


class OrganizationCollaborationUpdate(BaseModel):
    """Schema for updating organization collaboration"""
    collaboration_type: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    terms: Optional[dict] = None
    status: Optional[str] = None  # active, inactive, pending


class OrganizationCollaborationResponse(BaseModel):
    """Schema for organization collaboration response"""
    id: str
    organization_id: str
    partner_organization_id: str
    collaboration_type: str
    description: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    terms: Optional[dict] = None
    status: str
    created_at: datetime
    updated_at: datetime

    # Related data
    organization: OrganizationResponse
    partner_organization: OrganizationResponse

    class Config:
        from_attributes = True
