"""Function handlers for AI function calls"""
import logging
from typing import Dict, List
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

def _format_user_records_list(driver_rides: List[Dict], hitchhiker_requests: List[Dict]) -> str:
    """
    Format complete list of user's records with clear numbers
    
    Args:
        driver_rides: List of driver rides
        hitchhiker_requests: List of hitchhiker requests
    
    Returns:
        Formatted string with numbered list
    """
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
    
    if not driver_rides and not hitchhiker_requests:
        return "(אין נסיעות פעילות)"
    
    msg = ""
    
    if driver_rides:
        msg += "🚗 אני נוסע:\n"
        for i, ride in enumerate(driver_rides, 1):
            origin = ride.get("origin", "גברעם")
            destination = ride.get("destination", "")
            
            if ride.get("days"):
                # Translate days to Hebrew
                hebrew_days = [DAY_TRANSLATION.get(d, d) for d in ride.get("days", [])]
                days = ", ".join(hebrew_days)
                time_info = f"ימים: {days}"
            elif ride.get("travel_date"):
                time_info = f"תאריך: {ride['travel_date']}"
            else:
                time_info = ""
            
            msg += f"{i}) מ{origin} ל{destination} - {time_info} בשעה {ride['departure_time']}\n"
    
    if hitchhiker_requests:
        if msg:
            msg += "\n"
        msg += "🎒 צריך/ה טרמפ:\n"
        for i, req in enumerate(hitchhiker_requests, 1):
            origin = req.get("origin", "גברעם")
            destination = req.get("destination", "")
            msg += f"{i}) מ{origin} ל{destination} - {req['travel_date']} בשעה {req['departure_time']}\n"
    
    return msg.strip()

