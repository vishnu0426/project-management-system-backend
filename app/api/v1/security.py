"""
Security and compliance API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timedelta
import json

from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.models.user import User
from app.models.organization import Organization, OrganizationMember
from app.models.security import (
    DataRetentionPolicy, GDPRRequest, SecurityEvent, 
    BackupRecord, ComplianceAudit, SecurityAlert, ConsentRecord
)
from app.schemas.security import (
    DataRetentionPolicyCreate, DataRetentionPolicyResponse,
    GDPRRequestCreate, GDPRRequestResponse,
    SecurityEventResponse, SecurityAlertResponse,
    BackupRecordResponse, ComplianceAuditResponse,
    ConsentRecordCreate, ConsentRecordResponse
)

router = APIRouter()


@router.post("/organizations/{organization_id}/gdpr-requests", response_model=GDPRRequestResponse)
async def create_gdpr_request(
    organization_id: UUID,
    request_data: GDPRRequestCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Create a new GDPR request"""
    # Verify organization exists
    organization = db.query(Organization).filter(Organization.id == organization_id).first()
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    # Check if user exists in the organization
    user = None
    if request_data.requester_email:
        user = db.query(User).filter(User.email == request_data.requester_email).first()
        if user:
            # Verify user is member of organization
            member = db.query(OrganizationMember).filter(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id == user.id
            ).first()
            if not member:
                user = None
    
    # Create GDPR request
    gdpr_request = GDPRRequest(
        organization_id=organization_id,
        user_id=user.id if user else None,
        request_type=request_data.request_type,
        requester_email=request_data.requester_email,
        requester_name=request_data.requester_name,
        request_details=request_data.request_details,
        due_date=datetime.utcnow() + timedelta(days=30)  # GDPR 30-day requirement
    )
    
    db.add(gdpr_request)
    db.commit()
    db.refresh(gdpr_request)
    
    # Start background processing for the request
    # background_tasks.add_task(process_gdpr_request, gdpr_request.id, db)
    
    return gdpr_request


@router.get("/organizations/{organization_id}/gdpr-requests", response_model=List[GDPRRequestResponse])
async def get_gdpr_requests(
    organization_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all GDPR requests for organization"""
    # Check if user is admin/owner of the organization
    member = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == organization_id,
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.role.in_(['owner', 'admin'])
    ).first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners and admins can view GDPR requests"
        )
    
    requests = db.query(GDPRRequest).filter(
        GDPRRequest.organization_id == organization_id
    ).order_by(GDPRRequest.created_at.desc()).all()
    
    return requests


@router.put("/organizations/{organization_id}/gdpr-requests/{request_id}")
async def update_gdpr_request(
    organization_id: UUID,
    request_id: UUID,
    status_update: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update GDPR request status"""
    # Check if user is admin/owner of the organization
    member = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == organization_id,
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.role.in_(['owner', 'admin'])
    ).first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners and admins can update GDPR requests"
        )
    
    gdpr_request = db.query(GDPRRequest).filter(
        GDPRRequest.id == request_id,
        GDPRRequest.organization_id == organization_id
    ).first()
    
    if not gdpr_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="GDPR request not found"
        )
    
    gdpr_request.status = status_update
    gdpr_request.processed_by = current_user.id
    
    if status_update in ['completed', 'rejected']:
        gdpr_request.completed_at = datetime.utcnow()
    
    db.commit()
    
    return {"message": "GDPR request updated successfully"}


@router.post("/organizations/{organization_id}/data-retention-policies", response_model=DataRetentionPolicyResponse)
async def create_data_retention_policy(
    organization_id: UUID,
    policy_data: DataRetentionPolicyCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new data retention policy"""
    # Check if user is admin/owner of the organization
    member = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == organization_id,
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.role.in_(['owner', 'admin'])
    ).first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners and admins can create data retention policies"
        )
    
    policy = DataRetentionPolicy(
        organization_id=organization_id,
        policy_name=policy_data.policy_name,
        data_type=policy_data.data_type,
        retention_period_days=policy_data.retention_period_days,
        auto_delete=policy_data.auto_delete,
        archive_before_delete=policy_data.archive_before_delete,
        legal_basis=policy_data.legal_basis,
        description=policy_data.description,
        created_by=current_user.id
    )
    
    db.add(policy)
    db.commit()
    db.refresh(policy)
    
    return policy


@router.get("/organizations/{organization_id}/data-retention-policies", response_model=List[DataRetentionPolicyResponse])
async def get_data_retention_policies(
    organization_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all data retention policies for organization"""
    # Check if user has access to this organization
    member = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == organization_id,
        OrganizationMember.user_id == current_user.id
    ).first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to organization"
        )
    
    policies = db.query(DataRetentionPolicy).filter(
        DataRetentionPolicy.organization_id == organization_id,
        DataRetentionPolicy.is_active == True
    ).all()
    
    return policies


