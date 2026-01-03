"""Matching engine for drivers and hitchhikers"""
import logging
from typing import List, Dict
from datetime import datetime
from rapidfuzz import fuzz

logger = logging.getLogger(__name__)

async def find_matches_for_new_record(role: str, record_data: Dict, collection_prefix: str = "") -> List[Dict]:
    """Main matching function - called after every update"""
    try:
        logger.info(f"🔍 find_matches_for_new_record called:")
        logger.info(f"   Role: {role}")
        logger.info(f"   Destination: {record_data.get('destination')}")
        logger.info(f"   Date: {record_data.get('travel_date')}")
        logger.info(f"   Time: {record_data.get('departure_time')}")
        logger.info(f"   Collection: {collection_prefix or 'production'}")
        
        if role == "driver":
            result = await find_hitchhikers_for_driver(record_data, collection_prefix)
            logger.info(f"✅ find_hitchhikers_for_driver returned {len(result)} matches")
            return result
        elif role == "hitchhiker":
            result = await find_drivers_for_hitchhiker(record_data, collection_prefix)
            logger.info(f"✅ find_drivers_for_hitchhiker returned {len(result)} matches")
            return result
        
        logger.warning(f"⚠️ Unknown role: {role}")
        return []
    except Exception as e:
        logger.error(f"❌ Exception in find_matches_for_new_record: {e}", exc_info=True)
        return []

async def find_drivers_for_hitchhiker(hitchhiker: Dict, collection_prefix: str = "") -> List[Dict]:
    """Hitchhiker looking for ride → search drivers"""
    from database import get_drivers_by_route
    
    dest = hitchhiker["destination"]
    date = hitchhiker.get("travel_date")
    time = hitchhiker["departure_time"]
    
    logger.info(f"🔍 Looking for drivers: dest={dest}, date={date}, time={time}, collection={collection_prefix or 'production'}")
    
    if not date:
        logger.warning(f"⚠️ Hitchhiker missing travel_date: {hitchhiker}")
        return []
    
    drivers = await get_drivers_by_route(destination=dest, collection_prefix=collection_prefix)
    logger.info(f"📊 Found {len(drivers)} potential drivers")
    matches = []
    
    day_name = datetime.strptime(date, "%Y-%m-%d").strftime("%A")
    
    for driver in drivers:
        logger.info(f"  🚗 Checking driver: {driver.get('name', 'Unknown')} to {driver['destination']}")
        
        # 🆕 Check destination compatibility (direct or on-route)
        is_match, match_type, details = await _check_destination_compatibility(
            driver.get("origin", "גברעם"),
            driver["destination"],
            dest,
            driver
        )
        
        if not is_match:
            logger.info(f"    ❌ Destination incompatible")
            continue
        
        logger.info(f"    ✅ Destination match ({match_type})")
        if details:
            driver["_match_details"] = details  # Store for notification
        
        # Check if driver matches - either recurring (days) or one-time (travel_date)
        if driver.get("days"):
            # Recurring driver - check if day matches
            logger.info(f"    📅 Recurring driver, checking day: {day_name} in {driver.get('days')}")
            if day_name not in driver.get("days", []):
                logger.info(f"    ❌ Day not in driver's schedule")
                continue
        elif driver.get("travel_date"):
            # One-time driver - check if date matches
            logger.info(f"    📅 One-time driver, checking date: {date} vs {driver.get('travel_date')}")
            if driver.get("travel_date") != date:
                logger.info(f"    ❌ Date mismatch")
                continue
        else:
            # No days or date - skip
            logger.info(f"    ❌ Driver has no days or travel_date")
            continue
        
        # 🆕 Calculate dynamic time tolerance based on distance and flexibility
        from services.route_service import geocode_address, calculate_distance_between_points
        
        origin_coords = geocode_address(hitchhiker.get("origin", "גברעם"))
        hh_dest_coords = geocode_address(hitchhiker["destination"])
        
        if origin_coords and hh_dest_coords:
            distance_km = calculate_distance_between_points(origin_coords, hh_dest_coords)
            flexibility_level = hitchhiker.get("flexibility", "flexible")
            tolerance = _calculate_time_tolerance(flexibility_level, distance_km)
            
            logger.info(f"    📏 Distance: {distance_km:.1f}km, Flexibility: {flexibility_level} → ±{tolerance} min")
        else:
            tolerance = 30  # Fallback to default
            logger.info(f"    ⚠️ Failed to calculate distance, using default tolerance: ±{tolerance} min")
        
        if not _match_time(time, driver["departure_time"], tolerance):
            logger.info(f"    ❌ Time mismatch: {time} vs {driver['departure_time']} (tolerance: ±{tolerance} min)")
            continue
        if not driver.get("auto_approve_matches", True):
            logger.info(f"    ❌ Driver doesn't auto-approve")
            continue
        
        logger.info(f"    ✅ MATCH FOUND!")
        matches.append(driver)
    
    logger.info(f"Found {len(matches)} drivers for hitchhiker")
    return matches

