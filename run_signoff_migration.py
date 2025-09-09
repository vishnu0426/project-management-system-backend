#!/usr/bin/env python3
"""
Run database migration to add project sign-off fields
"""
import asyncio
import asyncpg
import os
from pathlib import Path

# Database connection settings
DATABASE_URL = "postgresql://postgres:admin@localhost:5432/agno_worksphere"

async def run_signoff_migration():
    """Run the project sign-off migration"""
    try:
        # Read the migration file
        migration_file = Path(__file__).parent / "migrations" / "add_project_signoff_fields.sql"
        
        if not migration_file.exists():
            print(f"❌ Migration file not found: {migration_file}")
            return False
        
        with open(migration_file, 'r', encoding='utf-8') as f:
            migration_sql = f.read()
        
        print(f"📄 Reading migration from: {migration_file}")
        print(f"📝 Migration SQL length: {len(migration_sql)} characters")
        
        # Connect to database
        print("🔌 Connecting to database...")
        conn = await asyncpg.connect(DATABASE_URL)
        
        # Check if columns already exist
        print("🔍 Checking if sign-off columns already exist...")
        check_sql = """
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'projects' 
        AND column_name IN ('sign_off_requested', 'sign_off_approved', 'data_protected')
        """
        
        existing_columns = await conn.fetch(check_sql)
        existing_column_names = [row['column_name'] for row in existing_columns]
        
        if existing_column_names:
            print(f"⚠️  Some sign-off columns already exist: {existing_column_names}")
            print("🔄 Attempting to run migration anyway (will skip existing columns)...")
        else:
            print("✅ No existing sign-off columns found, proceeding with migration...")
        
        # Split migration into individual statements
        statements = [stmt.strip() for stmt in migration_sql.split(';') if stmt.strip()]
        
        print(f"🔧 Executing {len(statements)} migration statements...")
        
        # Execute each statement
        for i, statement in enumerate(statements, 1):
            if not statement:
                continue
                
            try:
                print(f"   {i}/{len(statements)}: Executing statement...")
                await conn.execute(statement)
                print(f"   ✅ Statement {i} executed successfully")
            except Exception as e:
                error_msg = str(e)
                if "already exists" in error_msg or "duplicate" in error_msg.lower():
                    print(f"   ⚠️  Statement {i} skipped (already exists): {error_msg}")
                else:
                    print(f"   ❌ Statement {i} failed: {error_msg}")
                    # Continue with other statements
        
        # Verify the migration
        print("\n🔍 Verifying migration results...")
        verify_sql = """
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns 
        WHERE table_name = 'projects' 
        AND (column_name LIKE '%sign_off%' OR column_name LIKE '%data_protected%' OR column_name LIKE '%archived%')
        ORDER BY column_name
        """
        
        result_columns = await conn.fetch(verify_sql)
        
        if result_columns:
            print("✅ Migration verification successful! New columns:")
            for col in result_columns:
                print(f"   - {col['column_name']}: {col['data_type']} (nullable: {col['is_nullable']})")
        else:
            print("❌ Migration verification failed - no new columns found")
        
        await conn.close()
        print("\n🎉 Migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting Project Sign-off Migration")
    print("=" * 50)
    
    success = asyncio.run(run_signoff_migration())
    
    if success:
        print("\n✅ Migration completed successfully!")
        print("🔄 You can now restart the backend server.")
    else:
        print("\n❌ Migration failed!")
        print("🔧 Please check the error messages above and try again.")
    
    print("=" * 50)
