"""
Action executor module for conversation flow actions
Handles execution of actions defined in conversation_flow.json
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class ActionExecutor:
    """Executes actions defined in conversation flow"""
    
    def __init__(self, user_db, matching_service=None, notification_service=None):
        """Initialize action executor
        
        Args:
            user_db: UserDatabase instance
            matching_service: Optional MatchingService instance
            notification_service: Optional NotificationService instance
        """
        self.user_db = user_db
        self.matching_service = matching_service
        self.notification_service = notification_service
    
    def execute(self, phone_number: str, action: str, data: Dict[str, Any]):
        """Execute action by name
        
        Args:
            phone_number: User's phone number
            action: Action name to execute
            data: Additional data for the action
        """
        method_name = f"_execute_{action}"
        if hasattr(self, method_name):
            getattr(self, method_name)(phone_number, data)
        else:
            logger.warning(f"Unknown action: {action}")
    
    def _execute_complete_registration(self, phone_number: str, data: Dict[str, Any]):
        """Complete user registration"""
        self.user_db.complete_registration(phone_number)
        logger.info(f"User {phone_number} completed registration")
    
    def _execute_set_gevaram_as_home(self, phone_number: str, data: Dict[str, Any]):
        """Set Gevaram as home settlement"""
        self.user_db.save_to_profile(phone_number, 'home_settlement', 'גברעם')
        logger.info(f"Set home_settlement to 'גברעם' for {phone_number}")
    
    def _execute_restart_user(self, phone_number: str, data: Dict[str, Any]):
        """Restart user - handled by conversation engine"""
        # This action is handled by conversation engine's _handle_restart
        pass
    
    def _execute_save_ride_request(self, phone_number: str, data: Dict[str, Any]):
        """Save ride request"""
        profile = self.user_db.get_user(phone_number).get('profile', {})
        request_data = {
            'destination': profile.get('destination'),
            'time_range': profile.get('time_range'),
            'specific_datetime': profile.get('specific_datetime')
        }
        self.user_db.add_ride_request(phone_number, request_data)
        logger.info(f"Saved ride request for {phone_number}")
    
    def _execute_save_driver_ride_offer(self, phone_number: str, data: Dict[str, Any]):
        """Save driver ride offer"""
        profile = self.user_db.get_user(phone_number).get('profile', {})
        offer_data = {
            'type': 'driver_ride_offer',
            'departure_timing': profile.get('departure_timing'),
            'destination': profile.get('driver_destination'),
            'origin': 'גברעם'
        }
        self.user_db.add_ride_request(phone_number, offer_data)
        logger.info(f"Saved driver ride offer for {phone_number}: {offer_data}")
    
    def _execute_save_hitchhiker_ride_request(self, phone_number: str, data: Dict[str, Any]):
        """Save hitchhiker ride request and trigger matching"""
        profile = self.user_db.get_user(phone_number).get('profile', {})
        
        # Check if using MongoDB
        if hasattr(self.user_db, '_use_mongo') and self.user_db._use_mongo:
            # Get user from MongoDB
            user = self.user_db.mongo.get_collection("users").find_one({"phone_number": phone_number})
            if not user:
                logger.error(f"User not found in MongoDB: {phone_number}")
                return
            
            from src.database.models import RideRequestModel
            from bson import ObjectId
            
            # Create ride request
            ride_request = RideRequestModel.create(
                requester_id=user['_id'] if isinstance(user['_id'], ObjectId) else ObjectId(user['_id']),
                requester_phone=phone_number,
                request_type="hitchhiker_request",
                destination=profile.get('hitchhiker_destination'),
                origin='גברעם',
                ride_timing=profile.get('ride_timing'),
                specific_datetime=profile.get('specific_datetime'),
                time_range=profile.get('time_range')
            )
            
            # Save to MongoDB
            result = self.user_db.mongo.get_collection("ride_requests").insert_one(ride_request)
            ride_request['_id'] = result.inserted_id
            
            # Find matching drivers if matching service available
            if self.matching_service:
                matching_drivers = self.matching_service.find_matching_drivers(ride_request)
                
                # Create matches
                if matching_drivers:
                    matches = self.matching_service.create_matches(
                        ride_request['_id'],
                        user['_id'] if isinstance(user['_id'], ObjectId) else ObjectId(user['_id']),
                        matching_drivers
                    )
                    
                    # Send notifications if notification service available
                    if self.notification_service:
                        driver_phones = [d['driver_phone'] for d in matching_drivers]
                        self.notification_service.notify_drivers_new_request(
                            ride_request['_id'],
                            driver_phones
                        )
                    
                    logger.info(f"Saved ride request and created {len(matches)} matches")
                else:
                    logger.info(f"Saved ride request but no matching drivers found")
            else:
                logger.info(f"Saved ride request (matching service not available)")
        else:
            # Fallback to JSON
            request_data = {
                'type': 'hitchhiker_ride_request',
                'ride_timing': profile.get('ride_timing'),
                'destination': profile.get('hitchhiker_destination'),
                'origin': 'גברעם'
            }
            self.user_db.add_ride_request(phone_number, request_data)
            logger.info(f"Saved hitchhiker ride request for {phone_number}: {request_data}")
    
    def _execute_save_planned_trip(self, phone_number: str, data: Dict[str, Any]):
        """Save planned trip"""
        self.user_db.add_ride_request(phone_number, data)
        logger.info(f"Saved planned trip for {phone_number}")
    
    def _execute_save_ride_offer(self, phone_number: str, data: Dict[str, Any]):
        """Save ride offer"""
        profile = self.user_db.get_user(phone_number).get('profile', {})
        offer_data = {
            'type': 'ride_offer',
            'details': profile.get('ride_offer_details', data.get('input', ''))
        }
        self.user_db.add_ride_request(phone_number, offer_data)
        logger.info(f"Saved ride offer for {phone_number}")
    
    def _execute_use_default_destination(self, phone_number: str, data: Dict[str, Any]):
        """Use default destination"""
        default_dest = self.user_db.get_profile_value(phone_number, 'default_destination')
        self.user_db.save_to_profile(phone_number, 'destination', default_dest)
    
    def _execute_return_to_idle(self, phone_number: str, data: Dict[str, Any]):
        """Return to idle state"""
        pass  # Just stay in idle
    
    def _execute_show_help_command(self, phone_number: str, data: Dict[str, Any]):
        """Show help command - handled by command handler"""
        pass

