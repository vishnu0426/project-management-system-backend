"""
AI and automation API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.models.user import User
from app.models.organization import Organization, OrganizationMember
from app.models.ai_automation import (
    WorkflowRule, WorkflowExecution, AIModel, AIPrediction,
    SmartNotification, CustomField, CustomFieldValue,
    AutomationTemplate, AIInsight
)
from app.schemas.ai_automation import (
    WorkflowRuleCreate, WorkflowRuleResponse,
    AIPredictionResponse, SmartNotificationResponse,
    CustomFieldCreate, CustomFieldResponse,
    AutomationTemplateResponse, AIInsightResponse
)
from app.services.ai_service import AIService
from app.services.automation_service import AutomationService

router = APIRouter()


@router.get("/models")
async def get_ai_models(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get available AI models"""
    try:
        # Try to get models from database
        db_models = db.query(AIModel).filter(AIModel.is_active == True).all()

        if db_models:
            models = []
            for model in db_models:
                models.append({
                    "id": str(model.id),
                    "name": model.model_name,
                    "type": model.model_type,
                    "status": "active" if model.is_active else "inactive",
                    "description": model.description or f"{model.model_type} model",
                    "version": model.model_version,
                    "last_trained": model.last_trained.isoformat() if model.last_trained else None,
                    "usage_count": model.usage_count
                })
        else:
            # Return default models if none in database
            models = [
                {
                    "id": "text-classifier",
                    "name": "Text Classification Model",
                    "type": "classification",
                    "status": "active",
                    "description": "Classifies text content for priority and category detection"
                },
                {
                    "id": "priority-predictor",
                    "name": "Priority Prediction Model",
                    "type": "prediction",
                    "status": "active",
                    "description": "Predicts task priority based on content analysis"
                },
                {
                    "id": "time-estimator",
                    "name": "Time Estimation Model",
                    "type": "estimation",
                    "status": "active",
                    "description": "Estimates completion time for tasks and projects"
                },
                {
                    "id": "risk-analyzer",
                    "name": "Risk Analysis Model",
                    "type": "analysis",
                    "status": "active",
                    "description": "Analyzes project risks and potential bottlenecks"
                }
            ]

        return {
            "success": True,
            "data": models
        }

    except Exception as e:
        # Fallback to basic models if there's any error
        models = [
            {
                "id": "basic-classifier",
                "name": "Basic Text Classifier",
                "type": "classification",
                "status": "active",
                "description": "Basic text classification for project management"
            }
        ]
        return {
            "success": True,
            "data": models
        }


