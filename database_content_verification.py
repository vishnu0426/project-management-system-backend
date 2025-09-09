#!/usr/bin/env python3
"""
Database Content Verification - Detailed Table Analysis
"""
import asyncio
import sys
import os
from sqlalchemy import text

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__)))

async def verify_database_contents():
    """Verify detailed database contents and relationships"""
    print("🔍 DATABASE CONTENT VERIFICATION")
    print("=" * 80)
    
    try:
        from app.core.database import get_db
        
        async for db in get_db():
            try:
                # 1. Users Analysis
                print("\n1️⃣ USERS TABLE ANALYSIS")
                print("-" * 60)
                
                result = await db.execute(text("""
                    SELECT 
                        COUNT(*) as total_users,
                        COUNT(CASE WHEN email_verified = true THEN 1 END) as verified_users,
                        COUNT(CASE WHEN created_at > NOW() - INTERVAL '24 hours' THEN 1 END) as recent_users
                    FROM users
                """))
                user_stats = result.fetchone()
                print(f"   📊 Total Users: {user_stats[0]}")
                print(f"   ✅ Verified Users: {user_stats[1]}")
                print(f"   🆕 Recent Users (24h): {user_stats[2]}")
                
                # Sample user data
                result = await db.execute(text("""
                    SELECT email, first_name, last_name, created_at, email_verified
                    FROM users 
                    ORDER BY created_at DESC 
                    LIMIT 5
                """))
                recent_users = result.fetchall()
                print(f"\n   📋 Recent Users:")
                for user in recent_users:
                    verified_status = "✅" if user[4] else "❌"
                    print(f"      {verified_status} {user[1]} {user[2]} ({user[0]}) - {user[3].strftime('%Y-%m-%d %H:%M')}")
                
                # 2. Organizations Analysis
                print("\n2️⃣ ORGANIZATIONS TABLE ANALYSIS")
                print("-" * 60)
                
                result = await db.execute(text("""
                    SELECT 
                        COUNT(*) as total_orgs,
                        COUNT(CASE WHEN created_at > NOW() - INTERVAL '24 hours' THEN 1 END) as recent_orgs
                    FROM organizations
                """))
                org_stats = result.fetchone()
                print(f"   📊 Total Organizations: {org_stats[0]}")
                print(f"   🆕 Recent Organizations (24h): {org_stats[1]}")
                
                # Sample organization data
                result = await db.execute(text("""
                    SELECT o.name, o.description, u.email as created_by, o.created_at
                    FROM organizations o
                    JOIN users u ON o.created_by = u.id
                    ORDER BY o.created_at DESC 
                    LIMIT 5
                """))
                recent_orgs = result.fetchall()
                print(f"\n   📋 Recent Organizations:")
                for org in recent_orgs:
                    print(f"      🏢 {org[0]} (by {org[2]}) - {org[3].strftime('%Y-%m-%d %H:%M')}")
                
                # 3. Organization Members Analysis
                print("\n3️⃣ ORGANIZATION MEMBERS ANALYSIS")
                print("-" * 60)
                
                result = await db.execute(text("""
                    SELECT 
                        role,
                        COUNT(*) as count
                    FROM organization_members
                    GROUP BY role
                    ORDER BY count DESC
                """))
                role_stats = result.fetchall()
                print(f"   📊 Members by Role:")
                for role, count in role_stats:
                    print(f"      👤 {role.title()}: {count} members")
                
                # 4. Projects Analysis
                print("\n4️⃣ PROJECTS TABLE ANALYSIS")
                print("-" * 60)
                
                result = await db.execute(text("""
                    SELECT 
                        COUNT(*) as total_projects,
                        COUNT(CASE WHEN status = 'active' THEN 1 END) as active_projects,
                        COUNT(CASE WHEN created_at > NOW() - INTERVAL '24 hours' THEN 1 END) as recent_projects
                    FROM projects
                """))
                project_stats = result.fetchone()
                print(f"   📊 Total Projects: {project_stats[0]}")
                print(f"   ✅ Active Projects: {project_stats[1]}")
                print(f"   🆕 Recent Projects (24h): {project_stats[2]}")
                
                # Sample project data
                result = await db.execute(text("""
                    SELECT p.name, p.status, o.name as org_name, u.email as created_by, p.created_at
                    FROM projects p
                    JOIN organizations o ON p.organization_id = o.id
                    JOIN users u ON p.created_by = u.id
                    ORDER BY p.created_at DESC 
                    LIMIT 5
                """))
                recent_projects = result.fetchall()
                print(f"\n   📋 Recent Projects:")
                for project in recent_projects:
                    status_icon = "✅" if project[1] == "active" else "⏸️"
                    print(f"      {status_icon} {project[0]} ({project[2]}) by {project[3]} - {project[4].strftime('%Y-%m-%d %H:%M')}")
                
                # 5. Boards Analysis
                print("\n5️⃣ BOARDS TABLE ANALYSIS")
                print("-" * 60)
                
                result = await db.execute(text("SELECT COUNT(*) FROM boards"))
                board_count = result.scalar()
                print(f"   📊 Total Boards: {board_count}")
                
                if board_count > 0:
                    result = await db.execute(text("""
                        SELECT b.name, p.name as project_name, u.email as created_by, b.created_at
                        FROM boards b
                        JOIN projects p ON b.project_id = p.id
                        JOIN users u ON b.created_by = u.id
                        ORDER BY b.created_at DESC 
                        LIMIT 5
                    """))
                    boards = result.fetchall()
                    print(f"\n   📋 Boards:")
                    for board in boards:
                        print(f"      📋 {board[0]} (Project: {board[1]}) by {board[2]} - {board[3].strftime('%Y-%m-%d %H:%M')}")
                
                # 6. Cards Analysis
                print("\n6️⃣ CARDS TABLE ANALYSIS")
                print("-" * 60)
                
                result = await db.execute(text("""
                    SELECT 
                        COUNT(*) as total_cards,
                        COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_cards
                    FROM cards
                """))
                card_stats = result.fetchone()
                print(f"   📊 Total Cards: {card_stats[0]}")
                print(f"   ✅ Completed Cards: {card_stats[1]}")
                
                if card_stats[0] > 0:
                    result = await db.execute(text("""
                        SELECT c.title, c.status, c.priority, u.email as created_by, c.created_at
                        FROM cards c
                        JOIN users u ON c.created_by = u.id
                        ORDER BY c.created_at DESC 
                        LIMIT 5
                    """))
                    cards = result.fetchall()
                    print(f"\n   📋 Recent Cards:")
                    for card in cards:
                        priority_icon = "🔴" if card[2] == "high" else "🟡" if card[2] == "medium" else "🟢"
                        status_icon = "✅" if card[1] == "completed" else "⏳"
                        print(f"      {status_icon} {priority_icon} {card[0]} by {card[3]} - {card[4].strftime('%Y-%m-%d %H:%M')}")
                
                # 7. Sessions Analysis
                print("\n7️⃣ SESSIONS TABLE ANALYSIS")
                print("-" * 60)
                
                result = await db.execute(text("""
                    SELECT 
                        COUNT(*) as total_sessions,
                        COUNT(CASE WHEN is_active = true THEN 1 END) as active_sessions,
                        COUNT(CASE WHEN expires_at > NOW() THEN 1 END) as valid_sessions
                    FROM sessions
                """))
                session_stats = result.fetchone()
                print(f"   📊 Total Sessions: {session_stats[0]}")
                print(f"   ✅ Active Sessions: {session_stats[1]}")
                print(f"   🔑 Valid Sessions: {session_stats[2]}")
                
                # 8. Checklist Items Analysis
                print("\n8️⃣ CHECKLIST ITEMS ANALYSIS")
                print("-" * 60)
                
                result = await db.execute(text("""
                    SELECT 
                        COUNT(*) as total_items,
                        COUNT(CASE WHEN completed = true THEN 1 END) as completed_items
                    FROM checklist_items
                """))
                checklist_stats = result.fetchone()
                print(f"   📊 Total Checklist Items: {checklist_stats[0]}")
                print(f"   ✅ Completed Items: {checklist_stats[1]}")
                
                if checklist_stats[0] > 0:
                    completion_rate = (checklist_stats[1] / checklist_stats[0]) * 100
                    print(f"   📈 Completion Rate: {completion_rate:.1f}%")
                
                # 9. Data Integrity Checks
                print("\n9️⃣ DATA INTEGRITY CHECKS")
                print("-" * 60)
                
                # Check for orphaned records
                integrity_checks = [
                    ("Orphaned organization members", """
                        SELECT COUNT(*) FROM organization_members om
                        LEFT JOIN users u ON om.user_id = u.id
                        LEFT JOIN organizations o ON om.organization_id = o.id
                        WHERE u.id IS NULL OR o.id IS NULL
                    """),
                    ("Orphaned projects", """
                        SELECT COUNT(*) FROM projects p
                        LEFT JOIN organizations o ON p.organization_id = o.id
                        WHERE o.id IS NULL
                    """),
                    ("Orphaned boards", """
                        SELECT COUNT(*) FROM boards b
                        LEFT JOIN projects p ON b.project_id = p.id
                        WHERE p.id IS NULL
                    """),
                    ("Orphaned cards", """
                        SELECT COUNT(*) FROM cards c
                        LEFT JOIN columns col ON c.column_id = col.id
                        WHERE col.id IS NULL
                    """)
                ]
                
                for check_name, query in integrity_checks:
                    try:
                        result = await db.execute(text(query))
                        count = result.scalar()
                        if count == 0:
                            print(f"   ✅ {check_name}: None found")
                        else:
                            print(f"   ❌ {check_name}: {count} found")
                    except Exception as e:
                        print(f"   ⚠️ {check_name}: Check failed - {e}")
                
                # 10. Performance Metrics
                print("\n🔟 PERFORMANCE METRICS")
                print("-" * 60)
                
                # Check index usage (simplified)
                result = await db.execute(text("""
                    SELECT COUNT(*) FROM pg_stat_user_indexes 
                    WHERE idx_scan > 0
                """))
                used_indexes = result.scalar()
                
                result = await db.execute(text("""
                    SELECT COUNT(*) FROM pg_indexes 
                    WHERE schemaname = 'public'
                """))
                total_indexes = result.scalar()
                
                print(f"   📊 Total Indexes: {total_indexes}")
                print(f"   ✅ Used Indexes: {used_indexes}")
                if total_indexes > 0:
                    usage_rate = (used_indexes / total_indexes) * 100
                    print(f"   📈 Index Usage Rate: {usage_rate:.1f}%")
                
                print("\n" + "=" * 80)
                print("✅ DATABASE CONTENT VERIFICATION COMPLETED")
                print("=" * 80)
                
            except Exception as e:
                print(f"❌ Database content verification failed: {e}")
                import traceback
                traceback.print_exc()
            
            break
            
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Main execution"""
    await verify_database_contents()

if __name__ == "__main__":
    asyncio.run(main())
