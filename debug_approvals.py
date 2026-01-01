"""
Debug script to check pending approvals in Firestore
"""

import asyncio
from database import initialize_db, get_db

async def check_pending_approvals():
    """Check all pending approvals in the database"""
    db = initialize_db()
    
    if not db:
        print("❌ Database not available")
        return
    
    print("🔍 Checking pending_approvals collection...")
    
    try:
        docs = db.collection("pending_approvals").stream()
        
        count = 0
        for doc in docs:
            count += 1
            data = doc.to_dict()
            print(f"\n📋 Approval {count}:")
            print(f"   ID: {doc.id}")
            print(f"   Driver: {data.get('driver_phone')}")
            print(f"   Hitchhiker: {data.get('hitchhiker_phone')}")
            print(f"   Status: {data.get('status')}")
            print(f"   Created: {data.get('created_at')}")
        
        if count == 0:
            print("\n⚠️ No pending approvals found in database!")
            print("\nThis means:")
            print("1. No hitchhikers have requested rides yet, OR")
            print("2. All drivers have auto_approve_matches=True, OR")
            print("3. The create_pending_approval function is not working")
        else:
            print(f"\n✅ Total pending approvals: {count}")
    
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_pending_approvals())

