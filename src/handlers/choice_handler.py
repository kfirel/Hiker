"""
Choice Input Handler - Handles choice-based input processing
"""

import logging
from typing import Dict, Any, Tuple, Optional

logger = logging.getLogger(__name__)


class ChoiceHandler:
    """Handles choice-based input processing"""
    
    def __init__(self, conversation_engine):
        """
        Initialize choice handler
        
        Args:
            conversation_engine: Reference to ConversationEngine instance
        """
        self.engine = conversation_engine
        self.user_db = conversation_engine.user_db
    
    def handle(self, phone_number: str, state: Dict[str, Any], user_input: str) -> Tuple[str, Optional[str], Optional[list]]:
        """
        Handle choice-based input
        
        Returns:
            Tuple of (message, next_state, buttons)
        """
        # Check if user clicked restart button
        if user_input == 'restart_button':
            return self.engine._handle_restart(phone_number)
        
        # Handle confirm_restart state specially
        if state.get('id') == 'confirm_restart':
            options = state.get('options', {})
            if user_input in options:
                choice = options[user_input]
                if choice.get('value') == 'yes' and choice.get('action') == 'restart_user':
                    # User confirmed restart - perform it
                    return self.engine._handle_restart(phone_number)
                elif choice.get('value') == 'no':
                    # User cancelled - go back to menu
                    next_state = choice.get('next_state', 'registered_user_menu')
                    next_state_def = self.engine.flow['states'].get(next_state)
                    if next_state_def:
                        message = self.engine._get_state_message(phone_number, next_state_def)
                        buttons = self.engine._build_buttons(next_state_def)
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
                    confirm_state = self.engine.flow['states'].get('confirm_restart')
                    if confirm_state:
                        message = self.engine._get_state_message(phone_number, confirm_state)
                        buttons = self.engine._build_buttons(confirm_state)
                        return message, 'confirm_restart', buttons
                # Not registered or already confirmed - restart immediately
                return self.engine._handle_restart(phone_number)
            
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
                    help_msg, help_buttons = self.engine.command_handler.handle_show_help(phone_number)
                    return help_msg, None, help_buttons
                self.engine.action_executor.execute(phone_number, choice['action'], choice)
            
            # Get next state
            next_state = choice.get('next_state')
            
            # Check if choice has a custom message (response message for this choice)
            choice_message = choice.get('message')
            
            # Get next state message and buttons
            if next_state:
                next_state_def = self.engine.flow['states'].get(next_state)
                next_state_message = self.engine._get_state_message(phone_number, next_state_def)
                buttons = self.engine._build_buttons(next_state_def)
                
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
                            final_next = self.engine._get_next_state(phone_number, final_state, None)
                            if final_next:
                                final_state = self.engine.flow['states'].get(final_next)
                                if final_state:
                                    next_state = final_next
                                    next_state_def = final_state
                                    next_state_message = self.engine._get_state_message(phone_number, final_state)
                                    buttons = self.engine._build_buttons(final_state)
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
            return self._build_invalid_choice_error(state, user_input)
    
    def _build_invalid_choice_error(self, state: Dict[str, Any], user_input: str) -> Tuple[str, Optional[str], Optional[list]]:
        """Build error message for invalid choice"""
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
        
        buttons = self.engine._build_buttons(state)
        return error_msg, None, buttons









