"""
Firestore database operations
Handles all user data persistence for the hitchhiking bot
"""

import logging
from typing import Optional, Tuple, List, Dict, Any
from google.cloud import firestore
from utils.timezone_utils import israel_now_isoformat

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


async def get_or_create_user(phone_number: str, name: Optional[str] = None) -> Tuple[Dict[str, Any], bool]:
    """
    Get user from Firestore or create if doesn't exist
    
    Args:
        phone_number: User's phone number (document ID)
        name: User's WhatsApp profile name (optional)
    
    Returns:
        tuple: (user_data, is_new_user)
    """
    if not _db:
        return {"phone_number": phone_number, "name": name, "chat_history": []}, False
    
    try:
        doc_ref = _db.collection("users").document(phone_number)
        doc = doc_ref.get()
        
        if doc.exists:
            user_data = doc.to_dict()
            
            # Update name if provided and different from stored name
            if name and user_data.get("name") != name:
                doc_ref.update({"name": name})
                user_data["name"] = name
            
            return user_data, False
        else:
            user_data = {
                "phone_number": phone_number,
                "name": name,
                "notification_level": DEFAULT_NOTIFICATION_LEVEL,
                "driver_rides": [],
                "hitchhiker_requests": [],
                "created_at": israel_now_isoformat(),
                "last_seen": israel_now_isoformat(),
                "chat_history": []
            }
            doc_ref.set(user_data)
            return user_data, True
    except Exception as e:
        logger.error(f"❌ Error getting user: {str(e)}")
        # When DB fails, don't treat as new user to avoid spam
        return {"phone_number": phone_number, "name": name, "chat_history": []}, False


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
            "timestamp": israel_now_isoformat()
        })
        
        # Keep only last N messages
        chat_history = chat_history[-MAX_CHAT_HISTORY:]
        
        doc_ref.update({
            "chat_history": chat_history,
            "last_seen": israel_now_isoformat()
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
            "last_seen": israel_now_isoformat()
        }
        
        if role == "driver":
            update_data["driver_data"] = role_data
        elif role == "hitchhiker":
            update_data["hitchhiker_data"] = role_data
        
        doc_ref.set(update_data, merge=True)
        
        return True
    except Exception as e:
        logger.error(f"❌ Error updating role: {str(e)}")
        return False


async def add_user_ride_or_request(
    phone_number: str,
    ride_type: str,  # 'driver' or 'hitchhiker' to indicate which list to add to
    ride_data: Dict[str, Any],
    collection_prefix: str = ""
) -> Dict[str, Any]:
    """
    Add a new ride offer or hitchhiking request to user's list
    Users can have both driver rides and hitchhiker requests simultaneously
    
    Args:
        phone_number: User's phone number
        ride_type: Type of ride ('driver' or 'hitchhiker')
        ride_data: Data for the new ride/request (must include 'id')
        collection_prefix: Prefix for collection name (e.g., "test_" for sandbox)
    
    Returns:
        Dict with 'success' (bool), 'is_duplicate' (bool), and optional 'message' (str)
    """
    if not _db:
        return {"success": False, "is_duplicate": False, "message": "שגיאת חיבור למסד נתונים"}
    
    try:
        collection_name = f"{collection_prefix}users" if collection_prefix else "users"
        doc_ref = _db.collection(collection_name).document(phone_number)
        doc = doc_ref.get()
        
        if not doc.exists:
            # Create new user
            user_data = {
                "phone_number": phone_number,
                "notification_level": DEFAULT_NOTIFICATION_LEVEL,
                "driver_rides": [ride_data] if ride_type == "driver" else [],
                "hitchhiker_requests": [ride_data] if ride_type == "hitchhiker" else [],
                "created_at": israel_now_isoformat(),
                "last_seen": israel_now_isoformat(),
                "chat_history": []
            }
            doc_ref.set(user_data)
            return {"success": True, "is_duplicate": False}
        
        # Update existing user
        user_data = doc.to_dict()
        
        # Add to appropriate list
        if ride_type == "driver":
            driver_rides = user_data.get("driver_rides", [])
            
            # Check for duplicate (same destination and time)
            is_duplicate = False
            for existing_ride in driver_rides:
                if (existing_ride.get("destination") == ride_data.get("destination") and 
                    existing_ride.get("departure_time") == ride_data.get("departure_time") and
                    existing_ride.get("active", True)):
                    is_duplicate = True
                    destination = ride_data.get("destination", "")
                    origin = ride_data.get("origin", "גברעם")
                    time = ride_data.get("departure_time", "")
                    logger.warning(f"⚠️ Duplicate ride detected for {phone_number}: מ{origin} ל{destination}")
                    break
            
            if not is_duplicate:
                driver_rides.append(ride_data)
                doc_ref.update({
                    "driver_rides": driver_rides,
                    "last_seen": israel_now_isoformat()
                })
            else:
                destination = ride_data.get("destination", "")
                origin = ride_data.get("origin", "גברעם")
                time = ride_data.get("departure_time", "")
                return {
                    "success": False,
                    "is_duplicate": True,
                    "message": f"הנסיעה מ{origin} ל{destination} בשעה {time} כבר קיימת ברשימה שלך! 📋"
                }
        
        elif ride_type == "hitchhiker":
            hitchhiker_requests = user_data.get("hitchhiker_requests", [])
            
            # Check for duplicate (same destination and date/time)
            is_duplicate = False
            for existing_request in hitchhiker_requests:
                if (existing_request.get("destination") == ride_data.get("destination") and 
                    existing_request.get("travel_date") == ride_data.get("travel_date") and
                    existing_request.get("departure_time") == ride_data.get("departure_time") and
                    existing_request.get("active", True)):
                    is_duplicate = True
                    destination = ride_data.get("destination", "")
                    origin = ride_data.get("origin", "גברעם")
                    date = ride_data.get("travel_date", "")
                    logger.warning(f"⚠️ Duplicate request detected for {phone_number}: מ{origin} ל{destination}")
                    break
            
            if not is_duplicate:
                hitchhiker_requests.append(ride_data)
                doc_ref.update({
                    "hitchhiker_requests": hitchhiker_requests,
                    "last_seen": israel_now_isoformat()
                })
            else:
                destination = ride_data.get("destination", "")
                origin = ride_data.get("origin", "גברעם")
                date = ride_data.get("travel_date", "")
                time = ride_data.get("departure_time", "")
                return {
                    "success": False,
                    "is_duplicate": True,
                    "message": f"הבקשה מ{origin} ל{destination} בתאריך {date} בשעה {time} כבר קיימת ברשימה שלך! 📋"
                }
        
        return {"success": True, "is_duplicate": False}
    
    except Exception as e:
        logger.error(f"❌ Error adding ride/request: {str(e)}")
        return {"success": False, "is_duplicate": False, "message": f"שגיאה בשמירה: {str(e)}"}


async def get_user_rides_and_requests(phone_number: str, collection_prefix: str = "") -> Dict[str, Any]:
    """
    Get all active rides and requests for a user
    
    Args:
        phone_number: User's phone number
        collection_prefix: Prefix for collection name (e.g., "test_" for sandbox)
    
    Returns:
        Dictionary with driver_rides and hitchhiker_requests lists
    """
    if not _db:
        return {"driver_rides": [], "hitchhiker_requests": []}
    
    try:
        collection_name = f"{collection_prefix}users" if collection_prefix else "users"
        doc_ref = _db.collection(collection_name).document(phone_number)
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
    ride_id: str,
    collection_prefix: str = ""
) -> bool:
    """
    Remove (deactivate) a specific ride or request by ID
    
    Args:
        phone_number: User's phone number
        role: 'driver' or 'hitchhiker'
        ride_id: The unique ID of the ride/request to remove
        collection_prefix: Optional prefix for collection name (e.g., "test_")
    
    Returns:
        True if successful, False otherwise
    """
    if not _db:
        return False
    
    try:
        collection_name = f"{collection_prefix}users"
        doc_ref = _db.collection(collection_name).document(phone_number)
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
                return True
        
        return False
    
    except Exception as e:
        logger.error(f"❌ Error removing ride/request: {str(e)}")
        return False


