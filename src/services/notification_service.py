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
    
    def __init__(self, db, whatsapp_client):
        """
        Initialize notification service
        
        Args:
            db: MongoDBClient instance
            whatsapp_client: WhatsAppClient instance
        """
        self.db = db
        self.whatsapp_client = whatsapp_client
    
    def notify_drivers_new_request(self, ride_request_id: ObjectId, driver_phones: List[str]):
        """
        Notify drivers about new ride request
        
        Args:
            ride_request_id: Ride request ID
            driver_phones: List of driver phone numbers
        """
        ride_request = self.db.get_collection("ride_requests").find_one({"_id": ride_request_id})
        hitchhiker = self.db.get_collection("users").find_one({"_id": ride_request['requester_id']})
        
        if not ride_request or not hitchhiker:
            logger.error(f"Ride request or hitchhiker not found: {ride_request_id}")
            return
        
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
                # Send notification with approval buttons
                buttons = [
                    {
                        "type": "reply",
                        "reply": {
                            "id": f"approve_{match['match_id']}",
                            "title": "✅ מאשר"
                        }
                    },
                    {
                        "type": "reply",
                        "reply": {
                            "id": f"reject_{match['match_id']}",
                            "title": "❌ דוחה"
                        }
                    }
                ]
                
                self.whatsapp_client.send_interactive_buttons(
                    driver_phone,
                    message,
                    buttons
                )
                
                # Update match
                self.db.get_collection("matches").update_one(
                    {"_id": match['_id']},
                    {"$set": {"notification_sent_to_driver": True}}
                )
                
                # Log notification
                self._log_notification(
                    driver['_id'],
                    driver_phone,
                    "ride_request",
                    ride_request_id,
                    match['_id']
                )
    
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


