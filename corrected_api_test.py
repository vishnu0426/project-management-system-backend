#!/usr/bin/env python3
"""
Corrected API Test - Using Proper Endpoint Parameters
"""
import requests
import time
import json

base_url = "http://127.0.0.1:8000"

def test_corrected_api_flow():
    """Test API flow with correct parameter usage"""
    print("🔧 CORRECTED API FLOW TESTING")
    print("=" * 80)
    
    # Authentication
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
    
    # Get organization
    print("\n2️⃣ GET ORGANIZATION")
    print("-" * 60)
    
    try:
        response = requests.get(f"{base_url}/api/v1/organizations", headers=headers, timeout=10)
        if response.status_code == 200:
            orgs = response.json()
            if orgs and len(orgs) > 0:
                org_id = orgs[0].get('id')
                org_name = orgs[0].get('name')
                print(f"   ✅ Using organization: {org_name} ({org_id})")
            else:
                print("   ❌ No organizations found")
                return
        else:
            print(f"   ❌ Failed to get organizations: {response.status_code}")
            return
    except Exception as e:
        print(f"   ❌ Organization retrieval error: {e}")
        return
    
    # Test project creation with organization_id as query parameter
    print("\n3️⃣ PROJECT CREATION (Query Parameter)")
    print("-" * 60)
    
    project_data = {
        "name": f"Corrected API Test Project {int(time.time())}",
        "description": "Testing project creation with correct parameters",
        "status": "active",
        "priority": "medium"
    }
    
    try:
        # Try with organization_id as query parameter
        response = requests.post(
            f"{base_url}/api/v1/projects?organization_id={org_id}", 
            json=project_data, 
            headers=headers, 
            timeout=10
        )
        if response.status_code in [200, 201]:
            project = response.json()
            project_id = project.get('id')
            print(f"   ✅ Project created successfully: {project.get('name')}")
            print(f"      📊 Project ID: {project_id}")
        else:
            print(f"   ❌ Project creation failed: {response.status_code}")
            try:
                error_data = response.json()
                print(f"      📋 Error: {error_data}")
            except:
                print(f"      📋 Raw response: {response.text}")
            
            # Try alternative endpoint
            print("\n   🔄 Trying alternative endpoint...")
            try:
                response = requests.post(
                    f"{base_url}/api/v1/projects/organization/{org_id}", 
                    json=project_data, 
                    headers=headers, 
                    timeout=10
                )
                if response.status_code == 201:
                    project = response.json()
                    project_id = project.get('id')
                    print(f"   ✅ Project created via alternative endpoint: {project.get('name')}")
                    print(f"      📊 Project ID: {project_id}")
                else:
                    print(f"   ❌ Alternative endpoint also failed: {response.status_code}")
                    try:
                        error_data = response.json()
                        print(f"      📋 Error: {error_data}")
                    except:
                        print(f"      📋 Raw response: {response.text}")
                    return
            except Exception as e:
                print(f"   ❌ Alternative endpoint error: {e}")
                return
    except Exception as e:
        print(f"   ❌ Project creation error: {e}")
        return
    
    # Test board creation
    print("\n4️⃣ BOARD CREATION")
    print("-" * 60)
    
    board_data = {
        "name": f"Corrected API Test Board {int(time.time())}",
        "description": "Testing board creation with correct parameters",
        "project_id": project_id
    }
    
    try:
        response = requests.post(f"{base_url}/api/v1/boards", json=board_data, headers=headers, timeout=10)
        if response.status_code in [200, 201]:
            board = response.json()
            board_id = board.get('id')
            print(f"   ✅ Board created successfully: {board.get('name')}")
            print(f"      📊 Board ID: {board_id}")
        else:
            print(f"   ❌ Board creation failed: {response.status_code}")
            try:
                error_data = response.json()
                print(f"      📋 Error: {error_data}")
            except:
                print(f"      📋 Raw response: {response.text}")
            return
    except Exception as e:
        print(f"   ❌ Board creation error: {e}")
        return
    
    # Test board retrieval methods
    print("\n5️⃣ BOARD RETRIEVAL METHODS")
    print("-" * 60)
    
    # Method 1: Get specific board
    try:
        response = requests.get(f"{base_url}/api/v1/boards/{board_id}", headers=headers, timeout=10)
        print(f"   📋 GET /api/v1/boards/{board_id}: {response.status_code}")
        if response.status_code == 200:
            board_data = response.json()
            print(f"      ✅ Retrieved board: {board_data.get('name')}")
        else:
            try:
                error_data = response.json()
                print(f"      ❌ Error: {error_data}")
            except:
                print(f"      ❌ Raw response: {response.text}")
    except Exception as e:
        print(f"   ❌ Board retrieval error: {e}")
    
    # Method 2: Get boards via project
    try:
        response = requests.get(f"{base_url}/api/v1/projects/{project_id}/boards", headers=headers, timeout=10)
        print(f"   📋 GET /api/v1/projects/{project_id}/boards: {response.status_code}")
        if response.status_code == 200:
            boards = response.json()
            print(f"      ✅ Retrieved {len(boards)} boards via project")
        else:
            try:
                error_data = response.json()
                print(f"      ❌ Error: {error_data}")
            except:
                print(f"      ❌ Raw response: {response.text}")
    except Exception as e:
        print(f"   ❌ Project boards retrieval error: {e}")
    
    # Test column creation
    print("\n6️⃣ COLUMN CREATION")
    print("-" * 60)
    
    columns_to_create = [
        {"name": "To Do", "position": 0},
        {"name": "In Progress", "position": 1},
        {"name": "Done", "position": 2}
    ]
    
    created_columns = []
    for col_data in columns_to_create:
        col_data['board_id'] = board_id
        
        try:
            response = requests.post(f"{base_url}/api/v1/columns", json=col_data, headers=headers, timeout=10)
            if response.status_code in [200, 201]:
                column = response.json()
                created_columns.append(column)
                print(f"   ✅ Column created: {column.get('name')} (ID: {column.get('id')})")
            else:
                print(f"   ❌ Column creation failed: {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"      📋 Error: {error_data}")
                except:
                    print(f"      📋 Raw response: {response.text}")
        except Exception as e:
            print(f"   ❌ Column creation error: {e}")
    
    # Test card creation
    print("\n7️⃣ CARD CREATION")
    print("-" * 60)
    
    if created_columns:
        column_id = created_columns[0].get('id')  # Use first column
        
        cards_to_create = [
            {
                "title": "First Test Card",
                "description": "Testing card creation",
                "priority": "high"
            },
            {
                "title": "Second Test Card", 
                "description": "Another test card",
                "priority": "medium"
            }
        ]
        
        created_cards = []
        for card_data in cards_to_create:
            card_data['column_id'] = column_id
            
            try:
                response = requests.post(f"{base_url}/api/v1/cards", json=card_data, headers=headers, timeout=10)
                if response.status_code in [200, 201]:
                    card = response.json()
                    created_cards.append(card)
                    print(f"   ✅ Card created: {card.get('title')} (ID: {card.get('id')})")
                else:
                    print(f"   ❌ Card creation failed: {response.status_code}")
                    try:
                        error_data = response.json()
                        print(f"      📋 Error: {error_data}")
                    except:
                        print(f"      📋 Raw response: {response.text}")
            except Exception as e:
                print(f"   ❌ Card creation error: {e}")
        
        # Test checklist creation
        print("\n8️⃣ CHECKLIST CREATION")
        print("-" * 60)
        
        if created_cards:
            card_id = created_cards[0].get('id')  # Use first card
            
            checklist_items = [
                {"title": "Complete task analysis", "completed": False},
                {"title": "Review requirements", "completed": True},
                {"title": "Implement solution", "completed": False}
            ]
            
            for i, item_data in enumerate(checklist_items, 1):
                item_data['card_id'] = card_id
                
                try:
                    response = requests.post(f"{base_url}/api/v1/checklist", json=item_data, headers=headers, timeout=10)
                    if response.status_code in [200, 201]:
                        print(f"   ✅ Checklist item {i} created: {item_data['title']}")
                    else:
                        print(f"   ❌ Checklist item {i} creation failed: {response.status_code}")
                        try:
                            error_data = response.json()
                            print(f"      📋 Error: {error_data}")
                        except:
                            print(f"      📋 Raw response: {response.text}")
                except Exception as e:
                    print(f"   ❌ Checklist item {i} creation error: {e}")
    
    # Final verification
    print("\n9️⃣ FINAL VERIFICATION")
    print("-" * 60)
    
    # Verify data persistence
    verification_endpoints = [
        (f"/api/v1/projects/{project_id}", "Project"),
        (f"/api/v1/boards/{board_id}", "Board"),
        (f"/api/v1/projects/{project_id}/boards", "Project Boards")
    ]
    
    for endpoint, name in verification_endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", headers=headers, timeout=10)
            if response.status_code == 200:
                print(f"   ✅ {name} verification: Success")
            else:
                print(f"   ❌ {name} verification: Failed ({response.status_code})")
        except Exception as e:
            print(f"   ❌ {name} verification error: {e}")
    
    print("\n" + "=" * 80)
    print("✅ CORRECTED API FLOW TESTING COMPLETED")
    print("=" * 80)

if __name__ == "__main__":
    test_corrected_api_flow()
