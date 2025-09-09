#!/usr/bin/env python3
"""
Complete Database Clear Script
=============================

This script clears ALL data from both databases used by the application:
- agno_worksphere (main database)
- test_agnoworksphere (test database used by consolidated_server.py)

Usage:
    python clear_all_data.py

This will:
1. Clear all data from both databases
2. Reset auto-increment sequences
3. Provide a clean slate for development
"""

import asyncio
import asyncpg
import sys

async def clear_database(db_name, db_url):
    """Clear all data from a specific database"""
    print(f"\n🗑️  Clearing {db_name} database...")
    print("=" * 50)
    
    try:
        conn = await asyncpg.connect(db_url)
        
        # Get all tables
        tables = await conn.fetch('''
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        ''')
        
        if not tables:
            print(f"No tables found in {db_name}")
            await conn.close()
            return
        
        print(f"Found {len(tables)} tables")
        
        # Clear all tables
        total_records_cleared = 0
        for table in tables:
            table_name = table['table_name']
            try:
                count_before = await conn.fetchval(f'SELECT COUNT(*) FROM {table_name}')
                if count_before > 0:
                    await conn.execute(f'TRUNCATE TABLE {table_name} CASCADE')
                    print(f"  ✅ Cleared {table_name} ({count_before} records)")
                    total_records_cleared += count_before
                else:
                    print(f"  ⚪ {table_name} (already empty)")
            except Exception as e:
                print(f"  ❌ Error clearing {table_name}: {e}")
        
        # Reset sequences
        sequences = await conn.fetch('''
            SELECT sequence_name 
            FROM information_schema.sequences 
            WHERE sequence_schema = 'public'
        ''')
        
        for seq in sequences:
            seq_name = seq['sequence_name']
            try:
                await conn.execute(f'ALTER SEQUENCE {seq_name} RESTART WITH 1')
                print(f"  🔄 Reset sequence {seq_name}")
            except Exception as e:
                print(f"  ❌ Error resetting sequence {seq_name}: {e}")
        
        print(f"\n✅ {db_name} cleared successfully!")
        print(f"   Total records cleared: {total_records_cleared}")
        await conn.close()
        
    except Exception as e:
        print(f"❌ Error clearing {db_name}: {e}")
        return False
    
    return True

async def main():
    """Main function to clear all databases"""
    print("🚀 Complete Database Clear Script")
    print("=" * 50)
    print("This will clear ALL data from both databases!")
    print("⚠️  This action cannot be undone!")
    print("=" * 50)
    
    # Ask for confirmation
    response = input("Are you sure you want to proceed? (yes/no): ").lower().strip()
    if response not in ['yes', 'y']:
        print("❌ Operation cancelled")
        return
    
    databases = [
        ('agno_worksphere', 'postgresql://postgres:admin@localhost:5432/agno_worksphere'),
        ('test_agnoworksphere', 'postgresql://postgres:admin@localhost:5432/test_agnoworksphere')
    ]
    
    success_count = 0
    for db_name, db_url in databases:
        if await clear_database(db_name, db_url):
            success_count += 1
    
    print("\n" + "=" * 50)
    if success_count == len(databases):
        print("🎉 All databases cleared successfully!")
        print("\n📝 Next steps:")
        print("1. Restart the backend server to reinitialize with fresh demo data")
        print("2. Clear your browser cache or hard refresh (Ctrl+F5)")
        print("3. The application will start with clean demo data")
    else:
        print(f"⚠️  {success_count}/{len(databases)} databases cleared successfully")
        print("Some databases may still contain data")
    
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(main())
