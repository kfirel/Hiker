"""
Action executor module for conversation flow actions
Handles execution of actions defined in conversation_flow.yml
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
    
    def _execute_save_whatsapp_name_as_full_name(self, phone_number: str, data: Dict[str, Any]):
        """Save WhatsApp name as full_name"""
        user = self.user_db.get_user(phone_number)
        if not user:
            logger.error(f"User not found: {phone_number}")
            return
        
        # Get WhatsApp name from user document (check both root and profile)
        profile = user.get('profile', {})
        whatsapp_name = profile.get('whatsapp_name') or user.get('whatsapp_name')
        
        if whatsapp_name:
            # Save WhatsApp name as full_name
            self.user_db.save_to_profile(phone_number, 'full_name', whatsapp_name)
            logger.info(f"Saved WhatsApp name '{whatsapp_name}' as full_name for {phone_number}")
        else:
            logger.warning(f"No WhatsApp name found for {phone_number}")
    
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
        
        # Check if MongoDB is connected
        if not self.user_db._use_mongo or not self.user_db.mongo.is_connected():
            logger.error("MongoDB is not connected. Cannot save driver ride offer.")
            return
        
        # Get user from MongoDB
        user = self.user_db.mongo.get_collection("users").find_one({"phone_number": phone_number})
        if not user:
            logger.error(f"User not found in MongoDB: {phone_number}")
            return
        
        from src.database.models import RideRequestModel
        from src.time_utils import parse_time_to_range
        from bson import ObjectId
        
        # Get departure timing from user document (check both root and profile)
        departure_timing = user.get('departure_timing') or profile.get('departure_timing')
        
        # Convert departure timing to time range
        start_time_range, end_time_range = parse_time_to_range(departure_timing or "now", "soon")
        
        logger.info(f"⏰ Driver offer time range: {start_time_range} - {end_time_range}")
        
        # Get driver destination (check both root and profile)
        driver_destination = user.get('driver_destination') or profile.get('driver_destination')
        if not driver_destination:
            logger.error(f"Driver destination not found for {phone_number}")
            return
        
        # Create driver offer with time range
        driver_offer = RideRequestModel.create(
            requester_id=user['_id'] if isinstance(user['_id'], ObjectId) else ObjectId(user['_id']),
            requester_phone=phone_number,
            request_type="driver_offer",
            destination=driver_destination,
            origin='גברעם',
            start_time_range=start_time_range,
            end_time_range=end_time_range
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
                destination=driver_destination,
                departure_time_start=None,  # Driver offers don't have fixed departure time
                departure_time_end=None,
                days=None,
                offer_start_time=start_time_range,
                offer_end_time=end_time_range
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
                        
                        # Process auto-approvals for matches marked with auto_approve=True
                        # This handles the case where driver has 'always' preference and hitchhiker searches later
                        for match in matches:
                            if match.get('auto_approve'):
                                ride_request_id = match.get('ride_request_id')
                                if ride_request_id:
                                    logger.info(f"🔄 Match {match.get('match_id', '')} marked for auto-approval, will be processed when hitchhiker searches")
                                    # Note: Auto-approval will be processed when hitchhiker creates their request
                                    # and finds this driver offer, or when hitchhiker searches and finds this offer
                
                logger.info(f"Saved driver offer and created {len(matches)} matches")
            else:
                logger.info(f"Saved driver offer but no matching hitchhikers found")
        else:
            logger.warning(f"Matching service not available - cannot find matching hitchhikers")
    
    def _execute_save_hitchhiker_ride_request(self, phone_number: str, data: Dict[str, Any]):
        """Save hitchhiker ride request and trigger matching"""
        logger.info(f"🔄 _execute_save_hitchhiker_ride_request called for {phone_number}")
        
        # Check if MongoDB is connected
        if not self.user_db._use_mongo or not self.user_db.mongo.is_connected():
            logger.error("MongoDB is not connected. Cannot save hitchhiker ride request.")
            return
        
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
        
        logger.info(f"📝 Ride request data from MongoDB: destination={hitchhiker_destination}, ride_timing={ride_timing}, time_range={time_range}, specific_datetime={specific_datetime}")
        
        if not hitchhiker_destination:
            logger.error(f"No hitchhiker_destination found for {phone_number}")
            return
        
        from src.database.models import RideRequestModel
        from src.time_utils import parse_time_to_range
        from bson import ObjectId
        
        # Convert time input to time range
        # Priority: ride_timing > time_range > specific_datetime
        time_input = ride_timing or time_range or specific_datetime
        time_type = None
        if ride_timing:
            time_type = "soon"
        elif time_range:
            time_type = "range"
        elif specific_datetime:
            time_type = "specific"
        
        start_time_range, end_time_range = parse_time_to_range(time_input or "now", time_type)
        
        logger.info(f"⏰ Converted time to range: {start_time_range} - {end_time_range}")
        
        # Create ride request with time range
        ride_request = RideRequestModel.create(
            requester_id=user['_id'] if isinstance(user['_id'], ObjectId) else ObjectId(user['_id']),
            requester_phone=phone_number,
            request_type="hitchhiker_request",
            destination=hitchhiker_destination,
            origin='גברעם',
            start_time_range=start_time_range,
            end_time_range=end_time_range
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
                    # Send list of ALL matching drivers immediately
                    self.notification_service.notify_hitchhiker_matches_found(
                        ride_request['_id'],
                        len(matches),
                        matching_drivers=matching_drivers
                    )
                    
                    # Store ride request ID for auto-approval processing after confirmation message is sent
                    # This ensures hitchhiker gets confirmation message first, then approval notification
                    self.user_db.update_context(phone_number, 'pending_auto_approval_ride_request_id', str(ride_request['_id']))
                    logger.info(f"📝 Stored ride request {ride_request['_id']} for auto-approval processing after message is sent")
                
                logger.info(f"Saved ride request and created {len(matches)} matches")
            else:
                logger.info(f"Saved ride request but no matching drivers found")
        else:
            logger.warning(f"Matching service not available - cannot find matching drivers")
    
    def _process_auto_approvals(self, ride_request_id):
        """Process auto-approvals for drivers with 'always' preference"""
        from src.services.approval_service import ApprovalService
        from bson import ObjectId
        
        # Check if MongoDB is connected
        if not self.user_db._use_mongo or not self.user_db.mongo.is_connected():
            logger.error("MongoDB is not connected. Cannot process auto-approvals.")
            return
        
        # Get ride request with matched_drivers array
        ride_request = self.user_db.mongo.get_collection("ride_requests").find_one({"_id": ride_request_id})
        if not ride_request:
            return
        
        # Find matched drivers marked for auto-approval
        matched_drivers = ride_request.get('matched_drivers', [])
        auto_approve_drivers = [
            md for md in matched_drivers 
            if md.get('auto_approve') and 
               md.get('status') == 'pending_approval' and
               not md.get('auto_approval_notification_sent', False)
        ]
        
        if not auto_approve_drivers:
            return
        
        approval_service = ApprovalService(
            self.user_db.mongo,
            self.notification_service.whatsapp_client if self.notification_service else None,
            self.notification_service.user_logger if self.notification_service else None
        )
        
        for matched_driver in auto_approve_drivers:
            match_id = matched_driver.get('match_id', '')
            driver_id = matched_driver.get('driver_id')
            
            if not match_id or not driver_id:
                continue
            
            # Use atomic operation to mark as being processed
            result = self.user_db.mongo.get_collection("ride_requests").find_one_and_update(
                {
                    "_id": ride_request_id,
                    "matched_drivers.match_id": match_id,
                    "matched_drivers.auto_approve": True,
                    "matched_drivers.status": "pending_approval",
                    "matched_drivers.auto_approval_notification_sent": {"$ne": True}
                },
                {
                    "$set": {
                        "matched_drivers.$.auto_approval_processing": True
                    }
                },
                return_document=True
            )
            
            # If already processed by another call, skip it
            if not result:
                logger.info(f"Match {match_id} already being processed, skipping")
                continue
            
            # Get driver phone number
            driver = self.user_db.mongo.get_collection("users").find_one({"_id": driver_id})
            if not driver:
                # Clear processing flag
                self.user_db.mongo.get_collection("ride_requests").update_one(
                    {"_id": ride_request_id, "matched_drivers.match_id": match_id},
                    {"$unset": {"matched_drivers.$.auto_approval_processing": ""}}
                )
                continue
            
            driver_phone = driver.get('phone_number')
            if not driver_phone:
                # Clear processing flag
                self.user_db.mongo.get_collection("ride_requests").update_one(
                    {"_id": ride_request_id, "matched_drivers.match_id": match_id},
                    {"$unset": {"matched_drivers.$.auto_approval_processing": ""}}
                )
                continue
            
            try:
                # Check if driver already received notification for this hitchhiker
                hitchhiker_id = ride_request.get('requester_id')
                if hitchhiker_id:
                    # Check other ride requests for this driver-hitchhiker pair
                    other_requests = list(self.user_db.mongo.get_collection("ride_requests").find({
                        "requester_id": hitchhiker_id,
                        "matched_drivers.driver_id": driver_id,
                        "matched_drivers.status": "approved",
                        "matched_drivers.auto_approval_notification_sent": True
                    }))
                    
                    if other_requests:
                        logger.info(f"Driver {driver_phone} already received auto-approval notification for hitchhiker {hitchhiker_id}, skipping duplicate")
                        # Clear processing flag
                        self.user_db.mongo.get_collection("ride_requests").update_one(
                            {"_id": ride_request_id, "matched_drivers.match_id": match_id},
                            {"$unset": {"matched_drivers.$.auto_approval_processing": ""}}
                        )
                        continue
                
                # Use atomic operation to mark notification as being sent
                notification_result = self.user_db.mongo.get_collection("ride_requests").find_one_and_update(
                    {
                        "_id": ride_request_id,
                        "matched_drivers.match_id": match_id,
                        "matched_drivers.auto_approval_notification_sent": {"$ne": True}
                    },
                    {
                        "$set": {
                            "matched_drivers.$.auto_approval_notification_sending": True
                        }
                    },
                    return_document=True
                )
                
                # If notification was already sent, skip it
                if not notification_result:
                    logger.info(f"Driver {driver_phone} notification for match {match_id} already sent, skipping")
                    # Clear processing flag
                    self.user_db.mongo.get_collection("ride_requests").update_one(
                        {"_id": ride_request_id, "matched_drivers.match_id": match_id},
                        {"$unset": {"matched_drivers.$.auto_approval_processing": ""}}
                    )
                    continue
                
                # Auto-approve the match
                logger.info(f"🔄 Processing auto-approval for match {match_id} (driver {driver_phone})")
                success = approval_service.driver_approve(match_id, driver_phone, is_auto_approval=True)
                
                if success:
                    logger.info(f"✅ Auto-approved match {match_id} for driver {driver_phone}")
                    
                    # Send notification to driver that their details were sent automatically
                    notification_sent = False
                    if self.notification_service and self.notification_service.whatsapp_client:
                        # Get hitchhiker info for the message
                        hitchhiker = self.user_db.mongo.get_collection("users").find_one({"_id": ride_request['requester_id']})
                        
                        hitchhiker_name = "טרמפיסט"
                        if hitchhiker:
                            hitchhiker_name = hitchhiker.get('full_name') or hitchhiker.get('whatsapp_name') or 'טרמפיסט'
                        
                        destination = ride_request.get('destination', 'יעד')
                        
                        # Format time range for display
                        start_time = ride_request.get('start_time_range')
                        end_time = ride_request.get('end_time_range')
                        time_info = ""
                        if start_time and end_time:
                            time_info = f" בשעה {start_time.strftime('%H:%M')}-{end_time.strftime('%H:%M')}"
                        
                        # Send friendly notification to driver
                        auto_approval_message = f"""🎉 מצאנו התאמה!

