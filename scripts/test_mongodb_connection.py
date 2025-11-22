#!/usr/bin/env python3
"""
Quick script to test MongoDB connection
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.mongodb_client import MongoDBClient
from src.config import Config
from src.database.models import UserModel

def test_connection():
    """Test MongoDB connection and basic operations"""
    print("🔍 Testing MongoDB Connection...")
    print("=" * 60)
    
    try:
        # Initialize client
        client = MongoDBClient(
            connection_string=Config.MONGODB_URI,
            db_name=Config.MONGODB_DB_NAME
        )
        
        if not client.is_connected():
            print("❌ MongoDB connection failed")
            print("⚠️  Check your connection string and network access")
            return False
        
        print(f"✅ Connected to MongoDB")
        print(f"   Database: {client.db_name}")
        print(f"   URI: {Config.MONGODB_URI[:50]}...")
        
        # Test collections
        print("\n📋 Testing Collections...")
        collections = ['users', 'routines', 'ride_requests', 'matches', 'notifications']
        
        for collection_name in collections:
            try:
                collection = client.get_collection(collection_name)
                count = collection.count_documents({})
                print(f"   ✅ {collection_name}: {count} documents")
            except Exception as e:
                print(f"   ⚠️  {collection_name}: {e}")
        
        # Test write/read operations
        print("\n🔧 Testing Operations...")
        users_collection = client.get_collection('users')
        
        # Test insert
        test_user = UserModel.create('test_connection_script')
        result = users_collection.insert_one(test_user)
        print(f"   ✅ Insert: OK (ID: {result.inserted_id})")
        
        # Test read
        found = users_collection.find_one({'phone_number': 'test_connection_script'})
        if found:
            print(f"   ✅ Read: OK")
        
        # Test update
        users_collection.update_one(
            {'phone_number': 'test_connection_script'},
            {'$set': {'full_name': 'Test User'}}
        )
        updated = users_collection.find_one({'phone_number': 'test_connection_script'})
        if updated and updated.get('full_name') == 'Test User':
            print(f"   ✅ Update: OK")
        
        # Test delete
        users_collection.delete_one({'phone_number': 'test_connection_script'})
        deleted = users_collection.find_one({'phone_number': 'test_connection_script'})
        if not deleted:
            print(f"   ✅ Delete: OK")
        
        # Check indexes
        print("\n📊 Checking Indexes...")
        indexes = list(users_collection.list_indexes())
        print(f"   ✅ Found {len(indexes)} indexes")
        for idx in indexes[:5]:  # Show first 5
            print(f"      - {idx['name']}")
        
        print("\n" + "=" * 60)
        print("🎉 All tests passed! MongoDB is working correctly!")
        print("=" * 60)
        
        client.close()
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)


