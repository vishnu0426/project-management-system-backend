#!/usr/bin/env python3
"""
Check user table schema
"""
import asyncio
import asyncpg

async def check_user_schema():
    """Check user table schema"""
    try:
        conn = await asyncpg.connect('postgresql://postgres:admin@localhost:5432/agno_worksphere_test')
        
        # Check users table columns
        result = await conn.fetch("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'users'
            ORDER BY ordinal_position
        """)
        
        print("Users table schema:")
        for row in result:
            print(f"  {row['column_name']}: {row['data_type']} ({'NULL' if row['is_nullable'] == 'YES' else 'NOT NULL'})")
        
        await conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_user_schema())