async def handle_update_user_records(phone_number: str, arguments: Dict) -> Dict:
    """Handle update_user_records function call"""
    from database import add_user_ride_or_request, get_or_create_user, get_user_rides_and_requests
    from services.matching_service import find_matches_for_new_record, send_match_notifications
    
    # Get user name
    user_data, _ = await get_or_create_user(phone_number)
    user_name = user_data.get("name", "משתמש")
    
    role = arguments.get("role")
    origin = arguments.get("origin", "גברעם")  # Default to גברעם
    destination = arguments.get("destination")
    departure_time = arguments.get("departure_time", "08:00")
    
    # Check for return trip
    return_trip = arguments.get("return_trip", False)
    return_time = arguments.get("return_time")
    
    if not role or not destination:
        return {"status": "error", "message": "חסר מידע חיוני"}
    
    # Validate return trip
    if return_trip and not return_time:
        return {"status": "error", "message": "נסיעת הלוך-שוב דורשת גם שעת חזרה"}
    
    # Validate that we have either travel_date or days
    has_travel_date = arguments.get("travel_date")
    has_days = arguments.get("days")
    
    if not has_travel_date and not has_days:
        logger.warning(f"⚠️ Missing travel_date and days! Arguments: {arguments}")
        return {"status": "error", "message": "חסר תאריך או ימים"}
    
    def build_record(origin_val, destination_val, departure_time_val):
        """Helper function to build a record"""
        record = {
            "id": str(uuid.uuid4()),
            "origin": origin_val,
            "destination": destination_val,
            "name": user_name,
            "active": True,
            "created_at": datetime.utcnow().isoformat(),
        }
        
        if role == "driver":
            # Driver can have either recurring rides (days) or one-time rides (travel_date)
            if arguments.get("days"):
                # Recurring ride
                record.update({
                    "days": arguments.get("days"),
                    "departure_time": departure_time_val,
                    "auto_approve_matches": arguments.get("auto_approve_matches", True)
                })
            else:
                # One-time ride
                record.update({
                    "travel_date": arguments.get("travel_date"),
                    "departure_time": departure_time_val,
                    "auto_approve_matches": arguments.get("auto_approve_matches", True)
                })
        else:  # hitchhiker
            record.update({
                "travel_date": arguments.get("travel_date"),
                "departure_time": departure_time_val,
                "flexibility": arguments.get("flexibility", "flexible")
            })
        
        return record
    
    # Handle return trip (create TWO records)
    if return_trip and return_time:
        logger.info(f"🔄 Creating return trip: {origin} ↔ {destination}")
        
        # 1. Outbound record
        outbound_record = build_record(origin, destination, departure_time)
        logger.info(f"💾 Saving outbound record: {outbound_record}")
        result1 = await add_user_ride_or_request(phone_number, role, outbound_record)
        
        if not result1.get("success"):
            # If duplicate, return friendly message
            if result1.get("is_duplicate"):
                return {"status": "info", "message": result1.get("message", "הנסיעה כבר קיימת")}
            return {"status": "error", "message": result1.get("message", "שמירת נסיעת הלוך נכשלה")}
        
        # 2. Return record (reversed)
        return_record = build_record(destination, origin, return_time)
        logger.info(f"💾 Saving return record: {return_record}")
        result2 = await add_user_ride_or_request(phone_number, role, return_record)
        
        if not result2.get("success"):
            # If duplicate, return friendly message
            if result2.get("is_duplicate"):
                return {"status": "info", "message": result2.get("message", "הנסיעה כבר קיימת")}
            return {"status": "error", "message": result2.get("message", "שמירת נסיעת חזור נכשלה")}
        
        logger.info(f"✅ Both records saved successfully!")
        
        # Add phone number for matching
        outbound_record["phone_number"] = phone_number
        return_record["phone_number"] = phone_number
        
        # Run matching for BOTH
        logger.info(f"🔍 Starting match search for outbound trip...")
        matches_outbound = await find_matches_for_new_record(role, outbound_record)
        
        logger.info(f"🔍 Starting match search for return trip...")
        matches_return = await find_matches_for_new_record(role, return_record)
        
        # Send notifications
        if matches_outbound:
            await send_match_notifications(role, matches_outbound, outbound_record)
        if matches_return:
            await send_match_notifications(role, matches_return, return_record)
        
        # Build success message
        total_matches = len(matches_outbound) + len(matches_return)
        msg = f"נסיעה הלוך-שוב נשמרה! 🚗\n"
        msg += f"הלוך: מ{origin} ל{destination} בשעה {departure_time}\n"
        msg += f"חזור: מ{destination} ל{origin} בשעה {return_time}"
        
        if total_matches > 0:
            msg += f"\n\n🎯 נמצאו {total_matches} התאמות!"
        
        # Get updated list and append
        data = await get_user_rides_and_requests(phone_number)
        list_msg = _format_user_records_list(
            data.get("driver_rides", []),
            data.get("hitchhiker_requests", [])
        )
        
        msg += f"\n\n📋 הנסיעות שלך עכשיו:\n\n{list_msg}"
        
        return {"status": "success", "message": msg}
    
    # Single trip (existing logic)
    record = build_record(origin, destination, departure_time)
    
    # Save to DB
    logger.info(f"💾 Saving {role} record: {record}")
    result = await add_user_ride_or_request(phone_number, role, record)
    
    if not result.get("success"):
        # If duplicate, return friendly message with current list
        if result.get("is_duplicate"):
            # Get current list
            data = await get_user_rides_and_requests(phone_number)
            list_msg = _format_user_records_list(
                data.get("driver_rides", []),
                data.get("hitchhiker_requests", [])
            )
            duplicate_msg = result.get("message", "הנסיעה כבר קיימת")
            return {"status": "info", "message": f"{duplicate_msg}\n\n📋 הנסיעות שלך עכשיו:\n\n{list_msg}"}
        return {"status": "error", "message": result.get("message", "שמירה נכשלה")}
    
    logger.info(f"✅ Saved successfully!")
    
    # Find matches (always!)
    # Add phone_number and name to record for matching notifications
    record["phone_number"] = phone_number
    record["name"] = user_name
    
    logger.info(f"🔍 Starting match search for {role}...")
    matches = await find_matches_for_new_record(role, record)
    logger.info(f"🎯 Match search complete: {len(matches)} matches found")
    
    # Send notifications
    if matches:
        await send_match_notifications(role, matches, record)
    
    # Success message
    if role == "driver":
        if record.get("days"):
            msg = f"מעולה! הטרמפ הקבוע שלך ל{destination} נשמר 🚗"
        else:
            msg = f"מעולה! הטרמפ שלך ל{destination} נשמר 🚗"
        if matches:
            msg += f"\n✨ כבר נמצאו {len(matches)} טרמפיסטים מתאימים!"
    else:
        msg = f"הבקשה שלך ל{destination} נשמרה! 🎒"
        if matches:
            msg += f"\n🚗 נמצאו {len(matches)} נהגים מתאימים!"
    
    # Get updated list and append
    from database import get_user_rides_and_requests
    data = await get_user_rides_and_requests(phone_number)
    list_msg = _format_user_records_list(
        data.get("driver_rides", []),
        data.get("hitchhiker_requests", [])
    )
    
    msg += f"\n\n📋 הנסיעות שלך עכשיו:\n\n{list_msg}"
    
    return {"status": "success", "message": msg}

