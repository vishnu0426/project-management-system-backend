#!/usr/bin/env python3
"""
PostgreSQL Database Setup Script
Automatically sets up PostgreSQL database for Agno WorkSphere
"""
import asyncio
import asyncpg
import sys
import os
from pathlib import Path

# Add app to path
sys.path.append(str(Path(__file__).parent))

async def setup_postgresql_database():
    """Setup PostgreSQL database"""
    print("🐘 POSTGRESQL DATABASE SETUP")
    print("=" * 50)
    
    # Database configuration
    DB_HOST = "localhost"
    DB_PORT = 5432
    DB_USER = "postgres"
    DB_PASSWORD = "admin"
    DB_NAME = "agno_worksphere"
    
    try:
        # Connect to PostgreSQL server (not specific database)
        print(f"🔌 Connecting to PostgreSQL server at {DB_HOST}:{DB_PORT}...")
        conn = await asyncpg.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database="postgres"  # Connect to default postgres database
        )
        
        print("✅ Connected to PostgreSQL server")
        
        # Check if database exists
        db_exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", DB_NAME
        )
        
        if db_exists:
            print(f"✅ Database '{DB_NAME}' already exists")
        else:
            # Create database
            print(f"🔨 Creating database '{DB_NAME}'...")
            await conn.execute(f'CREATE DATABASE "{DB_NAME}"')
            print(f"✅ Database '{DB_NAME}' created successfully")
        
        await conn.close()
        
        # Test connection to the new database
        print(f"🔍 Testing connection to '{DB_NAME}'...")
        test_conn = await asyncpg.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        
        # Test basic query
        result = await test_conn.fetchval("SELECT 1")
        if result == 1:
            print("✅ Database connection test successful")
        
        await test_conn.close()
        
        print("\n🎉 PostgreSQL setup completed successfully!")
        print(f"📊 Database URL: postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")
        
        return True
        
    except asyncpg.exceptions.InvalidPasswordError:
        print("❌ Invalid PostgreSQL password")
        print("🔧 Please check your PostgreSQL password")
        return False
        
    except asyncpg.exceptions.ConnectionDoesNotExistError:
        print("❌ Cannot connect to PostgreSQL server")
        print("🔧 Please ensure PostgreSQL is running")
        print("   - Windows: Check PostgreSQL service in Services")
        print("   - macOS: brew services start postgresql")
        print("   - Linux: sudo systemctl start postgresql")
        return False
        
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        print("\n🔧 Troubleshooting:")
        print("1. Ensure PostgreSQL is installed and running")
        print("2. Check if the credentials are correct:")
        print(f"   - Host: {DB_HOST}")
        print(f"   - Port: {DB_PORT}")
        print(f"   - User: {DB_USER}")
        print(f"   - Password: {DB_PASSWORD}")
        print("3. Ensure the PostgreSQL user has database creation privileges")
        return False

async def main():
    """Main setup function"""
    success = await setup_postgresql_database()
    
    if success:
        print("\n✅ Ready to start the backend server!")
        print("   Run: python run.py")
    else:
        print("\n❌ Database setup failed")
        print("   Please fix the issues above and try again")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
