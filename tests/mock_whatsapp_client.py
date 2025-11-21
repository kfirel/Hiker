"""
Mock WhatsApp Client for testing
Replaces the real WhatsApp API calls with mock implementations
"""

import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

class MockWhatsAppClient:
    """Mock WhatsApp client that simulates API calls without actually sending messages"""
    
    def __init__(self):
        self.sent_messages = []  # Store all sent messages for testing
        self.call_count = 0
    
    def send_message(self, to_phone_number: str, message_text: str, buttons: Optional[List[Dict[str, Any]]] = None) -> bool:
        """
        Mock send_message - stores the message instead of sending it
        
        Args:
            to_phone_number: Recipient's phone number
            message_text: Text message to send
            buttons: Optional list of button dicts
            
        Returns:
            bool: Always True (simulating success)
        """
        self.call_count += 1
        message_data = {
            'to': to_phone_number,
            'message': message_text,
            'buttons': buttons,
            'timestamp': None  # Will be set by caller if needed
        }
        self.sent_messages.append(message_data)
        
        logger.debug(f"Mock WhatsApp: Sent message to {to_phone_number}")
        if buttons:
            logger.debug(f"Mock WhatsApp: Message includes {len(buttons)} buttons")
        
        return True
    
    def send_button_message(self, to_phone_number: str, message_text: str, buttons: List[Dict[str, Any]]) -> bool:
        """Mock send_button_message"""
        return self.send_message(to_phone_number, message_text, buttons)
    
    def send_list_message(self, to_phone_number: str, message_text: str, list_items: List[Dict[str, Any]]) -> bool:
        """Mock send_list_message"""
        return self.send_message(to_phone_number, message_text, list_items)
    
    def _send_text_message(self, to_phone_number: str, message_text: str) -> bool:
        """Mock _send_text_message"""
        return self.send_message(to_phone_number, message_text, None)
    
    def get_sent_messages(self) -> List[Dict[str, Any]]:
        """Get all sent messages"""
        return self.sent_messages
    
    def clear_messages(self):
        """Clear all stored messages"""
        self.sent_messages = []
        self.call_count = 0
    
    def get_message_count(self) -> int:
        """Get count of sent messages"""
        return len(self.sent_messages)

