"""
AI service for intelligent features and predictions
"""
import logging
import json
import random
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from openai import OpenAI

from app.models.ai_automation import AIModel, AIPrediction, AIInsight, SmartNotification
from app.models.card import Card
from app.models.project import Project
from app.models.user import User
from app.models.organization import Organization, OrganizationMember
from app.models.activity_log import ActivityLog

logger = logging.getLogger(__name__)


class AIService:
    """Service for AI-powered features and predictions"""

    def __init__(self, db: Session):
        self.db = db
        # Initialize OpenAI client
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4")
        self.ai_enabled = os.getenv("AI_ENABLED", "True").lower() == "true"

        if self.ai_enabled and self.openai_api_key:
            self.openai_client = OpenAI(api_key=self.openai_api_key)
            logger.info(f"OpenAI initialized with model: {self.openai_model}")
        else:
            self.openai_client = None
            logger.warning("OpenAI not configured - using mock data generation")

    async def _call_openai_api(self, prompt: str, max_tokens: int = 2000) -> str:
        """Call OpenAI API with error handling"""
        if not self.ai_enabled or not self.openai_client:
            raise Exception("OpenAI API not configured")

        try:
            response = self.openai_client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {"role": "system", "content": "You are an expert project manager and software architect. Generate detailed, professional project plans in JSON format."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.7
            )

            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"OpenAI API call failed: {str(e)}")
            raise Exception(f"AI generation failed: {str(e)}")
    
    async def generate_prediction(
        self,
        organization_id: str,
        entity_type: str,
        entity_id: str,
        prediction_type: str,
        input_data: Dict[str, Any]
    ) -> Optional[AIPrediction]:
        """Generate AI prediction for an entity"""
        try:
            # Get appropriate AI model
            model = self._get_model_for_prediction(prediction_type)
            if not model:
                logger.warning(f"No model found for prediction type: {prediction_type}")
                return None
            
            # Generate prediction based on type
            if prediction_type == 'priority':
                result = await self._predict_priority(entity_type, entity_id, input_data)
            elif prediction_type == 'completion_time':
                result = await self._predict_completion_time(entity_type, entity_id, input_data)
            elif prediction_type == 'risk_level':
                result = await self._predict_risk_level(entity_type, entity_id, input_data)
            elif prediction_type == 'effort_estimate':
                result = await self._predict_effort_estimate(entity_type, entity_id, input_data)
            else:
                logger.warning(f"Unknown prediction type: {prediction_type}")
                return None
            
            # Create prediction record
            prediction = AIPrediction(
                model_id=model.id,
                organization_id=organization_id,
                entity_type=entity_type,
                entity_id=entity_id,
                prediction_type=prediction_type,
                input_data=input_data,
                prediction_result=result['prediction'],
                confidence_score=result['confidence']
            )
            
            self.db.add(prediction)
            self.db.commit()
            self.db.refresh(prediction)
            
            # Update model usage
            model.usage_count += 1
            self.db.commit()
            
            logger.info(f"Generated {prediction_type} prediction for {entity_type} {entity_id}")
            return prediction
            
        except Exception as e:
            logger.error(f"Error generating prediction: {e}")
            self.db.rollback()
            return None
    
    def _get_model_for_prediction(self, prediction_type: str) -> Optional[AIModel]:
        """Get the appropriate AI model for prediction type"""
        model = self.db.query(AIModel).filter(
            AIModel.model_type == prediction_type,
            AIModel.is_active == True,
            AIModel.is_trained == True
        ).first()
        
        if not model:
            # Create a default model if none exists
            model = self._create_default_model(prediction_type)
        
        return model
    
    def _create_default_model(self, prediction_type: str) -> AIModel:
        """Create a default AI model for prediction type"""
        model_configs = {
            'priority': {
                'name': 'Priority Prediction Model',
                'description': 'Predicts task priority based on content and context',
                'config': {'algorithm': 'ensemble', 'features': ['title', 'description', 'project', 'assignee']}
            },
            'completion_time': {
                'name': 'Completion Time Prediction Model',
                'description': 'Estimates task completion time based on historical data',
                'config': {'algorithm': 'regression', 'features': ['complexity', 'assignee_history', 'project_type']}
            },
            'risk_level': {
                'name': 'Risk Assessment Model',
                'description': 'Assesses project and task risk levels',
                'config': {'algorithm': 'classification', 'features': ['timeline', 'resources', 'dependencies']}
            },
            'effort_estimate': {
                'name': 'Effort Estimation Model',
                'description': 'Estimates effort required for tasks',
                'config': {'algorithm': 'regression', 'features': ['scope', 'complexity', 'team_experience']}
            }
        }
        
        config = model_configs.get(prediction_type, {})
        
        model = AIModel(
            model_name=config.get('name', f'{prediction_type.title()} Model'),
            model_type=prediction_type,
            model_version='1.0.0',
            description=config.get('description', f'Default {prediction_type} model'),
            configuration=config.get('config', {}),
            is_active=True,
            is_trained=True,  # Assume pre-trained for demo
            last_trained=datetime.utcnow()
        )
        
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        
        return model
    
    async def _predict_priority(self, entity_type: str, entity_id: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Predict priority for an entity"""
        # Simplified priority prediction logic
        # In a real implementation, this would use ML models
        
        priority_scores = {'low': 0, 'medium': 1, 'high': 2, 'urgent': 3}
        
        # Analyze input data
        score = 0
        confidence = 0.7
        
        # Check for urgency keywords
        text_content = f"{input_data.get('title', '')} {input_data.get('description', '')}".lower()
        urgency_keywords = ['urgent', 'asap', 'critical', 'emergency', 'immediate', 'deadline']
        high_priority_keywords = ['important', 'priority', 'key', 'essential', 'crucial']
        
        if any(keyword in text_content for keyword in urgency_keywords):
            score += 2
            confidence += 0.1
        elif any(keyword in text_content for keyword in high_priority_keywords):
            score += 1
            confidence += 0.05
        
        # Check due date proximity
        due_date = input_data.get('due_date')
        if due_date:
            try:
                due_datetime = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                days_until_due = (due_datetime - datetime.utcnow()).days
                
                if days_until_due <= 1:
                    score += 2
                elif days_until_due <= 3:
                    score += 1
                    
                confidence += 0.1
            except:
                pass
        
        # Check project context
        if input_data.get('project_priority') == 'high':
            score += 1
            confidence += 0.05
        
        # Determine final priority
        if score >= 3:
            predicted_priority = 'urgent'
        elif score >= 2:
            predicted_priority = 'high'
        elif score >= 1:
            predicted_priority = 'medium'
        else:
            predicted_priority = 'low'
        
        return {
            'prediction': {
                'priority': predicted_priority,
                'score': score,
                'reasoning': self._generate_priority_reasoning(score, text_content, due_date)
            },
            'confidence': min(confidence, 0.95)
        }
    
    async def _predict_completion_time(self, entity_type: str, entity_id: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Predict completion time for an entity"""
        # Simplified completion time prediction
        
        base_hours = 4  # Default estimate
        confidence = 0.6
        
        # Analyze complexity indicators
        text_content = f"{input_data.get('title', '')} {input_data.get('description', '')}".lower()
        
        # Complexity keywords
        complex_keywords = ['complex', 'difficult', 'challenging', 'research', 'analysis', 'integration']
        simple_keywords = ['simple', 'easy', 'quick', 'minor', 'small', 'fix']
        
        if any(keyword in text_content for keyword in complex_keywords):
            base_hours *= 2
            confidence += 0.1
        elif any(keyword in text_content for keyword in simple_keywords):
            base_hours *= 0.5
            confidence += 0.1
        
        # Check historical data for similar tasks
        similar_tasks = self._get_similar_completed_tasks(entity_type, input_data)
        if similar_tasks:
            avg_completion_time = sum(task.get('completion_hours', base_hours) for task in similar_tasks) / len(similar_tasks)
            base_hours = (base_hours + avg_completion_time) / 2
            confidence += 0.2
        
        # Add some randomness for realism
        estimated_hours = base_hours * (0.8 + random.random() * 0.4)
        
        return {
            'prediction': {
                'estimated_hours': round(estimated_hours, 1),
                'estimated_days': round(estimated_hours / 8, 1),
                'confidence_range': {
                    'min_hours': round(estimated_hours * 0.7, 1),
                    'max_hours': round(estimated_hours * 1.3, 1)
                }
            },
            'confidence': min(confidence, 0.9)
        }
    
    async def _predict_risk_level(self, entity_type: str, entity_id: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Predict risk level for an entity"""
        risk_score = 0
        confidence = 0.5
        risk_factors = []
        
        # Check timeline pressure
        due_date = input_data.get('due_date')
        if due_date:
            try:
                due_datetime = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                days_until_due = (due_datetime - datetime.utcnow()).days
                
                if days_until_due <= 2:
                    risk_score += 3
                    risk_factors.append('Very tight deadline')
                elif days_until_due <= 7:
                    risk_score += 2
                    risk_factors.append('Tight deadline')
                    
                confidence += 0.15
            except:
                pass
        
        # Check complexity
        text_content = f"{input_data.get('title', '')} {input_data.get('description', '')}".lower()
        risk_keywords = ['complex', 'difficult', 'uncertain', 'experimental', 'new', 'unknown']
        
        if any(keyword in text_content for keyword in risk_keywords):
            risk_score += 2
            risk_factors.append('High complexity')
            confidence += 0.1
        
        # Check dependencies
        if input_data.get('has_dependencies', False):
            risk_score += 1
            risk_factors.append('External dependencies')
            confidence += 0.1
        
        # Check team experience
        if input_data.get('team_experience', 'medium') == 'low':
            risk_score += 2
            risk_factors.append('Limited team experience')
            confidence += 0.1
        
        # Determine risk level
        if risk_score >= 5:
            risk_level = 'high'
        elif risk_score >= 3:
            risk_level = 'medium'
        elif risk_score >= 1:
            risk_level = 'low'
        else:
            risk_level = 'very_low'
        
        return {
            'prediction': {
                'risk_level': risk_level,
                'risk_score': risk_score,
                'risk_factors': risk_factors,
                'mitigation_suggestions': self._generate_risk_mitigation(risk_factors)
            },
            'confidence': min(confidence, 0.85)
        }
    
    async def _predict_effort_estimate(self, entity_type: str, entity_id: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Predict effort estimate for an entity"""
        # Similar to completion time but focuses on effort points
        
        base_points = 3  # Default story points
        confidence = 0.6
        
        # Analyze scope and complexity
        text_content = f"{input_data.get('title', '')} {input_data.get('description', '')}".lower()
        
        # Effort indicators
        high_effort_keywords = ['implement', 'develop', 'create', 'build', 'design', 'research']
        low_effort_keywords = ['update', 'fix', 'adjust', 'modify', 'change', 'correct']
        
        if any(keyword in text_content for keyword in high_effort_keywords):
            base_points *= 1.5
            confidence += 0.1
        elif any(keyword in text_content for keyword in low_effort_keywords):
            base_points *= 0.7
            confidence += 0.1
        
        # Check for scope indicators
        if len(text_content) > 200:  # Longer descriptions suggest more complexity
            base_points *= 1.2
            confidence += 0.05
        
        # Fibonacci-like effort points
        effort_points = min(round(base_points), 13)  # Cap at 13 points
        
        return {
            'prediction': {
                'effort_points': effort_points,
                'effort_category': self._categorize_effort(effort_points),
                'breakdown': {
                    'analysis': round(effort_points * 0.2, 1),
                    'development': round(effort_points * 0.6, 1),
                    'testing': round(effort_points * 0.2, 1)
                }
            },
            'confidence': min(confidence, 0.8)
        }

    async def generate_ai_project_preview(
        self,
        project_name: str,
        organization_id: str,
        user_id: str,
        project_type: str = "general",
        team_size: int = 5,
        team_experience: str = "intermediate"
    ) -> Dict[str, Any]:
        """Generate AI project preview without creating actual project"""
        try:
            # Generate project description and details
            project_data = await self._generate_project_description(project_name, project_type)

            # Generate workflow and phases with team adaptation
            workflow = self._generate_project_workflow(project_name, project_type, project_data, team_size, team_experience)

            # Generate comprehensive task breakdown
            tasks = self._generate_project_tasks(project_name, project_type, project_data, workflow)

            # Calculate estimates
            estimated_duration = self._calculate_project_duration(tasks, team_size, team_experience)
            estimated_cost = self._calculate_project_cost(tasks, team_size, team_experience)

            # Generate AI suggestions
            suggestions = await self._generate_ai_suggestions(project_name, project_type, project_data)

            return {
                "project": project_data,
                "workflow": workflow,
                "tasks": tasks,
                "suggestions": suggestions,
                "metadata": {
                    "generated_at": datetime.utcnow().isoformat(),
                    "project_type": project_type,
                    "team_configuration": {
                        "size": team_size,
                        "experience": team_experience
                    }
                },
                "estimated_duration": estimated_duration,
                "estimated_cost": estimated_cost
            }

        except Exception as e:
            logger.error(f"AI project preview generation failed: {str(e)}")
            raise Exception(f"Failed to generate project preview: {str(e)}")

    async def _generate_ai_suggestions(self, project_name: str, project_type: str, project_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate AI-powered suggestions and recommendations for the project"""

        # Try OpenAI first if available
        if self.ai_enabled and self.openai_client:
            try:
                return await self._generate_ai_suggestions_with_ai(project_name, project_type, project_data)
            except Exception as e:
                logger.warning(f"OpenAI suggestions generation failed, falling back to templates: {str(e)}")

        # Fallback to template-based suggestions
        return self._generate_ai_suggestions_with_templates(project_name, project_type, project_data)

    async def _generate_ai_suggestions_with_ai(self, project_name: str, project_type: str, project_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate suggestions using OpenAI API"""
        prompt = f"""
        Generate intelligent suggestions and recommendations for a {project_type} project named "{project_name}".

        Project context:
        - Description: {project_data.get('description', 'N/A')}
        - Industry: {project_data.get('industry', 'Technology')}
        - Complexity: {project_data.get('complexity', 'medium')}

        Return a JSON array of suggestion objects with this structure:
        [
            {{
                "category": "technology",
                "title": "Suggestion title",
                "description": "Detailed suggestion description",
                "priority": "high|medium|low",
                "impact": "Description of potential impact",
                "implementation_effort": "low|medium|high",
                "tags": ["tag1", "tag2"],
                "resources": ["resource1", "resource2"]
            }}
        ]

        Generate 5-8 diverse suggestions covering:
        - Technology stack recommendations
        - Architecture and design patterns
        - Development best practices
        - Performance optimization
        - Security considerations
        - Testing strategies
        - Deployment and DevOps
        - User experience improvements

        Make suggestions specific to "{project_name}" and "{project_type}".
        """

        response = await self._call_openai_api(prompt, max_tokens=1500)

        try:
            # Parse JSON response
            suggestions = json.loads(response)
            return suggestions if isinstance(suggestions, list) else []
        except json.JSONDecodeError:
            # If JSON parsing fails, create basic suggestions
            return self._generate_ai_suggestions_with_templates(project_name, project_type, project_data)

    def _generate_ai_suggestions_with_templates(self, project_name: str, project_type: str, project_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate suggestions using templates (fallback method)"""

        suggestions = []

        # Technology suggestions based on project type
        tech_suggestions = {
            'web_application': [
                {
                    "category": "technology",
                    "title": "Modern Frontend Framework",
                    "description": f"Consider using React, Vue.js, or Angular for {project_name} to create a responsive and maintainable user interface.",
                    "priority": "high",
                    "impact": "Improved development speed and user experience",
                    "implementation_effort": "medium",
                    "tags": ["frontend", "framework", "ui"],
                    "resources": ["React Documentation", "Vue.js Guide", "Angular Tutorial"]
                },
                {
                    "category": "architecture",
                    "title": "API-First Design",
                    "description": "Design RESTful APIs first to enable better separation of concerns and future mobile app development.",
                    "priority": "high",
                    "impact": "Better scalability and maintainability",
                    "implementation_effort": "medium",
                    "tags": ["api", "architecture", "scalability"],
                    "resources": ["REST API Best Practices", "OpenAPI Specification"]
                }
            ],
            'mobile_app': [
                {
                    "category": "technology",
                    "title": "Cross-Platform Development",
                    "description": f"Use React Native or Flutter for {project_name} to target both iOS and Android with a single codebase.",
                    "priority": "high",
                    "impact": "Reduced development time and maintenance costs",
                    "implementation_effort": "medium",
                    "tags": ["mobile", "cross-platform", "efficiency"],
                    "resources": ["React Native Docs", "Flutter Documentation"]
                },
                {
                    "category": "performance",
                    "title": "Offline-First Architecture",
                    "description": "Implement offline capabilities to ensure the app works without internet connectivity.",
                    "priority": "medium",
                    "impact": "Better user experience and reliability",
                    "implementation_effort": "high",
                    "tags": ["offline", "performance", "ux"],
                    "resources": ["Offline-First Design Patterns", "Local Storage Solutions"]
                }
            ],
            'ecommerce_platform': [
                {
                    "category": "security",
                    "title": "PCI DSS Compliance",
                    "description": f"Ensure {project_name} meets PCI DSS requirements for secure payment processing.",
                    "priority": "high",
                    "impact": "Legal compliance and customer trust",
                    "implementation_effort": "high",
                    "tags": ["security", "compliance", "payments"],
                    "resources": ["PCI DSS Guidelines", "Payment Security Best Practices"]
                },
                {
                    "category": "performance",
                    "title": "CDN and Caching Strategy",
                    "description": "Implement content delivery network and caching to handle high traffic loads.",
                    "priority": "high",
                    "impact": "Improved page load times and scalability",
                    "implementation_effort": "medium",
                    "tags": ["performance", "cdn", "caching"],
                    "resources": ["CDN Best Practices", "Caching Strategies"]
                }
            ]
        }

        # Get suggestions for the project type
        type_suggestions = tech_suggestions.get(project_type, tech_suggestions['web_application'])
        suggestions.extend(type_suggestions)

        # Add general suggestions
        general_suggestions = [
            {
                "category": "testing",
                "title": "Automated Testing Strategy",
                "description": f"Implement comprehensive testing including unit, integration, and end-to-end tests for {project_name}.",
                "priority": "high",
                "impact": "Reduced bugs and improved code quality",
                "implementation_effort": "medium",
                "tags": ["testing", "quality", "automation"],
                "resources": ["Testing Best Practices", "Test Automation Tools"]
            },
            {
                "category": "devops",
                "title": "CI/CD Pipeline",
                "description": "Set up continuous integration and deployment pipeline for automated testing and deployment.",
                "priority": "medium",
                "impact": "Faster and more reliable deployments",
                "implementation_effort": "medium",
                "tags": ["devops", "automation", "deployment"],
                "resources": ["CI/CD Best Practices", "Pipeline Tools Comparison"]
            },
            {
                "category": "monitoring",
                "title": "Application Monitoring",
                "description": "Implement comprehensive monitoring and logging to track application performance and errors.",
                "priority": "medium",
                "impact": "Better visibility and faster issue resolution",
                "implementation_effort": "low",
                "tags": ["monitoring", "logging", "observability"],
                "resources": ["Monitoring Tools", "Logging Best Practices"]
            }
        ]

        suggestions.extend(general_suggestions)

        return suggestions[:8]  # Return up to 8 suggestions

    def _calculate_project_duration(self, tasks: List[Dict[str, Any]], team_size: int, team_experience: str) -> int:
        """Calculate estimated project duration in weeks"""
        if not tasks:
            return 8  # Default 8 weeks

        # Base duration calculation
        total_effort_points = sum(task.get('effort_points', 3) for task in tasks)

        # Experience multipliers
        experience_multipliers = {
            'beginner': 1.5,
            'intermediate': 1.0,
            'advanced': 0.8,
            'expert': 0.6
        }

        multiplier = experience_multipliers.get(team_experience, 1.0)

        # Team size factor (diminishing returns)
        team_factor = min(team_size / 5.0, 2.0)  # Cap at 2x efficiency

        # Calculate duration in weeks
        estimated_weeks = (total_effort_points * multiplier) / team_factor

        # Round to reasonable range (2-52 weeks)
        return max(2, min(52, round(estimated_weeks)))

    def _calculate_project_cost(self, tasks: List[Dict[str, Any]], team_size: int, team_experience: str) -> float:
        """Calculate estimated project cost in USD"""
        duration_weeks = self._calculate_project_duration(tasks, team_size, team_experience)

        # Average hourly rates by experience level
        hourly_rates = {
            'beginner': 50,
            'intermediate': 75,
            'advanced': 100,
            'expert': 150
        }

        avg_rate = hourly_rates.get(team_experience, 75)

        # Assume 40 hours per week per team member
        total_hours = duration_weeks * 40 * team_size

        # Add 20% overhead for project management, tools, etc.
        total_cost = total_hours * avg_rate * 1.2

        return round(total_cost, 2)

    async def generate_ai_project(
        self,
        project_name: str,
        organization_id: str,
        user_id: str,
        project_type: str = "general"
    ) -> Dict[str, Any]:
        """Generate a complete AI-powered project with description, workflow, and tasks"""
        try:
            # Generate project description and details
            project_data = await self._generate_project_description(project_name, project_type)

            # Generate workflow and phases with team adaptation
            workflow = self._generate_project_workflow(project_name, project_type, project_data, team_size=5, team_experience='intermediate')

            # Generate comprehensive task breakdown
            tasks = self._generate_project_tasks(project_name, project_type, project_data, workflow)

            # Generate project metadata
            metadata = self._generate_project_metadata(project_name, project_type, tasks)

            # Prepare integration setup data
            integration_setup_data = {
                'project_data': {
                    'name': project_name,
                    'project_type': project_type,
                    'id': None  # Will be set after project creation
                },
                'workflow': workflow,
                'tasks': tasks,
                'organization_id': organization_id
            }

            return {
                'success': True,
                'project': {
                    'name': project_name,
                    'description': project_data['description'],
                    'overview': project_data['overview'],
                    'objectives': project_data['objectives'],
                    'success_criteria': project_data['success_criteria'],
                    'organization_id': organization_id,
                    'created_by': user_id,
                    'project_type': project_type,
                    'estimated_duration': metadata['estimated_duration'],
                    'estimated_budget': metadata['estimated_budget'],
                    'risk_level': metadata['risk_level'],
                    'priority': metadata['priority']
                },
                'workflow': workflow,
                'tasks': tasks,
                'metadata': metadata,
                'integration_setup': integration_setup_data,
                'ai_generated': True,
                'generated_at': datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to generate AI project: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def _analyze_project_name(self, project_name: str) -> Dict[str, Any]:
        """Intelligently analyze project name to detect type, industry, and complexity"""
        name_lower = project_name.lower()

        # Project type detection keywords
        type_keywords = {
            'web_application': ['web', 'website', 'portal', 'dashboard', 'platform', 'app', 'application', 'system', 'saas'],
            'mobile_app': ['mobile', 'ios', 'android', 'app', 'smartphone', 'tablet'],
            'ecommerce_platform': ['ecommerce', 'e-commerce', 'shop', 'store', 'marketplace', 'retail', 'cart', 'checkout'],
            'data_analysis': ['analytics', 'data', 'analysis', 'insights', 'reporting', 'dashboard', 'bi', 'intelligence'],
            'marketing_campaign': ['marketing', 'campaign', 'promotion', 'advertising', 'brand', 'social media'],
            'api_service': ['api', 'service', 'microservice', 'backend', 'server', 'endpoint'],
            'automation': ['automation', 'workflow', 'bot', 'script', 'process', 'integration']
        }

        # Industry detection keywords
        industry_keywords = {
            'healthcare': ['health', 'medical', 'hospital', 'clinic', 'patient', 'doctor', 'pharmacy'],
            'finance': ['bank', 'finance', 'payment', 'trading', 'investment', 'fintech', 'crypto'],
            'education': ['education', 'learning', 'school', 'university', 'course', 'training', 'student'],
            'retail': ['retail', 'shop', 'store', 'fashion', 'clothing', 'product'],
            'manufacturing': ['manufacturing', 'factory', 'production', 'supply', 'inventory'],
            'real_estate': ['real estate', 'property', 'housing', 'rental', 'mortgage'],
            'entertainment': ['game', 'gaming', 'entertainment', 'media', 'streaming', 'music'],
            'food': ['food', 'restaurant', 'recipe', 'cooking', 'delivery', 'dining'],
            'travel': ['travel', 'booking', 'hotel', 'flight', 'tourism', 'vacation'],
            'fitness': ['fitness', 'gym', 'workout', 'health', 'exercise', 'sports']
        }

        # Complexity indicators
        complexity_keywords = {
            'high': ['enterprise', 'complex', 'advanced', 'comprehensive', 'full-scale', 'large'],
            'medium': ['standard', 'professional', 'business', 'commercial'],
            'low': ['simple', 'basic', 'minimal', 'quick', 'prototype', 'mvp']
        }

        # Detect project type
        detected_type = 'general'
        max_type_score = 0
        for ptype, keywords in type_keywords.items():
            score = sum(1 for keyword in keywords if keyword in name_lower)
            if score > max_type_score:
                max_type_score = score
                detected_type = ptype

        # Detect industry
        detected_industry = 'Technology'
        max_industry_score = 0
        for industry, keywords in industry_keywords.items():
            score = sum(1 for keyword in keywords if keyword in name_lower)
            if score > max_industry_score:
                max_industry_score = score
                detected_industry = industry.replace('_', ' ').title()

        # Detect complexity
        detected_complexity = 'medium'
        for complexity, keywords in complexity_keywords.items():
            if any(keyword in name_lower for keyword in keywords):
                detected_complexity = complexity
                break

        # Generate team size recommendation based on complexity and type
        team_size_map = {
            ('low', 'web_application'): '3-5 people',
            ('medium', 'web_application'): '5-8 people',
            ('high', 'web_application'): '8-15 people',
            ('low', 'mobile_app'): '2-4 people',
            ('medium', 'mobile_app'): '4-7 people',
            ('high', 'mobile_app'): '7-12 people',
            ('low', 'ecommerce_platform'): '4-6 people',
            ('medium', 'ecommerce_platform'): '6-10 people',
            ('high', 'ecommerce_platform'): '10-20 people'
        }

        recommended_team_size = team_size_map.get((detected_complexity, detected_type), '5-8 people')

        return {
            'project_type': detected_type,
            'industry': detected_industry,
            'complexity': detected_complexity,
            'recommended_team_size': recommended_team_size,
            'confidence_score': max(max_type_score, max_industry_score) / 3  # Normalize confidence
        }

    async def _generate_project_description(self, project_name: str, project_type: str) -> Dict[str, Any]:
        """Generate comprehensive project description and details with intelligent analysis"""

        # Try OpenAI first if available
        if self.ai_enabled and self.openai_client:
            try:
                return await self._generate_project_description_with_ai(project_name, project_type)
            except Exception as e:
                logger.warning(f"OpenAI generation failed, falling back to templates: {str(e)}")

        # Fallback to template-based generation
        return self._generate_project_description_with_templates(project_name, project_type)

    async def _generate_project_description_with_ai(self, project_name: str, project_type: str) -> Dict[str, Any]:
        """Generate project description using OpenAI API"""
        prompt = f"""
        Generate a comprehensive project description for a project named "{project_name}" of type "{project_type}".

        Return a JSON object with the following structure:
        {{
            "name": "{project_name}",
            "description": "Detailed project description (2-3 sentences)",
            "overview": "Comprehensive project overview (3-4 sentences)",
            "objectives": ["objective1", "objective2", "objective3", "objective4", "objective5"],
            "success_criteria": ["criteria1", "criteria2", "criteria3", "criteria4"],
            "industry": "detected industry",
            "complexity": "low/medium/high",
            "estimated_duration_weeks": number,
            "key_features": ["feature1", "feature2", "feature3"],
            "target_audience": "description of target users",
            "business_value": "description of business value and ROI"
        }}

        Make the content specific to "{project_name}" and relevant to the "{project_type}" project type.
        Be professional, detailed, and realistic.
        """

        response = await self._call_openai_api(prompt, max_tokens=1500)

        try:
            # Parse JSON response
            ai_data = json.loads(response)
            return ai_data
        except json.JSONDecodeError:
            # If JSON parsing fails, extract content and create structured response
            return {
                "name": project_name,
                "description": f"AI-generated {project_type} project: {project_name}",
                "overview": response[:500] if response else f"Comprehensive {project_type} project focused on {project_name}",
                "objectives": [
                    f"Develop core functionality for {project_name}",
                    "Implement user-friendly interface",
                    "Ensure scalability and performance",
                    "Maintain high code quality standards",
                    "Deploy to production environment"
                ],
                "success_criteria": [
                    "Project meets all functional requirements",
                    "Performance benchmarks achieved",
                    "User acceptance criteria satisfied",
                    "Successful production deployment"
                ],
                "industry": "Technology",
                "complexity": "medium"
            }

    def _generate_project_description_with_templates(self, project_name: str, project_type: str) -> Dict[str, Any]:
        """Generate project description using templates (fallback method)"""

        # Intelligent project analysis based on name
        analyzed_data = self._analyze_project_name(project_name)
        detected_type = analyzed_data.get('project_type', project_type)
        detected_industry = analyzed_data.get('industry', 'Technology')
        complexity_level = analyzed_data.get('complexity', 'medium')

        # Use detected type if it's more specific than provided type
        if detected_type != 'general' and project_type == 'general':
            project_type = detected_type

        # Project type templates
        project_templates = {
            'web_application': {
                'description_template': f"A comprehensive web application project focused on {project_name}. This project involves developing a modern, scalable web solution with user-friendly interface and robust backend functionality.",
                'objectives': [
                    "Develop a responsive and intuitive user interface",
                    "Implement secure user authentication and authorization",
                    "Create efficient data management and storage solutions",
                    "Ensure cross-browser compatibility and performance optimization",
                    "Implement comprehensive testing and quality assurance"
                ],
                'success_criteria': [
                    "Application loads within 3 seconds on average",
                    "99.9% uptime and reliability",
                    "Positive user feedback and adoption",
                    "Successful deployment to production environment",
                    "All security requirements met and validated"
                ]
            },
            'mobile_app': {
                'description_template': f"A cutting-edge mobile application project for {project_name}. This project focuses on creating an engaging, performant mobile experience across iOS and Android platforms.",
                'objectives': [
                    "Design intuitive mobile user experience",
                    "Implement native or cross-platform functionality",
                    "Optimize for mobile performance and battery life",
                    "Integrate with device features and capabilities",
                    "Ensure app store compliance and approval"
                ],
                'success_criteria': [
                    "App store approval and successful launch",
                    "High user ratings (4+ stars)",
                    "Smooth performance on target devices",
                    "Successful user onboarding and retention",
                    "Meeting all platform guidelines"
                ]
            },
            'data_analysis': {
                'description_template': f"A comprehensive data analysis project for {project_name}. This project involves collecting, processing, and analyzing data to derive meaningful insights and support decision-making.",
                'objectives': [
                    "Collect and clean relevant data sources",
                    "Perform exploratory data analysis",
                    "Develop predictive models and algorithms",
                    "Create interactive visualizations and dashboards",
                    "Generate actionable insights and recommendations"
                ],
                'success_criteria': [
                    "Data quality and completeness achieved",
                    "Accurate and reliable analytical models",
                    "Clear and compelling data visualizations",
                    "Stakeholder approval of insights",
                    "Successful implementation of recommendations"
                ]
            },
            'marketing_campaign': {
                'description_template': f"A strategic marketing campaign project for {project_name}. This project focuses on developing and executing a comprehensive marketing strategy to achieve specific business objectives.",
                'objectives': [
                    "Define target audience and market segments",
                    "Develop compelling marketing messages and content",
                    "Execute multi-channel marketing campaigns",
                    "Track and measure campaign performance",
                    "Optimize campaigns based on data and feedback"
                ],
                'success_criteria': [
                    "Achieve target reach and engagement metrics",
                    "Generate qualified leads and conversions",
                    "Positive brand awareness and sentiment",
                    "ROI targets met or exceeded",
                    "Successful campaign completion within budget"
                ]
            },
            'ecommerce_platform': {
                'description_template': f"A comprehensive e-commerce platform project for {project_name}. This project involves building a scalable online marketplace with advanced features for product management, payment processing, and customer experience optimization.",
                'objectives': [
                    "Develop user-friendly product catalog and search functionality",
                    "Implement secure payment processing and checkout flow",
                    "Create comprehensive admin dashboard for store management",
                    "Build customer account management and order tracking",
                    "Integrate inventory management and shipping solutions",
                    "Implement analytics and reporting capabilities"
                ],
                'success_criteria': [
                    "Platform handles 10,000+ concurrent users",
                    "Payment processing success rate above 99.5%",
                    "Page load times under 2 seconds",
                    "Mobile-responsive design with 95%+ compatibility",
                    "PCI DSS compliance achieved",
                    "Customer satisfaction score above 4.5/5"
                ]
            },
            'saas_application': {
                'description_template': f"A Software-as-a-Service application project for {project_name}. This project focuses on building a cloud-based solution with multi-tenancy, subscription management, and enterprise-grade security.",
                'objectives': [
                    "Design scalable multi-tenant architecture",
                    "Implement subscription and billing management",
                    "Develop comprehensive API and integration capabilities",
                    "Create role-based access control and security features",
                    "Build analytics dashboard and reporting tools",
                    "Implement automated deployment and monitoring"
                ],
                'success_criteria': [
                    "99.9% uptime SLA achievement",
                    "Sub-second API response times",
                    "SOC 2 Type II compliance",
                    "Successful multi-tenant data isolation",
                    "Automated scaling for 100x traffic spikes",
                    "Customer churn rate below 5% monthly"
                ]
            },
            'devops_infrastructure': {
                'description_template': f"A DevOps and Infrastructure project for {project_name}. This project involves setting up robust CI/CD pipelines, infrastructure automation, and monitoring systems for reliable software delivery.",
                'objectives': [
                    "Implement automated CI/CD pipelines",
                    "Set up infrastructure as code (IaC)",
                    "Configure comprehensive monitoring and alerting",
                    "Establish security scanning and compliance checks",
                    "Create disaster recovery and backup strategies",
                    "Implement container orchestration and scaling"
                ],
                'success_criteria': [
                    "Deployment frequency increased by 10x",
                    "Mean time to recovery (MTTR) under 30 minutes",
                    "Zero-downtime deployments achieved",
                    "Infrastructure provisioning automated 100%",
                    "Security vulnerabilities detected within 24 hours",
                    "Cost optimization of 30% through automation"
                ]
            },
            'research_development': {
                'description_template': f"A Research & Development project for {project_name}. This project focuses on innovative research, prototyping, and development of cutting-edge solutions with scientific rigor and documentation.",
                'objectives': [
                    "Conduct comprehensive literature review and market analysis",
                    "Design and execute controlled experiments",
                    "Develop proof-of-concept prototypes",
                    "Validate hypotheses through data collection and analysis",
                    "Document findings and create technical specifications",
                    "Prepare intellectual property and patent applications"
                ],
                'success_criteria': [
                    "Research objectives met with statistical significance",
                    "Prototype demonstrates feasibility and performance",
                    "Peer-reviewed publications or patent applications filed",
                    "Technology transfer or commercialization plan developed",
                    "Research methodology validated and reproducible",
                    "Stakeholder approval for next phase development"
                ]
            },
            'event_management': {
                'description_template': f"An Event Management project for {project_name}. This project involves comprehensive planning, coordination, and execution of events with focus on attendee experience and operational excellence.",
                'objectives': [
                    "Define event scope, objectives, and target audience",
                    "Secure venue, vendors, and necessary permits",
                    "Develop marketing and registration strategies",
                    "Coordinate logistics, catering, and technical requirements",
                    "Implement attendee engagement and networking opportunities",
                    "Execute post-event analysis and follow-up activities"
                ],
                'success_criteria': [
                    "Target attendance numbers achieved",
                    "Event executed within budget constraints",
                    "Attendee satisfaction score above 4.0/5",
                    "Zero critical incidents or safety issues",
                    "Media coverage and social engagement targets met",
                    "Positive ROI or strategic objectives accomplished"
                ]
            },
            'general': {
                'description_template': f"A comprehensive project focused on {project_name}. This project involves careful planning, execution, and delivery of key objectives while maintaining high quality standards.",
                'objectives': [
                    "Define clear project scope and requirements",
                    "Develop detailed project plan and timeline",
                    "Execute project phases according to plan",
                    "Monitor progress and manage risks",
                    "Deliver high-quality results on time and within budget"
                ],
                'success_criteria': [
                    "All project deliverables completed successfully",
                    "Project completed within timeline and budget",
                    "Stakeholder satisfaction achieved",
                    "Quality standards met or exceeded",
                    "Successful project closure and handover"
                ]
            }
        }

        template = project_templates.get(project_type, project_templates['general'])

        # Enhanced description with intelligent analysis
        enhanced_description = template['description_template']
        if analyzed_data['confidence_score'] > 0.3:  # High confidence in analysis
            enhanced_description += f" Based on intelligent analysis, this project is classified as a {detected_industry} industry {detected_type.replace('_', ' ')} with {complexity_level} complexity level."

        return {
            'description': enhanced_description,
            'overview': f"This project aims to deliver {project_name} through a structured approach involving planning, development, testing, and deployment phases. The project will follow industry best practices and agile methodologies to ensure successful delivery.",
            'objectives': template['objectives'],
            'success_criteria': template['success_criteria'],
            'industry': detected_industry,
            'project_type': detected_type,
            'complexity': complexity_level,
            'team_size': analyzed_data['recommended_team_size'],
            'ai_analysis': analyzed_data
        }

    def _generate_project_workflow(self, project_name: str, project_type: str, project_data: Dict[str, Any], team_size: int = 5, team_experience: str = 'intermediate') -> Dict[str, Any]:
        """Generate intelligent project workflow with team-based adaptation"""

        # Common workflow phases for different project types
        workflow_templates = {
            'web_application': [
                {
                    'name': 'Planning & Analysis',
                    'description': 'Requirements gathering, technical analysis, and project planning',
                    'duration_days': 7,
                    'deliverables': ['Requirements document', 'Technical specification', 'Project plan']
                },
                {
                    'name': 'Design & Architecture',
                    'description': 'UI/UX design, system architecture, and database design',
                    'duration_days': 10,
                    'deliverables': ['UI mockups', 'System architecture', 'Database schema']
                },
                {
                    'name': 'Development',
                    'description': 'Frontend and backend development, API implementation',
                    'duration_days': 21,
                    'deliverables': ['Frontend application', 'Backend API', 'Database implementation']
                },
                {
                    'name': 'Testing & QA',
                    'description': 'Unit testing, integration testing, and quality assurance',
                    'duration_days': 7,
                    'deliverables': ['Test cases', 'Test reports', 'Bug fixes']
                },
                {
                    'name': 'Deployment & Launch',
                    'description': 'Production deployment, monitoring setup, and launch',
                    'duration_days': 5,
                    'deliverables': ['Production deployment', 'Monitoring setup', 'Launch documentation']
                }
            ],
            'mobile_app': [
                {
                    'name': 'Concept & Planning',
                    'description': 'App concept definition, market research, and planning',
                    'duration_days': 5,
                    'deliverables': ['App concept document', 'Market analysis', 'Feature specification']
                },
                {
                    'name': 'Design & Prototyping',
                    'description': 'UI/UX design, prototyping, and user experience optimization',
                    'duration_days': 12,
                    'deliverables': ['App designs', 'Interactive prototype', 'User flow diagrams']
                },
                {
                    'name': 'Development',
                    'description': 'Native or cross-platform app development',
                    'duration_days': 25,
                    'deliverables': ['iOS app', 'Android app', 'Backend services']
                },
                {
                    'name': 'Testing & Optimization',
                    'description': 'Device testing, performance optimization, and bug fixes',
                    'duration_days': 8,
                    'deliverables': ['Test results', 'Performance reports', 'Optimized app']
                },
                {
                    'name': 'App Store Submission',
                    'description': 'App store preparation, submission, and launch',
                    'duration_days': 7,
                    'deliverables': ['App store listings', 'Approved apps', 'Launch materials']
                }
            ],
            'ecommerce_platform': [
                {
                    'name': 'Market Research & Planning',
                    'description': 'Market analysis, competitor research, and platform strategy definition',
                    'duration_days': 10,
                    'deliverables': ['Market analysis report', 'Competitor analysis', 'Platform requirements', 'Technical architecture']
                },
                {
                    'name': 'Core Platform Development',
                    'description': 'Product catalog, user management, and basic e-commerce functionality',
                    'duration_days': 30,
                    'deliverables': ['Product catalog system', 'User authentication', 'Shopping cart', 'Basic admin panel']
                },
                {
                    'name': 'Payment & Security Integration',
                    'description': 'Payment gateway integration, security implementation, and compliance',
                    'duration_days': 15,
                    'deliverables': ['Payment processing', 'Security measures', 'PCI compliance', 'SSL certificates']
                },
                {
                    'name': 'Advanced Features & Optimization',
                    'description': 'Search functionality, recommendations, performance optimization',
                    'duration_days': 20,
                    'deliverables': ['Search engine', 'Recommendation system', 'Performance optimization', 'Mobile optimization']
                },
                {
                    'name': 'Testing & Launch',
                    'description': 'Comprehensive testing, load testing, and production deployment',
                    'duration_days': 12,
                    'deliverables': ['Test results', 'Load testing report', 'Production deployment', 'Launch documentation']
                }
            ],
            'saas_application': [
                {
                    'name': 'Architecture & Infrastructure Design',
                    'description': 'Multi-tenant architecture design and cloud infrastructure planning',
                    'duration_days': 12,
                    'deliverables': ['System architecture', 'Database design', 'Infrastructure plan', 'Security framework']
                },
                {
                    'name': 'Core Application Development',
                    'description': 'Multi-tenant core functionality and API development',
                    'duration_days': 35,
                    'deliverables': ['Core application', 'REST APIs', 'Multi-tenant data isolation', 'Authentication system']
                },
                {
                    'name': 'Subscription & Billing System',
                    'description': 'Subscription management, billing integration, and payment processing',
                    'duration_days': 18,
                    'deliverables': ['Subscription management', 'Billing system', 'Payment integration', 'Usage tracking']
                },
                {
                    'name': 'Enterprise Features & Security',
                    'description': 'Enterprise-grade features, security compliance, and audit trails',
                    'duration_days': 22,
                    'deliverables': ['RBAC system', 'Audit logging', 'Compliance features', 'Enterprise integrations']
                },
                {
                    'name': 'Deployment & Monitoring',
                    'description': 'Production deployment, monitoring setup, and performance optimization',
                    'duration_days': 10,
                    'deliverables': ['Production deployment', 'Monitoring dashboard', 'Performance metrics', 'SLA documentation']
                }
            ],
            'devops_infrastructure': [
                {
                    'name': 'Infrastructure Assessment & Planning',
                    'description': 'Current state analysis and infrastructure roadmap development',
                    'duration_days': 8,
                    'deliverables': ['Infrastructure audit', 'Gap analysis', 'Roadmap document', 'Tool selection']
                },
                {
                    'name': 'CI/CD Pipeline Implementation',
                    'description': 'Automated build, test, and deployment pipeline setup',
                    'duration_days': 15,
                    'deliverables': ['CI/CD pipelines', 'Automated testing', 'Deployment automation', 'Pipeline documentation']
                },
                {
                    'name': 'Infrastructure as Code',
                    'description': 'Infrastructure automation and configuration management',
                    'duration_days': 12,
                    'deliverables': ['IaC templates', 'Configuration management', 'Environment provisioning', 'Version control']
                },
                {
                    'name': 'Monitoring & Security',
                    'description': 'Comprehensive monitoring, alerting, and security implementation',
                    'duration_days': 10,
                    'deliverables': ['Monitoring setup', 'Alert configuration', 'Security scanning', 'Compliance checks']
                },
                {
                    'name': 'Optimization & Documentation',
                    'description': 'Performance optimization, cost management, and knowledge transfer',
                    'duration_days': 7,
                    'deliverables': ['Performance optimization', 'Cost analysis', 'Documentation', 'Team training']
                }
            ],
            'research_development': [
                {
                    'name': 'Research Planning & Literature Review',
                    'description': 'Research methodology design and comprehensive literature analysis',
                    'duration_days': 14,
                    'deliverables': ['Research proposal', 'Literature review', 'Methodology document', 'Ethics approval']
                },
                {
                    'name': 'Experimental Design & Setup',
                    'description': 'Experiment design, equipment setup, and protocol development',
                    'duration_days': 18,
                    'deliverables': ['Experimental design', 'Equipment setup', 'Protocols', 'Safety procedures']
                },
                {
                    'name': 'Data Collection & Analysis',
                    'description': 'Systematic data collection and statistical analysis',
                    'duration_days': 25,
                    'deliverables': ['Raw data', 'Statistical analysis', 'Preliminary results', 'Data validation']
                },
                {
                    'name': 'Prototype Development',
                    'description': 'Proof-of-concept development and validation testing',
                    'duration_days': 20,
                    'deliverables': ['Prototype', 'Validation tests', 'Performance metrics', 'Technical specifications']
                },
                {
                    'name': 'Documentation & IP Protection',
                    'description': 'Research documentation, publication preparation, and IP filing',
                    'duration_days': 12,
                    'deliverables': ['Research report', 'Publication draft', 'Patent application', 'Technology transfer plan']
                }
            ],
            'event_management': [
                {
                    'name': 'Event Conceptualization & Planning',
                    'description': 'Event concept development, objective setting, and initial planning',
                    'duration_days': 10,
                    'deliverables': ['Event concept', 'Objectives document', 'Budget plan', 'Timeline']
                },
                {
                    'name': 'Venue & Vendor Management',
                    'description': 'Venue selection, vendor negotiations, and contract management',
                    'duration_days': 15,
                    'deliverables': ['Venue contracts', 'Vendor agreements', 'Catering arrangements', 'Equipment rentals']
                },
                {
                    'name': 'Marketing & Registration',
                    'description': 'Marketing campaign execution and registration system setup',
                    'duration_days': 20,
                    'deliverables': ['Marketing materials', 'Registration system', 'Promotional campaigns', 'Attendee communications']
                },
                {
                    'name': 'Logistics & Coordination',
                    'description': 'Detailed logistics planning and team coordination',
                    'duration_days': 12,
                    'deliverables': ['Logistics plan', 'Staff assignments', 'Equipment setup', 'Emergency procedures']
                },
                {
                    'name': 'Event Execution & Follow-up',
                    'description': 'Event execution, real-time management, and post-event activities',
                    'duration_days': 8,
                    'deliverables': ['Event execution', 'Attendee feedback', 'Financial reconciliation', 'Post-event report']
                }
            ],
            'general': [
                {
                    'name': 'Initiation & Planning',
                    'description': 'Project initiation, scope definition, and detailed planning',
                    'duration_days': 5,
                    'deliverables': ['Project charter', 'Scope document', 'Project plan']
                },
                {
                    'name': 'Execution Phase 1',
                    'description': 'First phase of project execution and deliverable creation',
                    'duration_days': 14,
                    'deliverables': ['Phase 1 deliverables', 'Progress reports', 'Quality reviews']
                },
                {
                    'name': 'Execution Phase 2',
                    'description': 'Second phase of project execution and refinement',
                    'duration_days': 14,
                    'deliverables': ['Phase 2 deliverables', 'Integration testing', 'Stakeholder reviews']
                },
                {
                    'name': 'Finalization & Review',
                    'description': 'Final deliverable preparation and quality assurance',
                    'duration_days': 7,
                    'deliverables': ['Final deliverables', 'Quality reports', 'Documentation']
                },
                {
                    'name': 'Closure & Handover',
                    'description': 'Project closure, handover, and lessons learned',
                    'duration_days': 3,
                    'deliverables': ['Handover documentation', 'Project closure report', 'Lessons learned']
                }
            ]
        }

        phases = workflow_templates.get(project_type, workflow_templates['general'])

        # Apply team-based adaptations
        phases = self._adapt_workflow_for_team(phases, team_size, team_experience, project_type)

        # Calculate total duration
        total_duration = sum(phase['duration_days'] for phase in phases)

        # Generate parallel execution suggestions
        parallel_opportunities = self._identify_parallel_execution_opportunities(phases, project_type)

        # Generate quality gates
        quality_gates = self._generate_quality_gates(phases, project_type)

        # Generate milestone celebrations
        milestone_celebrations = self._generate_milestone_celebrations(phases, project_name)

        return {
            'phases': phases,
            'total_duration_days': total_duration,
            'methodology': self._select_methodology(team_size, team_experience, project_type),
            'milestones': [f"Phase {i+1} Completion: {phase['name']}" for i, phase in enumerate(phases)],
            'parallel_opportunities': parallel_opportunities,
            'quality_gates': quality_gates,
            'milestone_celebrations': milestone_celebrations,
            'team_adaptations': {
                'team_size': team_size,
                'experience_level': team_experience,
                'recommended_sprint_length': self._recommend_sprint_length(team_size, team_experience),
                'communication_frequency': self._recommend_communication_frequency(team_size)
            },
            'risk_mitigation': [
                'Regular progress reviews and stakeholder communication',
                'Iterative development with frequent testing',
                'Contingency planning for critical path items',
                'Quality gates at each phase completion',
                'Team capacity monitoring and adjustment',
                'Parallel execution where possible to reduce timeline'
            ]
        }

    def _generate_project_tasks(self, project_name: str, project_type: str, project_data: Dict[str, Any], workflow: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate comprehensive task breakdown for the project"""

        tasks = []
        task_templates = self._get_task_templates_by_type(project_type)

        # Generate tasks for each workflow phase
        for phase_index, phase in enumerate(workflow['phases']):
            phase_tasks = task_templates.get(phase['name'], [])

            for task_index, task_template in enumerate(phase_tasks):
                task = {
                    'title': task_template['title'].format(project_name=project_name),
                    'description': task_template['description'].format(project_name=project_name),
                    'phase': phase['name'],
                    'phase_index': phase_index,
                    'task_index': task_index,
                    'priority': task_template.get('priority', 'medium'),
                    'estimated_hours': task_template.get('estimated_hours', 8),
                    'story_points': task_template.get('story_points', self._calculate_story_points(task_template.get('estimated_hours', 8))),
                    'tags': task_template.get('tags', []),
                    'checklist': task_template.get('checklist', []),
                    'dependencies': task_template.get('dependencies', []),
                    'assignee_role': task_template.get('assignee_role', 'team_member'),
                    'risk_level': task_template.get('risk_level', self._assess_task_risk(task_template)),
                    'status': 'todo',
                    'ai_generated': True
                }

                # Add phase-specific context
                task['phase_description'] = phase['description']
                task['phase_deliverables'] = phase['deliverables']

                # Add smart deadline calculation
                task['suggested_deadline'] = self._calculate_smart_deadline(task, phase, workflow)

                # Add resource allocation recommendations
                task['resource_allocation'] = self._recommend_resource_allocation(task)

                tasks.append(task)

        # Post-process tasks for advanced dependency mapping
        tasks = self._enhance_task_dependencies(tasks, project_type)

        return tasks

    def _get_task_templates_by_type(self, project_type: str) -> Dict[str, List[Dict[str, Any]]]:
        """Get task templates organized by project phase"""

        # Web application task templates
        web_app_templates = {
            'Planning & Analysis': [
                {
                    'title': 'Gather Requirements for {project_name}',
                    'description': 'Conduct stakeholder interviews and document functional and non-functional requirements for {project_name}',
                    'priority': 'high',
                    'estimated_hours': 16,
                    'tags': ['requirements', 'analysis'],
                    'checklist': [
                        'Schedule stakeholder interviews',
                        'Prepare interview questions',
                        'Conduct interviews',
                        'Document functional requirements',
                        'Document non-functional requirements',
                        'Get stakeholder approval'
                    ],
                    'assignee_role': 'business_analyst'
                },
                {
                    'title': 'Create Technical Specification',
                    'description': 'Design system architecture and create detailed technical specification for {project_name}',
                    'priority': 'high',
                    'estimated_hours': 12,
                    'tags': ['architecture', 'technical'],
                    'checklist': [
                        'Review requirements document',
                        'Design system architecture',
                        'Select technology stack',
                        'Define API specifications',
                        'Create database schema',
                        'Document technical decisions'
                    ],
                    'assignee_role': 'technical_lead'
                },
                {
                    'title': 'Project Planning and Timeline',
                    'description': 'Create detailed project plan with milestones and resource allocation for {project_name}',
                    'priority': 'medium',
                    'estimated_hours': 8,
                    'tags': ['planning', 'timeline'],
                    'checklist': [
                        'Break down work into tasks',
                        'Estimate task durations',
                        'Identify dependencies',
                        'Allocate resources',
                        'Create project timeline',
                        'Set up project tracking'
                    ],
                    'assignee_role': 'project_manager'
                }
            ],
            'Design & Architecture': [
                {
                    'title': 'UI/UX Design for {project_name}',
                    'description': 'Create user interface designs and user experience flows for {project_name}',
                    'priority': 'high',
                    'estimated_hours': 20,
                    'tags': ['design', 'ui', 'ux'],
                    'checklist': [
                        'Create user personas',
                        'Design user journey maps',
                        'Create wireframes',
                        'Design high-fidelity mockups',
                        'Create design system',
                        'Get design approval'
                    ],
                    'assignee_role': 'ui_designer'
                },
                {
                    'title': 'Database Design and Schema',
                    'description': 'Design database structure and create schema for {project_name}',
                    'priority': 'high',
                    'estimated_hours': 12,
                    'tags': ['database', 'schema'],
                    'checklist': [
                        'Analyze data requirements',
                        'Design entity relationships',
                        'Create database schema',
                        'Define indexes and constraints',
                        'Plan data migration strategy',
                        'Review with team'
                    ],
                    'assignee_role': 'database_developer'
                },
                {
                    'title': 'API Design and Documentation',
                    'description': 'Design RESTful APIs and create comprehensive documentation for {project_name}',
                    'priority': 'medium',
                    'estimated_hours': 10,
                    'tags': ['api', 'documentation'],
                    'checklist': [
                        'Define API endpoints',
                        'Design request/response formats',
                        'Create API documentation',
                        'Define authentication methods',
                        'Plan rate limiting',
                        'Review API design'
                    ],
                    'assignee_role': 'backend_developer'
                }
            ],
            'Development': [
                {
                    'title': 'Frontend Development Setup',
                    'description': 'Set up frontend development environment and basic structure for {project_name}',
                    'priority': 'high',
                    'estimated_hours': 8,
                    'tags': ['frontend', 'setup'],
                    'checklist': [
                        'Set up development environment',
                        'Initialize project structure',
                        'Configure build tools',
                        'Set up routing',
                        'Implement basic layout',
                        'Configure state management'
                    ],
                    'assignee_role': 'frontend_developer'
                },
                {
                    'title': 'Backend API Implementation',
                    'description': 'Implement backend APIs and business logic for {project_name}',
                    'priority': 'high',
                    'estimated_hours': 24,
                    'tags': ['backend', 'api'],
                    'checklist': [
                        'Set up backend framework',
                        'Implement authentication',
                        'Create API endpoints',
                        'Implement business logic',
                        'Add input validation',
                        'Implement error handling'
                    ],
                    'assignee_role': 'backend_developer'
                },
                {
                    'title': 'Database Implementation',
                    'description': 'Implement database structure and data access layer for {project_name}',
                    'priority': 'high',
                    'estimated_hours': 16,
                    'tags': ['database', 'implementation'],
                    'checklist': [
                        'Create database tables',
                        'Implement data models',
                        'Create data access layer',
                        'Add database migrations',
                        'Implement data validation',
                        'Optimize database queries'
                    ],
                    'assignee_role': 'database_developer'
                },
                {
                    'title': 'Frontend Components Development',
                    'description': 'Develop reusable UI components and pages for {project_name}',
                    'priority': 'medium',
                    'estimated_hours': 20,
                    'tags': ['frontend', 'components'],
                    'checklist': [
                        'Create reusable components',
                        'Implement page layouts',
                        'Add form handling',
                        'Implement data fetching',
                        'Add loading states',
                        'Implement error handling'
                    ],
                    'assignee_role': 'frontend_developer'
                }
            ]
        }

        # E-commerce platform task templates
        ecommerce_templates = {
            'Market Research & Planning': [
                {
                    'title': 'E-commerce Market Analysis for {project_name}',
                    'description': 'Conduct comprehensive market research and competitive analysis for {project_name} e-commerce platform',
                    'priority': 'high',
                    'estimated_hours': 20,
                    'story_points': 8,
                    'tags': ['research', 'market-analysis', 'strategy'],
                    'checklist': [
                        'Analyze target market demographics and behavior',
                        'Research competitor platforms and features',
                        'Identify market gaps and opportunities',
                        'Define unique value proposition',
                        'Create customer personas',
                        'Document market requirements'
                    ],
                    'assignee_role': 'business_analyst',
                    'risk_level': 'low'
                },
                {
                    'title': 'E-commerce Platform Architecture Design',
                    'description': 'Design scalable architecture for {project_name} e-commerce platform with microservices approach',
                    'priority': 'high',
                    'estimated_hours': 24,
                    'story_points': 13,
                    'tags': ['architecture', 'scalability', 'microservices'],
                    'checklist': [
                        'Design microservices architecture',
                        'Plan database schema for products and orders',
                        'Define API specifications',
                        'Plan caching and CDN strategy',
                        'Design security architecture',
                        'Create deployment architecture'
                    ],
                    'assignee_role': 'solution_architect',
                    'risk_level': 'medium'
                }
            ],
            'Core Platform Development': [
                {
                    'title': 'Product Catalog System Development',
                    'description': 'Build comprehensive product catalog with categories, attributes, and inventory management for {project_name}',
                    'priority': 'high',
                    'estimated_hours': 40,
                    'story_points': 21,
                    'tags': ['backend', 'catalog', 'inventory'],
                    'checklist': [
                        'Implement product data models',
                        'Create category management system',
                        'Build product attribute framework',
                        'Implement inventory tracking',
                        'Create product search functionality',
                        'Add bulk product import/export'
                    ],
                    'assignee_role': 'backend_developer',
                    'risk_level': 'medium',
                    'dependencies': ['E-commerce Platform Architecture Design']
                },
                {
                    'title': 'Shopping Cart and Checkout Flow',
                    'description': 'Implement shopping cart functionality and streamlined checkout process for {project_name}',
                    'priority': 'high',
                    'estimated_hours': 32,
                    'story_points': 13,
                    'tags': ['frontend', 'cart', 'checkout'],
                    'checklist': [
                        'Build shopping cart UI components',
                        'Implement cart state management',
                        'Create checkout flow pages',
                        'Add guest checkout option',
                        'Implement cart persistence',
                        'Add cart abandonment recovery'
                    ],
                    'assignee_role': 'frontend_developer',
                    'risk_level': 'medium',
                    'dependencies': ['Product Catalog System Development']
                }
            ]
        }

        # SaaS application task templates
        saas_templates = {
            'Architecture & Infrastructure Design': [
                {
                    'title': 'Multi-Tenant Architecture Design for {project_name}',
                    'description': 'Design and implement multi-tenant architecture with data isolation for {project_name} SaaS platform',
                    'priority': 'high',
                    'estimated_hours': 32,
                    'story_points': 21,
                    'tags': ['architecture', 'multi-tenant', 'security'],
                    'checklist': [
                        'Design tenant isolation strategy',
                        'Plan database multi-tenancy approach',
                        'Create tenant provisioning workflow',
                        'Design cross-tenant security measures',
                        'Plan resource allocation per tenant',
                        'Document architecture decisions'
                    ],
                    'assignee_role': 'solution_architect',
                    'risk_level': 'high'
                }
            ],
            'Subscription & Billing System': [
                {
                    'title': 'Subscription Management System',
                    'description': 'Implement comprehensive subscription and billing management for {project_name} SaaS platform',
                    'priority': 'high',
                    'estimated_hours': 36,
                    'story_points': 21,
                    'tags': ['billing', 'subscription', 'payments'],
                    'checklist': [
                        'Design subscription plans and tiers',
                        'Implement billing cycle management',
                        'Create usage tracking system',
                        'Add payment method management',
                        'Implement invoice generation',
                        'Add subscription analytics'
                    ],
                    'assignee_role': 'backend_developer',
                    'risk_level': 'high'
                }
            ]
        }

        # DevOps infrastructure task templates
        devops_templates = {
            'CI/CD Pipeline Implementation': [
                {
                    'title': 'Automated CI/CD Pipeline Setup for {project_name}',
                    'description': 'Implement comprehensive CI/CD pipeline with automated testing and deployment for {project_name}',
                    'priority': 'high',
                    'estimated_hours': 28,
                    'story_points': 13,
                    'tags': ['cicd', 'automation', 'deployment'],
                    'checklist': [
                        'Set up version control workflows',
                        'Configure automated build process',
                        'Implement automated testing pipeline',
                        'Create deployment automation',
                        'Add rollback mechanisms',
                        'Configure pipeline monitoring'
                    ],
                    'assignee_role': 'devops_engineer',
                    'risk_level': 'medium'
                }
            ],
            'Infrastructure as Code': [
                {
                    'title': 'Infrastructure Automation with IaC',
                    'description': 'Implement Infrastructure as Code for {project_name} using Terraform and configuration management',
                    'priority': 'high',
                    'estimated_hours': 24,
                    'story_points': 13,
                    'tags': ['iac', 'terraform', 'automation'],
                    'checklist': [
                        'Create Terraform modules',
                        'Implement environment provisioning',
                        'Set up configuration management',
                        'Add infrastructure versioning',
                        'Create disaster recovery automation',
                        'Document infrastructure code'
                    ],
                    'assignee_role': 'devops_engineer',
                    'risk_level': 'medium'
                }
            ]
        }

        # Mobile app task templates
        mobile_app_templates = {
            'Concept & Planning': [
                {
                    'title': 'App Concept Definition for {project_name}',
                    'description': 'Define app concept, target audience, and core features for {project_name}',
                    'priority': 'high',
                    'estimated_hours': 12,
                    'tags': ['concept', 'planning'],
                    'checklist': [
                        'Define app purpose and goals',
                        'Identify target audience',
                        'Research competitor apps',
                        'Define core features',
                        'Create feature prioritization',
                        'Document app concept'
                    ],
                    'assignee_role': 'product_manager'
                }
            ],
            'Design & Prototyping': [
                {
                    'title': 'Mobile UI/UX Design for {project_name}',
                    'description': 'Create mobile-optimized user interface and experience design for {project_name}',
                    'priority': 'high',
                    'estimated_hours': 24,
                    'tags': ['mobile', 'design', 'ui'],
                    'checklist': [
                        'Create user flow diagrams',
                        'Design mobile wireframes',
                        'Create high-fidelity designs',
                        'Design app icons and assets',
                        'Create interactive prototype',
                        'Conduct usability testing'
                    ],
                    'assignee_role': 'mobile_designer'
                }
            ]
        }

        # General project task templates
        general_templates = {
            'Initiation & Planning': [
                {
                    'title': 'Project Charter for {project_name}',
                    'description': 'Create project charter defining scope, objectives, and stakeholders for {project_name}',
                    'priority': 'high',
                    'estimated_hours': 8,
                    'tags': ['charter', 'planning'],
                    'checklist': [
                        'Define project objectives',
                        'Identify stakeholders',
                        'Define project scope',
                        'Set success criteria',
                        'Identify risks and assumptions',
                        'Get charter approval'
                    ],
                    'assignee_role': 'project_manager'
                }
            ]
        }

        # Return appropriate templates based on project type
        template_map = {
            'web_application': web_app_templates,
            'mobile_app': mobile_app_templates,
            'ecommerce_platform': ecommerce_templates,
            'saas_application': saas_templates,
            'devops_infrastructure': devops_templates,
            'research_development': general_templates,  # Use general for now, can be expanded
            'event_management': general_templates,  # Use general for now, can be expanded
            'data_analysis': general_templates,
            'marketing_campaign': general_templates
        }

        return template_map.get(project_type, general_templates)

    def _generate_project_metadata(self, project_name: str, project_type: str, tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate project metadata including estimates and risk assessment"""

        # Calculate estimates based on tasks
        total_hours = sum(task.get('estimated_hours', 8) for task in tasks)
        total_days = max(1, total_hours // 8)  # Assuming 8-hour work days

        # Estimate budget (rough calculation)
        hourly_rate = 75  # Average hourly rate
        estimated_budget = total_hours * hourly_rate

        # Assess risk level based on project complexity
        risk_factors = {
            'web_application': 0.6,
            'mobile_app': 0.7,
            'data_analysis': 0.5,
            'marketing_campaign': 0.4,
            'general': 0.5
        }

        base_risk = risk_factors.get(project_type, 0.5)

        # Adjust risk based on project size
        if total_hours > 200:
            base_risk += 0.2
        elif total_hours > 100:
            base_risk += 0.1

        risk_level = 'low' if base_risk < 0.4 else 'medium' if base_risk < 0.7 else 'high'

        # Determine priority based on project type and complexity
        priority_mapping = {
            'web_application': 'high',
            'mobile_app': 'high',
            'data_analysis': 'medium',
            'marketing_campaign': 'medium',
            'general': 'medium'
        }

        priority = priority_mapping.get(project_type, 'medium')

        return {
            'estimated_duration': f"{total_days} days",
            'estimated_hours': total_hours,
            'estimated_budget': f"${estimated_budget:,.2f}",
            'risk_level': risk_level,
            'priority': priority,
            'complexity': 'high' if total_hours > 150 else 'medium' if total_hours > 75 else 'low',
            'team_size_recommendation': max(2, min(8, total_hours // 40)),
            'key_technologies': self._get_recommended_technologies(project_type),
            'success_metrics': [
                'On-time delivery',
                'Budget adherence',
                'Quality standards met',
                'Stakeholder satisfaction',
                'User acceptance'
            ]
        }

    def _get_recommended_technologies(self, project_type: str) -> List[str]:
        """Get recommended technologies based on project type"""

        tech_recommendations = {
            'web_application': [
                'React/Vue.js/Angular',
                'Node.js/Python/Java',
                'PostgreSQL/MongoDB',
                'Docker',
                'AWS/Azure/GCP'
            ],
            'mobile_app': [
                'React Native/Flutter',
                'Swift/Kotlin',
                'Firebase',
                'REST APIs',
                'App Store/Play Store'
            ],
            'data_analysis': [
                'Python/R',
                'Pandas/NumPy',
                'Jupyter Notebooks',
                'Tableau/Power BI',
                'SQL/NoSQL'
            ],
            'marketing_campaign': [
                'Google Analytics',
                'Social Media APIs',
                'Email Marketing Tools',
                'CRM Systems',
                'A/B Testing Tools'
            ],
            'general': [
                'Project Management Tools',
                'Communication Platforms',
                'Version Control',
                'Documentation Tools',
                'Quality Assurance Tools'
            ]
        }

        return tech_recommendations.get(project_type, tech_recommendations['general'])

    def _calculate_story_points(self, estimated_hours: int) -> int:
        """Calculate story points based on estimated hours using Fibonacci sequence"""
        if estimated_hours <= 2:
            return 1
        elif estimated_hours <= 4:
            return 2
        elif estimated_hours <= 8:
            return 3
        elif estimated_hours <= 16:
            return 5
        elif estimated_hours <= 24:
            return 8
        elif estimated_hours <= 40:
            return 13
        else:
            return 21

    def _assess_task_risk(self, task_template: Dict[str, Any]) -> str:
        """Assess risk level for a task based on complexity and dependencies"""
        estimated_hours = task_template.get('estimated_hours', 8)
        dependencies = task_template.get('dependencies', [])
        priority = task_template.get('priority', 'medium')

        risk_score = 0

        # Hours-based risk
        if estimated_hours > 30:
            risk_score += 3
        elif estimated_hours > 15:
            risk_score += 2
        elif estimated_hours > 8:
            risk_score += 1

        # Dependency-based risk
        risk_score += len(dependencies)

        # Priority-based risk
        if priority == 'high':
            risk_score += 2
        elif priority == 'urgent':
            risk_score += 3

        # Determine risk level
        if risk_score >= 6:
            return 'high'
        elif risk_score >= 3:
            return 'medium'
        else:
            return 'low'

    def _calculate_smart_deadline(self, task: Dict[str, Any], phase: Dict[str, Any], workflow: Dict[str, Any]) -> str:
        """Calculate smart deadline suggestions based on project timeline and dependencies"""
        from datetime import datetime, timedelta

        # Base calculation on phase duration and task position
        phase_duration = phase.get('duration_days', 14)
        task_position = task.get('task_index', 0)
        total_phase_tasks = 3  # Approximate tasks per phase

        # Calculate task duration within phase
        task_duration_ratio = (task_position + 1) / max(total_phase_tasks, 1)
        days_into_phase = int(phase_duration * task_duration_ratio)

        # Add phase offset
        phase_index = task.get('phase_index', 0)
        previous_phases_duration = sum(
            p.get('duration_days', 14) for i, p in enumerate(workflow['phases']) if i < phase_index
        )

        total_days_from_start = previous_phases_duration + days_into_phase

        # Calculate deadline from project start (assuming project starts today)
        start_date = datetime.now()
        deadline = start_date + timedelta(days=total_days_from_start)

        return deadline.strftime('%Y-%m-%d')

    def _recommend_resource_allocation(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Recommend resource allocation based on task complexity and type"""
        estimated_hours = task.get('estimated_hours', 8)
        assignee_role = task.get('assignee_role', 'team_member')
        priority = task.get('priority', 'medium')

        # Base resource recommendations
        resource_allocation = {
            'primary_assignee': assignee_role,
            'estimated_team_size': 1,
            'skill_requirements': [],
            'tools_needed': [],
            'review_required': False
        }

        # Adjust based on complexity
        if estimated_hours > 20:
            resource_allocation['estimated_team_size'] = 2
            resource_allocation['review_required'] = True
        elif estimated_hours > 40:
            resource_allocation['estimated_team_size'] = 3
            resource_allocation['review_required'] = True

        # Role-specific recommendations
        role_skills = {
            'frontend_developer': ['JavaScript', 'React/Vue/Angular', 'CSS', 'HTML'],
            'backend_developer': ['Python/Java/Node.js', 'Database', 'API Design', 'Security'],
            'ui_designer': ['Figma/Sketch', 'User Research', 'Prototyping', 'Design Systems'],
            'devops_engineer': ['Docker', 'Kubernetes', 'CI/CD', 'Cloud Platforms'],
            'business_analyst': ['Requirements Analysis', 'Documentation', 'Stakeholder Management'],
            'solution_architect': ['System Design', 'Architecture Patterns', 'Technology Selection']
        }

        resource_allocation['skill_requirements'] = role_skills.get(assignee_role, ['General Skills'])

        # Priority-based adjustments
        if priority in ['high', 'urgent']:
            resource_allocation['review_required'] = True
            if priority == 'urgent':
                resource_allocation['estimated_team_size'] = max(resource_allocation['estimated_team_size'], 2)

        return resource_allocation

    def _enhance_task_dependencies(self, tasks: List[Dict[str, Any]], project_type: str) -> List[Dict[str, Any]]:
        """Enhance task dependencies with intelligent mapping"""

        # Create task lookup by title for dependency resolution
        task_lookup = {task['title']: task for task in tasks}

        # Define common dependency patterns
        dependency_patterns = {
            'web_application': {
                'Frontend Development Setup': ['Technical Specification', 'UI/UX Design'],
                'Backend API Implementation': ['Database Design and Schema', 'API Design and Documentation'],
                'Frontend Components Development': ['Frontend Development Setup', 'Backend API Implementation']
            },
            'ecommerce_platform': {
                'Shopping Cart and Checkout Flow': ['Product Catalog System Development'],
                'Payment & Security Integration': ['Shopping Cart and Checkout Flow']
            },
            'saas_application': {
                'Subscription Management System': ['Multi-Tenant Architecture Design']
            }
        }

        # Apply dependency patterns
        patterns = dependency_patterns.get(project_type, {})

        for task in tasks:
            task_name_key = None
            # Find matching pattern key
            for pattern_key in patterns.keys():
                if pattern_key in task['title']:
                    task_name_key = pattern_key
                    break

            if task_name_key and task_name_key in patterns:
                # Add dependencies based on patterns
                for dep_pattern in patterns[task_name_key]:
                    for other_task in tasks:
                        if dep_pattern in other_task['title'] and other_task['title'] != task['title']:
                            if other_task['title'] not in task['dependencies']:
                                task['dependencies'].append(other_task['title'])

        # Add phase-based dependencies (tasks in later phases depend on earlier phases)
        for task in tasks:
            current_phase_index = task.get('phase_index', 0)
            if current_phase_index > 0:
                # Find tasks from previous phases to depend on
                for other_task in tasks:
                    other_phase_index = other_task.get('phase_index', 0)
                    if other_phase_index == current_phase_index - 1:
                        # Add dependency on key tasks from previous phase
                        if other_task.get('priority') == 'high' and other_task['title'] not in task['dependencies']:
                            task['dependencies'].append(other_task['title'])
                            break  # Only add one key dependency per previous phase

        return tasks

    def _adapt_workflow_for_team(self, phases: List[Dict[str, Any]], team_size: int, team_experience: str, project_type: str) -> List[Dict[str, Any]]:
        """Adapt workflow phases based on team characteristics"""

        # Experience-based duration adjustments
        experience_multipliers = {
            'junior': 1.3,      # 30% longer for junior teams
            'intermediate': 1.0, # Baseline
            'senior': 0.8,      # 20% faster for senior teams
            'expert': 0.7       # 30% faster for expert teams
        }

        # Team size adjustments (diminishing returns after optimal size)
        def get_team_size_multiplier(size: int) -> float:
            if size <= 2:
                return 1.2  # Small teams take longer
            elif size <= 5:
                return 1.0  # Optimal size
            elif size <= 8:
                return 0.9  # Slightly faster with more people
            else:
                return 1.1  # Too many people, coordination overhead

        experience_mult = experience_multipliers.get(team_experience, 1.0)
        team_size_mult = get_team_size_multiplier(team_size)

        # Apply adjustments
        for phase in phases:
            original_duration = phase['duration_days']
            adjusted_duration = int(original_duration * experience_mult * team_size_mult)
            phase['duration_days'] = max(1, adjusted_duration)  # Minimum 1 day

            # Add team-specific recommendations
            phase['team_recommendations'] = []

            if team_experience == 'junior':
                phase['team_recommendations'].extend([
                    'Assign senior mentor for guidance',
                    'Include extra time for learning and rework',
                    'Implement pair programming sessions'
                ])
            elif team_experience == 'expert':
                phase['team_recommendations'].extend([
                    'Consider advanced techniques and optimizations',
                    'Leverage team expertise for innovation',
                    'Mentor junior team members if available'
                ])

            if team_size > 6:
                phase['team_recommendations'].append('Break into smaller sub-teams to reduce coordination overhead')
            elif team_size < 3:
                phase['team_recommendations'].append('Consider bringing in additional resources for complex phases')

        return phases

    def _identify_parallel_execution_opportunities(self, phases: List[Dict[str, Any]], project_type: str) -> List[Dict[str, Any]]:
        """Identify opportunities for parallel task execution"""

        parallel_opportunities = []

        # Project-type specific parallel opportunities
        parallel_patterns = {
            'web_application': [
                {
                    'phase': 'Development',
                    'parallel_tasks': ['Frontend Development', 'Backend API Implementation'],
                    'description': 'Frontend and backend development can proceed in parallel after API design is complete',
                    'coordination_required': 'Regular API contract reviews and integration testing'
                }
            ],
            'ecommerce_platform': [
                {
                    'phase': 'Core Platform Development',
                    'parallel_tasks': ['Product Catalog System', 'User Management System'],
                    'description': 'Product catalog and user systems can be developed independently',
                    'coordination_required': 'Shared database schema coordination'
                },
                {
                    'phase': 'Advanced Features',
                    'parallel_tasks': ['Search Functionality', 'Recommendation Engine'],
                    'description': 'Search and recommendations can be developed in parallel',
                    'coordination_required': 'Data format standardization'
                }
            ],
            'saas_application': [
                {
                    'phase': 'Core Application Development',
                    'parallel_tasks': ['Multi-tenant Core', 'API Development'],
                    'description': 'Core application and API layer can be developed simultaneously',
                    'coordination_required': 'API contract definition and regular integration'
                }
            ]
        }

        return parallel_patterns.get(project_type, [])

    def _generate_quality_gates(self, phases: List[Dict[str, Any]], project_type: str) -> List[Dict[str, Any]]:
        """Generate quality gates and review checkpoints"""

        quality_gates = []

        for i, phase in enumerate(phases):
            gate = {
                'phase': phase['name'],
                'gate_name': f"{phase['name']} Quality Gate",
                'criteria': [],
                'reviewers': [],
                'artifacts_required': phase.get('deliverables', [])
            }

            # Common quality criteria
            gate['criteria'].extend([
                'All planned deliverables completed',
                'Code review completed (if applicable)',
                'Testing completed with acceptable results',
                'Documentation updated',
                'Stakeholder approval obtained'
            ])

            # Phase-specific criteria
            if 'design' in phase['name'].lower():
                gate['criteria'].extend([
                    'Design consistency validated',
                    'Accessibility requirements met',
                    'User experience validated'
                ])
                gate['reviewers'].extend(['UI/UX Designer', 'Product Manager'])

            elif 'development' in phase['name'].lower():
                gate['criteria'].extend([
                    'Code quality standards met',
                    'Security review completed',
                    'Performance benchmarks achieved'
                ])
                gate['reviewers'].extend(['Technical Lead', 'Security Reviewer'])

            elif 'testing' in phase['name'].lower():
                gate['criteria'].extend([
                    'Test coverage targets met',
                    'Critical bugs resolved',
                    'Performance testing completed'
                ])
                gate['reviewers'].extend(['QA Lead', 'Performance Engineer'])

            # Default reviewers
            if not gate['reviewers']:
                gate['reviewers'] = ['Project Manager', 'Technical Lead']

            quality_gates.append(gate)

        return quality_gates

    def _generate_milestone_celebrations(self, phases: List[Dict[str, Any]], project_name: str) -> List[Dict[str, Any]]:
        """Generate milestone celebrations to boost team morale"""

        celebrations = []

        celebration_ideas = [
            'Team lunch or dinner',
            'Virtual celebration meeting',
            'Recognition in company newsletter',
            'Small team gifts or swag',
            'Extra time off or flexible hours',
            'Team building activity',
            'Public recognition in all-hands meeting',
            'Project showcase presentation'
        ]

        for i, phase in enumerate(phases):
            celebration = {
                'milestone': f"{phase['name']} Completion",
                'celebration_type': celebration_ideas[i % len(celebration_ideas)],
                'description': f"Celebrate the successful completion of {phase['name']} for {project_name}",
                'participants': 'All team members',
                'timing': 'Within 1-2 days of phase completion'
            }

            # Special celebrations for major milestones
            if i == 0:  # First phase
                celebration['celebration_type'] = 'Project kickoff celebration'
                celebration['description'] = f"Celebrate the successful start and first milestone of {project_name}"
            elif i == len(phases) - 1:  # Final phase
                celebration['celebration_type'] = 'Project completion celebration'
                celebration['description'] = f"Celebrate the successful completion of {project_name}"
                celebration['participants'] = 'All team members and stakeholders'

            celebrations.append(celebration)

        return celebrations

    def _select_methodology(self, team_size: int, team_experience: str, project_type: str) -> str:
        """Select appropriate project methodology based on team and project characteristics"""

        # Small teams with high experience
        if team_size <= 3 and team_experience in ['senior', 'expert']:
            return 'Lean Startup with rapid iterations'

        # Large teams
        elif team_size > 8:
            return 'Scaled Agile (SAFe) with multiple scrum teams'

        # Complex technical projects
        elif project_type in ['saas_application', 'devops_infrastructure']:
            return 'DevOps-enhanced Agile with continuous delivery'

        # Research projects
        elif project_type == 'research_development':
            return 'Stage-Gate process with iterative research cycles'

        # Default for most projects
        else:
            return 'Agile Scrum with 2-week sprints'

    def _recommend_sprint_length(self, team_size: int, team_experience: str) -> str:
        """Recommend sprint length based on team characteristics"""

        if team_experience == 'junior':
            return '1 week (shorter cycles for faster feedback)'
        elif team_size > 8:
            return '3 weeks (longer cycles for coordination)'
        else:
            return '2 weeks (standard agile sprint)'

    def _recommend_communication_frequency(self, team_size: int) -> Dict[str, str]:
        """Recommend communication frequency based on team size"""

        if team_size <= 3:
            return {
                'daily_standups': 'Every other day',
                'sprint_reviews': 'End of each sprint',
                'retrospectives': 'End of each sprint',
                'stakeholder_updates': 'Weekly'
            }
        elif team_size > 8:
            return {
                'daily_standups': 'Daily (by sub-team)',
                'sprint_reviews': 'End of each sprint',
                'retrospectives': 'End of each sprint',
                'stakeholder_updates': 'Bi-weekly',
                'cross_team_sync': 'Twice weekly'
            }
        else:
            return {
                'daily_standups': 'Daily',
                'sprint_reviews': 'End of each sprint',
                'retrospectives': 'End of each sprint',
                'stakeholder_updates': 'Weekly'
            }

    async def create_project_from_confirmation(
        self,
        confirmation_data: Dict[str, Any],
        final_tasks: List[Dict[str, Any]],
        workflow: Dict[str, Any],
        user_id: str
    ) -> Dict[str, Any]:
        """Create actual project from confirmed preview data"""
        try:
            import uuid
            # This would create the actual project, board, and tasks
            project_id = str(uuid.uuid4())

            # Create project structure
            project = {
                "id": project_id,
                "name": confirmation_data.get("name"),
                "description": confirmation_data.get("description"),
                "organization_id": confirmation_data.get("organization_id"),
                "created_by": user_id,
                "created_at": datetime.utcnow().isoformat(),
                "status": "active",
                "workflow": workflow,
                "tasks": final_tasks
            }

            return {
                "project": project,
                "tasks_created": len(final_tasks),
                "workflow": workflow
            }

        except Exception as e:
            logger.error(f"Project creation from confirmation failed: {str(e)}")
            raise Exception(f"Failed to create project: {str(e)}")

    async def update_project_workflow(
        self,
        project_id: str,
        phase: str,
        workflow_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update project workflow for specific phase"""
        try:
            # Update workflow based on phase
            updated_workflow = workflow_data.copy()
            updated_workflow["last_updated"] = datetime.utcnow().isoformat()
            updated_workflow["updated_phase"] = phase

            # Phase-specific updates
            if phase == "configure":
                updated_workflow["configuration"] = workflow_data
            elif phase == "overview":
                updated_workflow["overview"] = workflow_data
            elif phase == "tech_stack":
                updated_workflow["technology"] = workflow_data
            elif phase == "workflows":
                updated_workflow["processes"] = workflow_data
            elif phase == "tasks":
                updated_workflow["task_structure"] = workflow_data

            return updated_workflow

        except Exception as e:
            logger.error(f"Workflow update failed: {str(e)}")
            raise Exception(f"Failed to update workflow: {str(e)}")

    async def generate_smart_suggestions(
        self,
        project_id: str,
        suggestion_type: str,
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate smart suggestions for project optimization"""
        try:
            suggestions = []

            if suggestion_type == "task_optimization":
                suggestions = self._generate_task_optimization_suggestions(context)
            elif suggestion_type == "dependency":
                suggestions = self._generate_dependency_suggestions(context)
            elif suggestion_type == "priority":
                suggestions = self._generate_priority_suggestions(context)
            elif suggestion_type == "assignment":
                suggestions = self._generate_assignment_suggestions(context)

            return suggestions

        except Exception as e:
            logger.error(f"Smart suggestions generation failed: {str(e)}")
            raise Exception(f"Failed to generate suggestions: {str(e)}")

    async def apply_smart_suggestion(
        self,
        suggestion_id: str,
        project_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Apply a smart suggestion to the project"""
        try:
            # This would apply the suggestion to the actual project
            result = {
                "suggestion_id": suggestion_id,
                "project_id": project_id,
                "applied_by": user_id,
                "applied_at": datetime.utcnow().isoformat(),
                "status": "applied"
            }

            return result

        except Exception as e:
            logger.error(f"Suggestion application failed: {str(e)}")
            raise Exception(f"Failed to apply suggestion: {str(e)}")

    async def get_project_templates(
        self,
        project_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get available project templates"""
        try:
            templates = [
                {
                    "id": "web_app_template",
                    "name": "Web Application Template",
                    "type": "web_application",
                    "description": "Complete web application with frontend, backend, and database",
                    "phases": ["Planning", "Design", "Development", "Testing", "Deployment"],
                    "estimated_duration": 12,
                    "complexity": "medium"
                },
                {
                    "id": "mobile_app_template",
                    "name": "Mobile App Template",
                    "type": "mobile_app",
                    "description": "Cross-platform mobile application development",
                    "phases": ["Research", "Design", "Development", "Testing", "Publishing"],
                    "estimated_duration": 16,
                    "complexity": "high"
                },
                {
                    "id": "ecommerce_template",
                    "name": "E-commerce Platform Template",
                    "type": "ecommerce_platform",
                    "description": "Full-featured e-commerce platform with payment processing",
                    "phases": ["Planning", "Core Development", "Payment Integration", "Testing", "Launch"],
                    "estimated_duration": 20,
                    "complexity": "high"
                }
            ]

            if project_type:
                templates = [t for t in templates if t["type"] == project_type]

            return templates

        except Exception as e:
            logger.error(f"Template retrieval failed: {str(e)}")
            raise Exception(f"Failed to get templates: {str(e)}")

    async def setup_project_integrations(
        self,
        project_id: str,
        workflow: Dict[str, Any]
    ):
        """Setup project integrations in background"""
        try:
            # This would setup various integrations like calendar, notifications, etc.
            logger.info(f"Setting up integrations for project {project_id}")

            # Simulate integration setup
            integrations = ["calendar", "notifications", "analytics"]
            for integration in integrations:
                logger.info(f"Setting up {integration} integration for project {project_id}")

        except Exception as e:
            logger.error(f"Integration setup failed: {str(e)}")

    def _generate_task_optimization_suggestions(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate task optimization suggestions"""
        suggestions = [
            {
                "id": "opt_1",
                "type": "task_optimization",
                "title": "Break down large tasks",
                "description": "Consider breaking tasks with >40 hours into smaller subtasks",
                "impact": "high",
                "effort": "low"
            },
            {
                "id": "opt_2",
                "type": "task_optimization",
                "title": "Parallelize independent tasks",
                "description": "Run independent tasks in parallel to reduce timeline",
                "impact": "medium",
                "effort": "medium"
            }
        ]
        return suggestions

    def _generate_dependency_suggestions(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate dependency optimization suggestions"""
        suggestions = [
            {
                "id": "dep_1",
                "type": "dependency",
                "title": "Reduce critical path dependencies",
                "description": "Minimize dependencies on critical path tasks",
                "impact": "high",
                "effort": "medium"
            }
        ]
        return suggestions

    def _generate_priority_suggestions(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate priority optimization suggestions"""
        suggestions = [
            {
                "id": "pri_1",
                "type": "priority",
                "title": "Prioritize high-impact tasks",
                "description": "Focus on tasks with highest business value first",
                "impact": "high",
                "effort": "low"
            }
        ]
        return suggestions

    def _generate_assignment_suggestions(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate assignment optimization suggestions"""
        suggestions = [
            {
                "id": "assign_1",
                "type": "assignment",
                "title": "Balance workload across team",
                "description": "Redistribute tasks to balance team member workloads",
                "impact": "medium",
                "effort": "low"
            }
        ]
        return suggestions
