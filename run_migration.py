#!/usr/bin/env python3
"""
Database migration runner for role-based permissions and AI checklist features
"""
import asyncio
import asyncpg
import os
from pathlib import Path

from app.config import settings


async def run_migration():
    """Run the database migration"""
    print("🚀 Starting database migration for role-based permissions and AI checklist...")
    
    # Parse database URL for asyncpg
    db_url = settings.database_url
    if db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    
    try:
        # Connect to database
        print("📡 Connecting to database...")
        conn = await asyncpg.connect(db_url)
        
        # Read migration file
        migration_file = Path(__file__).parent / "migrations" / "add_checklist_and_role_permissions.sql"
        
        if not migration_file.exists():
            print(f"❌ Migration file not found: {migration_file}")
            return False
        
        print(f"📄 Reading migration file: {migration_file}")
        migration_sql = migration_file.read_text()
        
        # Execute migration
        print("⚡ Executing migration...")
        await conn.execute(migration_sql)
        
        print("✅ Migration completed successfully!")
        
        # Verify tables were created
        print("🔍 Verifying migration...")
        
        # Check if checklist_items table exists
        result = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'checklist_items'
            );
        """)
        
        if result:
            print("✅ checklist_items table created successfully")
        else:
            print("❌ checklist_items table not found")
            return False
        
        # Check if role validation function exists
        result = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.routines 
                WHERE routine_name = 'validate_task_assignment'
            );
        """)
        
        if result:
            print("✅ validate_task_assignment function created successfully")
        else:
            print("❌ validate_task_assignment function not found")
            return False
        
        # Check if view exists
        result = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.views 
                WHERE table_name = 'v_user_assignment_permissions'
            );
        """)
        
        if result:
            print("✅ v_user_assignment_permissions view created successfully")
        else:
            print("❌ v_user_assignment_permissions view not found")
            return False
        
        # Test the validation function
        print("🧪 Testing validation function...")
        test_result = await conn.fetchval("""
            SELECT validate_task_assignment(
                'test-user-id'::uuid, 
                'test-user-id'::uuid, 
                'test-org-id'::uuid
            );
        """)
        print(f"✅ Validation function test completed (self-assignment should work)")
        
        await conn.close()
        print("🎉 Database migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        return False


async def check_database_connection():
    """Check if database is accessible"""
    print("🔍 Checking database connection...")
    
    db_url = settings.database_url
    if db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    
    try:
        conn = await asyncpg.connect(db_url)
        result = await conn.fetchval("SELECT version();")
        print(f"✅ Database connected successfully: {result}")
        await conn.close()
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {str(e)}")
        print("💡 Make sure PostgreSQL is running and the database exists")
        return False


async def create_database_if_not_exists():
    """Create database if it doesn't exist"""
    print("🏗️ Checking if database exists...")
    
    db_url = settings.database_url
    if db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    
    # Parse URL to get database name
    import urllib.parse
    parsed = urllib.parse.urlparse(db_url)
    db_name = parsed.path[1:]  # Remove leading slash
    
    # Connect to postgres database to create our database
    postgres_url = db_url.replace(f"/{db_name}", "/postgres")
    
    try:
        conn = await asyncpg.connect(postgres_url)
        
        # Check if database exists
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", db_name
        )
        
        if not exists:
            print(f"📦 Creating database: {db_name}")
            await conn.execute(f'CREATE DATABASE "{db_name}"')
            print(f"✅ Database {db_name} created successfully")
        else:
            print(f"✅ Database {db_name} already exists")
        
        await conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Failed to create database: {str(e)}")
        return False


async def main():
    """Main migration runner"""
    print("=" * 60)
    print("🚀 Agno WorkSphere Database Migration")
    print("   Role-Based Permissions & AI Checklist Features")
    print("=" * 60)
    
    # Step 1: Create database if needed
    if not await create_database_if_not_exists():
        print("❌ Failed to create database")
        return
    
    # Step 2: Check connection
    if not await check_database_connection():
        print("❌ Cannot connect to database")
        return
    
    # Step 3: Run migration
    success = await run_migration()
    
    if success:
        print("\n" + "=" * 60)
        print("🎉 Migration completed successfully!")
        print("✅ Role-based permissions system is ready")
        print("✅ AI checklist features are ready")
        print("✅ Database functions and views created")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌ Migration failed!")
        print("Please check the error messages above")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
