"""Function handlers for AI function calls"""
import logging
from typing import Dict, List
import uuid
from datetime import timedelta
from utils.timezone_utils import israel_now_isoformat

logger = logging.getLogger(__name__)

def _normalize_location(value: str) -> str:
    return value.strip().lower().replace('"', "").replace("'", "")

def _is_gvaram_location(value: str) -> bool:
    if not value:
        return False
    normalized = _normalize_location(value)
    return "גברעם" in normalized or "gvaram" in normalized

def _infer_travel_date_from_time(time_str: str) -> str:
    from utils import get_israel_now
    try:
        hours, minutes = map(int, time_str.split(":"))
    except Exception:
        return ""
    now = get_israel_now()
    candidate = now.replace(hour=hours, minute=minutes, second=0, microsecond=0)
    if candidate <= now:
        candidate = candidate + timedelta(days=1)
    return candidate.strftime("%Y-%m-%d")

def _round_flex_minutes(minutes: int) -> str:
    """
    Round flexibility to clean hours or minutes for display.
    """
    if minutes >= 60:
        hours = max(1, int(round(minutes / 60)))
        return f"{hours} ש'"
    rounded = max(10, int(round(minutes / 10)) * 10)
    return f"{rounded} דק'"

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
        return ""
    
    msg = ""
    
    # 🔄 Reverse lists so newest items appear first
    driver_rides_reversed = list(reversed(driver_rides))
    hitchhiker_requests_reversed = list(reversed(hitchhiker_requests))
    
    if driver_rides:
        msg += "🚗 אני נוסע:\n"
        for i, ride in enumerate(driver_rides_reversed, 1):
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
        
        # Import functions for flexibility calculation
        from services.route_service import geocode_address, calculate_distance_between_points
        from services.matching_service import _calculate_time_tolerance
        
        for i, req in enumerate(hitchhiker_requests_reversed, 1):
            origin = req.get("origin", "גברעם")
            destination = req.get("destination", "")
            flexibility_level = req.get("flexibility", "flexible")
            
            # Calculate actual time tolerance
            origin_coords = geocode_address(origin)
            dest_coords = geocode_address(destination)
            
            if origin_coords and dest_coords:
                distance_km = calculate_distance_between_points(origin_coords, dest_coords)
                tolerance_minutes = _calculate_time_tolerance(flexibility_level, distance_km)
                
                # Format flexibility text with emoji
                if flexibility_level == "strict":
                    flex_emoji = "🔒"
                    flex_text = "זמן קבוע, ±30 דק'"
                elif flexibility_level == "very_flexible":
                    flex_emoji = "🟢"
                    flex_text = "מאוד גמיש, ±6 ש'"
                else:  # flexible
                    flex_emoji = "🟡"
                    flex_text = f"גמיש, ±{_round_flex_minutes(tolerance_minutes)}"
            else:
                # Fallback if geocoding fails
                if flexibility_level == "strict":
                    flex_emoji = "🔒"
                    flex_text = "זמן קבוע, ±30 דק'"
                elif flexibility_level == "very_flexible":
                    flex_emoji = "🟢"
                    flex_text = "מאוד גמיש, ±6 ש'"
                else:
                    flex_emoji = "🟡"
                    flex_text = "גמיש"
            
            travel_date = req.get("travel_date") or "ללא תאריך"
            msg += f"{i}) מ{origin} ל{destination} - {travel_date} בשעה {req['departure_time']} {flex_emoji} ({flex_text})\n"
    
    return msg.strip()

def find_conflict(user_data: dict, role: str, destination: str, travel_date: str) -> dict:
    """
    Find conflicting records (driver vs hitchhiker for same destination+date).
    
    Args:
        user_data: User data dictionary with rides and requests
        role: The role being created ("driver" or "hitchhiker")
        destination: Destination to check
        travel_date: Date to check (YYYY-MM-DD)
    
    Returns:
        dict with conflict info if found, None otherwise
    """
    opposite_role = "hitchhiker" if role == "driver" else "driver"
    opposite_key = "hitchhiker_requests" if opposite_role == "hitchhiker" else "driver_rides"
    
    records = user_data.get(opposite_key, [])
    for idx, record in enumerate(records):
        record_dest = record.get("destination", "").strip()
        record_date = record.get("travel_date", "")
        
        # Normalize destinations for comparison
        if record_dest.lower() == destination.lower() and record_date == travel_date:
            return {
                "role": opposite_role,
                "record_number": idx + 1,
                "destination": record_dest,
                "date": record_date,
                "time": record.get("departure_time", "")
            }
    
    return None

