#!/usr/bin/env python3
"""
Database Clear Script for Agno WorkSphere
Safely clears all data from the database while preserving the schema
"""

import asyncio
import asyncpg
import os
import sys
from datetime import datetime
from pathlib import Path

# Add the backend directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.config import settings

async def clear_all_data():
    """Clear all data from the database while preserving schema"""
    print("🧹 AGNO WORKSPHERE - DATABASE DATA CLEARING")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Parse database URL
    db_url = settings.database_url
    if not db_url:
        print("❌ DATABASE_URL not found in environment")
        return False
    
    # Extract database connection details
    try:
        # Remove the asyncpg prefix if present
        if db_url.startswith('postgresql+asyncpg://'):
            db_url = db_url.replace('postgresql+asyncpg://', 'postgresql://')
        
        # Parse URL components
        import urllib.parse
        parsed = urllib.parse.urlparse(db_url)
        
        db_config = {
            'host': parsed.hostname or 'localhost',
            'port': parsed.port or 5432,
            'user': parsed.username or 'postgres',
            'password': parsed.password or 'admin',
            'database': parsed.path.lstrip('/') or 'agno_worksphere'
        }
        
        print(f"📊 Database Configuration:")
        print(f"   Host: {db_config['host']}")
        print(f"   Port: {db_config['port']}")
        print(f"   Database: {db_config['database']}")
        print(f"   User: {db_config['user']}")
        
    except Exception as e:
        print(f"❌ Failed to parse database URL: {str(e)}")
        return False
    
    try:
        # Connect to the database
        print(f"\n🔌 Connecting to database...")
        conn = await asyncpg.connect(**db_config)
        
        # Get all table names to ensure we clear everything
        print(f"\n📋 Discovering database tables...")
        tables_result = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)
        
        all_tables = [row['table_name'] for row in tables_result]
        print(f"Found {len(all_tables)} tables: {', '.join(all_tables)}")
        
        # Define the order for clearing tables (respecting foreign key constraints)
        # Clear child tables first, then parent tables
        clear_order = [
            # AI and automation related tables
            'ai_insights',
            'ai_predictions', 
            'workflow_executions',
            'workflow_rules',
            'automation_templates',
            'custom_field_values',
            'custom_fields',
            'smart_notifications',
            'ai_generated_projects',
            'ai_models',
            
            # Notification related tables
            'notification_preferences',
            'notification_templates',
            'notifications',
            
            # Card and task related tables
            'card_assignments',
            'checklist_items',
            'cards',
            
            # Board structure tables
            'columns',
            'boards',
            
            # Project related tables
            'projects',
            
            # Organization related tables
            'invitation_tokens',
            'meeting_schedules',
            'user_organization_contexts',
            'organization_settings',
            'organization_members',
            'organizations',
            
            # User related tables
            'registrations',
            'users',
            
            # Other tables that might exist
            'comments',
            'attachments',
            'activity_logs',
            'consent_records',
            'metric_snapshots',
            'security_alerts',
            'data_exports',
            'integration_templates',
            'report_executions',
            'bulk_operation_logs',
            'integration_sync_logs',
            'bulk_user_operations',
            'performance_metrics',
            'organization_templates',
            'backup_records',
            'webhook_events'
        ]
        
        # Temporarily disable foreign key constraints
        print(f"\n🔒 Temporarily disabling foreign key constraints...")
        await conn.execute("SET session_replication_role = replica;")

        # Clear tables in the specified order
        print(f"\n🗑️  Clearing data from tables...")
        cleared_count = 0

        for table_name in clear_order:
            if table_name in all_tables:
                try:
                    # Get count before deletion
                    count_before = await conn.fetchval(f"SELECT COUNT(*) FROM {table_name}")

                    # Clear the table
                    await conn.execute(f"TRUNCATE TABLE {table_name} RESTART IDENTITY CASCADE")

                    print(f"   ✅ Cleared {table_name} ({count_before} records)")
                    cleared_count += 1

                except Exception as e:
                    # Fallback to DELETE if TRUNCATE fails
                    try:
                        await conn.execute(f"DELETE FROM {table_name}")
                        print(f"   ✅ Cleared {table_name} ({count_before} records) [fallback]")
                        cleared_count += 1
                    except Exception as e2:
                        print(f"   ⚠️  Warning: Could not clear {table_name}: {str(e2)}")

        # Clear any remaining tables not in our list
        remaining_tables = [t for t in all_tables if t not in clear_order]
        if remaining_tables:
            print(f"\n🔍 Clearing remaining tables...")
            for table_name in remaining_tables:
                try:
                    count_before = await conn.fetchval(f"SELECT COUNT(*) FROM {table_name}")
                    await conn.execute(f"TRUNCATE TABLE {table_name} RESTART IDENTITY CASCADE")
                    print(f"   ✅ Cleared {table_name} ({count_before} records)")
                    cleared_count += 1
                except Exception as e:
                    # Fallback to DELETE if TRUNCATE fails
                    try:
                        await conn.execute(f"DELETE FROM {table_name}")
                        print(f"   ✅ Cleared {table_name} ({count_before} records) [fallback]")
                        cleared_count += 1
                    except Exception as e2:
                        print(f"   ⚠️  Warning: Could not clear {table_name}: {str(e2)}")

        # Re-enable foreign key constraints
        print(f"\n🔓 Re-enabling foreign key constraints...")
        await conn.execute("SET session_replication_role = DEFAULT;")
        
        # Reset sequences if they exist
        print(f"\n🔄 Resetting sequences...")
        sequences_result = await conn.fetch("""
            SELECT sequence_name 
            FROM information_schema.sequences 
            WHERE sequence_schema = 'public'
        """)
        
        for seq_row in sequences_result:
            seq_name = seq_row['sequence_name']
            try:
                await conn.execute(f"ALTER SEQUENCE {seq_name} RESTART WITH 1")
                print(f"   ✅ Reset sequence {seq_name}")
            except Exception as e:
                print(f"   ⚠️  Warning: Could not reset sequence {seq_name}: {str(e)}")
        
        await conn.close()
        
        print(f"\n🎉 DATABASE CLEARING COMPLETED SUCCESSFULLY!")
        print(f"✅ Cleared {cleared_count} tables")
        print(f"✅ Database schema preserved")
        print(f"✅ All data removed")
        print(f"✅ Sequences reset")
        print(f"✅ Database ready for fresh data")
        
        return True
        
    except Exception as e:
        print(f"❌ Database clearing failed: {str(e)}")
        return False

