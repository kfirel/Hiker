"""
Approval Service - Manages pending driver/hitchhiker approvals
Reduces AI dependency by handling approval logic in code
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from database import get_db, get_or_create_user
from services.whatsapp_service import send_whatsapp_message
from services.matching_service import find_matches_for_user, format_driver_info, format_hitchhiker_info

logger = logging.getLogger(__name__)

# ============================================================================
# Pending Approvals Management
# ============================================================================

async def create_pending_approval(
    driver_phone: str,
    hitchhiker_phone: str,
    hitchhiker_request_id: str,
    driver_ride_id: str
) -> bool:
    """
    Create a pending approval in Firestore
    When hitchhiker requests ride and driver has auto_approve=False
    
    Args:
        driver_phone: Driver's phone number
        hitchhiker_phone: Hitchhiker's phone number
        hitchhiker_request_id: ID of the hitchhiker's request
        driver_ride_id: ID of the driver's ride
    
    Returns:
        True if successful
    """
    db = get_db()
    if not db:
        logger.error(f"❌ Cannot create pending approval: DB not available")
        return False
    
    try:
        approval_data = {
            "driver_phone": driver_phone,
            "hitchhiker_phone": hitchhiker_phone,
            "hitchhiker_request_id": hitchhiker_request_id,
            "driver_ride_id": driver_ride_id,
            "status": "pending",  # pending, approved, rejected
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": None  # TODO: Add expiration
        }
        
        # Store in pending_approvals collection
        approval_id = f"{driver_phone}_{hitchhiker_phone}_{hitchhiker_request_id}"
        
        logger.info(f"💾 Creating pending approval: driver={driver_phone}, hitchhiker={hitchhiker_phone}")
        db.collection("pending_approvals").document(approval_id).set(approval_data)
        
        logger.info(f"✅ Pending approval created: {approval_id}")
        return True
    
    except Exception as e:
        logger.error(f"❌ Error creating pending approval: {e}")
        return False


async def get_pending_approvals_for_driver(driver_phone: str) -> List[Dict[str, Any]]:
    """
    Get all pending approvals for a driver
    
    Args:
        driver_phone: Driver's phone number
    
    Returns:
        List of pending approval dictionaries
    """
    db = get_db()
    if not db:
        logger.warning(f"⚠️ DB not available for pending approvals")
        return []
    
    try:
        approvals = []
        docs = db.collection("pending_approvals")\
                  .filter("driver_phone", "==", driver_phone)\
                  .filter("status", "==", "pending")\
                  .stream()
        
        for doc in docs:
            approval_data = doc.to_dict()
            approval_data["id"] = doc.id
            approvals.append(approval_data)
        
        logger.info(f"🔍 Found {len(approvals)} pending approvals for driver {driver_phone}")
        return approvals
    
    except Exception as e:
        logger.error(f"❌ Error getting pending approvals: {e}")
        return []


async def check_and_handle_approval_response(phone_number: str, message: str) -> Optional[str]:
    """
    Check if user has pending approvals and handle their response
    This runs BEFORE AI processing to handle simple yes/no responses
    
    Args:
        phone_number: User's phone number
        message: User's message text
    
    Returns:
        Response text if handled, None if should go to AI
    """
    # Check for simple yes/no responses
    message_lower = message.lower().strip()
    
    is_yes = message_lower in ["כן", "yes", "שלח", "אישור", "בטח", "כן שלח", "אוקיי", "ok", "👍"]
    is_no = message_lower in ["לא", "no", "לא תודה", "ביטול", "לא מעוניין", "👎"]
    
    if not (is_yes or is_no):
        return None  # Not a simple approval response, let AI handle
    
    # Get pending approvals
    pending = await get_pending_approvals_for_driver(phone_number)
    
    if not pending:
        return None  # No pending approvals, let AI handle
    
    # Handle the response
    if is_yes:
        return await approve_all_pending(phone_number, pending)
    else:
        return await reject_all_pending(phone_number, pending)


async def approve_all_pending(driver_phone: str, pending_approvals: List[Dict[str, Any]]) -> str:
    """
    Approve all pending requests and send driver details to hitchhikers
    
    Args:
        driver_phone: Driver's phone number
        pending_approvals: List of pending approval dicts
    
    Returns:
        Response message for driver
    """
    db = get_db()
    if not db:
        return "שגיאה במערכת, נסה שוב"
    
    # Get driver info
    driver_user_data, _ = await get_or_create_user(driver_phone)
    driver_name = driver_user_data.get("name", "")
    
    sent_count = 0
    failed = []
    
    for approval in pending_approvals:
        hitchhiker_phone = approval.get("hitchhiker_phone")
        driver_ride_id = approval.get("driver_ride_id")
        
        # Get driver ride details
        driver_rides = driver_user_data.get("driver_rides", [])
        driver_ride = next((r for r in driver_rides if r.get("id") == driver_ride_id), None)
        
        if not driver_ride or not hitchhiker_phone:
            continue
        
        # Format driver info
        driver_info_dict = {
            "phone_number": driver_phone,
            "name": driver_name,
            "destination": driver_ride.get("destination"),
            "departure_time": driver_ride.get("departure_time"),
            "days": driver_ride.get("days", []),
            "return_time": driver_ride.get("return_time")
        }
        
        formatted_driver = format_driver_info(driver_info_dict)
        
        # Send notification to hitchhiker
        destination = driver_ride.get("destination", "")
        driver_name_display = f"{driver_name} " if driver_name else ""
        notification = f"""🚗 נהג מאשר את הבקשה שלך!

