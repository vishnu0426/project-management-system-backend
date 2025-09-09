"""
AI and automation models
"""
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Boolean, Integer, Float
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class WorkflowRule(Base):
    __tablename__ = "workflow_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey('projects.id', ondelete='CASCADE'), nullable=True)
    rule_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    trigger_type = Column(String(50), nullable=False)  # card_created, card_updated, due_date_approaching, etc.
    trigger_conditions = Column(JSON, nullable=False)  # Conditions that must be met
    actions = Column(JSON, nullable=False)  # Actions to perform when triggered
    is_active = Column(Boolean, default=True, nullable=False)
    priority = Column(Integer, default=1, nullable=False)  # Rule execution priority
    execution_count = Column(Integer, default=0, nullable=False)
    last_executed = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    organization = relationship("Organization")
    project = relationship("Project")
    creator = relationship("User", foreign_keys=[created_by])
    executions = relationship("WorkflowExecution", back_populates="rule", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<WorkflowRule(id={self.id}, name={self.rule_name}, active={self.is_active})>"


class WorkflowExecution(Base):
    __tablename__ = "workflow_executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_id = Column(UUID(as_uuid=True), ForeignKey('workflow_rules.id', ondelete='CASCADE'), nullable=False)
    trigger_data = Column(JSON, nullable=False)  # Data that triggered the rule
    execution_status = Column(String(50), default='pending', nullable=False)  # pending, running, completed, failed
    actions_performed = Column(JSON, nullable=True)  # Actions that were performed
    execution_results = Column(JSON, nullable=True)  # Results of each action
    error_details = Column(JSON, nullable=True)  # Error information if failed
    execution_time_ms = Column(Integer, nullable=True)  # Execution time in milliseconds
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    rule = relationship("WorkflowRule", back_populates="executions")

    def __repr__(self):
        return f"<WorkflowExecution(id={self.id}, rule_id={self.rule_id}, status={self.execution_status})>"


class AIModel(Base):
    __tablename__ = "ai_models"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_name = Column(String(255), nullable=False)
    model_type = Column(String(50), nullable=False)  # text_classification, priority_prediction, sentiment_analysis
    model_version = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    configuration = Column(JSON, nullable=False)  # Model configuration and parameters
    training_data_info = Column(JSON, nullable=True)  # Information about training data
    performance_metrics = Column(JSON, nullable=True)  # Model performance metrics
    is_active = Column(Boolean, default=True, nullable=False)
    is_trained = Column(Boolean, default=False, nullable=False)
    last_trained = Column(DateTime(timezone=True), nullable=True)
    usage_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    predictions = relationship("AIPrediction", back_populates="model", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<AIModel(id={self.id}, name={self.model_name}, type={self.model_type})>"


class AIPrediction(Base):
    __tablename__ = "ai_predictions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_id = Column(UUID(as_uuid=True), ForeignKey('ai_models.id', ondelete='CASCADE'), nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    entity_type = Column(String(50), nullable=False)  # card, project, user
    entity_id = Column(UUID(as_uuid=True), nullable=False)  # ID of the entity being predicted
    prediction_type = Column(String(50), nullable=False)  # priority, completion_time, risk_level
    input_data = Column(JSON, nullable=False)  # Input data used for prediction
    prediction_result = Column(JSON, nullable=False)  # Prediction results
    confidence_score = Column(Float, nullable=True)  # Confidence level (0-1)
    is_accepted = Column(Boolean, nullable=True)  # Whether user accepted the prediction
    feedback_score = Column(Integer, nullable=True)  # User feedback (1-5)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    model = relationship("AIModel", back_populates="predictions")
    organization = relationship("Organization")

    def __repr__(self):
        return f"<AIPrediction(id={self.id}, type={self.prediction_type}, confidence={self.confidence_score})>"


class SmartNotification(Base):
    __tablename__ = "smart_notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    notification_type = Column(String(50), nullable=False)  # smart_reminder, priority_alert, deadline_warning
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    priority = Column(String(20), default='medium', nullable=False)  # low, medium, high, urgent
    context_data = Column(JSON, nullable=True)  # Additional context for the notification
    ai_generated = Column(Boolean, default=False, nullable=False)  # Whether this was AI-generated
    personalization_score = Column(Float, nullable=True)  # How personalized this notification is
    delivery_method = Column(String(50), default='in_app', nullable=False)  # in_app, email, push, sms
    scheduled_for = Column(DateTime(timezone=True), nullable=True)  # When to deliver the notification
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    read_at = Column(DateTime(timezone=True), nullable=True)
    action_taken = Column(String(100), nullable=True)  # Action user took in response
    effectiveness_score = Column(Float, nullable=True)  # How effective the notification was
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    organization = relationship("Organization")
    user = relationship("User", foreign_keys=[user_id])

    def __repr__(self):
        return f"<SmartNotification(id={self.id}, type={self.notification_type}, priority={self.priority})>"


class CustomField(Base):
    __tablename__ = "custom_fields"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    field_name = Column(String(255), nullable=False)
    field_type = Column(String(50), nullable=False)  # text, number, date, select, multi_select, boolean
    entity_type = Column(String(50), nullable=False)  # card, project, user
    description = Column(Text, nullable=True)
    field_options = Column(JSON, nullable=True)  # Options for select fields
    validation_rules = Column(JSON, nullable=True)  # Validation rules
    is_required = Column(Boolean, default=False, nullable=False)
    is_searchable = Column(Boolean, default=True, nullable=False)
    display_order = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    organization = relationship("Organization")
    creator = relationship("User", foreign_keys=[created_by])
    values = relationship("CustomFieldValue", back_populates="field", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<CustomField(id={self.id}, name={self.field_name}, type={self.field_type})>"


class CustomFieldValue(Base):
    __tablename__ = "custom_field_values"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    field_id = Column(UUID(as_uuid=True), ForeignKey('custom_fields.id', ondelete='CASCADE'), nullable=False)
    entity_id = Column(UUID(as_uuid=True), nullable=False)  # ID of the entity (card, project, user)
    value_text = Column(Text, nullable=True)  # Text value
    value_number = Column(Float, nullable=True)  # Numeric value
    value_date = Column(DateTime(timezone=True), nullable=True)  # Date value
    value_boolean = Column(Boolean, nullable=True)  # Boolean value
    value_json = Column(JSON, nullable=True)  # JSON value for complex data
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    field = relationship("CustomField", back_populates="values")

    def __repr__(self):
        return f"<CustomFieldValue(id={self.id}, field_id={self.field_id}, entity_id={self.entity_id})>"


class AutomationTemplate(Base):
    __tablename__ = "automation_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False)  # project_management, notifications, integrations
    description = Column(Text, nullable=True)
    template_data = Column(JSON, nullable=False)  # Template configuration
    use_cases = Column(JSON, nullable=True)  # Common use cases
    is_public = Column(Boolean, default=True, nullable=False)
    is_featured = Column(Boolean, default=False, nullable=False)
    usage_count = Column(Integer, default=0, nullable=False)
    rating = Column(Float, default=0.0, nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    creator = relationship("User", foreign_keys=[created_by])

    def __repr__(self):
        return f"<AutomationTemplate(id={self.id}, name={self.template_name}, category={self.category})>"


class AIInsight(Base):
    __tablename__ = "ai_insights"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    insight_type = Column(String(50), nullable=False)  # productivity, bottleneck, trend, recommendation
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    insight_data = Column(JSON, nullable=False)  # Detailed insight data
    confidence_level = Column(Float, nullable=False)  # Confidence in the insight (0-1)
    impact_score = Column(Float, nullable=True)  # Potential impact score (0-10)
    actionable_items = Column(JSON, nullable=True)  # Suggested actions
    related_entities = Column(JSON, nullable=True)  # Related projects, users, etc.
    is_dismissed = Column(Boolean, default=False, nullable=False)
    dismissed_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    dismissed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    organization = relationship("Organization")
    dismisser = relationship("User", foreign_keys=[dismissed_by])

    def __repr__(self):
        return f"<AIInsight(id={self.id}, type={self.insight_type}, confidence={self.confidence_level})>"


class AIGeneratedProject(Base):
    __tablename__ = "ai_generated_projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)

    # AI Generation metadata
    generation_prompt = Column(Text, nullable=True)  # Original prompt used
    ai_model_used = Column(String(100), nullable=False)  # e.g., "gpt-4"
    generation_parameters = Column(JSON, nullable=True)  # Parameters used for generation

    # Generated content
    ai_description = Column(Text, nullable=True)  # AI-generated description
    ai_overview = Column(JSON, nullable=True)  # AI-generated overview data
    ai_objectives = Column(JSON, nullable=True)  # AI-generated objectives
    ai_success_criteria = Column(JSON, nullable=True)  # AI-generated success criteria
    ai_tech_stack = Column(JSON, nullable=True)  # AI-suggested technology stack
    ai_workflow = Column(JSON, nullable=True)  # AI-generated workflow
    ai_tasks = Column(JSON, nullable=True)  # AI-generated tasks
    ai_suggestions = Column(JSON, nullable=True)  # AI-generated suggestions

    # Quality metrics
    generation_quality_score = Column(Float, nullable=True)  # Quality assessment (0-1)
    user_satisfaction_score = Column(Integer, nullable=True)  # User feedback (1-5)
    modifications_made = Column(JSON, nullable=True)  # User modifications to AI content

    # Generation process metadata
    generation_time_ms = Column(Integer, nullable=True)  # Time taken to generate
    tokens_used = Column(Integer, nullable=True)  # OpenAI tokens consumed
    generation_cost = Column(Float, nullable=True)  # Cost of generation
    fallback_used = Column(Boolean, default=False, nullable=False)  # Whether fallback was used

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    project = relationship("Project")
    organization = relationship("Organization")
    user = relationship("User", foreign_keys=[user_id])

    def __repr__(self):
        return f"<AIGeneratedProject(id={self.id}, project_id={self.project_id}, model={self.ai_model_used})>"