async def find_hitchhikers_for_driver(driver: Dict, collection_prefix: str = "") -> List[Dict]:
    """Driver offers ride → search hitchhikers"""
    from database import get_hitchhiker_requests
    
    dest = driver["destination"]
    time = driver["departure_time"]
    
    logger.info(f"🔍 Looking for hitchhikers: dest={dest}, days={driver.get('days')}, date={driver.get('travel_date')}, time={time}, collection={collection_prefix or 'production'}")
    
    hitchhikers = await get_hitchhiker_requests(destination=dest, collection_prefix=collection_prefix)
    logger.info(f"📊 Found {len(hitchhikers)} potential hitchhikers")
    matches = []
    
    for hitchhiker in hitchhikers:
        logger.info(f"  🎒 Checking hitchhiker to {hitchhiker['destination']}")
        
        # 🆕 Check destination compatibility (direct or on-route)
        is_match, match_type, details = await _check_destination_compatibility(
            driver.get("origin", "גברעם"),
            dest,
            hitchhiker["destination"],
            driver
        )
        
        if not is_match:
            logger.info(f"    ❌ Destination incompatible")
            continue
        
        logger.info(f"    ✅ Destination match ({match_type})")
        if details:
            hitchhiker["_match_details"] = details  # Store for notification
        
        # Check date/day match
        request_date = hitchhiker.get("travel_date")
        if not request_date:
            logger.info(f"    ❌ Hitchhiker missing travel_date")
            continue
        
        if driver.get("days"):
            # Recurring driver - check if hitchhiker's date falls on driver's days
            day_name = datetime.strptime(request_date, "%Y-%m-%d").strftime("%A")
            logger.info(f"    📅 Recurring driver, checking day: {day_name} in {driver.get('days')}")
            if day_name not in driver.get("days", []):
                logger.info(f"    ❌ Day not in driver's schedule")
                continue
        elif driver.get("travel_date"):
            # One-time driver - check if dates match exactly
            logger.info(f"    📅 One-time driver, checking dates: {driver.get('travel_date')} vs {request_date}")
            if driver.get("travel_date") != request_date:
                logger.info(f"    ❌ Date mismatch")
                continue
        else:
            # No days or date - skip
            logger.info(f"    ❌ Driver has no days or travel_date")
            continue
        
        # 🆕 Calculate dynamic time tolerance based on distance and flexibility
        from services.route_service import geocode_address, calculate_distance_between_points
        
        origin_coords = geocode_address(driver.get("origin", "גברעם"))
        hh_dest_coords = geocode_address(hitchhiker["destination"])
        
        if origin_coords and hh_dest_coords:
            distance_km = calculate_distance_between_points(origin_coords, hh_dest_coords)
            flexibility_level = hitchhiker.get("flexibility", "flexible")
            tolerance = _calculate_time_tolerance(flexibility_level, distance_km)
            
            logger.info(f"    📏 Distance: {distance_km:.1f}km, Flexibility: {flexibility_level} → ±{tolerance} min")
        else:
            tolerance = 30  # Fallback to default
            logger.info(f"    ⚠️ Failed to calculate distance, using default tolerance: ±{tolerance} min")
        
        if not _match_time(time, hitchhiker["departure_time"], tolerance):
            logger.info(f"    ❌ Time mismatch: {time} vs {hitchhiker['departure_time']} (tolerance: ±{tolerance} min)")
            continue
        
        logger.info(f"    ✅ MATCH FOUND!")
        matches.append(hitchhiker)
    
    logger.info(f"Found {len(matches)} hitchhikers for driver")
    return matches

async def send_match_notifications(role: str, matches: List[Dict], new_record: Dict, send_whatsapp: bool = True):
    """Send match notifications"""
    from whatsapp.whatsapp_service import send_whatsapp_message
    
    if not matches:
        logger.info(f"❌ No matches found")
        return
    
    # Skip WhatsApp messages in sandbox mode
    if not send_whatsapp:
        logger.info(f"🧪 Sandbox mode: Found {len(matches)} matches but skipping WhatsApp notifications")
        for match in matches:
            logger.info(f"   Match: {match.get('phone_number')} - {match.get('destination')}")
        return
    
    if role == "driver":
        # Driver added → notify hitchhikers about the driver
        driver_msg = _format_driver_message(new_record)
        for hitchhiker in matches:
            await send_whatsapp_message(hitchhiker["phone_number"], driver_msg)
        
        # Also notify driver about matching hitchhikers
        driver_phone = new_record.get("phone_number")
        for hitchhiker in matches:
            hitchhiker_msg = _format_hitchhiker_message(hitchhiker, new_record.get("destination"))
            await send_whatsapp_message(driver_phone, hitchhiker_msg)
    
    elif role == "hitchhiker":
        # Hitchhiker added → notify hitchhiker about drivers
        hitchhiker_phone = new_record.get("phone_number")
        for driver in matches:
            driver_msg = _format_driver_message(driver)
            await send_whatsapp_message(hitchhiker_phone, driver_msg)
        
        # Also notify drivers about the new hitchhiker
        for driver in matches:
            hitchhiker_msg = _format_hitchhiker_message(new_record, driver.get("destination"))
            await send_whatsapp_message(driver["phone_number"], hitchhiker_msg)

