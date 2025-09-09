#!/usr/bin/env python3
"""
Comprehensive test suite for all fixes
"""
import sys
import os
import asyncio

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__)))

def test_app_structure():
    """Test that the app structure is correct"""
    print("🔍 Testing App Structure...")
    
    try:
        from app.main import app
        
        # Count routes
        routes = [route.path for route in app.routes if hasattr(route, 'path')]
        print(f"   ✅ Found {len(routes)} routes")
        
        # Check key routes exist
        key_routes = [
            "/api/v1/auth/register",
            "/api/v1/auth/login", 
            "/api/v1/auth/me",
            "/api/v1/auth/logout",
            "/api/v1/boards",
            "/api/v1/boards/{board_id}",
            "/api/v1/projects/{project_id}/boards",
            "/api/v1/columns",
            "/api/v1/columns/{column_id}",
            "/api/v1/cards",
            "/api/v1/cards/{card_id}",
            "/api/v1/organizations-enhanced/{organization_id}/settings"
        ]
        
        missing_routes = []
        for route in key_routes:
            # Check if route pattern exists (simplified check)
            route_base = route.split('{')[0].rstrip('/')
            found = any(r.startswith(route_base) for r in routes)
            if found:
                print(f"   ✅ {route}")
            else:
                print(f"   ❌ {route}")
                missing_routes.append(route)
        
        if not missing_routes:
            print("   ✅ All key routes found")
            return True
        else:
            print(f"   ❌ Missing routes: {missing_routes}")
            return False
            
    except Exception as e:
        print(f"   ❌ App structure test failed: {e}")
        return False

def test_database_config():
    """Test database configuration"""
    print("\n🔍 Testing Database Configuration...")
    
    try:
        from app.config import settings
        from app.core.database import engine
        
        print(f"   ✅ Database URL: {settings.database_url}")
        print(f"   ✅ Database engine created")
        
        # Check if SQLite file exists
        if "sqlite" in settings.database_url:
            db_file = settings.database_url.split("///")[-1]
            if os.path.exists(db_file):
                print(f"   ✅ SQLite database file exists: {db_file}")
            else:
                print(f"   ❌ SQLite database file missing: {db_file}")
                return False
        
        return True
        
    except Exception as e:
        print(f"   ❌ Database config test failed: {e}")
        return False

def test_email_service():
    """Test email service configuration"""
    print("\n🔍 Testing Email Service...")
    
    try:
        from app.services.email_service import EmailService
        from app.config import settings
        
        email_service = EmailService()
        
        print(f"   ✅ SMTP Host: {settings.smtp_host}")
        print(f"   ✅ SMTP User: {settings.smtp_user}")
        print(f"   ✅ Email service initialized")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Email service test failed: {e}")
        return False

def test_model_fixes():
    """Test model fixes (metadata -> item_metadata)"""
    print("\n🔍 Testing Model Fixes...")
    
    try:
        from app.models.card import ChecklistItem
        
        # Check if ChecklistItem has item_metadata field
        if hasattr(ChecklistItem, 'item_metadata'):
            print("   ✅ ChecklistItem.item_metadata field exists")
        else:
            print("   ❌ ChecklistItem.item_metadata field missing")
            return False
        
        # Check if old metadata field is gone
        if hasattr(ChecklistItem, 'metadata'):
            print("   ❌ Old ChecklistItem.metadata field still exists")
            return False
        else:
            print("   ✅ Old ChecklistItem.metadata field removed")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Model fixes test failed: {e}")
        return False

def test_frontend_config():
    """Test frontend configuration files"""
    print("\n🔍 Testing Frontend Configuration...")
    
    try:
        # Check API service files
        api_files = [
            "agnoworksphere/agnoworksphere/src/utils/realApiService.js",
            "agnoworksphere/agnoworksphere/src/utils/kanbanApiService.js", 
            "agnoworksphere/agnoworksphere/src/utils/sessionService.js",
            "agnoworksphere/agnoworksphere/src/utils/organizationSettings.js",
            "agnoworksphere/agnoworksphere/.env.example"
        ]
        
        all_good = True
        for file_path in api_files:
            full_path = os.path.join("..", "..", file_path)
            if os.path.exists(full_path):
                with open(full_path, 'r') as f:
                    content = f.read()
                    if "localhost:8000" in content:
                        print(f"   ✅ {file_path} - port 8000 configured")
                    else:
                        print(f"   ❌ {file_path} - port 8000 not found")
                        all_good = False
            else:
                print(f"   ❌ {file_path} - file not found")
                all_good = False
        
        return all_good
        
    except Exception as e:
        print(f"   ❌ Frontend config test failed: {e}")
        return False

async def main():
    """Run all tests"""
    print("🚀 Comprehensive Test Suite")
    print("=" * 60)
    
    tests = [
        ("App Structure", test_app_structure),
        ("Database Config", test_database_config), 
        ("Email Service", test_email_service),
        ("Model Fixes", test_model_fixes),
        ("Frontend Config", test_frontend_config)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"   ❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 60)
    print("📊 Test Results Summary:")
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status} - {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Overall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All tests passed! The fixes are working correctly.")
    else:
        print("⚠️  Some tests failed. Review the issues above.")

if __name__ == "__main__":
    asyncio.run(main())
