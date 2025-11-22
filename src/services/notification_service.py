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
            # Find match for this driver
            driver = self.db.get_collection("users").find_one({"phone_number": driver_phone})
            if not driver:
                continue
            
            match = self.db.get_collection("matches").find_one({
                "ride_request_id": ride_request_id,
                "driver_id": driver['_id']
            })
            
            if match:
                # Check if notification already sent (prevent duplicates)
                if match.get('notification_sent_to_driver'):
                    logger.info(f"Notification already sent to driver {driver_phone} for match {match['match_id']}")
                    continue
                
                # Check driver's preference for sharing name
                # save_to_profile saves directly to root level of user document in MongoDB
                # But get_user returns it nested in 'profile' dict, so check both places
                share_name_preference = driver.get('share_name_with_hitchhiker')
                if not share_name_preference:
                    # Check in profile dict (as returned by get_user)
                    profile = driver.get('profile', {})
                    share_name_preference = profile.get('share_name_with_hitchhiker')
                # Default to 'ask' for backward compatibility (to maintain current behavior)
                if not share_name_preference:
                    share_name_preference = 'ask'
                
                logger.info(f"Driver {driver_phone} share_name_preference: {share_name_preference}")
                
                if share_name_preference == 'always':
                    # Driver wants to share details automatically - mark for auto-approval
                    # We'll approve after the hitchhiker receives confirmation message
                    logger.info(f"Driver {driver_phone} has 'always' preference - marking match {match['match_id']} for auto-approval")
                    
                    # Mark match for auto-approval (will be processed after hitchhiker confirmation)
                    match_id = match.get('match_id', '')
                    if match_id:
                        # Mark notification as sent (even though we didn't send one to driver)
                        # and mark for auto-approval
                        self.db.get_collection("matches").update_one(
                            {"_id": match['_id']},
                            {"$set": {
                                "notification_sent_to_driver": True,
                                "auto_approve": True  # Flag to trigger auto-approval later
                            }}
                        )
                        logger.info(f"✅ Marked match {match_id} for auto-approval (driver {driver_phone} has 'always' preference)")
                    else:
                        logger.error(f"❌ Match {match['_id']} has no match_id, cannot mark for auto-approval")
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
                    
                    # Send message through normal flow (same as regular messages in app.py)
                    # Logging is now automatic in WhatsAppClient.send_message (lowest level)
                    success = self.whatsapp_client.send_message(
                        driver_phone,
                        message,
                        buttons=buttons,
                        state="notification"
                    )
                    
                    if success:
                        # Update match to mark notification as sent (BEFORE logging to prevent duplicates)
                        self.db.get_collection("matches").update_one(
                            {"_id": match['_id']},
                            {"$set": {"notification_sent_to_driver": True}}
                        )
                        
                        # Logging is now automatic in WhatsAppClient.send_message (lowest level)
                        # The message is already logged when send_message is called
                        
                        # Log notification to database
                        self._log_notification(
                            driver['_id'],
                            driver_phone,
                            "ride_request",
                            ride_request_id,
                            match['_id']
                        )
                        
                        logger.info(f"✅ Notification sent to driver {driver_phone} for ride request {ride_request_id}")
                    else:
                        logger.error(f"❌ Failed to send notification to driver {driver_phone}")
    
    def notify_hitchhiker_matches_found(self, ride_request_id: ObjectId, num_matches: int):
        """
        Notify hitchhiker that matches were found (before driver approval)
        
        Args:
            ride_request_id: Ride request ID
            num_matches: Number of matches found
        """
        ride_request = self.db.get_collection("ride_requests").find_one({"_id": ride_request_id})
        if not ride_request:
            logger.error(f"Ride request not found: {ride_request_id}")
            return
        
        hitchhiker = self.db.get_collection("users").find_one({"_id": ride_request['requester_id']})
        if not hitchhiker or not self.whatsapp_client:
            return
        
        hitchhiker_phone = hitchhiker.get('phone_number')
        if not hitchhiker_phone:
            return
        
        # Build message
        if num_matches == 1:
            message = "🎉 מצאתי לך נהג מתאים! הוא יקבל בקרוב התראה ואם הוא מאשר - תקבל את פרטי הקשר שלו. 📲"
        else:
            message = f"🎉 מצאתי לך {num_matches} נהגים מתאימים! הם יקבלו בקרוב התראה ואם אחד מהם מאשר - תקבל את פרטי הקשר שלו. 📲"
        
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
        time_info = ride_request.get('specific_datetime') or ride_request.get('time_range') or 'גמיש'
        
        return f"""🚗 בקשה חדשה לטרמפ!

👤 טרמפיסט: {hitchhiker_name}
📍 מ: {origin}
🎯 ל: {destination}
⏰ זמן: {time_info}

האם אתה יכול לעזור?"""
    
    def _log_notification(self, recipient_id: ObjectId, recipient_phone: str,
                         notification_type: str, ride_request_id: ObjectId = None,
                         match_id: ObjectId = None):
        """Log notification to database"""
        notification = {
            "recipient_id": recipient_id,
            "recipient_phone": recipient_phone,
            "type": notification_type,
            "title": "בקשה חדשה לטרמפ",
            "message": "יש בקשה חדשה לטרמפ",
            "ride_request_id": ride_request_id,
            "match_id": match_id,
            "status": "sent",
            "sent_at": datetime.now(),
            "created_at": datetime.now()
        }
        
        self.db.get_collection("notifications").insert_one(notification)


