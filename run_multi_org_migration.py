#!/usr/bin/env python3
"""
Run Multi-Organization Migration
Apply the multi-organization database schema changes
"""
import asyncio
import asyncpg
from pathlib import Path
from app.config import settings


async def run_migration():
    """Run the multi-organization migration"""
    print("🚀 Starting multi-organization migration...")
    
    # Parse database URL for asyncpg
    db_url = settings.database_url
    if db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    
    try:
        # Connect to database
        print("📡 Connecting to database...")
        conn = await asyncpg.connect(db_url)
        
        # Read migration file
        migration_file = Path(__file__).parent / "migrations" / "add_multi_organization_features.sql"
        
        if not migration_file.exists():
            print(f"❌ Migration file not found: {migration_file}")
            return False
        
        print(f"📄 Reading migration file: {migration_file}")
        migration_sql = migration_file.read_text()
        
        # Execute migration
        print("⚡ Executing migration...")
        await conn.execute(migration_sql)
        
        print("✅ Multi-organization migration completed successfully!")
        
        # Verify tables were created
        print("🔍 Verifying created tables...")
        tables_result = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN (
                'organization_settings', 
                'user_organization_contexts', 
                'invitation_tokens', 
                'meeting_schedules'
            )
            ORDER BY table_name;
        """)
        
        created_tables = [row['table_name'] for row in tables_result]
        print(f"📊 Created tables: {created_tables}")
        
        # Check if default data was inserted
        org_settings_count = await conn.fetchval(
            "SELECT COUNT(*) FROM organization_settings"
        )
        
        user_contexts_count = await conn.fetchval(
            "SELECT COUNT(*) FROM user_organization_contexts"
        )
        
        print(f"📈 Organization settings created: {org_settings_count}")
        print(f"📈 User contexts created: {user_contexts_count}")
        
        # Verify indexes were created
        indexes_result = await conn.fetch("""
            SELECT indexname 
            FROM pg_indexes 
            WHERE schemaname = 'public' 
            AND indexname LIKE 'idx_%organization%'
            OR indexname LIKE 'idx_%meeting%'
            OR indexname LIKE 'idx_%invitation%'
            ORDER BY indexname;
        """)
        
        created_indexes = [row['indexname'] for row in indexes_result]
        print(f"🔍 Created indexes: {created_indexes}")
        
        print("🎉 Multi-organization migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        await conn.close()


if __name__ == "__main__":
    success = asyncio.run(run_migration())
    if success:
        print("✅ All done! Multi-organization features are now available.")
    else:
        print("❌ Migration failed. Please check the errors above.")
        exit(1)
