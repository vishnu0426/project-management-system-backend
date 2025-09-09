#!/usr/bin/env python3
"""
Database Tables Inspection Tool
"""
import asyncio
import sys
import os
from sqlalchemy import text, inspect

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__)))

async def check_database_tables():
    """Check all database tables and their structure"""
    print("🔍 DATABASE TABLES INSPECTION")
    print("=" * 80)
    
    try:
        from app.core.database import get_db
        
        async for db in get_db():
            try:
                # Get all table names
                result = await db.execute(text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    ORDER BY table_name;
                """))
                
                tables = [row[0] for row in result.fetchall()]
                
                print(f"📊 Found {len(tables)} tables in the database:")
                print("-" * 80)
                
                for i, table_name in enumerate(tables, 1):
                    print(f"{i:2d}. {table_name}")
                
                print("\n" + "=" * 80)
                print("📋 DETAILED TABLE ANALYSIS")
                print("=" * 80)
                
                # Analyze each table
                for table_name in tables:
                    await analyze_table(db, table_name)
                
                # Check indexes
                print("\n" + "=" * 80)
                print("📊 DATABASE INDEXES")
                print("=" * 80)
                await check_indexes(db)
                
                # Check constraints
                print("\n" + "=" * 80)
                print("🔗 FOREIGN KEY CONSTRAINTS")
                print("=" * 80)
                await check_constraints(db)
                
            except Exception as e:
                print(f"❌ Database inspection failed: {e}")
                import traceback
                traceback.print_exc()
            
            break
            
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        import traceback
        traceback.print_exc()

async def analyze_table(db, table_name):
    """Analyze a specific table"""
    try:
        # Get column information
        result = await db.execute(text(f"""
            SELECT 
                column_name,
                data_type,
                is_nullable,
                column_default,
                character_maximum_length
            FROM information_schema.columns 
            WHERE table_name = '{table_name}' 
            ORDER BY ordinal_position;
        """))
        
        columns = result.fetchall()
        
        # Get row count
        count_result = await db.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
        row_count = count_result.scalar()
        
        print(f"\n📋 Table: {table_name.upper()}")
        print(f"   📊 Rows: {row_count}")
        print(f"   📝 Columns: {len(columns)}")
        
        if len(columns) <= 10:  # Show details for smaller tables
            print("   🔍 Structure:")
            for col in columns:
                col_name, data_type, nullable, default, max_length = col
                nullable_str = "NULL" if nullable == "YES" else "NOT NULL"
                length_str = f"({max_length})" if max_length else ""
                default_str = f" DEFAULT {default}" if default else ""
                print(f"      • {col_name}: {data_type}{length_str} {nullable_str}{default_str}")
        
        # Show sample data for key tables
        if table_name in ['users', 'organizations', 'projects', 'boards', 'cards'] and row_count > 0:
            sample_result = await db.execute(text(f"SELECT * FROM {table_name} LIMIT 3"))
            samples = sample_result.fetchall()
            if samples:
                print(f"   📄 Sample data ({len(samples)} rows):")
                for i, sample in enumerate(samples, 1):
                    print(f"      Row {i}: {len(sample)} fields")
        
    except Exception as e:
        print(f"   ❌ Error analyzing {table_name}: {e}")

async def check_indexes(db):
    """Check database indexes"""
    try:
        result = await db.execute(text("""
            SELECT 
                schemaname,
                tablename,
                indexname,
                indexdef
            FROM pg_indexes 
            WHERE schemaname = 'public'
            ORDER BY tablename, indexname;
        """))
        
        indexes = result.fetchall()
        
        print(f"📊 Found {len(indexes)} indexes:")
        
        current_table = None
        for schema, table, index_name, index_def in indexes:
            if table != current_table:
                print(f"\n📋 Table: {table}")
                current_table = table
            
            # Simplify index definition for readability
            if "UNIQUE" in index_def:
                index_type = "UNIQUE"
            elif "PRIMARY KEY" in index_def:
                index_type = "PRIMARY KEY"
            else:
                index_type = "INDEX"
            
            print(f"   • {index_name} ({index_type})")
        
    except Exception as e:
        print(f"❌ Error checking indexes: {e}")

async def check_constraints(db):
    """Check foreign key constraints"""
    try:
        result = await db.execute(text("""
            SELECT
                tc.table_name,
                tc.constraint_name,
                tc.constraint_type,
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            LEFT JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
                AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_schema = 'public'
            ORDER BY tc.table_name, tc.constraint_name;
        """))
        
        constraints = result.fetchall()
        
        print(f"🔗 Found {len(constraints)} foreign key constraints:")
        
        current_table = None
        for table, constraint, c_type, column, foreign_table, foreign_column in constraints:
            if table != current_table:
                print(f"\n📋 Table: {table}")
                current_table = table
            
            print(f"   • {column} → {foreign_table}.{foreign_column}")
        
    except Exception as e:
        print(f"❌ Error checking constraints: {e}")

async def main():
    """Main execution"""
    await check_database_tables()

if __name__ == "__main__":
    asyncio.run(main())