def _match_destination(dest1: str, dest2: str) -> bool:
    """Fuzzy match destinations (80%+ similarity)"""
    return fuzz.ratio(dest1.lower(), dest2.lower()) >= 80


async def _check_destination_compatibility(
    driver_origin: str,
    driver_dest: str,
    hitchhiker_dest: str,
    driver_ride: Dict
) -> tuple:
    """
    Check if destinations are compatible (direct match or on-route)
    
    Returns:
        (is_match: bool, match_type: str, details: Optional[Dict])
    """
    from typing import Optional, Tuple
    
    # 1. Try direct fuzzy match first
    if _match_destination(driver_dest, hitchhiker_dest):
        return True, "exact_match", None
    
    # 2. Check if route data is available
    # Handle both old format (nested arrays) and new format (flat array)
    route_coords = driver_ride.get("route_coordinates")
    
    # If flat format, convert back to pairs
    if not route_coords and driver_ride.get("route_coordinates_flat"):
        flat_coords = driver_ride.get("route_coordinates_flat")
        if flat_coords:  # Make sure we have data
            num_points = driver_ride.get("route_num_points", len(flat_coords) // 2)
            # Convert [lat1,lon1,lat2,lon2] back to [(lat1,lon1), (lat2,lon2)]
            route_coords = [(flat_coords[i], flat_coords[i+1]) for i in range(0, len(flat_coords), 2)]
            logger.info(f"    📍 Loaded route with {len(route_coords)} points from DB")
    
    route_threshold = driver_ride.get("route_threshold_km")
    
    # 🆕 If route calculation is still pending, skip on-route check for now
    if driver_ride.get("route_calculation_pending") and not route_coords:
        logger.info(f"    ⏳ Route calculation still in progress, skipping on-route check")
        return False, None, None
    
    if not route_coords:
        # Lazy loading for old rides without route data
        logger.info(f"    💤 Lazy loading route for {driver_origin} → {driver_dest}")
        from services.route_service import get_route_data
        
        route_data = await get_route_data(driver_origin, driver_dest)
        
        if not route_data:
            logger.info(f"    ❌ Failed to calculate route")
            return False, None, None
        
        # Save for next time
        from database import update_ride_route_data
        await update_ride_route_data(
            driver_ride.get("phone_number"),
            driver_ride.get("id"),
            route_data
        )
        
        route_coords = route_data["coordinates"]
        route_threshold = route_data["threshold_km"]
    
    # 3. Calculate minimum distance from hitchhiker destination to route
    from services.route_service import (
        geocode_address, 
        calculate_min_distance_to_route, 
        calculate_dynamic_threshold,
        calculate_distance_between_points
    )
    
    hitchhiker_coords = geocode_address(hitchhiker_dest)
    if not hitchhiker_coords:
        logger.info(f"    ❌ Failed to geocode hitchhiker destination: {hitchhiker_dest}")
        return False, None, None
    
    # 🆕 Calculate distance from driver origin to hitchhiker destination
    driver_origin_coords = geocode_address(driver_origin)
    if not driver_origin_coords:
        logger.info(f"    ❌ Failed to geocode driver origin: {driver_origin}")
        return False, None, None
    
    distance_from_origin = calculate_distance_between_points(driver_origin_coords, hitchhiker_coords)
    
    # 🆕 Calculate dynamic threshold based on distance from origin
    dynamic_threshold = calculate_dynamic_threshold(distance_from_origin)
    
    # Calculate minimum distance from hitchhiker destination to route
    min_distance = calculate_min_distance_to_route(route_coords, hitchhiker_coords)
    
    logger.info(f"    📏 Distance from origin: {distance_from_origin:.1f}km → threshold: {dynamic_threshold:.1f}km")
    logger.info(f"    📏 Distance from route: {min_distance:.1f}km")
    
    if min_distance <= dynamic_threshold:
        return True, "on_route", {
            "distance": min_distance,
            "threshold": dynamic_threshold,
            "distance_from_origin": distance_from_origin
        }
    
    return False, None, None

def _match_time(time1: str, time2: str, tolerance: int = 30) -> bool:
    """Check if times are close (within tolerance minutes)"""
    try:
        h1, m1 = map(int, time1.split(":"))
        h2, m2 = map(int, time2.split(":"))
        diff = abs((h1 * 60 + m1) - (h2 * 60 + m2))
        return diff <= tolerance
    except:
        return False

def _calculate_time_tolerance(flexibility_level: str, distance_km: float) -> int:
    """
    Calculate time tolerance in minutes based on flexibility level and distance
    
    Formula:
    - strict:         30 minutes (fixed)
    - flexible:       30 + (distance_km / 50) * 30 minutes (max 180 = 3h)
    - very_flexible:  360 minutes (6 hours - fixed!)
    
    Examples:
    - Ashkelon (12km):      strict=±30min, flexible=±37min, very_flexible=±6h
    - Beer Sheva (50km):    strict=±30min, flexible=±60min, very_flexible=±6h
    - Tel Aviv (70km):      strict=±30min, flexible=±72min, very_flexible=±6h
    - Mitzpe Ramon (200km): strict=±30min, flexible=±180min, very_flexible=±6h
    
    Note: very_flexible is ALWAYS 6 hours, regardless of distance!
    This is used when user doesn't specify a time.
    
    Args:
        flexibility_level: 'strict', 'flexible', or 'very_flexible'
        distance_km: Distance from origin to destination (not used for very_flexible)
        
    Returns:
        Tolerance in minutes
    """
    if flexibility_level == "strict":
        return 30  # Always ±30 minutes
    
    elif flexibility_level == "flexible":
        # ±30 + (distance_km / 50) * 30 minutes
        # Example: 200km = ±30 + 4*30 = ±150 minutes (2.5 hours)
        tolerance = 30 + (distance_km / 50) * 30
        return min(int(tolerance), 180)  # Max 3 hours
    
    elif flexibility_level == "very_flexible":
        # Very flexible = always 6 hours (when user doesn't specify time)
        # This gives maximum flexibility for hitchhikers
        return 360  # Always 6 hours
    
    else:
        # Default to very_flexible (if no time specified)
        return 360  # Always 6 hours

def _format_driver_message(driver: Dict) -> str:
    """Format driver match notification"""
    # Day translation map
    DAY_TRANSLATION = {
        "Sunday": "א'",
        "Monday": "ב'",
        "Tuesday": "ג'",
        "Wednesday": "ד'",
        "Thursday": "ה'",
        "Friday": "ו'",
        "Saturday": "ש'"
    }
    
    if driver.get("days"):
        # Recurring driver - translate days to Hebrew
        hebrew_days = [DAY_TRANSLATION.get(d, d[:3]) for d in driver.get("days", [])]
        days_str = ", ".join(hebrew_days)
        time_info = f"ימים: {days_str}"
    elif driver.get("travel_date"):
        # One-time driver
        time_info = f"תאריך: {driver['travel_date']}"
    else:
        time_info = ""
    
    msg = f"""🚗 נמצא נהג!

{driver.get('name', 'נהג')} נוסע ל{driver['destination']}
{time_info}
שעה: {driver['departure_time']}"""
    
    # 🆕 Add on-route information if this is an on-route match
    match_details = driver.get("_match_details")
    if match_details:
        distance = match_details["distance"]
        msg += f"\n\n📍 היעד שלך נמצא בדרך ({distance:.1f} ק\"מ מהמסלול)"
    
    msg += f"""

📱 טלפון: {driver['phone_number']}

בהצלחה! 🙂"""
    
    return msg

def _format_hitchhiker_message(hitchhiker: Dict, destination: str) -> str:
    """Format hitchhiker match notification"""
    # Translate flexibility level to Hebrew
    flexibility_hebrew = {
        "strict": "זמן קבוע ⏰",
        "flexible": "גמיש 🟡",
        "very_flexible": "מאוד גמיש 🟢"
    }
    
    flexibility_level = hitchhiker.get("flexibility", "flexible")
    flex_text = flexibility_hebrew.get(flexibility_level, "גמיש 🟡")
    
    msg = f"""🎒 נמצא טרמפיסט!

{hitchhiker.get('name', 'טרמפיסט')} מחפש/ת נסיעה ל{hitchhiker.get('destination', destination)}
תאריך: {hitchhiker.get('travel_date')}
שעה: {hitchhiker.get('departure_time')}
גמישות: {flex_text}"""
    
    # 🆕 Add on-route information if this is an on-route match
    match_details = hitchhiker.get("_match_details")
    if match_details:
        distance = match_details["distance"]
        msg += f"\n\n📍 היעד שלו/ה בדרך אליך ({distance:.1f} ק\"מ מהמסלול שלך)"
    
    msg += f"""

📱 טלפון: {hitchhiker['phone_number']}

בהצלחה! 🙂"""
    
    return msg
