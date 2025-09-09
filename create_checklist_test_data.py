#!/usr/bin/env python3
"""
Create test data for checklist functionality
"""
import asyncio
import sys
import os

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__)))

async def create_test_data():
    """Create test data for checklist functionality"""
    try:
        from app.core.database import get_db
        from app.models.card import Card, ChecklistItem
        from app.models.user import User
        from app.models.column import Column
        from app.models.board import Board
        from app.models.project import Project
        from app.models.organization import Organization
        from sqlalchemy import select
        
        print("🔍 Creating test data for checklist functionality...")
        
        async for db in get_db():
            try:
                # Find an existing user
                user_result = await db.execute(select(User).limit(1))
                user = user_result.scalar_one_or_none()
                
                if not user:
                    print("❌ No users found in database")
                    return False
                
                print(f"✅ Found user: {user.email}")
                
                # Find an existing card
                card_result = await db.execute(select(Card).limit(1))
                card = card_result.scalar_one_or_none()
                
                if not card:
                    print("❌ No cards found in database")
                    return False
                
                print(f"✅ Found card: {card.title}")
                
                # Check if card already has checklist items
                existing_items_result = await db.execute(
                    select(ChecklistItem).where(ChecklistItem.card_id == card.id)
                )
                existing_items = existing_items_result.scalars().all()
                
                if existing_items:
                    print(f"✅ Card already has {len(existing_items)} checklist items")
                    return True
                
                # Create test checklist items
                test_items = [
                    {"text": "Review requirements", "completed": False, "position": 1},
                    {"text": "Design mockups", "completed": True, "position": 2},
                    {"text": "Implement functionality", "completed": False, "position": 3},
                    {"text": "Write tests", "completed": False, "position": 4},
                    {"text": "Deploy to staging", "completed": False, "position": 5}
                ]
                
                created_items = []
                for item_data in test_items:
                    item = ChecklistItem(
                        card_id=card.id,
                        text=item_data["text"],
                        completed=item_data["completed"],
                        position=item_data["position"],
                        created_by=user.id
                    )
                    db.add(item)
                    created_items.append(item)
                
                await db.commit()
                
                print(f"✅ Created {len(created_items)} checklist items:")
                for item in created_items:
                    status = "✅" if item.completed else "⬜"
                    print(f"   {status} {item.text}")
                
                return True
                
            except Exception as e:
                print(f"❌ Failed to create test data: {e}")
                import traceback
                traceback.print_exc()
                await db.rollback()
                return False
            
            break
            
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main function"""
    print("🚀 Creating Checklist Test Data")
    print("=" * 50)
    
    success = await create_test_data()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ Test data created successfully!")
    else:
        print("❌ Failed to create test data!")

if __name__ == "__main__":
    asyncio.run(main())