@router.get("/workflows")
async def get_ai_workflows(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get automated workflow configurations"""
    workflows = [
        {
            "id": "auto-priority",
            "name": "Automatic Priority Assignment",
            "description": "Automatically assigns priority based on task content",
            "trigger": "task_created",
            "actions": ["analyze_content", "set_priority"],
            "status": "active"
        },
        {
            "id": "smart-assignment",
            "name": "Smart Task Assignment",
            "description": "Assigns tasks to team members based on skills and workload",
            "trigger": "task_created",
            "actions": ["analyze_requirements", "find_best_assignee", "assign_task"],
            "status": "active"
        },
        {
            "id": "deadline-reminder",
            "name": "Intelligent Deadline Reminders",
            "description": "Sends smart reminders based on task complexity and progress",
            "trigger": "time_based",
            "actions": ["check_progress", "calculate_risk", "send_notification"],
            "status": "active"
        }
    ]

    return {
        "success": True,
        "data": workflows
    }


@router.post("/predictions")
async def create_ai_prediction(
    prediction_request: Dict[str, Any],
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Generate AI predictions for tasks/projects"""
    entity_type = prediction_request.get('entity_type')
    entity_id = prediction_request.get('entity_id')
    prediction_type = prediction_request.get('prediction_type')
    input_data = prediction_request.get('input_data', {})

    # Mock AI prediction logic
    prediction_result = {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "prediction_type": prediction_type,
        "prediction": None,
        "confidence": 0.85,
        "explanation": "",
        "factors": []
    }

    if prediction_type == "priority":
        # Analyze title and description for priority keywords
        title = input_data.get('title', '').lower()
        description = input_data.get('description', '').lower()

        high_priority_keywords = ['urgent', 'critical', 'emergency', 'asap', 'immediately', 'blocker', 'production']
        medium_priority_keywords = ['important', 'needed', 'required', 'should']

        if any(keyword in title or keyword in description for keyword in high_priority_keywords):
            prediction_result.update({
                "prediction": "high",
                "confidence": 0.92,
                "explanation": "High priority detected based on urgent keywords in content",
                "factors": ["urgent_keywords", "content_analysis"]
            })
        elif any(keyword in title or keyword in description for keyword in medium_priority_keywords):
            prediction_result.update({
                "prediction": "medium",
                "confidence": 0.78,
                "explanation": "Medium priority suggested based on content importance indicators",
                "factors": ["importance_keywords", "content_analysis"]
            })
        else:
            prediction_result.update({
                "prediction": "low",
                "confidence": 0.65,
                "explanation": "Low priority assigned as default with no urgent indicators",
                "factors": ["default_assignment", "no_urgent_indicators"]
            })

    elif prediction_type == "completion_time":
        # Estimate completion time based on content complexity
        content_length = len(input_data.get('title', '') + input_data.get('description', ''))
        if content_length > 200:
            hours = 8
        elif content_length > 100:
            hours = 4
        else:
            hours = 2

        prediction_result.update({
            "prediction": f"{hours} hours",
            "confidence": 0.75,
            "explanation": f"Estimated {hours} hours based on task complexity analysis",
            "factors": ["content_complexity", "historical_data"]
        })

    return {
        "success": True,
        "data": prediction_result
    }


@router.get("/insights")
async def get_ai_insights(
    entity_type: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get AI-generated insights and recommendations"""
    insights = [
        {
            "id": "productivity-trend",
            "type": "productivity",
            "title": "Team Productivity Increasing",
            "description": "Your team's productivity has increased by 15% this month",
            "impact": "positive",
            "confidence": 0.88,
            "recommendations": [
                "Continue current workflow practices",
                "Consider expanding successful strategies to other projects"
            ],
            "data": {
                "trend": "upward",
                "percentage_change": 15,
                "time_period": "last_30_days"
            }
        },
        {
            "id": "bottleneck-detection",
            "type": "bottleneck",
            "title": "Potential Bottleneck in Review Process",
            "description": "Tasks are spending 40% longer in review stage than average",
            "impact": "negative",
            "confidence": 0.82,
            "recommendations": [
                "Add additional reviewers to reduce queue time",
                "Implement automated pre-review checks",
                "Consider parallel review processes for non-critical items"
            ],
            "data": {
                "stage": "review",
                "delay_percentage": 40,
                "affected_tasks": 12
            }
        },
        {
            "id": "skill-gap-analysis",
            "type": "recommendation",
            "title": "Frontend Development Capacity",
            "description": "High demand for frontend development skills detected",
            "impact": "neutral",
            "confidence": 0.75,
            "recommendations": [
                "Consider hiring additional frontend developers",
                "Provide frontend training for existing team members",
                "Prioritize frontend tasks in sprint planning"
            ],
            "data": {
                "skill_area": "frontend_development",
                "demand_level": "high",
                "current_capacity": "medium"
            }
        }
    ]

    if entity_type:
        insights = [insight for insight in insights if insight.get('entity_type') == entity_type or not insight.get('entity_type')]

    return {
        "success": True,
        "data": insights
    }


@router.post("/organizations/{organization_id}/workflow-rules", response_model=WorkflowRuleResponse)
async def create_workflow_rule(
    organization_id: UUID,
    rule_data: WorkflowRuleCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new workflow automation rule"""
    # Check if user is admin/owner of the organization
    member = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == organization_id,
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.role.in_(['owner', 'admin'])
    ).first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners and admins can create workflow rules"
        )
    
    rule = WorkflowRule(
        organization_id=organization_id,
        project_id=rule_data.project_id,
        rule_name=rule_data.rule_name,
        description=rule_data.description,
        trigger_type=rule_data.trigger_type,
        trigger_conditions=rule_data.trigger_conditions,
        actions=rule_data.actions,
        priority=rule_data.priority,
        created_by=current_user.id
    )
    
    db.add(rule)
    db.commit()
    db.refresh(rule)
    
    return rule


