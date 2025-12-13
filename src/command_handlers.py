"""
Command handlers module for conversation commands
Handles special commands like 'back', 'restart', 'help', etc.
"""

import logging
from typing import Dict, Any, Tuple, Optional

logger = logging.getLogger(__name__)


class CommandHandler:
    """Handles special conversation commands"""
    
    def __init__(self, conversation_engine):
        """Initialize command handler
        
        Args:
            conversation_engine: Reference to ConversationEngine instance
        """
        self.engine = conversation_engine
        self.user_db = conversation_engine.user_db
        self.flow = conversation_engine.flow
    
    def handle_go_back(self, phone_number: str) -> Tuple[str, Optional[list]]:
        """Handle 'go_back' command - return to previous state
        
        Args:
            phone_number: User's phone number
            
        Returns:
            Tuple of (message, buttons)
        """
        user = self.user_db.get_user(phone_number)
        if not user:
            return ("אין היסטוריה. אתה בתחילת התהליך.", None)
        
        history = user.get('state', {}).get('history', [])
        
        # Need at least 2 states to go back (current + previous)
        if len(history) < 2:
            return ("אין לאן לחזור. אתה בתחילת התהליך.", None)
        
        # Get previous state (second-to-last)
        previous_state_entry = history[-2]
        previous_state_id = previous_state_entry['state']
        
        # Remove current state from history and restore previous
        history.pop()  # Remove current state
        self.user_db.set_user_state(phone_number, previous_state_id, previous_state_entry.get('context', {}))
        
        # Get previous state definition and return its message
        prev_state_def = self.flow['states'].get(previous_state_id)
        if prev_state_def:
            message = self.engine._get_state_message(phone_number, prev_state_def)
            buttons = self.engine._build_buttons(prev_state_def)
            return (message, buttons)
        
        return ("חזרתי לשלב הקודם.", None)
    
    def handle_restart(self, phone_number: str, require_confirmation: bool = True) -> Tuple[str, Optional[list]]:
        """Handle 'restart' command - restart conversation
        
        Args:
            phone_number: User's phone number
            require_confirmation: Whether to require confirmation before restart
            
        Returns:
            Tuple of (message, buttons)
        """
        # Check if user is registered - if so, require confirmation
        if require_confirmation and self.user_db.is_registered(phone_number):
            # Move to confirmation state
            self.user_db.set_user_state(phone_number, 'confirm_restart')
            message = (
                "⚠️ אתה בטוח שאתה רוצה להתחיל מחדש?\n\n"
                "זה ימחק את כל המידע שלך! 😱\n\n"
                "1. ✅ כן, אני בטוח\n"
                "2. ❌ לא, אני רוצה לחזור"
            )
            buttons = [
                {'id': '1', 'title': '✅ כן, אני בטוח'},
                {'id': '2', 'title': '❌ לא, חזור'}
            ]
            return (message, buttons)
        
        # Not registered or confirmation not required - restart immediately
        return self._perform_restart(phone_number)
    
    def _perform_restart(self, phone_number: str) -> Tuple[str, Optional[list]]:
        """Actually perform the restart
        
        Args:
            phone_number: User's phone number
            
        Returns:
            Tuple of (message, buttons)
        """
        # Use the engine's restart handler
        message, next_state, buttons = self.engine._handle_restart(phone_number)
        return (message, buttons)
    
    def handle_show_help(self, phone_number: str) -> Tuple[str, Optional[list]]:
        """Handle 'show_help' command - show help menu
        
        Args:
            phone_number: User's phone number
            
        Returns:
            Tuple of (message, buttons)
        """
        # Get contextual help based on current state
        current_state_id = self.user_db.get_user_state(phone_number)
        current_state = self.flow['states'].get(current_state_id)
        
        # Base help message
        help_message = "📖 עזרה - פקודות זמינות:\n\n"
        help_message += "• חזור / אחורה - חזרה שלב אחורה ⬅️\n"
        help_message += "• חדש - התחלה מחדש 🔄\n"
        help_message += "• תפריט - חזרה לתפריט הראשי 📋\n"
        help_message += "• עזרה - הצגת העזרה הזו ❓\n\n"
        
        # Add contextual help if in a specific state
        if current_state:
            contextual_help = self._get_contextual_help(current_state_id, current_state)
            if contextual_help:
                help_message += f"💡 עזרה לשלב הנוכחי:\n{contextual_help}\n\n"
        
        help_message += "יש עוד שאלות? פשוט כתוב! 😊"
        
        # Return to current state after help
        buttons = self.engine._build_buttons(current_state) if current_state else None
        
        return (help_message, buttons)
    
    def _get_contextual_help(self, state_id: str, state: Dict[str, Any]) -> Optional[str]:
        """Get contextual help for a specific state
        
        Args:
            state_id: State ID
            state: State definition
            
        Returns:
            Help message or None
        """
        expected_input = state.get('expected_input')
        
        if expected_input == 'choice':
            options = state.get('options', {})
            if options:
                help_text = "בחר אחת מהאפשרויות:\n"
                for opt_id, opt_data in options.items():
                    label = opt_data.get('label', f'אפשרות {opt_id}')
                    help_text += f"• {opt_id} - {label}\n"
                return help_text
        
        elif expected_input == 'text':
            if state_id in self.engine.SETTLEMENT_STATES:
                return "כתוב שם ישוב או עיר. למשל: תל אביב, ירושלים, חיפה"
            elif state_id in self.engine.TIME_STATES:
                return "כתוב שעה בפורמט: 07:00 או 7:00 או 7"
            elif state_id in self.engine.TIME_RANGE_STATES:
                return "כתוב טווח שעות: 7-9 או 08:00-10:00"
            elif state_id in self.engine.DAYS_STATES:
                return "כתוב ימים: א-ה או א,ג,ה או 'כל יום'"
            elif state_id in self.engine.NAME_STATES:
                return "כתוב את השם המלא שלך"
        
        return None
    
    def handle_show_menu(self, phone_number: str) -> Tuple[str, Optional[list]]:
        """Handle 'show_menu' command - show main menu
        
        Args:
            phone_number: User's phone number
            
        Returns:
            Tuple of (message, buttons)
        """
        if self.user_db.is_registered(phone_number):
            # Move to menu state
            self.user_db.set_user_state(phone_number, 'registered_user_menu')
            menu_state = self.flow['states'].get('registered_user_menu')
            if menu_state:
                message = self.engine._get_state_message(phone_number, menu_state)
                buttons = self.engine._build_buttons(menu_state)
                return (message, buttons)
        
        # Not registered - start registration
        return ("אתה עדיין לא רשום. בוא נתחיל! 😊", None)
    
    def handle_delete_data(self, phone_number: str) -> Tuple[str, Optional[list]]:
        """Handle 'delete_data' command - delete all user data
        
        Args:
            phone_number: User's phone number
            
        Returns:
            Tuple of (message, buttons)
        """
        self.user_db.delete_user_data(phone_number)
        return ("כל המידע שלך נמחק. שלח הודעה כדי להתחיל מחדש.", None)
    
    def handle_found_ride(self, phone_number: str) -> Tuple[str, Optional[list]]:
        """Handle 'מצאתי' command - mark ride request as found and stop notifications
        
        Args:
            phone_number: User's phone number
            
        Returns:
            Tuple of (message, buttons)
        """
        if not self.user_db._use_mongo or not self.user_db.mongo.is_connected():
            return ("❌ שגיאה: מסד הנתונים לא זמין.", None)
        
        user = self.user_db.mongo.get_collection("users").find_one({"phone_number": phone_number})
        if not user:
            return ("❌ לא נמצא משתמש.", None)
        
        # Find active ride requests for this hitchhiker
        active_requests = list(self.user_db.mongo.get_collection("ride_requests").find({
            "requester_id": user['_id'],
            "status": {"$in": ["pending", "matched"]}
        }))
        
        if not active_requests:
            return ("✅ אין לך בקשות טרמפ פעילות כרגע.", None)
        
        from datetime import datetime
        now = datetime.now()
        
        # Mark all active requests as "found" (completed)
        for request in active_requests:
            self.user_db.mongo.get_collection("ride_requests").update_one(
                {"_id": request['_id']},
                {
                    "$set": {
                        "status": "found",
                        "found_at": now
                    }
                }
            )
            
            # Also mark all pending matched drivers as "found" to stop notifications
            self.user_db.mongo.get_collection("ride_requests").update_one(
                {"_id": request['_id']},
                {
                    "$set": {
                        "matched_drivers.$[elem].status": "found",
                        "matched_drivers.$[elem].found_at": now
                    }
                },
                array_filters=[{
                    "elem.status": {"$in": ["pending_approval", "approved"]}
                }]
            )
        
        num_requests = len(active_requests)
        if num_requests == 1:
            return ("✅ מעולה! סימנתי שהמצאת טרמפ. לא אשלח לך עוד התראות על נהגים עבור הבקשה הזו. 🎉", None)
        else:
            return (f"✅ מעולה! סימנתי שהמצאת טרמפ עבור {num_requests} בקשות. לא אשלח לך עוד התראות על נהגים. 🎉", None)



