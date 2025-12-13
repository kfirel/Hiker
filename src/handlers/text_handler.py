"""
Text Input Handler - Handles text input processing
"""

import logging
from typing import Dict, Any, Tuple, Optional

logger = logging.getLogger(__name__)


class TextHandler:
    """Handles text input processing"""
    
    def __init__(self, conversation_engine):
        """
        Initialize text handler
        
        Args:
            conversation_engine: Reference to ConversationEngine instance
        """
        self.engine = conversation_engine
        self.user_db = conversation_engine.user_db
    
    def handle(self, phone_number: str, state: Dict[str, Any], user_input: str) -> Tuple[str, Optional[str], Optional[list]]:
        """
        Handle text input with validation
        
        Returns tuple of (message, next_state, buttons)
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
                restart_msg, restart_state, _ = self.engine._handle_restart(phone_number)
                return restart_msg, restart_state, None
            
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
                        next_state_def = self.engine.flow['states'].get(next_state)
                        if next_state_def and not next_state_def.get('message') and not next_state_def.get('expected_input'):
                            auto_next_state = self.engine._get_next_state(phone_number, next_state_def, None)
                            if auto_next_state:
                                next_state_def = self.engine.flow['states'].get(auto_next_state)
                                next_state = auto_next_state
                        message = self.engine._get_state_message(phone_number, next_state_def) if next_state_def else "תודה!"
                        buttons = self.engine._build_buttons(next_state_def) if next_state_def else None
                        return message, next_state, buttons
            # Clear suggestions if user typed something else (new input)
            self.user_db.update_context(phone_number, 'pending_suggestions', None)
        
        # Validation based on state
        validation_result = self.engine._validate_input(state_id, user_input)
        
        if not validation_result['is_valid']:
            # Return error message with suggestions if available
            error_msg = validation_result['error_message']
            if validation_result.get('suggestions'):
                suggestions = validation_result['suggestions']
                # Save suggestions to context for interactive buttons
                self.user_db.update_context(phone_number, 'pending_suggestions', suggestions)
                # Only use "הישוב" message for settlement states, use original error message otherwise
                if state_id in self.engine.SETTLEMENT_STATES:
                    error_msg = f"הישוב \"{user_input}\" לא נמצא במערכת. 🤔\n\n💡 התכוונת ל:\n"
                # Note: suggestions will be shown as buttons, not text
            else:
                # Enhanced error messages with examples and context
                error_msg = self.engine.message_formatter.get_enhanced_error_message(state_id, state, user_input, error_msg)
            
            buttons = self.engine._build_buttons(state)
            return error_msg, None, buttons
        
        # If validation passed, use normalized value
        final_value = validation_result.get('normalized_value', user_input)
        
        # Save input to profile
        if state.get('save_to'):
            self.user_db.save_to_profile(phone_number, state['save_to'], final_value)
            logger.info(f"Saved {state['save_to']} = '{final_value}' for {phone_number}")
        
        # Perform action if specified (but only if not already executed in next_state)
        # Skip action here if next_state has the same action - it will be executed there
        next_state = state.get('next_state')
        next_state_def = self.engine.flow['states'].get(next_state) if next_state else None
        
        if state.get('action'):
            # Only execute if next_state doesn't have the same action
            if not (next_state_def and next_state_def.get('action') == state.get('action')):
                self.engine.action_executor.execute(phone_number, state['action'], {'input': final_value})
            else:
                logger.debug(f"Skipping action '{state.get('action')}' - will be executed in next_state '{next_state}'")
        
        # Special handling: If registered user is updating name, return to show_my_info
        if state_id == 'ask_full_name' and self.user_db.is_registered(phone_number):
            # User is updating name, not registering - return to show_my_info
            next_state = 'show_my_info'
            next_state_def = self.engine.flow['states'].get(next_state)
            if next_state_def:
                message = self.engine._get_state_message(phone_number, next_state_def)
                buttons = self.engine._build_buttons(next_state_def)
                return message, next_state, buttons
        
        # Get next state
        next_state = state.get('next_state')
        
        if not next_state:
            return "תודה! הפרטים נשמרו.", None, None
        
        # Get next state definition
        next_state_def = self.engine.flow['states'].get(next_state)
        if not next_state_def:
            return "תודה! הפרטים נשמרו.", None
        
        # Check if next state is a routing state (no message, no input)
        if not next_state_def.get('message') and not next_state_def.get('expected_input'):
            # Auto-advance through routing state
            auto_next_state = self.engine._get_next_state(phone_number, next_state_def, None)
            if auto_next_state:
                next_state_def = self.engine.flow['states'].get(auto_next_state)
                next_state = auto_next_state
        
        # Get next state message
        message = self.engine._get_state_message(phone_number, next_state_def)
        
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
            next_state_def = self.engine.flow['states'].get(next_state)
            if next_state_def:
                buttons = self.engine._build_buttons(next_state_def)
        
        return message, next_state, buttons