async def update_user_ride_or_request(
    phone_number: str,
    role: str,
    ride_id: str,
    updates: Dict[str, Any],
    collection_prefix: str = ""
) -> bool:
    """
    Update specific fields in an existing ride or request by ID
    
    Args:
        phone_number: User's phone number
        role: 'driver' or 'hitchhiker'
        ride_id: The unique ID of the ride/request to update
        updates: Dictionary of fields to update (e.g., {"departure_time": "15:00", "destination": "חיפה"})
        collection_prefix: Prefix for collection name (e.g., "test_" for sandbox)
    
    Returns:
        True if successful, False otherwise
    """
    if not _db:
        return False
    
    try:
        collection_name = f"{collection_prefix}users" if collection_prefix else "users"
        doc_ref = _db.collection(collection_name).document(phone_number)
        doc = doc_ref.get()
        
        if not doc.exists:
            return False
        
        user_data = doc.to_dict()
        
        if role == "driver":
            driver_rides = user_data.get("driver_rides", [])
            updated = False
            for ride in driver_rides:
                if ride.get("id") == ride_id:
                    # Update only the provided fields
                    for key, value in updates.items():
                        ride[key] = value
                    updated = True
                    break
            
            if updated:
                doc_ref.update({"driver_rides": driver_rides})
                logger.info(f"✅ Updated driver ride {ride_id}")
                return True
        
        elif role == "hitchhiker":
            hitchhiker_requests = user_data.get("hitchhiker_requests", [])
            updated = False
            for request in hitchhiker_requests:
                if request.get("id") == ride_id:
                    # Update only the provided fields
                    for key, value in updates.items():
                        request[key] = value
                    updated = True
                    break
            
            if updated:
                doc_ref.update({"hitchhiker_requests": hitchhiker_requests})
                logger.info(f"✅ Updated hitchhiker request {ride_id}")
                return True
        
        return False
    
    except Exception as e:
        logger.error(f"❌ Error updating ride/request: {str(e)}")
        return False


