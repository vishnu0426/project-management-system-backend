"""
Registration management endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, func
from typing import Optional, Dict, Any
import json
from datetime import datetime

from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.core.exceptions import ValidationError, ResourceNotFoundError
from app.models.user import User
from app.models.registration import Registration
from app.schemas.registration import (
    RegistrationCreate, RegistrationUpdate, RegistrationResponse, RegistrationListResponse
)

router = APIRouter()


@router.post("/", response_model=RegistrationResponse)
async def create_registration(
    registration_data: RegistrationCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Create a new registration record with all form data"""
    
    # Extract system information from request
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    
    # Parse browser info from user agent (basic parsing)
    browser_info = {
        "user_agent": user_agent,
        "ip_address": client_ip,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Check if email already exists in registrations
    result = await db.execute(
        select(Registration).where(Registration.email == registration_data.email)
    )
    existing_registration = result.scalar_one_or_none()
    
    if existing_registration:
        raise ValidationError(f"Registration already exists for email: {registration_data.email}")
    
    # Create registration record
    registration = Registration(
        # Personal Information
        first_name=registration_data.first_name,
        last_name=registration_data.last_name,
        email=registration_data.email,
        phone_number=registration_data.phone_number,
        
        # Organization Information
        organization_name=registration_data.organization_name,
        organization_domain=registration_data.organization_domain,
        organization_size=registration_data.organization_size,
        industry=registration_data.industry,
        
        # Role and Access
        requested_role=registration_data.requested_role,
        
        # Additional Information
        job_title=registration_data.job_title,
        department=registration_data.department,
        company_website=registration_data.company_website,
        
        # Registration Context
        registration_source=registration_data.registration_source,
        referral_source=registration_data.referral_source,
        marketing_consent=registration_data.marketing_consent,
        terms_accepted=registration_data.terms_accepted,
        privacy_policy_accepted=registration_data.privacy_policy_accepted,
        
        # System Information
        ip_address=client_ip,
        user_agent=user_agent,
        browser_info=browser_info,
        
        # Additional metadata
        form_metadata=registration_data.form_metadata or {},
        
        # Default status
        status='pending'
    )
    
    db.add(registration)
    await db.commit()
    await db.refresh(registration)
    
    return RegistrationResponse.from_orm(registration)


@router.get("/", response_model=RegistrationListResponse)
async def list_registrations(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """List all registrations (admin only)"""
    
    # Build query
    query = select(Registration)
    
    # Apply filters
    if status:
        query = query.where(Registration.status == status)
    
    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                Registration.first_name.ilike(search_term),
                Registration.last_name.ilike(search_term),
                Registration.email.ilike(search_term),
                Registration.organization_name.ilike(search_term)
            )
        )
    
    # Get total count
    count_result = await db.execute(select(func.count(Registration.id)).select_from(query.subquery()))
    total = count_result.scalar()
    
    # Apply pagination and ordering
    query = query.order_by(desc(Registration.created_at))
    query = query.offset((page - 1) * per_page).limit(per_page)
    
    # Execute query
    result = await db.execute(query)
    registrations = result.scalars().all()
    
    return RegistrationListResponse(
        registrations=[RegistrationResponse.from_orm(reg) for reg in registrations],
        total=total,
        page=page,
        per_page=per_page,
        total_pages=(total + per_page - 1) // per_page
    )


@router.get("/{registration_id}", response_model=RegistrationResponse)
async def get_registration(
    registration_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific registration by ID"""
    result = await db.execute(
        select(Registration).where(Registration.id == registration_id)
    )
    registration = result.scalar_one_or_none()
    
    if not registration:
        raise ResourceNotFoundError("Registration not found")
    
    return RegistrationResponse.from_orm(registration)


@router.put("/{registration_id}", response_model=RegistrationResponse)
async def update_registration(
    registration_id: str,
    update_data: RegistrationUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a registration record"""
    result = await db.execute(
        select(Registration).where(Registration.id == registration_id)
    )
    registration = result.scalar_one_or_none()
    
    if not registration:
        raise ResourceNotFoundError("Registration not found")
    
    # Update fields
    for field, value in update_data.dict(exclude_unset=True).items():
        if hasattr(registration, field):
            setattr(registration, field, value)
    
    # Set processor info if status is being changed
    if update_data.status and update_data.status != registration.status:
        registration.processed_by = current_user.id
        registration.processed_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(registration)
    
    return RegistrationResponse.from_orm(registration)


@router.delete("/{registration_id}")
async def delete_registration(
    registration_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a registration record"""
    result = await db.execute(
        select(Registration).where(Registration.id == registration_id)
    )
    registration = result.scalar_one_or_none()
    
    if not registration:
        raise ResourceNotFoundError("Registration not found")
    
    await db.delete(registration)
    await db.commit()
    
    return {"success": True, "message": "Registration deleted successfully"}