@router.get("/organizations/{organization_id}/workflow-rules", response_model=List[WorkflowRuleResponse])
async def get_workflow_rules(
    organization_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all workflow rules for organization"""
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
    
    rules = db.query(WorkflowRule).filter(
        WorkflowRule.organization_id == organization_id
    ).order_by(WorkflowRule.priority.desc(), WorkflowRule.created_at.desc()).all()
    
    return rules


@router.put("/organizations/{organization_id}/workflow-rules/{rule_id}/toggle")
async def toggle_workflow_rule(
    organization_id: UUID,
    rule_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Toggle workflow rule active status"""
    # Check if user is admin/owner of the organization
    member = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == organization_id,
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.role.in_(['owner', 'admin'])
    ).first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners and admins can modify workflow rules"
        )
    
    rule = db.query(WorkflowRule).filter(
        WorkflowRule.id == rule_id,
        WorkflowRule.organization_id == organization_id
    ).first()
    
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow rule not found"
        )
    
    rule.is_active = not rule.is_active
    db.commit()
    
    return {"message": f"Workflow rule {'activated' if rule.is_active else 'deactivated'} successfully"}


@router.post("/organizations/{organization_id}/ai/predict")
async def get_ai_prediction(
    organization_id: UUID,
    prediction_request: Dict[str, Any],
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get AI prediction for an entity"""
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
    
    ai_service = AIService(db)
    
    # Process prediction in background
    background_tasks.add_task(
        ai_service.generate_prediction,
        organization_id,
        prediction_request.get('entity_type'),
        prediction_request.get('entity_id'),
        prediction_request.get('prediction_type'),
        prediction_request.get('input_data', {})
    )
    
    return {"message": "Prediction request submitted", "status": "processing"}


@router.get("/organizations/{organization_id}/ai/predictions", response_model=List[AIPredictionResponse])
async def get_ai_predictions(
    organization_id: UUID,
    entity_type: Optional[str] = None,
    entity_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get AI predictions for organization"""
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
    
    query = db.query(AIPrediction).filter(
        AIPrediction.organization_id == organization_id
    )
    
    if entity_type:
        query = query.filter(AIPrediction.entity_type == entity_type)
    
    if entity_id:
        query = query.filter(AIPrediction.entity_id == entity_id)
    
    predictions = query.order_by(AIPrediction.created_at.desc()).limit(100).all()
    
    return predictions


@router.get("/organizations/{organization_id}/smart-notifications", response_model=List[SmartNotificationResponse])
async def get_smart_notifications(
    organization_id: UUID,
    unread_only: bool = False,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get smart notifications for user"""
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
    
    query = db.query(SmartNotification).filter(
        SmartNotification.organization_id == organization_id,
        SmartNotification.user_id == current_user.id
    )
    
    if unread_only:
        query = query.filter(SmartNotification.read_at.is_(None))
    
    notifications = query.order_by(SmartNotification.created_at.desc()).limit(50).all()
    
    return notifications


@router.put("/organizations/{organization_id}/smart-notifications/{notification_id}/read")
async def mark_notification_read(
    organization_id: UUID,
    notification_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Mark smart notification as read"""
    notification = db.query(SmartNotification).filter(
        SmartNotification.id == notification_id,
        SmartNotification.organization_id == organization_id,
        SmartNotification.user_id == current_user.id
    ).first()
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    notification.read_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Notification marked as read"}


@router.post("/organizations/{organization_id}/custom-fields", response_model=CustomFieldResponse)
async def create_custom_field(
    organization_id: UUID,
    field_data: CustomFieldCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a custom field"""
    # Check if user is admin/owner of the organization
    member = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == organization_id,
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.role.in_(['owner', 'admin'])
    ).first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners and admins can create custom fields"
        )
    
    custom_field = CustomField(
        organization_id=organization_id,
        field_name=field_data.field_name,
        field_type=field_data.field_type,
        entity_type=field_data.entity_type,
        description=field_data.description,
        field_options=field_data.field_options,
        validation_rules=field_data.validation_rules,
        is_required=field_data.is_required,
        is_searchable=field_data.is_searchable,
        display_order=field_data.display_order,
        created_by=current_user.id
    )
    
    db.add(custom_field)
    db.commit()
    db.refresh(custom_field)
    
    return custom_field


@router.get("/organizations/{organization_id}/custom-fields", response_model=List[CustomFieldResponse])
async def get_custom_fields(
    organization_id: UUID,
    entity_type: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get custom fields for organization"""
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
    
    query = db.query(CustomField).filter(
        CustomField.organization_id == organization_id,
        CustomField.is_active == True
    )
    
    if entity_type:
        query = query.filter(CustomField.entity_type == entity_type)
    
    fields = query.order_by(CustomField.display_order, CustomField.field_name).all()
    
    return fields


@router.get("/automation-templates", response_model=List[AutomationTemplateResponse])
async def get_automation_templates(
    category: Optional[str] = None,
    featured_only: bool = False,
    db: Session = Depends(get_db)
):
    """Get automation templates"""
    try:
        # Initialize default templates if none exist
        existing_count = db.query(AutomationTemplate).count()
        if existing_count == 0:
            await _initialize_default_automation_templates(db)

        query = db.query(AutomationTemplate).filter(
            AutomationTemplate.is_public == True
        )

        if category:
            query = query.filter(AutomationTemplate.category == category)

        if featured_only:
            query = query.filter(AutomationTemplate.is_featured == True)

        templates = query.order_by(
            AutomationTemplate.is_featured.desc(),
            AutomationTemplate.rating.desc(),
            AutomationTemplate.usage_count.desc()
        ).all()

        return templates
    except Exception as e:
        # Return default templates if database query fails
        return _get_default_automation_templates(category, featured_only)


@router.post("/organizations/{organization_id}/automation-templates/{template_id}/apply")
async def apply_automation_template(
    organization_id: UUID,
    template_id: UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    customizations: Optional[Dict[str, Any]] = None
):
    """Apply an automation template to organization"""
    # Check if user is admin/owner of the organization
    member = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == organization_id,
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.role.in_(['owner', 'admin'])
    ).first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners and admins can apply automation templates"
        )
    
    template = db.query(AutomationTemplate).filter(
        AutomationTemplate.id == template_id,
        AutomationTemplate.is_public == True
    ).first()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Automation template not found"
        )
    
    # Apply template in background
    automation_service = AutomationService(db)
    background_tasks.add_task(
        automation_service.apply_template,
        organization_id,
        template_id,
        current_user.id,
        customizations or {}
    )
    
    # Update usage count
    template.usage_count += 1
    db.commit()
    
    return {"message": "Automation template is being applied", "status": "processing"}


