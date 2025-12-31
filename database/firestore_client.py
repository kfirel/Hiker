"""
Firestore database operations
Handles all user data persistence for the hitchhiking bot
"""

import logging
from datetime import datetime
from typing import Optional, Tuple, List, Dict, Any
from google.cloud import firestore

from config import (
    GOOGLE_CLOUD_PROJECT,
    DEFAULT_NOTIFICATION_LEVEL,
    MAX_CHAT_HISTORY
)

logger = logging.getLogger(__name__)

# Global Firestore client
_db = None


def initialize_db() -> Optional[firestore.Client]:
    """Initialize Firestore client"""
    global _db
    
    try:
        if GOOGLE_CLOUD_PROJECT:
            _db = firestore.Client(project=GOOGLE_CLOUD_PROJECT)
            logger.info(f"✅ Firestore initialized for project: {GOOGLE_CLOUD_PROJECT}")
        else:
            _db = firestore.Client()
            logger.info("✅ Firestore initialized successfully")
        return _db
    except Exception as e:
        logger.error(f"❌ Failed to initialize Firestore: {str(e)}")
        logger.warning("⚠️  Continuing without database...")
        return None


def get_db() -> Optional[firestore.Client]:
    """Get the Firestore client instance"""
    return _db


async def get_or_create_user(phone_number: str) -> Tuple[Dict[str, Any], bool]:
    """
    Get user from Firestore or create if doesn't exist
    
    Args:
        phone_number: User's phone number (document ID)
    
    Returns:
        tuple: (user_data, is_new_user)
    """
    if not _db:
        return {"phone_number": phone_number, "chat_history": []}, False
    
    try:
        doc_ref = _db.collection("users").document(phone_number)
        doc = doc_ref.get()
        
        if doc.exists:
            return doc.to_dict(), False
        else:
            user_data = {
                "phone_number": phone_number,
                "role": None,
                "notification_level": DEFAULT_NOTIFICATION_LEVEL,
                "driver_data": {},
                "hitchhiker_data": {},
                "created_at": datetime.utcnow().isoformat(),
                "last_seen": datetime.utcnow().isoformat(),
                "chat_history": []
            }
            doc_ref.set(user_data)
            logger.info(f"✅ Created new user: {phone_number}")
            return user_data, True
    except Exception as e:
        logger.error(f"❌ Error getting user: {str(e)}")
        # When DB fails, don't treat as new user to avoid spam
        return {"phone_number": phone_number, "chat_history": []}, False


async def add_message_to_history(phone_number: str, role: str, content: str) -> bool:
    """
    Add message to chat history (keep last N messages)
    
    Args:
        phone_number: User's phone number
        role: Message role ('user' or 'assistant')
        content: Message content
    
    Returns:
        True if successful, False otherwise
    """
    if not _db:
        return False
    
    try:
        doc_ref = _db.collection("users").document(phone_number)
        doc = doc_ref.get()
        
        if not doc.exists:
            return False
        
        user_data = doc.to_dict()
        chat_history = user_data.get("chat_history", [])
        
        chat_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Keep only last N messages
        chat_history = chat_history[-MAX_CHAT_HISTORY:]
        
        doc_ref.update({
            "chat_history": chat_history,
            "last_seen": datetime.utcnow().isoformat()
        })
        
        return True
    except Exception as e:
        logger.error(f"❌ Error adding to history: {str(e)}")
        return False


async def update_user_role_and_data(
    phone_number: str,
    role: str,
    role_data: Dict[str, Any]
) -> bool:
    """
    Update user role and data
    
    Args:
        phone_number: User's phone number
        role: User role ('driver' or 'hitchhiker')
        role_data: Data specific to the role
    
    Returns:
        True if successful, False otherwise
    """
    if not _db:
        return False
    
    try:
        doc_ref = _db.collection("users").document(phone_number)
        
        update_data = {
            "role": role,
            "last_seen": datetime.utcnow().isoformat()
        }
        
        if role == "driver":
            update_data["driver_data"] = role_data
        elif role == "hitchhiker":
            update_data["hitchhiker_data"] = role_data
        
        doc_ref.set(update_data, merge=True)
        logger.info(f"✅ Updated {phone_number} as {role}")
        
        return True
    except Exception as e:
        logger.error(f"❌ Error updating role: {str(e)}")
        return False


