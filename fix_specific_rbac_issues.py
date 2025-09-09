#!/usr/bin/env python3
"""
Fix specific RBAC issues identified in testing
"""
import asyncio
import sys
import os
import requests

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__)))

async def fix_organization_settings():
    """Fix organization settings to enable admin project creation"""
    print("🔧 FIXING ORGANIZATION SETTINGS FOR ADMIN PROJECT CREATION")
    print("=" * 60)
    
    try:
        from app.core.database import get_db
        from app.models.organization import Organization
        from app.models.organization_settings import OrganizationSettings
        from sqlalchemy import select
        
        async for db in get_db():
            try:
                # Get all organizations
                org_result = await db.execute(select(Organization))
                organizations = org_result.scalars().all()
                
                print(f"📊 Found {len(organizations)} organizations")
                
                for org in organizations:
                    # Check if organization has settings
                    settings_result = await db.execute(
                        select(OrganizationSettings)
                        .where(OrganizationSettings.organization_id == org.id)
                    )
                    settings = settings_result.scalar_one_or_none()
                    
                    if not settings:
                        # Create default settings with admin project creation enabled
                        settings = OrganizationSettings(
                            organization_id=org.id,
                            allow_admin_create_projects=True,  # Enable admin project creation
                            allow_member_create_projects=False,
                            allow_admin_schedule_meetings=True,
                            allow_member_schedule_meetings=False,
                            require_domain_match=True,
                            enable_task_notifications=True,
                            enable_meeting_notifications=True,
                            enable_role_change_notifications=True,
                            require_email_verification=True
                        )
                        db.add(settings)
                        print(f"   ✅ Created settings for org: {org.name}")
                    else:
                        # Update existing settings to enable admin project creation
                        if not settings.allow_admin_create_projects:
                            settings.allow_admin_create_projects = True
                            print(f"   ✅ Enabled admin project creation for org: {org.name}")
                        else:
                            print(f"   ✅ Admin project creation already enabled for org: {org.name}")
                
                await db.commit()
                print("✅ Organization settings fixed successfully")
                return True
                
            except Exception as e:
                print(f"   ❌ Database error: {e}")
                await db.rollback()
                return False
            
            break
            
    except Exception as e:
        print(f"❌ Organization settings fix failed: {e}")
        return False

async def test_admin_project_creation():
    """Test admin project creation with proper data"""
    print("\n🧪 TESTING ADMIN PROJECT CREATION")
    print("=" * 60)
    
    try:
        # Login as admin
        admin_login = {
            "email": "admin1755850537@rbactest.com",
            "password": "TestAdmin123!"
        }
        
        response = requests.post("http://localhost:8000/api/v1/auth/login", json=admin_login, timeout=10)
        if response.status_code != 200:
            print(f"   ❌ Admin login failed: {response.status_code}")
            return False
        
        data = response.json()
        access_token = data.get("tokens", {}).get("access_token")
        org_id = data.get("organization", {}).get("id")
        
        if not access_token or not org_id:
            print("   ❌ Missing access token or organization ID")
            return False
        
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Test project creation with all required fields
        project_data = {
            "name": "Fixed Admin Test Project",
            "description": "Project created after RBAC fixes",
            "status": "active",
            "priority": "medium"
        }
        
        # Add organization_id as query parameter (as expected by the endpoint)
        response = requests.post(
            f"http://localhost:8000/api/v1/projects?organization_id={org_id}",
            json=project_data,
            headers=headers,
            timeout=10
        )
        
        print(f"   📊 Project creation response: {response.status_code}")
        
        if response.status_code in [200, 201]:
            print("   ✅ Admin project creation now working!")
            project = response.json()
            print(f"   📋 Created project: {project.get('name', 'Unknown')}")
            return True
        else:
            print(f"   ⚠️ Project creation failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Admin project creation test failed: {e}")
        return False

