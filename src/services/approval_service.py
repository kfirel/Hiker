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
    
    def __init__(self, db, whatsapp_client=None):
        """
        Initialize approval service
        
        Args:
            db: MongoDBClient instance
            whatsapp_client: WhatsAppClient instance (optional)
        """
        self.db = db
        self.whatsapp_client = whatsapp_client
    
    def driver_approve(self, match_id: str, driver_phone: str) -> bool:
        """
        Driver approves a match
        
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
                    "status": "approved",
                    "driver_response": "approved",
                    "driver_response_at": datetime.now(),
                    "updated_at": datetime.now()
                }
            }
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
            
            # Notify hitchhiker if whatsapp client available
            if self.whatsapp_client:
                self._notify_hitchhiker_approved(match, driver, ride_request)
        
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
    
    def _notify_hitchhiker_approved(self, match: Dict[str, Any], driver: Dict[str, Any], 
                                    ride_request: Dict[str, Any]):
        """Send approval notification to hitchhiker"""
        hitchhiker = self.db.get_collection("users").find_one({"_id": match['hitchhiker_id']})
        if not hitchhiker or not self.whatsapp_client:
            return
        
        driver_name = driver.get('full_name') or driver.get('whatsapp_name') or 'נהג'
        destination = ride_request.get('destination', 'יעד')
        time_info = ride_request.get('specific_datetime') or ride_request.get('time_range') or 'גמיש'
        
        message = f"""🎉 מעולה! נהג אישר את הבקשה שלך!

🚗 נהג: {driver_name}
📍 יעד: {destination}
⏰ זמן: {time_info}

הנהג יצור איתך קשר בקרוב! 📲"""
        
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


