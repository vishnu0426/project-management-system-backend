#!/usr/bin/env python3
"""
Debug performance issues by testing database operations directly
"""
import asyncio
import time
import sys
import os

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__)))

async def test_database_performance():
    """Test database operations directly"""
    print("🔍 DEBUGGING DATABASE PERFORMANCE")
    print("=" * 50)
    
    try:
        from app.core.database import get_db
        from app.models.user import User
        from app.models.organization import Organization, OrganizationMember
        from sqlalchemy import select, text
        
        async for db in get_db():
            try:
                # Test 1: Simple query
                print("📊 Test 1: Simple user query")
                start_time = time.time()
                result = await db.execute(select(User).limit(1))
                user = result.scalar_one_or_none()
                end_time = time.time()
                print(f"   ⏱️ Time: {(end_time - start_time) * 1000:.1f}ms")
                print(f"   📊 Result: {user.email if user else 'No users found'}")
                
                # Test 2: Join query (similar to organizations endpoint)
                print("\n📊 Test 2: Organization join query")
                start_time = time.time()
                result = await db.execute(
                    select(Organization, OrganizationMember.role)
                    .join(OrganizationMember, Organization.id == OrganizationMember.organization_id)
                    .limit(5)
                )
                orgs = result.all()
                end_time = time.time()
                print(f"   ⏱️ Time: {(end_time - start_time) * 1000:.1f}ms")
                print(f"   📊 Result: {len(orgs)} organizations found")
                
                # Test 3: Raw SQL query
                print("\n📊 Test 3: Raw SQL query")
                start_time = time.time()
                result = await db.execute(text("SELECT COUNT(*) FROM users"))
                count = result.scalar()
                end_time = time.time()
                print(f"   ⏱️ Time: {(end_time - start_time) * 1000:.1f}ms")
                print(f"   📊 Result: {count} users total")
                
                # Test 4: Connection test
                print("\n📊 Test 4: Database connection test")
                start_time = time.time()
                result = await db.execute(text("SELECT 1"))
                value = result.scalar()
                end_time = time.time()
                print(f"   ⏱️ Time: {(end_time - start_time) * 1000:.1f}ms")
                print(f"   📊 Result: {value}")
                
                # Test 5: Multiple small queries (N+1 simulation)
                print("\n📊 Test 5: Multiple small queries")
                start_time = time.time()
                for i in range(5):
                    result = await db.execute(text("SELECT 1"))
                    result.scalar()
                end_time = time.time()
                print(f"   ⏱️ Time: {(end_time - start_time) * 1000:.1f}ms for 5 queries")
                print(f"   📊 Average per query: {((end_time - start_time) * 1000) / 5:.1f}ms")
                
            except Exception as e:
                print(f"❌ Database test failed: {e}")
                import traceback
                traceback.print_exc()
            
            break
            
    except Exception as e:
        print(f"❌ Failed to test database: {e}")
        import traceback
        traceback.print_exc()

async def test_auth_dependency():
    """Test the authentication dependency performance"""
    print("\n🔍 TESTING AUTH DEPENDENCY PERFORMANCE")
    print("=" * 50)
    
    try:
        from app.core.deps import get_current_active_user
        from app.core.database import get_db
        from app.services.session_service import SessionService
        
        # Test session lookup performance
        async for db in get_db():
            try:
                session_service = SessionService(db)
                
                # Test session validation
                print("📊 Testing session validation")
                start_time = time.time()
                
                # Get a valid session token from database
                from sqlalchemy import select
                from app.models.session import UserSession
                result = await db.execute(
                    select(UserSession).where(UserSession.is_active == True).limit(1)
                )
                session = result.scalar_one_or_none()
                
                if session:
                    # Test session validation performance
                    start_time = time.time()
                    user = await session_service.get_user_from_session(session.session_token)
                    end_time = time.time()
                    print(f"   ⏱️ Session validation time: {(end_time - start_time) * 1000:.1f}ms")
                    print(f"   📊 User: {user.email if user else 'No user found'}")
                else:
                    print("   ❌ No active sessions found")
                
            except Exception as e:
                print(f"❌ Auth test failed: {e}")
                import traceback
                traceback.print_exc()
            
            break
            
    except Exception as e:
        print(f"❌ Failed to test auth: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Main test execution"""
    await test_database_performance()
    await test_auth_dependency()

if __name__ == "__main__":
    asyncio.run(main())
