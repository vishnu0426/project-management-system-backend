#!/usr/bin/env python3
"""
Debug Billing Access Issues
"""
import asyncio
import sys
import os
import requests

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__)))

async def debug_billing_access():
    """Debug billing access issues"""
    print("🔍 DEBUGGING BILLING ACCESS ISSUES")
    print("=" * 60)
    
    base_url = "http://localhost:8000"
    
    # Test admin billing access
    admin_login = {
        "email": "admin1755850537@rbactest.com",
        "password": "TestAdmin123!"
    }
    
    response = requests.post(f"{base_url}/api/v1/auth/login", json=admin_login, timeout=10)
    if response.status_code == 200:
        admin_data = response.json()
        admin_token = admin_data.get("tokens", {}).get("access_token")
        admin_org_id = admin_data.get("organization", {}).get("id")
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        print(f"🔧 Admin authenticated: {admin_data.get('user', {}).get('email')}")
        print(f"🏢 Admin org ID: {admin_org_id}")
        
        # Test billing endpoint
        print(f"\n📋 Testing billing endpoint: GET /api/v1/organizations/{admin_org_id}/billing")
        response = requests.get(f"{base_url}/api/v1/organizations/{admin_org_id}/billing", headers=admin_headers, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        # Check admin role in database
        try:
            from app.core.database import get_db
            from app.services.enhanced_role_permissions import EnhancedRolePermissions
            
            async for db in get_db():
                permissions = EnhancedRolePermissions(db)
                user_role = await permissions.get_user_role(str(admin_data.get('user', {}).get('id')), admin_org_id)
                print(f"🔍 Admin role in database: {user_role}")
                break
                
        except Exception as e:
            print(f"❌ Database check failed: {e}")
    
    # Test member organization creation
    print(f"\n🏢 TESTING MEMBER ORGANIZATION CREATION")
    print("=" * 60)
    
    member_login = {
        "email": "member1755850537@rbactest.com",
        "password": "TestMember123!"
    }
    
    response = requests.post(f"{base_url}/api/v1/auth/login", json=member_login, timeout=10)
    if response.status_code == 200:
        member_data = response.json()
        member_token = member_data.get("tokens", {}).get("access_token")
        member_headers = {"Authorization": f"Bearer {member_token}"}
        
        print(f"👤 Member authenticated: {member_data.get('user', {}).get('email')}")
        
        # Check member's existing memberships
        try:
            from app.core.database import get_db
            from app.models.organization import OrganizationMember
            from sqlalchemy import select
            
            async for db in get_db():
                result = await db.execute(
                    select(OrganizationMember).where(
                        OrganizationMember.user_id == member_data.get('user', {}).get('id')
                    )
                )
                memberships = result.scalars().all()
                
                print(f"🔍 Member's existing memberships:")
                for membership in memberships:
                    print(f"   🏢 Org: {membership.organization_id}, Role: {membership.role}")
                
                break
                
        except Exception as e:
            print(f"❌ Database check failed: {e}")
        
        # Test organization creation
        org_data = {
            "name": "Debug Test Org",
            "description": "Should be denied"
        }
        
        print(f"\n📋 Testing org creation: POST /api/v1/organizations")
        response = requests.post(f"{base_url}/api/v1/organizations", json=org_data, headers=member_headers, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")

async def main():
    """Main debug execution"""
    try:
        await debug_billing_access()
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
