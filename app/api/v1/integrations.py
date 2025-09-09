"""
Integration API endpoints for third-party services
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from uuid import UUID
import json
import hmac
import hashlib
from datetime import datetime

from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.models.user import User
from app.models.organization import Organization, OrganizationMember
from app.models.integrations import (
    Integration, IntegrationSyncLog, WebhookEvent, 
    APIKey, ExternalAccount, IntegrationTemplate
)
from app.schemas.integrations import (
    IntegrationCreate, IntegrationResponse, IntegrationUpdate,
    WebhookEventResponse, APIKeyCreate, APIKeyResponse,
    ExternalAccountResponse, IntegrationTemplateResponse
)
from app.services.integration_service import IntegrationService

router = APIRouter()


@router.get("/organizations/{organization_id}/integrations", response_model=List[IntegrationResponse])
async def get_integrations(
    organization_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all integrations for organization"""
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
    
    integrations = db.query(Integration).filter(
        Integration.organization_id == organization_id
    ).all()
    
    return integrations


@router.post("/organizations/{organization_id}/integrations", response_model=IntegrationResponse)
async def create_integration(
    organization_id: UUID,
    integration_data: IntegrationCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new integration"""
    # Check if user is admin/owner of the organization
    member = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == organization_id,
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.role.in_(['owner', 'admin'])
    ).first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners and admins can create integrations"
        )
    
    # Create integration
    integration = Integration(
        organization_id=organization_id,
        integration_type=integration_data.integration_type,
        name=integration_data.name,
        description=integration_data.description,
        configuration=integration_data.configuration,
        sync_frequency=integration_data.sync_frequency,
        created_by=current_user.id
    )
    
    db.add(integration)
    db.commit()
    db.refresh(integration)
    
    # Initialize integration in background
    integration_service = IntegrationService(db)
    background_tasks.add_task(
        integration_service.initialize_integration,
        integration.id
    )
    
    return integration


@router.put("/organizations/{organization_id}/integrations/{integration_id}")
async def update_integration(
    organization_id: UUID,
    integration_id: UUID,
    integration_data: IntegrationUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update integration configuration"""
    # Check if user is admin/owner of the organization
    member = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == organization_id,
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.role.in_(['owner', 'admin'])
    ).first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners and admins can update integrations"
        )
    
    integration = db.query(Integration).filter(
        Integration.id == integration_id,
        Integration.organization_id == organization_id
    ).first()
    
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found"
        )
    
    # Update integration
    if integration_data.name:
        integration.name = integration_data.name
    if integration_data.description is not None:
        integration.description = integration_data.description
    if integration_data.configuration:
        integration.configuration = integration_data.configuration
    if integration_data.sync_enabled is not None:
        integration.sync_enabled = integration_data.sync_enabled
    if integration_data.sync_frequency:
        integration.sync_frequency = integration_data.sync_frequency
    
    db.commit()
    db.refresh(integration)
    
    return integration


@router.delete("/organizations/{organization_id}/integrations/{integration_id}")
async def delete_integration(
    organization_id: UUID,
    integration_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete integration"""
    # Check if user is admin/owner of the organization
    member = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == organization_id,
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.role.in_(['owner', 'admin'])
    ).first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners and admins can delete integrations"
        )
    
    integration = db.query(Integration).filter(
        Integration.id == integration_id,
        Integration.organization_id == organization_id
    ).first()
    
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found"
        )
    
    db.delete(integration)
    db.commit()
    
    return {"message": "Integration deleted successfully"}


@router.post("/organizations/{organization_id}/integrations/{integration_id}/sync")
async def trigger_sync(
    organization_id: UUID,
    integration_id: UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Trigger manual sync for integration"""
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
    
    integration = db.query(Integration).filter(
        Integration.id == integration_id,
        Integration.organization_id == organization_id
    ).first()
    
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found"
        )
    
    # Trigger sync in background
    integration_service = IntegrationService(db)
    background_tasks.add_task(
        integration_service.sync_integration,
        integration.id
    )
    
    return {"message": "Sync triggered successfully"}


@router.get("/organizations/{organization_id}/integrations/{integration_id}/logs", response_model=List[Dict[str, Any]])
async def get_integration_logs(
    organization_id: UUID,
    integration_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get sync logs for integration"""
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
    
    logs = db.query(IntegrationSyncLog).filter(
        IntegrationSyncLog.integration_id == integration_id
    ).order_by(IntegrationSyncLog.started_at.desc()).limit(50).all()
    
    return [
        {
            "id": str(log.id),
            "sync_type": log.sync_type,
            "status": log.status,
            "records_processed": log.records_processed,
            "records_created": log.records_created,
            "records_updated": log.records_updated,
            "records_failed": log.records_failed,
            "duration_ms": log.duration_ms,
            "started_at": log.started_at.isoformat(),
            "completed_at": log.completed_at.isoformat() if log.completed_at else None,
            "error_details": log.error_details
        }
        for log in logs
    ]


@router.post("/webhooks/{organization_id}")
async def receive_webhook(
    organization_id: UUID,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Receive webhook from external service"""
    try:
        # Get request data
        body = await request.body()
        headers = dict(request.headers)
        
        # Create webhook event record
        webhook_event = WebhookEvent(
            organization_id=organization_id,
            event_type="external_webhook",
            event_source=headers.get("user-agent", "unknown"),
            payload=json.loads(body.decode()) if body else {},
            headers=headers
        )
        
        db.add(webhook_event)
        db.commit()
        db.refresh(webhook_event)
        
        # Process webhook in background
        integration_service = IntegrationService(db)
        background_tasks.add_task(
            integration_service.process_webhook,
            webhook_event.id
        )
        
        return {"status": "received", "event_id": str(webhook_event.id)}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error processing webhook: {str(e)}"
        )


