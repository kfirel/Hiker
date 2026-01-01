"""
Intent Detector - Detects if message requires function call
This is a safety net in case AI doesn't call the function
"""

import logging
import re
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def detect_travel_intent(message: str) -> Optional[Dict[str, Any]]:
    """
    Detect if message contains travel intent that requires function call
    This is a FALLBACK in case AI doesn't call the function
    
    Args:
        message: User's message text
    
    Returns:
        Dict with extracted parameters if travel intent detected, None otherwise
    """
    message_lower = message.lower().strip()
    
    # Detect role
    is_driver = any(keyword in message_lower for keyword in [
        "אני נוסע", "אני נוסעת", "אנחנו נוסעים", "נוסע ל", "נוסעת ל"
    ])
    
    is_hitchhiker = any(keyword in message_lower for keyword in [
        "מחפש טרמפ", "מחפשת טרמפ", "צריך טרמפ", "צריכה טרמפ", 
        "רוצה טרמפ", "טרמפ ל"
    ])
    
    if not (is_driver or is_hitchhiker):
        return None
    
    role = "driver" if is_driver else "hitchhiker"
    
    # Extract destination (simple pattern matching)
    # Look for "ל[city]" pattern
    destination_match = re.search(r'ל([א-ת\s]+?)(?:\s|$|ב|מ)', message)
    if not destination_match:
        return None
    
    destination = destination_match.group(1).strip()
    
    # Extract time (HH:MM or just H)
    time_match = re.search(r'\b(\d{1,2}):?(\d{2})?\b', message)
    departure_time = None
    if time_match:
        hour = time_match.group(1)
        minute = time_match.group(2) or "00"
        departure_time = f"{int(hour):02d}:{minute}"
    
    # Detect "every day" / "all days"
    all_days = any(keyword in message_lower for keyword in ["כל יום", "כל הימים"])
    
    days = None
    if all_days and is_driver:
        days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    
    # Detect date keywords for hitchhiker
    travel_date = None
    if is_hitchhiker:
        now = datetime.utcnow()
        if "מחר" in message_lower:
            travel_date = (now + timedelta(days=1)).strftime("%Y-%m-%d")
        elif "היום" in message_lower:
            travel_date = now.strftime("%Y-%m-%d")
    
    # Build result
    result = {
        "role": role,
        "destination": destination,
        "origin": "גברעם"  # Default
    }
    
    if departure_time:
        result["departure_time"] = departure_time
    
    if days:
        result["days"] = days
    
    if travel_date:
        result["travel_date"] = travel_date
    
    logger.info(f"🔍 Intent detected: {result}")
    return result


def should_force_function_call(message: str) -> bool:
    """
    Check if message clearly requires function call but AI might not call it
    
    Examples:
    - "אני נוסעת כל יום לאשקלון ב8" → True (clear travel intent)
    - "כן" → False (not travel intent)
    - "תודה" → False (not travel intent)
    
    Args:
        message: User's message text
    
    Returns:
        True if we should force function call
    """
    intent = detect_travel_intent(message)
    
    if not intent:
        return False
    
    # Check if we have minimum required fields
    has_destination = intent.get("destination") is not None
    has_time = intent.get("departure_time") is not None
    
    return has_destination and has_time

