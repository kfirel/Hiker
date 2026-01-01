"""
Ride/Request-related function handlers
"""

import logging
import uuid
from datetime import datetime as dt
from typing import Dict, Any

from config import DEFAULT_ORIGIN
from database import add_user_ride_or_request, get_user_rides_and_requests, remove_user_ride_or_request
from services.matching_service import find_matches_for_user

logger = logging.getLogger(__name__)


async def handle_update_user_records(
    phone_number: str,
    function_args: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Create new ride or hitchhiker request
    
    Args:
        phone_number: User's phone number
        function_args: Function arguments with ride/request details
    
    Returns:
        Dictionary with success status and matches
    """
    from services.ai_service import notify_hitchhikers_about_new_driver
    
    role = function_args.get("role")
    role_data = {}
    
    if role == "driver":
        # Get approval preference (default: True = auto-approve)
        auto_approve = function_args.get("auto_approve_matches", True)
        
        # Create outbound ride
        outbound_ride = {
            "id": str(uuid.uuid4()),
            "origin": function_args.get("origin", DEFAULT_ORIGIN),
            "destination": function_args.get("destination"),
            "days": function_args.get("days", []),
            "departure_time": function_args.get("departure_time"),
            "return_time": None,
            "notes": function_args.get("notes", ""),
            "auto_approve_matches": auto_approve,
            "created_at": dt.utcnow().isoformat(),
            "active": True
        }
        
        # Add outbound ride
        success = await add_user_ride_or_request(phone_number, role, outbound_ride)
        if not success:
            return {"success": False, "message": "Failed to save outbound ride"}
        
        role_data = outbound_ride
        
        # If driver has return_time, create a SEPARATE return ride
        return_time = function_args.get("return_time")
        if return_time:
            return_ride = {
                "id": str(uuid.uuid4()),
                "origin": function_args.get("destination"),
                "destination": function_args.get("origin", DEFAULT_ORIGIN),
                "days": function_args.get("days", []),
                "departure_time": return_time,
                "return_time": None,
                "notes": function_args.get("notes", "") + " (חזרה)" if function_args.get("notes") else "(חזרה)",
                "auto_approve_matches": auto_approve,
                "created_at": dt.utcnow().isoformat(),
                "active": True
            }
            
            success_return = await add_user_ride_or_request(phone_number, role, return_ride)
            if success_return:
                logger.info(f"↩️ נסיעת חזור: {return_ride['destination']} בשעה {return_time}")
    
    elif role == "hitchhiker":
        role_data = {
            "id": str(uuid.uuid4()),
            "origin": function_args.get("origin", DEFAULT_ORIGIN),
            "destination": function_args.get("destination"),
            "travel_date": function_args.get("travel_date"),
            "departure_time": function_args.get("departure_time"),
            "flexibility": function_args.get("flexibility", "flexible"),
            "notes": function_args.get("notes", ""),
            "created_at": dt.utcnow().isoformat(),
            "active": True
        }
        
        success = await add_user_ride_or_request(phone_number, role, role_data)
        if not success:
            return {"success": False, "message": "Failed to update user records"}
    
    # Find matches for both roles
    if role == "hitchhiker":
        # Hitchhiker: Find matching drivers and notify them
        matches = await find_matches_for_user(role, role_data)
        drivers = matches.get("drivers", [])
        
        # Use approval service to handle all notifications
        from services.approval_service import notify_drivers_about_hitchhiker
        
        notification_result = await notify_drivers_about_hitchhiker(
            hitchhiker_phone=phone_number,
            hitchhiker_data=role_data,
            matching_drivers=drivers
        )
        
        auto_sent = notification_result.get("auto_sent", 0)
        pending_approval = notification_result.get("pending_approval", 0)
        
        logger.info(f"📊 Hitchhiker notifications: {auto_sent} auto-sent, {pending_approval} pending approval")
        
        # Build response text in CODE (not AI!)
        if auto_sent > 0 and pending_approval > 0:
            response_text = f"נשמר! מצאתי {auto_sent + pending_approval} נהגים:\n"
            response_text += f"• {auto_sent} נהגים נשלחו אליך\n"
            response_text += f"• {pending_approval} נהגים קיבלו את הבקשה ויענו בקרוב"
        elif auto_sent > 0:
            response_text = f"מעולה! מצאתי {auto_sent} נהגים מתאימים"
        elif pending_approval > 0:
            response_text = f"נשמר! שלחתי את הבקשה ל-{pending_approval} נהגים. נעדכן אותך כשיאשרו 👍"
        else:
            response_text = "נשמר! נעדכן אותך כשיופיע נהג מתאים"
        
        return {
            "success": True,
            "message": response_text,  # Ready-made response!
            "data": role_data,
            "auto_sent": auto_sent,
            "pending_approval": pending_approval,
            "role": "hitchhiker"
        }
    
    else:  # driver
        # Driver: Find matching hitchhikers
        matches = await find_matches_for_user(role, role_data)
        auto_approve = role_data.get("auto_approve_matches", True)
        notifications_sent = 0
        
        if matches.get("matches_found", 0) > 0:
            hitchhikers = matches.get("hitchhikers", [])
            
            if auto_approve:
                # Auto-approve: Send notifications immediately
                await notify_hitchhikers_about_new_driver(phone_number, role_data, hitchhikers)
                notifications_sent = len(hitchhikers)
                
                return {
                    "success": True,
                    "message": f"Driver ride saved. Your details were automatically sent to {notifications_sent} matching hitchhikers.",
                    "data": role_data,
                    "matches_found": 0,
                    "notifications_sent": notifications_sent
                }
            else:
                # Manual approval required - ASK the driver explicitly
                logger.info(f"⏸️  אישור ידני: נמצאו {len(hitchhikers)} טרמפיסטים | נהג: {phone_number}")
                
                return {
                    "success": True,
                    "message": f"DRIVER APPROVAL REQUIRED: Found {len(hitchhikers)} matching hitchhikers. You MUST ask the driver: 'רוצה שאשלח את הפרטים שלך ל-{len(hitchhikers)} טרמפיסטים מתאימים?' Wait for their confirmation before sending.",
                    "data": role_data,
                    "matches_found": len(hitchhikers),
                    "pending_approval": True,
                    "notifications_sent": 0,
                    "requires_confirmation": True  # Signal to AI to ask
                }
        else:
            # No matches found
            return {
                "success": True,
                "message": "Driver ride saved. No matching hitchhikers found yet.",
                "data": role_data,
                "matches_found": 0,
                "notifications_sent": 0
            }


async def handle_modify_request(phone_number: str, function_args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Modify existing ride/request (deprecated - use remove + add instead)
    
    Args:
        phone_number: User's phone number
        function_args: Function arguments
    
    Returns:
        Dictionary with status
    """
    from database import get_or_create_user
    
    user_data, _ = await get_or_create_user(phone_number)
    driver_rides = user_data.get("driver_rides", [])
    hitchhiker_requests = user_data.get("hitchhiker_requests", [])
    
    if not driver_rides and not hitchhiker_requests:
        return {
            "success": False,
            "message": "No active rides or requests to modify. Please use remove_request to delete and then create a new one."
        }
    
    return {
        "success": False,
        "message": "To modify a ride/request, please first remove it using 'remove my ride' and then add a new one. This ensures accurate matching."
    }


async def handle_remove_request(phone_number: str, function_args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove user's ride or request with smart detection
    
    Args:
        phone_number: User's phone number
        function_args: Optional destination filter
    
    Returns:
        Dictionary with success status
    """
    from database import get_db, get_or_create_user
    
    user_data, _ = await get_or_create_user(phone_number)
    db = get_db()
    
    if not db:
        return {"success": False, "message": "Database not available"}
    
    try:
        # Get current rides and requests
        rides_and_requests = await get_user_rides_and_requests(phone_number)
        driver_rides = rides_and_requests.get("driver_rides", [])
        hitchhiker_requests = rides_and_requests.get("hitchhiker_requests", [])
        
        total_active = len(driver_rides) + len(hitchhiker_requests)
        
        if total_active == 0:
            return {"success": False, "message": "You don't have any active requests"}
        
        # Check if destination was specified
        destination_filter = function_args.get("destination")
        removed_item = None
        
        if destination_filter:
            # Try to find and remove specific destination
            found = False
            
            for request in hitchhiker_requests:
                if destination_filter.lower() in request.get("destination", "").lower():
                    request["active"] = False
                    removed_item = f"hitchhiker request to {request.get('destination')}"
                    found = True
                    break
            
            if not found:
                for ride in driver_rides:
                    if destination_filter.lower() in ride.get("destination", "").lower():
                        ride["active"] = False
                        removed_item = f"driver ride to {ride.get('destination')}"
                        found = True
                        break
            
            if not found:
                return {
                    "success": False,
                    "message": f"No active request/ride found for destination: {destination_filter}"
                }
        else:
            # No destination specified - smart removal logic
            if total_active == 1:
                # Only 1 active - remove it
                if hitchhiker_requests:
                    request = hitchhiker_requests[0]
                    request["active"] = False
                    removed_item = f"hitchhiker request to {request.get('destination')}"
                else:
                    ride = driver_rides[0]
                    ride["active"] = False
                    removed_item = f"driver ride to {ride.get('destination')}"
            else:
                # Multiple active - ask for clarification
                destinations = []
                if driver_rides:
                    destinations.extend([f"driver: {r.get('destination')}" for r in driver_rides])
                if hitchhiker_requests:
                    destinations.extend([f"hitchhiker: {r.get('destination')}" for r in hitchhiker_requests])
                
                return {
                    "success": False,
                    "message": f"You have {total_active} active rides/requests. Please specify which one to remove: {', '.join(destinations)}"
                }
        
        # Update database
        doc_ref = db.collection("users").document(phone_number)
        doc_ref.update({
            "driver_rides": driver_rides,
            "hitchhiker_requests": hitchhiker_requests
        })
        
        logger.info(f"🗑️  בוטל: {removed_item} | משתמש: {phone_number}")
        
        return {
            "success": True,
            "message": f"Removed: {removed_item}"
        }
        
    except Exception as e:
        logger.error(f"Error removing request: {str(e)}", exc_info=True)
        return {"success": False, "message": "Failed to remove request"}

