"""
Google Cloud Firestore database operations
Handles all user data persistence for the hitchhiking bot
"""

import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

logger = logging.getLogger(__name__)

# Firestore client (initialized on startup)
db = None

def initialize_firestore():
    """Initialize Firestore client"""
    global db
    try:
        # Firestore will use GOOGLE_APPLICATION_CREDENTIALS env var
        db = firestore.Client()
        logger.info("Firestore client initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Firestore: {str(e)}")
        raise


async def get_user(phone_number: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve user data from Firestore
    
    Args:
        phone_number: User's phone number (document ID)
    
    Returns:
        User data dictionary or None if user doesn't exist
    """
    try:
        doc_ref = db.collection("users").document(phone_number)
        doc = doc_ref.get()
        
        if doc.exists:
            user_data = doc.to_dict()
            logger.info(f"Retrieved user data for {phone_number}")
            return user_data
        else:
            logger.info(f"User {phone_number} not found")
            return None
    
    except Exception as e:
        logger.error(f"Error getting user {phone_number}: {str(e)}")
        return None


async def update_user(phone_number: str, user_data: Dict[str, Any]) -> bool:
    """
    Update or create user data in Firestore
    
    Args:
        phone_number: User's phone number (document ID)
        user_data: Dictionary containing user data to update
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Update last_seen timestamp
        user_data["last_seen"] = datetime.utcnow().isoformat()
        
        doc_ref = db.collection("users").document(phone_number)
        doc_ref.set(user_data, merge=True)
        
        logger.info(f"Updated user data for {phone_number}")
        return True
    
    except Exception as e:
        logger.error(f"Error updating user {phone_number}: {str(e)}")
        return False


async def add_message_to_history(
    phone_number: str, 
    role: str, 
    content: str, 
    max_history: int = 5
) -> bool:
    """
    Add a message to user's chat history (keep last N messages)
    
    Args:
        phone_number: User's phone number
        role: Message role ('user' or 'assistant')
        content: Message content
        max_history: Maximum number of messages to keep (default: 5)
    
    Returns:
        True if successful, False otherwise
    """
    try:
        doc_ref = db.collection("users").document(phone_number)
        doc = doc_ref.get()
        
        if not doc.exists:
            logger.warning(f"User {phone_number} not found when adding message")
            return False
        
        user_data = doc.to_dict()
        chat_history = user_data.get("chat_history", [])
        
        # Add new message
        chat_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Keep only last N messages
        chat_history = chat_history[-max_history:]
        
        # Update Firestore
        doc_ref.update({"chat_history": chat_history})
        logger.info(f"Added message to history for {phone_number}")
        
        return True
    
    except Exception as e:
        logger.error(f"Error adding message to history for {phone_number}: {str(e)}")
        return False


async def get_drivers_by_route(
    origin: Optional[str] = None,
    destination: Optional[str] = None,
    days: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Search for drivers matching specific criteria
    
    Args:
        origin: Starting location
        destination: Destination location
        days: List of days (e.g., ['Sunday', 'Monday'])
    
    Returns:
        List of matching driver records
    """
    try:
        query = db.collection("users").where(filter=FieldFilter("role", "==", "driver"))
        
        drivers = []
        docs = query.stream()
        
        for doc in docs:
            driver_data = doc.to_dict()
            driver_info = driver_data.get("driver_data", {})
            
            # Basic filtering (can be enhanced with more sophisticated matching)
            if origin and driver_info.get("origin"):
                if origin.lower() not in driver_info["origin"].lower():
                    continue
            
            if destination and driver_info.get("destination"):
                if destination.lower() not in driver_info["destination"].lower():
                    continue
            
            if days and driver_info.get("days"):
                driver_days = driver_info["days"]
                if not any(day in driver_days for day in days):
                    continue
            
            drivers.append(driver_data)
        
        logger.info(f"Found {len(drivers)} matching drivers")
        return drivers
    
    except Exception as e:
        logger.error(f"Error searching for drivers: {str(e)}")
        return []


async def get_hitchhiker_requests(
    destination: Optional[str] = None,
    active_only: bool = True
) -> List[Dict[str, Any]]:
    """
    Get hitchhiker requests, optionally filtered by destination
    
    Args:
        destination: Filter by destination
        active_only: Only return recent/active requests
    
    Returns:
        List of hitchhiker records
    """
    try:
        query = db.collection("users").where(filter=FieldFilter("role", "==", "hitchhiker"))
        
        hitchhikers = []
        docs = query.stream()
        
        for doc in docs:
            hitchhiker_data = doc.to_dict()
            hitchhiker_info = hitchhiker_data.get("hitchhiker_data", {})
            
            # Filter by destination if provided
            if destination and hitchhiker_info.get("destination"):
                if destination.lower() not in hitchhiker_info["destination"].lower():
                    continue
            
            hitchhikers.append(hitchhiker_data)
        
        logger.info(f"Found {len(hitchhikers)} hitchhiker requests")
        return hitchhikers
    
    except Exception as e:
        logger.error(f"Error getting hitchhiker requests: {str(e)}")
        return []


async def update_user_role_and_data(
    phone_number: str,
    role: str,
    role_data: Dict[str, Any]
) -> bool:
    """
    Update user role and associated data (driver_data or hitchhiker_data)
    
    Args:
        phone_number: User's phone number
        role: User role ('driver' or 'hitchhiker')
        role_data: Data specific to the role
    
    Returns:
        True if successful, False otherwise
    """
    try:
        doc_ref = db.collection("users").document(phone_number)
        
        update_data = {
            "role": role,
            "last_seen": datetime.utcnow().isoformat()
        }
        
        if role == "driver":
            update_data["driver_data"] = role_data
        elif role == "hitchhiker":
            update_data["hitchhiker_data"] = role_data
        
        doc_ref.set(update_data, merge=True)
        logger.info(f"Updated role and data for {phone_number}: {role}")
        
        return True
    
    except Exception as e:
        logger.error(f"Error updating role for {phone_number}: {str(e)}")
        return False


