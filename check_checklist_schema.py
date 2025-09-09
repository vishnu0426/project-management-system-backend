#!/usr/bin/env python3
"""
Check checklist_items table schema
"""
import asyncio
import asyncpg

async def check_checklist_schema():
    """Check checklist_items table schema"""
    try:
        conn = await asyncpg.connect('postgresql://postgres:admin@localhost:5432/agno_worksphere_test')
        
        # Check checklist_items table columns
        result = await conn.fetch("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'checklist_items'
            ORDER BY ordinal_position
        """)
        
        print("Checklist Items table schema:")
        for row in result:
            print(f"  {row['column_name']}: {row['data_type']} ({'NULL' if row['is_nullable'] == 'YES' else 'NOT NULL'})")
        
        await conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_checklist_schema())
