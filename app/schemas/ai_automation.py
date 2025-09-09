"""
Schemas for AI and automation features
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from uuid import UUID


class WorkflowRuleCreate(BaseModel):
    rule_name: str = Field(max_length=255)
    description: Optional[str] = None
    project_id: Optional[UUID] = None
    trigger_type: str = Field(pattern="^(card_created|card_updated|card_completed|due_date_approaching|project_created|user_assigned)$")
    trigger_conditions: Dict[str, Any]
    actions: List[Dict[str, Any]]
    priority: int = Field(default=1, ge=1, le=10)


class WorkflowRuleResponse(BaseModel):
    id: UUID
    organization_id: UUID
    project_id: Optional[UUID] = None
    rule_name: str
    description: Optional[str] = None
    trigger_type: str
    trigger_conditions: Dict[str, Any]
    actions: List[Dict[str, Any]]
    is_active: bool
    priority: int
    execution_count: int
    last_executed: Optional[datetime] = None
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class WorkflowExecutionResponse(BaseModel):
    id: UUID
    rule_id: UUID
    trigger_data: Dict[str, Any]
    execution_status: str
    actions_performed: Optional[List[Dict[str, Any]]] = None
    execution_results: Optional[Dict[str, Any]] = None
    error_details: Optional[Dict[str, Any]] = None
    execution_time_ms: Optional[int] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class AIPredictionResponse(BaseModel):
    id: UUID
    model_id: UUID
    organization_id: UUID
    entity_type: str
    entity_id: UUID
    prediction_type: str
    input_data: Dict[str, Any]
    prediction_result: Dict[str, Any]
    confidence_score: Optional[float] = None
    is_accepted: Optional[bool] = None
    feedback_score: Optional[int] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class SmartNotificationResponse(BaseModel):
    id: UUID
    organization_id: UUID
    user_id: UUID
    notification_type: str
    title: str
    message: str
    priority: str
    context_data: Optional[Dict[str, Any]] = None
    ai_generated: bool
    personalization_score: Optional[float] = None
    delivery_method: str
    scheduled_for: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    action_taken: Optional[str] = None
    effectiveness_score: Optional[float] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class CustomFieldCreate(BaseModel):
    field_name: str = Field(max_length=255)
    field_type: str = Field(pattern="^(text|number|date|select|multi_select|boolean|url|email)$")
    entity_type: str = Field(pattern="^(card|project|user)$")
    description: Optional[str] = None
    field_options: Optional[List[str]] = None
    validation_rules: Optional[Dict[str, Any]] = None
    is_required: bool = False
    is_searchable: bool = True
    display_order: int = Field(default=0, ge=0)


class CustomFieldResponse(BaseModel):
    id: UUID
    organization_id: UUID
    field_name: str
    field_type: str
    entity_type: str
    description: Optional[str] = None
    field_options: Optional[List[str]] = None
    validation_rules: Optional[Dict[str, Any]] = None
    is_required: bool
    is_searchable: bool
    display_order: int
    is_active: bool
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class CustomFieldValueCreate(BaseModel):
    field_id: UUID
    entity_id: UUID
    value: Union[str, int, float, bool, datetime, List[str], Dict[str, Any]]


class CustomFieldValueResponse(BaseModel):
    id: UUID
    field_id: UUID
    entity_id: UUID
    value_text: Optional[str] = None
    value_number: Optional[float] = None
    value_date: Optional[datetime] = None
    value_boolean: Optional[bool] = None
    value_json: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class AutomationTemplateResponse(BaseModel):
    id: UUID
    template_name: str
    category: str
    description: Optional[str] = None
    template_data: Dict[str, Any]
    use_cases: Optional[List[str]] = None
    is_public: bool
    is_featured: bool
    usage_count: int
    rating: float
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class AIInsightResponse(BaseModel):
    id: UUID
    organization_id: UUID
    insight_type: str
    title: str
    description: str
    insight_data: Dict[str, Any]
    confidence_level: float
    impact_score: Optional[float] = None
    actionable_items: Optional[List[Dict[str, Any]]] = None
    related_entities: Optional[Dict[str, Any]] = None
    is_dismissed: bool
    dismissed_by: Optional[UUID] = None
    dismissed_at: Optional[datetime] = None
    created_at: datetime
    expires_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class AIModelResponse(BaseModel):
    id: UUID
    model_name: str
    model_type: str
    model_version: str
    description: Optional[str] = None
    configuration: Dict[str, Any]
    performance_metrics: Optional[Dict[str, Any]] = None
    is_active: bool
    is_trained: bool
    last_trained: Optional[datetime] = None
    usage_count: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class WorkflowTrigger(BaseModel):
    trigger_type: str
    conditions: Dict[str, Any]
    description: str


class WorkflowAction(BaseModel):
    action_type: str = Field(pattern="^(assign_user|change_status|set_priority|send_notification|create_card|update_field)$")
    parameters: Dict[str, Any]
    description: str


class AutomationRule(BaseModel):
    name: str
    description: Optional[str] = None
    trigger: WorkflowTrigger
    actions: List[WorkflowAction]
    conditions: Optional[List[Dict[str, Any]]] = None
    is_active: bool = True


class PredictionRequest(BaseModel):
    entity_type: str = Field(pattern="^(card|project|user)$")
    entity_id: UUID
    prediction_type: str = Field(pattern="^(priority|completion_time|risk_level|effort_estimate)$")
    input_data: Dict[str, Any]


class PredictionResult(BaseModel):
    prediction_type: str
    predicted_value: Union[str, int, float]
    confidence_score: float
    explanation: Optional[str] = None
    factors: Optional[List[Dict[str, Any]]] = None


class SmartNotificationCreate(BaseModel):
    user_id: UUID
    notification_type: str
    title: str
    message: str
    priority: str = Field(default="medium", pattern="^(low|medium|high|urgent)$")
    context_data: Optional[Dict[str, Any]] = None
    delivery_method: str = Field(default="in_app", pattern="^(in_app|email|push|sms)$")
    scheduled_for: Optional[datetime] = None


class AIInsightCreate(BaseModel):
    insight_type: str = Field(pattern="^(productivity|bottleneck|trend|recommendation|risk)$")
    title: str
    description: str
    insight_data: Dict[str, Any]
    confidence_level: float = Field(ge=0.0, le=1.0)
    impact_score: Optional[float] = Field(None, ge=0.0, le=10.0)
    actionable_items: Optional[List[Dict[str, Any]]] = None
    related_entities: Optional[Dict[str, Any]] = None
    expires_at: Optional[datetime] = None


class AutomationMetrics(BaseModel):
    organization_id: UUID
    total_rules: int
    active_rules: int
    total_executions: int
    successful_executions: int
    failed_executions: int
    average_execution_time_ms: float
    most_used_triggers: List[Dict[str, Any]]
    most_used_actions: List[Dict[str, Any]]
    time_saved_hours: float


class AIMetrics(BaseModel):
    organization_id: UUID
    total_predictions: int
    prediction_accuracy: float
    models_active: int
    insights_generated: int
    insights_acted_upon: int
    user_satisfaction_score: float
    processing_time_ms: float
