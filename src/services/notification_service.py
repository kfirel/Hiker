"""
Notification Service - Sends WhatsApp notifications for matches
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
import logging
from bson import ObjectId

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for sending notifications"""
    
    def __init__(self, db, whatsapp_client, user_logger=None, conversation_engine=None):
        """
        Initialize notification service
        
        Args:
            db: MongoDBClient instance
            whatsapp_client: WhatsAppClient instance
            user_logger: Optional UserLogger instance for logging notifications
            conversation_engine: Optional ConversationEngine instance for sending through normal flow
        """
        self.db = db
        self.whatsapp_client = whatsapp_client
        self.user_logger = user_logger
        self.conversation_engine = conversation_engine
    
    def notify_drivers_new_request(self, ride_request_id: ObjectId, driver_phones: List[str]):
        """
        Notify drivers about new ride request
        
        For drivers with preference "always" - automatically approve and send details to hitchhiker
        For drivers with preference "ask" - send notification asking for approval
        
        Args:
            ride_request_id: Ride request ID
            driver_phones: List of driver phone numbers
        """
        ride_request = self.db.get_collection("ride_requests").find_one({"_id": ride_request_id})
        hitchhiker = self.db.get_collection("users").find_one({"_id": ride_request['requester_id']})
        
        if not ride_request or not hitchhiker:
            logger.error(f"Ride request or hitchhiker not found: {ride_request_id}")
            return
        
        # Import ApprovalService here to avoid circular imports
        from src.services.approval_service import ApprovalService
        approval_service = ApprovalService(self.db, self.whatsapp_client, self.user_logger)
        
        message = self._build_driver_notification_message(ride_request, hitchhiker)
        
        for driver_phone in driver_phones:
            # Find driver
            driver = self.db.get_collection("users").find_one({"phone_number": driver_phone})
            if not driver:
                continue
            
            # Find matched driver entry in ride_request
            ride_request = self.db.get_collection("ride_requests").find_one({"_id": ride_request_id})
            if not ride_request:
                continue
            
            # Find matched driver entry
            matched_driver = None
            for md in ride_request.get('matched_drivers', []):
                if str(md.get('driver_id')) == str(driver['_id']):
                    matched_driver = md
                    break
            
            if not matched_driver:
                logger.warning(f"Matched driver entry not found for driver {driver_phone} in ride request {ride_request_id}")
                continue
            
            # Check if notification already sent (prevent duplicates)
            if matched_driver.get('notification_sent_to_driver'):
                logger.info(f"Notification already sent to driver {driver_phone} for match {matched_driver.get('match_id')}")
                continue
            
            # Check driver's preference for sharing name
            share_name_preference = driver.get('share_name_with_hitchhiker')
            if not share_name_preference:
                profile = driver.get('profile', {})
                share_name_preference = profile.get('share_name_with_hitchhiker')
            if not share_name_preference:
                share_name_preference = 'ask'
            
            logger.info(f"Driver {driver_phone} share_name_preference: {share_name_preference}")
            
            if share_name_preference == 'always':
                # Driver wants to share details automatically - mark for auto-approval
                logger.info(f"Driver {driver_phone} has 'always' preference - marking for auto-approval")
                
                match_id = matched_driver.get('match_id', '')
                if match_id:
                    # Mark notification as sent and auto-approve in matched_drivers array
                    self.db.get_collection("ride_requests").update_one(
                        {"_id": ride_request_id, "matched_drivers.match_id": match_id},
                        {"$set": {
                            "matched_drivers.$.notification_sent_to_driver": True,
                            "matched_drivers.$.auto_approve": True
                        }}
                    )
                    logger.info(f"✅ Marked match {match_id} for auto-approval (driver {driver_phone} has 'always' preference)")
                else:
                    logger.error(f"❌ Matched driver entry has no match_id, cannot mark for auto-approval")
            else:
                # Driver wants to be asked - send notification with approval buttons
                # Use simple numbers (1/2) - system will find the pending match automatically
                buttons = [
                    {
                        "type": "reply",
                        "reply": {
                            "id": "1",  # 1 = approve (simple number, system finds match)
                            "title": "✅ מאשר"
                        }
                    },
                    {
                        "type": "reply",
                        "reply": {
                            "id": "2",  # 2 = reject (simple number, system finds match)
                            "title": "❌ דוחה"
                        }
                    }
                ]
                
                # Send message through normal flow
                success = self.whatsapp_client.send_message(
                    driver_phone,
                    message,
                    buttons=buttons,
                    state="notification"
                )
                
                if success:
                    # Update matched_driver entry to mark notification as sent
                    match_id = matched_driver.get('match_id', '')
                    if match_id:
                        self.db.get_collection("ride_requests").update_one(
                            {"_id": ride_request_id, "matched_drivers.match_id": match_id},
                            {"$set": {"matched_drivers.$.notification_sent_to_driver": True}}
                        )
                    
                    logger.info(f"✅ Notification sent to driver {driver_phone} for ride request {ride_request_id}")
                else:
                    logger.error(f"❌ Failed to send notification to driver {driver_phone}")
    
    def notify_hitchhiker_matches_found(self, ride_request_id: ObjectId, num_matches: int, matching_drivers: List[Dict[str, Any]] = None):
        """
        Notify hitchhiker that matches were found (before driver approval)
        Send list of ALL matching drivers immediately
        
        Args:
            ride_request_id: Ride request ID
            num_matches: Number of matches found
            matching_drivers: List of matching driver info dicts (optional, for detailed list)
        """
        ride_request = self.db.get_collection("ride_requests").find_one({"_id": ride_request_id})
        if not ride_request:
            logger.error(f"Ride request not found: {ride_request_id}")
            return
        
        # Check if ride request was already marked as "found"
        if ride_request.get('status') == 'found':
            logger.info(f"Ride request {ride_request_id} already marked as found, skipping notification")
            return
        
        hitchhiker = self.db.get_collection("users").find_one({"_id": ride_request['requester_id']})
        if not hitchhiker or not self.whatsapp_client:
            return
        
        hitchhiker_phone = hitchhiker.get('phone_number')
        if not hitchhiker_phone:
            return
        
        destination = ride_request.get('destination', 'יעד')
        
        # Format time range for display
        start_time = ride_request.get('start_time_range')
        end_time = ride_request.get('end_time_range')
        if start_time and end_time:
            time_info = f"{start_time.strftime('%H:%M')}-{end_time.strftime('%H:%M')}"
        else:
            time_info = 'גמיש'
        
        # Build message with list of all matching drivers
        if matching_drivers and len(matching_drivers) > 0:
            # Import PreferenceHelper for consistent name handling
            from src.utils.preference_helper import PreferenceHelper
            
            # Send detailed list of all matching drivers
            if len(matching_drivers) == 1:
                driver_info = matching_drivers[0]
                # Get driver from database to use PreferenceHelper
                driver = self.db.get_collection("users").find_one({"_id": driver_info.get('driver_id')})
                driver_name = PreferenceHelper.get_driver_name(driver) if driver else 'נהג'
                message = f"""🎉 מצאתי לך נהג מתאים!

🚗 נהג: {driver_name}
📍 נוסע ל: {destination}
⏰ זמן יציאה משוער: {time_info}

הנהג יקבל בקרוב התראה על הבקשה שלך.
אם הוא מאשר - תקבל את פרטי הקשר שלו תוך כמה דקות. 📲

(אם הנהג לא יאשר או לא יגיב תוך זמן סביר, אמשיך לחפש לך נהגים אחרים) 🔍"""
            else:
                message = f"""🎉 מצאתי לך {len(matching_drivers)} נהגים מתאימים!

👥 רשימת הנהגים שנמצאו:

"""
                for i, driver_info in enumerate(matching_drivers, 1):
                    # Get driver from database to use PreferenceHelper
                    driver = self.db.get_collection("users").find_one({"_id": driver_info.get('driver_id')})
                    driver_name = PreferenceHelper.get_driver_name(driver) if driver else f'נהג #{i}'
                    message += f"""🚗 נהג #{i}: {driver_name}
📍 נוסע ל: {destination}
⏰ זמן יציאה משוער: {time_info}

"""
                
                message += """הנהגים יקבלו בקרוב התראה על הבקשה שלך.
הנהג הראשון שיאשר - תקבל את פרטי הקשר שלו תוך כמה דקות. 📲

(אם אף אחד לא יאשר, אמשיך לחפש לך נהגים אחרים) 🔍"""
        else:
            # Fallback to simple message if matching_drivers not provided
            if num_matches == 1:
                message = """🎉 מצאתי לך נהג מתאים!

הנהג יקבל בקרוב התראה על הבקשה שלך.
אם הוא מאשר - תקבל את פרטי הקשר שלו תוך כמה דקות. 📲

(אם הנהג לא יאשר או לא יגיב תוך זמן סביר, אמשיך לחפש לך נהגים אחרים) 🔍"""
            else:
                message = f"""🎉 מצאתי לך {num_matches} נהגים מתאימים!

הנהגים יקבלו בקרוב התראה על הבקשה שלך.
הנהג הראשון שיאשר - תקבל את פרטי הקשר שלו תוך כמה דקות. 📲

(אם אף אחד לא יאשר, אמשיך לחפש לך נהגים אחרים) 🔍"""
        
        # Send message
        self.whatsapp_client.send_message(
            hitchhiker_phone,
            message,
            state="match_found_notification"
        )
        
        logger.info(f"✅ Notified hitchhiker {hitchhiker_phone} that {num_matches} match(es) were found")
    
    def _build_driver_notification_message(self, ride_request: Dict[str, Any], 
                                          hitchhiker: Dict[str, Any]) -> str:
        """Build notification message for driver"""
        hitchhiker_name = hitchhiker.get('full_name') or hitchhiker.get('whatsapp_name') or 'טרמפיסט'
        origin = ride_request.get('origin', 'גברעם')
        destination = ride_request.get('destination', 'יעד')
        
        # Format time range for display
        start_time = ride_request.get('start_time_range')
        end_time = ride_request.get('end_time_range')
        if start_time and end_time:
            time_info = f"{start_time.strftime('%H:%M')}-{end_time.strftime('%H:%M')}"
        else:
            time_info = 'גמיש'
        
        return f"""🚗 בקשה חדשה לטרמפ!

👤 טרמפיסט: {hitchhiker_name}
📍 מ: {origin}
🎯 ל: {destination}
⏰ טווח זמן נסיעה: {time_info}
(הטרמפיסט צריך להגיע ליעד בטווח השעות הזה)

האם אתה יכול לעזור?"""
    
# _log_notification removed - notifications collection no longer exists


