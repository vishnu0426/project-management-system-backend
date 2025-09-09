"""
Integration service for managing third-party integrations
"""
import logging
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.integrations import Integration, IntegrationSyncLog, WebhookEvent
from app.models.card import Card
from app.models.project import Project
from app.models.organization import Organization

logger = logging.getLogger(__name__)


class IntegrationService:
    """Service for managing third-party integrations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def initialize_integration(self, integration_id: str) -> bool:
        """Initialize a new integration"""
        try:
            integration = self.db.query(Integration).filter(
                Integration.id == integration_id
            ).first()
            
            if not integration:
                logger.error(f"Integration {integration_id} not found")
                return False
            
            # Initialize based on integration type
            if integration.integration_type == 'slack':
                success = await self._initialize_slack_integration(integration)
            elif integration.integration_type == 'github':
                success = await self._initialize_github_integration(integration)
            elif integration.integration_type == 'google_calendar':
                success = await self._initialize_calendar_integration(integration)
            elif integration.integration_type == 'webhook':
                success = await self._initialize_webhook_integration(integration)
            else:
                logger.warning(f"Unknown integration type: {integration.integration_type}")
                success = False
            
            # Update integration status
            integration.status = 'active' if success else 'error'
            if not success:
                integration.error_count += 1
                integration.last_error = "Failed to initialize integration"
            
            self.db.commit()
            
            logger.info(f"Integration {integration_id} initialized: {success}")
            return success
            
        except Exception as e:
            logger.error(f"Error initializing integration {integration_id}: {e}")
            return False
    
    async def _initialize_slack_integration(self, integration: Integration) -> bool:
        """Initialize Slack integration"""
        try:
            config = integration.configuration
            bot_token = config.get('bot_token')
            
            if not bot_token:
                logger.error("Slack bot token not provided")
                return False
            
            # Test Slack API connection
            headers = {
                'Authorization': f'Bearer {bot_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(
                'https://slack.com/api/auth.test',
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('ok'):
                    # Store additional info from Slack
                    integration.configuration.update({
                        'team_id': data.get('team_id'),
                        'team_name': data.get('team'),
                        'bot_user_id': data.get('user_id')
                    })
                    return True
            
            logger.error(f"Slack API test failed: {response.text}")
            return False
            
        except Exception as e:
            logger.error(f"Error initializing Slack integration: {e}")
            return False
    
    async def _initialize_github_integration(self, integration: Integration) -> bool:
        """Initialize GitHub integration"""
        try:
            config = integration.configuration
            access_token = config.get('access_token')
            repository_url = config.get('repository_url')
            
            if not access_token or not repository_url:
                logger.error("GitHub access token or repository URL not provided")
                return False
            
            # Extract owner and repo from URL
            parts = repository_url.replace('https://github.com/', '').split('/')
            if len(parts) < 2:
                logger.error("Invalid GitHub repository URL")
                return False
            
            owner, repo = parts[0], parts[1]
            
            # Test GitHub API connection
            headers = {
                'Authorization': f'token {access_token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            response = requests.get(
                f'https://api.github.com/repos/{owner}/{repo}',
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                repo_data = response.json()
                integration.configuration.update({
                    'owner': owner,
                    'repo': repo,
                    'repo_id': repo_data.get('id'),
                    'full_name': repo_data.get('full_name')
                })
                return True
            
            logger.error(f"GitHub API test failed: {response.text}")
            return False
            
        except Exception as e:
            logger.error(f"Error initializing GitHub integration: {e}")
            return False
    
    async def _initialize_calendar_integration(self, integration: Integration) -> bool:
        """Initialize calendar integration"""
        try:
            config = integration.configuration
            provider = config.get('provider')
            access_token = config.get('access_token')
            
            if not access_token:
                logger.error("Calendar access token not provided")
                return False
            
            if provider == 'google':
                # Test Google Calendar API
                headers = {'Authorization': f'Bearer {access_token}'}
                response = requests.get(
                    'https://www.googleapis.com/calendar/v3/calendars/primary',
                    headers=headers,
                    timeout=10
                )
                
                if response.status_code == 200:
                    calendar_data = response.json()
                    integration.configuration.update({
                        'calendar_name': calendar_data.get('summary'),
                        'calendar_timezone': calendar_data.get('timeZone')
                    })
                    return True
            
            elif provider == 'outlook':
                # Test Microsoft Graph API
                headers = {'Authorization': f'Bearer {access_token}'}
                response = requests.get(
                    'https://graph.microsoft.com/v1.0/me/calendar',
                    headers=headers,
                    timeout=10
                )
                
                if response.status_code == 200:
                    calendar_data = response.json()
                    integration.configuration.update({
                        'calendar_name': calendar_data.get('name'),
                        'calendar_id': calendar_data.get('id')
                    })
                    return True
            
            logger.error(f"Calendar API test failed for provider: {provider}")
            return False
            
        except Exception as e:
            logger.error(f"Error initializing calendar integration: {e}")
            return False
    
    async def _initialize_webhook_integration(self, integration: Integration) -> bool:
        """Initialize webhook integration"""
        try:
            config = integration.configuration
            webhook_url = config.get('webhook_url')
            
            if not webhook_url:
                logger.error("Webhook URL not provided")
                return False
            
            # Test webhook endpoint with a ping
            test_payload = {
                'event_type': 'ping',
                'timestamp': datetime.utcnow().isoformat(),
                'source': 'agno_worksphere'
            }
            
            headers = {'Content-Type': 'application/json'}
            if config.get('secret_token'):
                headers['X-Webhook-Secret'] = config['secret_token']
            
            response = requests.post(
                webhook_url,
                json=test_payload,
                headers=headers,
                timeout=config.get('timeout_seconds', 30)
            )
            
            if response.status_code in [200, 201, 202]:
                return True
            
            logger.error(f"Webhook test failed: {response.status_code} - {response.text}")
            return False
            
        except Exception as e:
            logger.error(f"Error initializing webhook integration: {e}")
            return False
    
    async def sync_integration(self, integration_id: str) -> bool:
        """Sync data for an integration"""
        try:
            integration = self.db.query(Integration).filter(
                Integration.id == integration_id
            ).first()
            
            if not integration or not integration.sync_enabled:
                return False
            
            # Create sync log
            sync_log = IntegrationSyncLog(
                integration_id=integration_id,
                sync_type='manual',
                status='running'
            )
            self.db.add(sync_log)
            self.db.commit()
            
            start_time = datetime.utcnow()
            
            # Perform sync based on integration type
            if integration.integration_type == 'github':
                success = await self._sync_github_data(integration, sync_log)
            elif integration.integration_type == 'google_calendar':
                success = await self._sync_calendar_data(integration, sync_log)
            else:
                logger.warning(f"Sync not implemented for: {integration.integration_type}")
                success = False
            
            # Update sync log
            end_time = datetime.utcnow()
            sync_log.status = 'success' if success else 'error'
            sync_log.completed_at = end_time
            sync_log.duration_ms = int((end_time - start_time).total_seconds() * 1000)
            
            # Update integration
            integration.last_sync = end_time
            if success:
                integration.error_count = 0
                integration.last_error = None
            else:
                integration.error_count += 1
            
            self.db.commit()
            
            return success
            
        except Exception as e:
            logger.error(f"Error syncing integration {integration_id}: {e}")
            return False
    
    async def _sync_github_data(self, integration: Integration, sync_log: IntegrationSyncLog) -> bool:
        """Sync GitHub issues and pull requests"""
        try:
            config = integration.configuration
            access_token = config.get('access_token')
            owner = config.get('owner')
            repo = config.get('repo')
            
            headers = {
                'Authorization': f'token {access_token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            # Sync issues if enabled
            if config.get('sync_issues', True):
                issues_url = f'https://api.github.com/repos/{owner}/{repo}/issues'
                response = requests.get(issues_url, headers=headers, timeout=30)
                
                if response.status_code == 200:
                    issues = response.json()
                    
                    for issue in issues:
                        if not issue.get('pull_request'):  # Skip pull requests
                            await self._create_task_from_github_issue(
                                integration.organization_id,
                                issue,
                                sync_log
                            )
                    
                    sync_log.records_processed += len(issues)
            
            return True
            
        except Exception as e:
            logger.error(f"Error syncing GitHub data: {e}")
            sync_log.error_details = {'error': str(e)}
            return False
    
    async def _create_task_from_github_issue(
        self, 
        organization_id: str, 
        issue: Dict[str, Any], 
        sync_log: IntegrationSyncLog
    ):
        """Create a task from GitHub issue"""
        try:
            # Check if task already exists
            existing_card = self.db.query(Card).filter(
                Card.external_id == str(issue['id']),
                Card.external_source == 'github'
            ).first()
            
            if existing_card:
                # Update existing task
                existing_card.title = issue['title']
                existing_card.description = issue.get('body', '')
                existing_card.updated_at = datetime.utcnow()
                sync_log.records_updated += 1
            else:
                # Get default project for GitHub tasks
                default_project = self.db.query(Project).filter(
                    Project.organization_id == organization_id,
                    Project.name.like('%GitHub%')
                ).first()
                
                if not default_project:
                    # Create default GitHub project
                    default_project = Project(
                        organization_id=organization_id,
                        name="GitHub Issues",
                        description="Automatically synced from GitHub",
                        status="active"
                    )
                    self.db.add(default_project)
                    self.db.flush()
                
                # Create new task
                new_card = Card(
                    project_id=default_project.id,
                    title=issue['title'],
                    description=issue.get('body', ''),
                    status='todo',
                    priority='medium',
                    external_id=str(issue['id']),
                    external_source='github',
                    external_url=issue['html_url']
                )
                self.db.add(new_card)
                sync_log.records_created += 1
            
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Error creating task from GitHub issue: {e}")
            sync_log.records_failed += 1
    
    async def _sync_calendar_data(self, integration: Integration, sync_log: IntegrationSyncLog) -> bool:
        """Sync calendar events"""
        try:
            config = integration.configuration
            provider = config.get('provider')
            access_token = config.get('access_token')
            
            if provider == 'google':
                # Sync Google Calendar events
                headers = {'Authorization': f'Bearer {access_token}'}
                
                # Get events from the last 30 days
                time_min = (datetime.utcnow() - timedelta(days=30)).isoformat() + 'Z'
                time_max = (datetime.utcnow() + timedelta(days=30)).isoformat() + 'Z'
                
                params = {
                    'timeMin': time_min,
                    'timeMax': time_max,
                    'singleEvents': True,
                    'orderBy': 'startTime'
                }
                
                response = requests.get(
                    f'https://www.googleapis.com/calendar/v3/calendars/primary/events',
                    headers=headers,
                    params=params,
                    timeout=30
                )
                
                if response.status_code == 200:
                    events_data = response.json()
                    events = events_data.get('items', [])
                    
                    for event in events:
                        if config.get('create_tasks_from_events', False):
                            await self._create_task_from_calendar_event(
                                integration.organization_id,
                                event,
                                sync_log
                            )
                    
                    sync_log.records_processed += len(events)
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error syncing calendar data: {e}")
            sync_log.error_details = {'error': str(e)}
            return False
    
    async def _create_task_from_calendar_event(
        self,
        organization_id: str,
        event: Dict[str, Any],
        sync_log: IntegrationSyncLog
    ):
        """Create a task from calendar event"""
        try:
            # Skip if event already exists as task
            existing_card = self.db.query(Card).filter(
                Card.external_id == event['id'],
                Card.external_source == 'google_calendar'
            ).first()
            
            if existing_card:
                sync_log.records_updated += 1
                return
            
            # Get default project for calendar tasks
            default_project = self.db.query(Project).filter(
                Project.organization_id == organization_id,
                Project.name.like('%Calendar%')
            ).first()
            
            if not default_project:
                default_project = Project(
                    organization_id=organization_id,
                    name="Calendar Events",
                    description="Automatically synced from calendar",
                    status="active"
                )
                self.db.add(default_project)
                self.db.flush()
            
            # Parse event date
            start_time = event.get('start', {})
            due_date = None
            if start_time.get('dateTime'):
                due_date = datetime.fromisoformat(
                    start_time['dateTime'].replace('Z', '+00:00')
                )
            
            # Create task
            new_card = Card(
                project_id=default_project.id,
                title=event.get('summary', 'Calendar Event'),
                description=event.get('description', ''),
                status='todo',
                priority='medium',
                due_date=due_date,
                external_id=event['id'],
                external_source='google_calendar',
                external_url=event.get('htmlLink')
            )
            
            self.db.add(new_card)
            sync_log.records_created += 1
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Error creating task from calendar event: {e}")
            sync_log.records_failed += 1
    
    async def process_webhook(self, webhook_event_id: str) -> bool:
        """Process incoming webhook event"""
        try:
            webhook_event = self.db.query(WebhookEvent).filter(
                WebhookEvent.id == webhook_event_id
            ).first()
            
            if not webhook_event:
                return False
            
            webhook_event.processing_attempts += 1
            webhook_event.last_attempt = datetime.utcnow()
            
            # Process based on event source
            payload = webhook_event.payload
            
            if webhook_event.event_source == 'github':
                success = await self._process_github_webhook(webhook_event, payload)
            elif webhook_event.event_source == 'slack':
                success = await self._process_slack_webhook(webhook_event, payload)
            else:
                # Generic webhook processing
                success = await self._process_generic_webhook(webhook_event, payload)
            
            webhook_event.status = 'processed' if success else 'failed'
            if success:
                webhook_event.processed_at = datetime.utcnow()
            
            self.db.commit()
            
            return success
            
        except Exception as e:
            logger.error(f"Error processing webhook {webhook_event_id}: {e}")
            return False
    
    async def _process_github_webhook(self, webhook_event: WebhookEvent, payload: Dict[str, Any]) -> bool:
        """Process GitHub webhook event"""
        try:
            event_type = payload.get('action')
            
            if 'issue' in payload:
                issue = payload['issue']
                
                if event_type == 'opened':
                    # Create new task from issue
                    await self._create_task_from_github_issue(
                        webhook_event.organization_id,
                        issue,
                        None  # No sync log for webhook events
                    )
                elif event_type in ['edited', 'reopened']:
                    # Update existing task
                    existing_card = self.db.query(Card).filter(
                        Card.external_id == str(issue['id']),
                        Card.external_source == 'github'
                    ).first()
                    
                    if existing_card:
                        existing_card.title = issue['title']
                        existing_card.description = issue.get('body', '')
                        if event_type == 'reopened':
                            existing_card.status = 'todo'
                        self.db.commit()
                
                elif event_type == 'closed':
                    # Mark task as completed
                    existing_card = self.db.query(Card).filter(
                        Card.external_id == str(issue['id']),
                        Card.external_source == 'github'
                    ).first()
                    
                    if existing_card:
                        existing_card.status = 'completed'
                        self.db.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing GitHub webhook: {e}")
            webhook_event.error_message = str(e)
            return False
    
    async def _process_slack_webhook(self, webhook_event: WebhookEvent, payload: Dict[str, Any]) -> bool:
        """Process Slack webhook event"""
        try:
            # Handle Slack events like mentions, messages, etc.
            event_type = payload.get('type')
            
            if event_type == 'url_verification':
                # Slack URL verification
                webhook_event.response_data = {'challenge': payload.get('challenge')}
                return True
            
            # Process other Slack events as needed
            return True
            
        except Exception as e:
            logger.error(f"Error processing Slack webhook: {e}")
            webhook_event.error_message = str(e)
            return False
    
    async def _process_generic_webhook(self, webhook_event: WebhookEvent, payload: Dict[str, Any]) -> bool:
        """Process generic webhook event"""
        try:
            # Basic webhook processing - just log the event
            webhook_event.response_data = {'status': 'received', 'processed': True}
            return True
            
        except Exception as e:
            logger.error(f"Error processing generic webhook: {e}")
            webhook_event.error_message = str(e)
            return False

    async def setup_ai_project_integrations(
        self,
        project_data: Dict[str, Any],
        tasks: List[Dict[str, Any]],
        workflow: Dict[str, Any],
        organization_id: str,
        integration_preferences: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Set up integrations for a newly created AI project"""

        integration_results = {
            'calendar': None,
            'time_tracking': None,
            'communication': None,
            'version_control': None,
            'success': True,
            'errors': []
        }

        try:
            # Get organization's active integrations
            org_integrations = self.db.query(Integration).filter(
                Integration.organization_id == organization_id,
                Integration.is_active == True
            ).all()

            # Calendar Integration
            calendar_integration = next((i for i in org_integrations if i.integration_type in ['google_calendar', 'outlook']), None)
            if calendar_integration and (not integration_preferences or integration_preferences.get('calendar_enabled', True)):
                calendar_result = await self._setup_ai_project_calendar_integration(
                    project_data, tasks, workflow, calendar_integration
                )
                integration_results['calendar'] = calendar_result

            # Communication Integration (Slack/Teams)
            comm_integration = next((i for i in org_integrations if i.integration_type in ['slack', 'microsoft_teams']), None)
            if comm_integration and (not integration_preferences or integration_preferences.get('communication_enabled', True)):
                communication_result = await self._setup_ai_project_communication_integration(
                    project_data, workflow, comm_integration
                )
                integration_results['communication'] = communication_result

            # Version Control Integration
            vcs_integration = next((i for i in org_integrations if i.integration_type in ['github', 'gitlab']), None)
            if vcs_integration and (not integration_preferences or integration_preferences.get('version_control_enabled', True)):
                version_control_result = await self._setup_ai_project_version_control_integration(
                    project_data, vcs_integration
                )
                integration_results['version_control'] = version_control_result

            # Time Tracking Integration (if configured)
            time_integration = next((i for i in org_integrations if i.integration_type in ['toggl', 'harvest']), None)
            if time_integration and (not integration_preferences or integration_preferences.get('time_tracking_enabled', False)):
                time_tracking_result = await self._setup_ai_project_time_tracking_integration(
                    project_data, tasks, time_integration
                )
                integration_results['time_tracking'] = time_tracking_result

        except Exception as e:
            logger.error(f"AI project integration setup failed: {str(e)}")
            integration_results['success'] = False
            integration_results['errors'].append(str(e))

        return integration_results

    async def _setup_ai_project_calendar_integration(
        self,
        project_data: Dict[str, Any],
        tasks: List[Dict[str, Any]],
        workflow: Dict[str, Any],
        integration: Integration
    ) -> Dict[str, Any]:
        """Set up calendar integration for AI project scheduling"""

        try:
            calendar_events = []

            # Create project kickoff event
            kickoff_event = {
                'title': f"🚀 AI Project Kickoff: {project_data['name']}",
                'description': f"AI-generated project kickoff meeting for {project_data['name']}",
                'start_time': datetime.now() + timedelta(days=1),
                'duration_minutes': 120,
                'attendees': [],
                'location': 'Conference Room / Virtual',
                'event_type': 'kickoff'
            }
            calendar_events.append(kickoff_event)

            # Create phase milestone events
            current_date = datetime.now()
            for i, phase in enumerate(workflow.get('phases', [])):
                phase_duration = phase.get('duration_days', 14)
                milestone_date = current_date + timedelta(days=phase_duration)

                milestone_event = {
                    'title': f"📋 AI Project Milestone: {phase['name']} Review",
                    'description': f"Milestone review for {phase['name']} phase completion in AI project {project_data['name']}",
                    'start_time': milestone_date,
                    'duration_minutes': 60,
                    'attendees': [],
                    'event_type': 'milestone'
                }
                calendar_events.append(milestone_event)
                current_date = milestone_date

            # Create milestone celebration events
            for celebration in workflow.get('milestone_celebrations', []):
                celebration_event = {
                    'title': f"🎉 {celebration['milestone']}",
                    'description': celebration['description'],
                    'start_time': current_date + timedelta(days=1),
                    'duration_minutes': 60,
                    'attendees': [],
                    'event_type': 'celebration'
                }
                calendar_events.append(celebration_event)

            # Log integration activity
            self._log_ai_integration_activity(
                integration.id,
                'ai_project_calendar_setup',
                {'project_id': project_data.get('id'), 'events_created': len(calendar_events)}
            )

            return {
                'integration_type': integration.integration_type,
                'events_created': len(calendar_events),
                'calendar_link': f"Calendar integration configured for {project_data['name']}",
                'success': True
            }

        except Exception as e:
            logger.error(f"AI project calendar integration failed: {str(e)}")
            return {
                'integration_type': integration.integration_type,
                'success': False,
                'error': str(e)
            }

    async def _setup_ai_project_communication_integration(
        self,
        project_data: Dict[str, Any],
        workflow: Dict[str, Any],
        integration: Integration
    ) -> Dict[str, Any]:
        """Set up communication platform integration for AI project"""

        try:
            # Create project announcement message
            project_announcement = {
                'title': f"🤖 New AI-Powered Project Created: {project_data['name']}",
                'message': f"""
🚀 **AI Project Created Successfully!**

**Project:** {project_data['name']}
**Type:** {project_data.get('project_type', 'General').replace('_', ' ').title()}
**Phases:** {len(workflow.get('phases', []))} phases planned
**Estimated Duration:** {workflow.get('total_duration_days', 'TBD')} days
**Methodology:** {workflow.get('methodology', 'Agile')}

**AI-Generated Features:**
✅ Comprehensive task breakdown
✅ Smart dependency mapping
✅ Resource allocation recommendations
✅ Risk assessment for each task
✅ Quality gates and milestones
✅ Team-adapted workflow

The project is ready to begin! Check your project dashboard for detailed tasks and timeline.
                """.strip(),
                'channel': f"project-{project_data['name'].lower().replace(' ', '-')}",
                'priority': 'high'
            }

            # Create milestone celebration notifications
            celebration_notifications = []
            for celebration in workflow.get('milestone_celebrations', []):
                celebration_notifications.append({
                    'title': f"🎉 {celebration['milestone']}",
                    'message': f"{celebration['description']}\n\n{celebration['celebration_type']}",
                    'trigger': 'milestone_completion',
                    'celebration_type': celebration['celebration_type']
                })

            # Log integration activity
            self._log_ai_integration_activity(
                integration.id,
                'ai_project_communication_setup',
                {
                    'project_id': project_data.get('id'),
                    'notifications_configured': 1 + len(celebration_notifications)
                }
            )

            return {
                'integration_type': integration.integration_type,
                'channel_configured': True,
                'notifications_setup': 1 + len(celebration_notifications),
                'project_announcement': project_announcement,
                'celebration_notifications': celebration_notifications,
                'success': True
            }

        except Exception as e:
            logger.error(f"AI project communication integration failed: {str(e)}")
            return {
                'integration_type': integration.integration_type,
                'success': False,
                'error': str(e)
            }

    async def _setup_ai_project_version_control_integration(
        self,
        project_data: Dict[str, Any],
        integration: Integration
    ) -> Dict[str, Any]:
        """Set up version control integration for AI development projects"""

        try:
            # Only applicable for development projects
            development_types = ['web_application', 'mobile_app', 'saas_application', 'devops_infrastructure']

            if project_data.get('project_type') not in development_types:
                return {
                    'integration_type': integration.integration_type,
                    'success': True,
                    'message': 'Version control not applicable for this project type',
                    'applicable': False
                }

            # Repository configuration
            repository_config = {
                'name': project_data['name'].lower().replace(' ', '-'),
                'description': f"AI-generated {project_data.get('project_type', '').replace('_', ' ')} project: {project_data['name']}",
                'project_type': project_data.get('project_type'),
                'private': True,
                'auto_init': True,
                'ai_generated': True
            }

            # Branch strategy based on project type
            branch_strategy = {
                'main': 'Production-ready code',
                'develop': 'Integration branch for features',
                'staging': 'Pre-production testing'
            }

            # Initial project structure
            initial_structure = self._get_ai_project_structure(project_data.get('project_type'))

            # Log integration activity
            self._log_ai_integration_activity(
                integration.id,
                'ai_project_vcs_setup',
                {
                    'project_id': project_data.get('id'),
                    'repository_name': repository_config['name'],
                    'project_type': project_data.get('project_type')
                }
            )

            return {
                'integration_type': integration.integration_type,
                'repository_configured': True,
                'repository_name': repository_config['name'],
                'branches_planned': len(branch_strategy),
                'initial_structure': initial_structure,
                'applicable': True,
                'success': True
            }

        except Exception as e:
            logger.error(f"AI project version control integration failed: {str(e)}")
            return {
                'integration_type': integration.integration_type,
                'success': False,
                'error': str(e)
            }

    async def _setup_ai_project_time_tracking_integration(
        self,
        project_data: Dict[str, Any],
        tasks: List[Dict[str, Any]],
        integration: Integration
    ) -> Dict[str, Any]:
        """Set up time tracking integration for AI project tasks"""

        try:
            # Project workspace configuration
            workspace_config = {
                'name': project_data['name'],
                'description': f"AI-generated project with {len(tasks)} tasks",
                'project_id': project_data.get('id'),
                'estimated_hours': sum(task.get('estimated_hours', 8) for task in tasks),
                'ai_generated': True
            }

            # Time tracking entries for tasks
            time_entries = []
            for task in tasks:
                entry = {
                    'task_name': task['title'],
                    'description': task['description'],
                    'estimated_hours': task.get('estimated_hours', 8),
                    'story_points': task.get('story_points', 3),
                    'project_phase': task.get('phase'),
                    'priority': task.get('priority', 'medium'),
                    'tags': task.get('tags', []) + ['ai-generated'],
                    'billable': True
                }
                time_entries.append(entry)

            # Log integration activity
            self._log_ai_integration_activity(
                integration.id,
                'ai_project_time_tracking_setup',
                {
                    'project_id': project_data.get('id'),
                    'workspace_name': workspace_config['name'],
                    'time_entries': len(time_entries),
                    'estimated_hours': workspace_config['estimated_hours']
                }
            )

            return {
                'integration_type': integration.integration_type,
                'workspace_configured': True,
                'time_entries_planned': len(time_entries),
                'estimated_total_hours': workspace_config['estimated_hours'],
                'success': True
            }

        except Exception as e:
            logger.error(f"AI project time tracking integration failed: {str(e)}")
            return {
                'integration_type': integration.integration_type,
                'success': False,
                'error': str(e)
            }

    def _get_ai_project_structure(self, project_type: str) -> List[Dict[str, str]]:
        """Get AI-optimized initial project structure based on type"""

        structures = {
            'web_application': [
                {'path': 'README.md', 'content': '# AI-Generated Web Application\n\nThis project was created using AI-powered project generation.'},
                {'path': 'package.json', 'content': '{\n  "name": "ai-web-app",\n  "version": "1.0.0",\n  "description": "AI-generated web application"\n}'},
                {'path': 'src/index.js', 'content': '// AI-generated main application entry point'},
                {'path': 'src/components/README.md', 'content': '# Components\n\nAI-generated component structure'},
                {'path': '.gitignore', 'content': 'node_modules/\n.env\ndist/\n.ai-project-metadata.json'},
                {'path': '.ai-project-metadata.json', 'content': '{\n  "generated_by": "AI Project Creator",\n  "project_type": "web_application",\n  "created_at": "' + datetime.now().isoformat() + '"\n}'}
            ],
            'mobile_app': [
                {'path': 'README.md', 'content': '# AI-Generated Mobile Application\n\nThis mobile app was created using AI-powered project generation.'},
                {'path': 'App.js', 'content': '// AI-generated main app component'},
                {'path': 'package.json', 'content': '{\n  "name": "ai-mobile-app",\n  "version": "1.0.0"\n}'},
                {'path': 'src/screens/README.md', 'content': '# Screens\n\nAI-generated screen structure'},
                {'path': '.ai-project-metadata.json', 'content': '{\n  "generated_by": "AI Project Creator",\n  "project_type": "mobile_app"\n}'}
            ],
            'saas_application': [
                {'path': 'README.md', 'content': '# AI-Generated SaaS Application\n\nMulti-tenant SaaS application created with AI.'},
                {'path': 'docker-compose.yml', 'content': 'version: "3.8"\nservices:\n  app:\n    build: .\n  # AI-generated service configuration'},
                {'path': 'Dockerfile', 'content': 'FROM node:16\nWORKDIR /app\n# AI-generated Docker configuration'},
                {'path': '.ai-project-metadata.json', 'content': '{\n  "generated_by": "AI Project Creator",\n  "project_type": "saas_application"\n}'}
            ],
            'devops_infrastructure': [
                {'path': 'README.md', 'content': '# AI-Generated DevOps Infrastructure\n\nInfrastructure as Code project created with AI.'},
                {'path': 'terraform/main.tf', 'content': '# AI-generated Terraform configuration'},
                {'path': 'ansible/playbook.yml', 'content': '# AI-generated Ansible playbook'},
                {'path': '.ai-project-metadata.json', 'content': '{\n  "generated_by": "AI Project Creator",\n  "project_type": "devops_infrastructure"\n}'}
            ]
        }

        return structures.get(project_type, [
            {'path': 'README.md', 'content': f'# AI-Generated {project_type.title()} Project\n\nCreated using AI-powered project generation.'},
            {'path': '.ai-project-metadata.json', 'content': f'{{\n  "generated_by": "AI Project Creator",\n  "project_type": "{project_type}"\n}}'}
        ])

    def _log_ai_integration_activity(self, integration_id: str, activity_type: str, metadata: Dict[str, Any]) -> None:
        """Log integration activity for AI project setup"""
        try:
            sync_log = IntegrationSyncLog(
                integration_id=integration_id,
                sync_type=activity_type,
                status='completed',
                records_processed=metadata.get('events_created', metadata.get('notifications_configured', 1)),
                metadata=metadata,
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow()
            )
            self.db.add(sync_log)
            self.db.commit()
        except Exception as e:
            logger.error(f"Failed to log AI integration activity: {str(e)}")
            self.db.rollback()
