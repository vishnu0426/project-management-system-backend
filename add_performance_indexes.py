#!/usr/bin/env python3
"""
Add performance indexes to the database
"""
import asyncio
import sys
import os

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__)))

async def add_performance_indexes():
    """Add performance indexes to critical tables"""
    print("🚀 ADDING PERFORMANCE INDEXES")
    print("=" * 50)
    
    try:
        from app.core.database import get_db
        from sqlalchemy import text
        
        indexes_to_create = [
            # User table indexes
            ("idx_users_email", "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)"),
            ("idx_users_created_at", "CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at)"),

            # Organization member indexes
            ("idx_org_members_user_id", "CREATE INDEX IF NOT EXISTS idx_org_members_user_id ON organization_members(user_id)"),
            ("idx_org_members_org_id", "CREATE INDEX IF NOT EXISTS idx_org_members_org_id ON organization_members(organization_id)"),
            ("idx_org_members_role", "CREATE INDEX IF NOT EXISTS idx_org_members_role ON organization_members(role)"),
            ("idx_org_members_user_org", "CREATE INDEX IF NOT EXISTS idx_org_members_user_org ON organization_members(user_id, organization_id)"),

            # Project indexes
            ("idx_projects_org_id", "CREATE INDEX IF NOT EXISTS idx_projects_org_id ON projects(organization_id)"),
            ("idx_projects_created_by", "CREATE INDEX IF NOT EXISTS idx_projects_created_by ON projects(created_by)"),
            ("idx_projects_status", "CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status)"),

            # Board indexes
            ("idx_boards_project_id", "CREATE INDEX IF NOT EXISTS idx_boards_project_id ON boards(project_id)"),
            ("idx_boards_created_by", "CREATE INDEX IF NOT EXISTS idx_boards_created_by ON boards(created_by)"),

            # Card indexes
            ("idx_cards_board_id", "CREATE INDEX IF NOT EXISTS idx_cards_board_id ON cards(board_id)"),
            ("idx_cards_created_by", "CREATE INDEX IF NOT EXISTS idx_cards_created_by ON cards(created_by)"),
            ("idx_cards_assigned_to", "CREATE INDEX IF NOT EXISTS idx_cards_assigned_to ON cards(assigned_to)"),
            ("idx_cards_status", "CREATE INDEX IF NOT EXISTS idx_cards_status ON cards(status)"),
            ("idx_cards_priority", "CREATE INDEX IF NOT EXISTS idx_cards_priority ON cards(priority)"),

            # Session indexes
            ("idx_sessions_user_id", "CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id)"),
            ("idx_sessions_token", "CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(session_token)"),
            ("idx_sessions_active", "CREATE INDEX IF NOT EXISTS idx_sessions_active ON sessions(is_active)"),
            ("idx_sessions_expires", "CREATE INDEX IF NOT EXISTS idx_sessions_expires ON sessions(expires_at)"),

            # Organization indexes
            ("idx_organizations_created_by", "CREATE INDEX IF NOT EXISTS idx_organizations_created_by ON organizations(created_by)"),
            ("idx_organizations_domain", "CREATE INDEX IF NOT EXISTS idx_organizations_domain ON organizations(domain)"),
        ]
        
        async for db in get_db():
            try:
                created_count = 0
                failed_count = 0
                
                for index_name, sql in indexes_to_create:
                    try:
                        print(f"   📊 Creating index: {index_name}")
                        await db.execute(text(sql))
                        created_count += 1
                        print(f"   ✅ Created: {index_name}")
                    except Exception as e:
                        failed_count += 1
                        if "already exists" in str(e).lower() or "relation" in str(e).lower():
                            print(f"   ℹ️ Already exists: {index_name}")
                        else:
                            print(f"   ❌ Failed to create {index_name}: {e}")
                            await db.rollback()

                await db.commit()
                
                print(f"\n📊 INDEX CREATION SUMMARY")
                print(f"   ✅ Created: {created_count}")
                print(f"   ❌ Failed: {failed_count}")
                print(f"   📋 Total attempted: {len(indexes_to_create)}")
                
                # Analyze tables for query optimization
                print(f"\n📊 ANALYZING TABLES FOR PERFORMANCE")
                tables_to_analyze = [
                    "users", "organizations", "organization_members", 
                    "projects", "boards", "cards", "sessions"
                ]
                
                for table in tables_to_analyze:
                    try:
                        await db.execute(text(f"ANALYZE {table}"))
                        print(f"   ✅ Analyzed: {table}")
                    except Exception as e:
                        print(f"   ❌ Failed to analyze {table}: {e}")
                
                await db.commit()
                
            except Exception as e:
                print(f"❌ Database operation failed: {e}")
                await db.rollback()
            
            break
            
    except Exception as e:
        print(f"❌ Failed to add indexes: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Main execution"""
    await add_performance_indexes()

if __name__ == "__main__":
    asyncio.run(main())