async def add_user_ride_or_request(
    phone_number: str,
    role: str,
    role_data: Dict[str, Any]
) -> bool:
    """
    Add a new ride offer or hitchhiking request to user's list
    Supports multiple active rides/requests per user
    
    Args:
        phone_number: User's phone number
        role: User role ('driver' or 'hitchhiker')
        role_data: Data for the new ride/request (must include 'id')
    
    Returns:
        True if successful, False otherwise
    """
    if not _db:
        return False
    
    try:
        doc_ref = _db.collection("users").document(phone_number)
        doc = doc_ref.get()
        
        if not doc.exists:
            # Create new user
            user_data = {
                "phone_number": phone_number,
                "role": role,
                "notification_level": DEFAULT_NOTIFICATION_LEVEL,
                "driver_rides": [] if role == "hitchhiker" else [role_data],
                "hitchhiker_requests": [role_data] if role == "hitchhiker" else [],
                "driver_data": {},  # Legacy field
                "hitchhiker_data": {},  # Legacy field
                "created_at": datetime.utcnow().isoformat(),
                "last_seen": datetime.utcnow().isoformat(),
                "chat_history": []
            }
            doc_ref.set(user_data)
            logger.info(f"✅ Created new user {phone_number} with {role} entry")
            return True
        
        # Update existing user
        user_data = doc.to_dict()
        
        # Update role (can be 'driver', 'hitchhiker', or 'both')
        current_role = user_data.get("role")
        if current_role and current_role != role:
            new_role = "both"  # User is both driver and hitchhiker
        else:
            new_role = role
        
        # Add to appropriate list
        if role == "driver":
            driver_rides = user_data.get("driver_rides", [])
            
            # Check for duplicate (same destination and time)
            is_duplicate = False
            for existing_ride in driver_rides:
                if (existing_ride.get("destination") == role_data.get("destination") and 
                    existing_ride.get("departure_time") == role_data.get("departure_time") and
                    existing_ride.get("active", True)):
                    is_duplicate = True
                    logger.warning(f"⚠️ Skipping duplicate ride for {phone_number}: {role_data.get('destination')}")
                    break
            
            if not is_duplicate:
                driver_rides.append(role_data)
                doc_ref.update({
                    "role": new_role,
                    "driver_rides": driver_rides,
                    "last_seen": datetime.utcnow().isoformat()
                })
                logger.info(f"✅ Added driver ride for {phone_number} (total: {len(driver_rides)})")
            else:
                return False  # Duplicate detected
        
        elif role == "hitchhiker":
            hitchhiker_requests = user_data.get("hitchhiker_requests", [])
            
            # Check for duplicate (same destination and date/time)
            is_duplicate = False
            for existing_request in hitchhiker_requests:
                if (existing_request.get("destination") == role_data.get("destination") and 
                    existing_request.get("travel_date") == role_data.get("travel_date") and
                    existing_request.get("departure_time") == role_data.get("departure_time") and
                    existing_request.get("active", True)):
                    is_duplicate = True
                    logger.warning(f"⚠️ Skipping duplicate request for {phone_number}: {role_data.get('destination')}")
                    break
            
            if not is_duplicate:
                hitchhiker_requests.append(role_data)
                doc_ref.update({
                    "role": new_role,
                    "hitchhiker_requests": hitchhiker_requests,
                    "last_seen": datetime.utcnow().isoformat()
                })
                logger.info(f"✅ Added hitchhiker request for {phone_number} (total: {len(hitchhiker_requests)})")
            else:
                return False  # Duplicate detected
        
        return True
    
    except Exception as e:
        logger.error(f"❌ Error adding ride/request: {str(e)}")
        return False


async def get_user_rides_and_requests(phone_number: str) -> Dict[str, Any]:
    """
    Get all active rides and requests for a user
    
    Args:
        phone_number: User's phone number
    
    Returns:
        Dictionary with driver_rides and hitchhiker_requests lists
    """
    if not _db:
        return {"driver_rides": [], "hitchhiker_requests": []}
    
    try:
        doc_ref = _db.collection("users").document(phone_number)
        doc = doc_ref.get()
        
        if not doc.exists:
            return {"driver_rides": [], "hitchhiker_requests": []}
        
        user_data = doc.to_dict()
        driver_rides = [r for r in user_data.get("driver_rides", []) if r.get("active", True)]
        hitchhiker_requests = [r for r in user_data.get("hitchhiker_requests", []) if r.get("active", True)]
        
        return {
            "driver_rides": driver_rides,
            "hitchhiker_requests": hitchhiker_requests
        }
    
    except Exception as e:
        logger.error(f"❌ Error getting user rides/requests: {str(e)}")
        return {"driver_rides": [], "hitchhiker_requests": []}


async def remove_user_ride_or_request(
    phone_number: str,
    role: str,
    ride_id: str
) -> bool:
    """
    Remove (deactivate) a specific ride or request by ID
    
    Args:
        phone_number: User's phone number
        role: 'driver' or 'hitchhiker'
        ride_id: The unique ID of the ride/request to remove
    
    Returns:
        True if successful, False otherwise
    """
    if not _db:
        return False
    
    try:
        doc_ref = _db.collection("users").document(phone_number)
        doc = doc_ref.get()
        
        if not doc.exists:
            return False
        
        user_data = doc.to_dict()
        
        if role == "driver":
            driver_rides = user_data.get("driver_rides", [])
            updated = False
            for ride in driver_rides:
                if ride.get("id") == ride_id:
                    ride["active"] = False
                    updated = True
                    break
            
            if updated:
                doc_ref.update({"driver_rides": driver_rides})
                logger.info(f"✅ Deactivated driver ride {ride_id} for {phone_number}")
                return True
        
        elif role == "hitchhiker":
            hitchhiker_requests = user_data.get("hitchhiker_requests", [])
            updated = False
            for request in hitchhiker_requests:
                if request.get("id") == ride_id:
                    request["active"] = False
                    updated = True
                    break
            
            if updated:
                doc_ref.update({"hitchhiker_requests": hitchhiker_requests})
                logger.info(f"✅ Deactivated hitchhiker request {ride_id} for {phone_number}")
                return True
        
        return False
    
    except Exception as e:
        logger.error(f"❌ Error removing ride/request: {str(e)}")
        return False


