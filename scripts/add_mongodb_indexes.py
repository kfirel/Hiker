#!/usr/bin/env python3
"""
Script to add MongoDB indexes for performance optimization
Run this script to add all required indexes to your MongoDB database
"""

import os
import sys
from pymongo import MongoClient
from pymongo.errors import OperationFailure

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import Config

def add_indexes():
    """Add all required indexes to MongoDB collections"""
    
    # Connect to MongoDB
    try:
        client = MongoClient(Config.MONGODB_URI)
        db = client[Config.MONGODB_DB_NAME]
        
        print("🔗 Connected to MongoDB")
        print(f"📊 Database: {Config.MONGODB_DB_NAME}")
        print("")
        
        # List of indexes to create
        indexes = [
            # Users collection
            {
                'collection': 'users',
                'index': [('phone_number', 1)],
                'options': {'unique': True},
                'name': 'phone_number_1'
            },
            {
                'collection': 'users',
                'index': [('state', 1)],
                'options': {},
                'name': 'state_1'
            },
            {
                'collection': 'users',
                'index': [('user_type', 1)],
                'options': {},
                'name': 'user_type_1'
            },
            # Ride requests collection
            {
                'collection': 'ride_requests',
                'index': [('requester_id', 1), ('created_at', -1)],
                'options': {},
                'name': 'requester_id_1_created_at_-1'
            },
            {
                'collection': 'ride_requests',
                'index': [('destination', 1)],
                'options': {},
                'name': 'destination_1'
            },
            # Matches collection
            {
                'collection': 'matches',
                'index': [('driver_id', 1), ('status', 1)],
                'options': {},
                'name': 'driver_id_1_status_1'
            },
            {
                'collection': 'matches',
                'index': [('ride_request_id', 1)],
                'options': {},
                'name': 'ride_request_id_1'
            },
            # Routines collection
            {
                'collection': 'routines',
                'index': [('driver_id', 1)],
                'options': {},
                'name': 'driver_id_1'
            },
        ]
        
        # Add indexes
        created_count = 0
        skipped_count = 0
        error_count = 0
        
        for idx_config in indexes:
            collection_name = idx_config['collection']
            index_spec = idx_config['index']
            options = idx_config.get('options', {})
            index_name = idx_config.get('name', None)
            
            try:
                collection = db[collection_name]
                
                # Check if index already exists
                existing_indexes = collection.index_information()
                if index_name and index_name in existing_indexes:
                    print(f"⏭️  Skipping {collection_name}.{index_name} (already exists)")
                    skipped_count += 1
                    continue
                
                # Create index
                result = collection.create_index(index_spec, **options, name=index_name)
                print(f"✅ Created index: {collection_name}.{index_name or result}")
                created_count += 1
                
            except OperationFailure as e:
                if 'already exists' in str(e).lower() or 'duplicate key' in str(e).lower():
                    print(f"⏭️  Skipping {collection_name}.{index_name} (already exists)")
                    skipped_count += 1
                else:
                    print(f"❌ Error creating index {collection_name}.{index_name}: {e}")
                    error_count += 1
            except Exception as e:
                print(f"❌ Error creating index {collection_name}.{index_name}: {e}")
                error_count += 1
        
        print("")
        print("=" * 50)
        print(f"✅ Created: {created_count}")
        print(f"⏭️  Skipped: {skipped_count}")
        print(f"❌ Errors: {error_count}")
        print("=" * 50)
        
        # Show all indexes
        print("")
        print("📋 Current indexes:")
        print("-" * 50)
        for idx_config in indexes:
            collection_name = idx_config['collection']
            collection = db[collection_name]
            indexes_list = collection.index_information()
            print(f"\n{collection_name}:")
            for idx_name, idx_info in indexes_list.items():
                print(f"  - {idx_name}: {idx_info.get('key', 'N/A')}")
        
        client.close()
        print("")
        print("✅ Done!")
        
    except Exception as e:
        print(f"❌ Error connecting to MongoDB: {e}")
        sys.exit(1)

if __name__ == '__main__':
    print("🚀 MongoDB Index Creation Script")
    print("=" * 50)
    print("")
    add_indexes()

