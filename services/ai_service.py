"""
AI Service - Gemini AI integration
Handles AI-powered conversation and function calling
"""

import logging
import json
from datetime import datetime
from typing import Dict, Any, List

from google import genai
from google.genai import types

from config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    SYSTEM_PROMPT,
    ERROR_MESSAGE_HEBREW,
    MAX_CONVERSATION_CONTEXT,
    DEFAULT_ORIGIN
)
from database import (
    add_message_to_history, 
    update_user_role_and_data, 
    add_user_ride_or_request,
    get_user_rides_and_requests,
    remove_user_ride_or_request
)
from services.whatsapp_service import send_whatsapp_message
from services.matching_service import find_matches_for_user, format_driver_info

logger = logging.getLogger(__name__)


def get_function_tool():
    """Get the function calling tool for Gemini"""
    return types.Tool(
        function_declarations=[
            types.FunctionDeclaration(
                name="update_user_records",
                description="Update user role and structured data in the database. Use this when you have collected enough information about the user.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "role": types.Schema(
                            type=types.Type.STRING,
                            description="User's role - either 'driver' or 'hitchhiker'",
                            enum=["driver", "hitchhiker"]
                        ),
                        "origin": types.Schema(
                            type=types.Type.STRING,
                            description="Starting location - always 'גברעם' (default)"
                        ),
                        "destination": types.Schema(
                            type=types.Type.STRING,
                            description="Destination location (e.g., 'תל אביב', 'חיפה')"
                        ),
                        "days": types.Schema(
                            type=types.Type.ARRAY,
                            description="Days of the week (for drivers)",
                            items=types.Schema(type=types.Type.STRING)
                        ),
                        "departure_time": types.Schema(
                            type=types.Type.STRING,
                            description="Departure time - e.g., '09:00', '17:30'"
                        ),
                        "return_time": types.Schema(
                            type=types.Type.STRING,
                            description="Return time (for drivers who make round trips)"
                        ),
                        "travel_date": types.Schema(
                            type=types.Type.STRING,
                            description="Specific travel date for hitchhikers"
                        ),
                        "flexibility": types.Schema(
                            type=types.Type.STRING,
                            description="Time flexibility for hitchhikers"
                        ),
                        "notes": types.Schema(
                            type=types.Type.STRING,
                            description="Additional notes or preferences"
                        )
                    },
                    required=["role", "destination"]
                )
            ),
            types.FunctionDeclaration(
                name="get_user_info",
                description="Get the user's current information from the database. Use when user asks 'what's my info', 'show my details', or similar.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={}
                )
            ),
            types.FunctionDeclaration(
                name="delete_user_data",
                description="Delete all user data from the database. Use ONLY when user explicitly requests to delete their data or account.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "confirmation": types.Schema(
                            type=types.Type.STRING,
                            description="User's confirmation message"
                        )
                    },
                    required=["confirmation"]
                )
            ),
            types.FunctionDeclaration(
                name="remove_request",
                description="Remove or cancel the user's hitchhiking/driver request. Use when user wants to cancel their request. Can optionally specify destination.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "destination": types.Schema(
                            type=types.Type.STRING,
                            description="Optional: Specific destination to remove (e.g., 'אשקלון', 'תל אביב')"
                        )
                    }
                )
            ),
            types.FunctionDeclaration(
                name="modify_request",
                description="Modify specific fields of the user's existing request without creating a new one.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "destination": types.Schema(
                            type=types.Type.STRING,
                            description="New destination (optional)"
                        ),
                        "departure_time": types.Schema(
                            type=types.Type.STRING,
                            description="New departure time (optional)"
                        ),
                        "travel_date": types.Schema(
                            type=types.Type.STRING,
                            description="New travel date (optional, for hitchhikers)"
                        ),
                        "days": types.Schema(
                            type=types.Type.ARRAY,
                            description="New days of week (optional, for drivers)",
                            items=types.Schema(type=types.Type.STRING)
                        )
                    }
                )
            ),
            types.FunctionDeclaration(
                name="list_my_rides_requests",
                description="List all active rides (if driver) and hitchhiking requests (if hitchhiker) for this user. Use when user asks 'what are my rides', 'show my requests', etc.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={}
                )
            ),
            types.FunctionDeclaration(
                name="remove_ride_request",
                description="Remove a specific ride or request by number. User must specify which one (e.g., 'remove my first ride', 'delete ride number 2').",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "role": types.Schema(
                            type=types.Type.STRING,
                            description="Type of entry to remove: 'driver' or 'hitchhiker'",
                            enum=["driver", "hitchhiker"]
                        ),
                        "index": types.Schema(
                            type=types.Type.INTEGER,
                            description="The index/number of the ride or request to remove (0-based)"
                        )
                    },
                    required=["role", "index"]
                )
            ),
            types.FunctionDeclaration(
                name="show_matching_hitchhikers",
                description="Show matching hitchhikers for a driver's routes. Use when driver asks 'who is looking for a ride', 'show me hitchhikers', 'give me hitchhiker details', etc.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "ride_index": types.Schema(
                            type=types.Type.INTEGER,
                            description="Optional: Index of specific ride to check (0-based). If not provided, checks all active rides."
                        )
                    }
                )
            )
        ]
    )