{driver_name_display}יכול לקחת אותך ל{destination}:
{formatted_driver}

צור קשר ישירות! 📲"""
        
        try:
            await send_whatsapp_message(hitchhiker_phone, notification)
            sent_count += 1
            
            # Mark as approved
            approval_id = approval.get("id")
            db.collection("pending_approvals").document(approval_id).update({
                "status": "approved",
                "approved_at": datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            logger.error(f"❌ Error sending to {hitchhiker_phone}: {e}")
            failed.append(hitchhiker_phone)
    
    # Build response
    if sent_count > 0:
        response = f"מעולה! שלחתי את הפרטים שלך ל-{sent_count} טרמפיסטים 🚗"
        if failed:
            response += f"\n\n⚠️ {len(failed)} הודעות נכשלו"
    else:
        response = "לא הצלחתי לשלוח הודעות. נסה שוב מאוחר יותר."
    
    logger.info(f"✅ Driver {driver_phone} approved {sent_count} requests")
    return response


async def reject_all_pending(driver_phone: str, pending_approvals: List[Dict[str, Any]]) -> str:
    """
    Reject all pending requests
    
    Args:
        driver_phone: Driver's phone number
        pending_approvals: List of pending approval dicts
    
    Returns:
        Response message for driver
    """
    db = get_db()
    if not db:
        return "שגיאה במערכת"
    
    count = 0
    for approval in pending_approvals:
        try:
            approval_id = approval.get("id")
            db.collection("pending_approvals").document(approval_id).update({
                "status": "rejected",
                "rejected_at": datetime.utcnow().isoformat()
            })
            count += 1
        except Exception as e:
            logger.error(f"❌ Error rejecting approval: {e}")
    
    logger.info(f"❌ Driver {driver_phone} rejected {count} requests")
    return f"בסדר, לא שלחתי. ביטלתי {count} בקשות."


# ============================================================================
# Auto-notification when hitchhiker creates request
# ============================================================================

async def notify_drivers_about_hitchhiker(
    hitchhiker_phone: str,
    hitchhiker_data: Dict[str, Any],
    matching_drivers: List[Dict[str, Any]]
) -> Dict[str, int]:
    """
    Send notifications to drivers about new hitchhiker request
    Handles both auto-approve and manual-approve drivers
    
    Args:
        hitchhiker_phone: Hitchhiker's phone number
        hitchhiker_data: Hitchhiker's request data
        matching_drivers: List of matching drivers
    
    Returns:
        {"auto_sent": count, "pending_approval": count}
    """
    from database import get_or_create_user
    
    logger.info(f"📢 notify_drivers_about_hitchhiker called: {len(matching_drivers)} drivers")
    
    hitchhiker_user_data, _ = await get_or_create_user(hitchhiker_phone)
    hitchhiker_name = hitchhiker_user_data.get("name", "")
    hitchhiker_display = f"{hitchhiker_name} " if hitchhiker_name else "מישהו "
    
    destination = hitchhiker_data.get("destination", "")
    travel_date = hitchhiker_data.get("travel_date", "")
    departure_time = hitchhiker_data.get("departure_time", "")
    hitchhiker_request_id = hitchhiker_data.get("id")
    
    logger.info(f"📋 Hitchhiker details: dest={destination}, date={travel_date}, time={departure_time}, id={hitchhiker_request_id}")
    
    auto_sent = 0
    pending_approval = 0
    
    for driver in matching_drivers:
        driver_phone = driver.get("phone_number")
        driver_ride_id = driver.get("ride_id")
        auto_approve = driver.get("auto_approve_matches", True)
        
        logger.info(f"🚗 Processing driver: phone={driver_phone}, ride_id={driver_ride_id}, auto_approve={auto_approve}")
        
        if not driver_phone:
            logger.warning(f"⚠️ Skipping driver - no phone number")
            continue
        
        if auto_approve:
            # Auto-approve: Send driver details immediately to hitchhiker
            driver_name = driver.get("name", "")
            driver_info_dict = {
                "phone_number": driver_phone,
                "name": driver_name,
                "destination": driver.get("destination"),
                "departure_time": driver.get("departure_time"),
                "days": driver.get("days", []),
                "return_time": driver.get("return_time")
            }
            
            formatted_driver = format_driver_info(driver_info_dict)
            
            notification = f"""🚗 נהג חדש נוסע ל{destination}!

