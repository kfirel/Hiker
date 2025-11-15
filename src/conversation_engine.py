"""
Conversation flow engine that processes the conversation flow JSON
"""

import json
import logging
import re
import os
from typing import Dict, Any, Tuple, Optional
from src.validation import validate_settlement, validate_days, validate_time, validate_time_range
from src.user_logger import UserLogger

logger = logging.getLogger(__name__)

class ConversationEngine:
    """Engine to process conversation flow"""
    
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
        
        # If registered user sending message after idle, show menu
        if current_state_id == 'idle' and self.user_db.is_registered(phone_number):
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
            
            # If next state has automatic message, append it
            next_state_def = self.flow['states'].get(next_state)
            if next_state_def and not next_state_def.get('expected_input'):
                # Automatic state (no input needed), process it immediately
                next_message = self._get_state_message(phone_number, next_state_def)
                if next_message:
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
            
            # If state has no message and no input expected, auto-advance
            if not message and not state.get('expected_input'):
                next_state = self._get_next_state(phone_number, state, None)
                if next_state:
                    next_state_def = self.flow['states'].get(next_state)
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
            # No input expected, just move to next state
            next_state = self._get_next_state(phone_number, state, user_input)
            message = self._get_state_message(phone_number, state)
            buttons = self._build_buttons(self.flow['states'].get(next_state)) if next_state else None
            return message, next_state, buttons
    
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
            # Invalid choice
            error_msg = f"בחירה לא חוקית. אנא בחר מהאפשרויות."
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
                error_msg = f"הישוב \"{user_input}\" לא נמצא במערכת. 🤔\n\n💡 התכוונת ל:\n"
                # Note: suggestions will be shown as buttons, not text
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
        # States that need settlement validation
        settlement_states = ['ask_settlement', 'ask_destination', 'ask_routine_destination', 
                           'ask_default_destination_name']
        
        # States that need days validation
        days_states = ['ask_routine_days']
        
        # States that need time validation
        time_states = ['ask_routine_departure_time', 'ask_routine_return_time']
        
        # States that need time range validation
        time_range_states = ['ask_time_range']
        
        if state_id in settlement_states:
            is_valid, exact_match, suggestions = validate_settlement(user_input)
            if is_valid:
                return {
                    'is_valid': True,
                    'normalized_value': exact_match,
                    'error_message': None,
                    'suggestions': None
                }
            else:
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
        
        elif state_id in days_states:
            is_valid, normalized, error_msg = validate_days(user_input)
            return {
                'is_valid': is_valid,
                'normalized_value': normalized,
                'error_message': error_msg,
                'suggestions': None
            }
        
        elif state_id in time_states:
            is_valid, normalized, error_msg = validate_time(user_input)
            return {
                'is_valid': is_valid,
                'normalized_value': normalized,
                'error_message': error_msg,
                'suggestions': None
            }
        
        elif state_id in time_range_states:
            is_valid, normalized, error_msg = validate_time_range(user_input)
            return {
                'is_valid': is_valid,
                'normalized_value': normalized,
                'error_message': error_msg,
                'suggestions': None
            }
        
        # Default: no validation needed
        return {
            'is_valid': True,
            'normalized_value': user_input,
            'error_message': None,
            'suggestions': None
        }
    
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
        
        elif action == 'save_ride_request':
            profile = self.user_db.get_user(phone_number).get('profile', {})
            request_data = {
                'destination': profile.get('destination'),
                'time_range': profile.get('time_range'),
                'specific_datetime': profile.get('specific_datetime')
            }
            self.user_db.add_ride_request(phone_number, request_data)
            logger.info(f"Saved ride request for {phone_number}")
        
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
        
        # Note: We keep the logs (don't delete) so we have history
        # If you want to delete logs on restart, uncomment the next line:
        # self.user_logger.clear_user_logs(phone_number)
        
        # Create fresh user (this ensures user exists in database)
        self.user_db.create_user(phone_number)
        
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
                return ("חזרה אחורה (לא מוטמע עדיין)", None)
            
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
        for option_id, option_data in options.items():
            buttons.append({
                'id': option_id,
                'title': option_data.get('label', f'אפשרות {option_id}')
            })
        
        # Add restart button
        # If we have 3 or fewer buttons, it will become a list (supports up to 10)
        # If we already have many buttons, add restart as last option
        if len(buttons) < 10:
            buttons.append({
                'id': 'restart_button',
                'title': '🔄 התחל מחדש',
                'description': 'חזור להתחלה' if len(buttons) >= 3 else None
            })
        
        return buttons if buttons else None