@router.get("/organizations/{organization_id}/security-events", response_model=List[SecurityEventResponse])
async def get_security_events(
    organization_id: UUID,
    severity: Optional[str] = None,
    event_type: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get security events for organization"""
    # Check if user is admin/owner of the organization
    member = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == organization_id,
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.role.in_(['owner', 'admin'])
    ).first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners and admins can view security events"
        )
    
    query = db.query(SecurityEvent).filter(SecurityEvent.organization_id == organization_id)
    
    if severity:
        query = query.filter(SecurityEvent.severity == severity)
    
    if event_type:
        query = query.filter(SecurityEvent.event_type == event_type)
    
    events = query.order_by(SecurityEvent.created_at.desc()).limit(100).all()
    
    return events


@router.get("/organizations/{organization_id}/security-alerts", response_model=List[SecurityAlertResponse])
async def get_security_alerts(
    organization_id: UUID,
    status_filter: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get security alerts for organization"""
    # Check if user is admin/owner of the organization
    member = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == organization_id,
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.role.in_(['owner', 'admin'])
    ).first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners and admins can view security alerts"
        )
    
    query = db.query(SecurityAlert).filter(SecurityAlert.organization_id == organization_id)
    
    if status_filter:
        query = query.filter(SecurityAlert.status == status_filter)
    
    alerts = query.order_by(SecurityAlert.created_at.desc()).all()
    
    return alerts


@router.post("/organizations/{organization_id}/backups")
async def create_backup(
    organization_id: UUID,
    backup_type: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new backup"""
    # Check if user is admin/owner of the organization
    member = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == organization_id,
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.role.in_(['owner', 'admin'])
    ).first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners and admins can create backups"
        )
    
    # Create backup record
    backup = BackupRecord(
        organization_id=organization_id,
        backup_type=backup_type,
        backup_scope='organization',
        file_path=f"/backups/{organization_id}/{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{backup_type}.backup",
        encryption_enabled=True,
        retention_until=datetime.utcnow() + timedelta(days=90),  # 90-day retention
        created_by=current_user.id
    )
    
    db.add(backup)
    db.commit()
    db.refresh(backup)
    
    # Start background backup process
    # background_tasks.add_task(process_backup, backup.id, db)
    
    return {"message": "Backup started successfully", "backup_id": backup.id}


@router.get("/organizations/{organization_id}/backups", response_model=List[BackupRecordResponse])
async def get_backups(
    organization_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get backup records for organization"""
    # Check if user is admin/owner of the organization
    member = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == organization_id,
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.role.in_(['owner', 'admin'])
    ).first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners and admins can view backups"
        )
    
    backups = db.query(BackupRecord).filter(
        BackupRecord.organization_id == organization_id
    ).order_by(BackupRecord.started_at.desc()).all()
    
    return backups


@router.post("/organizations/{organization_id}/consent", response_model=ConsentRecordResponse)
async def record_consent(
    organization_id: UUID,
    consent_data: ConsentRecordCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Record user consent"""
    # Verify user is member of organization
    member = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == organization_id,
        OrganizationMember.user_id == current_user.id
    ).first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to organization"
        )
    
    consent = ConsentRecord(
        user_id=current_user.id,
        organization_id=organization_id,
        consent_type=consent_data.consent_type,
        consent_given=consent_data.consent_given,
        consent_method=consent_data.consent_method,
        legal_basis=consent_data.legal_basis,
        purpose_description=consent_data.purpose_description,
        data_categories=consent_data.data_categories,
        retention_period=consent_data.retention_period,
        third_party_sharing=consent_data.third_party_sharing,
        consent_version=consent_data.consent_version,
        expires_at=consent_data.expires_at
    )
    
    db.add(consent)
    db.commit()
    db.refresh(consent)
    
    return consent


@router.get("/organizations/{organization_id}/compliance/audit", response_model=List[ComplianceAuditResponse])
async def get_compliance_audits(
    organization_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get compliance audit records"""
    # Check if user is admin/owner of the organization
    member = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == organization_id,
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.role.in_(['owner', 'admin'])
    ).first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners and admins can view compliance audits"
        )
    
    audits = db.query(ComplianceAudit).filter(
        ComplianceAudit.organization_id == organization_id
    ).order_by(ComplianceAudit.created_at.desc()).all()
    
    return audits
