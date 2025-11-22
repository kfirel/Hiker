import requests
import logging
from typing import Optional
from src.config import Config

logger = logging.getLogger(__name__)

class WhatsAppClient:
    """Client for sending messages via WhatsApp Cloud API"""
    
    def __init__(self, user_logger=None):
        """
        Initialize WhatsApp client
        
        Args:
            user_logger: Optional UserLogger instance for automatic logging of sent messages
        """
        self.phone_number_id = Config.WHATSAPP_PHONE_NUMBER_ID
        self.access_token = Config.WHATSAPP_ACCESS_TOKEN
        self.api_url = Config.WHATSAPP_API_URL
        self.user_logger = user_logger
    
    def get_user_profile_name(self, phone_number: str) -> Optional[str]:
        """
        Get user's profile name from WhatsApp API
        
        Args:
            phone_number (str): User's phone number (with country code, no +)
            
        Returns:
            str: User's profile name, or None if not available
        """
        # WhatsApp Cloud API endpoint for getting user profile
        profile_url = f"https://graph.facebook.com/v18.0/{phone_number}"
        
        headers = {
            'Authorization': f'Bearer {self.access_token}'
        }
        
        params = {
            'fields': 'profile'
        }
        
        try:
            # Add timeout to prevent hanging (2 seconds for connect, 3 seconds for read)
            response = requests.get(profile_url, headers=headers, params=params, timeout=(2, 3))
            if response.status_code == 200:
                data = response.json()
                # Profile name is usually in 'name' field
                profile_name = data.get('name') or data.get('profile', {}).get('name')
                if profile_name:
                    logger.info(f"Retrieved profile name for {phone_number}: {profile_name}")
                    return profile_name
            else:
                logger.debug(f"Could not get profile for {phone_number}: {response.status_code}")
        except requests.exceptions.Timeout:
            logger.debug(f"Timeout getting profile name for {phone_number}")
        except Exception as e:
            logger.debug(f"Error getting profile name for {phone_number}: {str(e)}")
        
        return None
    
    def send_message(self, to_phone_number, message_text, buttons=None, state=None):
        """
        Send a text message via WhatsApp Cloud API
        
        Args:
            to_phone_number (str): Recipient's phone number (with country code, no +)
            message_text (str): Text message to send
            buttons (list): Optional list of button dicts for interactive message
            state (str): Optional conversation state for logging
            
        Returns:
            bool: True if successful, False otherwise
        """
        # If buttons provided and <= 3, use reply buttons
        if buttons and len(buttons) <= 3:
            success = self.send_button_message(to_phone_number, message_text, buttons)
        # If buttons > 3, use list message
        elif buttons and len(buttons) > 3:
            success = self.send_list_message(to_phone_number, message_text, buttons)
        # No buttons, send regular text
        else:
            success = self._send_text_message(to_phone_number, message_text)
        
        # Log message automatically after successful send (lowest level logging)
        if success and self.user_logger:
            self.user_logger.log_bot_response(to_phone_number, message_text, state=state, buttons=buttons)
        
        return success
    
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
            # Add timeout to prevent hanging (5 seconds for send, 2 seconds for connect)
            response = requests.post(self.api_url, json=payload, headers=headers, timeout=(2, 5))
            response.raise_for_status()
            
            logger.info(f"Text message sent successfully to {to_phone_number}")
            return True
            
        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout sending message to {to_phone_number}: {str(e)}")
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send message to {to_phone_number}: {str(e)}")
            if hasattr(e, 'response') and e.response is not None and hasattr(e.response, 'text'):
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
            # Support both formats: {'id': '...', 'title': '...'} and {'type': 'reply', 'reply': {...}}
            if 'type' in btn and btn['type'] == 'reply':
                # Already in correct format
                button_components.append(btn)
            elif 'id' in btn and 'title' in btn:
                # Simple format, convert to WhatsApp format
                button_components.append({
                    'type': 'reply',
                    'reply': {
                        'id': btn['id'],
                        'title': btn['title'][:20]  # Max 20 chars for button title
                    }
                })
            elif 'reply' in btn:
                # Already has 'reply' key, just add type
                button_components.append({
                    'type': 'reply',
                    'reply': btn['reply']
                })
            else:
                logger.warning(f"Skipping invalid button format: {btn}")
        
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
            logger.info(f"Sending button message to {to_phone_number} with {len(button_components)} buttons")
            logger.debug(f"Button payload: {payload}")
            
            # Add timeout to prevent hanging (5 seconds for send, 2 seconds for connect)
            response = requests.post(self.api_url, json=payload, headers=headers, timeout=(2, 5))
            response.raise_for_status()
            
            logger.info(f"Button message sent successfully to {to_phone_number}")
            return True
            
        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout sending button message to {to_phone_number}: {str(e)}")
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send button message to {to_phone_number}: {str(e)}")
            if hasattr(e, 'response') and e.response is not None and hasattr(e.response, 'text'):
                logger.error(f"Response: {e.response.text}")
            logger.error(f"Failed payload: {payload}")
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
            # Handle different button formats
            # Format 1: Simple format {'id': '...', 'title': '...'}
            # Format 2: WhatsApp format {'type': 'reply', 'reply': {'id': '...', 'title': '...'}}
            if 'reply' in item and isinstance(item['reply'], dict):
                # WhatsApp format - extract from reply
                item_id = item['reply'].get('id', '')
                item_title = item['reply'].get('title', '')
            elif 'id' in item:
                # Simple format
                item_id = item['id']
                item_title = item.get('title', '')
            else:
                logger.warning(f"Skipping invalid list item format: {item}")
                continue
            
            row = {
                'id': str(item_id),
                'title': item_title[:24]  # Max 24 chars
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
            # Add timeout to prevent hanging (5 seconds for send, 2 seconds for connect)
            response = requests.post(self.api_url, json=payload, headers=headers, timeout=(2, 5))
            response.raise_for_status()
            
            logger.info(f"List message sent successfully to {to_phone_number}")
            return True
            
        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout sending list message to {to_phone_number}: {str(e)}")
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send list message to {to_phone_number}: {str(e)}")
            if hasattr(e, 'response') and e.response is not None and hasattr(e.response, 'text'):
                logger.error(f"Response: {e.response.text}")
            return False