async def notify_hitchhikers_about_new_driver(
    driver_phone: str,
    driver_data: Dict[str, Any],
    hitchhikers: List[Dict[str, Any]]
) -> None:
    """
    Send WhatsApp notifications to hitchhikers about a new matching driver
    
    Args:
        driver_phone: Driver's phone number
        driver_data: Driver's route information
        hitchhikers: List of matching hitchhikers
    """
    if not hitchhikers:
        return
    
    # Filter out the driver's own phone number (in case they're also a hitchhiker)
    filtered_hitchhikers = [h for h in hitchhikers if h.get("phone_number") != driver_phone]
    
    if not filtered_hitchhikers:
        logger.info(f"⚠️ No hitchhikers to notify (driver {driver_phone} was filtered out)")
        return
    
    # Format driver information for the notification
    driver_info_dict = {
        "phone_number": driver_phone,
        "destination": driver_data.get("destination"),
        "departure_time": driver_data.get("departure_time"),
        "days": driver_data.get("days", []),
        "return_time": driver_data.get("return_time")
    }
    
    formatted_driver = format_driver_info(driver_info_dict)
    
    # Create notification message
    destination = driver_data.get("destination", "")
    notification = f"""🚗 נהג חדש נוסע ל{destination}!

{formatted_driver}

צור קשר איתו ישירות! 📲"""
    
    # Send notification to each hitchhiker (excluding the driver)
    for hitchhiker in filtered_hitchhikers:
        hitchhiker_phone = hitchhiker.get("phone_number")
        if hitchhiker_phone:
            try:
                await send_whatsapp_message(hitchhiker_phone, notification)
                logger.info(f"📤 Sent notification to hitchhiker {hitchhiker_phone}")
            except Exception as e:
                logger.error(f"❌ Failed to notify hitchhiker {hitchhiker_phone}: {str(e)}")


