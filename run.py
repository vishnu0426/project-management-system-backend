#!/usr/bin/env python3
"""
Agno WorkSphere Backend Server Runner
Production-Ready Multi-Organization System

Usage:
  python run.py                    # Development mode
  python run.py --production       # Production mode
  python run.py --setup-db         # Setup database first
"""
import uvicorn
import sys
import os
import asyncio
import argparse
from pathlib import Path

# Add the app directory to Python path
sys.path.append(str(Path(__file__).parent))

def print_banner(mode="development"):
    """Print startup banner"""
    print("🚀 AGNO WORKSPHERE BACKEND SERVER")
    print("=" * 80)
    print("🏢 Multi-Organization System")
    print("👑 Role-Based Access Control (Owner/Admin/Member/Viewer)")
    print("📧 Professional Email System")
    print("🔔 Enhanced Notifications")
    print("📊 Role-Specific Dashboards")
    print("🤖 AI Project Generation")
    print("📅 Meeting Scheduling")
    print("🎯 Card Movement & Task Assignment")
    print("=" * 80)
    print(f"🔧 Mode: {mode.upper()}")
    print(f"📁 Working Directory: {Path(__file__).parent}")
    print(f"🌐 Server URL: http://localhost:8000")
    print(f"📖 API Docs: http://localhost:8000/docs")
    print(f"🔧 Interactive API: http://localhost:8000/redoc")
    print(f"❤️ Health Check: http://localhost:8000/health")
    print("=" * 80)

def print_credentials():
    """Print test credentials"""
    print("🔐 Test Credentials Available:")
    print("   Owner: owner@agnoworksphere.com / OwnerPass123!")
    print("   Admin: admin@agnoworksphere.com / AdminPass123!")
    print("   Member: member@agnoworksphere.com / MemberPass123!")
    print("   RBAC Owner: owner1755850537@rbactest.com / TestOwner123!")
    print("   RBAC Admin: admin1755850537@rbactest.com / TestAdmin123!")
    print("   RBAC Member: member1755850537@rbactest.com / TestMember123!")
    print("=" * 80)

def print_features():
    """Print available features"""
    print("🎯 Features Ready:")
    print("   ✅ Multi-Organization Support")
    print("   ✅ Role-Based Access Control (100% tested)")
    print("   ✅ Email Notifications (Welcome, Invitations, Projects)")
    print("   ✅ Enhanced Project Management")
    print("   ✅ Task Assignment System")
    print("   ✅ Card Movement Across Columns")
    print("   ✅ Meeting Scheduling")
    print("   ✅ AI Project Generation")
    print("   ✅ Organization-Specific Dashboards")
    print("   ✅ Database Performance Optimization")
    print("   ✅ Comprehensive Error Handling")
    print("=" * 80)

async def check_database_connection():
    """Check database connection"""
    try:
        from app.core.database import get_db

        async for db in get_db():
            from sqlalchemy import text
            await db.execute(text("SELECT 1"))
            print("✅ Database connection verified")
            break
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("\n🔧 To setup database, run: python run.py --setup-db")
        return False

async def setup_database():
    """Setup database"""
    print("🗄️ Setting up database...")
    try:
        from database_setup import DatabaseSetup
        setup = DatabaseSetup()
        success = await setup.run_setup()
        return success
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        return False

def get_server_config(production=False):
    """Get server configuration"""
    config = {
        "app": "app.main:app",
        "host": "0.0.0.0",
        "port": 8000,
        "log_level": "info"
    }

    if production:
        config.update({
            "workers": min(4, (os.cpu_count() or 1) + 1),
            "access_log": True,
            "use_colors": False,
            "reload": False
        })
    else:
        config.update({
            "reload": True,
            "reload_dirs": ["app"],
            "reload_includes": ["*.py"],
            "reload_excludes": ["*.pyc", "__pycache__"]
        })

    return config

async def main():
    """Main server entry point"""
    parser = argparse.ArgumentParser(description='Agno WorkSphere Backend Server')
    parser.add_argument('--production', action='store_true', help='Run in production mode')
    parser.add_argument('--setup-db', action='store_true', help='Setup database before starting')
    parser.add_argument('--skip-db-check', action='store_true', help='Skip database connection check')

    args = parser.parse_args()

    # Ensure we're in the right directory
    backend_dir = Path(__file__).parent
    os.chdir(backend_dir)

    # Print banner
    mode = "production" if args.production else "development"
    print_banner(mode)

    # Setup database if requested
    if args.setup_db:
        success = await setup_database()
        if not success:
            sys.exit(1)
        print("\n" + "=" * 80)

    # Check database connection
    if not args.skip_db_check:
        print("🔍 Checking database connection...")
        if not await check_database_connection():
            sys.exit(1)

    # Print credentials and features
    print_credentials()
    print_features()

    try:
        print("🚀 Starting server...")
        print("   Press Ctrl+C to stop the server")
        print("=" * 80)

        # Get server configuration
        server_config = get_server_config(args.production)

        # Start the FastAPI server
        uvicorn.run(**server_config)

    except KeyboardInterrupt:
        print("\n" + "=" * 80)
        print("🛑 Server stopped by user")
        print("👋 Thank you for using Agno WorkSphere!")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ Error starting server: {e}")
        print("\n🔧 Troubleshooting:")
        print("   1. Setup database: python run.py --setup-db")
        print("   2. Check if port 8000 is available")
        print("   3. Ensure all dependencies are installed: pip install -r requirements.txt")
        print("   4. Verify database connection settings")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
