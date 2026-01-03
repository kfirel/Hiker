#!/usr/bin/env python3
"""
Update existing hitchhiker requests with origin/destination coordinates
Run this script to add map support for old hitchhiker requests
"""

import sys
import os

# Add parent directory to path
parent_dir = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, parent_dir)

import logging

# Import minimal dependencies
os.environ.setdefault('GOOGLE_APPLICATION_CREDENTIALS', '')  # Will use default credentials

from google.cloud import firestore
import firebase_admin
from firebase_admin import credentials

# We'll define our own geocode function to avoid circular imports
def simple_geocode(address):
    """Simple geocoding using geopy"""
    from geopy.geocoders import Nominatim
    try:
        geolocator = Nominatim(user_agent="hiker_update_script")
        location = geolocator.geocode(address + ", Israel")
        if location:
            return (location.latitude, location.longitude)
    except:
        pass
    return None

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


def update_hitchhiker_coordinates(collection_prefix=""):
    """
    Update all hitchhiker requests with origin/destination coordinates
    
    Args:
        collection_prefix: Optional prefix for collection name (e.g., "test_")
    """
    logger.info(f"🚀 Starting hitchhiker coordinates update for '{collection_prefix}users'...")
    
    # Initialize Firebase
    try:
        if not firebase_admin._apps:
            firebase_admin.initialize_app()
    except Exception as e:
        logger.error(f"❌ Failed to initialize Firebase: {e}")
        return
    
    db = firestore.Client()
    if not db:
        logger.error("❌ Failed to initialize Firestore")
        return
    
    collection_name = f"{collection_prefix}users"
    users_docs = db.collection(collection_name).stream()
    
    updated_count = 0
    skipped_count = 0
    error_count = 0
    
    for doc in users_docs:
        user_data = doc.to_dict()
        phone = user_data.get("phone_number")
        name = user_data.get("name", "Unknown")
        
        hitchhiker_requests = user_data.get("hitchhiker_requests", [])
        if not hitchhiker_requests:
            continue
        
        logger.info(f"📱 Processing user: {name} ({phone}) - {len(hitchhiker_requests)} requests")
        
        updated = False
        
        for request in hitchhiker_requests:
            request_id = request.get("id")
            origin = request.get("origin", "גברעם")
            destination = request.get("destination")
            
            # Skip if already has coordinates
            if request.get("origin_coordinates") and request.get("destination_coordinates"):
                logger.info(f"   ⏭️  Request {request_id[:8]}... already has coordinates - skipping")
                skipped_count += 1
                continue
            
            if not destination:
                logger.warning(f"   ⚠️  Request {request_id[:8]}... missing destination - skipping")
                error_count += 1
                continue
            
            # Geocode origin and destination
            try:
                logger.info(f"   🗺️  Geocoding: {origin} → {destination}")
                
                origin_coords = simple_geocode(origin)
                dest_coords = simple_geocode(destination)
                
                if origin_coords and dest_coords:
                    request["origin_coordinates"] = list(origin_coords)
                    request["destination_coordinates"] = list(dest_coords)
                    updated = True
                    updated_count += 1
                    logger.info(f"   ✅ Updated request {request_id[:8]}...")
                else:
                    logger.warning(f"   ❌ Failed to geocode - origin_coords={origin_coords}, dest_coords={dest_coords}")
                    error_count += 1
                    
            except Exception as e:
                logger.error(f"   ❌ Error geocoding request {request_id[:8]}: {e}")
                error_count += 1
        
        # Update user document if any requests were updated
        if updated:
            try:
                doc.reference.update({"hitchhiker_requests": hitchhiker_requests})
                logger.info(f"   💾 Saved updates for user {phone}")
            except Exception as e:
                logger.error(f"   ❌ Error saving updates for user {phone}: {e}")
    
    logger.info(f"\n{'='*50}")
    logger.info(f"✅ Update complete!")
    logger.info(f"   Updated: {updated_count}")
    logger.info(f"   Skipped (already had coords): {skipped_count}")
    logger.info(f"   Errors: {error_count}")
    logger.info(f"{'='*50}\n")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Update hitchhiker requests with coordinates")
    parser.add_argument(
        "--collection-prefix",
        default="",
        help="Collection prefix (e.g., 'test_' for test_users)"
    )
    
    args = parser.parse_args()
    
    # Confirm before running
    collection_name = f"{args.collection_prefix}users" if args.collection_prefix else "users"
    print(f"\n⚠️  This will update all hitchhiker requests in '{collection_name}' collection")
    print(f"   Origin and destination will be geocoded and coordinates added")
    
    response = input("\nContinue? (yes/no): ")
    if response.lower() not in ['yes', 'y']:
        print("❌ Cancelled")
        sys.exit(0)
    
    update_hitchhiker_coordinates(args.collection_prefix)

