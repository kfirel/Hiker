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
        # Get all drivers
        docs = _db.collection("users").where("role", "==", "driver").stream()
        
        drivers = []
        for doc in docs:
            driver_data = doc.to_dict()
            driver_info = driver_data.get("driver_data", {})
            
            # Filter by destination (origin is always גברעם)
            if destination and driver_info.get("destination"):
                if destination.lower() not in driver_info["destination"].lower():
                    continue
            
            drivers.append({
                "phone_number": driver_data.get("phone_number"),
                "destination": driver_info.get("destination"),
                "days": driver_info.get("days", []),
                "departure_time": driver_info.get("departure_time"),
                "return_time": driver_info.get("return_time"),
                "available_seats": driver_info.get("available_seats", 3)
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
        # Get all hitchhikers
        docs = _db.collection("users").where("role", "==", "hitchhiker").stream()
        
        hitchhikers = []
        for doc in docs:
            hitchhiker_data = doc.to_dict()
            hitchhiker_info = hitchhiker_data.get("hitchhiker_data", {})
            
            # Filter by destination
            if destination and hitchhiker_info.get("destination"):
                if destination.lower() not in hitchhiker_info["destination"].lower():
                    continue
            
            hitchhikers.append({
                "phone_number": hitchhiker_data.get("phone_number"),
                "destination": hitchhiker_info.get("destination"),
                "travel_date": hitchhiker_info.get("travel_date"),
                "departure_time": hitchhiker_info.get("departure_time"),
                "flexibility": hitchhiker_info.get("flexibility", "flexible")
            })
        
        logger.info(f"🚶 Found {len(hitchhikers)} matching hitchhikers")
        return hitchhikers
    
    except Exception as e:
        logger.error(f"❌ Error searching for hitchhikers: {str(e)}")
        return []

