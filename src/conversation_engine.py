"""
Conversation flow engine that processes the conversation flow JSON
"""

import json
import logging
import re
import os
from typing import Dict, Any, Tuple, Optional

# Configure logging if not already configured
from src.logging_config import setup_logging
setup_logging()

from src.validation import validate_settlement, validate_days, validate_time, validate_time_range, validate_name, validate_text_input, validate_datetime
from src.user_logger import UserLogger
from src.command_handlers import CommandHandler
from src.action_executor import ActionExecutor
from src.message_formatter import MessageFormatter

logger = logging.getLogger(__name__)

class ConversationEngine:
    """Engine to process conversation flow"""
    
    # State type constants for validation
    NAME_STATES = ['ask_full_name']
    SETTLEMENT_STATES = ['ask_destination', 'ask_routine_destination', 
                        'ask_default_destination_name', 'ask_hitchhiker_destination', 'ask_driver_destination']
    DAYS_STATES = ['ask_routine_days']
    TIME_STATES = ['ask_routine_departure_time', 'ask_routine_return_time']
    TIME_RANGE_STATES = ['ask_time_range']
    TEXT_STATES = ['ask_specific_datetime']
    
    def __init__(self, flow_file='conversation_flow.json', user_db=None, user_logger=None):
        # If relative path, look in src/ directory
        if not os.path.isabs(flow_file) and not os.path.exists(flow_file):
            src_dir = os.path.dirname(os.path.abspath(__file__))
            flow_file = os.path.join(src_dir, flow_file)
        self.flow_file = flow_file
        self.user_db = user_db
        self.user_logger = user_logger or UserLogger()
        self.flow = self._load_flow()
        self.command_handler = CommandHandler(self)
        
        # Initialize services (MongoDB is always available now)
        matching_service = None
        notification_service = None
        
        from src.services.matching_service import MatchingService
        from src.services.notification_service import NotificationService
        
        matching_service = MatchingService(user_db.mongo)
        # Notification service needs WhatsApp client - will be set in app.py
        # For now, create without client (will be updated in app.py)
        notification_service = None  # Will be set in app.py after WhatsApp client is initialized
        
        self.action_executor = ActionExecutor(user_db, matching_service, notification_service)
        
        # Store user_logger for later use when notification_service is set
        self._user_logger = user_logger
        self.message_formatter = MessageFormatter(user_db)
    
    def _load_flow(self) -> Dict[str, Any]:
        """Load conversation flow from JSON"""
        try:
            with open(self.flow_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load conversation flow: {e}")
            return {'states': {}, 'commands': {}}
    
    def process_message(self, phone_number: str, message_text: str) -> Tuple[str, Optional[list]]:
        """
        Process incoming message and return response with optional buttons
        
        Args:
            phone_number: User's phone number
            message_text: Message text from user
            
        Returns:
            Tuple of (response_message, buttons_list)
        """
        message_text = message_text.strip()
        
        # Log incoming message
        self.user_logger.log_user_message(phone_number, message_text)
        
        # Check for special commands
        command_response = self._check_commands(phone_number, message_text)
        if command_response:
            response_msg, buttons = command_response if isinstance(command_response, tuple) else (command_response, None)
            # Logging is now automatic in WhatsAppClient.send_message (lowest level)
            return response_msg, buttons
        
        # Get user's current state
        if not self.user_db.user_exists(phone_number):
            self.user_db.create_user(phone_number)
        
        current_state_id = self.user_db.get_user_state(phone_number)
        
        # If registered user sending message after idle or registration_complete, show menu
        # Also check if user has completed profile (has user_type) even if not marked as registered
        if current_state_id in ['idle', 'registration_complete']:
            user = self.user_db.get_user(phone_number)
            if not user:
                # User doesn't exist - restart registration
                logger.info(f"User {phone_number} in {current_state_id} but doesn't exist, restarting registration")
                current_state_id = 'initial'
                self.user_db.set_user_state(phone_number, current_state_id)
            else:
                # Get profile from user document (MongoDB stores directly in user, not nested in 'profile')
                profile = user.get('profile', {})
                # Also check user document directly for user_type (MongoDB stores it at root level)
                user_type = user.get('user_type') or profile.get('user_type')
                is_registered = self.user_db.is_registered(phone_number)
                has_user_type = user_type is not None
                
                logger.info(f"User {phone_number} in {current_state_id}: is_registered={is_registered}, has_user_type={has_user_type}, user_type={user_type}")
                
                if is_registered or has_user_type:
                    # If user has profile but not marked as registered, mark them now
                    if has_user_type and not is_registered:
                        self.user_db.complete_registration(phone_number)
                        logger.info(f"Marked user {phone_number} as registered (had profile)")
                    
                    # Move to idle first if in registration_complete
                    if current_state_id == 'registration_complete':
                        self.user_db.set_user_state(phone_number, 'idle', {'last_state': 'idle'})
                    
                    current_state_id = 'registered_user_menu'
                    self.user_db.set_user_state(phone_number, current_state_id)
                    logger.info(f"Moving user {phone_number} to registered_user_menu")
                else:
                    # User in idle but not registered - restart registration flow
                    logger.warning(f"User {phone_number} in {current_state_id} but not registered (is_registered={is_registered}, has_user_type={has_user_type}), restarting registration")
                    current_state_id = 'initial'
                    self.user_db.set_user_state(phone_number, current_state_id)
        
        # Get current state definition
        current_state = self.flow['states'].get(current_state_id)
        
        if not current_state:
            logger.error(f"State not found: {current_state_id}")
            return "מצטער, משהו השתבש. הקש 'חדש' כדי להתחיל מחדש.", None
        
        # Process input based on state
        result = self._process_state(phone_number, current_state, message_text)
        
        # Handle different return formats
        if len(result) == 3:
            response, next_state, buttons = result
        else:
            response, next_state = result
            buttons = None
        
        # Determine which state to log
        # If moving to next_state, log that state (since message is for next state)
        # Otherwise, log current state
        log_state = next_state if next_state else current_state_id
        
        # Move to next state BEFORE logging (so log shows correct state)
        if next_state:
            logger.info(f"🔄 Moving to next_state: {next_state} (from state: {current_state_id})")
            # Set last_state to the new state (message was already shown in response)
            # Don't add to history here - it will be added when state actually changes
            self.user_db.set_user_state(phone_number, next_state, {'last_state': next_state}, add_to_history=True)
            
            # If next state has automatic message, append it (but ONLY if not already in response)
            next_state_def = self.flow['states'].get(next_state)
            if next_state_def:
                logger.info(f"📋 Next state def: id={next_state_def.get('id')}, message={bool(next_state_def.get('message'))}, expected_input={next_state_def.get('expected_input')}, action={next_state_def.get('action')}")
                
                # Perform action if specified (important for states like confirm_hitchhiker_ride_request)
                # Action should be executed regardless of whether message is already in response
                if next_state_def.get('action') and not next_state_def.get('expected_input'):
                    logger.info(f"✅ Executing action '{next_state_def.get('action')}' for state '{next_state}'")
                    self.action_executor.execute(phone_number, next_state_def['action'], {})
                    
                    # Store ride request ID for auto-approval processing after message is sent
                    # This will be handled in app.py after the message is sent
                    if next_state_def.get('action') == 'save_hitchhiker_ride_request':
                        from bson import ObjectId
                        user = self.user_db.mongo.get_collection("users").find_one({"phone_number": phone_number})
                        if user:
                            ride_request = self.user_db.mongo.get_collection("ride_requests").find_one(
                                {"requester_id": user['_id']},
                                sort=[("created_at", -1)]
                            )
                            if ride_request:
                                # Store ride request ID in user context for later processing
                                self.user_db.update_context(phone_number, 'pending_auto_approval_ride_request_id', str(ride_request['_id']))
                                logger.info(f"📝 Stored ride request {ride_request['_id']} for auto-approval processing after message is sent")
                
                next_message = self._get_state_message(phone_number, next_state_def)
                # Check if message isn't already in response (avoid duplicates)
                if next_message and next_message.strip() not in response:
                    response = f"{response}\n\n{next_message}"
                    # Update log_state to the auto next state
                    log_state = next_state_def.get('id', log_state)
                    
                    # Check if there's another next state
                    auto_next_state = self._get_next_state(phone_number, next_state_def, None)
                    if auto_next_state:
                        self.user_db.set_user_state(phone_number, auto_next_state, {'last_state': auto_next_state})
                        log_state = auto_next_state  # Update log state to auto next
                        # Get buttons for the auto next state
                        auto_next_state_def = self.flow['states'].get(auto_next_state)
                        if auto_next_state_def:
                            buttons = self._build_buttons(auto_next_state_def)
        
        # Logging is now automatic in WhatsAppClient.send_message (lowest level)
        # We don't log here anymore - the message will be logged when it's actually sent
        
        return response, buttons
    
    def _process_state(self, phone_number: str, state: Dict[str, Any], user_input: str):
        """Process current state with user input
        
        Returns tuple of (message, next_state) or (message, next_state, buttons)
        """
        
        # Special handling for idle state - should have been handled in process_message
        # But if we reach here, it means user is not registered, so restart registration
        # BUT: Check if user is actually registered first (might be a race condition)
        if state.get('id') == 'idle':
            user = self.user_db.get_user(phone_number)
            if user:
                profile = user.get('profile', {})
                user_type = user.get('user_type') or profile.get('user_type')
                is_registered = self.user_db.is_registered(phone_number)
                has_user_type = user_type is not None
                
                if is_registered or has_user_type:
                    # User is registered - move to menu instead of restarting
                    logger.info(f"User {phone_number} in idle but is registered, moving to registered_user_menu")
                    self.user_db.set_user_state(phone_number, 'registered_user_menu', {'last_state': 'registered_user_menu'})
                    menu_state = self.flow['states'].get('registered_user_menu')
                    if menu_state:
                        return self._process_state(phone_number, menu_state, user_input)
            
            logger.warning(f"User {phone_number} in idle state but not registered, restarting registration")
            # Move to initial state to restart registration
            self.user_db.set_user_state(phone_number, 'initial', {'last_state': 'initial'})
            initial_state = self.flow['states'].get('initial')
            if initial_state:
                return self._process_state(phone_number, initial_state, user_input)
            # Fallback to ask_full_name
            ask_full_name_state = self.flow['states'].get('ask_full_name')
            if ask_full_name_state:
                message = self._get_state_message(phone_number, ask_full_name_state)
                buttons = self._build_buttons(ask_full_name_state)
                self.user_db.set_user_state(phone_number, 'ask_full_name', {'last_state': 'ask_full_name'})
                return message, 'ask_full_name', buttons
        
        # Check state conditions
        if not self._check_condition(phone_number, state):
            # Condition not met, move to else state or skip
            next_state = state.get('else_next_state')
            if next_state:
                next_state_def = self.flow['states'].get(next_state)
                if next_state_def:
                    # If next state is also a routing state, continue traversing
                    if not next_state_def.get('message') and not next_state_def.get('expected_input'):
                        return self._process_state(phone_number, next_state_def, user_input)
                    message = self._get_state_message(phone_number, next_state_def)
                    buttons = self._build_buttons(next_state_def)
                    return message, next_state, buttons
            return "שגיאה: תנאי לא התקיים", 'idle', None
        
        # IMPORTANT: If this is a routing state (no message, no expected_input),
        # process it immediately regardless of is_first_time or user input
        # This handles cases where user sends a message while in a routing state
        if not state.get('message') and not state.get('expected_input'):
            # This is a routing state - auto-advance to next state
            next_state = self._get_next_state(phone_number, state, user_input)
            if next_state:
                next_state_def = self.flow['states'].get(next_state)
                if next_state_def:
                    # If next state is also a routing state, continue traversing
                    if not next_state_def.get('message') and not next_state_def.get('expected_input'):
                        return self._process_state(phone_number, next_state_def, user_input)
                    # Get message from next state
                    message = self._get_state_message(phone_number, next_state_def)
                    buttons = self._build_buttons(next_state_def)
                    self.user_db.set_user_state(phone_number, next_state, {'last_state': next_state})
                    return message, next_state, buttons
            # No next state - shouldn't happen, but handle gracefully
            return "שגיאה: לא נמצא מצב המשך", 'idle', None
        
        # Check if this is the first time in this state (no previous input)
        # Check if current state matches the state we're processing
        current_state_id = self.user_db.get_user_state(phone_number)
        context = self.user_db.get_user_context(phone_number)
        
        # It's first time ONLY if current state doesn't match the state we're processing
        # If current state matches, user is already in this state and input should be processed
        is_first_time = current_state_id != state['id']
        
        # IMPORTANT: If user already sent input (user_input is not empty), process it immediately
        # This handles the case where state was just updated and user sent input in the same call
        # This is especially important for rapid state transitions in tests
        # This check MUST come BEFORE the special case check below
        if user_input and user_input.strip() and state.get('expected_input'):
            # User sent input - process it instead of showing first-time message
            is_first_time = False
        
        # Special case: if current state matches but last_state doesn't, it means state was updated
        # but context wasn't - still treat as first time to show the message
        # BUT only if user didn't send input (if they did, we already set is_first_time = False above)
        if current_state_id == state['id'] and context.get('last_state') != state['id'] and is_first_time:
            # State matches but context doesn't - update context and treat as first time
            self.user_db.set_user_state(phone_number, state['id'], {'last_state': state['id']}, add_to_history=False)
            # Only set to first time if user didn't send input
            if not (user_input and user_input.strip() and state.get('expected_input')):
                is_first_time = True
        
        # If first time AND state expects input, show message and wait for input
        # BUT if user already sent input (user_input is not empty and not a command), process it!
        if is_first_time:
            # Check if user_input looks like actual input (not empty, not just whitespace)
            # If it does, and we're in a state that expects input, process it instead of showing message
            if state.get('expected_input') and user_input and user_input.strip():
                # User already sent input - process it instead of showing first-time message
                is_first_time = False
            else:
                # First time and no input yet - show message
                message = self._get_state_message(phone_number, state)
                buttons = self._build_buttons(state)
                self.user_db.set_user_state(phone_number, state['id'], {'last_state': state['id']})
                
                # Perform action if specified on first entry to state (for states without input)
                if state.get('action') and not state.get('expected_input'):
                    self.action_executor.execute(phone_number, state['action'], {})
                
                # If state has no message and no input expected, auto-advance through routing states
                if not message and not state.get('expected_input'):
                    next_state = self._get_next_state(phone_number, state, None)
                    if next_state:
                        next_state_def = self.flow['states'].get(next_state)
                        if next_state_def:
                            # Continue traversing routing states recursively
                            if not next_state_def.get('message') and not next_state_def.get('expected_input'):
                                return self._process_state(phone_number, next_state_def, user_input)
                            message = self._get_state_message(phone_number, next_state_def)
                            buttons = self._build_buttons(next_state_def)
                            self.user_db.set_user_state(phone_number, next_state, {'last_state': next_state})
                            return message, next_state, buttons
                
                # Return with buttons even for first time
                # If state has expected_input, don't advance yet - wait for user input
                # But if state has no expected_input, we should advance to next_state
                if not state.get('expected_input'):
                    next_state = self._get_next_state(phone_number, state, None)
                    if next_state:
                        return message, next_state, buttons
                return message, None, buttons  # Don't advance yet, wait for user input
        
        # Update last_state in context to mark that we've processed input in this state
        # This prevents treating subsequent messages as first-time entry
        if not is_first_time:
            # User already in this state and sending input - update last_state
            self.user_db.set_user_state(phone_number, state['id'], {'last_state': state['id']}, add_to_history=False)
        
        # Process user input based on expected type
        expected_input = state.get('expected_input')
        
        if expected_input == 'choice':
            # Handle choice input (returns 3 values)
            return self._handle_choice_input(phone_number, state, user_input)
        
        elif expected_input == 'text':
            # Handle text input (returns 2 values: message, next_state)
            message, next_state = self._handle_text_input(phone_number, state, user_input)
            # Build buttons for the next state OR from suggestions
            buttons = None
            
            # Check if there are pending suggestions for interactive selection
            context = self.user_db.get_user_context(phone_number)
            if context.get('pending_suggestions') and not next_state:
                # Build buttons from suggestions
                suggestions = context['pending_suggestions']
                buttons = []
                for i, suggestion in enumerate(suggestions[:3], 1):  # Max 3 buttons
                    buttons.append({
                        'type': 'reply',
                        'reply': {
                            'id': str(i),
                            'title': suggestion[:20]  # WhatsApp button title max 20 chars
                        }
                    })
                # Add restart button (always included)
                buttons.append({
                    'type': 'reply',
                    'reply': {
                        'id': 'restart_button',
                        'title': '🔄 התחל מחדש'
                    }
                })
            elif next_state:
                next_state_def = self.flow['states'].get(next_state)
                if next_state_def:
                    buttons = self._build_buttons(next_state_def)
            return message, next_state, buttons
        
        else:
            # No input expected - this is a routing state or final state
            # Auto-advance to next state immediately
            next_state = self._get_next_state(phone_number, state, user_input)
            if next_state:
                next_state_def = self.flow['states'].get(next_state)
                if next_state_def:
                    # If next state is also a routing state, continue traversing
                    if not next_state_def.get('message') and not next_state_def.get('expected_input'):
                        return self._process_state(phone_number, next_state_def, user_input)
                    # Get message from next state
                    message = self._get_state_message(phone_number, next_state_def)
                    buttons = self._build_buttons(next_state_def)
                    self.user_db.set_user_state(phone_number, next_state, {'last_state': next_state})
                    return message, next_state, buttons
            
            # If no next state and we're in registration_complete or similar final state,
            # move to idle and show menu for registered users
            if state.get('id') == 'registration_complete':
                # Move to idle state
                self.user_db.set_user_state(phone_number, 'idle', {'last_state': 'idle'})
                # Check if user is registered and show menu
                profile = self.user_db.get_user(phone_number).get('profile', {})
                is_registered = self.user_db.is_registered(phone_number)
                has_user_type = profile.get('user_type') is not None
                
                if is_registered or has_user_type:
                    # Show registered user menu
                    menu_state = self.flow['states'].get('registered_user_menu')
                    if menu_state:
                        return self._process_state(phone_number, menu_state, user_input)
            
            # No next state - shouldn't happen, but handle gracefully
            return "תודה! הפרטים נשמרו.", None, None
    
    def _handle_choice_input(self, phone_number: str, state: Dict[str, Any], user_input: str) -> Tuple[str, Optional[str], Optional[list]]:
        """Handle choice-based input
        
        Returns:
            Tuple of (message, next_state, buttons)
        """
        # Check if user clicked restart button
        if user_input == 'restart_button':
            return self._handle_restart(phone_number)
        
        # Handle confirm_restart state specially
        if state.get('id') == 'confirm_restart':
            options = state.get('options', {})
            if user_input in options:
                choice = options[user_input]
                if choice.get('value') == 'yes' and choice.get('action') == 'restart_user':
                    # User confirmed restart - perform it
                    return self._handle_restart(phone_number)
                elif choice.get('value') == 'no':
                    # User cancelled - go back to menu
                    next_state = choice.get('next_state', 'registered_user_menu')
                    next_state_def = self.flow['states'].get(next_state)
                    if next_state_def:
                        message = self._get_state_message(phone_number, next_state_def)
                        buttons = self._build_buttons(next_state_def)
                        return message, next_state, buttons
                    return "חזרתי לתפריט.", next_state, None
        
        options = state.get('options', {})
        
        if user_input in options:
            choice = options[user_input]
            
            # Check if action is restart_user
            if choice.get('action') == 'restart_user':
                # Check if we're in a state that requires confirmation
                if self.user_db.is_registered(phone_number) and state.get('id') != 'confirm_restart':
                    # Move to confirmation state
                    self.user_db.set_user_state(phone_number, 'confirm_restart', add_to_history=False)
                    confirm_state = self.flow['states'].get('confirm_restart')
                    if confirm_state:
                        message = self._get_state_message(phone_number, confirm_state)
                        buttons = self._build_buttons(confirm_state)
                        return message, 'confirm_restart', buttons
                # Not registered or already confirmed - restart immediately
                return self._handle_restart(phone_number)
            
            # Save to profile if needed (check both state and choice for save_to)
            save_to_key = choice.get('save_to') or state.get('save_to')
            if save_to_key:
                self.user_db.save_to_profile(phone_number, save_to_key, choice['value'])
                logger.info(f"Saved {save_to_key} = '{choice['value']}' for {phone_number}")
            
            # Perform action if specified
            if choice.get('action'):
                # Handle special actions
                if choice.get('action') == 'show_help_command':
                    # Show help via command handler
                    help_msg, help_buttons = self.command_handler.handle_show_help(phone_number)
                    return help_msg, None, help_buttons
                self.action_executor.execute(phone_number, choice['action'], choice)
            
            # Get next state
            next_state = choice.get('next_state')
            
            # Check if choice has a custom message (response message for this choice)
            choice_message = choice.get('message')
            
            # Get next state message and buttons
            if next_state:
                next_state_def = self.flow['states'].get(next_state)
                next_state_message = self._get_state_message(phone_number, next_state_def)
                buttons = self._build_buttons(next_state_def)
                
                # If choice has a custom message, combine it with next state message
                # This allows showing both the response to the choice AND the next state message
                if choice_message:
                    # If next state has a message, combine them (choice message first, then next state)
                    if next_state_message:
                        # Combine messages: choice response + next state message
                        message = f"{choice_message}\n\n{next_state_message}"
                    else:
                        # Next state is routing - use choice message and process routing
                        message = choice_message
                        # Process routing states recursively to get final state
                        final_state = next_state_def
                        while final_state and not final_state.get('message') and not final_state.get('expected_input'):
                            final_next = self._get_next_state(phone_number, final_state, None)
                            if final_next:
                                final_state = self.flow['states'].get(final_next)
                                if final_state:
                                    next_state = final_next
                                    next_state_def = final_state
                                    next_state_message = self._get_state_message(phone_number, final_state)
                                    buttons = self._build_buttons(final_state)
                                    # If final state has message, combine with choice message
                                    if next_state_message:
                                        message = f"{choice_message}\n\n{next_state_message}"
                                else:
                                    break
                            else:
                                break
                        # Update state to final state (likely idle)
                        if next_state:
                            self.user_db.set_user_state(phone_number, next_state, {'last_state': next_state}, add_to_history=True)
                else:
                    message = next_state_message
            else:
                # No next state - use choice message if available, otherwise default
                message = choice_message if choice_message else "תודה!"
                buttons = None
            
            return message, next_state, buttons
        else:
            # Invalid choice - provide clearer error message with context
            options_list = list(state.get('options', {}).keys())
            state_id = state.get('id', 'unknown')
            
            # Build helpful error message
            if options_list:
                # Show available options with labels
                options_labels = []
                for opt_id in options_list:
                    opt_data = state.get('options', {}).get(opt_id, {})
                    label = opt_data.get('label', opt_id)
                    options_labels.append(f"{opt_id} ({label})")
                
                error_msg = f"❌ נראה שהקלדת טקסט במקום לבחור מספר.\n\n💡 אנא בחר אחת מהאפשרויות:\n" + "\n".join([f"• {opt}" for opt in options_labels])
                
                # Add context based on state
                if 'user_type' in state_id:
                    error_msg += "\n\n(פשוט הקש 1, 2 או 3) 👆"
                elif 'when' in state_id or 'time' in state_id.lower():
                    error_msg += "\n\n(פשוט הקש 1, 2, 3 או 4) 👆"
                elif 'routine' in state_id:
                    error_msg += "\n\n(פשוט הקש 1 או 2) 👆"
                else:
                    error_msg += "\n\n(פשוט הקש את המספר של האפשרות שברצונך לבחור) 👆"
            else:
                error_msg = "❌ בחירה לא חוקית. אנא בחר מהאפשרויות המוצגות."
            
            buttons = self._build_buttons(state)
            return error_msg, None, buttons
    
    def _handle_text_input(self, phone_number: str, state: Dict[str, Any], user_input: str) -> Tuple[str, Optional[str]]:
        """Handle text input with validation
        
        Returns tuple of (message, next_state)
        """
        state_id = state.get('id')
        
        # Check if user is responding to a previous suggestion
        context = self.user_db.get_user_context(phone_number)
        if context.get('pending_suggestions'):
            suggestions = context.get('pending_suggestions')
            
            # Check if user clicked restart button
            if user_input == 'restart_button':
                self.user_db.update_context(phone_number, 'pending_suggestions', None)
                # Call restart handler but return only 2 values for text input
                restart_msg, restart_state, _ = self._handle_restart(phone_number)
                return restart_msg, restart_state
            
            # Check if user selected by number (from button click)
            if user_input.isdigit():
                idx = int(user_input) - 1
                if 0 <= idx < len(suggestions):
                    # User selected a suggestion
                    selected_value = suggestions[idx]
                    # Clear pending suggestions
                    self.user_db.update_context(phone_number, 'pending_suggestions', None)
                    # Save the selected value
                    if state.get('save_to'):
                        self.user_db.save_to_profile(phone_number, state['save_to'], selected_value)
                        logger.info(f"Saved {state['save_to']} = '{selected_value}' for {phone_number}")
                    # Continue to next state
                    next_state = state.get('next_state')
                    if next_state:
                        next_state_def = self.flow['states'].get(next_state)
                        if next_state_def and not next_state_def.get('message') and not next_state_def.get('expected_input'):
                            auto_next_state = self._get_next_state(phone_number, next_state_def, None)
                            if auto_next_state:
                                next_state_def = self.flow['states'].get(auto_next_state)
                                next_state = auto_next_state
                        message = self._get_state_message(phone_number, next_state_def) if next_state_def else "תודה!"
                        return message, next_state
            # Clear suggestions if user typed something else (new input)
            self.user_db.update_context(phone_number, 'pending_suggestions', None)
        
        # Validation based on state
        validation_result = self._validate_input(state_id, user_input)
        
        if not validation_result['is_valid']:
            # Return error message with suggestions if available
            error_msg = validation_result['error_message']
            if validation_result.get('suggestions'):
                suggestions = validation_result['suggestions']
                # Save suggestions to context for interactive buttons
                self.user_db.update_context(phone_number, 'pending_suggestions', suggestions)
                # Only use "הישוב" message for settlement states, use original error message otherwise
                if state_id in self.SETTLEMENT_STATES:
                    error_msg = f"הישוב \"{user_input}\" לא נמצא במערכת. 🤔\n\n💡 התכוונת ל:\n"
                # Note: suggestions will be shown as buttons, not text
            else:
                # Enhanced error messages with examples and context
                error_msg = self.message_formatter.get_enhanced_error_message(state_id, state, user_input, error_msg)
            
            return error_msg, None
        
        # If validation passed, use normalized value
        final_value = validation_result.get('normalized_value', user_input)
        
        # Save input to profile
        if state.get('save_to'):
            self.user_db.save_to_profile(phone_number, state['save_to'], final_value)
            logger.info(f"Saved {state['save_to']} = '{final_value}' for {phone_number}")
        
        # Perform action if specified (but only if not already executed in next_state)
        # Skip action here if next_state has the same action - it will be executed there
        next_state = state.get('next_state')
        next_state_def = self.flow['states'].get(next_state) if next_state else None
        
        if state.get('action'):
            # Only execute if next_state doesn't have the same action
            if not (next_state_def and next_state_def.get('action') == state.get('action')):
                self.action_executor.execute(phone_number, state['action'], {'input': final_value})
            else:
                logger.debug(f"Skipping action '{state.get('action')}' - will be executed in next_state '{next_state}'")
        
        # Special handling: If registered user is updating name, return to show_my_info
        if state_id == 'ask_full_name' and self.user_db.is_registered(phone_number):
            # User is updating name, not registering - return to show_my_info
            next_state = 'show_my_info'
            next_state_def = self.flow['states'].get(next_state)
            if next_state_def:
                message = self._get_state_message(phone_number, next_state_def)
                buttons = self._build_buttons(next_state_def)
                return message, next_state
        
        # Get next state
        next_state = state.get('next_state')
        
        if not next_state:
            return "תודה! הפרטים נשמרו.", None
        
        # Get next state definition
        next_state_def = self.flow['states'].get(next_state)
        if not next_state_def:
            return "תודה! הפרטים נשמרו.", None
        
        # Check if next state is a routing state (no message, no input)
        if not next_state_def.get('message') and not next_state_def.get('expected_input'):
            # Auto-advance through routing state
            auto_next_state = self._get_next_state(phone_number, next_state_def, None)
            if auto_next_state:
                next_state_def = self.flow['states'].get(auto_next_state)
                next_state = auto_next_state
        
        # Don't execute action here - it will be executed in _process_message when transitioning to next_state
        # This prevents duplicate execution. The action is executed once in _process_message (line 161-162)
        
        # Get next state message
        message = self._get_state_message(phone_number, next_state_def)
        
        return message, next_state
    
    def _validate_input(self, state_id: str, user_input: str) -> Dict[str, Any]:
        """
        Validate user input based on state
        
        Returns:
            Dict with keys: is_valid, normalized_value, error_message, suggestions
        """
        if state_id in self.NAME_STATES:
            is_valid, normalized, error_msg = validate_name(user_input)
            return {
                'is_valid': is_valid,
                'normalized_value': normalized,
                'error_message': error_msg,
                'suggestions': None
            }
        
        elif state_id in self.SETTLEMENT_STATES:
            is_valid, exact_match, suggestions = validate_settlement(user_input)
            if is_valid:
                return {
                    'is_valid': True,
                    'normalized_value': exact_match,
                    'error_message': None,
                    'suggestions': None
                }
            else:
                # Invalid settlement - require valid input
                if suggestions:
                    return {
                        'is_valid': False,
                        'normalized_value': None,
                        'error_message': f'הישוב "{user_input}" לא נמצא במערכת. 🤔',
                        'suggestions': suggestions
                    }
                else:
                    return {
                        'is_valid': False,
                        'normalized_value': None,
                        'error_message': f'הישוב "{user_input}" לא נמצא במערכת. 😅\n\nנסה לכתוב שם ישוב מוכר (למשל: ירושלים, תל אביב, חיפה...)',
                        'suggestions': None
                    }
        
        elif state_id in self.DAYS_STATES:
            is_valid, normalized, error_msg = validate_days(user_input)
            return {
                'is_valid': is_valid,
                'normalized_value': normalized,
                'error_message': error_msg,
                'suggestions': None
            }
        
        elif state_id in self.TIME_STATES:
            is_valid, normalized, error_msg = validate_time(user_input)
            return {
                'is_valid': is_valid,
                'normalized_value': normalized,
                'error_message': error_msg,
                'suggestions': None
            }
        
        elif state_id in self.TIME_RANGE_STATES:
            is_valid, normalized, error_msg = validate_time_range(user_input)
            return {
                'is_valid': is_valid,
                'normalized_value': normalized,
                'error_message': error_msg,
                'suggestions': None
            }
        
        elif state_id in self.TEXT_STATES:
            # Special handling for datetime states
            if state_id == 'ask_specific_datetime':
                is_valid, normalized, error_msg = validate_datetime(user_input)
                return {
                    'is_valid': is_valid,
                    'normalized_value': normalized,
                    'error_message': error_msg,
                    'suggestions': None
                }
            else:
                # Generic text validation for other text fields
                is_valid, normalized, error_msg = validate_text_input(user_input, min_length=1, max_length=200)
                return {
                    'is_valid': is_valid,
                    'normalized_value': normalized,
                    'error_message': error_msg,
                    'suggestions': None
                }
        
        # Default: basic validation (not empty, reasonable length)
        user_input_stripped = user_input.strip()
        if not user_input_stripped:
            return {
                'is_valid': False,
                'normalized_value': None,
                'error_message': "קלט לא יכול להיות ריק. אנא הכנס ערך תקין.",
                'suggestions': None
            }
        
        if len(user_input_stripped) > 1000:
            return {
                'is_valid': False,
                'normalized_value': None,
                'error_message': "קלט ארוך מדי. אנא הכנס עד 1000 תווים.",
                'suggestions': None
            }
        
        return {
            'is_valid': True,
            'normalized_value': user_input_stripped,
            'error_message': None,
            'suggestions': None
        }
    
    def _get_user_summary(self, phone_number: str) -> str:
        """Generate a summary of user information for display in messages"""
        return self.message_formatter.get_user_summary(phone_number)
    
    def _get_state_message(self, phone_number: str, state: Dict[str, Any]) -> str:
        """Get message for state with variable substitution"""
        return self.message_formatter.format_message(phone_number, state)
    
    def _get_next_state(self, phone_number: str, state: Dict[str, Any], user_input: Optional[str]) -> Optional[str]:
        """Determine next state based on conditions"""
        # Check for conditional next state
        if state.get('condition'):
            if self._check_condition(phone_number, state):
                return state.get('next_state')
            else:
                return state.get('else_next_state')
        
        return state.get('next_state')
    
    def _check_condition(self, phone_number: str, state: Dict[str, Any]) -> bool:
        """Check if state condition is met"""
        condition = state.get('condition')
        
        if not condition:
            return True
        
        # Parse condition
        if condition == 'user_not_registered':
            return not self.user_db.is_registered(phone_number)
        
        elif condition == 'user_registered':
            return self.user_db.is_registered(phone_number)
        
        elif condition == 'user_type_is_both':
            user_type = self.user_db.get_profile_value(phone_number, 'user_type')
            return user_type == 'both'
        
        elif condition == 'user_is_driver':
            user_type = self.user_db.get_profile_value(phone_number, 'user_type')
            return user_type == 'driver'
        
        elif condition == 'user_is_hitchhiker':
            user_type = self.user_db.get_profile_value(phone_number, 'user_type')
            return user_type == 'hitchhiker'
        
        elif condition == 'has_default_destination':
            default_dest = self.user_db.get_profile_value(phone_number, 'default_destination')
            return default_dest is not None and default_dest != ''
        
        # Default: condition met
        return True
    
    def _handle_restart(self, phone_number: str) -> Tuple[str, Optional[str], Optional[list]]:
        """Handle restart action - full user data reset"""
        # Log restart event BEFORE clearing (so it's saved)
        self.user_logger.log_event(phone_number, 'restart', {'reason': 'user_requested'})
        
        # Delete all user data to start fresh
        self.user_db.delete_user_data(phone_number)
        
        # Clear all context variables to ensure complete cleanup
        # Create a fresh user first to ensure user exists
        self.user_db.create_user(phone_number)
        
        # Explicitly reset context to ensure no state leaks
        self.user_db.set_user_state(phone_number, 'initial', {})
        
        # Note: We keep the logs (don't delete) so we have history
        # If you want to delete logs on restart, uncomment the next line:
        # self.user_logger.clear_user_logs(phone_number)
        
        # Get initial state and first actual state
        initial_state = self.flow['states']['initial']
        next_state = initial_state.get('next_state', 'ask_full_name')
        next_state_def = self.flow['states'].get(next_state)
        
        # Build welcome message and buttons
        message = self._get_state_message(phone_number, next_state_def)
        buttons = self._build_buttons(next_state_def)
        
        # Set user to the first state
        self.user_db.set_user_state(phone_number, next_state, {'last_state': next_state})
        
        return message, next_state, buttons
    
    def _check_commands(self, phone_number: str, message_text: str):
        """Check if message is a special command
        
        Returns:
            None if not a command, or tuple of (message, buttons) if is a command
        """
        commands = self.flow.get('commands', {})
        
        if message_text in commands:
            command = commands[message_text]
            
            if command == 'go_back':
                return self.command_handler.handle_go_back(phone_number)
            
            elif command == 'restart':
                return self.command_handler.handle_restart(phone_number, require_confirmation=True)
            
            elif command == 'delete_data':
                return self.command_handler.handle_delete_data(phone_number)
            
            elif command == 'show_help':
                return self.command_handler.handle_show_help(phone_number)
            
            elif command == 'show_menu':
                return self.command_handler.handle_show_menu(phone_number)
        
        return None
    
    def _build_buttons(self, state: Dict[str, Any]) -> Optional[list]:
        """
        Build button list from state options with restart button
        
        Args:
            state: State definition dict
            
        Returns:
            List of button dicts or None if no options
        """
        if not state or state.get('expected_input') != 'choice':
            return None
        
        options = state.get('options', {})
        if not options:
            return None
        
        buttons = []
        has_restart_option = False
        
        for option_id, option_data in options.items():
            buttons.append({
                'id': option_id,
                'title': option_data.get('label', f'אפשרות {option_id}')
            })
            # Check if this option is a restart option
            label_lower = option_data.get('label', '').lower()
            if (option_data.get('value') == 'restart' or 
                option_data.get('action') == 'restart_user' or 
                'restart' in label_lower or
                'התחל מחדש' in option_data.get('label', '') or
                'איפוס' in option_data.get('label', '')):
                has_restart_option = True
        
        # Add restart button only if not already present in options
        # If we have 3 or fewer buttons, it will become a list (supports up to 10)
        # If we already have many buttons, add restart as last option
        if not has_restart_option and len(buttons) < 10:
            buttons.append({
                'id': 'restart_button',
                'title': '🔄 התחל מחדש',
                'description': 'חזור להתחלה' if len(buttons) >= 3 else None
            })
        
        return buttons if buttons else None
    

