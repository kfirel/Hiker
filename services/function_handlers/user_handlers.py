"""
User-related function handlers
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


async def handle_get_user_info(phone_number: str, function_args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get user's current information from the database
    
    Args:
        phone_number: User's phone number
        function_args: Function arguments (not used)
    
    Returns:
        Dictionary with user info
    """
    from database import get_or_create_user
    
    user_data, _ = await get_or_create_user(phone_number)
    driver_rides = user_data.get("driver_rides", [])
    hitchhiker_requests = user_data.get("hitchhiker_requests", [])
    
    return {
        "success": True,
        "user_info": {
            "phone_number": user_data.get("phone_number"),
            "name": user_data.get("name"),
            "active_driver_rides": len([r for r in driver_rides if r.get("active", True)]),
            "active_hitchhiker_requests": len([r for r in hitchhiker_requests if r.get("active", True)]),
            "created_at": user_data.get("created_at"),
            "last_seen": user_data.get("last_seen")
        }
    }


async def handle_delete_user_data(phone_number: str, function_args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Delete all user data from the database
    
    Args:
        phone_number: User's phone number
        function_args: Function arguments (not used)
    
    Returns:
        Success status
    """
    from database import get_db
    
    db = get_db()
    if not db:
        return {"success": False, "message": "Database not available"}
    
    try:
        db.collection("users").document(phone_number).delete()
        logger.info(f"🗑️  מחיקת משתמש: {phone_number}")
        return {
            "success": True,
            "message": "All your data has been deleted from the system."
        }
    except Exception as e:
        logger.error(f"Error deleting user data: {str(e)}")
        return {"success": False, "message": "Failed to delete data"}

