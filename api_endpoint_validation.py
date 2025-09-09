#!/usr/bin/env python3
"""
API Endpoint Validation - Test Specific Issues Found
"""
import requests
import time
import json

base_url = "http://127.0.0.1:8000"

def test_api_endpoints():
    """Test specific API endpoints that showed issues"""
    print("🔍 API ENDPOINT VALIDATION")
    print("=" * 80)
    
    # First, authenticate to get a token
    print("\n1️⃣ AUTHENTICATION")
    print("-" * 60)
    
    login_data = {"email": "owner1755850537@rbactest.com", "password": "TestOwner123!"}
    try:
        response = requests.post(f"{base_url}/api/v1/auth/login", json=login_data, timeout=10)
        if response.status_code == 200:
            data = response.json()
            token = data.get('tokens', {}).get('access_token')
            headers = {"Authorization": f"Bearer {token}"}
            print("   ✅ Authentication successful")
        else:
            print(f"   ❌ Authentication failed: {response.status_code}")
            return
    except Exception as e:
        print(f"   ❌ Authentication error: {e}")
        return
    
    # Test project creation with correct parameters
    print("\n2️⃣ PROJECT CREATION TESTING")
    print("-" * 60)
    
    # Get organization first
    try:
        response = requests.get(f"{base_url}/api/v1/organizations", headers=headers, timeout=10)
        if response.status_code == 200:
            orgs = response.json()
            if orgs and len(orgs) > 0:
                org_id = orgs[0].get('id')
                print(f"   ✅ Using organization: {orgs[0].get('name')} ({org_id})")
                
                # Test project creation with organization_id in body (not query)
                project_data = {
                    "name": f"API Test Project {int(time.time())}",
                    "description": "Testing project creation via API",
                    "organization_id": org_id
                }
                
                response = requests.post(f"{base_url}/api/v1/projects", json=project_data, headers=headers, timeout=10)
                if response.status_code == 201:
                    project = response.json()
                    project_id = project.get('id')
                    print(f"   ✅ Project created successfully: {project.get('name')}")
                    
                    # Test board creation
                    print("\n3️⃣ BOARD CREATION TESTING")
                    print("-" * 60)
                    
                    board_data = {
                        "name": f"API Test Board {int(time.time())}",
                        "description": "Testing board creation via API",
                        "project_id": project_id
                    }
                    
                    response = requests.post(f"{base_url}/api/v1/boards", json=board_data, headers=headers, timeout=10)
                    if response.status_code == 201:
                        board = response.json()
                        board_id = board.get('id')
                        print(f"   ✅ Board created successfully: {board.get('name')}")
                        
                        # Test boards retrieval
                        print("\n4️⃣ BOARDS RETRIEVAL TESTING")
                        print("-" * 60)
                        
                        # Test different board endpoints
                        board_endpoints = [
                            f"/api/v1/boards",
                            f"/api/v1/boards/{board_id}",
                            f"/api/v1/projects/{project_id}/boards"
                        ]
                        
                        for endpoint in board_endpoints:
                            try:
                                response = requests.get(f"{base_url}{endpoint}", headers=headers, timeout=10)
                                print(f"   📋 GET {endpoint}: {response.status_code}")
                                if response.status_code == 200:
                                    data = response.json()
                                    if isinstance(data, list):
                                        print(f"      📊 Found {len(data)} boards")
                                    elif isinstance(data, dict):
                                        print(f"      📊 Board: {data.get('name', 'Unknown')}")
                                else:
                                    try:
                                        error_data = response.json()
                                        print(f"      ❌ Error: {error_data}")
                                    except:
                                        print(f"      ❌ Raw response: {response.text}")
                            except Exception as e:
                                print(f"   ❌ Error testing {endpoint}: {e}")
                        
                        # Test column creation
                        print("\n5️⃣ COLUMN CREATION TESTING")
                        print("-" * 60)
                        
                        column_data = {
                            "name": "To Do",
                            "position": 0,
                            "board_id": board_id
                        }
                        
                        response = requests.post(f"{base_url}/api/v1/columns", json=column_data, headers=headers, timeout=10)
                        if response.status_code == 201:
                            column = response.json()
                            column_id = column.get('id')
                            print(f"   ✅ Column created successfully: {column.get('name')}")
                            
                            # Test card creation
                            print("\n6️⃣ CARD CREATION TESTING")
                            print("-" * 60)
                            
                            card_data = {
                                "title": f"API Test Card {int(time.time())}",
                                "description": "Testing card creation via API",
                                "column_id": column_id
                            }
                            
                            response = requests.post(f"{base_url}/api/v1/cards", json=card_data, headers=headers, timeout=10)
                            if response.status_code == 201:
                                card = response.json()
                                card_id = card.get('id')
                                print(f"   ✅ Card created successfully: {card.get('title')}")
                                
                                # Test checklist creation
                                print("\n7️⃣ CHECKLIST CREATION TESTING")
                                print("-" * 60)
                                
                                checklist_items = [
                                    {"title": "API Test Item 1", "completed": False, "card_id": card_id},
                                    {"title": "API Test Item 2", "completed": False, "card_id": card_id},
                                    {"title": "API Test Item 3", "completed": True, "card_id": card_id}
                                ]
                                
                                for i, item_data in enumerate(checklist_items, 1):
                                    response = requests.post(f"{base_url}/api/v1/checklist", json=item_data, headers=headers, timeout=10)
                                    if response.status_code == 201:
                                        print(f"   ✅ Checklist item {i} created successfully")
                                    else:
                                        print(f"   ❌ Checklist item {i} creation failed: {response.status_code}")
                                        try:
                                            error_data = response.json()
                                            print(f"      📋 Error: {error_data}")
                                        except:
                                            print(f"      📋 Raw response: {response.text}")
                                
                                # Test card update
                                print("\n8️⃣ CARD UPDATE TESTING")
                                print("-" * 60)
                                
                                update_data = {
                                    "title": "Updated API Test Card",
                                    "description": "Updated description via API",
                                    "status": "in_progress"
                                }
                                
                                response = requests.put(f"{base_url}/api/v1/cards/{card_id}", json=update_data, headers=headers, timeout=10)
                                if response.status_code == 200:
                                    print("   ✅ Card updated successfully")
                                else:
                                    print(f"   ❌ Card update failed: {response.status_code}")
                                    try:
                                        error_data = response.json()
                                        print(f"      📋 Error: {error_data}")
                                    except:
                                        print(f"      📋 Raw response: {response.text}")
                                
                            else:
                                print(f"   ❌ Card creation failed: {response.status_code}")
                                try:
                                    error_data = response.json()
                                    print(f"      📋 Error: {error_data}")
                                except:
                                    print(f"      📋 Raw response: {response.text}")
                        else:
                            print(f"   ❌ Column creation failed: {response.status_code}")
                            try:
                                error_data = response.json()
                                print(f"      📋 Error: {error_data}")
                            except:
                                print(f"      📋 Raw response: {response.text}")
                    else:
                        print(f"   ❌ Board creation failed: {response.status_code}")
                        try:
                            error_data = response.json()
                            print(f"      📋 Error: {error_data}")
                        except:
                            print(f"      📋 Raw response: {response.text}")
                else:
                    print(f"   ❌ Project creation failed: {response.status_code}")
                    try:
                        error_data = response.json()
                        print(f"      📋 Error: {error_data}")
                    except:
                        print(f"      📋 Raw response: {response.text}")
            else:
                print("   ❌ No organizations found")
        else:
            print(f"   ❌ Failed to get organizations: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Organization retrieval error: {e}")
    
    # Test API endpoint availability
    print("\n9️⃣ API ENDPOINT AVAILABILITY")
    print("-" * 60)
    
    endpoints_to_test = [
        ("/api/v1/", "API Root"),
        ("/api/v1/auth/me", "User Profile"),
        ("/api/v1/organizations", "Organizations"),
        ("/api/v1/projects", "Projects"),
        ("/api/v1/boards", "Boards"),
        ("/api/v1/cards", "Cards"),
        ("/api/v1/columns", "Columns"),
        ("/health", "Health Check"),
        ("/docs", "API Documentation")
    ]
    
    for endpoint, name in endpoints_to_test:
        try:
            if endpoint in ["/health", "/docs"]:
                response = requests.get(f"{base_url}{endpoint}", timeout=10)
            else:
                response = requests.get(f"{base_url}{endpoint}", headers=headers, timeout=10)
            
            if response.status_code in [200, 201]:
                print(f"   ✅ {name}: Available ({response.status_code})")
            elif response.status_code == 405:
                print(f"   ⚠️ {name}: Method not allowed ({response.status_code})")
            else:
                print(f"   ❌ {name}: Error ({response.status_code})")
        except Exception as e:
            print(f"   ❌ {name}: Connection error - {e}")
    
    print("\n" + "=" * 80)
    print("✅ API ENDPOINT VALIDATION COMPLETED")
    print("=" * 80)

if __name__ == "__main__":
    test_api_endpoints()
