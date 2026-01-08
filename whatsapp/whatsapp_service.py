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
    Send WhatsApp message to user (or save to history for test users)
    
    For test users (972500000001-004), messages are saved to chat history
    instead of being sent via WhatsApp. This allows testing in the Sandbox UI.
    
    Args:
        phone_number: Recipient's phone number
        message: Message text to send
    
    Returns:
        True if successful, False otherwise
    """
    from config import TEST_USERS
    
    try:
        # Check if this is a test user
        if phone_number in TEST_USERS:
            logger.info(f"🧪 ═══ TEST USER - SAVING TO HISTORY (NO WHATSAPP) ═══")
            logger.info(f"📱 User: {phone_number}")
            logger.info(f"💬 Message ({len(message)} chars):\n{message}")
            
            # Save to regular chat history instead of sending WhatsApp
            # Test users are in the same database as regular users
            from database import add_message_to_history
            await add_message_to_history(
                phone_number,
                "assistant",
                message
            )
            
            logger.info(f"✅ Message saved to chat history for test user (no WhatsApp sent)")
            return True
        
        if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
            logger.warning("WhatsApp credentials not configured")
            return False
        
        # Log outgoing message
        logger.info(f"📤 ═══ SENDING TO WHATSAPP ═══")
        logger.info(f"📱 To: {phone_number}")
        logger.info(f"💬 Message ({len(message)} chars):\n{message}")
        
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
        
        logger.info(f"✅ WhatsApp API Response: {response.status_code}")
        return True
    
    except Exception as e:
        logger.error(f"❌ Error sending WhatsApp message: {str(e)}")
        return False



