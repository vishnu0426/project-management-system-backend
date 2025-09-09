#!/usr/bin/env python3
"""
Check and fix migration status
"""
import asyncio
import asyncpg

async def check_migration_status():
    """Check current migration status"""
    try:
        conn = await asyncpg.connect('postgresql://postgres:admin@localhost:5432/agno_worksphere_test')
        
        # Check current alembic version
        result = await conn.fetch('SELECT * FROM alembic_version')
        print(f"Current alembic version: {result}")
        
        # Check if organizations table has contact_email column
        result = await conn.fetch("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'organizations' 
            AND column_name = 'contact_email'
        """)
        
        if result:
            print("✅ contact_email column already exists in organizations table")
            
            # Mark migration as applied
            await conn.execute("""
                UPDATE alembic_version 
                SET version_num = 'add_org_contact_fields'
                WHERE version_num IS NOT NULL
            """)
            print("✅ Migration marked as applied")
        else:
            print("❌ contact_email column does not exist")
        
        await conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_migration_status())
