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
        original_message = message  # Keep original for cleanup checks
        
        # Substitute variables from user profile
        user = self.user_db.get_user(phone_number)
        profile = user.get('profile', {}) if user else {}
        
        # Get raw MongoDB user if available (for fields not in converted format)
        mongo_user_raw = None
        if hasattr(self.user_db, '_use_mongo') and self.user_db._use_mongo and self.user_db.mongo:
            try:
                mongo_user_raw = self.user_db.mongo.get_collection("users").find_one({"phone_number": phone_number})
            except Exception as e:
                logger.debug(f"Could not fetch raw MongoDB user: {e}")
        
        # Get WhatsApp name value first (for cleanup later)
        whatsapp_name_value = None
        if user:
            whatsapp_name_value = profile.get('whatsapp_name') or user.get('whatsapp_name') or ''
        elif mongo_user_raw:
            whatsapp_name_value = mongo_user_raw.get('whatsapp_name') or ''
        
        # Find all {variable} patterns
        variables = re.findall(r'\{(\w+)\}', message)
        for var in variables:
            # Special handling for name variables - use WhatsApp name as fallback
            if var in ['full_name', 'name']:
                value = profile.get('full_name') or profile.get('whatsapp_name') or 'חבר/ה'
                if not value and mongo_user_raw:
                    value = mongo_user_raw.get('full_name') or mongo_user_raw.get('whatsapp_name') or 'חבר/ה'
            elif var == 'whatsapp_name':
                # Use the value we already got, fallback to full_name or generic greeting
                value = whatsapp_name_value or profile.get('full_name') or 'חבר/ה'
                if not value and mongo_user_raw:
                    value = mongo_user_raw.get('whatsapp_name') or mongo_user_raw.get('full_name') or 'חבר/ה'
            elif var == 'user_summary':
                # Special variable for user summary
                value = self.get_user_summary(phone_number)
            else:
                # Check profile first
                value = profile.get(var)
                # Then check user document root level (for JSON mode)
                if value is None and user:
                    value = user.get(var)
                # Finally check raw MongoDB user (for MongoDB-stored fields like routine_destination)
                if value is None and mongo_user_raw:
                    value = mongo_user_raw.get(var)
                if value is None:
                    value = f'[{var}]'
            message = message.replace(f'{{{var}}}', str(value))
        
        # Clean up empty WhatsApp name references in messages
        # Handle cases where {whatsapp_name} was empty - clean up spacing
        if '{whatsapp_name}' in original_message and not whatsapp_name_value:
            # Pattern: "היי{whatsapp_name}!" becomes "היי!" if whatsapp_name is empty
            # Pattern: "היי {whatsapp_name}!" becomes "היי!" if whatsapp_name is empty
            message = re.sub(r'היי\s*\{whatsapp_name\}\s*!', 'היי!', message)
            message = re.sub(r'היי\s*\{whatsapp_name\}\s*👋', 'היי 👋', message)
            message = re.sub(r'היי\s*\{whatsapp_name\}', 'היי', message)
            # Also handle cases where name appears in middle: "היי {whatsapp_name}!"
            message = re.sub(r'היי\s+!', 'היי!', message)
            message = re.sub(r'היי\s+👋', 'היי 👋', message)
        
        return message
    
    def get_user_summary(self, phone_number: str) -> str:
        """Generate a summary of user information for display in messages
        
        Args:
            phone_number: User's phone number
            
        Returns:
            Formatted user summary string
        """
        from datetime import datetime
        
        profile = self.user_db.get_user(phone_number).get('profile', {})
        user = self.user_db.get_user(phone_number)
        
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
        
        # Get routines from database
        routines = []
        if hasattr(self.user_db, 'mongo') and self.user_db.mongo and self.user_db.mongo.is_connected():
            try:
                user_doc = self.user_db.mongo.get_collection("users").find_one({"phone_number": phone_number})
                if user_doc:
                    user_id = user_doc.get('_id')
                    routines_cursor = self.user_db.mongo.get_collection("routines").find({
                        "user_id": user_id,
                        "is_active": True
                    })
                    routines = list(routines_cursor)
            except Exception as e:
                logger.warning(f"Failed to fetch routines from database: {e}")
        
        # Display routines
        if routines:
            summary_parts.append("")  # Empty line before routines
            summary_parts.append("🔄 שגרות נסיעה:")
            for idx, routine in enumerate(routines, 1):
                dest = routine.get('destination', '')
                days = routine.get('days', [])
                # Handle both array and string formats (backward compatibility)
                if isinstance(days, list):
                    days_str = ', '.join(days) if days else ''
                else:
                    days_str = str(days) if days else ''
                dep_start = routine.get('departure_time_start')
                dep_end = routine.get('departure_time_end')
                ret_start = routine.get('return_time_start')
                ret_end = routine.get('return_time_end')
                
                routine_str = f"   {idx}. {dest}"
                if days_str:
                    routine_str += f" ({days_str})"
                
                if dep_start and dep_end:
                    if isinstance(dep_start, datetime):
                        dep_start_str = dep_start.strftime('%H:%M')
                    else:
                        dep_start_str = str(dep_start)[:5] if len(str(dep_start)) >= 5 else str(dep_start)
                    if isinstance(dep_end, datetime):
                        dep_end_str = dep_end.strftime('%H:%M')
                    else:
                        dep_end_str = str(dep_end)[:5] if len(str(dep_end)) >= 5 else str(dep_end)
                    routine_str += f" - יוצא {dep_start_str}-{dep_end_str}"
                
                if ret_start and ret_end:
                    if isinstance(ret_start, datetime):
                        ret_start_str = ret_start.strftime('%H:%M')
                    else:
                        ret_start_str = str(ret_start)[:5] if len(str(ret_start)) >= 5 else str(ret_start)
                    if isinstance(ret_end, datetime):
                        ret_end_str = ret_end.strftime('%H:%M')
                    else:
                        ret_end_str = str(ret_end)[:5] if len(str(ret_end)) >= 5 else str(ret_end)
                    routine_str += f", חוזר {ret_start_str}-{ret_end_str}"
                
                summary_parts.append(routine_str)
        else:
            # Fallback to profile routines (for backward compatibility)
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
        
        # Get active ride requests (for hitchhikers)
        if user_type in ['hitchhiker', 'both']:
            active_requests = []
            if hasattr(self.user_db, 'mongo') and self.user_db.mongo and self.user_db.mongo.is_connected():
                try:
                    user_doc = self.user_db.mongo.get_collection("users").find_one({"phone_number": phone_number})
                    if user_doc:
                        user_id = user_doc.get('_id')
                        # Ride requests are stored as ride_requests with type="hitchhiker_request"
                        requests_cursor = self.user_db.mongo.get_collection("ride_requests").find({
                            "requester_id": user_id,
                            "type": "hitchhiker_request",
                            "status": {"$in": ["pending", "active"]}
                        }).sort("created_at", -1).limit(5)  # Show up to 5 recent requests
                        active_requests = list(requests_cursor)
                except Exception as e:
                    logger.warning(f"Failed to fetch ride requests from database: {e}")
            
            if active_requests:
                summary_parts.append("")  # Empty line before requests
                summary_parts.append("🚶 בקשות טרמפ פעילות:")
                for idx, request in enumerate(active_requests, 1):
                    dest = request.get('destination', '')
                    start_time = request.get('start_time_range')
                    end_time = request.get('end_time_range')
                    
                    request_str = f"   {idx}. ל-{dest}"
                    if start_time and end_time:
                        if isinstance(start_time, datetime):
                            start_str = start_time.strftime('%d/%m %H:%M')
                        else:
                            start_str = str(start_time)[:16]
                        if isinstance(end_time, datetime):
                            end_str = end_time.strftime('%d/%m %H:%M')
                        else:
                            end_str = str(end_time)[:16]
                        request_str += f" ({start_str} - {end_str})"
                    
                    summary_parts.append(request_str)
        
        # Get active ride offers (for drivers)
        if user_type in ['driver', 'both']:
            active_offers = []
            if hasattr(self.user_db, 'mongo') and self.user_db.mongo and self.user_db.mongo.is_connected():
                try:
                    user_doc = self.user_db.mongo.get_collection("users").find_one({"phone_number": phone_number})
                    if user_doc:
                        user_id = user_doc.get('_id')
                        # Ride offers are stored as ride_requests with type="driver_offer"
                        offers_cursor = self.user_db.mongo.get_collection("ride_requests").find({
                            "requester_id": user_id,
                            "type": "driver_offer",
                            "status": {"$in": ["pending", "active"]}
                        }).sort("created_at", -1).limit(5)  # Show up to 5 recent offers
                        active_offers = list(offers_cursor)
                except Exception as e:
                    logger.warning(f"Failed to fetch ride offers from database: {e}")
            
            if active_offers:
                summary_parts.append("")  # Empty line before offers
                summary_parts.append("🚗 הצעות נסיעה פעילות:")
                for idx, offer in enumerate(active_offers, 1):
                    dest = offer.get('destination', '')
                    start_time = offer.get('start_time_range')
                    end_time = offer.get('end_time_range')
                    
                    offer_str = f"   {idx}. ל-{dest}"
                    if start_time and end_time:
                        start_str = start_time.strftime('%d/%m %H:%M') if isinstance(start_time, datetime) else str(start_time)[:16]
                        end_str = end_time.strftime('%d/%m %H:%M') if isinstance(end_time, datetime) else str(end_time)[:16]
                        offer_str += f" ({start_str} - {end_str})"
                    
                    summary_parts.append(offer_str)
        
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