async def get_drivers_by_route(
    origin: Optional[str] = None,
    destination: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Search for drivers matching specific route
    
    Args:
        origin: Starting location (optional)
        destination: Destination location (optional)
    
    Returns:
        List of matching driver records
    """
    if not _db:
        return []
    
    try:
        # Get all users (both "driver" and "both" roles)
        docs = _db.collection("users").stream()
        
        drivers = []
        for doc in docs:
            user_data = doc.to_dict()
            role = user_data.get("role")
            
            # Skip if not a driver
            if role not in ["driver", "both"]:
                continue
            
            phone_number = user_data.get("phone_number")
            
            # Check new list-based structure
            driver_rides = user_data.get("driver_rides", [])
            for ride in driver_rides:
                # Skip inactive rides
                if not ride.get("active", True):
                    continue
                
                # Filter by destination (origin is always גברעם)
                if destination and ride.get("destination"):
                    if destination.lower() not in ride["destination"].lower():
                        continue
                
                drivers.append({
                    "phone_number": phone_number,
                    "destination": ride.get("destination"),
                    "days": ride.get("days", []),
                    "departure_time": ride.get("departure_time"),
                    "return_time": ride.get("return_time"),
                    "ride_id": ride.get("id")
                })
            
            # Also check legacy driver_data for backward compatibility
            driver_info = user_data.get("driver_data", {})
            if driver_info and driver_info.get("destination"):
                # Filter by destination
                if destination:
                    if destination.lower() not in driver_info["destination"].lower():
                        continue
                
                drivers.append({
                    "phone_number": phone_number,
                    "destination": driver_info.get("destination"),
                    "days": driver_info.get("days", []),
                    "departure_time": driver_info.get("departure_time"),
                    "return_time": driver_info.get("return_time"),
                    "ride_id": "legacy"
                })
        
        logger.info(f"🚗 Found {len(drivers)} matching drivers")
        return drivers
    
    except Exception as e:
        logger.error(f"❌ Error searching for drivers: {str(e)}")
        return []


async def get_hitchhiker_requests(
    destination: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get hitchhiker requests, optionally filtered by destination
    
    Args:
        destination: Filter by destination (optional)
    
    Returns:
        List of hitchhiker records
    """
    if not _db:
        return []
    
    try:
        # Get all users (both "hitchhiker" and "both" roles)
        docs = _db.collection("users").stream()
        
        hitchhikers = []
        for doc in docs:
            user_data = doc.to_dict()
            role = user_data.get("role")
            
            # Skip if not a hitchhiker
            if role not in ["hitchhiker", "both"]:
                continue
            
            phone_number = user_data.get("phone_number")
            
            # Check new list-based structure
            hitchhiker_requests = user_data.get("hitchhiker_requests", [])
            for request in hitchhiker_requests:
                # Skip inactive requests
                if not request.get("active", True):
                    continue
                
                # Filter by destination
                if destination and request.get("destination"):
                    if destination.lower() not in request["destination"].lower():
                        continue
                
                hitchhikers.append({
                    "phone_number": phone_number,
                    "destination": request.get("destination"),
                    "travel_date": request.get("travel_date"),
                    "departure_time": request.get("departure_time"),
                    "flexibility": request.get("flexibility", "flexible"),
                    "request_id": request.get("id")
                })
            
            # Also check legacy hitchhiker_data for backward compatibility
            hitchhiker_info = user_data.get("hitchhiker_data", {})
            if hitchhiker_info and hitchhiker_info.get("destination"):
                # Filter by destination
                if destination:
                    if destination.lower() not in hitchhiker_info["destination"].lower():
                        continue
                
                hitchhikers.append({
                    "phone_number": phone_number,
                    "destination": hitchhiker_info.get("destination"),
                    "travel_date": hitchhiker_info.get("travel_date"),
                    "departure_time": hitchhiker_info.get("departure_time"),
                    "flexibility": hitchhiker_info.get("flexibility", "flexible"),
                    "request_id": "legacy"
                })
        
        logger.info(f"🚶 Found {len(hitchhikers)} matching hitchhikers")
        return hitchhikers
    
    except Exception as e:
        logger.error(f"❌ Error searching for hitchhikers: {str(e)}")
        return []