@router.get("/organizations/{organization_id}/webhooks", response_model=List[WebhookEventResponse])
async def get_webhook_events(
    organization_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get webhook events for organization"""
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
    
    events = db.query(WebhookEvent).filter(
        WebhookEvent.organization_id == organization_id
    ).order_by(WebhookEvent.created_at.desc()).limit(100).all()
    
    return events


@router.post("/organizations/{organization_id}/api-keys", response_model=APIKeyResponse)
async def create_api_key(
    organization_id: UUID,
    api_key_data: APIKeyCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new API key"""
    # Check if user is admin/owner of the organization
    member = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == organization_id,
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.role.in_(['owner', 'admin'])
    ).first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners and admins can create API keys"
        )
    
    # Generate API key
    import secrets
    import hashlib
    
    api_key = f"aws_{secrets.token_urlsafe(32)}"
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    key_prefix = api_key[:8]
    
    # Create API key record
    api_key_record = APIKey(
        organization_id=organization_id,
        user_id=current_user.id,
        key_name=api_key_data.key_name,
        key_hash=key_hash,
        key_prefix=key_prefix,
        permissions=api_key_data.permissions,
        rate_limit=api_key_data.rate_limit,
        expires_at=api_key_data.expires_at
    )
    
    db.add(api_key_record)
    db.commit()
    db.refresh(api_key_record)
    
    # Return the actual key only once
    response = APIKeyResponse.from_orm(api_key_record)
    response.api_key = api_key  # Include the actual key in response
    
    return response


@router.get("/organizations/{organization_id}/api-keys", response_model=List[APIKeyResponse])
async def get_api_keys(
    organization_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get API keys for organization"""
    # Check if user is admin/owner of the organization
    member = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == organization_id,
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.role.in_(['owner', 'admin'])
    ).first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners and admins can view API keys"
        )
    
    api_keys = db.query(APIKey).filter(
        APIKey.organization_id == organization_id
    ).all()
    
    return api_keys


@router.get("/integration-templates", response_model=List[IntegrationTemplateResponse])
async def get_integration_templates(
    integration_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get available integration templates"""
    try:
        # Initialize default templates if none exist
        existing_count = db.query(IntegrationTemplate).count()
        if existing_count == 0:
            await _initialize_default_integration_templates(db)

        query = db.query(IntegrationTemplate).filter(
            IntegrationTemplate.is_public == True,
            IntegrationTemplate.is_active == True
        )

        if integration_type:
            query = query.filter(IntegrationTemplate.integration_type == integration_type)

        templates = query.all()
        return templates
    except Exception as e:
        # Return default templates if database query fails
        return _get_default_integration_templates(integration_type)


async def _initialize_default_integration_templates(db: Session):
    """Initialize default integration templates"""
    default_templates = [
        {
            "name": "Slack Project Notifications",
            "integration_type": "slack",
            "description": "Send project updates to Slack channels",
            "configuration_schema": {
                "webhook_url": {"type": "string", "required": True},
                "channel": {"type": "string", "required": True}
            },
            "is_public": True,
            "is_active": True
        },
        {
            "name": "GitHub Issue Sync",
            "integration_type": "github",
            "description": "Sync cards with GitHub issues",
            "configuration_schema": {
                "repository": {"type": "string", "required": True},
                "access_token": {"type": "string", "required": True}
            },
            "is_public": True,
            "is_active": True
        },
        {
            "name": "Google Calendar Integration",
            "integration_type": "google_calendar",
            "description": "Sync project deadlines with Google Calendar",
            "configuration_schema": {
                "calendar_id": {"type": "string", "required": True},
                "credentials": {"type": "object", "required": True}
            },
            "is_public": True,
            "is_active": True
        }
    ]

    for template_data in default_templates:
        template = IntegrationTemplate(**template_data)
        db.add(template)

    db.commit()


def _get_default_integration_templates(integration_type: Optional[str] = None):
    """Get default integration templates as fallback"""
    templates = [
        {
            "id": "slack-notifications",
            "name": "Slack Project Notifications",
            "integration_type": "slack",
            "description": "Send project updates to Slack channels",
            "configuration_schema": {
                "webhook_url": {"type": "string", "required": True},
                "channel": {"type": "string", "required": True}
            },
            "is_public": True,
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "id": "github-sync",
            "name": "GitHub Issue Sync",
            "integration_type": "github",
            "description": "Sync cards with GitHub issues",
            "configuration_schema": {
                "repository": {"type": "string", "required": True},
                "access_token": {"type": "string", "required": True}
            },
            "is_public": True,
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    ]

    if integration_type:
        templates = [t for t in templates if t["integration_type"] == integration_type]

    return templates
