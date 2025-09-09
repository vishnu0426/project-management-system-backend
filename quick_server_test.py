#!/usr/bin/env python3
"""
Quick server test to debug registration issue
"""
import asyncio
import sys
import os
import time

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__)))

async def test_registration_directly():
    """Test registration directly without HTTP"""
    print("🔍 TESTING REGISTRATION DIRECTLY")
    print("=" * 50)
    
    try:
        from app.core.database import get_db
        from app.api.v1.endpoints.auth import register
        from app.schemas.auth import UserRegister
        from fastapi import BackgroundTasks
        
        # Create test data
        user_data = UserRegister(
            email=f"direct_test_{int(time.time())}@example.com",
            password="TestPassword123!",
            first_name="Direct",
            last_name="Test"
        )
        
        print(f"📝 Testing with data: {user_data.dict()}")
        
        # Create background tasks
        background_tasks = BackgroundTasks()
        
        # Get database session
        async for db in get_db():
            try:
                # Call registration function directly
                result = await register(user_data, background_tasks, db)
                print(f"✅ Registration successful!")
                print(f"📊 Result: {result}")
                
            except Exception as e:
                print(f"❌ Registration failed: {type(e).__name__}: {str(e)}")
                import traceback
                print(f"📋 Traceback:\n{traceback.format_exc()}")
                
            break
            
    except Exception as e:
        print(f"❌ Setup failed: {type(e).__name__}: {str(e)}")
        import traceback
        print(f"📋 Traceback:\n{traceback.format_exc()}")

async def main():
    """Main test execution"""
    await test_registration_directly()

if __name__ == "__main__":
    asyncio.run(main())