@router.get("/organizations/{organization_id}/ai-insights", response_model=List[AIInsightResponse])
async def get_ai_insights(
    organization_id: UUID,
    insight_type: Optional[str] = None,
    active_only: bool = True,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get AI insights for organization"""
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
    
    query = db.query(AIInsight).filter(
        AIInsight.organization_id == organization_id
    )
    
    if insight_type:
        query = query.filter(AIInsight.insight_type == insight_type)
    
    if active_only:
        query = query.filter(AIInsight.is_dismissed == False)
    
    insights = query.order_by(
        AIInsight.impact_score.desc(),
        AIInsight.confidence_level.desc(),
        AIInsight.created_at.desc()
    ).limit(20).all()
    
    return insights


@router.put("/organizations/{organization_id}/ai-insights/{insight_id}/dismiss")
async def dismiss_ai_insight(
    organization_id: UUID,
    insight_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Dismiss an AI insight"""
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
    
    insight = db.query(AIInsight).filter(
        AIInsight.id == insight_id,
        AIInsight.organization_id == organization_id
    ).first()
    
    if not insight:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI insight not found"
        )
    
    insight.is_dismissed = True
    insight.dismissed_by = current_user.id
    insight.dismissed_at = datetime.utcnow()
    db.commit()
    
    return {"message": "AI insight dismissed successfully"}


