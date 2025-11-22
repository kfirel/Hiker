"""
Integration tests for Hiker WhatsApp Bot
Tests data persistence, matching, and notifications with MongoDB
"""

import sys
import os
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from bson import ObjectId

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
import logging
from tests.integration_report_generator import IntegrationReportGenerator
from tests.conftest import integration_conversation_engine, mock_mongo_client, mongo_db
from tests.mock_whatsapp_client import MockWhatsAppClient

logger = logging.getLogger(__name__)


class IntegrationScenarioTester:
    """Test integration scenarios with multiple users"""
    
    def __init__(self, engine, mongo_db, whatsapp_client):
        self.engine = engine
        self.mongo_db = mongo_db
        self.whatsapp_client = whatsapp_client
        self.user_logger = engine.user_logger if hasattr(engine, 'user_logger') else None
        self.scenario_data = {
            'users': {},
            'conversations': [],
            'db_snapshots': [],
            'matches': [],
            'notifications': []
        }
    
    def run_scenario(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run a complete integration scenario
        
        Args:
            scenario: Scenario definition from YAML
            
        Returns:
            Dict with scenario results
        """
        scenario_id = scenario.get('id')
        scenario_name = scenario.get('name')
        scenario_description = scenario.get('description')
        users = scenario.get('users', [])
        
        # Reset state
        self.scenario_data = {
            'users': {},
            'conversations': [],
            'db_snapshots': [],
            'matches': [],
            'notifications': []
        }
        
        # Track all user interactions chronologically
        all_interactions = []
        
        # Process each user action in order
        for user_action in users:
            user_id = user_action.get('user_id')
            phone = user_action.get('phone')
            action_type = user_action.get('type')
            setup_messages = user_action.get('setup_messages', [])
            action_messages = user_action.get('action_messages', [])
            wait_after = user_action.get('wait_after', 0)
            
            # Initialize user if not exists
            if phone not in self.scenario_data['users']:
                self.scenario_data['users'][phone] = {
                    'user_id': user_id,
                    'phone': phone,
                    'type': action_type,
                    'conversations': []
                }
            
            # Process setup messages
            for msg in setup_messages:
                result = self._process_message(phone, msg, user_id)
                if result:
                    if isinstance(result, tuple):
                        interaction, notification_interactions = result
                        all_interactions.append(interaction)
                        # Add notification interactions for recipients
                        all_interactions.extend(notification_interactions)
                    else:
                        all_interactions.append(result)
                # No sleep needed - MongoDB operations are synchronous
            
            # Process action messages
            for idx, msg in enumerate(action_messages):
                # Replace placeholder match IDs with actual ones
                if msg.startswith('approve_MATCH_') or msg.startswith('reject_MATCH_'):
                    replaced_msg = self._replace_match_id(phone, msg)
                    # Only use replaced message if we found a match, otherwise log warning
                    if replaced_msg != msg:
                        msg = replaced_msg
                    else:
                        logger.warning(f"Could not find match ID for {phone}, using original message: {msg}")
                
                # Check if this is an approval message ("1" or "approve_") and if there's an auto-approval match
                # In that case, skip this message as auto-approval already happened
                if msg == '1' or msg.startswith('approve_') or msg.startswith('1_'):
                    driver = self.mongo_db.mongo.get_collection("users").find_one({"phone_number": phone})
                    if driver:
                        # Check if there's a match marked for auto-approval (auto_approve=True) or already auto-approved
                        auto_approved_match = self.mongo_db.mongo.get_collection("matches").find_one({
                            "driver_id": driver['_id'],
                            "$or": [
                                {"auto_approve": True},
                                {"is_auto_approval": True, "status": "approved"}
                            ]
                        })
                        if auto_approved_match:
                            logger.info(f"Skipping approval message '{msg}' for driver {phone} - match was already auto-approved or marked for auto-approval")
                            continue  # Skip this message, auto-approval already happened or will happen
                
                # Log which message we're processing (for debugging)
                logger.debug(f"Processing action message {idx+1}/{len(action_messages)} for {phone}: '{msg}'")
                
                result = self._process_message(phone, msg, user_id)
                if result:
                    if isinstance(result, tuple):
                        interaction, notification_interactions = result
                        all_interactions.append(interaction)
                        # Add notification interactions for recipients
                        all_interactions.extend(notification_interactions)
                    else:
                        all_interactions.append(result)
                else:
                    logger.warning(f"No interaction returned for message '{msg}' from {phone}")
                
                # After message is sent, check if we need to process auto-approvals
                # This ensures hitchhiker gets confirmation message first, then approval notification
                user_context = self.mongo_db.get_user_context(phone)
                pending_ride_request_id = user_context.get('pending_auto_approval_ride_request_id')
                if pending_ride_request_id:
                    from bson import ObjectId
                    logger.info(f"🔄 Processing auto-approvals for ride request {pending_ride_request_id} after message sent")
                    
                    # Clear messages before auto-approval to capture only new messages
                    self.whatsapp_client.clear_messages()
                    
                    self.engine.action_executor._process_auto_approvals(ObjectId(pending_ride_request_id))
                    
                    # Collect messages sent during auto-approval (to hitchhiker)
                    sent_messages = self.whatsapp_client.get_sent_messages()
                    auto_approval_interactions = []
                    for sent_msg in sent_messages:
                        recipient_phone = sent_msg['to']
                        recipient_user_id = None
                        if recipient_phone in self.scenario_data['users']:
                            recipient_user_id = self.scenario_data['users'][recipient_phone].get('user_id')
                        auto_approval_interaction = {
                            'timestamp': datetime.now(),
                            'user_id': recipient_user_id or recipient_phone,
                            'user_phone': recipient_phone,
                            'user_message': None,
                            'bot_response': sent_msg['message'],
                            'buttons': sent_msg.get('buttons'),
                            'notifications_sent': [],
                            'is_notification': True
                        }
                        auto_approval_interactions.append(auto_approval_interaction)
                    
                    # Add auto-approval interactions to all_interactions
                    all_interactions.extend(auto_approval_interactions)
                    
                    # Clear the pending flag
                    self.mongo_db.update_context(phone, 'pending_auto_approval_ride_request_id', None)
                
                # No sleep needed - MongoDB operations are synchronous
                # State is updated immediately after each message
            
            # Wait if specified
            if wait_after > 0:
                import time
                time.sleep(wait_after)
        
        # Take final database snapshot
        self._take_db_snapshot()
        
        # Collect matches and notifications
        self._collect_matches_and_notifications()
        
        return {
            'scenario_id': scenario_id,
            'scenario_name': scenario_name,
            'scenario_description': scenario_description,
            'interactions': all_interactions,
            'db_snapshot': self.scenario_data['db_snapshots'][-1] if self.scenario_data['db_snapshots'] else {},
            'matches': self.scenario_data['matches'],
            'notifications': self.scenario_data['notifications'],
            'users': self.scenario_data['users'],
            'log_files': self._get_log_files()  # Add log files info
        }
    
    def _process_message(self, phone: str, message: str, user_id: str) -> Optional[tuple]:
        """Process a single message and return interaction data"""
        try:
            # Clear WhatsApp client messages before processing
            self.whatsapp_client.clear_messages()
            
            # Check if this is a name sharing response (check before approval/rejection)
            if message.startswith('share_name_yes_') or message.startswith('share_name_no_'):
                # Replace placeholder match_id with actual match_id
                message = self._replace_name_sharing_match_id(phone, message)
                
                from src.services.approval_service import ApprovalService
                approval_service = ApprovalService(self.mongo_db.mongo, self.whatsapp_client, self.user_logger)
                success = approval_service.handle_name_sharing_response(phone, message)
                if success:
                    # Get confirmation message sent to driver
                    sent_messages = self.whatsapp_client.get_sent_messages()
                    bot_response = None
                    buttons = None
                    for sent_msg in reversed(sent_messages):
                        if sent_msg['to'] == phone:
                            bot_response = sent_msg['message']
                            buttons = sent_msg.get('buttons')
                            break
                    if not bot_response:
                        bot_response = "✅ הטרמפיסט קיבל את פרטי הקשר שלך."
                else:
                    bot_response = "❌ שגיאה בעיבוד הבקשה."
                    buttons = None
                # Logging is now automatic in WhatsAppClient.send_message
                if bot_response:
                    self.whatsapp_client.send_message(phone, bot_response, state="name_sharing_response")
                # Get sent messages and continue with normal flow
                sent_messages = self.whatsapp_client.get_sent_messages()
                notifications = []
                notification_interactions = []
                for sent_msg in sent_messages:
                    if sent_msg['to'] != phone:
                        notifications.append({
                            'to': sent_msg['to'],
                            'message': sent_msg['message'],
                            'buttons': sent_msg.get('buttons')
                        })
                        recipient_phone = sent_msg['to']
                        recipient_user_id = None
                        if recipient_phone in self.scenario_data['users']:
                            recipient_user_id = self.scenario_data['users'][recipient_phone].get('user_id')
                        notification_interaction = {
                            'timestamp': datetime.now(),
                            'user_id': recipient_user_id or recipient_phone,
                            'user_phone': recipient_phone,
                            'user_message': None,
                            'bot_response': sent_msg['message'],
                            'buttons': sent_msg.get('buttons'),
                            'notifications_sent': [],
                            'is_notification': True
                        }
                        notification_interactions.append(notification_interaction)
                interaction = {
                    'timestamp': datetime.now(),
                    'user_id': user_id,
                    'user_phone': phone,
                    'user_message': message,
                    'bot_response': bot_response,
                    'buttons': buttons,
                    'notifications_sent': notifications
                }
                if phone in self.scenario_data['users']:
                    self.scenario_data['users'][phone]['conversations'].append(interaction)
                return interaction, notification_interactions
            
            # Check if this is an approval/rejection message (needs special handling)
            # Support both old format (approve_/reject_) and new format (1/2)
            if (message.startswith('approve_') or message.startswith('reject_') or
                message.startswith('1_') or message.startswith('2_') or
                message in ['1', '2']):
                # Handle match approval/rejection directly (similar to app.py's handle_match_response)
                # This ensures ApprovalService is called and hitchhiker gets notified
                try:
                    # Extract match_id from button_id
                    # Support multiple formats: approve_xxx, reject_xxx, 1_xxx, 2_xxx, or just "1"/"2"
                    if message.startswith('approve_'):
                        match_id = message.replace('approve_', '')
                        is_approval = True
                    elif message.startswith('reject_'):
                        match_id = message.replace('reject_', '')
                        is_approval = False
                    elif message.startswith('1_'):
                        match_id = message.replace('1_', '')
                        is_approval = True
                    elif message.startswith('2_'):
                        match_id = message.replace('2_', '')
                        is_approval = False
                    elif message == '1':
                        # Simple "1" - find pending match
                        match_id = None
                        is_approval = True
                    elif message == '2':
                        # Simple "2" - find pending match
                        match_id = None
                        is_approval = False
                    else:
                        logger.error(f"Invalid button ID format: {message}")
                        bot_response = "❌ שגיאה בעיבוד הבקשה."
                        buttons = None
                        match_id = None
                    
                    if match_id is not None or message in ['1', '2']:
                        # Handle case where match_id is empty or just "MATCH_" (from test inputs)
                        # Or if user sent simple "1" or "2"
                        if not match_id or match_id == 'MATCH_' or message in ['1', '2']:
                            logger.info(f"Empty match_id in button_id: {message}, trying to find match from database")
                            # Try to find the most recent pending match for this driver
                            # Only if notification was sent (to avoid false positives during registration)
                            driver = self.mongo_db.mongo.get_collection("users").find_one({"phone_number": phone})
                            if driver:
                                # First check if there's an auto-approved match (should skip manual approval)
                                auto_approved_match = self.mongo_db.mongo.get_collection("matches").find_one({
                                    "driver_id": driver['_id'],
                                    "is_auto_approval": True,
                                    "status": "approved"
                                })
                                if auto_approved_match:
                                    logger.info(f"Found auto-approved match for driver {phone} - skipping manual approval message")
                                    # Return None to skip this message
                                    return None
                                
                                matches = list(self.mongo_db.mongo.get_collection("matches").find({
                                    "driver_id": driver['_id'],
                                    "status": "pending_approval",
                                    "notification_sent_to_driver": True  # Only if notification was sent
                                }).sort("matched_at", -1).limit(1))
                                if matches:
                                    match_id = matches[0].get('match_id', '')
                                    logger.info(f"Found match_id from database: {match_id}")
                                else:
                                    # If "1" or "2" was sent but no pending match, treat as regular message
                                    if message in ['1', '2']:
                                        logger.info(f"User sent '{message}' but no pending match found, treating as regular message")
                                        # Process as regular message through conversation engine
                                        bot_response, buttons = self.engine.process_message(phone, message)
                                        if bot_response:
                                            current_state = self.engine.user_db.get_user_state(phone) if self.engine.user_db.user_exists(phone) else None
                                            self.whatsapp_client.send_message(phone, bot_response, buttons=buttons, state=current_state)
                                        # Get sent messages and continue with normal flow
                                        sent_messages = self.whatsapp_client.get_sent_messages()
                                        notifications = []
                                        notification_interactions = []
                                        for sent_msg in sent_messages:
                                            if sent_msg['to'] != phone:
                                                notifications.append({
                                                    'to': sent_msg['to'],
                                                    'message': sent_msg['message'],
                                                    'buttons': sent_msg.get('buttons')
                                                })
                                                recipient_phone = sent_msg['to']
                                                recipient_user_id = None
                                                if recipient_phone in self.scenario_data['users']:
                                                    recipient_user_id = self.scenario_data['users'][recipient_phone].get('user_id')
                                                notification_interaction = {
                                                    'timestamp': datetime.now(),
                                                    'user_id': recipient_user_id or recipient_phone,
                                                    'user_phone': recipient_phone,
                                                    'user_message': None,
                                                    'bot_response': sent_msg['message'],
                                                    'buttons': sent_msg.get('buttons'),
                                                    'notifications_sent': [],
                                                    'is_notification': True
                                                }
                                                notification_interactions.append(notification_interaction)
                                        interaction = {
                                            'timestamp': datetime.now(),
                                            'user_id': user_id,
                                            'user_phone': phone,
                                            'user_message': message,
                                            'bot_response': bot_response,
                                            'buttons': buttons,
                                            'notifications_sent': notifications
                                        }
                                        if phone in self.scenario_data['users']:
                                            self.scenario_data['users'][phone]['conversations'].append(interaction)
                                        return interaction, notification_interactions
                                    else:
                                        logger.error(f"No pending matches found for driver {phone}")
                                        bot_response = "מצטער, לא נמצאה בקשה ממתינה לאישור. נסה שוב מאוחר יותר."
                                        buttons = None
                            else:
                                logger.error(f"Driver not found: {phone}")
                                bot_response = "מצטער, לא נמצא משתמש במערכת. נסה שוב מאוחר יותר."
                                buttons = None
                        
                        if match_id:
                            from src.services.approval_service import ApprovalService
                            
                            # Clear messages before approval to capture only new messages
                            self.whatsapp_client.clear_messages()
                            
                            approval_service = ApprovalService(self.mongo_db.mongo, self.whatsapp_client, self.user_logger)
                            
                            if is_approval:
                                # Check if this is an auto-approval (driver shouldn't receive confirmation message)
                                match = self.mongo_db.mongo.get_collection("matches").find_one({"match_id": match_id})
                                is_auto_approval = match.get('is_auto_approval', False) if match else False
                                
                                success = approval_service.driver_approve(match_id, phone, is_auto_approval=is_auto_approval)
                                if success:
                                    # Don't send confirmation message if this was an auto-approval
                                    if is_auto_approval:
                                        logger.info(f"Auto-approval for match {match_id} - skipping confirmation message to driver")
                                        # Auto-approval message is sent by _process_auto_approvals, so return None to skip
                                        return None
                                    
                                    # Check if driver needs to be asked about name sharing
                                    driver = self.mongo_db.mongo.get_collection("users").find_one({"phone_number": phone})
                                    share_name_preference = driver.get('share_name_with_hitchhiker') if driver else None
                                    if not share_name_preference and driver:
                                        profile = driver.get('profile', {})
                                        share_name_preference = profile.get('share_name_with_hitchhiker', 'ask')
                                    if not share_name_preference:
                                        share_name_preference = 'ask'
                                    
                                    if share_name_preference == 'ask':
                                        # Driver will be asked separately - don't send confirmation yet
                                        return None
                                    else:
                                        bot_response = "✅ אישרת את הבקשה! הטרמפיסט יקבל התראה ויצור איתך קשר בקרוב. 📲"
                                else:
                                    bot_response = "❌ שגיאה באישור הבקשה. נסה שוב או פנה לתמיכה."
                            else:
                                success = approval_service.driver_reject(match_id, phone)
                                if success:
                                    bot_response = "❌ דחית את הבקשה. הטרמפיסט ימשיך לחפש נהגים אחרים."
                                else:
                                    bot_response = "❌ שגיאה בדחיית הבקשה. נסה שוב או פנה לתמיכה."
                            
                            buttons = None
                            # Logging is now automatic in WhatsAppClient.send_message (lowest level)
                            self.whatsapp_client.send_message(phone, bot_response, state="match_response")
                            
                            # After approval, check if hitchhiker received notification
                            # Get all sent messages (including those sent to hitchhiker by approval_service)
                            sent_messages = self.whatsapp_client.get_sent_messages()
                            notifications = []
                            notification_interactions = []
                            for sent_msg in sent_messages:
                                if sent_msg['to'] != phone:
                                    # This is a notification to another user (hitchhiker)
                                    notifications.append({
                                        'to': sent_msg['to'],
                                        'message': sent_msg['message'],
                                        'buttons': sent_msg.get('buttons')
                                    })
                                    recipient_phone = sent_msg['to']
                                    recipient_user_id = None
                                    if recipient_phone in self.scenario_data['users']:
                                        recipient_user_id = self.scenario_data['users'][recipient_phone].get('user_id')
                                    notification_interaction = {
                                        'timestamp': datetime.now(),
                                        'user_id': recipient_user_id or recipient_phone,
                                        'user_phone': recipient_phone,
                                        'user_message': None,
                                        'bot_response': sent_msg['message'],
                                        'buttons': sent_msg.get('buttons'),
                                        'notifications_sent': [],
                                        'is_notification': True
                                    }
                                    notification_interactions.append(notification_interaction)
                            
                            interaction = {
                                'timestamp': datetime.now(),
                                'user_id': user_id,
                                'user_phone': phone,
                                'user_message': message,
                                'bot_response': bot_response,
                                'buttons': buttons,
                                'notifications_sent': notifications
                            }
                            if phone in self.scenario_data['users']:
                                self.scenario_data['users'][phone]['conversations'].append(interaction)
                            return interaction, notification_interactions
                except Exception as e:
                    logger.error(f"Error handling match response: {e}", exc_info=True)
                    bot_response = f"מצטער, אירעה שגיאה. נסה שוב או הקש 'עזרה'."
                    buttons = None
                    self.whatsapp_client.send_message(phone, bot_response)
            else:
                # Process message normally
                bot_response, buttons = self.engine.process_message(phone, message)
                
                # Send response through WhatsApp client (this will automatically log it)
                # This mimics the behavior in app.py where messages are sent after processing
                if bot_response:
                    # Get current state for logging
                    current_state = self.engine.user_db.get_user_state(phone) if self.engine.user_db.user_exists(phone) else None
                    self.whatsapp_client.send_message(phone, bot_response, buttons=buttons, state=current_state)
            
            # Get sent messages from WhatsApp client
            sent_messages = self.whatsapp_client.get_sent_messages()
            
            # Check if notifications were sent (to other users)
            notifications = []
            notification_interactions = []  # Separate interactions for recipients
            
            for sent_msg in sent_messages:
                if sent_msg['to'] != phone:  # Message to different user
                    notifications.append({
                        'to': sent_msg['to'],
                        'message': sent_msg['message'],
                        'buttons': sent_msg.get('buttons')
                    })
                    
                    # Create separate interaction for the recipient
                    recipient_phone = sent_msg['to']
                    recipient_user_id = None
                    # Find recipient user_id if exists
                    if recipient_phone in self.scenario_data['users']:
                        recipient_user_id = self.scenario_data['users'][recipient_phone].get('user_id')
                    
                    notification_interaction = {
                        'timestamp': datetime.now(),
                        'user_id': recipient_user_id or recipient_phone,
                        'user_phone': recipient_phone,
                        'user_message': None,  # No user message - this is a notification
                        'bot_response': sent_msg['message'],
                        'buttons': sent_msg.get('buttons'),
                        'notifications_sent': [],  # No notifications sent from this interaction
                        'is_notification': True  # Mark as notification
                    }
                    notification_interactions.append(notification_interaction)
            
            interaction = {
                'timestamp': datetime.now(),
                'user_id': user_id,
                'user_phone': phone,
                'user_message': message,
                'bot_response': bot_response,
                'buttons': buttons,
                'notifications_sent': notifications  # Keep for reference, but won't display in sender's row
            }
            
            # Store in user's conversation history
            if phone in self.scenario_data['users']:
                self.scenario_data['users'][phone]['conversations'].append(interaction)
            
            # Take DB snapshot after important actions
            if any(keyword in message.lower() for keyword in ['approve', 'reject', '1', '2']):
                self._take_db_snapshot()
            
            # Return both the main interaction and notification interactions
            return interaction, notification_interactions
            
        except Exception as e:
            error_interaction = {
                'timestamp': datetime.now(),
                'user_id': user_id,
                'user_phone': phone,
                'user_message': message,
                'bot_response': f"ERROR: {str(e)}",
                'buttons': None,
                'error': str(e)
            }
            return error_interaction, []
    
    def _replace_match_id(self, phone: str, message: str) -> str:
        """Replace placeholder match ID with actual match ID"""
        if not hasattr(self.mongo_db, '_use_mongo') or not self.mongo_db._use_mongo:
            return message
        
        if not (message.startswith('approve_') or message.startswith('reject_')):
            return message
        
        # Extract the prefix (approve_ or reject_)
        prefix = 'approve_' if message.startswith('approve_') else 'reject_'
        original_match_id = message.replace(prefix, '')
        
        # If match_id is already provided and not empty/MATCH_, use it
        if original_match_id and original_match_id != 'MATCH_':
            return message
        
        # Find user
        user = self.mongo_db.mongo.get_collection("users").find_one({"phone_number": phone})
        if not user:
            logger.warning(f"User not found for phone {phone}, cannot replace match_id")
            return message
        
        # Find pending matches for this driver, sorted by creation time (newest first)
        matches = list(self.mongo_db.mongo.get_collection("matches").find({
            "driver_id": user['_id'],
            "status": "pending_approval"
        }).sort("matched_at", -1))
        
        if matches:
            match_id = matches[0].get('match_id', '')
            if match_id:
                logger.info(f"Replacing match_id for {phone}: {prefix}{match_id}")
                return f"{prefix}{match_id}"
            else:
                logger.warning(f"Match found but no match_id field for {phone}")
        else:
            logger.warning(f"No pending matches found for driver {phone}")
        
        return message
    
    def _replace_name_sharing_match_id(self, phone: str, message: str) -> str:
        """Replace placeholder match ID in name sharing button ID with actual match ID"""
        if not hasattr(self.mongo_db, '_use_mongo') or not self.mongo_db._use_mongo:
            return message
        
        if not (message.startswith('share_name_yes_') or message.startswith('share_name_no_')):
            return message
        
        # Extract the prefix and match_id placeholder
        if message.startswith('share_name_yes_'):
            prefix = 'share_name_yes_'
            original_match_id = message.replace('share_name_yes_', '')
        else:
            prefix = 'share_name_no_'
            original_match_id = message.replace('share_name_no_', '')
        
        # If match_id is already provided and not empty, use it
        if original_match_id:
            return message
        
        # Find user
        user = self.mongo_db.mongo.get_collection("users").find_one({"phone_number": phone})
        if not user:
            logger.warning(f"User not found for phone {phone}, cannot replace name sharing match_id")
            return message
        
        # First try to find match from driver's document (stored at root level by _ask_driver_about_name_sharing)
        # The match_id is stored directly in the user document, not in context
        user = self.mongo_db.mongo.get_collection("users").find_one({"phone_number": phone})
        if user:
            # Check root level first (where _ask_driver_about_name_sharing stores it)
            pending_match_id = user.get('pending_name_share_match_id')
            if pending_match_id:
                logger.info(f"Replacing name sharing match_id for {phone} from user document root: {prefix}{pending_match_id}")
                return f"{prefix}{pending_match_id}"
            
            # Fallback: try to find from context (for backward compatibility)
            context = self.mongo_db.get_user_context(phone)
            pending_match_id = context.get('pending_name_share_match_id')
            if pending_match_id:
                logger.info(f"Replacing name sharing match_id for {phone} from context: {prefix}{pending_match_id}")
                return f"{prefix}{pending_match_id}"
        
        # Fallback: find the most recent pending match for this driver
        matches = list(self.mongo_db.mongo.get_collection("matches").find({
            "driver_id": user['_id'],
            "status": "pending_approval"
        }).sort("matched_at", -1).limit(1))
        
        if matches:
            match_id = matches[0].get('match_id', '')
            if match_id:
                logger.info(f"Found match_id from database for {phone}: {prefix}{match_id}")
                return f"{prefix}{match_id}"
            else:
                logger.warning(f"Match found but no match_id field for {phone}")
        else:
            logger.warning(f"No pending matches found for driver {phone}")
        
        return message
    
    def _take_db_snapshot(self):
        """Take a snapshot of database state"""
        if not hasattr(self.mongo_db, '_use_mongo') or not self.mongo_db._use_mongo:
            return
        
        snapshot = {
            'timestamp': datetime.now(),
            'users': [],
            'routines': [],
            'ride_requests': [],
            'matches': []
        }
        
        # Get all users
        users = list(self.mongo_db.mongo.get_collection("users").find({}))
        for user in users:
            snapshot['users'].append({
                'phone': user.get('phone_number'),
                'name': user.get('full_name'),
                'type': user.get('user_type'),
                'state': user.get('current_state')
            })
        
        # Get all routines
        routines = list(self.mongo_db.mongo.get_collection("routines").find({}))
        for routine in routines:
            snapshot['routines'].append({
                'phone': routine.get('phone_number'),
                'destination': routine.get('destination'),
                'days': routine.get('days'),
                'departure_time': routine.get('departure_time')
            })
        
        # Get all ride requests
        ride_requests = list(self.mongo_db.mongo.get_collection("ride_requests").find({}))
        for req in ride_requests:
            snapshot['ride_requests'].append({
                'request_id': req.get('request_id'),
                'phone': req.get('requester_phone'),
                'destination': req.get('destination'),
                'status': req.get('status')
            })
        
        # Get all matches
        matches = list(self.mongo_db.mongo.get_collection("matches").find({}))
        for match in matches:
            snapshot['matches'].append({
                'match_id': match.get('match_id'),
                'status': match.get('status'),
                'driver_response': match.get('driver_response')
            })
        
        self.scenario_data['db_snapshots'].append(snapshot)
    
    def _collect_matches_and_notifications(self):
        """Collect all matches and notifications from database"""
        if not hasattr(self.mongo_db, '_use_mongo') or not self.mongo_db._use_mongo:
            return
        
        # Get all matches
        matches = list(self.mongo_db.mongo.get_collection("matches").find({}))
        for match in matches:
            self.scenario_data['matches'].append({
                'match_id': match.get('match_id'),
                'status': match.get('status'),
                'driver_response': match.get('driver_response'),
                'matched_at': match.get('matched_at')
            })
        
        # Get all notifications (from WhatsApp client)
        sent_messages = self.whatsapp_client.get_sent_messages()
        for msg in sent_messages:
            self.scenario_data['notifications'].append({
                'to': msg['to'],
                'message': msg['message'],
                'buttons': msg.get('buttons'),
                'timestamp': datetime.now()
            })
    
    def _get_log_files(self) -> List[Dict[str, str]]:
        """Get list of log files created during this scenario"""
        import os
        log_files = []
        
        if hasattr(self.engine, 'user_logger'):
            logs_dir = self.engine.user_logger.logs_dir
            if logs_dir and os.path.exists(logs_dir):
                for filename in sorted(os.listdir(logs_dir)):
                    if filename.endswith('.log') and filename.startswith('user_'):
                        phone = filename.replace('user_', '').replace('.log', '')
                        log_files.append({
                            'phone': phone,
                            'filename': filename,
                            'path': os.path.join(logs_dir, filename)
                        })
        
        return log_files


def load_integration_scenarios(yaml_file: str = "tests/test_integration_inputs.yml") -> list:
    """Load integration scenarios from YAML file"""
    yaml_path = Path(project_root) / yaml_file
    
    if not yaml_path.exists():
        pytest.fail(f"Integration test input file not found: {yaml_path}")
    
    with open(yaml_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    return data.get('scenarios', [])


@pytest.fixture(scope="function")
def integration_scenarios():
    """Load all integration scenarios from YAML file"""
    return load_integration_scenarios()


def test_all_integration_scenarios(integration_conversation_engine, mongo_db, integration_scenarios):
    """
    Test all integration scenarios and generate HTML report
    
    This test runs all scenarios and generates a comprehensive HTML report
    showing data persistence, matching, and notifications
    """
    from tests.mock_whatsapp_client import MockWhatsAppClient
    
    # Create timestamped folder for this test run
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    test_runs_base = Path(project_root) / "test_runs"
    test_run_dir = test_runs_base / f"integration_run_{timestamp}"
    test_run_dir.mkdir(parents=True, exist_ok=True)
    
    # Create/update latest directory structure
    latest_dir = test_runs_base / "latest"
    # If latest is a symlink, remove it and create a directory
    if latest_dir.exists() and latest_dir.is_symlink():
        latest_dir.unlink()
    if not latest_dir.exists():
        latest_dir.mkdir(exist_ok=True)
    
    # Create symbolic link to integration directory in latest
    import shutil
    latest_integration_link = latest_dir / "integration"
    if latest_integration_link.exists() or latest_integration_link.is_symlink():
        if latest_integration_link.is_symlink():
            latest_integration_link.unlink()
        elif latest_integration_link.is_dir():
            shutil.rmtree(latest_integration_link)
    latest_integration_link.symlink_to(f"../{test_run_dir.name}")
    
    # Also keep the old symlink for backward compatibility
    latest_link = test_runs_base / "latest_integration"
    if latest_link.exists() or latest_link.is_symlink():
        latest_link.unlink()
    latest_link.symlink_to(test_run_dir.name)
    
    # Create logs subdirectory
    test_logs_dir = test_run_dir / "logs"
    test_logs_dir.mkdir(exist_ok=True)
    
    # Update user logger to use test logs directory
    original_logs_dir = integration_conversation_engine.user_logger.logs_dir
    integration_conversation_engine.user_logger.logs_dir = str(test_logs_dir)
    
    # Create WhatsApp client mock with user logger (for automatic logging)
    whatsapp_client = MockWhatsAppClient(user_logger=integration_conversation_engine.user_logger)
    
    # Update conversation engine services with mock WhatsApp client
    if hasattr(mongo_db, '_use_mongo') and mongo_db._use_mongo:
        from src.services.matching_service import MatchingService
        from src.services.notification_service import NotificationService
        
        matching_service = MatchingService(mongo_db.mongo)
        notification_service = NotificationService(mongo_db.mongo, whatsapp_client, integration_conversation_engine.user_logger)
        integration_conversation_engine.action_executor.matching_service = matching_service
        integration_conversation_engine.action_executor.notification_service = notification_service
    
    # Create report generator
    report_filename = "integration_test_report.html"
    report_generator = IntegrationReportGenerator(report_filename)
    
    passed_count = 0
    failed_count = 0
    
    # Run each scenario
    for scenario in integration_scenarios:
        # Clear database before each scenario
        if hasattr(mongo_db, '_use_mongo') and mongo_db._use_mongo:
            mongo_db.mongo.get_collection("users").delete_many({})
            mongo_db.mongo.get_collection("routines").delete_many({})
            mongo_db.mongo.get_collection("ride_requests").delete_many({})
            mongo_db.mongo.get_collection("matches").delete_many({})
            mongo_db.mongo.get_collection("notifications").delete_many({})
        
        # Clear WhatsApp client
        whatsapp_client.clear_messages()
        
        # Create tester
        tester = IntegrationScenarioTester(integration_conversation_engine, mongo_db, whatsapp_client)
        
        try:
            # Run scenario
            result = tester.run_scenario(scenario)
            
            # Check if scenario succeeded (no errors)
            success = not any(
                interaction.get('error') for interaction in result['interactions']
            )
            
            if success:
                passed_count += 1
            else:
                failed_count += 1
            
            # Add to report
            report_generator.add_scenario(result)
            
        except Exception as e:
            failed_count += 1
            # Add error scenario to report
            report_generator.add_scenario({
                'scenario_id': scenario.get('id'),
                'scenario_name': scenario.get('name'),
                'scenario_description': scenario.get('description'),
                'interactions': [],
                'db_snapshot': {},
                'matches': [],
                'notifications': [],
                'users': {},
                'error': str(e)
            })
    
    # Restore original logs directory
    integration_conversation_engine.user_logger.logs_dir = original_logs_dir
    
    # Generate and save report
    report_path = report_generator.save_report(output_dir=str(test_run_dir))
    
    # Copy integration report to latest directory
    import shutil
    latest_report = latest_dir / "integration_test_report.html"
    if report_path and Path(report_path).exists():
        shutil.copy2(report_path, latest_report)
    
    # Create index.html in latest directory
    try:
        from tests.create_latest_index import create_latest_index
        create_latest_index(test_runs_base)
    except Exception as e:
        print(f"Warning: Failed to create latest index: {e}")
    
    # Create summary file
    summary_file = test_run_dir / "summary.txt"
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("="*80 + "\n")
        f.write("INTEGRATION TEST RUN SUMMARY\n")
        f.write("="*80 + "\n")
        f.write(f"Run Date/Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total scenarios tested: {len(integration_scenarios)}\n")
        f.write(f"✅ Passed: {passed_count}\n")
        f.write(f"❌ Failed: {failed_count}\n")
        f.write(f"\nTest Run Directory: {test_run_dir}\n")
        f.write(f"Latest Link: {latest_link} -> {test_run_dir.name}\n")
        f.write(f"Report: {report_path}\n")
        f.write(f"Logs: {test_logs_dir}\n")
        f.write("="*80 + "\n")
    
    # Print summary
    total = len(integration_scenarios)
    print(f"\n{'='*80}")
    print(f"📊 INTEGRATION TEST SUMMARY")
    print(f"{'='*80}")
    print(f"Run Date/Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total scenarios tested: {total}")
    print(f"✅ Passed: {passed_count}")
    print(f"❌ Failed: {failed_count}")
    print(f"\n📁 Test Run Directory: {test_run_dir}")
    print(f"🔗 Latest Link: {latest_link} -> {test_run_dir.name}")
    print(f"📄 Report: {report_path}")
    print(f"📝 Logs: {test_logs_dir}")
    print(f"📋 Summary: {summary_file}")
    print(f"{'='*80}")
    
    # Assert that all scenarios passed
    assert failed_count == 0, f"{failed_count} out of {total} scenarios failed. See report for details."


if __name__ == '__main__':
    # Allow running directly for debugging
    pytest.main([__file__, '-v', '--tb=short'])

