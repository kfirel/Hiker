"""
State Helper - Helper functions for state management
"""

import logging
from typing import Dict, Any, Tuple

logger = logging.getLogger(__name__)


class StateHelper:
    """Helper functions for state management"""
    
    @staticmethod
    def determine_is_first_time(
        user_db,
        phone_number: str,
        state: Dict[str, Any],
        user_input: str
    ) -> Tuple[bool, bool]:
        """
        Determine if this is the first time entering a state
        
        Args:
            user_db: UserDatabase instance
            phone_number: User's phone number
            state: Current state definition
            user_input: User input (may be empty)
            
        Returns:
            Tuple of (is_first_time, has_user_input)
        """
        current_state_id = user_db.get_user_state(phone_number)
        context = user_db.get_user_context(phone_number)
        state_id = state.get('id')
        
        # Check if user has sent input
        has_user_input = bool(user_input and user_input.strip() and state.get('expected_input'))
        
        # It's first time ONLY if current state doesn't match the state we're processing
        # If current state matches, user is already in this state and input should be processed
        is_first_time = current_state_id != state_id
        
        # IMPORTANT: If user already sent input, process it immediately instead of showing first-time message
        # This handles the case where state was just updated and user sent input in the same call
        # This is especially important for rapid state transitions in tests
        if has_user_input:
            is_first_time = False
        
        # Special case: if current state matches but last_state doesn't, it means state was updated
        # but context wasn't - still treat as first time to show the message
        # BUT only if user didn't send input (if they did, we already set is_first_time = False above)
        if current_state_id == state_id and context.get('last_state') != state_id and is_first_time:
            # State matches but context doesn't - update context
            user_db.set_user_state(phone_number, state_id, {'last_state': state_id}, add_to_history=False)
            # Only set to first time if user didn't send input
            if not has_user_input:
                is_first_time = True
        
        return is_first_time, has_user_input
    
    @staticmethod
    def handle_first_time_entry(
        engine,
        phone_number: str,
        state: Dict[str, Any],
        user_input: str
    ) -> Tuple[str, str, list]:
        """
        Handle first-time entry to a state
        
        Args:
            engine: ConversationEngine instance
            phone_number: User's phone number
            state: Current state definition
            user_input: User input (may be empty)
            
        Returns:
            Tuple of (message, next_state, buttons)
        """
        state_id = state.get('id')
        
        # Check if user_input looks like actual input (not empty, not just whitespace)
        # If it does, and we're in a state that expects input, process it instead of showing message
        if state.get('expected_input') and user_input and user_input.strip():
            # User already sent input - process it instead of showing first-time message
            # This will be handled by the caller
            return None, None, None
        
        # First time and no input yet - show message
        message = engine._get_state_message(phone_number, state)
        buttons = engine._build_buttons(state)
        engine.user_db.set_user_state(phone_number, state_id, {'last_state': state_id})
        
        # Perform action if specified on first entry to state (for states without input)
        if state.get('action') and not state.get('expected_input'):
            engine.action_executor.execute(phone_number, state['action'], {})
        
        # If state has no message and no input expected, auto-advance through routing states
        if not message and not state.get('expected_input'):
            next_state = engine._get_next_state(phone_number, state, None)
            if next_state:
                next_state_def = engine.flow['states'].get(next_state)
                if next_state_def:
                    # Continue traversing routing states recursively
                    if not next_state_def.get('message') and not next_state_def.get('expected_input'):
                        return engine._process_state(phone_number, next_state_def, user_input)
                    message = engine._get_state_message(phone_number, next_state_def)
                    buttons = engine._build_buttons(next_state_def)
                    engine.user_db.set_user_state(phone_number, next_state, {'last_state': next_state})
                    return message, next_state, buttons
        
        # Return with buttons even for first time
        # If state has expected_input, don't advance yet - wait for user input
        # But if state has no expected_input, we should advance to next_state
        if not state.get('expected_input'):
            next_state = engine._get_next_state(phone_number, state, None)
            if next_state:
                return message, next_state, buttons
        
        return message, None, buttons  # Don't advance yet, wait for user input