{driver_name + ' ' if driver_name else ''}מציע נסיעה:
{formatted_driver}

צור קשר ישירות! 📲"""
            
            try:
                await send_whatsapp_message(hitchhiker_phone, notification)
                auto_sent += 1
                logger.info(f"📤 Auto-sent driver {driver_phone} to hitchhiker {hitchhiker_phone}")
            except Exception as e:
                logger.error(f"❌ Failed to send: {e}")
        
        else:
            # Manual approval: Ask driver first
            logger.info(f"⏸️ Manual approval needed for driver {driver_phone}")
            
            notification = f"""🚗 טרמפיסט חדש!

{hitchhiker_display}מחפש טרמפ ל{destination}
📅 {travel_date}
🕐 {departure_time}

רוצה שאשלח לו את הפרטים שלך?
(השב 'כן' או 'לא')"""
            
            try:
                logger.info(f"📤 Sending approval request to driver {driver_phone}")
                await send_whatsapp_message(driver_phone, notification)
                
                # Create pending approval
                logger.info(f"💾 Creating pending approval in DB...")
                approval_created = await create_pending_approval(
                    driver_phone=driver_phone,
                    hitchhiker_phone=hitchhiker_phone,
                    hitchhiker_request_id=hitchhiker_request_id,
                    driver_ride_id=driver_ride_id
                )
                
                if approval_created:
                    pending_approval += 1
                    logger.info(f"✅ Pending approval created and message sent to driver {driver_phone}")
                else:
                    logger.error(f"❌ Failed to create pending approval for driver {driver_phone}")
                    
            except Exception as e:
                logger.error(f"❌ Failed to send approval request to {driver_phone}: {e}", exc_info=True)
    
    return {
        "auto_sent": auto_sent,
        "pending_approval": pending_approval
    }