async def handle_update_user_records(phone_number: str, arguments: Dict, collection_prefix: str = "", send_whatsapp: bool = True) -> Dict:
    """Handle update_user_records function call"""
    from database import add_user_ride_or_request, get_user_rides_and_requests
    from services.matching_service import find_matches_for_new_record, send_match_notifications
    
    # Get user name (from the sandbox user data if in sandbox mode)
    if collection_prefix:
        # Sandbox mode - get from test collection
        user_data = await get_user_rides_and_requests(phone_number, collection_prefix)
        # Try to get name from first query, or use default
        from database import get_db
        db = get_db()
        if db:
            doc = db.collection(f"{collection_prefix}users").document(phone_number).get()
            if doc.exists:
                user_name = doc.to_dict().get("name", "משתמש")
            else:
                user_name = "משתמש"
        else:
            user_name = "משתמש"
    else:
        # Production mode - use regular function
        from database import get_or_create_user
        user_data, _ = await get_or_create_user(phone_number)
        user_name = user_data.get("name", "משתמש")
    
    role = arguments.get("role")
    origin = arguments.get("origin", "גברעם")  # Default to גברעם
    destination = arguments.get("destination")
    departure_time = arguments.get("departure_time")
    
    # Check for return trip
    return_trip = arguments.get("return_trip", False)
    return_time = arguments.get("return_time")
    
    if not role or not destination:
        return {"status": "error", "message": "חסר מידע חיוני"}
    
    if not departure_time:
        return {"status": "error", "message": "באיזו שעה? (למשל: בשעה 8, בבוקר, בערב)"}
    
    # Validate return trip
    if return_trip and not return_time:
        return {"status": "error", "message": "נסיעת הלוך-שוב דורשת גם שעת חזרה"}
    
    # Validate that we have either travel_date or days
    has_travel_date = arguments.get("travel_date")
    has_days = arguments.get("days")
    
    if not has_travel_date and not has_days:
        inferred_date = _infer_travel_date_from_time(departure_time)
        if inferred_date:
            arguments["travel_date"] = inferred_date
            has_travel_date = inferred_date
        else:
            logger.warning(f"⚠️ Missing travel_date and days! Arguments: {arguments}")
            return {"status": "error", "message": "חסר תאריך או ימים"}

    # Enforce Gvaram-only origin/destination
    if not (_is_gvaram_location(origin) or _is_gvaram_location(destination)):
        return {
            "status": "error",
            "message": "המערכת תומכת רק בנסיעות מ/אל גברעם. האם אתה יוצא מגברעם או מגיע לגברעם?"
        }
    
    # NEW: Check for conflicts (only for one-time trips with travel_date)
    travel_date = arguments.get("travel_date")
    if travel_date:
        conflict = find_conflict(user_data, role, destination, travel_date)
        if conflict:
            return (
                f"DUPLICATE_CONFLICT|{role}|{conflict['role']}|{destination}|{travel_date}|"
                f"{departure_time}|{conflict['record_number']}"
            )
    
    def build_record(origin_val, destination_val, departure_time_val):
        """Helper function to build a record"""
        record = {
            "id": str(uuid.uuid4()),
            "origin": origin_val,
            "destination": destination_val,
            "name": user_name,
            "active": True,
            "created_at": israel_now_isoformat(),
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
            
            # 🆕 Initialize route data placeholders (will be calculated in background)
            record.update({
                "route_coordinates": None,
                "route_distance_km": None,
                "route_threshold_km": None,
                "route_calculation_pending": True
            })
        else:  # hitchhiker
            record.update({
                "travel_date": arguments.get("travel_date"),
                "departure_time": departure_time_val,
                "flexibility": arguments.get("flexibility", "flexible")  # Default: flexible (±1h based on distance)
            })
            
            # 🗺️ Geocode origin and destination for map display
            try:
                from services.route_service import geocode_address
                origin_coords = geocode_address(origin_val)
                dest_coords = geocode_address(destination_val)
                
                if origin_coords and dest_coords:
                    record["origin_coordinates"] = origin_coords
                    record["destination_coordinates"] = dest_coords
                    logger.info(f"📍 Geocoded hitchhiker locations: {origin_val} → {destination_val}")
                else:
                    logger.warning(f"⚠️ Could not geocode hitchhiker locations")
            except Exception as e:
                logger.error(f"❌ Error geocoding hitchhiker locations: {e}")
        
        return record
    
    # Handle return trip (create TWO records)
    if return_trip and return_time:
        logger.info(f"🔄 Creating return trip: {origin} ↔ {destination}")
        
        # 1. Outbound record
        outbound_record = build_record(origin, destination, departure_time)
        logger.info(f"💾 Saving outbound record: {outbound_record}")
        result1 = await add_user_ride_or_request(phone_number, role, outbound_record, collection_prefix)
        
        if not result1.get("success"):
            # If duplicate, return friendly message
            if result1.get("is_duplicate"):
                return {"status": "info", "message": result1.get("message", "הנסיעה כבר קיימת")}
            return {"status": "error", "message": result1.get("message", "שמירת נסיעת הלוך נכשלה")}
        
        # 2. Return record (reversed)
        return_record = build_record(destination, origin, return_time)
        logger.info(f"💾 Saving return record: {return_record}")
        result2 = await add_user_ride_or_request(phone_number, role, return_record, collection_prefix)
        
        if not result2.get("success"):
            # If duplicate, return friendly message
            if result2.get("is_duplicate"):
                return {"status": "info", "message": result2.get("message", "הנסיעה כבר קיימת")}
            return {"status": "error", "message": result2.get("message", "שמירת נסיעת חזור נכשלה")}
        
        logger.info(f"✅ Both records saved successfully!")
        
        # 🆕 Start background route calculations (fire-and-forget)
        if role == "driver":
            import asyncio
            from services.route_service import calculate_and_save_route_background
            
            asyncio.create_task(calculate_and_save_route_background(
                phone_number,
                outbound_record["id"],
                origin,
                destination,
                collection_prefix=collection_prefix
            ))
            
            asyncio.create_task(calculate_and_save_route_background(
                phone_number,
                return_record["id"],
                destination,
                origin,
                collection_prefix=collection_prefix
            ))
            logger.info(f"🔄 Route calculations started in background")
        
        # Add phone number for matching
        outbound_record["phone_number"] = phone_number
        return_record["phone_number"] = phone_number
        
        # Run matching for BOTH
        logger.info(f"🔍 Starting match search for outbound trip...")
        matches_outbound = await find_matches_for_new_record(role, outbound_record, collection_prefix)
        
        logger.info(f"🔍 Starting match search for return trip...")
        matches_return = await find_matches_for_new_record(role, return_record, collection_prefix)
        
        # Build success message (send before notifications)
        total_matches = len(matches_outbound) + len(matches_return)
        msg = f"נסיעה הלוך-שוב נשמרה! 🚗\n"
        msg += f"הלוך: מ{origin} ל{destination} בשעה {departure_time}\n"
        msg += f"חזור: מ{destination} ל{origin} בשעה {return_time}"
        
        if total_matches > 0:
            msg += f"\n\n🎯 נמצאו {total_matches} התאמות!"
        
        # Get updated list and append
        data = await get_user_rides_and_requests(phone_number, collection_prefix)
        list_msg = _format_user_records_list(
            data.get("driver_rides", []),
            data.get("hitchhiker_requests", [])
        )
        
        if list_msg:
            msg += f"\n\n📋 הנסיעות שלך עכשיו:\n\n{list_msg}"
        elif role == "hitchhiker":
            msg += "\n\n💡 המערכת מחפשת עבורך טרמפ ותעדכן אותך מיד כשנמצא אחד!"
        
        # Send match notifications AFTER the success message (with small delay)
        if matches_outbound or matches_return:
            import asyncio
            
            async def send_notifications_delayed():
                await asyncio.sleep(0.5)  # Small delay to ensure success message is sent first
                if matches_outbound:
                    await send_match_notifications(role, matches_outbound, outbound_record, send_whatsapp)
                if matches_return:
                    await send_match_notifications(role, matches_return, return_record, send_whatsapp)
            
            asyncio.create_task(send_notifications_delayed())
        
        return {"status": "success", "message": msg}
    
    # Single trip (existing logic)
    record = build_record(origin, destination, departure_time)
    
    # Save to DB
    logger.info(f"💾 Saving {role} record: {record}")
    result = await add_user_ride_or_request(phone_number, role, record, collection_prefix)
    
    if not result.get("success"):
        # If duplicate, return friendly message with current list
        if result.get("is_duplicate"):
            # Get current list
            data = await get_user_rides_and_requests(phone_number, collection_prefix)
            list_msg = _format_user_records_list(
                data.get("driver_rides", []),
                data.get("hitchhiker_requests", [])
            )
            duplicate_msg = result.get("message", "הנסיעה כבר קיימת")
            if list_msg:
                return {"status": "info", "message": f"{duplicate_msg}\n\n📋 הנסיעות שלך עכשיו:\n\n{list_msg}"}
            return {"status": "info", "message": duplicate_msg}
        return {"status": "error", "message": result.get("message", "שמירה נכשלה")}
    
    logger.info(f"✅ Saved successfully!")
    
    # 🆕 Start background route calculation (fire-and-forget)
    if role == "driver":
        import asyncio
        from services.route_service import calculate_and_save_route_background
        
        asyncio.create_task(calculate_and_save_route_background(
            phone_number,
            record["id"],
            origin,
            destination,
            collection_prefix=collection_prefix
        ))
        logger.info(f"🔄 Route calculation started in background")
    
    # Find matches (always!)
    # Add phone_number and name to record for matching notifications
    record["phone_number"] = phone_number
    record["name"] = user_name
    
    logger.info(f"🔍 Starting match search for {role}...")
    logger.info(f"📋 Record data: destination={destination}, time={record.get('departure_time')}, date={record.get('travel_date')}, days={record.get('days')}")
    
    try:
        matches = await find_matches_for_new_record(role, record, collection_prefix)
        logger.info(f"🎯 Match search complete: {len(matches)} matches found")
    except Exception as e:
        logger.error(f"❌ ERROR in find_matches_for_new_record: {e}", exc_info=True)
        matches = []  # Continue with empty matches
    
    # Success message (send first, before notifications)
    if role == "driver":
        if record.get("days"):
            msg = f"מעולה! הטרמפ הקבוע שלך ל{destination} נשמר 🚗"
        else:
            msg = f"מעולה! הטרמפ שלך ל{destination} נשמר 🚗"
        # Don't show hitchhiker matches to driver (policy decision)
        if matches:
            logger.info(f"🔕 Suppressing hitchhiker match count for driver ({len(matches)} matches found)")
    else:
        # Hitchhiker - add flexibility info
        msg = f"הבקשה שלך ל{destination} נשמרה! 🎒"
        
        # Calculate and show time flexibility
        flexibility_level = record.get("flexibility", "flexible")
        logger.info(f"📊 Flexibility saved in record: {flexibility_level}")
        
        if matches:
            msg += f"\n🚗 נמצאו {len(matches)} נהגים מתאימים!"
    
    # Get updated list and append
    from database import get_user_rides_and_requests
    data = await get_user_rides_and_requests(phone_number, collection_prefix)
    list_msg = _format_user_records_list(
        data.get("driver_rides", []),
        data.get("hitchhiker_requests", [])
    )
    
    if list_msg:
        msg += f"\n\n📋 הנסיעות שלך עכשיו:\n\n{list_msg}"
    elif role == "hitchhiker":
        msg += "\n\n💡 המערכת מחפשת עבורך טרמפ ותעדכן אותך מיד כשנמצא אחד!"
    
    # For test users: include match details in the main message
    # ONLY for hitchhikers - drivers should NOT see hitchhiker details
    from config import TEST_USERS
    is_test_user = phone_number in TEST_USERS
    
    if matches and is_test_user and role == "hitchhiker":
        logger.info(f"📝 Adding {len(matches)} driver details to message (test user, hitchhiker)")
        logger.info(f"   Current message length before adding matches: {len(msg)}")
        from services import matching_service
        msg += "\n\n💡 התאמות שנמצאו:"
        for i, match in enumerate(matches, 1):
            try:
                # Show driver details to hitchhiker
                logger.info(f"   Formatting driver {i}: {match.get('phone_number')} to {match.get('destination')}")
                match_msg = matching_service._format_driver_message(match)
                logger.info(f"   Match message length: {len(match_msg)}")
                msg += f"\n\n{i}. {match_msg}"
            except Exception as e:
                logger.error(f"   ❌ Error formatting match {i}: {type(e).__name__}: {str(e)}", exc_info=True)
                msg += f"\n\n{i}. שגיאה בפורמט ההתאמה"
        
        logger.info(f"   ✅ Finished adding matches, final message length: {len(msg)}")
    elif matches and is_test_user and role == "driver":
        logger.info(f"🚗 Driver added: Found {len(matches)} hitchhiker matches but NOT showing them to driver (policy)")
    
    # Send match notifications AFTER the success message (with small delay)
    # Always send notifications - whatsapp_service will handle test users automatically
    # BUT: For drivers, skip initial notifications - they'll be sent after route calculation
    if matches and send_whatsapp and role != "driver":
        import asyncio
        
        async def send_notifications_delayed():
            await asyncio.sleep(0.5)  # Small delay to ensure success message is sent first
            await send_match_notifications(role, matches, record, send_whatsapp)
        
        asyncio.create_task(send_notifications_delayed())
    elif matches and role == "driver":
        logger.info(f"🚗 Skipping initial notifications for driver - will send after route calculation")
    
    return {"status": "success", "message": msg}

async def handle_view_user_records(phone_number: str, collection_prefix: str = "") -> Dict:
    """Handle view_user_records function call"""
    from database import get_user_rides_and_requests
    
    data = await get_user_rides_and_requests(phone_number, collection_prefix)
    drivers = data.get("driver_rides", [])
    hitchhikers = data.get("hitchhiker_requests", [])
    
    if not drivers and not hitchhikers:
        return {
            "status": "success",
            "message": (
                "אין לך נסיעות פעילות כרגע.\n"
                "כדי לבקש טרמפ כתוב למשל: \"צריך טרמפ לתל אביב מחר ב-13\"\n"
                "כדי להציע נסיעה כתוב למשל: \"נוסע מחר לתל אביב ב-10\""
            )
        }
    
    msg = _format_user_records_list(drivers, hitchhikers)
    
    # Add helpful note if user has hitchhiker requests
    if hitchhikers:
        msg += "\n\n💡 המערכת מחפשת עבורך טרמפ ותעדכן אותך מיד כשנמצא אחד!"
    
    return {"status": "success", "message": msg}

async def handle_delete_user_record(phone_number: str, arguments: Dict, collection_prefix: str = "") -> Dict:
    """Handle delete_user_record function call"""
    from database import remove_user_ride_or_request, get_user_rides_and_requests
    
    record_number = arguments.get("record_number")
    role = arguments.get("role")
    
    if not record_number or not role:
        return {"status": "error", "message": "חסר מספר נסיעה או תפקיד"}
    
    # Get user's records
    data = await get_user_rides_and_requests(phone_number, collection_prefix)
    
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
    
    # IMPORTANT: The display list is REVERSED, convert display number to array index
    actual_index = len(records) - record_number
    record = records[actual_index]
    record_id = record.get("id")
    
    logger.info(f"🔍 Deleting display record #{record_number} → array index [{actual_index}]: {record.get('destination')}")
    
    if not record_id:
        return {"status": "error", "message": "שגיאה: הרשומה לא מכילה מזהה"}
    
    # Delete by actual ID
    success = await remove_user_ride_or_request(phone_number, role, record_id, collection_prefix)
    
    if not success:
        return {"status": "error", "message": "מחיקה נכשלה"}
    
    # Get updated list
    data = await get_user_rides_and_requests(phone_number, collection_prefix)
    list_msg = _format_user_records_list(
        data.get("driver_rides", []),
        data.get("hitchhiker_requests", [])
    )
    
    if list_msg:
        return {
            "status": "success",
            "message": f"{record_type} {record_number}) נמחק/ה בהצלחה! ✅\n\n📋 הנסיעות שלך עכשיו:\n\n{list_msg}"
        }
    return {
        "status": "success",
        "message": f"{record_type} {record_number}) נמחק/ה בהצלחה! ✅\n\nאין נסיעות פעילות"
    }

async def handle_delete_all_user_records(phone_number: str, arguments: Dict, collection_prefix: str = "") -> Dict:
    """Handle delete_all_user_records function call - delete all records of a type or everything"""
    from database import remove_user_ride_or_request, get_user_rides_and_requests
    
    role = arguments.get("role")
    
    if not role:
        return {"status": "error", "message": "חסר תפקיד"}
    
    # Get user's records
    data = await get_user_rides_and_requests(phone_number, collection_prefix)
    
    # Handle "all" - delete both drivers and hitchhikers
    if role == "all":
        driver_records = data.get("driver_rides", [])
        hitchhiker_records = data.get("hitchhiker_requests", [])
        
        if not driver_records and not hitchhiker_records:
            return {"status": "success", "message": "אין לך נסיעות למחוק"}
        
        # Delete all driver rides
        deleted_drivers = 0
        for record in driver_records:
            record_id = record.get("id")
            if record_id:
                success = await remove_user_ride_or_request(phone_number, "driver", record_id, collection_prefix)
                if success:
                    deleted_drivers += 1
        
        # Delete all hitchhiker requests
        deleted_hitchhikers = 0
        for record in hitchhiker_records:
            record_id = record.get("id")
            if record_id:
                success = await remove_user_ride_or_request(phone_number, "hitchhiker", record_id, collection_prefix)
                if success:
                    deleted_hitchhikers += 1
        
        total_deleted = deleted_drivers + deleted_hitchhikers
        return {
            "status": "success",
            "message": f"כל הנסיעות נמחקו בהצלחה! ✅\n🚗 {deleted_drivers} טרמפים נמחקו\n🎒 {deleted_hitchhikers} בקשות נמחקו\n\nאין נסיעות פעילות"
        }
    
    # Handle specific role
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
            success = await remove_user_ride_or_request(phone_number, role, record_id, collection_prefix)
            if success:
                deleted_count += 1
    
    # Get updated list
    data = await get_user_rides_and_requests(phone_number, collection_prefix)
    list_msg = _format_user_records_list(
        data.get("driver_rides", []),
        data.get("hitchhiker_requests", [])
    )
    
    if not list_msg:
        return {
            "status": "success",
            "message": f"כל ה{record_type} נמחקו בהצלחה! ✅ ({deleted_count} נמחקו)\n\nאין נסיעות פעילות"
        }
    
    return {
        "status": "success",
        "message": f"כל ה{record_type} נמחקו בהצלחה! ✅ ({deleted_count} נמחקו)\n\n📋 הנסיעות שלך עכשיו:\n\n{list_msg}"
    }

async def handle_update_user_record(phone_number: str, arguments: Dict, collection_prefix: str = "", send_whatsapp: bool = True) -> Dict:
    """Handle update_user_record function call - update existing ride/request"""
    from database import get_user_rides_and_requests, update_user_ride_or_request
    from services.matching_service import find_matches_for_new_record, send_match_notifications
    
    record_number = arguments.get("record_number")
    role = arguments.get("role")
    
    if not record_number or not role:
        return {"status": "error", "message": "חסר מספר נסיעה או תפקיד"}
    
    # Get user's records
    data = await get_user_rides_and_requests(phone_number, collection_prefix)
    
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
    
    # IMPORTANT: The display list is REVERSED (newest first), but the DB array is not!
    # Convert from display number to actual array index
    # Display: [1:newest, 2:older, 3:oldest] → Array: [0:oldest, 1:older, 2:newest]
    actual_index = len(records) - record_number
    record = records[actual_index]
    record_id = record.get("id")
    
    logger.info(f"🔍 Converting display record #{record_number} → array index [{actual_index}]: {record.get('destination')}")
    
    if not record_id:
        return {"status": "error", "message": "שגיאה: הרשומה לא מכילה מזהה"}
    
    # Build updates dictionary (only fields that were provided)
    updates = {}
    update_messages = []
    needs_route_recalc = False  # Track if route needs recalculation
    
    if "origin" in arguments:
        updates["origin"] = arguments["origin"]
        update_messages.append(f"מוצא → {arguments['origin']}")
        needs_route_recalc = True  # Origin changed - recalculate route
    
    if "destination" in arguments:
        updates["destination"] = arguments["destination"]
        update_messages.append(f"יעד → {arguments['destination']}")
        needs_route_recalc = True  # Destination changed - recalculate route
    
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
    
    # If route needs recalculation, mark it as pending
    if needs_route_recalc and role == "driver":
        updates["route_calculation_pending"] = True
    
    # DEBUG: Log what we're updating
    logger.info(f"🔍 DEBUG update_user_record: Updating {role} record {record_number} (id={record_id}) with: {updates}")
    logger.info(f"   Before update: {record.get('destination')} at {record.get('departure_time')}")
    
    # Enforce Gvaram-only origin/destination for updates
    candidate_origin = updates.get("origin", record.get("origin", ""))
    candidate_destination = updates.get("destination", record.get("destination", ""))
    if not (_is_gvaram_location(candidate_origin) or _is_gvaram_location(candidate_destination)):
        return {
            "status": "error",
            "message": "המערכת תומכת רק בנסיעות מ/אל גברעם. עדכן מוצא או יעד בהתאם."
        }

    # Update in DB
    success = await update_user_ride_or_request(phone_number, role, record_id, updates, collection_prefix)
    
    if not success:
        return {"status": "error", "message": "עדכון נכשל"}
    
    # Get updated record for matching
    data = await get_user_rides_and_requests(phone_number, collection_prefix)
    
    # IMPORTANT: Convert display number to array index (list is reversed in display)
    if role == "driver":
        rides = data.get("driver_rides", [])
        updated_record = rides[len(rides) - record_number]
    else:
        requests = data.get("hitchhiker_requests", [])
        updated_record = requests[len(requests) - record_number]
    
    # 🆕 Recalculate route in background if origin/destination changed
    if needs_route_recalc and role == "driver":
        import asyncio
        from services.route_service import calculate_and_save_route_background
        
        asyncio.create_task(calculate_and_save_route_background(
            phone_number,
            record_id,
            updated_record.get("origin", "גברעם"),
            updated_record.get("destination"),
            collection_prefix=collection_prefix
        ))
        logger.info(f"🔄 Route recalculation started in background for {record_id}")
    
    # Add phone number for matching
    updated_record["phone_number"] = phone_number
    
    # Re-run matching!
    logger.info(f"🔍 Re-running match search after update...")
    matches = await find_matches_for_new_record(role, updated_record, collection_prefix)
    
    # Build success message (send before notifications)
    update_str = ", ".join(update_messages)
    msg = f"{record_type} {record_number}) עודכן/ה! ✅\n{update_str}"
    
    if matches:
        msg += f"\n\n🎯 נמצאו {len(matches)} התאמות חדשות!"
    else:
        # Inform user that search was performed but no matches found
        msg += "\n\n🔍 חיפשתי התאמות אבל לא נמצאו כרגע"
    
    # Get updated list
    data = await get_user_rides_and_requests(phone_number, collection_prefix)
    
    # DEBUG: Log the updated record to verify it was actually updated
    if role == "driver":
        rides = data.get("driver_rides", [])
        if record_number <= len(rides):
            actual_record = rides[record_number - 1]
            logger.info(f"🔍 DEBUG update_user_record: Record {record_number} after update: {actual_record.get('destination')} at {actual_record.get('departure_time')}")
        else:
            logger.warning(f"⚠️ DEBUG: record_number {record_number} > len(rides) {len(rides)}")
    
    list_msg = _format_user_records_list(
        data.get("driver_rides", []),
        data.get("hitchhiker_requests", [])
    )
    
    if list_msg:
        msg += f"\n\n📋 הנסיעות שלך עכשיו:\n\n{list_msg}"
    elif role == "hitchhiker":
        msg += "\n\n💡 המערכת מחפשת עבורך טרמפ ותעדכן אותך מיד כשנמצא אחד!"
    
    # Send match notifications AFTER the success message (with small delay)
    # BUT: For drivers with route recalc pending, skip - notifications will be sent after route calculation
    if matches and not (needs_route_recalc and role == "driver"):
        import asyncio
        
        async def send_notifications_delayed():
            await asyncio.sleep(0.5)  # Small delay to ensure success message is sent first
            await send_match_notifications(role, matches, updated_record, send_whatsapp)
        
        asyncio.create_task(send_notifications_delayed())
    elif matches and needs_route_recalc and role == "driver":
        logger.info(f"🚗 Skipping notifications for driver - will send after route recalculation")
    
    return {"status": "success", "message": msg}

async def handle_show_help(phone_number: str, collection_prefix: str = "") -> Dict:
    """
    Handle show_help function call - display help message or user's trips
    
    If user has active trips/requests, show them.
    Otherwise, show help message.
    """
    from database import get_user_rides_and_requests
    from config import HELP_MESSAGE
    
    # Get user's current trips
    data = await get_user_rides_and_requests(phone_number, collection_prefix)
    driver_rides = data.get("driver_rides", [])
    hitchhiker_requests = data.get("hitchhiker_requests", [])
    
    # If user has trips, show them
    if driver_rides or hitchhiker_requests:
        msg = "📋 הנסיעות שלך:\n\n"
        msg += _format_user_records_list(driver_rides, hitchhiker_requests)
        if hitchhiker_requests:
            msg += "\n\n💡 המערכת מחפשת עבורך טרמפ ותעדכן אותך מיד כשנמצא אחד!"
        return {
            "status": "success",
            "message": msg
        }
    
    # Otherwise, show help message
    return {
        "status": "success",
        "message": HELP_MESSAGE
    }

async def handle_resolve_duplicate(
    phone_number: str,
    args: dict,
    collection_prefix: str = "",
    send_whatsapp: bool = True
) -> str:
    """
    Resolve driver/hitchhiker conflict by deleting one and creating the other.
    
    Args:
        phone_number: User's phone number
        args: Arguments containing:
            - delete_role: "driver" or "hitchhiker" (what to delete)
            - delete_record_number: Record number to delete
            - create_role: "driver" or "hitchhiker" (what to create)
            - destination: Destination for new record
            - travel_date: Date for new record
            - departure_time: Time for new record
        collection_prefix: Collection prefix for sandbox mode
        send_whatsapp: Whether to send WhatsApp notifications
    
    Returns:
        Result message from creating the new record
    """
    logger.info(f"🔄 Resolving duplicate conflict for {phone_number}")
    logger.info(f"   Delete: {args['delete_role']} #{args['delete_record_number']}")
    logger.info(f"   Create: {args['create_role']} to {args['destination']}")
    
    # Step 1: Delete the conflicting record
    delete_result = await handle_delete_user_record(
        phone_number,
        {
            "role": args["delete_role"],
            "record_number": args["delete_record_number"]
        },
        collection_prefix
    )
    
    logger.info(f"   Delete result: {delete_result.get('status')}")
    
    # Step 2: Create the new record
    create_result = await handle_update_user_records(
        phone_number,
        {
            "role": args["create_role"],
            "destination": args["destination"],
            "travel_date": args["travel_date"],
            "departure_time": args["departure_time"]
        },
        collection_prefix,
        send_whatsapp=send_whatsapp
    )
    
    logger.info(f"   Create result: {create_result.get('status') if isinstance(create_result, dict) else 'success'}")
    
    return create_result
