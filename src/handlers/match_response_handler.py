"""
Match Response Handler - Handles driver approval/rejection responses
"""

import logging
from typing import Optional
from bson import ObjectId

from src.utils.button_parser import ButtonParser
from src.utils.preference_helper import PreferenceHelper
from src.services.approval_service import ApprovalService

logger = logging.getLogger(__name__)


class MatchResponseHandler:
    """Handles match approval/rejection responses"""
    
    def __init__(self, user_db, whatsapp_client, user_logger):
        """
        Initialize match response handler
        
        Args:
            user_db: UserDatabase instance
            whatsapp_client: WhatsAppClient instance
            user_logger: UserLogger instance
        """
        self.user_db = user_db
        self.whatsapp_client = whatsapp_client
        self.user_logger = user_logger
        self.button_parser = ButtonParser()
    
    def handle(self, driver_phone: str, button_id: str) -> bool:
        """
        Handle match response button click
        
        Args:
            driver_phone: Driver's phone number
            button_id: Button ID string
            
        Returns:
            True if handled successfully, False otherwise
        """
        try:
            # Parse button ID
            match_id, is_approval = self.button_parser.parse_match_response(button_id)
            
            if match_id is None and is_approval is None:
                logger.error(f"Invalid button ID format: {button_id}")
                return False
            
            # If match_id is empty or just "MATCH_", find from database
            if not match_id or match_id == 'MATCH_':
                match_id = self._find_match_from_db(driver_phone)
                if not match_id:
                    # Don't send error message if this was just "1" or "2" without match_id
                    # This might be a regular choice in a conversation flow, not a match approval
                    if button_id in ['1', '2']:
                        logger.debug(f"User {driver_phone} sent '{button_id}' but no pending match found - likely a conversation choice, not match approval")
                        return False
                    # Only send error if this was explicitly a match response button
                    self.whatsapp_client.send_message(
                        driver_phone,
                        "מצטער, לא נמצאה בקשה ממתינה לאישור. נסה שוב מאוחר יותר."
                    )
                    return False
            
            # Initialize approval service
            approval_service = ApprovalService(
                self.user_db.mongo,
                self.whatsapp_client,
                self.user_logger
            )
            
            # Handle approval or rejection
            if is_approval:
                return self._handle_approval(driver_phone, match_id, approval_service)
            else:
                return self._handle_rejection(driver_phone, match_id, approval_service)
        
        except Exception as e:
            logger.error(f"Error handling match response: {e}", exc_info=True)
            self.user_logger.log_error(
                driver_phone,
                f"Error handling match response '{button_id}'",
                e
            )
            self.whatsapp_client.send_message(
                driver_phone,
                "מצטער, אירעה שגיאה. נסה שוב או הקש 'עזרה'."
            )
            return False
    
    def _find_match_from_db(self, driver_phone: str) -> Optional[str]:
        """
        Find most recent pending match for driver from ride_requests.matched_drivers array
        
        Args:
            driver_phone: Driver's phone number
            
        Returns:
            Match ID or None if not found
        """
        driver = self.user_db.mongo.get_collection("users").find_one({"phone_number": driver_phone})
        if not driver:
            logger.error(f"Driver not found: {driver_phone}")
            self.whatsapp_client.send_message(
                driver_phone,
                "מצטער, לא נמצא משתמש במערכת. נסה שוב מאוחר יותר."
            )
            return None
        
        # Find ride requests with this driver in matched_drivers array
        ride_requests = list(self.user_db.mongo.get_collection("ride_requests").find({
            "matched_drivers.driver_id": driver['_id'],
            "matched_drivers.status": "pending_approval",
            "matched_drivers.notification_sent_to_driver": True
        }).sort("created_at", -1))
        
        # Find the most recent matched driver entry
        for ride_request in ride_requests:
            matched_drivers = ride_request.get('matched_drivers', [])
            for md in sorted(matched_drivers, key=lambda x: x.get('matched_at', ''), reverse=True):
                if (str(md.get('driver_id')) == str(driver['_id']) and 
                    md.get('status') == 'pending_approval' and 
                    md.get('notification_sent_to_driver')):
                    match_id = md.get('match_id', '')
                    if match_id:
                        logger.info(f"Found match_id from database: {match_id}")
                        return match_id
        
        return None
    
    def _handle_approval(self, driver_phone: str, match_id: str, approval_service: ApprovalService) -> bool:
        """
        Handle driver approval
        
        Args:
            driver_phone: Driver's phone number
            match_id: Match ID
            approval_service: ApprovalService instance
            
        Returns:
            True if successful
        """
        # Check if this is an auto-approval - find in ride_requests.matched_drivers
        ride_request = self.user_db.mongo.get_collection("ride_requests").find_one({
            "matched_drivers.match_id": match_id
        })
        is_auto_approval = False
        if ride_request:
            for md in ride_request.get('matched_drivers', []):
                if md.get('match_id') == match_id:
                    is_auto_approval = md.get('auto_approve', False)
                    break
        
        success = approval_service.driver_approve(match_id, driver_phone, is_auto_approval=is_auto_approval)
        
        if not success:
            self.whatsapp_client.send_message(
                driver_phone,
                "❌ שגיאה באישור הבקשה. נסה שוב או פנה לתמיכה.",
                state="match_response"
            )
            return False
        
        # Don't send confirmation message if this was an auto-approval
        if is_auto_approval:
            logger.info(f"Auto-approval for match {match_id} - skipping confirmation message to driver")
            return True
        
        # Check if driver needs to be asked about name sharing
        driver = self.user_db.mongo.get_collection("users").find_one({"phone_number": driver_phone})
        share_name_preference = PreferenceHelper.get_share_name_preference(driver) if driver else 'ask'
        
        if share_name_preference == 'ask':
            # Driver will be asked separately - don't send confirmation yet
            return True
        
        # Build and send confirmation message
        # Get match info from ride_request
        ride_request = self.user_db.mongo.get_collection("ride_requests").find_one({
            "matched_drivers.match_id": match_id
        })
        match_dict = None
        if ride_request:
            for md in ride_request.get('matched_drivers', []):
                if md.get('match_id') == match_id:
                    match_dict = md.copy()
                    match_dict['ride_request_id'] = ride_request['_id']
                    break
        
        message = self._build_approval_message(match_dict, ride_request)
        self.whatsapp_client.send_message(driver_phone, message, state="match_response")
        return True
    
    def _handle_rejection(self, driver_phone: str, match_id: str, approval_service: ApprovalService) -> bool:
        """
        Handle driver rejection
        
        Args:
            driver_phone: Driver's phone number
            match_id: Match ID
            approval_service: ApprovalService instance
            
        Returns:
            True if successful
        """
        success = approval_service.driver_reject(match_id, driver_phone)
        
        if not success:
            self.whatsapp_client.send_message(
                driver_phone,
                "❌ שגיאה בדחיית הבקשה. נסה שוב או פנה לתמיכה.",
                state="match_response"
            )
            return False
        
        # Build and send rejection message
        # Get match info from ride_request
        ride_request = self.user_db.mongo.get_collection("ride_requests").find_one({
            "matched_drivers.match_id": match_id
        })
        match_dict = None
        if ride_request:
            for md in ride_request.get('matched_drivers', []):
                if md.get('match_id') == match_id:
                    match_dict = md.copy()
                    match_dict['ride_request_id'] = ride_request['_id']
                    break
        
        message = self._build_rejection_message(match_dict, ride_request)
        self.whatsapp_client.send_message(driver_phone, message, state="match_response")
        return True
    
    def _build_approval_message(self, match: dict, ride_request: dict = None) -> str:
        """
        Build approval confirmation message
        
        Args:
            match: Matched driver entry dict
            ride_request: Ride request document (optional, will fetch if not provided)
            
        Returns:
            Message string
        """
        if not match and not ride_request:
            return "✅ אישרת את הבקשה!"
        
        # Get ride request if not provided
        if not ride_request and match:
            ride_request = self.user_db.mongo.get_collection("ride_requests").find_one({"_id": match.get('ride_request_id')})
        
        if not ride_request:
            return "✅ אישרת את הבקשה!"
        
        # Get hitchhiker info
        hitchhiker = self.user_db.mongo.get_collection("users").find_one({"_id": ride_request['requester_id']})
        hitchhiker_name = PreferenceHelper.get_hitchhiker_name(hitchhiker)
        destination = ride_request.get('destination', 'יעד')
        
        return f"✅ אישרת את הבקשה!\n\nהטרמפיסט {hitchhiker_name} (ל-{destination}) יקבל את פרטי הקשר שלך ויצור איתך קשר בקרוב. 📲"
    
    def _build_rejection_message(self, match: dict, ride_request: dict = None) -> str:
        """
        Build rejection confirmation message
        
        Args:
            match: Matched driver entry dict
            ride_request: Ride request document (optional, will fetch if not provided)
            
        Returns:
            Message string
        """
        if not match and not ride_request:
            return "❌ דחית את הבקשה."
        
        # Get ride request if not provided
        if not ride_request and match:
            ride_request = self.user_db.mongo.get_collection("ride_requests").find_one({"_id": match.get('ride_request_id')})
        
        if not ride_request:
            return "❌ דחית את הבקשה."
        
        # Get hitchhiker info
        hitchhiker = self.user_db.mongo.get_collection("users").find_one({"_id": ride_request['requester_id']})
        hitchhiker_name = PreferenceHelper.get_hitchhiker_name(hitchhiker)
        destination = ride_request.get('destination', 'יעד')
        
        return f"❌ דחית את הבקשה של {hitchhiker_name} (ל-{destination}).\n\nהטרמפיסט ימשיך לחפש נהגים אחרים. 👍"

