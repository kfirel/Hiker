"""
Approval Service - Handles driver approval/rejection of ride requests
"""

from datetime import datetime
from typing import Dict, Any, Optional
import logging
from bson import ObjectId

from src.utils.preference_helper import PreferenceHelper

logger = logging.getLogger(__name__)


class ApprovalService:
    """Service for handling driver approvals"""
    
    def __init__(self, db, whatsapp_client=None, user_logger=None):
        """
        Initialize approval service
        
        Args:
            db: MongoDBClient instance
            whatsapp_client: WhatsAppClient instance (optional)
            user_logger: UserLogger instance (optional) for logging notifications
        """
        self.db = db
        self.whatsapp_client = whatsapp_client
        self.user_logger = user_logger
    
    def driver_approve(self, match_id: str, driver_phone: str, is_auto_approval: bool = False) -> bool:
        """
        Driver approves a match
        
        Args:
            match_id: Match ID (from matched_drivers array)
            driver_phone: Driver's phone number
            is_auto_approval: If True, this is an automatic approval (driver won't receive confirmation message)
            
        Returns:
            True if successful
        """
        # Find ride request with this match_id in matched_drivers array
        ride_request = self.db.get_collection("ride_requests").find_one({
            "matched_drivers.match_id": match_id
        })
        
        if not ride_request:
            logger.error(f"Match not found: {match_id}")
            return False
        
        # Find the matched driver entry
        matched_driver = None
        for md in ride_request.get('matched_drivers', []):
            if md.get('match_id') == match_id:
                matched_driver = md
                break
        
        if not matched_driver:
            logger.error(f"Matched driver entry not found: {match_id}")
            return False
        
        # Verify driver
        driver = self.db.get_collection("users").find_one({"phone_number": driver_phone})
        if not driver or str(driver['_id']) != str(matched_driver['driver_id']):
            logger.error(f"Driver verification failed for match {match_id}")
            return False
        
        # Update matched_driver entry in ride_request
        update_data = {
            "matched_drivers.$.status": "approved",
            "matched_drivers.$.driver_response": "approved",
            "matched_drivers.$.driver_response_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        # Store is_auto_approval flag
        if is_auto_approval:
            update_data["matched_drivers.$.is_auto_approval"] = True
        
        self.db.get_collection("ride_requests").update_one(
            {"_id": ride_request['_id'], "matched_drivers.match_id": match_id},
            {"$set": update_data}
        )
        
        if ride_request:
            # Update ride request status to approved (but don't reject other matches)
            # This allows multiple drivers to approve the same request
            self.db.get_collection("ride_requests").update_one(
                {"_id": ride_request['_id']},
                {
                    "$set": {
                        "status": "approved",
                        "updated_at": datetime.now()
                    }
                }
            )
            
            # Don't reject other pending matches - allow multiple drivers to approve
            # Each driver can independently approve or reject
            
            # Check driver's preference for sharing name
            share_name_preference = PreferenceHelper.get_share_name_preference(driver)
            # Default to 'always' for backward compatibility (if not set)
            if not share_name_preference or share_name_preference == 'ask':
                # For approval flow, default to 'always' if not set
                share_name_preference = 'always' if share_name_preference != 'ask' else 'ask'
            
            logger.info(f"Driver {driver_phone} share_name_preference: {share_name_preference}")
            
            # Notify hitchhiker if whatsapp client available
            if self.whatsapp_client:
                if share_name_preference == 'ask':
                    # Ask driver first before notifying hitchhiker
                    # Create match-like dict for compatibility
                    match_dict = {
                        'match_id': match_id,
                        'driver_id': matched_driver['driver_id'],
                        'hitchhiker_id': ride_request['requester_id'],
                        'ride_request_id': ride_request['_id']
                    }
                    self._ask_driver_about_name_sharing(match_id, driver_phone, match_dict, ride_request)
                    # Don't send confirmation message yet - wait for driver's response
                    return True
                else:
                    # Notify hitchhiker immediately (with or without name based on preference)
                    # Create match-like dict for compatibility
                    match_dict = {
                        'match_id': match_id,
                        'driver_id': matched_driver['driver_id'],
                        'hitchhiker_id': ride_request['requester_id'],
                        'ride_request_id': ride_request['_id']
                    }
                    self._notify_hitchhiker_approved(match_dict, driver, ride_request, match_id)
        
        logger.info(f"Match {match_id} approved by driver {driver_phone}")
        return True
    
    def driver_reject(self, match_id: str, driver_phone: str) -> bool:
        """
        Driver rejects a match
        
        Args:
            match_id: Match ID (from matched_drivers array)
            driver_phone: Driver's phone number
            
        Returns:
            True if successful
        """
        # Find ride request with this match_id in matched_drivers array
        ride_request = self.db.get_collection("ride_requests").find_one({
            "matched_drivers.match_id": match_id
        })
        
        if not ride_request:
            logger.error(f"Match not found: {match_id}")
            return False
        
        # Find the matched driver entry
        matched_driver = None
        for md in ride_request.get('matched_drivers', []):
            if md.get('match_id') == match_id:
                matched_driver = md
                break
        
        if not matched_driver:
            logger.error(f"Matched driver entry not found: {match_id}")
            return False
        
        # Verify driver
        driver = self.db.get_collection("users").find_one({"phone_number": driver_phone})
        if not driver or str(driver['_id']) != str(matched_driver['driver_id']):
            logger.error(f"Driver verification failed for match {match_id}")
            return False
        
        # Update matched_driver entry in ride_request
        self.db.get_collection("ride_requests").update_one(
            {"_id": ride_request['_id'], "matched_drivers.match_id": match_id},
            {
                "$set": {
                    "matched_drivers.$.status": "rejected",
                    "matched_drivers.$.driver_response": "rejected",
                    "matched_drivers.$.driver_response_at": datetime.now(),
                    "updated_at": datetime.now()
                }
            }
        )
        
        logger.info(f"Match {match_id} rejected by driver {driver_phone}")
        return True
    
    def _ask_driver_about_name_sharing(self, match_id: str, driver_phone: str, 
                                       match: Dict[str, Any], ride_request: Dict[str, Any]):
        """Ask driver if they want to share their name with hitchhiker"""
        if not self.whatsapp_client:
            return
        
        hitchhiker = self.db.get_collection("users").find_one({"_id": match['hitchhiker_id']})
        if not hitchhiker:
            return
        
        hitchhiker_name = PreferenceHelper.get_hitchhiker_name(hitchhiker)
        destination = ride_request.get('destination', 'יעד')
        
        # Store match_id in driver's context for later processing
        self.db.get_collection("users").update_one(
            {"phone_number": driver_phone},
            {"$set": {"pending_name_share_match_id": match_id}}
        )
        
        # Get destination for the message
        destination = ride_request.get('destination', 'יעד')
        
        # Ask driver
        message = f"""✅ אישרת את הבקשה של {hitchhiker_name} (ל-{destination})!

האם לשלוח לטרמפיסט את השם והטלפון שלך?

1. בטח - לשלוח הכל
2. מעדיף שתשאל אותי לפני"""
        
        buttons = [
            {
                "type": "reply",
                "reply": {
                    "id": f"share_name_yes_{match_id}",
                    "title": "בטח"
                }
            },
            {
                "type": "reply",
                "reply": {
                    "id": f"share_name_no_{match_id}",
                    "title": "מעדיף שתשאל"
                }
            }
        ]
        
        self.whatsapp_client.send_message(driver_phone, message, buttons=buttons)
    
    def handle_name_sharing_response(self, driver_phone: str, button_id: str) -> bool:
        """Handle driver's response about sharing name"""
        # Extract match_id and response from button_id
        if button_id.startswith('share_name_yes_'):
            match_id = button_id.replace('share_name_yes_', '')
            share_name = True
        elif button_id.startswith('share_name_no_'):
            match_id = button_id.replace('share_name_no_', '')
            share_name = False
        else:
            logger.error(f"Invalid name sharing button ID: {button_id}")
            if self.whatsapp_client:
                self.whatsapp_client.send_message(
                    driver_phone,
                    "❌ שגיאה: קוד כפתור לא תקין. נסה שוב או פנה לתמיכה."
                )
            return False
        
        # Validate match_id
        if not match_id or match_id.strip() == '':
            logger.error(f"Empty match_id in name sharing button ID: {button_id}")
            # Try to find match from driver's context or database
            driver = self.db.get_collection("users").find_one({"phone_number": driver_phone})
            if driver:
                context = driver.get('context', {})
                match_id = context.get('pending_name_share_match_id')
            if not match_id:
                # Try to find most recent pending match from ride_requests
                driver = self.db.get_collection("users").find_one({"phone_number": driver_phone})
                if driver:
                    ride_requests = list(self.db.get_collection("ride_requests").find({
                        "matched_drivers.driver_id": driver['_id'],
                        "matched_drivers.status": "pending_approval"
                    }).sort("created_at", -1).limit(1))
                    if ride_requests:
                        for md in ride_requests[0].get('matched_drivers', []):
                            if str(md.get('driver_id')) == str(driver['_id']) and md.get('status') == 'pending_approval':
                                match_id = md.get('match_id')
                                break
            
            if not match_id:
                logger.error(f"Could not find match_id for driver {driver_phone}")
                if self.whatsapp_client:
                    self.whatsapp_client.send_message(
                        driver_phone,
                        "❌ שגיאה: לא נמצאה בקשה ממתינה. נסה שוב או פנה לתמיכה."
                    )
                return False
        
        # Find ride request with this match_id
        ride_request = self.db.get_collection("ride_requests").find_one({
            "matched_drivers.match_id": match_id
        })
        
        if not ride_request:
            logger.error(f"Match not found: {match_id}")
            if self.whatsapp_client:
                self.whatsapp_client.send_message(
                    driver_phone,
                    "❌ שגיאה: לא נמצאה התאמה. נסה שוב או פנה לתמיכה."
                )
            return False
        
        # Find matched driver entry
        matched_driver = None
        for md in ride_request.get('matched_drivers', []):
            if md.get('match_id') == match_id:
                matched_driver = md
                break
        
        if not matched_driver:
            logger.error(f"Matched driver entry not found: {match_id}")
            return False
        
        driver = self.db.get_collection("users").find_one({"phone_number": driver_phone})
        if not driver or str(driver['_id']) != str(matched_driver['driver_id']):
            logger.error(f"Driver verification failed for match {match_id}")
            if self.whatsapp_client:
                self.whatsapp_client.send_message(
                    driver_phone,
                    "❌ שגיאה: אימות נהג נכשל. נסה שוב או פנה לתמיכה."
                )
            return False
        
        # Clear pending match_id from driver's context
        self.db.get_collection("users").update_one(
            {"phone_number": driver_phone},
            {"$unset": {"pending_name_share_match_id": ""}}
        )
        
        # Notify hitchhiker with or without name based on driver's choice
        # Get hitchhiker and destination info for the message
        hitchhiker = self.db.get_collection("users").find_one({"_id": ride_request['requester_id']})
        hitchhiker_name = PreferenceHelper.get_hitchhiker_name(hitchhiker)
        destination = ride_request.get('destination', 'יעד') if ride_request else 'יעד'
        
        # Create match-like dict for compatibility
        match_dict = {
            'match_id': match_id,
            'driver_id': matched_driver['driver_id'],
            'hitchhiker_id': ride_request['requester_id'],
            'ride_request_id': ride_request['_id']
        }
        
        if share_name:
            # Create temporary driver dict with name (ensure preference is 'always')
            driver_with_name = driver.copy()
            driver_with_name['share_name_with_hitchhiker'] = 'always'
            self._notify_hitchhiker_approved(match_dict, driver_with_name, ride_request, match_id)
            confirmation = f"✅ אישרת את הבקשה!\n\nפרטי הקשר שלך (שם וטלפון) נשלחו לטרמפיסט {hitchhiker_name} (ל-{destination}).\nהוא יצור איתך קשר בקרוב כדי לתאם את הפרטים! 📲"
        else:
            # Create temporary driver dict without name (set preference to 'never')
            driver_without_name = driver.copy()
            driver_without_name['share_name_with_hitchhiker'] = 'never'
            self._notify_hitchhiker_approved(match_dict, driver_without_name, ride_request, match_id)
            confirmation = f"✅ אישרת את הבקשה!\n\nמספר הטלפון שלך נשלח לטרמפיסט {hitchhiker_name} (ל-{destination}).\nהוא יצור איתך קשר בקרוב כדי לתאם את הפרטים! 📲"
        
        self.whatsapp_client.send_message(driver_phone, confirmation)
        return True
    
    def _notify_hitchhiker_approved(self, match: Dict[str, Any], driver: Dict[str, Any], 
                                    ride_request: Dict[str, Any], match_id: str = None):
        """
        Send approval notification to hitchhiker with driver contact details.
        If multiple drivers have approved, send all of them in one message.
        """
        # Check if ride request was already marked as "found" - don't send notifications
        if ride_request.get('status') == 'found':
            logger.info(f"Ride request {ride_request['_id']} already marked as found, skipping approval notification")
            return
        
        hitchhiker = self.db.get_collection("users").find_one({"_id": match['hitchhiker_id']})
        if not hitchhiker or not self.whatsapp_client:
            return
        
        # Get fresh ride_request to get latest matched_drivers
        ride_request = self.db.get_collection("ride_requests").find_one({"_id": ride_request['_id']})
        if not ride_request:
            logger.error(f"Ride request not found: {ride_request['_id']}")
            return
        
        # Find all approved matched drivers from matched_drivers array
        matched_drivers = ride_request.get('matched_drivers', [])
        approved_drivers = []
        
        for matched_driver_entry in matched_drivers:
            if matched_driver_entry.get('status') == 'approved':
                approved_driver = self.db.get_collection("users").find_one({"_id": matched_driver_entry['driver_id']})
                if approved_driver:
                    approved_drivers.append({
                        'driver': approved_driver,
                        'match': matched_driver_entry  # Use matched_driver_entry as match dict
                    })
        
        if not approved_drivers:
            logger.warning(f"No approved drivers found for ride request {ride_request['_id']}")
            return
        
        destination = ride_request.get('destination', 'יעד')
        
        # Format time range for display
        start_time = ride_request.get('start_time_range')
        end_time = ride_request.get('end_time_range')
        if start_time and end_time:
            time_info = f"{start_time.strftime('%H:%M')}-{end_time.strftime('%H:%M')}"
        else:
            time_info = 'גמיש'
        
        # Build message with all approved drivers
        if len(approved_drivers) == 1:
            # Single driver - simple message
            driver_info = approved_drivers[0]
            driver = driver_info['driver']
            driver_phone = driver.get('phone_number', '')
            
            # Check driver's preference for sharing name
            share_name_preference = PreferenceHelper.get_share_name_preference(driver)
            if not share_name_preference or share_name_preference == 'ask':
                share_name_preference = 'always' if share_name_preference != 'ask' else 'ask'
            
            if share_name_preference == 'never':
                message = f"""🎉 מעולה! נהג מצא אותך מתאים!

👤 פרטי הנהג:
📱 טלפון: {driver_phone}
📍 נוסע ל: {destination}
⏰ זמן יציאה משוער: {time_info}
(הנהג יצא מגברעם בטווח השעות הזה)

תוכל ליצור איתו קשר עכשיו כדי לתאם את הפרטים המדויקים! 📲

אם מצאת טרמפ שלח ״מצאתי״ כדי שאפסיק לשלוח לך שמות של נהגים."""
            else:
                driver_name = PreferenceHelper.get_driver_name(driver)
                message = f"""🎉 מעולה! נהג מצא אותך מתאים!

👤 פרטי הנהג:
🚗 שם: {driver_name}
📱 טלפון: {driver_phone}
📍 נוסע ל: {destination}
⏰ זמן יציאה משוער: {time_info}
(הנהג יצא מגברעם בטווח השעות הזה)

תוכל ליצור איתו קשר עכשיו כדי לתאם את הפרטים המדויקים! 📲

אם מצאת טרמפ שלח ״מצאתי״ כדי שאפסיק לשלוח לך שמות של נהגים."""
        else:
            # Multiple drivers - send all of them
            message = f"""🎉 מעולה! {len(approved_drivers)} נהגים מצאו אותך מתאים!

👥 פרטי הנהגים:

"""
            
            for i, driver_info in enumerate(approved_drivers, 1):
                driver = driver_info['driver']
                driver_phone = driver.get('phone_number', '')
                
                # Check driver's preference for sharing name
                share_name_preference = PreferenceHelper.get_share_name_preference(driver)
                if not share_name_preference or share_name_preference == 'ask':
                    share_name_preference = 'always' if share_name_preference != 'ask' else 'ask'
                
                if share_name_preference == 'never':
                    message += f"""🚗 נהג #{i}:
📱 טלפון: {driver_phone}
📍 נוסע ל: {destination}
⏰ זמן יציאה משוער: {time_info}

"""
                else:
                    driver_name = PreferenceHelper.get_driver_name(driver)
                    message += f"""🚗 נהג #{i}:
👤 שם: {driver_name}
📱 טלפון: {driver_phone}
📍 נוסע ל: {destination}
⏰ זמן יציאה משוער: {time_info}

"""
            
            message += """תוכל ליצור קשר עם כל אחד מהם כדי לתאם את הפרטים המדויקים! 📲
(מומלץ ליצור קשר עם הנהג הראשון שיאשר)

אם מצאת טרמפ שלח ״מצאתי״ כדי שאפסיק לשלוח לך שמות של נהגים."""
        
        # Use atomic operation to ensure only one notification is sent with all approved drivers
        # This prevents multiple simultaneous calls from sending duplicate messages
        # We'll use a flag to track if notification is being sent, and only send if we successfully set it
        
        # Try to atomically set notification_sending flag and update count
        # Only one process will succeed, and that one will send the message
        result = self.db.get_collection("ride_requests").find_one_and_update(
            {
                "_id": ride_request['_id'],
                "$or": [
                    {"approval_notification_driver_count": {"$exists": False}},
                    {"approval_notification_driver_count": {"$lt": len(approved_drivers)}},
                    {"approval_notification_sending": {"$ne": True}}  # Not currently being sent
                ]
            },
            {
                "$set": {
                    "approval_notification_driver_count": len(approved_drivers),
                    "approval_notification_sending": True,  # Mark as being sent
                    "last_approval_notification_at": datetime.now()
                }
            },
            return_document=True
        )
        
        # Only send message if we successfully updated (meaning we're the first to update)
        if result:
            try:
                self.whatsapp_client.send_message(hitchhiker['phone_number'], message)
                
                logger.info(f"✅ Notified hitchhiker {hitchhiker['phone_number']} about {len(approved_drivers)} approved driver(s)")
            finally:
                # Always clear the sending flag, even if sending failed
                self.db.get_collection("ride_requests").update_one(
                    {"_id": ride_request['_id']},
                    {"$unset": {"approval_notification_sending": ""}}
                )
        else:
            logger.debug(f"Another process is already sending notification for ride request {ride_request['_id']}, skipping duplicate")
    
# _log_notification removed - notifications collection no longer exists



