"""
AI-powered checklist generation service
"""
import asyncio
import re
from typing import List, Dict, Optional
from datetime import datetime


class AIChecklistService:
    """AI service for generating intelligent checklist items"""
    
    # Task type patterns and their associated checklist templates
    TASK_TYPE_PATTERNS = {
        'development': {
            'keywords': ['develop', 'code', 'implement', 'build', 'create', 'api', 'frontend', 'backend', 'database', 'feature'],
            'templates': [
                'Review requirements and acceptance criteria',
                'Set up development environment',
                'Create technical design document',
                'Implement core functionality',
                'Write unit tests',
                'Perform code review',
                'Test functionality manually',
                'Update documentation'
            ]
        },
        'design': {
            'keywords': ['design', 'ui', 'ux', 'mockup', 'wireframe', 'prototype', 'visual', 'interface', 'layout'],
            'templates': [
                'Research user requirements',
                'Create initial wireframes',
                'Design visual mockups',
                'Review with stakeholders',
                'Iterate based on feedback',
                'Create design specifications',
                'Prepare assets for development',
                'Conduct usability testing'
            ]
        },
        'testing': {
            'keywords': ['test', 'qa', 'quality', 'bug', 'verify', 'validate', 'check'],
            'templates': [
                'Review test requirements',
                'Create test plan',
                'Set up test environment',
                'Execute test cases',
                'Document test results',
                'Report bugs and issues',
                'Verify bug fixes',
                'Sign off on testing'
            ]
        },
        'research': {
            'keywords': ['research', 'analyze', 'investigate', 'study', 'explore', 'evaluate'],
            'templates': [
                'Define research objectives',
                'Identify information sources',
                'Gather relevant data',
                'Analyze findings',
                'Document insights',
                'Present recommendations',
                'Review with team',
                'Plan next steps'
            ]
        },
        'deployment': {
            'keywords': ['deploy', 'release', 'launch', 'production', 'staging', 'environment'],
            'templates': [
                'Prepare deployment checklist',
                'Review code changes',
                'Run pre-deployment tests',
                'Deploy to staging environment',
                'Verify staging deployment',
                'Deploy to production',
                'Monitor system health',
                'Document deployment notes'
            ]
        },
        'meeting': {
            'keywords': ['meeting', 'discussion', 'review', 'planning', 'standup', 'retrospective'],
            'templates': [
                'Prepare meeting agenda',
                'Send calendar invites',
                'Gather required materials',
                'Facilitate discussion',
                'Take meeting notes',
                'Assign action items',
                'Send meeting summary',
                'Follow up on action items'
            ]
        }
    }
    
    # Priority-based checklist additions
    PRIORITY_ADDITIONS = {
        'high': [
            'Notify stakeholders of high priority',
            'Set up monitoring and alerts',
            'Prepare rollback plan'
        ],
        'urgent': [
            'Notify stakeholders immediately',
            'Set up real-time monitoring',
            'Prepare emergency rollback plan',
            'Schedule status updates'
        ],
        'medium': [
            'Review with team lead',
            'Update project timeline'
        ],
        'low': [
            'Document lessons learned'
        ]
    }
    
    # Project context-based additions
    PROJECT_CONTEXT_ADDITIONS = {
        'e-commerce': [
            'Test payment integration',
            'Verify security compliance',
            'Check mobile responsiveness'
        ],
        'mobile': [
            'Test on multiple devices',
            'Verify app store guidelines',
            'Check performance metrics'
        ],
        'api': [
            'Update API documentation',
            'Test rate limiting',
            'Verify authentication'
        ]
    }

    @classmethod
    def detect_task_type(cls, title: str, description: str = '') -> str:
        """Detect task type based on title and description"""
        content = f"{title} {description}".lower()
        
        best_match = 'development'
        max_score = 0
        
        for task_type, pattern in cls.TASK_TYPE_PATTERNS.items():
            score = sum(1 for keyword in pattern['keywords'] if keyword in content)
            
            if score > max_score:
                max_score = score
                best_match = task_type
        
        return best_match

    @classmethod
    def customize_checklist_items(cls, items: List[str], title: str, description: str = '') -> List[str]:
        """Customize checklist items based on specific task content"""
        content = f"{title} {description}".lower()
        
        customized_items = []
        for item in items:
            customized_item = item
            
            # API-specific customizations
            if 'api' in content:
                customized_item = customized_item.replace('functionality', 'API endpoints')
                customized_item = customized_item.replace('feature', 'API feature')
            
            # UI-specific customizations
            if 'ui' in content or 'interface' in content:
                customized_item = customized_item.replace('functionality', 'UI components')
                customized_item = customized_item.replace('feature', 'UI feature')
            
            # Database-specific customizations
            if 'database' in content or 'db' in content:
                customized_item = customized_item.replace('functionality', 'database operations')
                customized_item = customized_item.replace('feature', 'database feature')
            
            customized_items.append(customized_item)
        
        return customized_items

    @classmethod
    def calculate_confidence(cls, item: str, title: str, description: str = '') -> int:
        """Calculate confidence score for a checklist item"""
        content = f"{title} {description}".lower()
        item_words = item.lower().split()
        
        # Base confidence
        confidence = 70
        
        # Increase confidence if item words appear in task content
        matching_words = [word for word in item_words if len(word) > 3 and word in content]
        
        if item_words:
            confidence += (len(matching_words) / len(item_words)) * 20
        
        # Cap at 95% to indicate AI uncertainty
        return min(95, round(confidence))

    @classmethod
    async def generate_ai_checklist(
        cls,
        title: str,
        description: str = '',
        priority: str = 'medium',
        project_type: Optional[str] = None
    ) -> Dict:
        """Generate contextual checklist items based on task content"""
        try:
            # Simulate AI processing delay
            await asyncio.sleep(0.8)
            
            task_type = cls.detect_task_type(title, description)
            base_template = cls.TASK_TYPE_PATTERNS.get(task_type, cls.TASK_TYPE_PATTERNS['development'])['templates']
            
            # Start with base template items
            checklist_items = base_template.copy()
            
            # Add priority-specific items
            if priority in cls.PRIORITY_ADDITIONS:
                checklist_items.extend(cls.PRIORITY_ADDITIONS[priority])
            
            # Add project context items
            if project_type and project_type in cls.PROJECT_CONTEXT_ADDITIONS:
                checklist_items.extend(cls.PROJECT_CONTEXT_ADDITIONS[project_type])
            
            # Customize items based on task content
            checklist_items = cls.customize_checklist_items(checklist_items, title, description)
            
            # Limit to 3-8 items and add metadata
            final_items = []
            for i, item in enumerate(checklist_items[:8]):
                final_items.append({
                    'text': item,
                    'completed': False,
                    'position': i,
                    'ai_generated': True,
                    'confidence': cls.calculate_confidence(item, title, description),
                    'metadata': {
                        'task_type': task_type,
                        'generated_at': datetime.utcnow().isoformat(),
                        'priority': priority
                    }
                })
            
            return {
                'success': True,
                'items': final_items,
                'metadata': {
                    'task_type': task_type,
                    'confidence': sum(item['confidence'] for item in final_items) // len(final_items) if final_items else 0,
                    'generated_at': datetime.utcnow().isoformat(),
                    'item_count': len(final_items)
                }
            }
            
        except Exception as error:
            return {
                'success': False,
                'error': str(error),
                'items': []
            }

    @classmethod
    def get_suggested_items(cls, task_type: str = 'development') -> List[str]:
        """Get suggested checklist items for manual addition"""
        suggestions = {
            'development': [
                'Set up CI/CD pipeline',
                'Perform security review',
                'Optimize performance',
                'Add error handling'
            ],
            'design': [
                'Create style guide',
                'Test accessibility',
                'Optimize for mobile',
                'Validate with users'
            ],
            'testing': [
                'Automate test cases',
                'Test edge cases',
                'Performance testing',
                'Security testing'
            ]
        }
        
        return suggestions.get(task_type, suggestions['development'])


# Create singleton instance
ai_checklist_service = AIChecklistService()