async def verify_clearing():
    """Verify that all data has been cleared"""
    print(f"\n🔍 VERIFYING DATA CLEARING...")
    
    try:
        # Parse database URL
        db_url = settings.database_url
        if db_url.startswith('postgresql+asyncpg://'):
            db_url = db_url.replace('postgresql+asyncpg://', 'postgresql://')
        
        import urllib.parse
        parsed = urllib.parse.urlparse(db_url)
        
        db_config = {
            'host': parsed.hostname or 'localhost',
            'port': parsed.port or 5432,
            'user': parsed.username or 'postgres',
            'password': parsed.password or 'admin',
            'database': parsed.path.lstrip('/') or 'agno_worksphere'
        }
        
        conn = await asyncpg.connect(**db_config)
        
        # Check that tables are empty
        tables_result = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)
        
        print(f"📊 Table Status After Clearing:")
        total_records = 0
        
        for table_row in tables_result:
            table_name = table_row['table_name']
            try:
                count = await conn.fetchval(f"SELECT COUNT(*) FROM {table_name}")
                total_records += count
                if count == 0:
                    print(f"   ✅ {table_name}: empty")
                else:
                    print(f"   ⚠️  {table_name}: {count} records remaining")
            except Exception as e:
                print(f"   ❌ {table_name}: error checking ({str(e)})")
        
        await conn.close()
        
        if total_records == 0:
            print(f"✅ All tables are empty - clearing successful!")
        else:
            print(f"⚠️  {total_records} total records remaining across all tables")
        
        return total_records == 0
        
    except Exception as e:
        print(f"❌ Verification failed: {str(e)}")
        return False

async def main():
    """Main function"""
    print("🚀 Starting database data clearing...")
    
    # Ask for confirmation
    print(f"\n⚠️  WARNING: This will permanently delete ALL data from the database!")
    print(f"   Database: {settings.database_url}")
    print(f"   This action cannot be undone!")
    
    confirm = input(f"\nType 'CLEAR ALL DATA' to confirm: ")
    if confirm != 'CLEAR ALL DATA':
        print("❌ Operation cancelled - confirmation not provided")
        return
    
    # Clear all data
    clear_success = await clear_all_data()
    if not clear_success:
        print("❌ Data clearing failed. Exiting.")
        return
    
    # Verify clearing
    verify_success = await verify_clearing()
    if not verify_success:
        print("❌ Data clearing verification failed.")
        return
    
    print(f"\n🎯 DATABASE CLEARING COMPLETED!")
    print(f"✅ All data removed successfully")
    print(f"✅ Database schema intact")
    print(f"✅ Ready for fresh data")
    
    print(f"\n💡 Next Steps:")
    print(f"   • To populate demo data: python populate_demo_data.py")
    print(f"   • To reset entire database: python reset_database.py")
    print(f"   • To start fresh: python run.py")

if __name__ == "__main__":
    asyncio.run(main())
