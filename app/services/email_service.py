"""
Email service for sending notifications
"""
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List
import logging

from app.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Email service for sending notifications"""
    
    def __init__(self):
        self.smtp_host = settings.smtp_host
        self.smtp_port = settings.smtp_port
        self.smtp_user = settings.smtp_user
        self.smtp_pass = settings.smtp_pass
        self.from_email = settings.from_email
        self.from_name = getattr(settings, 'from_name', 'Agno WorkSphere')
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """Send an email"""
        try:
            # Check if SMTP credentials are available
            if not self.smtp_user or not self.smtp_pass:
                logger.info(f"📧 EMAIL (No SMTP Config - Logging Only)")
                logger.info(f"To: {to_email}")
                logger.info(f"Subject: {subject}")
                logger.info(f"Content: {text_content or html_content[:200]}...")
                print(f"\n📧 EMAIL NOT SENT (No SMTP Configuration)")
                print(f"To: {to_email}")
                print(f"Subject: {subject}")
                print(f"Content: {text_content or html_content[:200]}...")
                print("-" * 50)
                return False  # Return False to indicate email wasn't actually sent

            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"{self.from_name} <{self.from_email}>"
            message["To"] = to_email

            # Add text content
            if text_content:
                text_part = MIMEText(text_content, "plain")
                message.attach(text_part)

            # Add HTML content
            html_part = MIMEText(html_content, "html")
            message.attach(html_part)
            
            # Send email
            if self.smtp_user and self.smtp_pass:
                context = ssl.create_default_context()
                with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                    server.starttls(context=context)
                    server.login(self.smtp_user, self.smtp_pass)
                    server.sendmail(self.from_email, to_email, message.as_string())
                
                logger.info(f"Email sent successfully to {to_email}")
                print(f"\n✅ EMAIL SENT SUCCESSFULLY")
                print(f"To: {to_email}")
                print(f"Subject: {subject}")
                print("-" * 50)
                return True
            else:
                logger.warning("SMTP credentials not configured, email not sent")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False
    
    async def send_welcome_email(
        self,
        user_email: str,
        user_name: str,
        organization_name: str,
        login_url: str = "http://localhost:3000/login"
    ) -> bool:
        """Send welcome email to new user"""
        subject = f"Welcome to {organization_name} - Your Agno WorkSphere Account is Ready!"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Welcome to Agno WorkSphere</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .button {{ display: inline-block; background: #667eea; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .features {{ background: white; padding: 20px; border-radius: 5px; margin: 20px 0; }}
                .feature {{ margin: 10px 0; padding: 10px; border-left: 4px solid #667eea; }}
                .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 30px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎉 Welcome to Agno WorkSphere!</h1>
                    <p>Your project management journey starts here</p>
                </div>
                
                <div class="content">
                    <h2>Hello {user_name}!</h2>
                    
                    <p>Congratulations! You've successfully created your Agno WorkSphere account and you're now the <strong>Owner</strong> of <strong>{organization_name}</strong>.</p>
                    
                    <p>As an organization owner, you have full control over your workspace and can:</p>
                    
                    <div class="features">
                        <div class="feature">
                            <strong>👥 Manage Team Members</strong><br>
                            Invite team members and assign roles (Admin, Member, Viewer)
                        </div>
                        <div class="feature">
                            <strong>📊 Create Projects</strong><br>
                            Set up projects and organize work with Kanban boards
                        </div>
                        <div class="feature">
                            <strong>🔒 Control Access</strong><br>
                            Manage permissions and organization settings
                        </div>
                        <div class="feature">
                            <strong>📈 Track Progress</strong><br>
                            Monitor team activity and project progress
                        </div>
                    </div>
                    
                    <p>Ready to get started? Click the button below to access your dashboard:</p>
                    
                    <div style="text-align: center;">
                        <a href="{login_url}" class="button">Access Your Dashboard</a>
                    </div>
                    
                    <h3>🚀 Next Steps:</h3>
                    <ol>
                        <li><strong>Complete your profile</strong> - Add your avatar and personal information</li>
                        <li><strong>Invite your team</strong> - Add team members to your organization</li>
                        <li><strong>Create your first project</strong> - Start organizing your work</li>
                        <li><strong>Set up Kanban boards</strong> - Visualize your workflow</li>
                    </ol>
                    
                    <p>If you have any questions or need help getting started, don't hesitate to reach out to our support team.</p>
                    
                    <p>Welcome aboard!</p>
                    <p><strong>The Agno WorkSphere Team</strong></p>
                </div>
                
                <div class="footer">
                    <p>This email was sent to {user_email}</p>
                    <p>© 2024 Agno WorkSphere. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Welcome to Agno WorkSphere!
        
        Hello {user_name}!
        
        Congratulations! You've successfully created your Agno WorkSphere account and you're now the Owner of {organization_name}.
        
        As an organization owner, you have full control over your workspace and can:
        - Manage team members and assign roles
        - Create projects and organize work with Kanban boards
        - Control access and organization settings
        - Track progress and monitor team activity
        
        Ready to get started? Visit: {login_url}
        
        Next Steps:
        1. Complete your profile
        2. Invite your team
        3. Create your first project
        4. Set up Kanban boards
        
        Welcome aboard!
        The Agno WorkSphere Team
        """
        
        return await self.send_email(user_email, subject, html_content, text_content)
    
    async def send_invitation_email(
        self,
        to_email: str,
        inviter_name: str,
        organization_name: str,
        role: str,
        invitation_url: str
    ) -> bool:
        """Send invitation email to new team member"""
        subject = f"You're invited to join {organization_name} on Agno WorkSphere"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Team Invitation</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .button {{ display: inline-block; background: #667eea; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .role-badge {{ background: #e3f2fd; color: #1976d2; padding: 5px 15px; border-radius: 20px; font-weight: bold; }}
                .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 30px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎉 You're Invited!</h1>
                    <p>Join {organization_name} on Agno WorkSphere</p>
                </div>
                
                <div class="content">
                    <p>Hello!</p>
                    
                    <p><strong>{inviter_name}</strong> has invited you to join <strong>{organization_name}</strong> on Agno WorkSphere as a <span class="role-badge">{role.title()}</span>.</p>
                    
                    <p>Agno WorkSphere is a powerful project management platform that helps teams collaborate effectively and get things done.</p>
                    
                    <div style="text-align: center;">
                        <a href="{invitation_url}" class="button">Accept Invitation</a>
                    </div>
                    
                    <p>If you don't have an account yet, you'll be able to create one when you click the invitation link.</p>
                    
                    <p>Looking forward to having you on the team!</p>
                </div>
                
                <div class="footer">
                    <p>This invitation was sent to {to_email}</p>
                    <p>© 2024 Agno WorkSphere. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return await self.send_email(to_email, subject, html_content)

    async def send_project_creation_confirmation(
        self,
        owner_email: str,
        owner_name: str,
        project_data: dict,
        organization_name: str
    ) -> bool:
        """Send project creation confirmation email to owner"""
        subject = f"🎉 AI Project '{project_data.get('name', 'Untitled')}' Created Successfully!"

        # Extract project details
        project_name = project_data.get('name', 'Untitled Project')
        project_description = project_data.get('description', 'No description provided')
        team_size = project_data.get('teamSize', 'Not specified')
        industry = project_data.get('industry', 'Not specified')
        tasks_created = len(project_data.get('tasks', []))
        estimated_duration = project_data.get('estimatedDuration', 'Not specified')
        tech_stack = project_data.get('techStack', {})
        workflow_phases = project_data.get('workflow', {}).get('phases', [])

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Project Created Successfully</title>
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 0; background-color: #f8fafc; }}
                .container {{ max-width: 600px; margin: 0 auto; background-color: white; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 40px 30px; text-align: center; }}
                .header h1 {{ margin: 0; font-size: 28px; font-weight: 600; }}
                .header p {{ margin: 10px 0 0 0; opacity: 0.9; font-size: 16px; }}
                .content {{ padding: 40px 30px; }}
                .project-card {{ background: #f8fafc; border-radius: 12px; padding: 24px; margin: 20px 0; border-left: 4px solid #667eea; }}
                .project-title {{ font-size: 20px; font-weight: 600; color: #1a202c; margin: 0 0 8px 0; }}
                .project-description {{ color: #4a5568; margin: 0 0 16px 0; line-height: 1.6; }}
                .detail-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin: 20px 0; }}
                .detail-item {{ background: white; padding: 16px; border-radius: 8px; border: 1px solid #e2e8f0; }}
                .detail-label {{ font-size: 12px; font-weight: 600; color: #718096; text-transform: uppercase; margin-bottom: 4px; }}
                .detail-value {{ font-size: 14px; color: #2d3748; font-weight: 500; }}
                .tasks-section {{ background: #edf2f7; border-radius: 8px; padding: 20px; margin: 20px 0; }}
                .tasks-count {{ font-size: 24px; font-weight: 700; color: #667eea; }}
                .workflow-phases {{ margin: 20px 0; }}
                .phase {{ background: white; padding: 12px 16px; margin: 8px 0; border-radius: 6px; border-left: 3px solid #48bb78; }}
                .tech-stack {{ display: flex; flex-wrap: wrap; gap: 8px; margin: 12px 0; }}
                .tech-item {{ background: #667eea; color: white; padding: 4px 12px; border-radius: 16px; font-size: 12px; }}
                .cta-button {{ display: inline-block; background: #667eea; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: 600; margin: 20px 0; }}
                .footer {{ background: #f7fafc; padding: 30px; text-align: center; color: #718096; font-size: 14px; }}
                @media (max-width: 600px) {{ .detail-grid {{ grid-template-columns: 1fr; }} }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎉 Project Created Successfully!</h1>
                    <p>Your AI-powered project is ready to go</p>
                </div>

                <div class="content">
                    <p>Hello <strong>{owner_name}</strong>,</p>

                    <p>Great news! Your AI-powered project has been successfully created in <strong>{organization_name}</strong>. Our AI has generated a comprehensive project structure tailored to your needs.</p>

                    <div class="project-card">
                        <h2 class="project-title">{project_name}</h2>
                        <p class="project-description">{project_description}</p>

                        <div class="detail-grid">
                            <div class="detail-item">
                                <div class="detail-label">Industry</div>
                                <div class="detail-value">{industry}</div>
                            </div>
                            <div class="detail-item">
                                <div class="detail-label">Team Size</div>
                                <div class="detail-value">{team_size}</div>
                            </div>
                            <div class="detail-item">
                                <div class="detail-label">Estimated Duration</div>
                                <div class="detail-value">{estimated_duration}</div>
                            </div>
                            <div class="detail-item">
                                <div class="detail-label">Tasks Generated</div>
                                <div class="detail-value">{tasks_created} tasks</div>
                            </div>
                        </div>
                    </div>

                    <div class="tasks-section">
                        <h3>📋 AI-Generated Project Structure</h3>
                        <div class="tasks-count">{tasks_created}</div>
                        <p>comprehensive tasks have been automatically generated and organized for your project.</p>
                    </div>

                    {f'''
                    <div class="workflow-phases">
                        <h3>🔄 Project Workflow Phases</h3>
                        {''.join([f'<div class="phase">📌 {phase}</div>' for phase in workflow_phases[:5]])}
                    </div>
                    ''' if workflow_phases else ''}

                    {f'''
                    <div>
                        <h3>🛠️ Recommended Technology Stack</h3>
                        <div class="tech-stack">
                            {''.join([f'<span class="tech-item">{tech}</span>' for tech in list(tech_stack.get('frontend', [])) + list(tech_stack.get('backend', [])) + list(tech_stack.get('database', []))][:8])}
                        </div>
                    </div>
                    ''' if tech_stack else ''}

                    <a href="http://localhost:3000/projects" class="cta-button">View Your Project →</a>

                    <h3>🚀 What's Next?</h3>
                    <ul>
                        <li><strong>Review the generated tasks</strong> - Fine-tune the AI-generated task breakdown</li>
                        <li><strong>Assign team members</strong> - Distribute tasks among your team</li>
                        <li><strong>Set up your Kanban board</strong> - Visualize your project workflow</li>
                        <li><strong>Start tracking progress</strong> - Monitor your project's advancement</li>
                    </ul>

                    <p>Our AI has done the heavy lifting of project planning for you. Now you can focus on what matters most - executing your vision!</p>

                    <p>If you have any questions or need assistance, our support team is here to help.</p>

                    <p>Happy project managing!</p>
                    <p><strong>The Agno WorkSphere Team</strong></p>
                </div>

                <div class="footer">
                    <p>This email was sent to {owner_email}</p>
                    <p>© 2024 Agno WorkSphere. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_content = f"""
        Project Created Successfully!

        Hello {owner_name}!

        Great news! Your AI-powered project "{project_name}" has been successfully created in {organization_name}.

        Project Details:
        - Name: {project_name}
        - Description: {project_description}
        - Industry: {industry}
        - Team Size: {team_size}
        - Estimated Duration: {estimated_duration}
        - Tasks Generated: {tasks_created} tasks

        What's Next?
        1. Review the generated tasks
        2. Assign team members
        3. Set up your Kanban board
        4. Start tracking progress

        View your project: http://localhost:3000/projects

        Happy project managing!
        The Agno WorkSphere Team
        """

        return await self.send_email(owner_email, subject, html_content, text_content)

    async def send_enhanced_invitation_email(
        self,
        to_email: str,
        inviter_name: str,
        organization_name: str,
        role: str,
        invitation_url: str,
        temp_password: str,
        project_name: Optional[str] = None,
        custom_message: Optional[str] = None
    ) -> bool:
        """Send enhanced invitation email with temporary password"""
        subject = f"🎉 You're invited to join {organization_name} on Agno WorkSphere"

        # Role badge styling
        role_colors = {
            'owner': '#ff6b6b',
            'admin': '#4ecdc4',
            'member': '#45b7d1'
        }
        role_color = role_colors.get(role.lower(), '#45b7d1')

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Invitation to {organization_name}</title>
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; background-color: #f5f7fa; }}
                .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.1); }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 40px 30px; text-align: center; position: relative; }}
                .header::before {{ content: ''; position: absolute; top: 0; left: 0; right: 0; bottom: 0; background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><defs><pattern id="grain" width="100" height="100" patternUnits="userSpaceOnUse"><circle cx="25" cy="25" r="1" fill="white" opacity="0.1"/><circle cx="75" cy="75" r="1" fill="white" opacity="0.1"/></pattern></defs><rect width="100" height="100" fill="url(%23grain)"/></svg>'); }}
                .header h1 {{ margin: 0; font-size: 28px; font-weight: 700; position: relative; z-index: 1; }}
                .header .subtitle {{ margin: 10px 0 0 0; font-size: 16px; opacity: 0.9; position: relative; z-index: 1; }}
                .content {{ padding: 40px 30px; }}
                .invitation-card {{ background: linear-gradient(135deg, #f8f9ff 0%, #e8f4fd 100%); border-radius: 12px; padding: 30px; margin: 20px 0; border-left: 5px solid {role_color}; }}
                .role-badge {{ display: inline-block; background: {role_color}; color: white; padding: 8px 16px; border-radius: 20px; font-size: 14px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; margin: 10px 0; }}
                .credentials-box {{ background: #f8f9fa; border: 2px dashed #dee2e6; border-radius: 8px; padding: 20px; margin: 20px 0; text-align: center; }}
                .temp-password {{ font-family: 'Courier New', monospace; font-size: 18px; font-weight: bold; color: #e74c3c; background: white; padding: 10px 15px; border-radius: 6px; display: inline-block; margin: 10px 0; border: 2px solid #e74c3c; }}
                .cta-button {{ display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 16px 32px; text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 16px; margin: 20px 0; transition: all 0.3s ease; box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3); }}
                .cta-button:hover {{ transform: translateY(-2px); box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4); }}
                .features {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin: 30px 0; }}
                .feature {{ text-align: center; padding: 20px; background: #f8f9ff; border-radius: 8px; }}
                .feature-icon {{ font-size: 24px; margin-bottom: 10px; }}
                .footer {{ background: #f8f9fa; padding: 30px; text-align: center; color: #6c757d; font-size: 14px; }}
                .security-note {{ background: #fff3cd; border: 1px solid #ffeaa7; border-radius: 6px; padding: 15px; margin: 20px 0; color: #856404; }}
                @media (max-width: 600px) {{
                    .container {{ margin: 10px; }}
                    .header {{ padding: 30px 20px; }}
                    .content {{ padding: 30px 20px; }}
                    .features {{ grid-template-columns: 1fr; }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎉 You're Invited!</h1>
                    <p class="subtitle">Join {organization_name} on Agno WorkSphere</p>
                </div>

                <div class="content">
                    <div class="invitation-card">
                        <p><strong>{inviter_name}</strong> has invited you to join <strong>{organization_name}</strong> as a:</p>
                        <div class="role-badge">{role.title()}</div>
                        {f'<p><strong>Project:</strong> {project_name}</p>' if project_name else ''}
                        {f'<div style="margin: 15px 0; padding: 15px; background: white; border-radius: 6px; font-style: italic;">"{custom_message}"</div>' if custom_message else ''}
                    </div>

                    <div class="credentials-box">
                        <h3>🔐 Your Login Credentials</h3>
                        <p><strong>Email:</strong> {to_email}</p>
                        <p><strong>Temporary Password:</strong></p>
                        <div class="temp-password">{temp_password}</div>
                        <p style="font-size: 12px; color: #6c757d; margin-top: 15px;">
                            ⚠️ Please change this password after your first login for security
                        </p>
                    </div>

                    <div style="text-align: center;">
                        <a href="{invitation_url}" class="cta-button">
                            🚀 Accept Invitation & Get Started
                        </a>
                    </div>

                    <div class="features">
                        <div class="feature">
                            <div class="feature-icon">📊</div>
                            <h4>Project Management</h4>
                            <p>Organize work with Kanban boards</p>
                        </div>
                        <div class="feature">
                            <div class="feature-icon">👥</div>
                            <h4>Team Collaboration</h4>
                            <p>Work together seamlessly</p>
                        </div>
                        <div class="feature">
                            <div class="feature-icon">📈</div>
                            <h4>Progress Tracking</h4>
                            <p>Monitor project progress</p>
                        </div>
                        <div class="feature">
                            <div class="feature-icon">🔔</div>
                            <h4>Smart Notifications</h4>
                            <p>Stay updated on important changes</p>
                        </div>
                    </div>

                    <div class="security-note">
                        <strong>🛡️ Security Note:</strong> This invitation link is valid for 7 days.
                        If you didn't expect this invitation, please ignore this email.
                    </div>

                    <p>Welcome to the team! We're excited to have you aboard.</p>
                    <p><strong>The Agno WorkSphere Team</strong></p>
                </div>

                <div class="footer">
                    <p>This invitation was sent to {to_email}</p>
                    <p>© 2024 Agno WorkSphere. All rights reserved.</p>
                    <p>Need help? Contact our support team</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_content = f"""
        You're invited to join {organization_name}!

        Hello!

        {inviter_name} has invited you to join {organization_name} on Agno WorkSphere as a {role.title()}.
        {f'Project: {project_name}' if project_name else ''}
        {f'Message: "{custom_message}"' if custom_message else ''}

        Your login credentials:
        Email: {to_email}
        Temporary Password: {temp_password}

        Accept your invitation: {invitation_url}

        Please change your password after your first login for security.

        Welcome to the team!
        The Agno WorkSphere Team
        """

        return await self.send_email(to_email, subject, html_content, text_content)


# Global email service instance
email_service = EmailService()


# Convenience functions for backward compatibility
async def send_invitation_email(
    to_email: str,
    inviter_name: str,
    organization_name: str,
    role: str,
    invitation_url: str
) -> bool:
    """Send invitation email to new team member"""
    return await email_service.send_invitation_email(
        to_email, inviter_name, organization_name, role, invitation_url
    )


async def send_welcome_email(
    user_email: str,
    user_name: str,
    organization_name: str,
    login_url: str = "http://localhost:3000/login"
) -> bool:
    """Send welcome email to new user"""
    return await email_service.send_welcome_email(
        user_email, user_name, organization_name, login_url
    )


async def send_project_creation_confirmation(
    owner_email: str,
    owner_name: str,
    project_data: dict,
    organization_name: str
) -> bool:
    """Send project creation confirmation email to owner"""
    return await email_service.send_project_creation_confirmation(
        owner_email, owner_name, project_data, organization_name
    )