async def get_drivers_by_route(
    origin: Optional[str] = None,
    destination: Optional[str] = None,
    collection_prefix: str = ""
) -> List[Dict[str, Any]]:
    """
    Search for drivers matching specific route
    
    Args:
        origin: Starting location (optional)
        destination: Destination location (optional)
        collection_prefix: Prefix for collection name (e.g., "test_" for sandbox)
    
    Returns:
        List of matching driver records
    """
    if not _db:
        return []
    
    try:
        # Get all users and check their driver_rides
        collection_name = f"{collection_prefix}users" if collection_prefix else "users"
        docs = _db.collection(collection_name).stream()
        
        drivers = []
        for doc in docs:
            user_data = doc.to_dict()
            phone_number = user_data.get("phone_number")
            user_name = user_data.get("name")  # Get driver's name
            
            # Check new list-based structure
            driver_rides = user_data.get("driver_rides", [])
            for ride in driver_rides:
                # Skip inactive rides
                if not ride.get("active", True):
                    continue
                
                # Note: We don't filter by destination here anymore to allow
                # matching based on route proximity (e.g., driver to Tel Aviv
                # can match with hitchhiker to Ashkelon if Ashkelon is on the route)
                
                drivers.append({
                    "phone_number": phone_number,
                    "name": user_name,  # Include driver's name
                    "origin": ride.get("origin", "גברעם"),  # Include origin
                    "destination": ride.get("destination"),
                    "days": ride.get("days", []),
                    "travel_date": ride.get("travel_date"),  # Include travel_date for one-time rides
                    "departure_time": ride.get("departure_time"),
                    "return_time": ride.get("return_time"),
                    "auto_approve_matches": ride.get("auto_approve_matches", True),  # Include approval setting
                    "ride_id": ride.get("id"),
                    # Include route data for on-route matching
                    "route_coordinates_flat": ride.get("route_coordinates_flat"),
                    "route_num_points": ride.get("route_num_points"),
                    "route_distance_km": ride.get("route_distance_km"),
                    "route_threshold_km": ride.get("route_threshold_km"),
                    "route_calculation_pending": ride.get("route_calculation_pending", False)
                })
            
            # Also check legacy driver_data for backward compatibility
            driver_info = user_data.get("driver_data", {})
            if driver_info and driver_info.get("destination"):
                # Note: No destination filtering for legacy data either
                
                drivers.append({
                    "phone_number": phone_number,
                    "name": user_name,  # Include name for legacy data too
                    "origin": driver_info.get("origin", "גברעם"),  # Include origin
                    "destination": driver_info.get("destination"),
                    "days": driver_info.get("days", []),
                    "travel_date": driver_info.get("travel_date"),  # Include travel_date for one-time rides
                    "departure_time": driver_info.get("departure_time"),
                    "return_time": driver_info.get("return_time"),
                    "auto_approve_matches": driver_info.get("auto_approve_matches", True),  # Include approval setting
                    "ride_id": "legacy"
                })
        
        return drivers
    
    except Exception as e:
        logger.error(f"❌ Error searching for drivers: {str(e)}")
        return []


