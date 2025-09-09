#!/usr/bin/env python3
"""
Comprehensive End-to-End Application Testing
"""
import asyncio
import requests
import time
import json
import sys
import os
from sqlalchemy import text

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__)))

base_url = "http://127.0.0.1:8000"

class ComprehensiveE2ETest:
    def __init__(self):
        self.test_results = {
            "user_journey": [],
            "crud_operations": [],
            "rbac_tests": [],
            "database_verification": [],
            "entity_tests": [],
            "persistence_validation": [],
            "integration_tests": []
        }
        self.test_users = {}
        self.test_data = {
            "organizations": [],
            "projects": [],
            "boards": [],
            "cards": [],
            "columns": []
        }
        
    async def run_comprehensive_tests(self):
        """Run all comprehensive tests"""
        print("🚀 COMPREHENSIVE END-TO-END APPLICATION TESTING")
        print("=" * 80)
        
        try:
            # 1. Full Application Testing
            await self.test_complete_user_journey()
            await self.test_crud_operations()
            await self.test_rbac_system()
            
            # 2. Database Data Verification
            await self.verify_database_data()
            
            # 3. Specific Entity Testing
            await self.test_boards_functionality()
            await self.test_cards_functionality()
            await self.test_checklist_functionality()
            await self.test_user_data()
            
            # 4. Data Persistence Validation
            await self.validate_data_persistence()
            
            # 5. Integration Testing
            await self.test_api_integration()
            
            # Generate comprehensive report
            await self.generate_test_report()
            
        except Exception as e:
            print(f"❌ Comprehensive testing failed: {e}")
            import traceback
            traceback.print_exc()
    
    async def test_complete_user_journey(self):
        """Test complete user journey from registration to project management"""
        print("\n1️⃣ COMPLETE USER JOURNEY TESTING")
        print("-" * 60)
        
        journey_results = []
        timestamp = int(time.time())
        
        # Step 1: User Registration
        print("   📝 Step 1: User Registration")
        user_data = {
            "email": f"journey_user_{timestamp}@example.com",
            "password": "JourneyTest123!",
            "first_name": "Journey",
            "last_name": "User"
        }
        
        try:
            response = requests.post(f"{base_url}/api/v1/auth/register", json=user_data, timeout=10)
            if response.status_code == 201:
                reg_data = response.json()
                token = reg_data.get('tokens', {}).get('access_token')
                headers = {"Authorization": f"Bearer {token}"}
                self.test_users['journey_user'] = {
                    'data': user_data,
                    'token': token,
                    'headers': headers,
                    'user_id': reg_data.get('user', {}).get('id')
                }
                journey_results.append("✅ Registration successful")
                print("      ✅ User registered successfully")
            else:
                journey_results.append(f"❌ Registration failed: {response.status_code}")
                print(f"      ❌ Registration failed: {response.status_code}")
                return
        except Exception as e:
            journey_results.append(f"❌ Registration error: {e}")
            print(f"      ❌ Registration error: {e}")
            return
        
        # Step 2: Get User Profile
        print("   👤 Step 2: Get User Profile")
        try:
            response = requests.get(f"{base_url}/api/v1/auth/me", headers=headers, timeout=10)
            if response.status_code == 200:
                journey_results.append("✅ Profile retrieval successful")
                print("      ✅ Profile retrieved successfully")
            else:
                journey_results.append(f"❌ Profile retrieval failed: {response.status_code}")
                print(f"      ❌ Profile retrieval failed: {response.status_code}")
        except Exception as e:
            journey_results.append(f"❌ Profile error: {e}")
            print(f"      ❌ Profile error: {e}")
        
        # Step 3: Get Organizations
        print("   🏢 Step 3: Get Organizations")
        try:
            response = requests.get(f"{base_url}/api/v1/organizations", headers=headers, timeout=10)
            if response.status_code == 200:
                orgs = response.json()
                if orgs and len(orgs) > 0:
                    org_id = orgs[0].get('id')
                    self.test_data['organizations'].append({'id': org_id, 'name': orgs[0].get('name')})
                    journey_results.append("✅ Organizations retrieved successfully")
                    print(f"      ✅ Found {len(orgs)} organizations")
                else:
                    journey_results.append("⚠️ No organizations found")
                    print("      ⚠️ No organizations found")
            else:
                journey_results.append(f"❌ Organizations retrieval failed: {response.status_code}")
                print(f"      ❌ Organizations retrieval failed: {response.status_code}")
        except Exception as e:
            journey_results.append(f"❌ Organizations error: {e}")
            print(f"      ❌ Organizations error: {e}")
        
        # Step 4: Create Project
        print("   📊 Step 4: Create Project")
        if self.test_data['organizations']:
            org_id = self.test_data['organizations'][0]['id']
            project_data = {
                "name": f"Journey Test Project {timestamp}",
                "description": "End-to-end journey test project",
                "organization_id": org_id
            }
            
            try:
                response = requests.post(f"{base_url}/api/v1/projects", json=project_data, headers=headers, timeout=10)
                if response.status_code == 201:
                    project = response.json()
                    self.test_data['projects'].append(project)
                    journey_results.append("✅ Project created successfully")
                    print("      ✅ Project created successfully")
                else:
                    journey_results.append(f"❌ Project creation failed: {response.status_code}")
                    print(f"      ❌ Project creation failed: {response.status_code}")
                    try:
                        error_data = response.json()
                        print(f"      📋 Error details: {error_data}")
                    except:
                        print(f"      📋 Raw response: {response.text}")
            except Exception as e:
                journey_results.append(f"❌ Project creation error: {e}")
                print(f"      ❌ Project creation error: {e}")
        
        # Step 5: Create Board
        print("   📋 Step 5: Create Board")
        if self.test_data['projects']:
            project_id = self.test_data['projects'][0].get('id')
            board_data = {
                "name": f"Journey Test Board {timestamp}",
                "description": "End-to-end journey test board",
                "project_id": project_id
            }
            
            try:
                response = requests.post(f"{base_url}/api/v1/boards", json=board_data, headers=headers, timeout=10)
                if response.status_code == 201:
                    board = response.json()
                    self.test_data['boards'].append(board)
                    journey_results.append("✅ Board created successfully")
                    print("      ✅ Board created successfully")
                else:
                    journey_results.append(f"❌ Board creation failed: {response.status_code}")
                    print(f"      ❌ Board creation failed: {response.status_code}")
            except Exception as e:
                journey_results.append(f"❌ Board creation error: {e}")
                print(f"      ❌ Board creation error: {e}")
        
        # Step 6: Create Column
        print("   📝 Step 6: Create Column")
        if self.test_data['boards']:
            board_id = self.test_data['boards'][0].get('id')
            column_data = {
                "name": "To Do",
                "position": 0,
                "board_id": board_id
            }
            
            try:
                response = requests.post(f"{base_url}/api/v1/columns", json=column_data, headers=headers, timeout=10)
                if response.status_code == 201:
                    column = response.json()
                    self.test_data['columns'].append(column)
                    journey_results.append("✅ Column created successfully")
                    print("      ✅ Column created successfully")
                else:
                    journey_results.append(f"❌ Column creation failed: {response.status_code}")
                    print(f"      ❌ Column creation failed: {response.status_code}")
            except Exception as e:
                journey_results.append(f"❌ Column creation error: {e}")
                print(f"      ❌ Column creation error: {e}")
        
        # Step 7: Create Card
        print("   🎴 Step 7: Create Card")
        if self.test_data['columns']:
            column_id = self.test_data['columns'][0].get('id')
            card_data = {
                "title": f"Journey Test Card {timestamp}",
                "description": "End-to-end journey test card",
                "column_id": column_id
            }
            
            try:
                response = requests.post(f"{base_url}/api/v1/cards", json=card_data, headers=headers, timeout=10)
                if response.status_code == 201:
                    card = response.json()
                    self.test_data['cards'].append(card)
                    journey_results.append("✅ Card created successfully")
                    print("      ✅ Card created successfully")
                else:
                    journey_results.append(f"❌ Card creation failed: {response.status_code}")
                    print(f"      ❌ Card creation failed: {response.status_code}")
            except Exception as e:
                journey_results.append(f"❌ Card creation error: {e}")
                print(f"      ❌ Card creation error: {e}")
        
        self.test_results['user_journey'] = journey_results
        
        # Summary
        success_count = len([r for r in journey_results if r.startswith("✅")])
        total_count = len(journey_results)
        print(f"\n   📊 User Journey Summary: {success_count}/{total_count} steps successful")
    
    async def test_crud_operations(self):
        """Test CRUD operations across all entities"""
        print("\n2️⃣ CRUD OPERATIONS TESTING")
        print("-" * 60)
        
        if not self.test_users.get('journey_user'):
            print("   ❌ No test user available for CRUD testing")
            return
        
        headers = self.test_users['journey_user']['headers']
        crud_results = []
        
        # Test READ operations
        print("   📖 Testing READ operations")
        read_endpoints = [
            ("/api/v1/auth/me", "User Profile"),
            ("/api/v1/organizations", "Organizations"),
            ("/api/v1/projects", "Projects"),
            ("/api/v1/boards", "Boards"),
            ("/api/v1/cards", "Cards")
        ]
        
        for endpoint, name in read_endpoints:
            try:
                response = requests.get(f"{base_url}{endpoint}", headers=headers, timeout=10)
                if response.status_code == 200:
                    crud_results.append(f"✅ READ {name}: Success")
                    print(f"      ✅ READ {name}: {response.status_code}")
                else:
                    crud_results.append(f"❌ READ {name}: {response.status_code}")
                    print(f"      ❌ READ {name}: {response.status_code}")
            except Exception as e:
                crud_results.append(f"❌ READ {name}: Error - {e}")
                print(f"      ❌ READ {name}: Error - {e}")
        
        # Test UPDATE operations
        print("   ✏️ Testing UPDATE operations")
        if self.test_data['cards']:
            card_id = self.test_data['cards'][0].get('id')
            update_data = {
                "title": "Updated Journey Test Card",
                "description": "Updated description for testing"
            }
            
            try:
                response = requests.put(f"{base_url}/api/v1/cards/{card_id}", json=update_data, headers=headers, timeout=10)
                if response.status_code == 200:
                    crud_results.append("✅ UPDATE Card: Success")
                    print("      ✅ UPDATE Card: Success")
                else:
                    crud_results.append(f"❌ UPDATE Card: {response.status_code}")
                    print(f"      ❌ UPDATE Card: {response.status_code}")
            except Exception as e:
                crud_results.append(f"❌ UPDATE Card: Error - {e}")
                print(f"      ❌ UPDATE Card: Error - {e}")
        
        self.test_results['crud_operations'] = crud_results
        
        success_count = len([r for r in crud_results if r.startswith("✅")])
        total_count = len(crud_results)
        print(f"\n   📊 CRUD Operations Summary: {success_count}/{total_count} operations successful")
    
    async def test_rbac_system(self):
        """Test Role-Based Access Control"""
        print("\n3️⃣ RBAC SYSTEM TESTING")
        print("-" * 60)
        
        # Test with existing RBAC users
        rbac_users = {
            "owner": {"email": "owner1755850537@rbactest.com", "password": "TestOwner123!"},
            "admin": {"email": "admin1755850537@rbactest.com", "password": "TestAdmin123!"},
            "member": {"email": "member1755850537@rbactest.com", "password": "TestMember123!"},
            "viewer": {"email": "viewer1755850537@rbactest.com", "password": "TestViewer123!"}
        }
        
        rbac_results = []
        
        # Authenticate each role
        authenticated_users = {}
        for role, credentials in rbac_users.items():
            try:
                response = requests.post(f"{base_url}/api/v1/auth/login", json=credentials, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    token = data.get('tokens', {}).get('access_token')
                    authenticated_users[role] = {"Authorization": f"Bearer {token}"}
                    rbac_results.append(f"✅ {role.upper()} authentication: Success")
                    print(f"      ✅ {role.upper()} authenticated")
                else:
                    rbac_results.append(f"❌ {role.upper()} authentication: {response.status_code}")
                    print(f"      ❌ {role.upper()} authentication failed: {response.status_code}")
            except Exception as e:
                rbac_results.append(f"❌ {role.upper()} authentication: Error - {e}")
                print(f"      ❌ {role.upper()} authentication error: {e}")
        
        # Test role-specific access
        print("   🔐 Testing role-specific access")
        
        # Test organization creation (should only work for owners)
        org_data = {"name": f"RBAC Test Org {int(time.time())}", "description": "RBAC testing"}
        
        for role, headers in authenticated_users.items():
            try:
                response = requests.post(f"{base_url}/api/v1/organizations", json=org_data, headers=headers, timeout=10)
                if role == "owner":
                    expected = [200, 201]
                    success = response.status_code in expected
                else:
                    expected = [403]
                    success = response.status_code in expected
                
                if success:
                    rbac_results.append(f"✅ {role.upper()} org creation: Correct ({response.status_code})")
                    print(f"      ✅ {role.upper()} org creation: {response.status_code}")
                else:
                    rbac_results.append(f"❌ {role.upper()} org creation: Wrong ({response.status_code})")
                    print(f"      ❌ {role.upper()} org creation: {response.status_code}")
            except Exception as e:
                rbac_results.append(f"❌ {role.upper()} org creation: Error - {e}")
                print(f"      ❌ {role.upper()} org creation error: {e}")
        
        self.test_results['rbac_tests'] = rbac_results
        
        success_count = len([r for r in rbac_results if r.startswith("✅")])
        total_count = len(rbac_results)
        print(f"\n   📊 RBAC Testing Summary: {success_count}/{total_count} tests successful")

    async def verify_database_data(self):
        """Verify database data integrity and population"""
        print("\n4️⃣ DATABASE DATA VERIFICATION")
        print("-" * 60)

        try:
            from app.core.database import get_db

            async for db in get_db():
                verification_results = []

                # Check key table record counts
                key_tables = [
                    'users', 'organizations', 'organization_members',
                    'projects', 'boards', 'cards', 'sessions', 'registrations'
                ]

                print("   📊 Checking table record counts:")
                table_counts = {}

                for table in key_tables:
                    try:
                        result = await db.execute(text(f"SELECT COUNT(*) FROM {table}"))
                        count = result.scalar()
                        table_counts[table] = count
                        print(f"      📋 {table}: {count} records")

                        if count > 0:
                            verification_results.append(f"✅ {table}: {count} records")
                        else:
                            verification_results.append(f"⚠️ {table}: Empty")
                    except Exception as e:
                        verification_results.append(f"❌ {table}: Error - {e}")
                        print(f"      ❌ {table}: Error - {e}")

                # Check foreign key relationships
                print("\n   🔗 Checking foreign key relationships:")

                # Users -> Organizations relationship
                try:
                    result = await db.execute(text("""
                        SELECT COUNT(*) FROM organization_members om
                        JOIN users u ON om.user_id = u.id
                        JOIN organizations o ON om.organization_id = o.id
                    """))
                    valid_memberships = result.scalar()
                    print(f"      ✅ Valid user-organization memberships: {valid_memberships}")
                    verification_results.append(f"✅ User-Org relationships: {valid_memberships}")
                except Exception as e:
                    print(f"      ❌ User-Org relationship check failed: {e}")
                    verification_results.append(f"❌ User-Org relationships: Error")

                # Projects -> Organizations relationship
                try:
                    result = await db.execute(text("""
                        SELECT COUNT(*) FROM projects p
                        JOIN organizations o ON p.organization_id = o.id
                    """))
                    valid_projects = result.scalar()
                    print(f"      ✅ Valid project-organization relationships: {valid_projects}")
                    verification_results.append(f"✅ Project-Org relationships: {valid_projects}")
                except Exception as e:
                    print(f"      ❌ Project-Org relationship check failed: {e}")
                    verification_results.append(f"❌ Project-Org relationships: Error")

                # Boards -> Projects relationship
                try:
                    result = await db.execute(text("""
                        SELECT COUNT(*) FROM boards b
                        JOIN projects p ON b.project_id = p.id
                    """))
                    valid_boards = result.scalar()
                    print(f"      ✅ Valid board-project relationships: {valid_boards}")
                    verification_results.append(f"✅ Board-Project relationships: {valid_boards}")
                except Exception as e:
                    print(f"      ❌ Board-Project relationship check failed: {e}")
                    verification_results.append(f"❌ Board-Project relationships: Error")

                # Check data consistency
                print("\n   🔍 Checking data consistency:")

                # Check for orphaned records
                try:
                    result = await db.execute(text("""
                        SELECT COUNT(*) FROM organization_members om
                        LEFT JOIN users u ON om.user_id = u.id
                        WHERE u.id IS NULL
                    """))
                    orphaned_memberships = result.scalar()
                    if orphaned_memberships == 0:
                        print(f"      ✅ No orphaned organization memberships")
                        verification_results.append("✅ No orphaned memberships")
                    else:
                        print(f"      ❌ Found {orphaned_memberships} orphaned memberships")
                        verification_results.append(f"❌ {orphaned_memberships} orphaned memberships")
                except Exception as e:
                    print(f"      ❌ Orphaned records check failed: {e}")
                    verification_results.append("❌ Orphaned records check failed")

                self.test_results['database_verification'] = verification_results

                success_count = len([r for r in verification_results if r.startswith("✅")])
                total_count = len(verification_results)
                print(f"\n   📊 Database Verification Summary: {success_count}/{total_count} checks successful")

                break

        except Exception as e:
            print(f"   ❌ Database verification failed: {e}")
            self.test_results['database_verification'] = [f"❌ Database verification failed: {e}"]

    async def test_boards_functionality(self):
        """Test boards functionality specifically"""
        print("\n5️⃣ BOARDS FUNCTIONALITY TESTING")
        print("-" * 60)

        if not self.test_users.get('journey_user'):
            print("   ❌ No test user available for boards testing")
            return

        headers = self.test_users['journey_user']['headers']
        boards_results = []

        # Test board creation with different data
        print("   📋 Testing board creation variations")

        if self.test_data['projects']:
            project_id = self.test_data['projects'][0].get('id')

            # Test 1: Minimal board data
            minimal_board = {
                "name": "Minimal Test Board",
                "project_id": project_id
            }

            try:
                response = requests.post(f"{base_url}/api/v1/boards", json=minimal_board, headers=headers, timeout=10)
                if response.status_code == 201:
                    boards_results.append("✅ Minimal board creation: Success")
                    print("      ✅ Minimal board created successfully")
                else:
                    boards_results.append(f"❌ Minimal board creation: {response.status_code}")
                    print(f"      ❌ Minimal board creation failed: {response.status_code}")
            except Exception as e:
                boards_results.append(f"❌ Minimal board creation: Error - {e}")
                print(f"      ❌ Minimal board creation error: {e}")

            # Test 2: Full board data
            full_board = {
                "name": "Full Test Board",
                "description": "Complete board with all fields",
                "project_id": project_id
            }

            try:
                response = requests.post(f"{base_url}/api/v1/boards", json=full_board, headers=headers, timeout=10)
                if response.status_code == 201:
                    board_data = response.json()
                    self.test_data['boards'].append(board_data)
                    boards_results.append("✅ Full board creation: Success")
                    print("      ✅ Full board created successfully")
                else:
                    boards_results.append(f"❌ Full board creation: {response.status_code}")
                    print(f"      ❌ Full board creation failed: {response.status_code}")
            except Exception as e:
                boards_results.append(f"❌ Full board creation: Error - {e}")
                print(f"      ❌ Full board creation error: {e}")

        # Test board retrieval
        print("   📖 Testing board retrieval")
        try:
            response = requests.get(f"{base_url}/api/v1/boards", headers=headers, timeout=10)
            if response.status_code == 200:
                boards = response.json()
                boards_results.append(f"✅ Board retrieval: {len(boards)} boards found")
                print(f"      ✅ Retrieved {len(boards)} boards")
            else:
                boards_results.append(f"❌ Board retrieval: {response.status_code}")
                print(f"      ❌ Board retrieval failed: {response.status_code}")
        except Exception as e:
            boards_results.append(f"❌ Board retrieval: Error - {e}")
            print(f"      ❌ Board retrieval error: {e}")

        # Test board update
        print("   ✏️ Testing board update")
        if self.test_data['boards']:
            board_id = self.test_data['boards'][-1].get('id')  # Use the latest board
            update_data = {
                "name": "Updated Test Board",
                "description": "Updated description for testing"
            }

            try:
                response = requests.put(f"{base_url}/api/v1/boards/{board_id}", json=update_data, headers=headers, timeout=10)
                if response.status_code == 200:
                    boards_results.append("✅ Board update: Success")
                    print("      ✅ Board updated successfully")
                else:
                    boards_results.append(f"❌ Board update: {response.status_code}")
                    print(f"      ❌ Board update failed: {response.status_code}")
            except Exception as e:
                boards_results.append(f"❌ Board update: Error - {e}")
                print(f"      ❌ Board update error: {e}")

        self.test_results['entity_tests'].extend(boards_results)

        success_count = len([r for r in boards_results if r.startswith("✅")])
        total_count = len(boards_results)
        print(f"\n   📊 Boards Testing Summary: {success_count}/{total_count} tests successful")

    async def test_cards_functionality(self):
        """Test cards functionality specifically"""
        print("\n6️⃣ CARDS FUNCTIONALITY TESTING")
        print("-" * 60)

        if not self.test_users.get('journey_user'):
            print("   ❌ No test user available for cards testing")
            return

        headers = self.test_users['journey_user']['headers']
        cards_results = []

        # Test card creation with different data
        print("   🎴 Testing card creation variations")

        if self.test_data['columns']:
            column_id = self.test_data['columns'][0].get('id')

            # Test 1: Minimal card data
            minimal_card = {
                "title": "Minimal Test Card",
                "column_id": column_id
            }

            try:
                response = requests.post(f"{base_url}/api/v1/cards", json=minimal_card, headers=headers, timeout=10)
                if response.status_code == 201:
                    cards_results.append("✅ Minimal card creation: Success")
                    print("      ✅ Minimal card created successfully")
                else:
                    cards_results.append(f"❌ Minimal card creation: {response.status_code}")
                    print(f"      ❌ Minimal card creation failed: {response.status_code}")
            except Exception as e:
                cards_results.append(f"❌ Minimal card creation: Error - {e}")
                print(f"      ❌ Minimal card creation error: {e}")

            # Test 2: Full card data
            full_card = {
                "title": "Full Test Card",
                "description": "Complete card with all fields",
                "column_id": column_id,
                "priority": "high",
                "due_date": "2025-12-31T23:59:59Z"
            }

            try:
                response = requests.post(f"{base_url}/api/v1/cards", json=full_card, headers=headers, timeout=10)
                if response.status_code == 201:
                    card_data = response.json()
                    self.test_data['cards'].append(card_data)
                    cards_results.append("✅ Full card creation: Success")
                    print("      ✅ Full card created successfully")
                else:
                    cards_results.append(f"❌ Full card creation: {response.status_code}")
                    print(f"      ❌ Full card creation failed: {response.status_code}")
            except Exception as e:
                cards_results.append(f"❌ Full card creation: Error - {e}")
                print(f"      ❌ Full card creation error: {e}")

        # Test card retrieval
        print("   📖 Testing card retrieval")
        try:
            response = requests.get(f"{base_url}/api/v1/cards", headers=headers, timeout=10)
            if response.status_code == 200:
                cards = response.json()
                cards_results.append(f"✅ Card retrieval: {len(cards)} cards found")
                print(f"      ✅ Retrieved {len(cards)} cards")
            else:
                cards_results.append(f"❌ Card retrieval: {response.status_code}")
                print(f"      ❌ Card retrieval failed: {response.status_code}")
        except Exception as e:
            cards_results.append(f"❌ Card retrieval: Error - {e}")
            print(f"      ❌ Card retrieval error: {e}")

        self.test_results['entity_tests'].extend(cards_results)

        success_count = len([r for r in cards_results if r.startswith("✅")])
        total_count = len(cards_results)
        print(f"\n   📊 Cards Testing Summary: {success_count}/{total_count} tests successful")

    async def test_checklist_functionality(self):
        """Test checklist functionality"""
        print("\n7️⃣ CHECKLIST FUNCTIONALITY TESTING")
        print("-" * 60)

        if not self.test_users.get('journey_user'):
            print("   ❌ No test user available for checklist testing")
            return

        headers = self.test_users['journey_user']['headers']
        checklist_results = []

        # Test checklist item creation
        print("   ☑️ Testing checklist item creation")

        if self.test_data['cards']:
            card_id = self.test_data['cards'][0].get('id')

            # Create checklist items
            checklist_items = [
                {"title": "Test checklist item 1", "completed": False},
                {"title": "Test checklist item 2", "completed": False},
                {"title": "Test checklist item 3", "completed": True}
            ]

            for i, item_data in enumerate(checklist_items, 1):
                item_data['card_id'] = card_id

                try:
                    response = requests.post(f"{base_url}/api/v1/checklist", json=item_data, headers=headers, timeout=10)
                    if response.status_code == 201:
                        checklist_results.append(f"✅ Checklist item {i} creation: Success")
                        print(f"      ✅ Checklist item {i} created successfully")
                    else:
                        checklist_results.append(f"❌ Checklist item {i} creation: {response.status_code}")
                        print(f"      ❌ Checklist item {i} creation failed: {response.status_code}")
                except Exception as e:
                    checklist_results.append(f"❌ Checklist item {i} creation: Error - {e}")
                    print(f"      ❌ Checklist item {i} creation error: {e}")

        self.test_results['entity_tests'].extend(checklist_results)

        success_count = len([r for r in checklist_results if r.startswith("✅")])
        total_count = len(checklist_results)
        print(f"\n   📊 Checklist Testing Summary: {success_count}/{total_count} tests successful")

    async def test_user_data(self):
        """Test user data validation"""
        print("\n8️⃣ USER DATA TESTING")
        print("-" * 60)

        if not self.test_users.get('journey_user'):
            print("   ❌ No test user available for user data testing")
            return

        headers = self.test_users['journey_user']['headers']
        user_results = []

        # Test user profile retrieval
        print("   👤 Testing user profile data")
        try:
            response = requests.get(f"{base_url}/api/v1/auth/me", headers=headers, timeout=10)
            if response.status_code == 200:
                user_data = response.json()

                # Validate user data structure
                required_fields = ['id', 'email', 'first_name', 'last_name']
                missing_fields = [field for field in required_fields if field not in user_data]

                if not missing_fields:
                    user_results.append("✅ User profile structure: Complete")
                    print("      ✅ User profile has all required fields")
                else:
                    user_results.append(f"❌ User profile structure: Missing {missing_fields}")
                    print(f"      ❌ User profile missing fields: {missing_fields}")

                # Check email format
                email = user_data.get('email', '')
                if '@' in email and '.' in email:
                    user_results.append("✅ Email format: Valid")
                    print("      ✅ Email format is valid")
                else:
                    user_results.append("❌ Email format: Invalid")
                    print("      ❌ Email format is invalid")

            else:
                user_results.append(f"❌ User profile retrieval: {response.status_code}")
                print(f"      ❌ User profile retrieval failed: {response.status_code}")
        except Exception as e:
            user_results.append(f"❌ User profile retrieval: Error - {e}")
            print(f"      ❌ User profile retrieval error: {e}")

        self.test_results['entity_tests'].extend(user_results)

        success_count = len([r for r in user_results if r.startswith("✅")])
        total_count = len(user_results)
        print(f"\n   📊 User Data Testing Summary: {success_count}/{total_count} tests successful")

    async def validate_data_persistence(self):
        """Validate data persistence in database"""
        print("\n9️⃣ DATA PERSISTENCE VALIDATION")
        print("-" * 60)

        try:
            from app.core.database import get_db

            async for db in get_db():
                persistence_results = []

                # Check if created entities exist in database
                print("   💾 Validating entity persistence")

                # Check journey user exists
                if self.test_users.get('journey_user'):
                    user_email = self.test_users['journey_user']['data']['email']
                    try:
                        result = await db.execute(text("SELECT COUNT(*) FROM users WHERE email = :email"), {"email": user_email})
                        count = result.scalar()
                        if count > 0:
                            persistence_results.append("✅ Journey user persisted")
                            print("      ✅ Journey user found in database")
                        else:
                            persistence_results.append("❌ Journey user not persisted")
                            print("      ❌ Journey user not found in database")
                    except Exception as e:
                        persistence_results.append(f"❌ Journey user check: Error - {e}")
                        print(f"      ❌ Journey user check error: {e}")

                # Check created projects exist
                if self.test_data['projects']:
                    project_name = self.test_data['projects'][0].get('name')
                    try:
                        result = await db.execute(text("SELECT COUNT(*) FROM projects WHERE name = :name"), {"name": project_name})
                        count = result.scalar()
                        if count > 0:
                            persistence_results.append("✅ Test project persisted")
                            print("      ✅ Test project found in database")
                        else:
                            persistence_results.append("❌ Test project not persisted")
                            print("      ❌ Test project not found in database")
                    except Exception as e:
                        persistence_results.append(f"❌ Test project check: Error - {e}")
                        print(f"      ❌ Test project check error: {e}")

                # Check created boards exist
                if self.test_data['boards']:
                    board_name = self.test_data['boards'][0].get('name')
                    try:
                        result = await db.execute(text("SELECT COUNT(*) FROM boards WHERE name = :name"), {"name": board_name})
                        count = result.scalar()
                        if count > 0:
                            persistence_results.append("✅ Test board persisted")
                            print("      ✅ Test board found in database")
                        else:
                            persistence_results.append("❌ Test board not persisted")
                            print("      ❌ Test board not found in database")
                    except Exception as e:
                        persistence_results.append(f"❌ Test board check: Error - {e}")
                        print(f"      ❌ Test board check error: {e}")

                # Check created cards exist
                if self.test_data['cards']:
                    card_title = self.test_data['cards'][0].get('title')
                    try:
                        result = await db.execute(text("SELECT COUNT(*) FROM cards WHERE title = :title"), {"title": card_title})
                        count = result.scalar()
                        if count > 0:
                            persistence_results.append("✅ Test card persisted")
                            print("      ✅ Test card found in database")
                        else:
                            persistence_results.append("❌ Test card not persisted")
                            print("      ❌ Test card not found in database")
                    except Exception as e:
                        persistence_results.append(f"❌ Test card check: Error - {e}")
                        print(f"      ❌ Test card check error: {e}")

                self.test_results['persistence_validation'] = persistence_results

                success_count = len([r for r in persistence_results if r.startswith("✅")])
                total_count = len(persistence_results)
                print(f"\n   📊 Persistence Validation Summary: {success_count}/{total_count} checks successful")

                break

        except Exception as e:
            print(f"   ❌ Persistence validation failed: {e}")
            self.test_results['persistence_validation'] = [f"❌ Persistence validation failed: {e}"]

    async def test_api_integration(self):
        """Test API integration"""
        print("\n🔟 API INTEGRATION TESTING")
        print("-" * 60)

        integration_results = []

        # Test authentication token validity across endpoints
        print("   🔑 Testing token validity across endpoints")

        if self.test_users.get('journey_user'):
            headers = self.test_users['journey_user']['headers']

            # Test multiple endpoints with same token
            endpoints = [
                "/api/v1/auth/me",
                "/api/v1/organizations",
                "/api/v1/projects",
                "/api/v1/boards",
                "/api/v1/cards"
            ]

            for endpoint in endpoints:
                try:
                    response = requests.get(f"{base_url}{endpoint}", headers=headers, timeout=10)
                    if response.status_code in [200, 201]:
                        integration_results.append(f"✅ Token valid for {endpoint}")
                        print(f"      ✅ Token works for {endpoint}")
                    else:
                        integration_results.append(f"❌ Token invalid for {endpoint}: {response.status_code}")
                        print(f"      ❌ Token failed for {endpoint}: {response.status_code}")
                except Exception as e:
                    integration_results.append(f"❌ Token test for {endpoint}: Error - {e}")
                    print(f"      ❌ Token test for {endpoint}: Error - {e}")

        # Test API response format consistency
        print("   📋 Testing API response format consistency")

        if self.test_users.get('journey_user'):
            headers = self.test_users['journey_user']['headers']

            try:
                response = requests.get(f"{base_url}/api/v1/auth/me", headers=headers, timeout=10)
                if response.status_code == 200:
                    data = response.json()

                    # Check if response has expected structure
                    if isinstance(data, dict):
                        integration_results.append("✅ API response format: Valid JSON object")
                        print("      ✅ API returns valid JSON object")
                    else:
                        integration_results.append("❌ API response format: Not a JSON object")
                        print("      ❌ API does not return JSON object")
                else:
                    integration_results.append(f"❌ API response test: {response.status_code}")
                    print(f"      ❌ API response test failed: {response.status_code}")
            except Exception as e:
                integration_results.append(f"❌ API response test: Error - {e}")
                print(f"      ❌ API response test error: {e}")

        self.test_results['integration_tests'] = integration_results

        success_count = len([r for r in integration_results if r.startswith("✅")])
        total_count = len(integration_results)
        print(f"\n   📊 Integration Testing Summary: {success_count}/{total_count} tests successful")

    async def generate_test_report(self):
        """Generate comprehensive test report"""
        print("\n" + "=" * 80)
        print("📊 COMPREHENSIVE END-TO-END TEST REPORT")
        print("=" * 80)

        # Calculate overall statistics
        all_results = []
        for category, results in self.test_results.items():
            all_results.extend(results)

        total_tests = len(all_results)
        successful_tests = len([r for r in all_results if r.startswith("✅")])
        failed_tests = len([r for r in all_results if r.startswith("❌")])
        warning_tests = len([r for r in all_results if r.startswith("⚠️")])

        success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0

        print(f"\n📈 OVERALL STATISTICS:")
        print(f"   Total Tests: {total_tests}")
        print(f"   ✅ Successful: {successful_tests}")
        print(f"   ❌ Failed: {failed_tests}")
        print(f"   ⚠️ Warnings: {warning_tests}")
        print(f"   📊 Success Rate: {success_rate:.1f}%")

        # Category breakdown
        print(f"\n📋 CATEGORY BREAKDOWN:")
        for category, results in self.test_results.items():
            if results:
                category_success = len([r for r in results if r.startswith("✅")])
                category_total = len(results)
                category_rate = (category_success / category_total * 100) if category_total > 0 else 0
                print(f"   {category.replace('_', ' ').title()}: {category_success}/{category_total} ({category_rate:.1f}%)")

        # Test data summary
        print(f"\n📊 TEST DATA CREATED:")
        print(f"   Organizations: {len(self.test_data['organizations'])}")
        print(f"   Projects: {len(self.test_data['projects'])}")
        print(f"   Boards: {len(self.test_data['boards'])}")
        print(f"   Cards: {len(self.test_data['cards'])}")
        print(f"   Columns: {len(self.test_data['columns'])}")

        # Final assessment
        print(f"\n🎯 FINAL ASSESSMENT:")
        if success_rate >= 90:
            print("   ✅ EXCELLENT: System is production-ready")
        elif success_rate >= 80:
            print("   ✅ GOOD: System is mostly functional with minor issues")
        elif success_rate >= 70:
            print("   ⚠️ ACCEPTABLE: System has some issues that need attention")
        else:
            print("   ❌ NEEDS WORK: System has significant issues")

        print("=" * 80)

if __name__ == "__main__":
    test_suite = ComprehensiveE2ETest()
    asyncio.run(test_suite.run_comprehensive_tests())
