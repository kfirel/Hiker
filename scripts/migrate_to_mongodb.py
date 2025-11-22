#!/usr/bin/env python3
"""
Migration script to migrate data from JSON to MongoDB
"""

import sys
import os
import json
from datetime import datetime
from bson import ObjectId

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.mongodb_client import MongoDBClient
from src.database.models import UserModel, RoutineModel
from src.config import Config

def migrate_users(json_file='user_data.json'):
    """Migrate users from JSON to MongoDB"""
    
    # Load JSON data
    if not os.path.exists(json_file):
        print(f"❌ JSON file not found: {json_file}")
        return False
    
    with open(json_file, 'r', encoding='utf-8') as f:
        json_data = json.load(f)
    
    users = json_data.get('users', {})
    if not users:
        print("⚠️ No users found in JSON file")
        return False
    
    # Initialize MongoDB
    try:
        mongo = MongoDBClient(
            connection_string=Config.MONGODB_URI,
            db_name=Config.MONGODB_DB_NAME
        )
    except Exception as e:
        print(f"❌ Failed to connect to MongoDB: {e}")
        return False
    
    if not mongo.is_connected():
        print("❌ MongoDB is not connected")
        return False
    
    users_collection = mongo.get_collection("users")
    routines_collection = mongo.get_collection("routines")
    
    migrated_count = 0
    skipped_count = 0
    error_count = 0
    
    print(f"\n🔄 Starting migration of {len(users)} users...\n")
    
    for phone_number, user_data in users.items():
        try:
            # Check if user already exists
            existing = users_collection.find_one({"phone_number": phone_number})
            if existing:
                print(f"⏭️  User {phone_number} already exists, skipping...")
                skipped_count += 1
                continue
            
            # Convert JSON user to MongoDB format
            mongo_user = {
                "phone_number": phone_number,
                "whatsapp_name": user_data.get('profile', {}).get('whatsapp_name'),
                "full_name": user_data.get('profile', {}).get('full_name'),
                "home_settlement": user_data.get('profile', {}).get('home_settlement', 'גברעם'),
                "user_type": user_data.get('profile', {}).get('user_type'),
                "default_destination": user_data.get('profile', {}).get('default_destination'),
                "alert_preference": user_data.get('profile', {}).get('alert_preference'),
                "current_state": user_data.get('state', {}).get('current_state', 'initial'),
                "state_context": user_data.get('state', {}).get('context', {}),
                "state_history": user_data.get('state', {}).get('history', []),
                "is_registered": user_data.get('registered', False),
                "created_at": datetime.fromisoformat(user_data.get('created_at', datetime.now().isoformat())),
                "registered_at": datetime.fromisoformat(user_data['registered_at']) if user_data.get('registered_at') else None,
                "last_active": datetime.now()
            }
            
            # Insert user
            result = users_collection.insert_one(mongo_user)
            user_id = result.inserted_id
            
            # Migrate routines
            routines = user_data.get('routines', [])
            for routine in routines:
                routine_doc = RoutineModel.create(
                    user_id=user_id,
                    phone_number=phone_number,
                    destination=routine.get('routine_destination', ''),
                    days=routine.get('routine_days', ''),
                    departure_time=routine.get('routine_departure_time', ''),
                    return_time=routine.get('routine_return_time', '')
                )
                routines_collection.insert_one(routine_doc)
            
            migrated_count += 1
            print(f"✅ Migrated user {phone_number} ({mongo_user.get('full_name', 'N/A')})")
            
        except Exception as e:
            print(f"❌ Error migrating user {phone_number}: {e}")
            error_count += 1
    
    print(f"\n📊 Migration Summary:")
    print(f"   ✅ Migrated: {migrated_count}")
    print(f"   ⏭️  Skipped: {skipped_count}")
    print(f"   ❌ Errors: {error_count}")
    print(f"   📝 Total: {len(users)}")
    
    mongo.close()
    return error_count == 0

if __name__ == "__main__":
    json_file = sys.argv[1] if len(sys.argv) > 1 else 'user_data.json'
    
    print("🚀 MongoDB Migration Script")
    print("=" * 50)
    
    success = migrate_users(json_file)
    
    if success:
        print("\n✅ Migration completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Migration completed with errors")
        sys.exit(1)



