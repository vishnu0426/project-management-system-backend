#!/usr/bin/env python3
"""
Debug User Registration 500 Error
Analyze and fix the registration endpoint issues
"""
import asyncio
import sys
import os
import requests
import time
import traceback

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__)))

async def debug_registration_error():
    """Debug the user registration 500 error"""
    print("🔍 DEBUGGING USER REGISTRATION 500 ERROR")
    print("=" * 60)
    
    base_url = "http://localhost:8000"
    
    # Test registration with various scenarios
    test_cases = [
        {
            "name": "Valid Registration",
            "data": {
                "email": f"test_reg_{int(time.time())}@example.com",
                "password": "TestPassword123!",
                "first_name": "Test",
                "last_name": "User"
            }
        },
        {
            "name": "Minimal Registration",
            "data": {
                "email": f"minimal_{int(time.time())}@example.com",
                "password": "MinimalPass123!"
            }
        },
        {
            "name": "Registration with Organization",
            "data": {
                "email": f"org_test_{int(time.time())}@example.com",
                "password": "OrgTest123!",
                "first_name": "Org",
                "last_name": "Test",
                "organization_name": "Test Organization"
            }
        }
    ]
    
    for test_case in test_cases:
        print(f"\n📝 Testing: {test_case['name']}")
        print("-" * 40)
        
        try:
            response = requests.post(
                f"{base_url}/api/v1/auth/register",
                json=test_case['data'],
                timeout=10
            )
            
            print(f"Status Code: {response.status_code}")
            print(f"Response Headers: {dict(response.headers)}")
            
            if response.status_code == 500:
                print("❌ 500 Internal Server Error")
                try:
                    error_data = response.json()
                    print(f"Error Response: {error_data}")
                except:
                    print(f"Raw Response: {response.text}")
            elif response.status_code == 201:
                print("✅ Registration successful")
                try:
                    success_data = response.json()
                    print(f"Success Response: {success_data}")
                except:
                    print(f"Raw Response: {response.text}")
            else:
                print(f"⚠️ Unexpected status code: {response.status_code}")
                try:
                    response_data = response.json()
                    print(f"Response: {response_data}")
                except:
                    print(f"Raw Response: {response.text}")
                    
        except Exception as e:
            print(f"❌ Request failed: {e}")
            traceback.print_exc()
    
    # Check server logs by examining the database state
    print(f"\n💾 CHECKING DATABASE STATE")
    print("=" * 60)
    
    try:
        from app.core.database import get_db
        from app.models.user import User
        from app.models.organization import Organization
        from sqlalchemy import select, func, text
        
        async for db in get_db():
            try:
                # Check recent users
                recent_users_query = select(User).order_by(User.created_at.desc()).limit(5)
                result = await db.execute(recent_users_query)
                recent_users = result.scalars().all()
                
                print(f"📊 Recent users in database:")
                for user in recent_users:
                    print(f"   👤 {user.email} (created: {user.created_at})")
                
                # Check database constraints
                print(f"\n🔍 Checking database constraints:")
                
                # Check if email constraint exists
                email_constraint_query = text("""
                    SELECT constraint_name, constraint_type 
                    FROM information_schema.table_constraints 
                    WHERE table_name = 'users' AND constraint_type = 'UNIQUE'
                """)
                
                result = await db.execute(email_constraint_query)
                constraints = result.fetchall()
                
                print(f"   📋 Unique constraints on users table:")
                for constraint in constraints:
                    print(f"      🔒 {constraint[0]} ({constraint[1]})")
                
                # Check if there are any database errors
                try:
                    user_count = await db.scalar(select(func.count(User.id)))
                    org_count = await db.scalar(select(func.count(Organization.id)))
                    print(f"   📊 Total users: {user_count}")
                    print(f"   📊 Total organizations: {org_count}")
                except Exception as db_error:
                    print(f"   ❌ Database query error: {db_error}")
                
            except Exception as e:
                print(f"❌ Database check failed: {e}")
                await db.rollback()
            
            break
            
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        traceback.print_exc()
    
    # Test the registration endpoint schema
    print(f"\n📋 TESTING ENDPOINT SCHEMA")
    print("=" * 60)
    
    try:
        # Test with invalid data to see validation errors
        invalid_test_cases = [
            {
                "name": "Missing Email",
                "data": {
                    "password": "TestPassword123!",
                    "first_name": "Test"
                }
            },
            {
                "name": "Invalid Email",
                "data": {
                    "email": "invalid-email",
                    "password": "TestPassword123!"
                }
            },
            {
                "name": "Weak Password",
                "data": {
                    "email": f"weak_pass_{int(time.time())}@example.com",
                    "password": "123"
                }
            }
        ]
        
        for test_case in invalid_test_cases:
            print(f"\n📝 Testing: {test_case['name']}")
            try:
                response = requests.post(
                    f"{base_url}/api/v1/auth/register",
                    json=test_case['data'],
                    timeout=10
                )
                
                print(f"Status Code: {response.status_code}")
                if response.status_code == 422:
                    print("✅ Validation working correctly")
                    try:
                        validation_errors = response.json()
                        print(f"Validation Errors: {validation_errors}")
                    except:
                        print(f"Raw Response: {response.text}")
                else:
                    print(f"Response: {response.text}")
                    
            except Exception as e:
                print(f"❌ Request failed: {e}")
    
    except Exception as e:
        print(f"❌ Schema testing failed: {e}")
        traceback.print_exc()

async def main():
    """Main debug execution"""
    try:
        await debug_registration_error()
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