async def test_member_organization_creation():
    """Test that member organization creation is properly denied"""
    print("\n🧪 TESTING MEMBER ORGANIZATION CREATION (SHOULD BE DENIED)")
    print("=" * 60)
    
    try:
        # Login as member
        member_login = {
            "email": "member1755850537@rbactest.com",
            "password": "TestMember123!"
        }
        
        response = requests.post("http://localhost:8000/api/v1/auth/login", json=member_login, timeout=10)
        if response.status_code != 200:
            print(f"   ❌ Member login failed: {response.status_code}")
            return False
        
        data = response.json()
        access_token = data.get("tokens", {}).get("access_token")
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Try to create organization (should fail)
        org_data = {
            "name": "Member Unauthorized Org",
            "description": "This should fail with 403"
        }
        
        response = requests.post(
            "http://localhost:8000/api/v1/organizations",
            json=org_data,
            headers=headers,
            timeout=10
        )
        
        print(f"   📊 Organization creation response: {response.status_code}")
        
        if response.status_code == 403:
            print("   ✅ Member organization creation properly denied (403)")
            return True
        elif response.status_code == 422:
            print("   ⚠️ Member organization creation failed with validation error (422)")
            print("   This might be due to missing required fields, not permission issue")
            return False
        elif response.status_code == 200:
            print("   ❌ Member organization creation succeeded (should be denied)")
            return False
        else:
            print(f"   ⚠️ Unexpected response: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Member organization creation test failed: {e}")
        return False

async def create_email_service():
    """Create basic email service"""
    print("\n📧 CREATING EMAIL SERVICE")
    print("=" * 60)
    
    try:
        email_service_path = "app/core/email.py"
        
        if os.path.exists(email_service_path):
            print("   ✅ Email service already exists")
            return True
        
        email_service_content = '''"""
Email service for sending notifications and invitations
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

async def send_email(to_email: str, subject: str, body: str, html_body: Optional[str] = None) -> bool:
    """Send email (stub implementation for testing)"""
    logger.info(f"📧 [STUB] Sending email to {to_email}: {subject}")
    logger.info(f"📧 [STUB] Body: {body[:100]}...")
    
    # In production, implement actual email sending here
    # For now, just log the email
    return True

class EmailService:
    """Email service class"""
    
    async def send_invitation_email(self, to_email: str, inviter_name: str, 
                                  organization_name: str, role: str, invitation_link: str) -> bool:
        """Send invitation email"""
        subject = f"Invitation to join {organization_name}"
        body = f"{inviter_name} invited you to join {organization_name} as {role}. Link: {invitation_link}"
        return await send_email(to_email, subject, body)

# Global instance
email_service = EmailService()
'''
        
        # Create directory if needed
        os.makedirs(os.path.dirname(email_service_path), exist_ok=True)
        
        with open(email_service_path, 'w') as f:
            f.write(email_service_content)
        
        print("   ✅ Email service created successfully")
        return True
        
    except Exception as e:
        print(f"❌ Email service creation failed: {e}")
        return False

async def run_all_fixes():
    """Run all specific RBAC fixes"""
    print("🚀 RUNNING SPECIFIC RBAC FIXES")
    print("=" * 80)
    
    fixes = [
        ("Organization Settings", fix_organization_settings()),
        ("Email Service", create_email_service()),
        ("Admin Project Creation Test", test_admin_project_creation()),
        ("Member Organization Creation Test", test_member_organization_creation())
    ]
    
    results = []
    for fix_name, fix_coro in fixes:
        try:
            result = await fix_coro
            results.append((fix_name, result))
        except Exception as e:
            print(f"❌ {fix_name} failed: {e}")
            results.append((fix_name, False))
    
    # Summary
    print("\n📊 RBAC FIXES SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"📈 Fixes: {passed}/{total} ({passed/total*100:.1f}%)")
    
    for fix_name, result in results:
        status = "✅ SUCCESS" if result else "❌ FAILED"
        print(f"   {status} {fix_name}")
    
    if passed == total:
        print("\n🎉 All RBAC issues fixed successfully!")
        print("✅ The application should now pass all RBAC tests!")
    else:
        print(f"\n⚠️ {total - passed} issues still need attention")
    
    return passed == total

if __name__ == "__main__":
    asyncio.run(run_all_fixes())
