"""Function handlers for AI function calls"""
import logging
from typing import Dict, List
import uuid
from utils.timezone_utils import israel_now_isoformat

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
                    hours = tolerance_minutes // 60
                    minutes = tolerance_minutes % 60
                    if hours > 0 and minutes > 0:
                        flex_text = f"גמיש, ±{hours} ש' {minutes} דק'"
                    elif hours > 0:
                        flex_text = f"גמיש, ±{hours} ש'"
                    else:
                        flex_text = f"גמיש, ±{minutes} דק'"
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
            
            msg += f"{i}) מ{origin} ל{destination} - {req['travel_date']} בשעה {req['departure_time']} {flex_emoji} ({flex_text})\n"
    
    return msg.strip()

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
                "flexibility": arguments.get("flexibility", "very_flexible")  # Default: very flexible (±6h)
            })
            
            # 🗺️ Geocode origin and destination for map display
            try:
                from services.route_service import geocode_address
                origin_coords = geocode_address(origin_val)
                dest_coords = geocode_address(destination_val)
                
                if origin_coords and dest_coords:
                    record["origin_coordinates"] = origin_coords
                    record["destination_coordinates"] = dest_coords
                    logger.info(f"📍 Geocoded hitchhiker locations: {origin_val} → {dest_val}")
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
        
        msg += f"\n\n📋 הנסיעות שלך עכשיו:\n\n{list_msg}"
        
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
            return {"status": "info", "message": f"{duplicate_msg}\n\n📋 הנסיעות שלך עכשיו:\n\n{list_msg}"}
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
        if matches:
            msg += f"\n✨ כבר נמצאו {len(matches)} טרמפיסטים מתאימים!"
    else:
        # Hitchhiker - add flexibility info
        msg = f"הבקשה שלך ל{destination} נשמרה! 🎒"
        
        # Calculate and show time flexibility
        flexibility_level = record.get("flexibility", "very_flexible")
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
    
    msg += f"\n\n📋 הנסיעות שלך עכשיו:\n\n{list_msg}"
    
    # In sandbox mode (send_whatsapp=False), include match details in the main message
    if matches and not send_whatsapp:
        logger.info(f"📝 Adding {len(matches)} match details to message (sandbox mode)")
        logger.info(f"   Current message length before adding matches: {len(msg)}")
        from services import matching_service
        msg += "\n\n💡 התאמות שנמצאו:"
        for i, match in enumerate(matches, 1):
            try:
                if role == "hitchhiker":
                    # Show driver details
                    logger.info(f"   Formatting driver {i}: {match.get('phone_number')} to {match.get('destination')}")
                    match_msg = matching_service._format_driver_message(match)
                else:
                    # Show hitchhiker details
                    logger.info(f"   Formatting hitchhiker {i}: {match.get('phone_number')} to {match.get('destination')}")
                    match_msg = matching_service._format_hitchhiker_message(match, destination)
                logger.info(f"   Match message length: {len(match_msg)}")
                msg += f"\n\n{i}. {match_msg}"
            except Exception as e:
                logger.error(f"   ❌ Error formatting match {i}: {type(e).__name__}: {str(e)}", exc_info=True)
                msg += f"\n\n{i}. שגיאה בפורמט ההתאמה"
        
        logger.info(f"   ✅ Finished adding matches, final message length: {len(msg)}")
    
    # Send match notifications AFTER the success message (with small delay) - only in production
    if matches and send_whatsapp:
        import asyncio
        
        async def send_notifications_delayed():
            await asyncio.sleep(0.5)  # Small delay to ensure success message is sent first
            await send_match_notifications(role, matches, record, send_whatsapp)
        
        asyncio.create_task(send_notifications_delayed())
    
    return {"status": "success", "message": msg}

async def handle_view_user_records(phone_number: str, collection_prefix: str = "") -> Dict:
    """Handle view_user_records function call"""
    from database import get_user_rides_and_requests
    
    data = await get_user_rides_and_requests(phone_number, collection_prefix)
    drivers = data.get("driver_rides", [])
    hitchhikers = data.get("hitchhiker_requests", [])
    
    if not drivers and not hitchhikers:
        return {"status": "success", "message": "אין לך רשומות פעילות כרגע"}
    
    msg = _format_user_records_list(drivers, hitchhikers)
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
    
    # Get the actual record (0-based array)
    record = records[record_number - 1]
    record_id = record.get("id")
    
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
    
    return {
        "status": "success",
        "message": f"{record_type} {record_number}) נמחק/ה בהצלחה! ✅\n\n📋 הנסיעות שלך עכשיו:\n\n{list_msg}"
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
            "message": f"כל הנסיעות נמחקו בהצלחה! ✅\n🚗 {deleted_drivers} טרמפים נמחקו\n🎒 {deleted_hitchhikers} בקשות נמחקו\n\n📋 אין לך נסיעות פעילות"
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
    
    if list_msg == "(אין נסיעות פעילות)":
        return {
            "status": "success",
            "message": f"כל ה{record_type} נמחקו בהצלחה! ✅ ({deleted_count} נמחקו)\n\n📋 אין לך נסיעות פעילות"
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
    
    # Get the actual record (0-based array)
    record = records[record_number - 1]
    record_id = record.get("id")
    
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
    
    # Update in DB
    success = await update_user_ride_or_request(phone_number, role, record_id, updates, collection_prefix)
    
    if not success:
        return {"status": "error", "message": "עדכון נכשל"}
    
    # Get updated record for matching
    data = await get_user_rides_and_requests(phone_number, collection_prefix)
    if role == "driver":
        updated_record = data.get("driver_rides", [])[record_number - 1]
    else:
        updated_record = data.get("hitchhiker_requests", [])[record_number - 1]
    
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
    
    # Get updated list
    data = await get_user_rides_and_requests(phone_number, collection_prefix)
    list_msg = _format_user_records_list(
        data.get("driver_rides", []),
        data.get("hitchhiker_requests", [])
    )
    
    msg += f"\n\n📋 הנסיעות שלך עכשיו:\n\n{list_msg}"
    
    # Send match notifications AFTER the success message (with small delay)
    if matches:
        import asyncio
        
        async def send_notifications_delayed():
            await asyncio.sleep(0.5)  # Small delay to ensure success message is sent first
            await send_match_notifications(role, matches, updated_record, send_whatsapp)
        
        asyncio.create_task(send_notifications_delayed())
    
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
        
        return {
            "status": "success",
            "message": msg
        }
    
    # Otherwise, show help message
    return {
        "status": "success",
        "message": HELP_MESSAGE
    }
