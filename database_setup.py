#!/usr/bin/env python3
"""
Database Setup and Migration Script for Agno WorkSphere
Single command to setup database and run migrations
"""
import asyncio
import os
import sys
import time
from pathlib import Path
from sqlalchemy import text
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Add the app directory to Python path
sys.path.append(str(Path(__file__).parent))

class DatabaseSetup:
    def __init__(self):
        self.db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': os.getenv('DB_PORT', '5432'),
            'username': os.getenv('DB_USERNAME', 'postgres'),
            'password': os.getenv('DB_PASSWORD', 'admin'),
            'database': os.getenv('DB_NAME', 'agno_worksphere')
        }
        
        self.database_url = f"postgresql+asyncpg://{self.db_config['username']}:{self.db_config['password']}@{self.db_config['host']}:{self.db_config['port']}/{self.db_config['database']}"
        
    def print_banner(self):
        """Print setup banner"""
        print("DATABASE SETUP - AGNO WORKSPHERE")
        print("=" * 80)
        print(f"   Database Host: {self.db_config['host']}:{self.db_config['port']}")
        print(f"   Database Name: {self.db_config['database']}")
        print(f"   Username: {self.db_config['username']}")
        print("=" * 80)
    
    def create_database_if_not_exists(self):
        """Create database if it doesn't exist"""
        print("\n[1] CHECKING DATABASE EXISTENCE")
        print("-" * 60)
        
        try:
            # Connect to PostgreSQL server (not specific database)
            conn = psycopg2.connect(
                host=self.db_config['host'],
                port=self.db_config['port'],
                user=self.db_config['username'],
                password=self.db_config['password'],
                database='postgres'
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()
            
            # Check if database exists
            cursor.execute(f"SELECT 1 FROM pg_database WHERE datname = '{self.db_config['database']}'")
            exists = cursor.fetchone()
            
            if exists:
                print(f"   [OK] Database '{self.db_config['database']}' already exists")
            else:
                print(f"   [CREATE] Creating database '{self.db_config['database']}'...")
                cursor.execute(f"CREATE DATABASE {self.db_config['database']}")
                print(f"   [OK] Database '{self.db_config['database']}' created successfully")
            
            cursor.close()
            conn.close()
            return True
            
        except Exception as e:
            print(f"   [ERROR] Database creation failed: {e}")
            print("\nTroubleshooting:")
            print("   1. Make sure PostgreSQL is running")
            print("   2. Check database credentials")
            print("   3. Ensure user has CREATE DATABASE privileges")
            return False
    
    async def create_tables(self):
        """Create all database tables"""
        print("\n[2] CREATING DATABASE TABLES")
        print("-" * 60)

        try:
            from app.core.database import Base, engine

            # Create all tables
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            print("   [OK] All database tables created successfully")
            return True

        except Exception as e:
            print(f"   [ERROR] Table creation failed: {e}")
            return False
    
    async def create_indexes(self):
        """Create database indexes for performance"""
        print("\n[3] CREATING PERFORMANCE INDEXES")
        print("-" * 60)
        
        try:
            from app.core.database import get_db
            
            indexes = [
                # User indexes
                "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)",
                "CREATE INDEX IF NOT EXISTS idx_users_email_verified ON users(email_verified)",
                
                # Organization indexes
                "CREATE INDEX IF NOT EXISTS idx_organizations_created_by ON organizations(created_by)",
                "CREATE INDEX IF NOT EXISTS idx_organizations_domain ON organizations(domain)",
                
                # Organization member indexes
                "CREATE INDEX IF NOT EXISTS idx_org_members_user_id ON organization_members(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_org_members_org_id ON organization_members(organization_id)",
                "CREATE INDEX IF NOT EXISTS idx_org_members_role ON organization_members(role)",
                
                # Project indexes
                "CREATE INDEX IF NOT EXISTS idx_projects_org_id ON projects(organization_id)",
                "CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status)",
                
                # Board indexes
                "CREATE INDEX IF NOT EXISTS idx_boards_project_id ON boards(project_id)",
                
                # Card indexes
                "CREATE INDEX IF NOT EXISTS idx_cards_column_id ON cards(column_id)",
                "CREATE INDEX IF NOT EXISTS idx_cards_status ON cards(status)",
                "CREATE INDEX IF NOT EXISTS idx_cards_priority ON cards(priority)",
                
                # Session indexes
                "CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_sessions_session_token ON sessions(session_token)",
                "CREATE INDEX IF NOT EXISTS idx_sessions_active ON sessions(is_active)",
                
                # Card assignment indexes
                "CREATE INDEX IF NOT EXISTS idx_card_assignments_card_id ON card_assignments(card_id)",
                "CREATE INDEX IF NOT EXISTS idx_card_assignments_user_id ON card_assignments(user_id)"
            ]
            
            async for db in get_db():
                created_count = 0
                for index_sql in indexes:
                    try:
                        await db.execute(text(index_sql))
                        created_count += 1
                    except Exception as e:
                        print(f"   [WARN] Index creation warning: {e}")

                await db.commit()
                print(f"   [OK] Created {created_count}/{len(indexes)} performance indexes")
                break

            return True

        except Exception as e:
            print(f"   [ERROR] Index creation failed: {e}")
            return False
    
    async def seed_initial_data(self):
        """Seed initial data for testing"""
        print("\n[4] SEEDING INITIAL DATA")
        print("-" * 60)
        
        try:
            from app.core.database import get_db
            from app.models.user import User
            from app.models.organization import Organization, OrganizationMember
            from app.core.security import hash_password
            from sqlalchemy import select
            
            async for db in get_db():
                # Check if data already exists
                result = await db.execute(select(User).limit(1))
                if result.scalar_one_or_none():
                    print("   [OK] Initial data already exists, skipping seeding")
                    break
                
                # Create test users
                test_users = [
                    {
                        "email": "owner@agnoworksphere.com",
                        "password": "OwnerPass123!",
                        "first_name": "System",
                        "last_name": "Owner",
                        "role": "owner"
                    },
                    {
                        "email": "admin@agnoworksphere.com", 
                        "password": "AdminPass123!",
                        "first_name": "System",
                        "last_name": "Admin",
                        "role": "admin"
                    },
                    {
                        "email": "member@agnoworksphere.com",
                        "password": "MemberPass123!",
                        "first_name": "System",
                        "last_name": "Member",
                        "role": "member"
                    }
                ]
                
                created_users = []
                for user_data in test_users:
                    user = User(
                        email=user_data["email"],
                        password_hash=hash_password(user_data["password"]),
                        first_name=user_data["first_name"],
                        last_name=user_data["last_name"],
                        email_verified=True
                    )
                    db.add(user)
                    created_users.append((user, user_data["role"]))
                
                await db.flush()  # Get user IDs
                
                # Create default organization
                owner_user = created_users[0][0]  # First user is owner
                organization = Organization(
                    name="Agno WorkSphere Demo",
                    description="Default organization for testing and demonstration",
                    domain="agnoworksphere.com",
                    created_by=owner_user.id
                )
                db.add(organization)
                await db.flush()  # Get organization ID
                
                # Add users to organization with their roles
                for user, role in created_users:
                    member = OrganizationMember(
                        organization_id=organization.id,
                        user_id=user.id,
                        role=role,
                        invited_by=owner_user.id
                    )
                    db.add(member)
                
                await db.commit()
                print(f"   [OK] Created {len(test_users)} test users")
                print(f"   [OK] Created default organization: {organization.name}")
                print("   [OK] Initial data seeding completed")
                break

            return True

        except Exception as e:
            print(f"   [ERROR] Data seeding failed: {e}")
            return False
    
    async def verify_setup(self):
        """Verify database setup"""
        print("\n[5] VERIFYING DATABASE SETUP")
        print("-" * 60)
        
        try:
            from app.core.database import get_db
            
            async for db in get_db():
                # Check table counts
                tables_to_check = [
                    ("users", "Users"),
                    ("organizations", "Organizations"), 
                    ("organization_members", "Organization Members")
                ]
                
                for table_name, display_name in tables_to_check:
                    try:
                        result = await db.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                        count = result.scalar()
                        print(f"   [DATA] {display_name}: {count} records")
                    except Exception as e:
                        print(f"   [ERROR] {display_name}: Table check failed - {e}")

                print("   [OK] Database verification completed")
                break

            return True

        except Exception as e:
            print(f"   [ERROR] Database verification failed: {e}")
            return False
    
    async def run_setup(self):
        """Run complete database setup"""
        self.print_banner()
        
        start_time = time.time()
        
        # Step 1: Create database
        if not self.create_database_if_not_exists():
            return False
        
        # Step 2: Create tables
        if not await self.create_tables():
            return False
        
        # Step 3: Create indexes
        if not await self.create_indexes():
            return False
        
        # Step 4: Seed initial data
        if not await self.seed_initial_data():
            return False
        
        # Step 5: Verify setup
        if not await self.verify_setup():
            return False
        
        setup_time = time.time() - start_time
        
        print("\n" + "=" * 80)
        print("DATABASE SETUP COMPLETED SUCCESSFULLY")
        print("=" * 80)
        print(f"   Setup Time: {setup_time:.2f} seconds")
        print(f"   Database URL: {self.database_url}")
        print("\nTest Credentials:")
        print("   Owner: owner@agnoworksphere.com / OwnerPass123!")
        print("   Admin: admin@agnoworksphere.com / AdminPass123!")
        print("   Member: member@agnoworksphere.com / MemberPass123!")
        print("\nReady to start the server with: python run.py")
        print("=" * 80)
        
        return True

async def main():
    """Main setup function"""
    setup = DatabaseSetup()
    success = await setup.run_setup()
    
    if not success:
        print("\n[ERROR] Database setup failed!")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
