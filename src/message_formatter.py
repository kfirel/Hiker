"""
Message formatter module for conversation messages
Handles message formatting, variable substitution, and user summaries
"""

import re
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class MessageFormatter:
    """Formats messages with variable substitution and generates summaries"""
    
    # State type constants for error messages
    NAME_STATES = ['ask_full_name']
    SETTLEMENT_STATES = ['ask_destination', 'ask_routine_destination', 
                        'ask_default_destination_name', 'ask_hitchhiker_destination', 'ask_driver_destination']
    DAYS_STATES = ['ask_routine_days']
    TIME_STATES = ['ask_routine_departure_time', 'ask_routine_return_time']
    TIME_RANGE_STATES = ['ask_time_range']
    TEXT_STATES = ['ask_specific_datetime']
    
    def __init__(self, user_db):
        """Initialize message formatter
        
        Args:
            user_db: UserDatabase instance
        """
        self.user_db = user_db
    
    def format_message(self, phone_number: str, state: Dict[str, Any]) -> str:
        """Format message for state with variable substitution
        
        Args:
            phone_number: User's phone number
            state: State definition
            
        Returns:
            Formatted message string
        """
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
                value = self.get_user_summary(phone_number)
            else:
                value = profile.get(var, f'[{var}]')
            message = message.replace(f'{{{var}}}', str(value))
        
        return message
    
    def get_user_summary(self, phone_number: str) -> str:
        """Generate a summary of user information for display in messages
        
        Args:
            phone_number: User's phone number
            
        Returns:
            Formatted user summary string
        """
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
    
    def get_enhanced_error_message(self, state_id: str, state: Dict[str, Any], 
                                   user_input: str, base_error: str) -> str:
        """Get enhanced error message with examples and context
        
        Args:
            state_id: Current state ID
            state: State definition
            user_input: User's invalid input
            base_error: Base error message
            
        Returns:
            Enhanced error message with examples
        """
        enhanced_msg = base_error
        
        # Add examples based on state type
        if state_id in self.TIME_RANGE_STATES:
            enhanced_msg += "\n\n💡 דוגמאות נכונות:\n"
            enhanced_msg += "• 7-9 (פשוט שעות - הכי קל! 😊)\n"
            enhanced_msg += "• 08:00-10:00 (פורמט מלא)\n"
            enhanced_msg += "• 14:30-17:00 (עם דקות)\n"
            enhanced_msg += "\n⬅️ כתוב 'חזור' כדי לחזור לשלב הקודם"
        
        elif state_id in self.TIME_STATES:
            enhanced_msg += "\n\n💡 דוגמאות נכונות:\n"
            enhanced_msg += "• 08:00\n"
            enhanced_msg += "• 14:30\n"
            enhanced_msg += "• 7:00 (זה גם בסדר!)\n"
            enhanced_msg += "• 6 (זה גם יעבוד! יתפרש כ-06:00)\n"
            enhanced_msg += "\n⬅️ כתוב 'חזור' כדי לחזור לשלב הקודם"
        
        elif state_id in self.DAYS_STATES:
            enhanced_msg += "\n\n💡 דוגמאות נכונות:\n"
            enhanced_msg += "• א-ה (ראשון עד חמישי)\n"
            enhanced_msg += "• א,ג,ה (ימים ספציפיים)\n"
            enhanced_msg += "• כל יום\n"
            enhanced_msg += "• ראשון ושלישי\n"
            enhanced_msg += "\n⬅️ כתוב 'חזור' כדי לחזור לשלב הקודם"
        
        elif state_id in self.SETTLEMENT_STATES:
            enhanced_msg += "\n\n💡 דוגמאות:\n"
            enhanced_msg += "• תל אביב\n"
            enhanced_msg += "• ירושלים\n"
            enhanced_msg += "• חיפה\n"
            enhanced_msg += "\n⬅️ כתוב 'חזור' כדי לחזור לשלב הקודם"
        
        elif state_id in self.NAME_STATES:
            enhanced_msg += "\n\n💡 דוגמאות:\n"
            enhanced_msg += "• יוסי כהן\n"
            enhanced_msg += "• שרה לוי\n"
            enhanced_msg += "\n⬅️ כתוב 'חזור' כדי לחזור לשלב הקודם"
        
        else:
            # Generic error with back option
            enhanced_msg += "\n\n⬅️ כתוב 'חזור' כדי לחזור לשלב הקודם"
        
        return enhanced_msg