async def _initialize_default_automation_templates(db: Session):
    """Initialize default automation templates"""
    default_templates = [
        {
            "name": "Auto-assign High Priority Tasks",
            "description": "Automatically assign high priority tasks to available team members",
            "category": "task_management",
            "trigger_type": "card_created",
            "trigger_conditions": {"priority": "high"},
            "actions": [{"type": "assign_user", "criteria": "least_busy"}],
            "is_public": True,
            "is_featured": True,
            "rating": 4.5,
            "usage_count": 0
        },
        {
            "name": "Deadline Reminder Notifications",
            "description": "Send notifications when tasks are approaching deadlines",
            "category": "notifications",
            "trigger_type": "scheduled",
            "trigger_conditions": {"days_before_due": 2},
            "actions": [{"type": "send_notification", "template": "deadline_reminder"}],
            "is_public": True,
            "is_featured": True,
            "rating": 4.8,
            "usage_count": 0
        },
        {
            "name": "Project Status Updates",
            "description": "Automatically update project status based on task completion",
            "category": "project_management",
            "trigger_type": "card_status_changed",
            "trigger_conditions": {"status": "completed"},
            "actions": [{"type": "update_project_progress"}],
            "is_public": True,
            "is_featured": False,
            "rating": 4.2,
            "usage_count": 0
        }
    ]

    for template_data in default_templates:
        template = AutomationTemplate(**template_data)
        db.add(template)

    db.commit()


def _get_default_automation_templates(category: Optional[str] = None, featured_only: bool = False):
    """Get default automation templates as fallback"""
    templates = [
        {
            "id": "auto-assign-high-priority",
            "name": "Auto-assign High Priority Tasks",
            "description": "Automatically assign high priority tasks to available team members",
            "category": "task_management",
            "trigger_type": "card_created",
            "trigger_conditions": {"priority": "high"},
            "actions": [{"type": "assign_user", "criteria": "least_busy"}],
            "is_public": True,
            "is_featured": True,
            "rating": 4.5,
            "usage_count": 0,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "id": "deadline-reminders",
            "name": "Deadline Reminder Notifications",
            "description": "Send notifications when tasks are approaching deadlines",
            "category": "notifications",
            "trigger_type": "scheduled",
            "trigger_conditions": {"days_before_due": 2},
            "actions": [{"type": "send_notification", "template": "deadline_reminder"}],
            "is_public": True,
            "is_featured": True,
            "rating": 4.8,
            "usage_count": 0,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "id": "project-status-updates",
            "name": "Project Status Updates",
            "description": "Automatically update project status based on task completion",
            "category": "project_management",
            "trigger_type": "card_status_changed",
            "trigger_conditions": {"status": "completed"},
            "actions": [{"type": "update_project_progress"}],
            "is_public": True,
            "is_featured": False,
            "rating": 4.2,
            "usage_count": 0,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    ]

    if category:
        templates = [t for t in templates if t["category"] == category]

    if featured_only:
        templates = [t for t in templates if t["is_featured"]]

    return templates