async def handle_view_user_records(phone_number: str) -> Dict:
    """Handle view_user_records function call"""
    from database import get_user_rides_and_requests
    
    data = await get_user_rides_and_requests(phone_number)
    drivers = data.get("driver_rides", [])
    hitchhikers = data.get("hitchhiker_requests", [])
    
    if not drivers and not hitchhikers:
        return {"status": "success", "message": "אין לך רשומות פעילות כרגע"}
    
    msg = _format_user_records_list(drivers, hitchhikers)
    return {"status": "success", "message": msg}

async def handle_delete_user_record(phone_number: str, arguments: Dict) -> Dict:
    """Handle delete_user_record function call"""
    from database import remove_user_ride_or_request, get_user_rides_and_requests
    
    record_number = arguments.get("record_number")
    role = arguments.get("role")
    
    if not record_number or not role:
        return {"status": "error", "message": "חסר מספר נסיעה או תפקיד"}
    
    # Get user's records
    data = await get_user_rides_and_requests(phone_number)
    
    if role == "driver":
        records = data.get("driver_rides", [])
        record_type = "טרמפ"
    else:  # hitchhiker
        records = data.get("hitchhiker_requests", [])
        record_type = "בקשה"
    
    # Validate record_number (1-based for user)
    if record_number < 1 or record_number > len(records):
        return {
            "status": "error",
            "message": f"אין {record_type} מספר {record_number} (יש לך {len(records)} {record_type}ים)"
        }
    
    # Get the actual record (0-based array)
    record = records[record_number - 1]
    record_id = record.get("id")
    
    if not record_id:
        return {"status": "error", "message": "שגיאה: הרשומה לא מכילה מזהה"}
    
    # Delete by actual ID
    success = await remove_user_ride_or_request(phone_number, role, record_id)
    
    if not success:
        return {"status": "error", "message": "מחיקה נכשלה"}
    
    # Get updated list
    data = await get_user_rides_and_requests(phone_number)
    list_msg = _format_user_records_list(
        data.get("driver_rides", []),
        data.get("hitchhiker_requests", [])
    )
    
    return {
        "status": "success",
        "message": f"{record_type} {record_number}) נמחק/ה בהצלחה! ✅\n\n📋 הנסיעות שלך עכשיו:\n\n{list_msg}"
    }

async def handle_delete_all_user_records(phone_number: str, arguments: Dict) -> Dict:
    """Handle delete_all_user_records function call - delete all records of a type"""
    from database import remove_user_ride_or_request, get_user_rides_and_requests
    
    role = arguments.get("role")
    
    if not role:
        return {"status": "error", "message": "חסר תפקיד"}
    
    # Get user's records
    data = await get_user_rides_and_requests(phone_number)
    
    if role == "driver":
        records = data.get("driver_rides", [])
        record_type = "טרמפים"
    else:  # hitchhiker
        records = data.get("hitchhiker_requests", [])
        record_type = "בקשות"
    
    if not records:
        return {"status": "success", "message": f"אין לך {record_type} למחוק"}
    
    # Delete all records
    deleted_count = 0
    for record in records:
        record_id = record.get("id")
        if record_id:
            success = await remove_user_ride_or_request(phone_number, role, record_id)
            if success:
                deleted_count += 1
    
    # Get updated list
    data = await get_user_rides_and_requests(phone_number)
    list_msg = _format_user_records_list(
        data.get("driver_rides", []),
        data.get("hitchhiker_requests", [])
    )
    
    if list_msg == "(אין נסיעות פעילות)":
        return {
            "status": "success",
            "message": f"כל ה{record_type} נמחקו בהצלחה! ✅ ({deleted_count} נמחקו)\n\n📋 אין לך נסיעות פעילות"
        }
    
    return {
        "status": "success",
        "message": f"כל ה{record_type} נמחקו בהצלחה! ✅ ({deleted_count} נמחקו)\n\n📋 הנסיעות שלך עכשיו:\n\n{list_msg}"
    }

