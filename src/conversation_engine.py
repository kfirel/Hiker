"""
Conversation flow engine that processes the conversation flow JSON
"""

import json
import logging
import re
import os
from typing import Dict, Any, Tuple, Optional
from src.validation import validate_settlement, validate_days, validate_time, validate_time_range, validate_name, validate_text_input
from src.user_logger import UserLogger

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
            # Log bot response
            current_state = self.user_db.get_user_state(phone_number) if self.user_db.user_exists(phone_number) else None
            self.user_logger.log_bot_response(phone_number, response_msg, current_state, buttons)
            return response_msg, buttons
        
        # Get user's current state
        if not self.user_db.user_exists(phone_number):
            self.user_db.create_user(phone_number)
        
        current_state_id = self.user_db.get_user_state(phone_number)
        
        # If registered user sending message after idle or registration_complete, show menu
        # Also check if user has completed profile (has user_type) even if not marked as registered
        if current_state_id in ['idle', 'registration_complete']:
            profile = self.user_db.get_user(phone_number).get('profile', {})
            is_registered = self.user_db.is_registered(phone_number)
            has_user_type = profile.get('user_type') is not None
            
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
            # Set last_state to the new state (message was already shown in response)
            self.user_db.set_user_state(phone_number, next_state, {'last_state': next_state})
            
            # If next state has automatic message, append it (but ONLY if not already in response)
            next_state_def = self.flow['states'].get(next_state)
            if next_state_def and not next_state_def.get('expected_input'):
                # Automatic state (no input needed), process it immediately
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
        
        # Log bot response with the correct state (after all transitions)
        self.user_logger.log_bot_response(phone_number, response, log_state, buttons)
        
        return response, buttons
    
    def _process_state(self, phone_number: str, state: Dict[str, Any], user_input: str):
        """Process current state with user input
        
        Returns tuple of (message, next_state) or (message, next_state, buttons)
        """
        
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
        
        # If this is the first time in this state (no previous input), send the message
        context = self.user_db.get_user_context(phone_number)
        is_first_time = context.get('last_state') != state['id']
        
        if is_first_time:
            message = self._get_state_message(phone_number, state)
            buttons = self._build_buttons(state)
            self.user_db.set_user_state(phone_number, state['id'], {'last_state': state['id']})
            
            # Perform action if specified on first entry to state (for states without input)
            if state.get('action') and not state.get('expected_input'):
                self._perform_action(phone_number, state['action'], {})
            
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
                        return message, None, buttons
            
            # Return with buttons even for first time
            return message, None, buttons  # Don't advance yet, wait for user input
        
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
        
        options = state.get('options', {})
        
        if user_input in options:
            choice = options[user_input]
            
            # Check if action is restart_user
            if choice.get('action') == 'restart_user':
                return self._handle_restart(phone_number)
            
            # Save to profile if needed
            if state.get('save_to'):
                self.user_db.save_to_profile(phone_number, state['save_to'], choice['value'])
            
            # Perform action if specified
            if choice.get('action'):
                self._perform_action(phone_number, choice['action'], choice)
            
            # Get next state
            next_state = choice.get('next_state')
            
            # Get next state message and buttons
            if next_state:
                next_state_def = self.flow['states'].get(next_state)
                message = self._get_state_message(phone_number, next_state_def)
                buttons = self._build_buttons(next_state_def)
            else:
                message = "תודה!"
                buttons = None
            
            return message, next_state, buttons
        else:
            # Invalid choice - provide clearer error message
            options_list = list(state.get('options', {}).keys())
            if options_list:
                error_msg = f"בחירה לא חוקית. אנא בחר אחת מהאפשרויות: {', '.join(options_list)}"
            else:
                error_msg = "בחירה לא חוקית. אנא בחר מהאפשרויות המוצגות."
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
                # Add helpful context about what input is expected
                if state.get('expected_input') == 'text':
                    # Get state message to provide context
                    state_message = self._get_state_message(phone_number, state)
                    if state_message:
                        # Extract key instruction from message (first line or key phrase)
                        error_msg = f"{error_msg}\n\n💡 {state_message.split('?')[0] if '?' in state_message else state_message[:50]}..."
            return error_msg, None
        
        # If validation passed, use normalized value
        final_value = validation_result.get('normalized_value', user_input)
        
        # Save input to profile
        if state.get('save_to'):
            self.user_db.save_to_profile(phone_number, state['save_to'], final_value)
            logger.info(f"Saved {state['save_to']} = '{final_value}' for {phone_number}")
        
        # Perform action if specified
        if state.get('action'):
            self._perform_action(phone_number, state['action'], {'input': final_value})
        
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
            # Generic text validation for datetime and other text fields
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
        profile = self.user_db.get_user(phone_number).get('profile', {})
        user = self.user_db.get_user(phone_number)
        routines = user.get('routines', []) if user else []
        
        summary_parts = []
        
        # Name
        full_name = profile.get('full_name') or profile.get('whatsapp_name') or 'חבר/ה'
        summary_parts.append(f"👤 שם: {full_name}")
        
        # Home settlement
        home_settlement = profile.get('home_settlement', 'גברעם')
        summary_parts.append(f"🏠 ישוב בית: {home_settlement}")
        
        # User type
        user_type = profile.get('user_type', '')
        user_type_names = {
            'hitchhiker': '🚶 טרמפיסט',
            'driver': '🚗 נהג',
            'both': '🚗🚶 גיבור על'
        }
        if user_type:
            summary_parts.append(f"🎭 סוג משתמש: {user_type_names.get(user_type, user_type)}")
        
        # Default destination
        default_dest = profile.get('default_destination')
        if default_dest:
            summary_parts.append(f"⭐ יעד מועדף: {default_dest}")
        
        # Routines
        routine_dest = profile.get('routine_destination')
        routine_days = profile.get('routine_days')
        routine_departure = profile.get('routine_departure_time')
        routine_return = profile.get('routine_return_time')
        
        if routine_dest:
            routine_info = f"🔄 שגרת נסיעות: {routine_dest}"
            if routine_days:
                routine_info += f" ({routine_days})"
            if routine_departure:
                routine_info += f" - יוצא ב-{routine_departure}"
            if routine_return:
                routine_info += f", חוזר ב-{routine_return}"
            summary_parts.append(routine_info)
        
        # Alert preferences
        alert_pref = profile.get('alert_preference') or profile.get('alert_frequency')
        if alert_pref:
            alert_names = {
                'all': '🔔 על כל בקשה',
                'my_destinations': '🎯 רק היעדים שלי',
                'my_destinations_and_times': '🎯⏰ יעדים + שעות',
                'specific_area_any_time': '📍 איזור שלי',
                'specific_area_and_time': '📍⏰ איזור + שעות',
                'none': '🔕 בלי התראות'
            }
            alert_display = alert_names.get(alert_pref, alert_pref)
            summary_parts.append(f"📲 העדפות התראות: {alert_display}")
        
        return "\n".join(summary_parts) if summary_parts else ""
    
    def _get_state_message(self, phone_number: str, state: Dict[str, Any]) -> str:
        """Get message for state with variable substitution"""
        if not state:
            return ""
        
        message = state.get('message', '')
        
        # Substitute variables from user profile
        profile = self.user_db.get_user(phone_number).get('profile', {})
        
        # Find all {variable} patterns
        variables = re.findall(r'\{(\w+)\}', message)
        for var in variables:
            # Special handling for name variables - use WhatsApp name as fallback
            if var in ['full_name', 'name']:
                value = profile.get('full_name') or profile.get('whatsapp_name') or 'חבר/ה'
            elif var == 'user_summary':
                # Special variable for user summary
                value = self._get_user_summary(phone_number)
            else:
                value = profile.get(var, f'[{var}]')
            message = message.replace(f'{{{var}}}', str(value))
        
        return message
    
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
    
    def _perform_action(self, phone_number: str, action: str, data: Dict[str, Any]):
        """Perform specified action"""
        if action == 'complete_registration':
            self.user_db.complete_registration(phone_number)
            logger.info(f"User {phone_number} completed registration")
        
        elif action == 'set_gevaram_as_home':
            # Automatically set Gevaram as home settlement for all users
            self.user_db.save_to_profile(phone_number, 'home_settlement', 'גברעם')
            logger.info(f"Set home_settlement to 'גברעם' for {phone_number}")
        
        elif action == 'restart_user':
            # This will trigger a restart via the restart handler
            pass
        
        elif action == 'save_ride_request':
            profile = self.user_db.get_user(phone_number).get('profile', {})
            request_data = {
                'destination': profile.get('destination'),
                'time_range': profile.get('time_range'),
                'specific_datetime': profile.get('specific_datetime')
            }
            self.user_db.add_ride_request(phone_number, request_data)
            logger.info(f"Saved ride request for {phone_number}")
        
        elif action == 'save_driver_ride_offer':
            # Save driver ride offer with timing
            profile = self.user_db.get_user(phone_number).get('profile', {})
            offer_data = {
                'type': 'driver_ride_offer',
                'departure_timing': profile.get('departure_timing'),
                'destination': profile.get('driver_destination'),
                'origin': 'גברעם'
            }
            self.user_db.add_ride_request(phone_number, offer_data)
            logger.info(f"Saved driver ride offer for {phone_number}: {offer_data}")
        
        elif action == 'save_hitchhiker_ride_request':
            # Save hitchhiker ride request with timing
            profile = self.user_db.get_user(phone_number).get('profile', {})
            request_data = {
                'type': 'hitchhiker_ride_request',
                'ride_timing': profile.get('ride_timing'),
                'destination': profile.get('hitchhiker_destination'),
                'origin': 'גברעם'
            }
            self.user_db.add_ride_request(phone_number, request_data)
            logger.info(f"Saved hitchhiker ride request for {phone_number}: {request_data}")
        
        elif action == 'save_planned_trip':
            self.user_db.add_ride_request(phone_number, data)
            logger.info(f"Saved planned trip for {phone_number}")
        
        elif action == 'save_ride_offer':
            # Save the ride offer details
            profile = self.user_db.get_user(phone_number).get('profile', {})
            offer_data = {
                'type': 'ride_offer',
                'details': profile.get('ride_offer_details', data.get('input', ''))
            }
            self.user_db.add_ride_request(phone_number, offer_data)
            logger.info(f"Saved ride offer for {phone_number}")
        
        elif action == 'use_default_destination':
            default_dest = self.user_db.get_profile_value(phone_number, 'default_destination')
            self.user_db.save_to_profile(phone_number, 'destination', default_dest)
        
        elif action == 'return_to_idle':
            pass  # Just stay in idle
    
    def _format_options(self, options: Dict[str, Any]) -> str:
        """Format options for display"""
        formatted = []
        for key, option in options.items():
            formatted.append(f"{key}. {option['label']}")
        return '\n'.join(formatted)
    
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
                # Simple back functionality - reset to previous state if possible
                user = self.user_db.get_user(phone_number)
                if user and user.get('state', {}).get('history'):
                    history = user['state']['history']
                    if len(history) > 1:
                        # Get second-to-last state
                        previous_state = history[-2]['state']
                        self.user_db.set_user_state(phone_number, previous_state)
                        prev_state_def = self.flow['states'].get(previous_state)
                        if prev_state_def:
                            message = self._get_state_message(phone_number, prev_state_def)
                            buttons = self._build_buttons(prev_state_def)
                            return (message, buttons)
                return ("אין לאן לחזור. אתה בתחילת התהליך.", None)
            
            elif command == 'restart':
                # Use the centralized restart handler which logs the event
                message, next_state, buttons = self._handle_restart(phone_number)
                return (message, buttons)
            
            elif command == 'delete_data':
                self.user_db.delete_user_data(phone_number)
                return ("כל המידע שלך נמחק. שלח הודעה כדי להתחיל מחדש.", None)
            
            elif command == 'show_help':
                return ("פקודות זמינות:\n- חזור: חזרה שלב אחורה\n- חדש: התחלה מחדש\n- מחק: מחיקת כל המידע\n- תפריט: חזרה לתפריט הראשי", None)
            
            elif command == 'show_menu':
                if self.user_db.is_registered(phone_number):
                    self.user_db.set_user_state(phone_number, 'registered_user_menu')
                    menu_state = self.flow['states']['registered_user_menu']
                    message = self._get_state_message(phone_number, menu_state)
                    buttons = self._build_buttons(menu_state)
                    return (message, buttons)
                else:
                    return ("אתה עדיין לא רשום. הקש 'חדש' כדי להירשם.", None)
        
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

