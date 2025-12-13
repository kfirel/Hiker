"""
Preference Helper - Helper functions for user preferences
"""

import logging
import re
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class PreferenceHelper:
    """Helper for user preferences"""
    
    @staticmethod
    def get_share_name_preference(user: Dict[str, Any]) -> str:
        """
        Get share name preference with fallback
        
        Checks both root level and profile dict for backward compatibility
        
        Args:
            user: User document from database
            
        Returns:
            Preference value: 'always', 'ask', 'never', or 'ask' as default
        """
        if not user:
            return 'ask'
        
        # Check root level first (MongoDB stores directly)
        preference = user.get('share_name_with_hitchhiker')
        
        # Check profile dict (as returned by get_user)
        if not preference:
            profile = user.get('profile', {})
            preference = profile.get('share_name_with_hitchhiker')
        
        # Default to 'ask' if not found
        return preference or 'ask'
    
    @staticmethod
    def get_user_name(user: Dict[str, Any]) -> str:
        """
        Get user name with fallback
        
        Args:
            user: User document from database
            
        Returns:
            User name or default
        """
        if not user:
            return 'חבר/ה'
        
        # Try full_name first
        name = user.get('full_name')
        if name:
            return name
        
        # Fallback to whatsapp_name
        name = user.get('whatsapp_name')
        if name:
            return name
        
        # Check profile dict
        profile = user.get('profile', {})
        name = profile.get('full_name') or profile.get('whatsapp_name')
        if name:
            return name
        
        # Last resort: try to extract name from whatsapp_name if it contains "נהג" or "טרמפיסט"
        whatsapp_name = user.get('whatsapp_name') or profile.get('whatsapp_name')
        if whatsapp_name:
            # Remove common suffixes like "נהג", "טרמפיסט", "נהגת", "טרמפיסטית"
            cleaned_name = re.sub(r'\s*(נהג|טרמפיסט|נהגת|טרמפיסטית)\s*$', '', whatsapp_name, flags=re.IGNORECASE)
            if cleaned_name and cleaned_name != whatsapp_name:
                return cleaned_name
        
        return 'חבר/ה'
    
    @staticmethod
    def get_hitchhiker_name(hitchhiker: Optional[Dict[str, Any]]) -> str:
        """
        Get hitchhiker name with fallback
        
        Args:
            hitchhiker: Hitchhiker user document
            
        Returns:
            Hitchhiker name or default
        """
        if not hitchhiker:
            return 'טרמפיסט'
        
        return PreferenceHelper.get_user_name(hitchhiker) or 'טרמפיסט'
    
    @staticmethod
    def get_driver_name(driver: Optional[Dict[str, Any]]) -> str:
        """
        Get driver name with fallback
        
        Args:
            driver: Driver user document
            
        Returns:
            Driver name or default
        """
        if not driver:
            return 'נהג'
        
        return PreferenceHelper.get_user_name(driver) or 'נהג'