async def execute_function_call(
    function_name: str,
    function_args: Dict[str, Any],
    phone_number: str
) -> Dict[str, Any]:
    """
    Execute AI function call
    
    Args:
        function_name: Name of the function to execute
        function_args: Arguments for the function
        phone_number: User's phone number
    
    Returns:
        Result dictionary
    """
    try:
        if function_name == "update_user_records":
            role = function_args.get("role")
            
            # Build role data (origin is always גברעם)
            import uuid
            from datetime import datetime as dt
            
            role_data = {}
            if role == "driver":
                role_data = {
                    "id": str(uuid.uuid4()),  # Unique ID for this ride
                    "origin": DEFAULT_ORIGIN,
                    "destination": function_args.get("destination"),
                    "days": function_args.get("days", []),
                    "departure_time": function_args.get("departure_time"),
                    "return_time": function_args.get("return_time"),
                    "notes": function_args.get("notes", ""),
                    "created_at": dt.utcnow().isoformat(),
                    "active": True
                }
            elif role == "hitchhiker":
                role_data = {
                    "id": str(uuid.uuid4()),  # Unique ID for this request
                    "origin": DEFAULT_ORIGIN,
                    "destination": function_args.get("destination"),
                    "travel_date": function_args.get("travel_date"),
                    "departure_time": function_args.get("departure_time"),
                    "flexibility": function_args.get("flexibility", "flexible"),
                    "notes": function_args.get("notes", ""),
                    "created_at": dt.utcnow().isoformat(),
                    "active": True
                }
            
            # Add to user's list (supports multiple rides/requests)
            success = await add_user_ride_or_request(phone_number, role, role_data)
            
            if not success:
                return {"success": False, "message": "Failed to update user records"}
            
            # Find matches for both roles, but handle differently
            if role == "hitchhiker":
                # Hitchhiker: Show them matching drivers
                matches = await find_matches_for_user(role, role_data)
                return {
                    "success": True,
                    "message": f"User registered as {role}",
                    "role": role,
                    "data": role_data,
                    **matches
                }
            else:  # driver
                # Driver: Find matching hitchhikers and notify them
                matches = await find_matches_for_user(role, role_data)
                
                # Send notifications to matching hitchhikers
                if matches.get("matches_found", 0) > 0:
                    hitchhikers = matches.get("hitchhikers", [])
                    await notify_hitchhikers_about_new_driver(
                        phone_number,
                        role_data,
                        hitchhikers
                    )
                    logger.info(f"🔔 Notified {len(hitchhikers)} hitchhikers about new driver {phone_number}")
                
                # Don't show matches to the driver
                return {
                    "success": True,
                    "message": f"User registered as {role}",
                    "role": role,
                    "data": role_data,
                    "matches_found": 0,  # Don't show matches to drivers
                    "notifications_sent": matches.get("matches_found", 0)
                }
        
        elif function_name == "get_user_info":
            # Get user's current info from database
            from database import get_or_create_user
            user_data, _ = await get_or_create_user(phone_number)
            
            return {
                "success": True,
                "user_info": {
                    "phone_number": user_data.get("phone_number"),
                    "role": user_data.get("role"),
                    "driver_data": user_data.get("driver_data", {}),
                    "hitchhiker_data": user_data.get("hitchhiker_data", {}),
                    "created_at": user_data.get("created_at"),
                    "last_seen": user_data.get("last_seen")
                }
            }
        
        elif function_name == "delete_user_data":
            # Delete all user data
            from database import get_db
            db = get_db()
            if not db:
                return {"success": False, "message": "Database not available"}
            
            try:
                db.collection("users").document(phone_number).delete()
                logger.info(f"🗑️  User {phone_number} deleted their data")
                return {
                    "success": True,
                    "message": "All your data has been deleted from the system."
                }
            except Exception as e:
                logger.error(f"Error deleting user data: {str(e)}")
                return {"success": False, "message": "Failed to delete data"}
        
        elif function_name == "remove_request":
            # Remove user's request/ride - smart detection with optional destination filter
            from database import get_db, get_or_create_user
            
            user_data, _ = await get_or_create_user(phone_number)
            role = user_data.get("role")
            
            if not role or role not in ["driver", "hitchhiker", "both"]:
                return {"success": False, "message": "You don't have any active requests"}
            
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
                new_role = role
                
                if destination_filter:
                    # Try to find and remove specific destination
                    found = False
                    
                    # Check hitchhiker requests first (most common)
                    for request in hitchhiker_requests:
                        if destination_filter.lower() in request.get("destination", "").lower():
                            request["active"] = False
                            removed_item = f"hitchhiker request to {request.get('destination')}"
                            found = True
                            break
                    
                    # If not found in hitchhiker requests, check driver rides
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
                        # Multiple active items - remove the most recent one based on role
                        if role == "hitchhiker" and hitchhiker_requests:
                            request = hitchhiker_requests[-1]
                            request["active"] = False
                            removed_item = f"hitchhiker request to {request.get('destination')}"
                        elif role == "driver" and driver_rides:
                            ride = driver_rides[-1]
                            ride["active"] = False
                            removed_item = f"driver ride to {ride.get('destination')}"
                        elif role == "both":
                            if hitchhiker_requests:
                                request = hitchhiker_requests[-1]
                                request["active"] = False
                                removed_item = f"hitchhiker request to {request.get('destination')}"
                            elif driver_rides:
                                ride = driver_rides[-1]
                                ride["active"] = False
                                removed_item = f"driver ride to {ride.get('destination')}"
                
                # Determine new role based on remaining active items
                active_drivers = [r for r in driver_rides if r.get("active", True)]
                active_hitchhikers = [r for r in hitchhiker_requests if r.get("active", True)]
                
                if active_drivers and active_hitchhikers:
                    new_role = "both"
                elif active_drivers:
                    new_role = "driver"
                elif active_hitchhikers:
                    new_role = "hitchhiker"
                else:
                    new_role = None
                
                # Update database
                doc_ref = db.collection("users").document(phone_number)
                update_data = {
                    "role": new_role,
                    "driver_rides": driver_rides,
                    "hitchhiker_requests": hitchhiker_requests
                }
                
                # Clear legacy fields if no active rides/requests
                if not active_drivers:
                    update_data["driver_data"] = {}
                if not active_hitchhikers:
                    update_data["hitchhiker_data"] = {}
                
                doc_ref.update(update_data)
                
                logger.info(f"🗑️  User {phone_number} removed {removed_item}")
                
                remaining = len(active_drivers) + len(active_hitchhikers)
                
                return {
                    "success": True,
                    "message": f"Removed {removed_item}." + (f" You have {remaining} active requests/rides remaining." if remaining > 0 else ""),
                    "removed_item": removed_item,
                    "remaining_count": remaining
                }
            except Exception as e:
                logger.error(f"Error removing request: {str(e)}", exc_info=True)
                return {"success": False, "message": "Failed to remove request"}
        
        elif function_name == "modify_request":
            # Modify user's existing request
            from database import get_or_create_user, get_db
            user_data, _ = await get_or_create_user(phone_number)
            role = user_data.get("role")
            
            if not role:
                return {
                    "success": False,
                    "message": "No active request to modify"
                }
            
            db = get_db()
            if not db:
                return {"success": False, "message": "Database not available"}
            
            try:
                # Get current role data
                if role == "driver":
                    current_data = user_data.get("driver_data", {})
                    # Update only provided fields
                    if "destination" in function_args:
                        current_data["destination"] = function_args["destination"]
                    if "departure_time" in function_args:
                        current_data["departure_time"] = function_args["departure_time"]
                    if "days" in function_args:
                        current_data["days"] = function_args["days"]
                    
                    db.collection("users").document(phone_number).update({
                        "driver_data": current_data
                    })
                    
                elif role == "hitchhiker":
                    current_data = user_data.get("hitchhiker_data", {})
                    # Update only provided fields
                    if "destination" in function_args:
                        current_data["destination"] = function_args["destination"]
                    if "departure_time" in function_args:
                        current_data["departure_time"] = function_args["departure_time"]
                    if "travel_date" in function_args:
                        current_data["travel_date"] = function_args["travel_date"]
                    
                    db.collection("users").document(phone_number).update({
                        "hitchhiker_data": current_data
                    })
                
                logger.info(f"✏️  User {phone_number} modified their request")
                
                # Find new matches after modification
                matches = await find_matches_for_user(role, current_data)
                
                return {
                    "success": True,
                    "message": "Your request has been updated.",
                    "modified_data": current_data,
                    **matches
                }
            except Exception as e:
                logger.error(f"Error modifying request: {str(e)}")
                return {"success": False, "message": "Failed to modify request"}
        
        elif function_name == "list_my_rides_requests":
            # List all active rides and requests for the user
            rides_and_requests = await get_user_rides_and_requests(phone_number)
            driver_rides = rides_and_requests.get("driver_rides", [])
            hitchhiker_requests = rides_and_requests.get("hitchhiker_requests", [])
            
            # Format for display
            result = {
                "driver_rides_count": len(driver_rides),
                "hitchhiker_requests_count": len(hitchhiker_requests),
                "driver_rides": driver_rides,
                "hitchhiker_requests": hitchhiker_requests
            }
            
            logger.info(f"📋 Listed rides/requests for {phone_number}: {len(driver_rides)} rides, {len(hitchhiker_requests)} requests")
            return result
        
        elif function_name == "remove_ride_request":
            # Remove a specific ride or request by index
            role = function_args.get("role")
            index = function_args.get("index", 0)
            
            # Get current rides/requests
            rides_and_requests = await get_user_rides_and_requests(phone_number)
            
            if role == "driver":
                driver_rides = rides_and_requests.get("driver_rides", [])
                if 0 <= index < len(driver_rides):
                    ride_to_remove = driver_rides[index]
                    ride_id = ride_to_remove.get("id")
                    success = await remove_user_ride_or_request(phone_number, "driver", ride_id)
                    if success:
                        return {
                            "success": True,
                            "message": f"Removed driver ride to {ride_to_remove.get('destination')}",
                            "removed_ride": ride_to_remove
                        }
                else:
                    return {"success": False, "message": f"Invalid ride number: {index}"}
            
            elif role == "hitchhiker":
                hitchhiker_requests = rides_and_requests.get("hitchhiker_requests", [])
                if 0 <= index < len(hitchhiker_requests):
                    request_to_remove = hitchhiker_requests[index]
                    request_id = request_to_remove.get("id")
                    success = await remove_user_ride_or_request(phone_number, "hitchhiker", request_id)
                    if success:
                        return {
                            "success": True,
                            "message": f"Removed hitchhiker request to {request_to_remove.get('destination')}",
                            "removed_request": request_to_remove
                        }
                else:
                    return {"success": False, "message": f"Invalid request number: {index}"}
            
            return {"success": False, "message": "Failed to remove ride/request"}
        
        elif function_name == "show_matching_hitchhikers":
            # Show matching hitchhikers for driver's routes
            from database import get_or_create_user
            from services.matching_service import format_hitchhiker_info
            
            user_data, _ = await get_or_create_user(phone_number)
            
            # Check if user is a driver
            if user_data.get("role") not in ["driver", "both"]:
                return {
                    "success": False,
                    "message": "You need to be registered as a driver to see matching hitchhikers"
                }
            
            # Get user's active rides
            rides_and_requests = await get_user_rides_and_requests(phone_number)
            driver_rides = rides_and_requests.get("driver_rides", [])
            
            if not driver_rides:
                return {
                    "success": False,
                    "message": "You don't have any active driver rides"
                }
            
            # Get ride index if specified
            ride_index = function_args.get("ride_index")
            
            if ride_index is not None:
                # Show hitchhikers for specific ride
                if 0 <= ride_index < len(driver_rides):
                    ride = driver_rides[ride_index]
                    matches = await find_matches_for_user("driver", ride)
                    
                    hitchhikers = matches.get("hitchhikers", [])
                    if hitchhikers:
                        formatted_list = []
                        for i, hh in enumerate(hitchhikers, 1):
                            formatted_list.append(format_hitchhiker_info(hh, i))
                        
                        return {
                            "success": True,
                            "message": f"Found {len(hitchhikers)} matching hitchhikers for ride to {ride.get('destination')}",
                            "hitchhikers": hitchhikers,
                            "formatted": formatted_list
                        }
                    else:
                        return {
                            "success": True,
                            "message": f"No hitchhikers found for ride to {ride.get('destination')}"
                        }
                else:
                    return {"success": False, "message": f"Invalid ride index: {ride_index}"}
            else:
                # Show hitchhikers for all rides
                all_hitchhikers = []
                results_by_ride = []
                
                for i, ride in enumerate(driver_rides):
                    matches = await find_matches_for_user("driver", ride)
                    hitchhikers = matches.get("hitchhikers", [])
                    
                    if hitchhikers:
                        results_by_ride.append({
                            "ride_destination": ride.get("destination"),
                            "ride_time": ride.get("departure_time"),
                            "hitchhikers_count": len(hitchhikers),
                            "hitchhikers": hitchhikers
                        })
                        
                        # Add formatted info
                        for hh in hitchhikers:
                            if hh not in all_hitchhikers:
                                all_hitchhikers.append(hh)
                
                if all_hitchhikers:
                    formatted_list = []
                    for i, hh in enumerate(all_hitchhikers, 1):
                        formatted_list.append(format_hitchhiker_info(hh, i))
                    
                    return {
                        "success": True,
                        "message": f"Found {len(all_hitchhikers)} total matching hitchhikers across all your rides",
                        "total_hitchhikers": len(all_hitchhikers),
                        "results_by_ride": results_by_ride,
                        "formatted": formatted_list
                    }
                else:
                    return {
                        "success": True,
                        "message": "No matching hitchhikers found for any of your rides"
                    }
        
        return {"success": False, "message": f"Unknown function: {function_name}"}
    
    except Exception as e:
        logger.error(f"❌ Error executing function: {str(e)}")
        return {"success": False, "message": str(e)}


