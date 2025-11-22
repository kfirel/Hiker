"""
Approval Service - Handles driver approval/rejection of ride requests
"""

from datetime import datetime
from typing import Dict, Any, Optional
import logging
from bson import ObjectId

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
            match_id: Match ID
            driver_phone: Driver's phone number
            is_auto_approval: If True, this is an automatic approval (driver won't receive confirmation message)
            
        Returns:
            True if successful
        """
        match = self.db.get_collection("matches").find_one({"match_id": match_id})
        if not match:
            logger.error(f"Match not found: {match_id}")
            return False
        
        # Verify driver
        driver = self.db.get_collection("users").find_one({"phone_number": driver_phone})
        if not driver or str(driver['_id']) != str(match['driver_id']):
            logger.error(f"Driver verification failed for match {match_id}")
            return False
        
        # Update match
        update_data = {
            "status": "approved",
            "driver_response": "approved",
            "driver_response_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        # Store is_auto_approval flag so we know not to send confirmation message to driver
        if is_auto_approval:
            update_data["is_auto_approval"] = True
        
        self.db.get_collection("matches").update_one(
            {"match_id": match_id},
            {"$set": update_data}
        )
        
        # Update ride request
        ride_request = self.db.get_collection("ride_requests").find_one({"_id": match['ride_request_id']})
        if ride_request:
            self.db.get_collection("ride_requests").update_one(
                {"_id": match['ride_request_id']},
                {
                    "$set": {
                        "status": "approved",
                        "approved_driver_id": match['driver_id'],
                        "approved_at": datetime.now(),
                        "updated_at": datetime.now()
                    }
                }
            )
            
            # Reject other pending matches for this request
            self.db.get_collection("matches").update_many(
                {
                    "ride_request_id": match['ride_request_id'],
                    "match_id": {"$ne": match_id},
                    "status": "pending_approval"
                },
                {
                    "$set": {
                        "status": "rejected",
                        "driver_response": "rejected",
                        "updated_at": datetime.now()
                    }
                }
            )
            
            # Check driver's preference for sharing name
            # save_to_profile saves directly to root level of user document in MongoDB
            # But get_user returns it nested in 'profile' dict, so check both places
            share_name_preference = driver.get('share_name_with_hitchhiker')
            if not share_name_preference:
                # Check in profile dict (as returned by get_user)
                profile = driver.get('profile', {})
                share_name_preference = profile.get('share_name_with_hitchhiker')
            # Default to 'always' for backward compatibility
            if not share_name_preference:
                share_name_preference = 'always'
            
            logger.info(f"Driver {driver_phone} share_name_preference: {share_name_preference}")
            
            # Notify hitchhiker if whatsapp client available
            if self.whatsapp_client:
                if share_name_preference == 'ask':
                    # Ask driver first before notifying hitchhiker
                    self._ask_driver_about_name_sharing(match_id, driver_phone, match, ride_request)
                    # Don't send confirmation message yet - wait for driver's response
                    return True
                else:
                    # Notify hitchhiker immediately (with or without name based on preference)
                    self._notify_hitchhiker_approved(match, driver, ride_request, match_id)
        
        logger.info(f"Match {match_id} approved by driver {driver_phone}")
        return True
    
    def driver_reject(self, match_id: str, driver_phone: str) -> bool:
        """
        Driver rejects a match
        
        Args:
            match_id: Match ID
            driver_phone: Driver's phone number
            
        Returns:
            True if successful
        """
        match = self.db.get_collection("matches").find_one({"match_id": match_id})
        if not match:
            logger.error(f"Match not found: {match_id}")
            return False
        
        # Verify driver
        driver = self.db.get_collection("users").find_one({"phone_number": driver_phone})
        if not driver or str(driver['_id']) != str(match['driver_id']):
            logger.error(f"Driver verification failed for match {match_id}")
            return False
        
        # Update match
        self.db.get_collection("matches").update_one(
            {"match_id": match_id},
            {
                "$set": {
                    "status": "rejected",
                    "driver_response": "rejected",
                    "driver_response_at": datetime.now(),
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
        
        hitchhiker_name = hitchhiker.get('full_name') or hitchhiker.get('whatsapp_name') or 'טרמפיסט'
        destination = ride_request.get('destination', 'יעד')
        
        # Store match_id in driver's context for later processing
        self.db.get_collection("users").update_one(
            {"phone_number": driver_phone},
            {"$set": {"pending_name_share_match_id": match_id}}
        )
        
        # Ask driver
        message = f"""✅ אישרת את הבקשה של {hitchhiker_name}!

האם לשלוח את הפרטים שלך לטרמפיסט?

1. בטח
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
                    # Try to find most recent pending match
                    matches = list(self.db.get_collection("matches").find({
                        "driver_id": driver['_id'],
                        "status": "pending_approval"
                    }).sort("matched_at", -1).limit(1))
                    if matches:
                        match_id = matches[0].get('match_id', '')
            
            if not match_id:
                logger.error(f"Could not find match_id for driver {driver_phone}")
                if self.whatsapp_client:
                    self.whatsapp_client.send_message(
                        driver_phone,
                        "❌ שגיאה: לא נמצאה בקשה ממתינה. נסה שוב או פנה לתמיכה."
                    )
                return False
        
        # Get match and driver
        match = self.db.get_collection("matches").find_one({"match_id": match_id})
        if not match:
            logger.error(f"Match not found: {match_id}")
            if self.whatsapp_client:
                self.whatsapp_client.send_message(
                    driver_phone,
                    "❌ שגיאה: לא נמצאה התאמה. נסה שוב או פנה לתמיכה."
                )
            return False
        
        driver = self.db.get_collection("users").find_one({"phone_number": driver_phone})
        if not driver or str(driver['_id']) != str(match['driver_id']):
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
        
        # Get ride request
        ride_request = self.db.get_collection("ride_requests").find_one({"_id": match['ride_request_id']})
        if not ride_request:
            logger.error(f"Ride request not found: {match['ride_request_id']}")
            return False
        
        # Notify hitchhiker with or without name based on driver's choice
        if share_name:
            # Create temporary driver dict with name (ensure preference is 'always')
            driver_with_name = driver.copy()
            driver_with_name['share_name_with_hitchhiker'] = 'always'
            self._notify_hitchhiker_approved(match, driver_with_name, ride_request, match_id)
            confirmation = "✅ השם שלך נשלח לטרמפיסט! הוא יצור איתך קשר בקרוב. 📲"
        else:
            # Create temporary driver dict without name (set preference to 'never')
            driver_without_name = driver.copy()
            driver_without_name['share_name_with_hitchhiker'] = 'never'
            self._notify_hitchhiker_approved(match, driver_without_name, ride_request, match_id)
            confirmation = "✅ הטרמפיסט קיבל את פרטי הקשר שלך (ללא שם). הוא יצור איתך קשר בקרוב. 📲"
        
        self.whatsapp_client.send_message(driver_phone, confirmation)
        return True
    
    def _notify_hitchhiker_approved(self, match: Dict[str, Any], driver: Dict[str, Any], 
                                    ride_request: Dict[str, Any], match_id: str = None):
        """Send approval notification to hitchhiker with driver contact details"""
        hitchhiker = self.db.get_collection("users").find_one({"_id": match['hitchhiker_id']})
        if not hitchhiker or not self.whatsapp_client:
            return
        
        driver_phone = driver.get('phone_number', '')
        destination = ride_request.get('destination', 'יעד')
        time_info = ride_request.get('specific_datetime') or ride_request.get('time_range') or 'גמיש'
        
        # Check driver's preference for sharing name
        # save_to_profile saves directly to root level of user document in MongoDB
        # But get_user returns it nested in 'profile' dict, so check both places
        share_name_preference = driver.get('share_name_with_hitchhiker')
        if not share_name_preference:
            # Check in profile dict (as returned by get_user)
            profile = driver.get('profile', {})
            share_name_preference = profile.get('share_name_with_hitchhiker')
        # Default to 'always' for backward compatibility
        if not share_name_preference:
            share_name_preference = 'always'
        
        # Build message based on preference
        if share_name_preference == 'never':
            # Don't send driver name - only phone number
            message = f"""🎉 מעולה! נהג מצא אותך מתאים!

👤 פרטי הנהג:
📱 טלפון: {driver_phone}
📍 נוסע ל: {destination}
⏰ זמן: {time_info}

תוכל ליצור איתו קשר עכשיו כדי לתאם את הפרטים! 📲"""
        else:  # 'always' or default (should not be 'ask' here as it's handled separately)
            # Send driver name immediately
            driver_name = driver.get('full_name') or driver.get('whatsapp_name') or 'נהג'
            message = f"""🎉 מעולה! נהג מצא אותך מתאים!

👤 פרטי הנהג:
🚗 שם: {driver_name}
📱 טלפון: {driver_phone}
📍 נוסע ל: {destination}
⏰ זמן: {time_info}

תוכל ליצור איתו קשר עכשיו כדי לתאם את הפרטים! 📲"""
        
        self.whatsapp_client.send_message(hitchhiker['phone_number'], message)
        
        # Log notification
        self._log_notification(
            hitchhiker['_id'],
            hitchhiker['phone_number'],
            "approval",
            ride_request['_id'],
            match['_id']
        )
    
    def _log_notification(self, recipient_id: ObjectId, recipient_phone: str,
                         notification_type: str, ride_request_id: ObjectId = None,
                         match_id: ObjectId = None):
        """Log notification to database"""
        notification = {
            "recipient_id": recipient_id,
            "recipient_phone": recipient_phone,
            "type": notification_type,
            "title": "נהג אישר את הבקשה",
            "message": "נהג אישר את הבקשה שלך",
            "ride_request_id": ride_request_id,
            "match_id": match_id,
            "status": "sent",
            "sent_at": datetime.now(),
            "created_at": datetime.now()
        }
        
        self.db.get_collection("notifications").insert_one(notification)