טרמפיסט בשם {hitchhiker_name} מחפש טרמפ ל-{destination}{time_info}.

פרטי הקשר שלך (שם וטלפון) נשלחו אליו אוטומטית. 📲
הוא יצור איתך קשר בקרוב כדי לתאם את הפרטים! 🚗"""
                        
                        self.notification_service.whatsapp_client.send_message(
                            driver_phone,
                            auto_approval_message,
                            state="auto_approval_notification"
                        )
                        notification_sent = True
                        logger.info(f"✅ Sent auto-approval notification to driver {driver_phone}")
                    
                    # Mark as completed and clear flags
                    self.user_db.mongo.get_collection("ride_requests").update_one(
                        {"_id": ride_request_id, "matched_drivers.match_id": match_id},
                        {
                            "$set": {
                                "matched_drivers.$.auto_approval_notification_sent": notification_sent
                            },
                            "$unset": {
                                "matched_drivers.$.auto_approve": "",
                                "matched_drivers.$.auto_approval_processing": "",
                                "matched_drivers.$.auto_approval_notification_sending": ""
                            }
                        }
                    )
                else:
                    logger.error(f"❌ Failed to auto-approve match {match_id} for driver {driver_phone}")
                    # Clear processing and sending flags on failure
                    self.user_db.mongo.get_collection("ride_requests").update_one(
                        {"_id": ride_request_id, "matched_drivers.match_id": match_id},
                        {"$unset": {
                            "matched_drivers.$.auto_approval_processing": "",
                            "matched_drivers.$.auto_approval_notification_sending": ""
                        }}
                    )
            except Exception as e:
                logger.error(f"❌ Error processing auto-approval for match {match_id}: {e}")
                import traceback
                logger.error(traceback.format_exc())
                # Clear processing and sending flags on error
                self.user_db.mongo.get_collection("ride_requests").update_one(
                    {"_id": ride_request_id, "matched_drivers.match_id": match_id},
                    {"$unset": {
                        "matched_drivers.$.auto_approval_processing": "",
                        "matched_drivers.$.auto_approval_notification_sending": ""
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
        
        # Check if MongoDB is connected before accessing it
        if self.user_db._use_mongo and self.user_db.mongo.is_connected():
            # Get values directly from MongoDB
            mongo_user = self.user_db.mongo.get_collection("users").find_one({"phone_number": phone_number})
        else:
            mongo_user = None
        
        if mongo_user:
            logger.info(f"📊 MongoDB user fields: {list(mongo_user.keys())}")
            # Get routine fields directly from MongoDB user document
            if not routine_data.get('routine_destination'):
                routine_data['routine_destination'] = mongo_user.get('routine_destination')
            if not routine_data.get('routine_days'):
                routine_data['routine_days'] = mongo_user.get('routine_days')
            if not routine_data.get('routine_departure_time'):
                routine_data['routine_departure_time'] = mongo_user.get('routine_departure_time')
            if not routine_data.get('routine_return_time'):
                routine_data['routine_return_time'] = mongo_user.get('routine_return_time')
            logger.info(f"📝 Updated routine_data from MongoDB: {routine_data}")
        
        # Convert days string to array if needed
        routine_days = routine_data.get('routine_days')
        if isinstance(routine_days, str):
            from src.validation import parse_days_to_array
            routine_days = parse_days_to_array(routine_days)
            routine_data['routine_days'] = routine_days
        
        # Convert departure and return times to time ranges
        from src.time_utils import parse_routine_departure_time
        
        # For parse_routine_departure_time, pass days as string if it was originally a string
        days_for_parsing = routine_data.get('routine_days')
        if isinstance(days_for_parsing, list):
            # Convert array back to string for parsing (backward compatibility with parse_routine_departure_time)
            days_for_parsing = ', '.join(days_for_parsing) if days_for_parsing else None
        
        departure_time_start, departure_time_end = parse_routine_departure_time(
            routine_data.get('routine_departure_time'),
            days_for_parsing
        )
        
        return_time_start, return_time_end = parse_routine_departure_time(
            routine_data.get('routine_return_time'),
            days_for_parsing
        )
        
        logger.info(f"⏰ Departure time range: {departure_time_start} - {departure_time_end}")
        logger.info(f"⏰ Return time range: {return_time_start} - {return_time_end}")
        
        # Save routine with time ranges
        routine_data['departure_time_start'] = departure_time_start
        routine_data['departure_time_end'] = departure_time_end
        routine_data['return_time_start'] = return_time_start
        routine_data['return_time_end'] = return_time_end
        
        self.user_db.add_routine(phone_number, routine_data)
        
        # Check if matching service available
        logger.info(f"🔍 Checking conditions: matching_service={self.matching_service is not None}")
        
        if self.matching_service:
            
            logger.info(f"✅ Conditions met, proceeding with matching")
            
            # Check if MongoDB is connected
            if not self.user_db._use_mongo or not self.user_db.mongo.is_connected():
                logger.error("MongoDB is not connected. Cannot save routine and match.")
                return
            
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
                    departure_time_start=routine_data.get('departure_time_start'),
                    departure_time_end=routine_data.get('departure_time_end'),
                    days=routine_data['routine_days']
                )
                
                # Create matches
                if matching_requests:
                    matched_drivers_entries = self.matching_service.create_matches_for_driver(
                        user['_id'] if isinstance(user['_id'], ObjectId) else ObjectId(user['_id']),
                        phone_number,
                        matching_requests,
                        routine_id=routine['_id']
                    )
                    
                    # Send notifications if notification service available
                    if self.notification_service and matched_drivers_entries:
                        # Group by ride_request_id - get unique ride_request_ids from matching_requests
                        ride_request_ids = list(set([req['ride_request_id'] for req in matching_requests]))
                        
                        for ride_request_id in ride_request_ids:
                            ride_request = self.user_db.mongo.get_collection("ride_requests").find_one({
                                "_id": ride_request_id
                            })
                            
                            if not ride_request:
                                continue
                            
                            # Get driver phones for this request (just this driver since we're processing one routine)
                            driver_phones = [phone_number]
                            
                            if driver_phones:
                                # Notify drivers about the hitchhiker request (same as when hitchhiker registers)
                                # This will handle auto-approval and regular notifications
                                self.notification_service.notify_drivers_new_request(
                                    ObjectId(ride_request_id),
                                    driver_phones
                                )
                                
                                # Notify hitchhiker that matches were found
                                self.notification_service.notify_hitchhiker_matches_found(
                                    ObjectId(ride_request_id),
                                    len(driver_phones)
                                )
                                
                                logger.info(f"📤 Sent notifications for ride request {ride_request_id}: {len(driver_phones)} driver(s) notified")
                        
                        # Process auto-approvals if any matches were created
                        # This handles drivers with 'always' preference
                        for ride_request_id in ride_request_ids:
                            self._process_auto_approvals(ObjectId(ride_request_id))
                    
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