async def get_hitchhiker_requests(
    destination: Optional[str] = None,
    collection_prefix: str = ""
) -> List[Dict[str, Any]]:
    """
    Get hitchhiker requests, optionally filtered by destination
    
    Args:
        destination: Filter by destination (optional)
        collection_prefix: Prefix for collection name (e.g., "test_" for sandbox)
    
    Returns:
        List of hitchhiker records
    """
    if not _db:
        return []
    
    try:
        # Get all users and check their hitchhiker_requests
        collection_name = f"{collection_prefix}users" if collection_prefix else "users"
        docs = _db.collection(collection_name).stream()
        
        hitchhikers = []
        for doc in docs:
            user_data = doc.to_dict()
            phone_number = user_data.get("phone_number")
            user_name = user_data.get("name")  # Get hitchhiker's name
            
            # Check new list-based structure
            hitchhiker_requests = user_data.get("hitchhiker_requests", [])
            for request in hitchhiker_requests:
                # Skip inactive requests
                if not request.get("active", True):
                    continue
                
                # Note: We don't filter by destination here anymore to allow
                # matching based on route proximity (e.g., hitchhiker to Ashkelon
                # can match with driver to Tel Aviv if Ashkelon is on the route)
                
                hitchhikers.append({
                    "phone_number": phone_number,
                    "name": user_name,  # Include hitchhiker's name
                    "origin": request.get("origin", "גברעם"),  # Include origin
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
                    "name": user_name,  # Include name for legacy data too
                    "origin": hitchhiker_info.get("origin", "גברעם"),  # Include origin
                    "destination": hitchhiker_info.get("destination"),
                    "travel_date": hitchhiker_info.get("travel_date"),
                    "departure_time": hitchhiker_info.get("departure_time"),
                    "flexibility": hitchhiker_info.get("flexibility", "flexible"),
                    "request_id": "legacy"
                })
        
        return hitchhikers
    
    except Exception as e:
        logger.error(f"❌ Error searching for hitchhikers: {str(e)}")
        return []


