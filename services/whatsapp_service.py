"""
WhatsApp messaging service
Handles sending messages via WhatsApp Cloud API
"""

import logging
import requests

from config import WHATSAPP_TOKEN, WHATSAPP_API_URL, WHATSAPP_PHONE_NUMBER_ID

logger = logging.getLogger(__name__)


async def send_whatsapp_message(phone_number: str, message: str) -> bool:
    """
    Send WhatsApp message to user
    
    Args:
        phone_number: Recipient's phone number
        message: Message text to send
    
    Returns:
        True if successful, False otherwise
    """
    try:
        if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
            logger.warning("WhatsApp credentials not configured")
            return False
        
        headers = {
            "Authorization": f"Bearer {WHATSAPP_TOKEN}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "messaging_product": "whatsapp",
            "to": phone_number,
            "type": "text",
            "text": {"body": message}
        }
        
        response = requests.post(WHATSAPP_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        
        logger.info(f"✅ Message sent to {phone_number}")
        return True
    
    except Exception as e:
        logger.error(f"❌ Error sending message: {str(e)}")
        return False

