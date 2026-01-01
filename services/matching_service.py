"""Matching engine for drivers and hitchhikers"""
import logging
from typing import List, Dict
from datetime import datetime
from rapidfuzz import fuzz

logger = logging.getLogger(__name__)

async def find_matches_for_new_record(role: str, record_data: Dict) -> List[Dict]:
    """Main matching function - called after every update"""
    if role == "driver":
        return await find_hitchhikers_for_driver(record_data)
    elif role == "hitchhiker":
        return await find_drivers_for_hitchhiker(record_data)
    return []

async def find_drivers_for_hitchhiker(hitchhiker: Dict) -> List[Dict]:
    """Hitchhiker looking for ride → search drivers"""
    from database import get_drivers_by_route
    
    dest = hitchhiker["destination"]
    date = hitchhiker.get("travel_date")
    time = hitchhiker["departure_time"]
    
    logger.info(f"🔍 Looking for drivers: dest={dest}, date={date}, time={time}")
    
    if not date:
        logger.warning(f"⚠️ Hitchhiker missing travel_date: {hitchhiker}")
        return []
    
    drivers = await get_drivers_by_route(destination=dest)
    logger.info(f"📊 Found {len(drivers)} potential drivers")
    matches = []
    
    day_name = datetime.strptime(date, "%Y-%m-%d").strftime("%A")
    
    for driver in drivers:
        logger.info(f"  🚗 Checking driver: {driver.get('name', 'Unknown')} to {driver['destination']}")
        
        if not _match_destination(dest, driver["destination"]):
            logger.info(f"    ❌ Destination mismatch: {dest} vs {driver['destination']}")
            continue
        
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
        
        if not _match_time(time, driver["departure_time"]):
            logger.info(f"    ❌ Time mismatch: {time} vs {driver['departure_time']}")
            continue
        if not driver.get("auto_approve_matches", True):
            logger.info(f"    ❌ Driver doesn't auto-approve")
            continue
        
        logger.info(f"    ✅ MATCH FOUND!")
        matches.append(driver)
    
    logger.info(f"Found {len(matches)} drivers for hitchhiker")
    return matches

async def find_hitchhikers_for_driver(driver: Dict) -> List[Dict]:
    """Driver offers ride → search hitchhikers"""
    from database import get_hitchhiker_requests
    
    dest = driver["destination"]
    time = driver["departure_time"]
    
    logger.info(f"🔍 Looking for hitchhikers: dest={dest}, days={driver.get('days')}, date={driver.get('travel_date')}, time={time}")
    
    hitchhikers = await get_hitchhiker_requests(destination=dest)
    logger.info(f"📊 Found {len(hitchhikers)} potential hitchhikers")
    matches = []
    
    for hitchhiker in hitchhikers:
        logger.info(f"  🎒 Checking hitchhiker to {hitchhiker['destination']}")
        
        if not _match_destination(dest, hitchhiker["destination"]):
            logger.info(f"    ❌ Destination mismatch")
            continue
        
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
        
        if not _match_time(time, hitchhiker["departure_time"]):
            logger.info(f"    ❌ Time mismatch: {time} vs {hitchhiker['departure_time']}")
            continue
        
        logger.info(f"    ✅ MATCH FOUND!")
        matches.append(hitchhiker)
    
    logger.info(f"Found {len(matches)} hitchhikers for driver")
    return matches

async def send_match_notifications(role: str, matches: List[Dict], new_record: Dict):
    """Send match notifications"""
    from whatsapp.whatsapp_service import send_whatsapp_message
    
    if not matches:
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

def _match_time(time1: str, time2: str, tolerance: int = 30) -> bool:
    """Check if times are close (±30 min)"""
    try:
        h1, m1 = map(int, time1.split(":"))
        h2, m2 = map(int, time2.split(":"))
        diff = abs((h1 * 60 + m1) - (h2 * 60 + m2))
        return diff <= tolerance
    except:
        return False

def _format_driver_message(driver: Dict) -> str:
    """Format driver match notification"""
    if driver.get("days"):
        # Recurring driver
        days_str = ", ".join([d[:3] for d in driver.get("days", [])])
        time_info = f"ימים: {days_str}"
    elif driver.get("travel_date"):
        # One-time driver
        time_info = f"תאריך: {driver['travel_date']}"
    else:
        time_info = ""
    
    return f"""🚗 נמצא נהג!

{driver.get('name', 'נהג')} נוסע ל{driver['destination']}
{time_info}
שעה: {driver['departure_time']}

📱 טלפון: {driver['phone_number']}

בהצלחה! 🙂"""

def _format_hitchhiker_message(hitchhiker: Dict, destination: str) -> str:
    """Format hitchhiker match notification"""
    return f"""🎒 נמצא טרמפיסט!

{hitchhiker.get('name', 'טרמפיסט')} מחפש/ת נסיעה ל{destination}
תאריך: {hitchhiker.get('travel_date')}
שעה: {hitchhiker.get('departure_time')}

📱 טלפון: {hitchhiker['phone_number']}

בהצלחה! 🙂"""