async def process_message_with_ai(
    phone_number: str,
    message: str,
    user_data: Dict[str, Any],
    is_new_user: bool = False
) -> None:
    """
    Process user message with Gemini AI
    
    Args:
        phone_number: User's phone number
        message: User's message text
        user_data: User's data from database
        is_new_user: Whether this is a new user
    """
    try:
        if not GEMINI_API_KEY:
            # Fallback without AI
            response = f"קיבלתי: {message}\n(AI לא מופעל)"
            await send_whatsapp_message(phone_number, response)
            return
        
        # Add user message to history
        await add_message_to_history(phone_number, "user", message)
        
        # Get current context
        now = datetime.utcnow()
        current_timestamp = now.strftime("%Y-%m-%d %H:%M:%S UTC")
        current_day_of_week = now.strftime("%A")
        
        # Build system prompt with context
        system_prompt = SYSTEM_PROMPT.format(
            current_timestamp=current_timestamp,
            current_day_of_week=current_day_of_week
        )
        
        # Build conversation history
        chat_history = user_data.get("chat_history", [])
        conversation = []
        
        for msg in chat_history[-MAX_CONVERSATION_CONTEXT:]:  # Last N messages
            if msg["role"] == "user":
                conversation.append({"role": "user", "parts": [msg["content"]]})
            elif msg["role"] == "assistant":
                conversation.append({"role": "model", "parts": [msg["content"]]})
        
        # Initialize Gemini client
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        # Create config with tools
        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            tools=[get_function_tool()],
            temperature=0.7
        )
        
        # Build message history for API
        history = []
        for msg in conversation[:-1]:
            history.append(types.Content(
                role=msg["role"],
                parts=[types.Part(text=msg["parts"][0])]
            ))
        
        # Add current message
        history.append(types.Content(
            role="user",
            parts=[types.Part(text=message)]
        ))
        
        # Generate response with function calling
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=history,
            config=config
        )
        
        # Check for function calls
        function_calls_found = []
        if response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'function_call') and part.function_call:
                    function_calls_found.append(part.function_call)
        
        # If function calls were made, execute them and get final response
        if function_calls_found:
            # Collect all function responses
            function_responses = []
            
            for function_call in function_calls_found:
                function_name = function_call.name
                function_args = dict(function_call.args)
                
                # Convert RepeatedComposite (protobuf) to list for JSON serialization
                for key, value in function_args.items():
                    if hasattr(value, '__iter__') and not isinstance(value, (str, dict)):
                        function_args[key] = list(value)
                
                logger.info(f"🤖 AI called function: {function_name}")
                logger.info(f"   Args: {json.dumps(function_args, ensure_ascii=False)}")
                
                # Execute function
                result = await execute_function_call(function_name, function_args, phone_number)
                
                # Add to function responses
                function_responses.append(types.Part(
                    function_response=types.FunctionResponse(
                        name=function_name,
                        response={"result": result}
                    )
                ))
            
            # Send all function results back to AI for continuation
            history.append(response.candidates[0].content)
            history.append(types.Content(
                role="user",
                parts=function_responses
            ))
            
            # Get final response from AI
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=history,
                config=config
            )
        
        # Get final text response
        try:
            ai_response = response.text if hasattr(response, 'text') and response.text else ""
        except Exception as e:
            logger.warning(f"⚠️ Error getting text from response: {e}")
            ai_response = ""
        
        # Log response
        if ai_response:
            logger.info(f"🤖 AI response: {ai_response[:100]}...")
            
            # Send to user
            await send_whatsapp_message(phone_number, ai_response)
            
            # Add to history
            await add_message_to_history(phone_number, "assistant", ai_response)
        else:
            logger.warning(f"⚠️ AI returned no text response for {phone_number}")
            # Send a default message
            default_message = "הבקשה שלך התקבלה ונשמרה במערכת! ✅"
            await send_whatsapp_message(phone_number, default_message)
            await add_message_to_history(phone_number, "assistant", default_message)
    
    except Exception as e:
        logger.error(f"❌ Error in AI processing: {str(e)}", exc_info=True)
        await send_whatsapp_message(phone_number, ERROR_MESSAGE_HEBREW)

