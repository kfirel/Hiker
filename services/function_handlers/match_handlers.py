"""
Match-related function handlers
"""

import logging
from typing import Dict, Any

from database import get_user_rides_and_requests
from services.matching_service import find_matches_for_user, format_hitchhiker_info

logger = logging.getLogger(__name__)


async def handle_show_matching_hitchhikers(
    phone_number: str,
    function_args: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Show matching hitchhikers for driver's routes
    
    Args:
        phone_number: User's phone number
        function_args: Optional ride_index to filter
    
    Returns:
        Dictionary with matching hitchhikers
    """
    from database import get_or_create_user
    
    user_data, _ = await get_or_create_user(phone_number)
    
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


async def handle_approve_and_send(
    phone_number: str,
    function_args: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Driver approves sending details to hitchhikers
    
    Args:
        phone_number: User's phone number
        function_args: Optional ride_index to filter
    
    Returns:
        Dictionary with send status
    """
    from database import get_or_create_user
    from services.ai_service import notify_hitchhikers_about_new_driver
    
    user_data, _ = await get_or_create_user(phone_number)
    
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
    total_sent = 0
    
    if ride_index is not None:
        # Send for specific ride
        if 0 <= ride_index < len(driver_rides):
            ride = driver_rides[ride_index]
            matches = await find_matches_for_user("driver", ride)
            
            hitchhikers = matches.get("hitchhikers", [])
            if hitchhikers:
                await notify_hitchhikers_about_new_driver(phone_number, ride, hitchhikers)
                total_sent = len(hitchhikers)
                
                logger.info(f"✅ אושר ונשלח: {total_sent} טרמפיסטים ל-{ride.get('destination')} | נהג: {phone_number}")
                
                return {
                    "success": True,
                    "message": f"Great! Sent your details to {total_sent} hitchhikers for your ride to {ride.get('destination')}",
                    "notifications_sent": total_sent
                }
            else:
                return {
                    "success": True,
                    "message": f"No hitchhikers found for ride to {ride.get('destination')}"
                }
        else:
            return {"success": False, "message": f"Invalid ride index: {ride_index}"}
    
    else:
        # Send for all rides
        for ride in driver_rides:
            matches = await find_matches_for_user("driver", ride)
            hitchhikers = matches.get("hitchhikers", [])
            
            if hitchhikers:
                await notify_hitchhikers_about_new_driver(phone_number, ride, hitchhikers)
                total_sent += len(hitchhikers)
        
        if total_sent > 0:
            logger.info(f"✅ אושר ונשלח: {total_sent} טרמפיסטים (כל הנסיעות) | נהג: {phone_number}")
            
            return {
                "success": True,
                "message": f"Perfect! Sent your details to {total_sent} hitchhikers across all your rides",
                "notifications_sent": total_sent
            }
        else:
            return {
                "success": True,
                "message": "No matching hitchhikers found for any of your rides"
            }

