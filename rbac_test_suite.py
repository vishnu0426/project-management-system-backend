#!/usr/bin/env python3
"""
Comprehensive RBAC Test Suite for Agno WorkSphere
Tests role-based access control, user workflows, and organizational features
"""
import asyncio
import sys
import os
import json
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__)))

@dataclass
class TestUser:
    """Test user data structure"""
    email: str
    password: str
    first_name: str
    last_name: str
    role: str
    organization_id: Optional[str] = None
    user_id: Optional[str] = None
    access_token: Optional[str] = None

@dataclass
class TestOrganization:
    """Test organization data structure"""
    name: str
    description: str
    domain: str
    organization_id: Optional[str] = None
    owner_id: Optional[str] = None

@dataclass
class TestResult:
    """Test result data structure"""
    test_name: str
    passed: bool
    details: str
    role: str
    endpoint: str
    expected_status: int
    actual_status: int
    error_message: Optional[str] = None

class RBACTestSuite:
    """Comprehensive RBAC Test Suite"""
    
    def __init__(self):
        self.test_results: List[TestResult] = []
        self.test_users: Dict[str, TestUser] = {}
        self.test_organizations: List[TestOrganization] = []
        self.base_url = "http://localhost:8000"
        
        # Permission Matrix - Expected permissions for each role
        self.permission_matrix = {
            'owner': {
                'can_create_projects': True,
                'can_invite_members': True,
                'can_manage_organization': True,
                'can_schedule_meetings': True,
                'can_view_all_data': True,
                'can_manage_billing': True,
                'can_delete_organization': True,
                'can_assign_admin_role': True,
                'can_view_audit_logs': True,
                'can_export_data': True
            },
            'admin': {
                'can_create_projects': True,
                'can_invite_members': True,
                'can_manage_organization': True,
                'can_schedule_meetings': True,
                'can_view_all_data': True,
                'can_manage_billing': False,
                'can_delete_organization': False,
                'can_assign_admin_role': False,
                'can_view_audit_logs': True,
                'can_export_data': True
            },
            'member': {
                'can_create_projects': False,  # Configurable per org
                'can_invite_members': True,    # Limited to member role
                'can_manage_organization': False,
                'can_schedule_meetings': False, # Configurable per org
                'can_view_all_data': True,
                'can_manage_billing': False,
                'can_delete_organization': False,
                'can_assign_admin_role': False,
                'can_view_audit_logs': False,
                'can_export_data': False
            },
            'viewer': {
                'can_create_projects': False,
                'can_invite_members': False,
                'can_manage_organization': False,
                'can_schedule_meetings': False,
                'can_view_all_data': False,  # Limited to assigned projects
                'can_manage_billing': False,
                'can_delete_organization': False,
                'can_assign_admin_role': False,
                'can_view_audit_logs': False,
                'can_export_data': False
            }
        }
        
        # Test endpoints for each role
        self.test_endpoints = {
            'organization_management': [
                {'method': 'GET', 'path': '/api/v1/organizations', 'roles': ['owner', 'admin', 'member', 'viewer']},
                {'method': 'POST', 'path': '/api/v1/organizations', 'roles': ['owner']},
                {'method': 'PUT', 'path': '/api/v1/organizations/{org_id}', 'roles': ['owner', 'admin']},
                {'method': 'DELETE', 'path': '/api/v1/organizations/{org_id}', 'roles': ['owner']},
            ],
            'user_management': [
                {'method': 'GET', 'path': '/api/v1/teams/{org_id}/members', 'roles': ['owner', 'admin', 'member', 'viewer']},
                {'method': 'POST', 'path': '/api/v1/organizations/{org_id}/invite', 'roles': ['owner', 'admin', 'member']},
                {'method': 'PUT', 'path': '/api/v1/organizations/{org_id}/members/{user_id}/role', 'roles': ['owner', 'admin']},
                {'method': 'DELETE', 'path': '/api/v1/organizations/{org_id}/members/{user_id}', 'roles': ['owner', 'admin']},
            ],
            'project_management': [
                {'method': 'GET', 'path': '/api/v1/projects', 'roles': ['owner', 'admin', 'member', 'viewer']},
                {'method': 'POST', 'path': '/api/v1/projects', 'roles': ['owner', 'admin']},
                {'method': 'PUT', 'path': '/api/v1/projects/{project_id}', 'roles': ['owner', 'admin', 'member']},
                {'method': 'DELETE', 'path': '/api/v1/projects/{project_id}', 'roles': ['owner', 'admin']},
            ],
            'billing_management': [
                {'method': 'GET', 'path': '/api/v1/organizations/{org_id}/billing', 'roles': ['owner']},
                {'method': 'PUT', 'path': '/api/v1/organizations/{org_id}/billing', 'roles': ['owner']},
                {'method': 'GET', 'path': '/api/v1/organizations/{org_id}/subscription', 'roles': ['owner']},
                {'method': 'PUT', 'path': '/api/v1/organizations/{org_id}/subscription', 'roles': ['owner']},
            ]
        }

    async def setup_test_environment(self):
        """Setup test environment with users and organizations"""
        print("🔧 Setting up test environment...")
        
        # Create test organizations
        self.test_organizations = [
            TestOrganization(
                name="RBAC Test Org 1",
                description="Primary test organization for RBAC testing",
                domain="rbactest1.com"
            ),
            TestOrganization(
                name="RBAC Test Org 2", 
                description="Secondary test organization for multi-org testing",
                domain="rbactest2.com"
            )
        ]
        
        # Create test users for each role
        timestamp = int(time.time())
        self.test_users = {
            'owner': TestUser(
                email=f"owner{timestamp}@rbactest.com",
                password="TestOwner123!",
                first_name="Test",
                last_name="Owner",
                role="owner"
            ),
            'admin': TestUser(
                email=f"admin{timestamp}@rbactest.com",
                password="TestAdmin123!",
                first_name="Test",
                last_name="Admin",
                role="admin"
            ),
            'member': TestUser(
                email=f"member{timestamp}@rbactest.com",
                password="TestMember123!",
                first_name="Test",
                last_name="Member",
                role="member"
            ),
            'viewer': TestUser(
                email=f"viewer{timestamp}@rbactest.com",
                password="TestViewer123!",
                first_name="Test",
                last_name="Viewer",
                role="viewer"
            )
        }
        
        print(f"✅ Created {len(self.test_users)} test users")
        print(f"✅ Created {len(self.test_organizations)} test organizations")
        
        return True

    async def create_test_data(self):
        """Create test data in database"""
        try:
            from app.core.database import get_db
            from app.models.user import User
            from app.models.organization import Organization, OrganizationMember
            from app.core.security import hash_password
            
            print("📊 Creating test data in database...")
            
            async for db in get_db():
                try:
                    # Create organizations
                    for org_data in self.test_organizations:
                        org = Organization(
                            name=org_data.name,
                            description=org_data.description,
                            domain=org_data.domain,
                            created_by=None  # Will be set after owner is created
                        )
                        db.add(org)
                        await db.commit()
                        await db.refresh(org)
                        org_data.organization_id = str(org.id)
                        print(f"   ✅ Created organization: {org_data.name}")
                    
                    # Create users and assign to organizations
                    for role, user_data in self.test_users.items():
                        # Create user
                        user = User(
                            email=user_data.email,
                            password_hash=hash_password(user_data.password),
                            first_name=user_data.first_name,
                            last_name=user_data.last_name,
                            email_verified=True
                        )
                        db.add(user)
                        await db.commit()
                        await db.refresh(user)
                        user_data.user_id = str(user.id)
                        
                        # Assign to first organization
                        org_id = self.test_organizations[0].organization_id
                        user_data.organization_id = org_id
                        
                        # Create organization membership
                        membership = OrganizationMember(
                            organization_id=org_id,
                            user_id=user.id,
                            role=role
                        )
                        db.add(membership)
                        
                        print(f"   ✅ Created {role} user: {user_data.email}")
                    
                    await db.commit()
                    
                    # Update organization owner
                    owner_id = self.test_users['owner'].user_id
                    org = await db.get(Organization, self.test_organizations[0].organization_id)
                    org.created_by = owner_id
                    self.test_organizations[0].owner_id = owner_id
                    await db.commit()
                    
                    print("✅ Test data created successfully")
                    return True
                    
                except Exception as e:
                    print(f"❌ Failed to create test data: {e}")
                    await db.rollback()
                    return False
                
                break
                
        except Exception as e:
            print(f"❌ Database setup failed: {e}")
            return False

    def add_test_result(self, test_name: str, passed: bool, details: str, 
                       role: str, endpoint: str, expected_status: int, 
                       actual_status: int, error_message: str = None):
        """Add test result to results list"""
        result = TestResult(
            test_name=test_name,
            passed=passed,
            details=details,
            role=role,
            endpoint=endpoint,
            expected_status=expected_status,
            actual_status=actual_status,
            error_message=error_message
        )
        self.test_results.append(result)

    async def authenticate_user(self, role: str):
        """Authenticate a test user and get access token"""
        try:
            import requests

            user = self.test_users[role]

            # Login request
            login_data = {
                "email": user.email,
                "password": user.password
            }

            response = requests.post(
                f"{self.base_url}/api/v1/auth/login",
                json=login_data,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                # Extract access token from nested structure
                tokens = data.get("tokens", {})
                user.access_token = tokens.get("access_token")
                print(f"   ✅ Authenticated {role}: {user.email}")
                print(f"      Token: {user.access_token[:20]}..." if user.access_token else "No token")
                return True
            else:
                print(f"   ❌ Failed to authenticate {role}: {response.status_code}")
                return False

        except Exception as e:
            print(f"   ❌ Authentication error for {role}: {e}")
            return False

    async def test_admin_role(self):
        """Test admin role permissions and capabilities"""
        print("\n🔧 TASK 2: ADMIN ROLE TESTING")
        print("=" * 60)

        # Authenticate admin user
        if not await self.authenticate_user('admin'):
            return False

        admin_user = self.test_users['admin']
        headers = {"Authorization": f"Bearer {admin_user.access_token}"}

        import requests

        # Test 1: Organization Management
        print("\n📋 Test 1: Organization Management")

        # GET organizations (should succeed)
        try:
            response = requests.get(f"{self.base_url}/api/v1/organizations", headers=headers, timeout=10)
            self.add_test_result(
                "Admin - Get Organizations",
                response.status_code == 200,
                f"Admin can view organizations: {response.status_code}",
                "admin", "/api/v1/organizations", 200, response.status_code
            )
            print(f"   ✅ GET Organizations: {response.status_code}")
        except Exception as e:
            self.add_test_result("Admin - Get Organizations", False, f"Error: {e}", "admin", "/api/v1/organizations", 200, 0, str(e))
            print(f"   ❌ GET Organizations failed: {e}")

        # PUT organization (should succeed for admin)
        org_id = self.test_organizations[0].organization_id
        update_data = {
            "name": "Updated RBAC Test Org 1",
            "description": "Updated by admin user"
        }

        try:
            response = requests.put(f"{self.base_url}/api/v1/organizations/{org_id}",
                                  json=update_data, headers=headers, timeout=10)
            self.add_test_result(
                "Admin - Update Organization",
                response.status_code in [200, 204],
                f"Admin can update organization: {response.status_code}",
                "admin", f"/api/v1/organizations/{org_id}", 200, response.status_code
            )
            print(f"   ✅ PUT Organization: {response.status_code}")
        except Exception as e:
            self.add_test_result("Admin - Update Organization", False, f"Error: {e}", "admin", f"/api/v1/organizations/{org_id}", 200, 0, str(e))
            print(f"   ❌ PUT Organization failed: {e}")

        # Test 2: User Management
        print("\n👥 Test 2: User Management")

        # GET team members (should succeed)
        try:
            response = requests.get(f"{self.base_url}/api/v1/teams/{org_id}/members", headers=headers, timeout=10)
            self.add_test_result(
                "Admin - Get Team Members",
                response.status_code == 200,
                f"Admin can view team members: {response.status_code}",
                "admin", f"/api/v1/teams/{org_id}/members", 200, response.status_code
            )
            print(f"   ✅ GET Team Members: {response.status_code}")

            if response.status_code == 200:
                members = response.json()
                print(f"      Found {len(members)} team members")
        except Exception as e:
            self.add_test_result("Admin - Get Team Members", False, f"Error: {e}", "admin", f"/api/v1/teams/{org_id}/members", 200, 0, str(e))
            print(f"   ❌ GET Team Members failed: {e}")

        # Test 3: Project Management
        print("\n📊 Test 3: Project Management")

        # GET projects (should succeed)
        try:
            response = requests.get(f"{self.base_url}/api/v1/projects", headers=headers, timeout=10)
            self.add_test_result(
                "Admin - Get Projects",
                response.status_code == 200,
                f"Admin can view projects: {response.status_code}",
                "admin", "/api/v1/projects", 200, response.status_code
            )
            print(f"   ✅ GET Projects: {response.status_code}")
        except Exception as e:
            self.add_test_result("Admin - Get Projects", False, f"Error: {e}", "admin", "/api/v1/projects", 200, 0, str(e))
            print(f"   ❌ GET Projects failed: {e}")

        # POST project (should succeed for admin)
        project_data = {
            "name": "Admin Test Project",
            "description": "Project created by admin for testing",
            "organization_id": org_id
        }

        try:
            response = requests.post(f"{self.base_url}/api/v1/projects",
                                   json=project_data, headers=headers, timeout=10)
            self.add_test_result(
                "Admin - Create Project",
                response.status_code in [200, 201],
                f"Admin can create projects: {response.status_code}",
                "admin", "/api/v1/projects", 201, response.status_code
            )
            print(f"   ✅ POST Project: {response.status_code}")

            if response.status_code in [200, 201]:
                project = response.json()
                print(f"      Created project: {project.get('name', 'Unknown')}")
        except Exception as e:
            self.add_test_result("Admin - Create Project", False, f"Error: {e}", "admin", "/api/v1/projects", 201, 0, str(e))
            print(f"   ❌ POST Project failed: {e}")

        return True

    async def test_member_role(self):
        """Test member role permissions and capabilities"""
        print("\n👥 TASK 3: MEMBER ROLE TESTING")
        print("=" * 60)

        # Authenticate member user
        if not await self.authenticate_user('member'):
            return False

        member_user = self.test_users['member']
        headers = {"Authorization": f"Bearer {member_user.access_token}"}

        import requests

        # Test 1: Organization Management (Limited)
        print("\n📋 Test 1: Organization Management (Limited Access)")

        # GET organizations (should succeed)
        try:
            response = requests.get(f"{self.base_url}/api/v1/organizations", headers=headers, timeout=10)
            self.add_test_result(
                "Member - Get Organizations",
                response.status_code == 200,
                f"Member can view organizations: {response.status_code}",
                "member", "/api/v1/organizations", 200, response.status_code
            )
            print(f"   ✅ GET Organizations: {response.status_code}")
        except Exception as e:
            self.add_test_result("Member - Get Organizations", False, f"Error: {e}", "member", "/api/v1/organizations", 200, 0, str(e))
            print(f"   ❌ GET Organizations failed: {e}")

        # PUT organization (should fail for member)
        org_id = self.test_organizations[0].organization_id
        update_data = {
            "name": "Member Attempted Update",
            "description": "This should fail"
        }

        try:
            response = requests.put(f"{self.base_url}/api/v1/organizations/{org_id}",
                                  json=update_data, headers=headers, timeout=10)
            expected_fail = response.status_code in [403, 401]
            self.add_test_result(
                "Member - Update Organization (Should Fail)",
                expected_fail,
                f"Member correctly denied organization update: {response.status_code}",
                "member", f"/api/v1/organizations/{org_id}", 403, response.status_code
            )
            print(f"   ✅ PUT Organization (Expected Denial): {response.status_code}")
        except Exception as e:
            self.add_test_result("Member - Update Organization", False, f"Error: {e}", "member", f"/api/v1/organizations/{org_id}", 403, 0, str(e))
            print(f"   ❌ PUT Organization failed: {e}")

        # Test 2: User Management (Limited)
        print("\n👥 Test 2: User Management (Limited Access)")

        # GET team members (should succeed)
        try:
            response = requests.get(f"{self.base_url}/api/v1/teams/{org_id}/members", headers=headers, timeout=10)
            self.add_test_result(
                "Member - Get Team Members",
                response.status_code == 200,
                f"Member can view team members: {response.status_code}",
                "member", f"/api/v1/teams/{org_id}/members", 200, response.status_code
            )
            print(f"   ✅ GET Team Members: {response.status_code}")
        except Exception as e:
            self.add_test_result("Member - Get Team Members", False, f"Error: {e}", "member", f"/api/v1/teams/{org_id}/members", 200, 0, str(e))
            print(f"   ❌ GET Team Members failed: {e}")

        return True

    async def test_viewer_role(self):
        """Test viewer role permissions and capabilities"""
        print("\n👁️ TASK 4: VIEWER ROLE TESTING")
        print("=" * 60)

        # Authenticate viewer user
        if not await self.authenticate_user('viewer'):
            return False

        viewer_user = self.test_users['viewer']
        headers = {"Authorization": f"Bearer {viewer_user.access_token}"}

        import requests

        # Test 1: Read-Only Access
        print("\n📖 Test 1: Read-Only Access Verification")

        # GET organizations (should succeed)
        try:
            response = requests.get(f"{self.base_url}/api/v1/organizations", headers=headers, timeout=10)
            self.add_test_result(
                "Viewer - Get Organizations",
                response.status_code == 200,
                f"Viewer can view organizations: {response.status_code}",
                "viewer", "/api/v1/organizations", 200, response.status_code
            )
            print(f"   ✅ GET Organizations: {response.status_code}")
        except Exception as e:
            self.add_test_result("Viewer - Get Organizations", False, f"Error: {e}", "viewer", "/api/v1/organizations", 200, 0, str(e))
            print(f"   ❌ GET Organizations failed: {e}")

        # PUT organization (should fail for viewer)
        org_id = self.test_organizations[0].organization_id
        update_data = {
            "name": "Viewer Attempted Update",
            "description": "This should definitely fail"
        }

        try:
            response = requests.put(f"{self.base_url}/api/v1/organizations/{org_id}",
                                  json=update_data, headers=headers, timeout=10)
            expected_fail = response.status_code in [403, 401]
            self.add_test_result(
                "Viewer - Update Organization (Should Fail)",
                expected_fail,
                f"Viewer correctly denied organization update: {response.status_code}",
                "viewer", f"/api/v1/organizations/{org_id}", 403, response.status_code
            )
            print(f"   ✅ PUT Organization (Expected Denial): {response.status_code}")
        except Exception as e:
            self.add_test_result("Viewer - Update Organization", False, f"Error: {e}", "viewer", f"/api/v1/organizations/{org_id}", 403, 0, str(e))
            print(f"   ❌ PUT Organization failed: {e}")

        return True

    async def generate_test_report(self):
        """Generate comprehensive test report"""
        print("\n📊 COMPREHENSIVE RBAC TEST REPORT")
        print("=" * 80)

        # Summary statistics
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result.passed)
        failed_tests = total_tests - passed_tests

        print(f"📈 SUMMARY STATISTICS:")
        print(f"   Total Tests: {total_tests}")
        print(f"   Passed: {passed_tests} ✅")
        print(f"   Failed: {failed_tests} ❌")
        print(f"   Success Rate: {(passed_tests/total_tests*100):.1f}%" if total_tests > 0 else "   Success Rate: 0%")

        # Results by role
        print(f"\n📋 RESULTS BY ROLE:")
        for role in ['admin', 'member', 'viewer']:
            role_tests = [r for r in self.test_results if r.role == role]
            role_passed = sum(1 for r in role_tests if r.passed)
            role_total = len(role_tests)

            if role_total > 0:
                print(f"   {role.upper()}: {role_passed}/{role_total} ({role_passed/role_total*100:.1f}%)")
                for test in role_tests:
                    status = "✅" if test.passed else "❌"
                    print(f"      {status} {test.test_name}: {test.actual_status}")

        # Detailed results
        print(f"\n📝 DETAILED TEST RESULTS:")
        for result in self.test_results:
            status = "✅ PASS" if result.passed else "❌ FAIL"
            print(f"   {status} | {result.role.upper()} | {result.test_name}")
            print(f"      Endpoint: {result.endpoint}")
            print(f"      Expected: {result.expected_status}, Got: {result.actual_status}")
            print(f"      Details: {result.details}")
            if result.error_message:
                print(f"      Error: {result.error_message}")
            print()

        return True

    async def run_comprehensive_tests(self):
        """Run all RBAC tests"""
        print("\n🚀 Starting Comprehensive RBAC Test Suite")
        print("=" * 80)

        # Setup test environment
        if not await self.setup_test_environment():
            print("❌ Failed to setup test environment")
            return False

        # Create test data
        if not await self.create_test_data():
            print("❌ Failed to create test data")
            return False

        print("\n📋 Test Plan:")
        print("1. Pre-Test Analysis and Setup ✅")
        print("2. Admin Role Testing")
        print("3. Member Role Testing")
        print("4. Viewer Role Testing")
        print("5. User Invitation and Onboarding Workflow")
        print("6. Organization and Project Access Control")
        print("7. Billing and Subscription Management")
        print("8. Database Persistence and Data Integrity")
        print("9. Security and Edge Case Testing")
        print("10. Integration and Final Report")

        # Execute all role tests
        await self.test_admin_role()
        await self.test_member_role()
        await self.test_viewer_role()

        # Generate comprehensive report
        await self.generate_test_report()

        return True

async def main():
    """Main test execution function"""
    test_suite = RBACTestSuite()
    
    try:
        success = await test_suite.run_comprehensive_tests()
        
        if success:
            print("\n🎉 RBAC Test Suite Setup Complete!")
            print("Ready to execute comprehensive role-based access control tests")
        else:
            print("\n❌ RBAC Test Suite Setup Failed!")
            
    except Exception as e:
        print(f"❌ Test suite execution failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
