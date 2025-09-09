"""
Automation service for workflow rules and smart notifications
"""
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from app.models.ai_automation import (
    WorkflowRule, WorkflowExecution, SmartNotification, 
    AutomationTemplate, CustomField, CustomFieldValue
)
from app.models.card import Card
from app.models.project import Project
from app.models.user import User
from app.models.organization import Organization, OrganizationMember
from app.models.activity_log import ActivityLog

logger = logging.getLogger(__name__)


class AutomationService:
    """Service for workflow automation and smart notifications"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def process_trigger(
        self,
        organization_id: str,
        trigger_type: str,
        trigger_data: Dict[str, Any]
    ) -> List[WorkflowExecution]:
        """Process a trigger event and execute matching workflow rules"""
        executions = []
        
        try:
            # Find matching workflow rules
            rules = self.db.query(WorkflowRule).filter(
                WorkflowRule.organization_id == organization_id,
                WorkflowRule.trigger_type == trigger_type,
                WorkflowRule.is_active == True
            ).order_by(WorkflowRule.priority.desc()).all()
            
            for rule in rules:
                if self._evaluate_conditions(rule.trigger_conditions, trigger_data):
                    execution = await self._execute_workflow_rule(rule, trigger_data)
                    if execution:
                        executions.append(execution)
            
            logger.info(f"Processed {trigger_type} trigger, executed {len(executions)} rules")
            
        except Exception as e:
            logger.error(f"Error processing trigger {trigger_type}: {e}")
        
        return executions
    
    def _evaluate_conditions(self, conditions: Dict[str, Any], trigger_data: Dict[str, Any]) -> bool:
        """Evaluate if trigger data meets rule conditions"""
        try:
            for condition_key, condition_value in conditions.items():
                if condition_key not in trigger_data:
                    return False
                
                trigger_value = trigger_data[condition_key]
                
                # Handle different condition types
                if isinstance(condition_value, dict):
                    operator = condition_value.get('operator', 'equals')
                    expected_value = condition_value.get('value')
                    
                    if operator == 'equals' and trigger_value != expected_value:
                        return False
                    elif operator == 'not_equals' and trigger_value == expected_value:
                        return False
                    elif operator == 'contains' and expected_value not in str(trigger_value):
                        return False
                    elif operator == 'greater_than' and trigger_value <= expected_value:
                        return False
                    elif operator == 'less_than' and trigger_value >= expected_value:
                        return False
                    elif operator == 'in' and trigger_value not in expected_value:
                        return False
                else:
                    # Simple equality check
                    if trigger_value != condition_value:
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error evaluating conditions: {e}")
            return False
    
    async def _execute_workflow_rule(
        self,
        rule: WorkflowRule,
        trigger_data: Dict[str, Any]
    ) -> Optional[WorkflowExecution]:
        """Execute a workflow rule"""
        try:
            # Create execution record
            execution = WorkflowExecution(
                rule_id=rule.id,
                trigger_data=trigger_data,
                execution_status='running'
            )
            
            self.db.add(execution)
            self.db.flush()
            
            start_time = datetime.utcnow()
            actions_performed = []
            execution_results = {}
            
            # Execute each action
            for action in rule.actions:
                try:
                    result = await self._execute_action(action, trigger_data, rule.organization_id)
                    actions_performed.append(action)
                    execution_results[action.get('action_type', 'unknown')] = result
                except Exception as e:
                    logger.error(f"Error executing action {action}: {e}")
                    execution_results[action.get('action_type', 'unknown')] = {'error': str(e)}
            
            # Update execution record
            end_time = datetime.utcnow()
            execution.execution_status = 'completed'
            execution.actions_performed = actions_performed
            execution.execution_results = execution_results
            execution.execution_time_ms = int((end_time - start_time).total_seconds() * 1000)
            execution.completed_at = end_time
            
            # Update rule statistics
            rule.execution_count += 1
            rule.last_executed = end_time
            
            self.db.commit()
            
            logger.info(f"Executed workflow rule {rule.rule_name} successfully")
            return execution
            
        except Exception as e:
            logger.error(f"Error executing workflow rule {rule.rule_name}: {e}")
            
            # Update execution with error
            if execution:
                execution.execution_status = 'failed'
                execution.error_details = {'error': str(e)}
                execution.completed_at = datetime.utcnow()
                self.db.commit()
            
            return execution
    
    async def _execute_action(
        self,
        action: Dict[str, Any],
        trigger_data: Dict[str, Any],
        organization_id: str
    ) -> Dict[str, Any]:
        """Execute a specific action"""
        action_type = action.get('action_type')
        parameters = action.get('parameters', {})
        
        if action_type == 'assign_user':
            return await self._action_assign_user(parameters, trigger_data, organization_id)
        elif action_type == 'change_status':
            return await self._action_change_status(parameters, trigger_data, organization_id)
        elif action_type == 'set_priority':
            return await self._action_set_priority(parameters, trigger_data, organization_id)
        elif action_type == 'send_notification':
            return await self._action_send_notification(parameters, trigger_data, organization_id)
        elif action_type == 'create_card':
            return await self._action_create_card(parameters, trigger_data, organization_id)
        elif action_type == 'update_field':
            return await self._action_update_field(parameters, trigger_data, organization_id)
        else:
            raise ValueError(f"Unknown action type: {action_type}")
    
    async def _action_assign_user(
        self,
        parameters: Dict[str, Any],
        trigger_data: Dict[str, Any],
        organization_id: str
    ) -> Dict[str, Any]:
        """Assign user to a card"""
        card_id = trigger_data.get('card_id') or parameters.get('card_id')
        user_id = parameters.get('user_id')
        
        if not card_id or not user_id:
            raise ValueError("Missing card_id or user_id for assign_user action")
        
        card = self.db.query(Card).filter(Card.id == card_id).first()
        if not card:
            raise ValueError(f"Card {card_id} not found")
        
        # Verify user is member of organization
        member = self.db.query(OrganizationMember).filter(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == user_id
        ).first()
        
        if not member:
            raise ValueError(f"User {user_id} is not a member of organization")
        
        card.assigned_to = user_id
        self.db.commit()
        
        return {'success': True, 'card_id': str(card_id), 'assigned_to': str(user_id)}
    
    async def _action_change_status(
        self,
        parameters: Dict[str, Any],
        trigger_data: Dict[str, Any],
        organization_id: str
    ) -> Dict[str, Any]:
        """Change card status"""
        card_id = trigger_data.get('card_id') or parameters.get('card_id')
        new_status = parameters.get('status')
        
        if not card_id or not new_status:
            raise ValueError("Missing card_id or status for change_status action")
        
        card = self.db.query(Card).filter(Card.id == card_id).first()
        if not card:
            raise ValueError(f"Card {card_id} not found")
        
        old_status = card.status
        card.status = new_status
        self.db.commit()
        
        return {
            'success': True,
            'card_id': str(card_id),
            'old_status': old_status,
            'new_status': new_status
        }
    
    async def _action_set_priority(
        self,
        parameters: Dict[str, Any],
        trigger_data: Dict[str, Any],
        organization_id: str
    ) -> Dict[str, Any]:
        """Set card priority"""
        card_id = trigger_data.get('card_id') or parameters.get('card_id')
        new_priority = parameters.get('priority')
        
        if not card_id or not new_priority:
            raise ValueError("Missing card_id or priority for set_priority action")
        
        card = self.db.query(Card).filter(Card.id == card_id).first()
        if not card:
            raise ValueError(f"Card {card_id} not found")
        
        old_priority = card.priority
        card.priority = new_priority
        self.db.commit()
        
        return {
            'success': True,
            'card_id': str(card_id),
            'old_priority': old_priority,
            'new_priority': new_priority
        }
    
    async def _action_send_notification(
        self,
        parameters: Dict[str, Any],
        trigger_data: Dict[str, Any],
        organization_id: str
    ) -> Dict[str, Any]:
        """Send smart notification"""
        user_id = parameters.get('user_id') or trigger_data.get('user_id')
        message_template = parameters.get('message', 'Automated notification')
        title_template = parameters.get('title', 'Workflow Notification')
        priority = parameters.get('priority', 'medium')
        
        if not user_id:
            raise ValueError("Missing user_id for send_notification action")
        
        # Replace placeholders in message and title
        message = self._replace_placeholders(message_template, trigger_data)
        title = self._replace_placeholders(title_template, trigger_data)
        
        notification = SmartNotification(
            organization_id=organization_id,
            user_id=user_id,
            notification_type='workflow_automation',
            title=title,
            message=message,
            priority=priority,
            context_data=trigger_data,
            ai_generated=False,
            delivery_method='in_app'
        )
        
        self.db.add(notification)
        self.db.commit()
        
        return {
            'success': True,
            'notification_id': str(notification.id),
            'user_id': str(user_id),
            'message': message
        }
    
    async def _action_create_card(
        self,
        parameters: Dict[str, Any],
        trigger_data: Dict[str, Any],
        organization_id: str
    ) -> Dict[str, Any]:
        """Create a new card"""
        project_id = parameters.get('project_id') or trigger_data.get('project_id')
        title_template = parameters.get('title', 'Automated Task')
        description_template = parameters.get('description', '')
        
        if not project_id:
            raise ValueError("Missing project_id for create_card action")
        
        # Verify project exists and belongs to organization
        project = self.db.query(Project).filter(
            Project.id == project_id,
            Project.organization_id == organization_id
        ).first()
        
        if not project:
            raise ValueError(f"Project {project_id} not found in organization")
        
        # Replace placeholders
        title = self._replace_placeholders(title_template, trigger_data)
        description = self._replace_placeholders(description_template, trigger_data)
        
        card = Card(
            project_id=project_id,
            title=title,
            description=description,
            status=parameters.get('status', 'todo'),
            priority=parameters.get('priority', 'medium'),
            assigned_to=parameters.get('assigned_to')
        )
        
        self.db.add(card)
        self.db.commit()
        self.db.refresh(card)
        
        return {
            'success': True,
            'card_id': str(card.id),
            'title': title,
            'project_id': str(project_id)
        }
    
    async def _action_update_field(
        self,
        parameters: Dict[str, Any],
        trigger_data: Dict[str, Any],
        organization_id: str
    ) -> Dict[str, Any]:
        """Update a custom field value"""
        entity_id = trigger_data.get('card_id') or parameters.get('entity_id')
        field_name = parameters.get('field_name')
        field_value = parameters.get('field_value')
        
        if not entity_id or not field_name:
            raise ValueError("Missing entity_id or field_name for update_field action")
        
        # Find custom field
        custom_field = self.db.query(CustomField).filter(
            CustomField.organization_id == organization_id,
            CustomField.field_name == field_name,
            CustomField.is_active == True
        ).first()
        
        if not custom_field:
            raise ValueError(f"Custom field {field_name} not found")
        
        # Update or create field value
        field_value_record = self.db.query(CustomFieldValue).filter(
            CustomFieldValue.field_id == custom_field.id,
            CustomFieldValue.entity_id == entity_id
        ).first()
        
        if field_value_record:
            # Update existing value
            self._set_field_value(field_value_record, custom_field.field_type, field_value)
        else:
            # Create new value
            field_value_record = CustomFieldValue(
                field_id=custom_field.id,
                entity_id=entity_id
            )
            self._set_field_value(field_value_record, custom_field.field_type, field_value)
            self.db.add(field_value_record)
        
        self.db.commit()
        
        return {
            'success': True,
            'entity_id': str(entity_id),
            'field_name': field_name,
            'field_value': field_value
        }
    
    def _set_field_value(self, field_value_record: CustomFieldValue, field_type: str, value: Any):
        """Set the appropriate field value based on field type"""
        # Clear all values first
        field_value_record.value_text = None
        field_value_record.value_number = None
        field_value_record.value_date = None
        field_value_record.value_boolean = None
        field_value_record.value_json = None
        
        if field_type == 'text':
            field_value_record.value_text = str(value)
        elif field_type == 'number':
            field_value_record.value_number = float(value)
        elif field_type == 'date':
            if isinstance(value, str):
                field_value_record.value_date = datetime.fromisoformat(value.replace('Z', '+00:00'))
            else:
                field_value_record.value_date = value
        elif field_type == 'boolean':
            field_value_record.value_boolean = bool(value)
        else:
            field_value_record.value_json = value if isinstance(value, (dict, list)) else {'value': value}
    
    def _replace_placeholders(self, template: str, data: Dict[str, Any]) -> str:
        """Replace placeholders in template with actual data"""
        result = template
        
        for key, value in data.items():
            placeholder = f"{{{key}}}"
            if placeholder in result:
                result = result.replace(placeholder, str(value))
        
        return result
    
    async def apply_template(
        self,
        organization_id: str,
        template_id: str,
        user_id: str,
        customizations: Dict[str, Any]
    ) -> bool:
        """Apply an automation template to organization"""
        try:
            template = self.db.query(AutomationTemplate).filter(
                AutomationTemplate.id == template_id,
                AutomationTemplate.is_public == True
            ).first()
            
            if not template:
                logger.error(f"Template {template_id} not found")
                return False
            
            template_data = template.template_data
            
            # Apply customizations
            if customizations:
                template_data = self._apply_customizations(template_data, customizations)
            
            # Create workflow rules from template
            rules_created = 0
            
            for rule_config in template_data.get('rules', []):
                rule = WorkflowRule(
                    organization_id=organization_id,
                    rule_name=rule_config.get('name'),
                    description=rule_config.get('description'),
                    trigger_type=rule_config.get('trigger_type'),
                    trigger_conditions=rule_config.get('trigger_conditions', {}),
                    actions=rule_config.get('actions', []),
                    priority=rule_config.get('priority', 1),
                    created_by=user_id
                )
                
                self.db.add(rule)
                rules_created += 1
            
            # Create custom fields from template
            fields_created = 0
            
            for field_config in template_data.get('custom_fields', []):
                field = CustomField(
                    organization_id=organization_id,
                    field_name=field_config.get('name'),
                    field_type=field_config.get('type'),
                    entity_type=field_config.get('entity_type'),
                    description=field_config.get('description'),
                    field_options=field_config.get('options'),
                    is_required=field_config.get('required', False),
                    created_by=user_id
                )
                
                self.db.add(field)
                fields_created += 1
            
            self.db.commit()
            
            logger.info(f"Applied template {template.template_name}: {rules_created} rules, {fields_created} fields")
            return True
            
        except Exception as e:
            logger.error(f"Error applying template {template_id}: {e}")
            self.db.rollback()
            return False
    
    def _apply_customizations(self, template_data: Dict[str, Any], customizations: Dict[str, Any]) -> Dict[str, Any]:
        """Apply user customizations to template data"""
        # Simple customization logic - in a real implementation, this would be more sophisticated
        result = template_data.copy()
        
        # Apply rule customizations
        if 'rules' in customizations:
            for i, rule_custom in enumerate(customizations['rules']):
                if i < len(result.get('rules', [])):
                    result['rules'][i].update(rule_custom)
        
        # Apply field customizations
        if 'custom_fields' in customizations:
            for i, field_custom in enumerate(customizations['custom_fields']):
                if i < len(result.get('custom_fields', [])):
                    result['custom_fields'][i].update(field_custom)
        
        return result