async def update_ride_route_data(
    phone_number: str,
    ride_id: str,
    route_data: Dict,
    collection_prefix: str = ""
) -> bool:
    """
    Update route data for a ride (called from background task or lazy loading)
    
    Args:
        phone_number: User's phone number
        ride_id: Ride ID
        route_data: Dictionary with coordinates, distance_km, threshold_km
        collection_prefix: Prefix for collection name (e.g., "test_" for sandbox)
        
    Returns:
        True if successful, False otherwise
    """
    if not _db:
        logger.warning("⚠️ Database not initialized")
        return False
    
    try:
        collection_name = f"{collection_prefix}users" if collection_prefix else "users"
        doc_ref = _db.collection(collection_name).document(phone_number)
        doc = doc_ref.get()
        
        if not doc.exists:
            logger.warning(f"⚠️ User {phone_number} not found")
            return False
        
        user_data = doc.to_dict()
        driver_rides = user_data.get("driver_rides", [])
        
        updated = False
        for ride in driver_rides:
            if ride.get("id") == ride_id:
                # Flatten coordinates to avoid Firestore nested array limit
                # Convert [(lat1,lon1), (lat2,lon2)] to [lat1,lon1,lat2,lon2]
                flat_coords = []
                for lat, lon in route_data["coordinates"]:
                    flat_coords.extend([lat, lon])
                
                ride["route_coordinates_flat"] = flat_coords  # Flattened array
                ride["route_num_points"] = len(route_data["coordinates"])  # Number of points
                ride["route_distance_km"] = route_data["distance_km"]
                ride["route_threshold_km"] = route_data["threshold_km"]
                ride["route_calculation_pending"] = False  # Mark as complete
                updated = True
                logger.info(f"📍 Saving {len(route_data['coordinates'])} coordinates ({len(flat_coords)} values) to Firestore")
                break
        
        if updated:
            doc_ref.update({"driver_rides": driver_rides})
            logger.info(f"✅ Updated route data for ride {ride_id}: {route_data['distance_km']:.1f}km")
            return True
        else:
            logger.warning(f"⚠️ Ride {ride_id} not found for user {phone_number}")
            return False
        
    except Exception as e:
        logger.error(f"❌ Error updating route data: {e}")
        return False


# ==================== SANDBOX FUNCTIONS ====================
# These functions are used for testing in the admin sandbox environment

async def get_or_create_user_sandbox(phone_number: str, name: str, collection_prefix: str = "test_"):
    """Get or create a user in sandbox/test environment"""
    db = get_db()
    if not db:
        return None, False
    
    collection_name = f"{collection_prefix}users"
    user_ref = db.collection(collection_name).document(phone_number)
    user_doc = user_ref.get()
    
    if user_doc.exists:
        return user_doc.to_dict(), False
    else:
        # Create new test user
        new_user = {
            "phone_number": phone_number,
            "name": name,
            "chat_history": [],
            "driver_rides": [],
            "hitchhiker_rides": [],
            "created_at": israel_now_isoformat(),
            "last_message_at": israel_now_isoformat()
        }
        user_ref.set(new_user)
        logger.info(f"🧪 Created sandbox user: {phone_number} in {collection_name}")
        return new_user, True


async def add_message_to_history_sandbox(phone_number: str, role: str, content: str, collection_prefix: str = "test_"):
    """Add a message to user's chat history in sandbox/test environment"""
    db = get_db()
    if not db:
        return False
    
    collection_name = f"{collection_prefix}users"
    user_ref = db.collection(collection_name).document(phone_number)
    
    message = {
        "role": role,
        "content": content,
        "timestamp": israel_now_isoformat()
    }
    
    try:
        user_doc = user_ref.get()
        if user_doc.exists:
            user_data = user_doc.to_dict()
            chat_history = user_data.get("chat_history", [])
            chat_history.append(message)
            
            # Keep last 100 messages
            if len(chat_history) > 100:
                chat_history = chat_history[-100:]
            
            user_ref.update({
                "chat_history": chat_history,
                "last_message_at": israel_now_isoformat()
            })
            return True
        else:
            logger.warning(f"User {phone_number} not found in {collection_name}")
            return False
    except Exception as e:
        logger.error(f"Error adding message to sandbox history: {e}")
        return False

