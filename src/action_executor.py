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
        """Save driver ride offer and trigger matching"""
        profile = self.user_db.get_user(phone_number).get('profile', {})
        
        # Get user from MongoDB
        user = self.user_db.mongo.get_collection("users").find_one({"phone_number": phone_number})
        if not user:
            logger.error(f"User not found in MongoDB: {phone_number}")
            return
        
        from src.database.models import RideRequestModel
        from bson import ObjectId
        
        # Create driver offer
        driver_offer = RideRequestModel.create(
            requester_id=user['_id'] if isinstance(user['_id'], ObjectId) else ObjectId(user['_id']),
            requester_phone=phone_number,
            request_type="driver_offer",
            destination=profile.get('driver_destination'),
            origin='גברעם',
            ride_timing=profile.get('departure_timing')
        )
        
        # Save to MongoDB
        result = self.user_db.mongo.get_collection("ride_requests").insert_one(driver_offer)
        driver_offer['_id'] = result.inserted_id
        
        # Find matching hitchhikers if matching service available
        if self.matching_service:
            driver_info = {
                'driver_id': user['_id'],
                'driver_phone': phone_number,
                'driver_name': user.get('full_name') or user.get('whatsapp_name')
            }
            
            matching_requests = self.matching_service.find_matching_hitchhikers(
                driver_info,
                destination=profile.get('driver_destination'),
                departure_time=None,  # Driver offers don't have fixed departure time
                days=None
            )
            
            # Create matches
            if matching_requests:
                matches = self.matching_service.create_matches_for_driver(
                    user['_id'] if isinstance(user['_id'], ObjectId) else ObjectId(user['_id']),
                    phone_number,
                    matching_requests,
                    offer_id=driver_offer['_id']
                )
                
                # Send notifications if notification service available
                if self.notification_service:
                    # Notify driver about matches found
                    if matches:
                        logger.info(f"Found {len(matches)} matching hitchhikers for driver {phone_number}")
                        # Note: We could notify driver here, but typically we notify hitchhikers
                        # when they create requests, not drivers when they create offers
                
                logger.info(f"Saved driver offer and created {len(matches)} matches")
            else:
                logger.info(f"Saved driver offer but no matching hitchhikers found")
        else:
            logger.warning(f"Matching service not available - cannot find matching hitchhikers")
    
    def _execute_save_hitchhiker_ride_request(self, phone_number: str, data: Dict[str, Any]):
        """Save hitchhiker ride request and trigger matching"""
        logger.info(f"🔄 _execute_save_hitchhiker_ride_request called for {phone_number}")
        
        # Get user from MongoDB
        user = self.user_db.mongo.get_collection("users").find_one({"phone_number": phone_number})
        if not user:
            logger.error(f"User not found in MongoDB: {phone_number}")
            return
        
        logger.info(f"📊 MongoDB user fields: {list(user.keys())}")
        
        # Get values directly from MongoDB user document (like we do for routines)
        hitchhiker_destination = user.get('hitchhiker_destination')
        ride_timing = user.get('ride_timing')
        specific_datetime = user.get('specific_datetime')
        time_range = user.get('time_range')
        
        logger.info(f"📝 Ride request data from MongoDB: destination={hitchhiker_destination}, ride_timing={ride_timing}, time_range={time_range}")
        
        if not hitchhiker_destination:
            logger.error(f"No hitchhiker_destination found for {phone_number}")
            return
        
        from src.database.models import RideRequestModel
        from bson import ObjectId
        
        # Create ride request
        ride_request = RideRequestModel.create(
            requester_id=user['_id'] if isinstance(user['_id'], ObjectId) else ObjectId(user['_id']),
            requester_phone=phone_number,
            request_type="hitchhiker_request",
            destination=hitchhiker_destination,
            origin='גברעם',
            ride_timing=ride_timing,
            specific_datetime=specific_datetime,
            time_range=time_range
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
                # Use a set to track which drivers we've already notified (prevent duplicates)
                if self.notification_service:
                    driver_phones = [d['driver_phone'] for d in matching_drivers]
                    # Remove duplicates
                    driver_phones = list(set(driver_phones))
                    logger.info(f"🔔 Sending notifications to {len(driver_phones)} driver(s): {driver_phones}")
                    self.notification_service.notify_drivers_new_request(
                        ride_request['_id'],
                        driver_phones
                    )
                    
                    # Notify hitchhiker that matches were found (before driver approval)
                    self.notification_service.notify_hitchhiker_matches_found(
                        ride_request['_id'],
                        len(matches)
                    )
                    
                    # Note: Auto-approvals will be processed after the confirmation message is sent
                    # This is handled in conversation_engine.py after the action completes
                
                logger.info(f"Saved ride request and created {len(matches)} matches")
            else:
                logger.info(f"Saved ride request but no matching drivers found")
        else:
            logger.warning(f"Matching service not available - cannot find matching drivers")
    
    def _process_auto_approvals(self, ride_request_id):
        """Process auto-approvals for drivers with 'always' preference"""
        from src.services.approval_service import ApprovalService
        from bson import ObjectId
        
        # Find all matches marked for auto-approval that haven't been processed yet
        # Use atomic operation to prevent race conditions
        matches = list(self.user_db.mongo.get_collection("matches").find({
            "ride_request_id": ride_request_id,
            "auto_approve": True,
            "status": "pending_approval",
            "auto_approval_notification_sent": {"$ne": True}  # Only if not already sent
        }))
        
        if not matches:
            return
        
        approval_service = ApprovalService(
            self.user_db.mongo,
            self.notification_service.whatsapp_client if self.notification_service else None,
            self.notification_service.user_logger if self.notification_service else None
        )
        
        for match in matches:
            match_id = match.get('match_id', '')
            driver_id = match.get('driver_id')
            
            if not match_id or not driver_id:
                continue
            
            # Use atomic operation to mark match as being processed
            # This prevents race conditions if function is called multiple times
            updated_match = self.user_db.mongo.get_collection("matches").find_one_and_update(
                {
                    "_id": match['_id'],
                    "auto_approve": True,
                    "status": "pending_approval",
                    "auto_approval_notification_sent": {"$ne": True}
                },
                {
                    "$set": {
                        "auto_approval_processing": True  # Mark as being processed
                    }
                },
                return_document=True
            )
            
            # If match was already processed by another call, skip it
            if not updated_match:
                logger.info(f"Match {match_id} already being processed, skipping")
                continue
            
            # Get driver phone number
            driver = self.user_db.mongo.get_collection("users").find_one({"_id": driver_id})
            if not driver:
                # Clear processing flag if driver not found
                self.user_db.mongo.get_collection("matches").update_one(
                    {"_id": match['_id']},
                    {"$unset": {"auto_approval_processing": ""}}
                )
                continue
            
            driver_phone = driver.get('phone_number')
            if not driver_phone:
                # Clear processing flag if phone not found
                self.user_db.mongo.get_collection("matches").update_one(
                    {"_id": match['_id']},
                    {"$unset": {"auto_approval_processing": ""}}
                )
                continue
            
            try:
                # Check if driver already received notification for this hitchhiker (prevent duplicates across multiple ride requests)
                # This prevents duplicate notifications if hitchhiker requests multiple times
                ride_request = self.user_db.mongo.get_collection("ride_requests").find_one({"_id": ride_request_id})
                hitchhiker_id = ride_request.get('requester_id') if ride_request else None
                
                if hitchhiker_id:
                    existing_notification = self.user_db.mongo.get_collection("matches").find_one({
                        "driver_id": driver_id,
                        "hitchhiker_id": hitchhiker_id,
                        "auto_approval_notification_sent": True,
                        "status": "approved"
                    })
                    
                    if existing_notification:
                        logger.info(f"Driver {driver_phone} already received auto-approval notification for hitchhiker {hitchhiker_id}, skipping duplicate")
                        # Clear processing flag and continue
                        self.user_db.mongo.get_collection("matches").update_one(
                            {"_id": match['_id']},
                            {"$unset": {"auto_approval_processing": ""}}
                        )
                        continue
                
                # Use atomic operation to check and mark notification as being sent
                # This prevents duplicate notifications even if function is called multiple times concurrently
                notification_match = self.user_db.mongo.get_collection("matches").find_one_and_update(
                    {
                        "_id": match['_id'],
                        "auto_approval_notification_sent": {"$ne": True}  # Only if not already sent
                    },
                    {
                        "$set": {
                            "auto_approval_notification_sending": True  # Mark as being sent
                        }
                    },
                    return_document=True
                )
                
                # If notification was already sent or is being sent by another call, skip it
                if not notification_match:
                    logger.info(f"Driver {driver_phone} notification for match {match_id} already sent or being sent, skipping")
                    # Clear processing flag and continue
                    self.user_db.mongo.get_collection("matches").update_one(
                        {"_id": match['_id']},
                        {"$unset": {"auto_approval_processing": ""}}
                    )
                    continue
                
                # Auto-approve the match (mark as auto-approval so driver won't receive confirmation message)
                logger.info(f"🔄 Processing auto-approval for match {match_id} (driver {driver_phone})")
                success = approval_service.driver_approve(match_id, driver_phone, is_auto_approval=True)
                
                if success:
                    logger.info(f"✅ Auto-approved match {match_id} for driver {driver_phone}")
                    
                    # Send notification to driver that their details were sent automatically
                    notification_sent = False
                    if self.notification_service and self.notification_service.whatsapp_client:
                        # Get hitchhiker info for the message
                        ride_request = self.user_db.mongo.get_collection("ride_requests").find_one({"_id": ride_request_id})
                        hitchhiker = None
                        if ride_request:
                            hitchhiker = self.user_db.mongo.get_collection("users").find_one({"_id": ride_request['requester_id']})
                        
                        hitchhiker_name = "טרמפיסט"
                        if hitchhiker:
                            hitchhiker_name = hitchhiker.get('full_name') or hitchhiker.get('whatsapp_name') or 'טרמפיסט'
                        
                        # Send friendly notification to driver
                        auto_approval_message = f"""🎉 מצאנו התאמה!

הפרטים שלך נשלחו ל{hitchhiker_name} אוטומטית. 📲
הוא יצור איתך קשר בקרוב! 🚗"""
                        
                        self.notification_service.whatsapp_client.send_message(
                            driver_phone,
                            auto_approval_message,
                            state="auto_approval_notification"
                        )
                        notification_sent = True
                        logger.info(f"✅ Sent auto-approval notification to driver {driver_phone}")
                    
                    # Mark as completed and clear flags using atomic operation
                    self.user_db.mongo.get_collection("matches").update_one(
                        {"_id": match['_id']},
                        {
                            "$set": {
                                "auto_approval_notification_sent": notification_sent
                            },
                            "$unset": {
                                "auto_approve": "",
                                "auto_approval_processing": "",
                                "auto_approval_notification_sending": ""  # Clear sending flag
                            }
                        }
                    )
                else:
                    logger.error(f"❌ Failed to auto-approve match {match_id} for driver {driver_phone}")
                    # Clear processing and sending flags on failure
                    self.user_db.mongo.get_collection("matches").update_one(
                        {"_id": match['_id']},
                        {"$unset": {
                            "auto_approval_processing": "",
                            "auto_approval_notification_sending": ""
                        }}
                    )
            except Exception as e:
                logger.error(f"❌ Error processing auto-approval for match {match_id}: {e}")
                import traceback
                logger.error(traceback.format_exc())
                # Clear processing and sending flags on error
                self.user_db.mongo.get_collection("matches").update_one(
                    {"_id": match['_id']},
                    {"$unset": {
                        "auto_approval_processing": "",
                        "auto_approval_notification_sending": ""
                    }}
                )
    
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
    
    def _execute_save_routine_and_match(self, phone_number: str, data: Dict[str, Any]):
        """Save routine and find matching hitchhikers"""
        logger.info(f"🔄 _execute_save_routine_and_match called for {phone_number}")
        logger.info(f"📥 Received data: {data}")
        
        # Get fresh user data
        user = self.user_db.get_user(phone_number)
        profile = user.get('profile', {}) if user else {}
        
        logger.info(f"📋 Full profile: {profile}")
        
        routine_data = {
            'routine_destination': profile.get('routine_destination'),
            'routine_days': profile.get('routine_days'),
            'routine_departure_time': profile.get('routine_departure_time'),
            'routine_return_time': profile.get('routine_return_time')
        }
        
        logger.info(f"📝 Saving routine: {routine_data}")
        
        # If routine_return_time is in data['input'], use it
        if data.get('input') and not routine_data.get('routine_return_time'):
            routine_data['routine_return_time'] = data.get('input')
            logger.info(f"✅ Using routine_return_time from input: {data.get('input')}")
        
        # Get values directly from MongoDB
        mongo_user = self.user_db.mongo.get_collection("users").find_one({"phone_number": phone_number})
        if mongo_user:
            logger.info(f"📊 MongoDB user fields: {list(mongo_user.keys())}")
            # Get routine fields directly from MongoDB user document
            if not routine_data.get('routine_destination'):
                routine_data['routine_destination'] = mongo_user.get('routine_destination')
            if not routine_data.get('routine_days'):
                routine_data['routine_days'] = mongo_user.get('routine_days')
            if not routine_data.get('routine_departure_time'):
                routine_data['routine_departure_time'] = mongo_user.get('routine_departure_time')
            logger.info(f"📝 Updated routine_data from MongoDB: {routine_data}")
        
        # Save routine
        self.user_db.add_routine(phone_number, routine_data)
        
        # Check if matching service available
        logger.info(f"🔍 Checking conditions: matching_service={self.matching_service is not None}")
        
        if self.matching_service:
            
            logger.info(f"✅ Conditions met, proceeding with matching")
            # Get user from MongoDB
            user = self.user_db.mongo.get_collection("users").find_one({"phone_number": phone_number})
            if not user:
                logger.error(f"User not found in MongoDB: {phone_number}")
                return
            
            logger.info(f"✅ User found in MongoDB: {user.get('full_name') or user.get('phone_number')}")
            
            # Get the routine we just created
            routine = self.user_db.mongo.get_collection("routines").find_one({
                "user_id": user['_id'] if isinstance(user['_id'], str) else user['_id'],
                "destination": routine_data['routine_destination'],
                "is_active": True
            }, sort=[("created_at", -1)])  # Get most recent
            
            if routine:
                from bson import ObjectId
                
                driver_info = {
                    'driver_id': user['_id'],
                    'driver_phone': phone_number,
                    'driver_name': user.get('full_name') or user.get('whatsapp_name')
                }
                
                # Find matching hitchhikers
                matching_requests = self.matching_service.find_matching_hitchhikers(
                    driver_info,
                    destination=routine_data['routine_destination'],
                    departure_time=routine_data['routine_departure_time'],
                    days=routine_data['routine_days']
                )
                
                # Create matches
                if matching_requests:
                    matches = self.matching_service.create_matches_for_driver(
                        user['_id'] if isinstance(user['_id'], ObjectId) else ObjectId(user['_id']),
                        phone_number,
                        matching_requests,
                        routine_id=routine['_id']
                    )
                    
                    # Send notifications if notification service available
                    if self.notification_service and matches:
                        # Notify hitchhikers about new driver routine
                        for match in matches:
                            ride_request = self.user_db.mongo.get_collection("ride_requests").find_one({
                                "_id": match['ride_request_id']
                            })
                            if ride_request:
                                hitchhiker_phone = ride_request.get('requester_phone')
                                if hitchhiker_phone:
                                    # Notify hitchhiker about new matching driver
                                    message = (
                                        f"🚗 נהג חדש נוסע ל-{routine_data['routine_destination']}!\n\n"
                                        f"נמצא נהג שמתאים לבקשה שלך. הוא נוסע ב-{routine_data['routine_days']} "
                                        f"ב-{routine_data['routine_departure_time']}.\n\n"
                                        f"הנהג יקבל התראה ויצור איתך קשר אם הוא מעוניין! 📲"
                                    )
                                    # Use notification service's whatsapp client
                                    self.notification_service.whatsapp_client.send_message(
                                        hitchhiker_phone, message
                                    )
                    
                    logger.info(f"Saved routine and created {len(matches)} matches")
                else:
                    logger.info(f"Saved routine but no matching hitchhikers found")
        
        logger.info(f"Saved routine for {phone_number}: {routine_data}")
    
    def _execute_return_to_idle(self, phone_number: str, data: Dict[str, Any]):
        """Return to idle state"""
        pass  # Just stay in idle
    
    def _execute_show_help_command(self, phone_number: str, data: Dict[str, Any]):
        """Show help command - handled by command handler"""
        pass

