"""
Matching service
Logic for matching drivers with hitchhikers
"""

import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta

from database import get_drivers_by_route, get_hitchhiker_requests

logger = logging.getLogger(__name__)


def parse_time(time_str: str) -> datetime:
    """Parse time string (HH:MM) to datetime object for comparison"""
    try:
        return datetime.strptime(time_str, "%H:%M")
    except:
        return None


def times_match(time1: str, time2: str, flexibility: str = "flexible") -> bool:
    """
    Check if two times match within flexibility range
    
    Args:
        time1: First time string (HH:MM)
        time2: Second time string (HH:MM)
        flexibility: "flexible" (±5 hours) or "strict" (±1 hour)
    
    Returns:
        True if times match within flexibility range
    """
    if not time1 or not time2:
        return True  # If either time is missing, consider it a match
    
    t1 = parse_time(time1)
    t2 = parse_time(time2)
    
    if not t1 or not t2:
        return True  # If parsing fails, consider it a match
    
    # Determine time window based on flexibility
    if flexibility == "strict":
        window_hours = 1  # ±1 hour
    else:  # "flexible" or any other value
        window_hours = 5  # ±5 hours
    
    # Calculate time difference
    time_diff = abs((t1 - t2).total_seconds() / 3600)  # Convert to hours
    
    return time_diff <= window_hours


def format_driver_info(driver: Dict[str, Any]) -> str:
    """Format driver information for display"""
    phone = driver.get("phone_number", "לא זמין")
    dest = driver.get("destination", "לא צוין")
    time = driver.get("departure_time", "לא צוין")
    days = driver.get("days", [])
    
    days_str = ", ".join(days) if days else "לא צוין"
    
    return f"📞 {phone}\n🎯 {dest}\n🕐 {time}\n📅 {days_str}"


def format_hitchhiker_info(hitchhiker: Dict[str, Any], index: int = None) -> str:
    """Format hitchhiker information for display"""
    phone = hitchhiker.get("phone_number", "לא זמין")
    dest = hitchhiker.get("destination", "לא צוין")
    time = hitchhiker.get("departure_time", "לא צוין")
    date = hitchhiker.get("travel_date", "לא צוין")
    
    prefix = f"{index}️⃣ " if index else ""
    return f"{prefix}📞 {phone}\n🎯 {dest}\n🕐 {time}\n📅 {date}"


async def find_matches_for_user(
    role: str,
    role_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Find matches for a user (driver or hitchhiker)
    
    Args:
        role: User role ('driver' or 'hitchhiker')
        role_data: User's role-specific data
    
    Returns:
        Dictionary with matches found and formatted information
    """
    destination = role_data.get("destination")
    
    if role == "hitchhiker":
        # Find drivers going to same destination
        drivers = await get_drivers_by_route(
            origin="גברעם",
            destination=destination
        )
        
        # Filter by time with flexibility
        hitchhiker_time = role_data.get("departure_time")
        hitchhiker_flexibility = role_data.get("flexibility", "flexible")
        
        matched_drivers = []
        for driver in drivers:
            driver_time = driver.get("departure_time")
            if times_match(hitchhiker_time, driver_time, hitchhiker_flexibility):
                matched_drivers.append(driver)
        
        # Format driver information
        formatted_drivers = []
        for driver in matched_drivers[:5]:  # Return top 5 matches
            formatted_drivers.append({
                "phone_number": driver.get("phone_number"),
                "destination": driver.get("destination"),
                "departure_time": driver.get("departure_time"),
                "days": driver.get("days", []),
                "formatted": format_driver_info(driver)
            })
        
        logger.info(f"🔍 Found {len(matched_drivers)} drivers matching time ±{5 if hitchhiker_flexibility == 'flexible' else 1}h")
        
        return {
            "matches_found": len(matched_drivers),
            "drivers": formatted_drivers,
            "role": "hitchhiker"
        }
    
    elif role == "driver":
        # Find hitchhikers looking for rides to same destination
        hitchhikers = await get_hitchhiker_requests(
            destination=destination
        )
        
        # Filter by time with hitchhiker's flexibility
        driver_time = role_data.get("departure_time")
        
        matched_hitchhikers = []
        for hh in hitchhikers:
            hitchhiker_time = hh.get("departure_time")
            hitchhiker_flexibility = hh.get("flexibility", "flexible")
            if times_match(driver_time, hitchhiker_time, hitchhiker_flexibility):
                matched_hitchhikers.append(hh)
        
        # Format hitchhiker information
        formatted_hitchhikers = []
        for hh in matched_hitchhikers[:5]:  # Return top 5 matches
            formatted_hitchhikers.append({
                "phone_number": hh.get("phone_number"),
                "destination": hh.get("destination"),
                "travel_date": hh.get("travel_date"),
                "departure_time": hh.get("departure_time"),
                "formatted": format_hitchhiker_info(hh)
            })
        
        logger.info(f"🔍 Found {len(matched_hitchhikers)} hitchhikers with matching times")
        
        return {
            "matches_found": len(matched_hitchhikers),
            "hitchhikers": formatted_hitchhikers,
            "role": "driver"
        }
    
    return {
        "matches_found": 0,
        "role": role
    }

