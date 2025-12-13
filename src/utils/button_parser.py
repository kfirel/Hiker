"""
Button Parser - Parses button IDs to extract action and data
"""

import logging
from typing import Tuple, Optional

logger = logging.getLogger(__name__)


class ButtonParser:
    """Parses button IDs to extract action and data"""
    
    # Supported button formats
    APPROVE_PREFIXES = ['approve_', '1_']
    REJECT_PREFIXES = ['reject_', '2_']
    
    def __init__(self):
        """Initialize button parser"""
        pass
    
    def parse_match_response(self, button_id: str) -> Tuple[Optional[str], Optional[bool]]:
        """
        Parse match response button ID
        
        Supports multiple formats:
        - Old: "approve_MATCH_xxx" or "reject_MATCH_xxx"
        - New: "1_MATCH_xxx" or "2_MATCH_xxx"
        - Simple: "1" or "2" (match_id will be None, needs to be found from DB)
        
        Args:
            button_id: Button ID string
            
        Returns:
            Tuple of (match_id, is_approval) or (None, None) if invalid
        """
        button_id = button_id.strip()
        
        # Check approve formats
        for prefix in self.APPROVE_PREFIXES:
            if button_id.startswith(prefix):
                match_id = button_id.replace(prefix, '', 1)
                return match_id, True
        
        # Check reject formats
        for prefix in self.REJECT_PREFIXES:
            if button_id.startswith(prefix):
                match_id = button_id.replace(prefix, '', 1)
                return match_id, False
        
        # Check simple formats ("1" or "2")
        if button_id == '1':
            return None, True  # match_id will be found from DB
        elif button_id == '2':
            return None, False  # match_id will be found from DB
        
        logger.error(f"Invalid button ID format: {button_id}")
        return None, None
    
    def parse_name_sharing(self, button_id: str) -> Tuple[Optional[str], Optional[bool]]:
        """
        Parse name sharing response button ID
        
        Formats:
        - "share_name_yes_MATCH_xxx"
        - "share_name_no_MATCH_xxx"
        
        Args:
            button_id: Button ID string
            
        Returns:
            Tuple of (match_id, share_name) or (None, None) if invalid
        """
        button_id = button_id.strip()
        
        if button_id.startswith('share_name_yes_'):
            match_id = button_id.replace('share_name_yes_', '', 1)
            return match_id, True
        elif button_id.startswith('share_name_no_'):
            match_id = button_id.replace('share_name_no_', '', 1)
            return match_id, False
        
        logger.error(f"Invalid name sharing button ID format: {button_id}")
        return None, None
    
    def is_match_response(self, button_id: str) -> bool:
        """Check if button ID is a match response"""
        match_id, is_approval = self.parse_match_response(button_id)
        return match_id is not None or is_approval is not None
    
    def is_name_sharing(self, button_id: str) -> bool:
        """Check if button ID is a name sharing response"""
        match_id, share_name = self.parse_name_sharing(button_id)
        return match_id is not None