async def handle_update_user_record(phone_number: str, arguments: Dict) -> Dict:
    """Handle update_user_record function call - update existing ride/request"""
    from database import get_user_rides_and_requests, update_user_ride_or_request
    from services.matching_service import find_matches_for_new_record, send_match_notifications
    
    record_number = arguments.get("record_number")
    role = arguments.get("role")
    
    if not record_number or not role:
        return {"status": "error", "message": "חסר מספר נסיעה או תפקיד"}
    
    # Get user's records
    data = await get_user_rides_and_requests(phone_number)
    
    if role == "driver":
        records = data.get("driver_rides", [])
        record_type = "טרמפ"
    else:  # hitchhiker
        records = data.get("hitchhiker_requests", [])
        record_type = "בקשה"
    
    # Validate record_number (1-based for user)
    if record_number < 1 or record_number > len(records):
        return {
            "status": "error",
            "message": f"אין {record_type} מספר {record_number} (יש לך {len(records)} {record_type}ים)"
        }
    
    # Get the actual record (0-based array)
    record = records[record_number - 1]
    record_id = record.get("id")
    
    if not record_id:
        return {"status": "error", "message": "שגיאה: הרשומה לא מכילה מזהה"}
    
    # Build updates dictionary (only fields that were provided)
    updates = {}
    update_messages = []
    
    if "destination" in arguments:
        updates["destination"] = arguments["destination"]
        update_messages.append(f"יעד → {arguments['destination']}")
    
    if "departure_time" in arguments:
        updates["departure_time"] = arguments["departure_time"]
        update_messages.append(f"שעה → {arguments['departure_time']}")
    
    if "travel_date" in arguments:
        updates["travel_date"] = arguments["travel_date"]
        update_messages.append(f"תאריך → {arguments['travel_date']}")
    
    if "days" in arguments:
        updates["days"] = arguments["days"]
        days_str = ", ".join([d[:3] for d in arguments["days"]])
        update_messages.append(f"ימים → {days_str}")
    
    # Validate that at least one field is being updated
    if not updates:
        return {"status": "error", "message": "לא צוין מה לעדכן (שעה, תאריך, יעד וכו')"}
    
    # Update in DB
    success = await update_user_ride_or_request(phone_number, role, record_id, updates)
    
    if not success:
        return {"status": "error", "message": "עדכון נכשל"}
    
    # Get updated record for matching
    data = await get_user_rides_and_requests(phone_number)
    if role == "driver":
        updated_record = data.get("driver_rides", [])[record_number - 1]
    else:
        updated_record = data.get("hitchhiker_requests", [])[record_number - 1]
    
    # Add phone number for matching
    updated_record["phone_number"] = phone_number
    
    # Re-run matching!
    logger.info(f"🔍 Re-running match search after update...")
    matches = await find_matches_for_new_record(role, updated_record)
    
    if matches:
        await send_match_notifications(role, matches, updated_record)
    
    # Build success message
    update_str = ", ".join(update_messages)
    msg = f"{record_type} {record_number}) עודכן/ה! ✅\n{update_str}"
    
    if matches:
        msg += f"\n\n🎯 נמצאו {len(matches)} התאמות חדשות!"
    
    # Get updated list
    data = await get_user_rides_and_requests(phone_number)
    list_msg = _format_user_records_list(
        data.get("driver_rides", []),
        data.get("hitchhiker_requests", [])
    )
    
    msg += f"\n\n📋 הנסיעות שלך עכשיו:\n\n{list_msg}"
    
    return {"status": "success", "message": msg}
