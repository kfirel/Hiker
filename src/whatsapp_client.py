import requests
import logging
from src.config import Config

logger = logging.getLogger(__name__)

class WhatsAppClient:
    """Client for sending messages via WhatsApp Cloud API"""
    
    def __init__(self):
        self.phone_number_id = Config.WHATSAPP_PHONE_NUMBER_ID
        self.access_token = Config.WHATSAPP_ACCESS_TOKEN
        self.api_url = Config.WHATSAPP_API_URL
    
    def send_message(self, to_phone_number, message_text, buttons=None):
        """
        Send a text message via WhatsApp Cloud API
        
        Args:
            to_phone_number (str): Recipient's phone number (with country code, no +)
            message_text (str): Text message to send
            buttons (list): Optional list of button dicts for interactive message
            
        Returns:
            bool: True if successful, False otherwise
        """
        # If buttons provided and <= 3, use reply buttons
        if buttons and len(buttons) <= 3:
            return self.send_button_message(to_phone_number, message_text, buttons)
        # If buttons > 3, use list message
        elif buttons and len(buttons) > 3:
            return self.send_list_message(to_phone_number, message_text, buttons)
        # No buttons, send regular text
        else:
            return self._send_text_message(to_phone_number, message_text)
    
    def _send_text_message(self, to_phone_number, message_text):
        """Send a plain text message"""
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'messaging_product': 'whatsapp',
            'to': to_phone_number,
            'type': 'text',
            'text': {
                'body': message_text
            }
        }
        
        try:
            response = requests.post(self.api_url, json=payload, headers=headers)
            response.raise_for_status()
            
            logger.info(f"Text message sent successfully to {to_phone_number}")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send message to {to_phone_number}: {str(e)}")
            if hasattr(e.response, 'text'):
                logger.error(f"Response: {e.response.text}")
            return False
    
    def send_button_message(self, to_phone_number, message_text, buttons):
        """
        Send an interactive message with reply buttons (max 3 buttons)
        
        Args:
            to_phone_number (str): Recipient's phone number
            message_text (str): Message body text
            buttons (list): List of button dicts with 'id' and 'title'
                           Example: [{'id': '1', 'title': 'Option 1'}, ...]
        
        Returns:
            bool: True if successful, False otherwise
        """
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        # Build buttons array (max 3)
        button_components = []
        for btn in buttons[:3]:  # Limit to 3 buttons
            button_components.append({
                'type': 'reply',
                'reply': {
                    'id': btn['id'],
                    'title': btn['title'][:20]  # Max 20 chars for button title
                }
            })
        
        payload = {
            'messaging_product': 'whatsapp',
            'recipient_type': 'individual',
            'to': to_phone_number,
            'type': 'interactive',
            'interactive': {
                'type': 'button',
                'body': {
                    'text': message_text
                },
                'action': {
                    'buttons': button_components
                }
            }
        }
        
        try:
            response = requests.post(self.api_url, json=payload, headers=headers)
            response.raise_for_status()
            
            logger.info(f"Button message sent successfully to {to_phone_number}")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send button message to {to_phone_number}: {str(e)}")
            if hasattr(e.response, 'text'):
                logger.error(f"Response: {e.response.text}")
            return False
    
    def send_list_message(self, to_phone_number, message_text, list_items):
        """
        Send an interactive list message (for 4+ options)
        
        Args:
            to_phone_number (str): Recipient's phone number
            message_text (str): Message body text
            list_items (list): List of item dicts with 'id', 'title', and optional 'description'
                              Example: [{'id': '1', 'title': 'Option 1', 'description': 'Details'}, ...]
        
        Returns:
            bool: True if successful, False otherwise
        """
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        # Build list rows
        rows = []
        for item in list_items[:10]:  # Max 10 items in a list
            row = {
                'id': item['id'],
                'title': item['title'][:24]  # Max 24 chars
            }
            if 'description' in item:
                row['description'] = item['description'][:72]  # Max 72 chars
            rows.append(row)
        
        payload = {
            'messaging_product': 'whatsapp',
            'recipient_type': 'individual',
            'to': to_phone_number,
            'type': 'interactive',
            'interactive': {
                'type': 'list',
                'body': {
                    'text': message_text
                },
                'action': {
                    'button': 'בחר אפשרות',  # Button text to open list
                    'sections': [
                        {
                            'title': 'אפשרויות',
                            'rows': rows
                        }
                    ]
                }
            }
        }
        
        try:
            response = requests.post(self.api_url, json=payload, headers=headers)
            response.raise_for_status()
            
            logger.info(f"List message sent successfully to {to_phone_number}")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send list message to {to_phone_number}: {str(e)}")
            if hasattr(e.response, 'text'):
                logger.error(f"Response: {e.response.text}")
            return False

