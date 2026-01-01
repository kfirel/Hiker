"""
Matching service
Logic for matching drivers with hitchhikers
"""

import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta

from database import get_drivers_by_route, get_hitchhiker_requests
from config import DEFAULT_ORIGIN

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
    name = driver.get("name", "")
    phone = driver.get("phone_number", "לא זמין")
    dest = driver.get("destination", "לא צוין")
    time = driver.get("departure_time", "לא צוין")
    days = driver.get("days", [])
    
    days_str = ", ".join(days) if days else "לא צוין"
    
    # Include name if available
    name_line = f"👤 {name}\n" if name else ""
    
    return f"{name_line}📞 {phone}\n🎯 {dest}\n🕐 {time}\n📅 {days_str}"


def format_hitchhiker_info(hitchhiker: Dict[str, Any], index: int = None) -> str:
    """Format hitchhiker information for display"""
    name = hitchhiker.get("name", "")
    phone = hitchhiker.get("phone_number", "לא זמין")
    dest = hitchhiker.get("destination", "לא צוין")
    time = hitchhiker.get("departure_time", "לא צוין")
    date = hitchhiker.get("travel_date", "לא צוין")
    
    prefix = f"{index}️⃣ " if index else ""
    name_line = f"👤 {name}\n" if name else ""
    return f"{prefix}{name_line}📞 {phone}\n🎯 {dest}\n🕐 {time}\n📅 {date}"


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
        hitchhiker_time = role_data.get("departure_time")
        hitchhiker_flexibility = role_data.get("flexibility", "flexible")
        hitchhiker_origin = role_data.get("origin", DEFAULT_ORIGIN)
        
        # Simple matching: Find drivers with matching origin → destination route
        # No special handling needed - return trips are already separate rides!
        drivers = await get_drivers_by_route(
            origin=hitchhiker_origin,
            destination=destination
        )
        
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
                "name": driver.get("name"),
                "destination": driver.get("destination"),
                "departure_time": driver.get("departure_time"),
                "days": driver.get("days", []),
                "auto_approve_matches": driver.get("auto_approve_matches", True),  # Include approval setting
                "formatted": format_driver_info(driver)
            })
        
        flexibility_hours = 5 if hitchhiker_flexibility == 'flexible' else 1
        logger.info(f"🔍 התאמה לטרמפיסט: {len(matched_drivers)} נהגים | מסלול: {hitchhiker_origin} → {destination} | גמישות: ±{flexibility_hours}h")
        
        return {
            "matches_found": len(matched_drivers),
            "drivers": formatted_drivers,
            "role": "hitchhiker"
        }
    
    elif role == "driver":
        driver_time = role_data.get("departure_time")
        driver_origin = role_data.get("origin", DEFAULT_ORIGIN)
        
        # Simple matching: Find hitchhikers going to driver's destination
        # No special handling needed - if driver has a return ride, it's a separate ride entry!
        hitchhikers = await get_hitchhiker_requests(destination=destination)
        
        matched_hitchhikers = []
        for hh in hitchhikers:
            hitchhiker_time = hh.get("departure_time")
            hitchhiker_flexibility = hh.get("flexibility", "flexible")
            # Also check origin matches
            hitchhiker_origin = hh.get("origin", DEFAULT_ORIGIN)
            if hitchhiker_origin == driver_origin and times_match(driver_time, hitchhiker_time, hitchhiker_flexibility):
                matched_hitchhikers.append(hh)
        
        # Format hitchhiker information
        formatted_hitchhikers = []
        for hh in matched_hitchhikers[:5]:  # Return top 5 matches
            formatted_hitchhikers.append({
                "phone_number": hh.get("phone_number"),
                "name": hh.get("name"),
                "destination": hh.get("destination"),
                "travel_date": hh.get("travel_date"),
                "departure_time": hh.get("departure_time"),
                "formatted": format_hitchhiker_info(hh)
            })
        
        logger.info(f"🔍 התאמה לנהג: {len(matched_hitchhikers)} טרמפיסטים | מסלול: {driver_origin} → {destination}")
        
        return {
            "matches_found": len(matched_hitchhikers),
            "hitchhikers": formatted_hitchhikers,
            "role": "driver"
        }
    
    return {
        "matches_found": 0,
        "role": role
    }

