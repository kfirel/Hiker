"""
WhatsApp webhook handler
Processes incoming WhatsApp messages
"""

import logging
from typing import Dict, Any

from config import get_welcome_message, NON_TEXT_MESSAGE_HEBREW
from database import get_or_create_user, get_db
from services import send_whatsapp_message, process_message_with_ai
import admin

logger = logging.getLogger(__name__)


async def handle_whatsapp_message(message: Dict[str, Any]) -> bool:
    """
    Handle a single WhatsApp message
    
    Args:
        message: Message object from WhatsApp webhook
    
    Returns:
        True if handled successfully
    """
    try:
        from_number = message.get("from")
        message_type = message.get("type")
        user_name = message.get("_contact_name")  # Extract name from webhook
        
        user_display = f"{user_name} ({from_number})" if user_name else from_number
        
        # Enhanced logging for incoming message
        logger.info(f"📥 ═══ RECEIVED FROM WHATSAPP ═══")
        logger.info(f"👤 From: {user_display}")
        logger.info(f"📋 Type: {message_type}")
        
        if message_type == "text":
            message_text = message["text"]["body"]
            logger.info(f"💬 Text: {message_text}")
            
            # Check for admin commands (new secure system)
            db = get_db()
            if db and message_text.startswith("/a"):
                admin_response = await admin.handle_admin_whatsapp_command(
                    from_number, message_text, db
                )
                
                if admin_response:
                    await send_whatsapp_message(from_number, admin_response)
                    return True
            
            # Get or create user (with name)
            user_data, is_new_user = await get_or_create_user(from_number, user_name)
            
            # Send welcome message to new users and skip AI processing
            if is_new_user:
                welcome_msg = get_welcome_message(user_name)
                await send_whatsapp_message(from_number, welcome_msg)
                await add_message_to_history(from_number, "assistant", welcome_msg)
                logger.info(f"👋 משתמש חדש: {user_display}")
                # Don't process first message with AI - welcome is enough
                return True
            
            # Process with AI for existing users
            await process_message_with_ai(from_number, message_text, user_data, is_new_user=False)
            return True
        
        else:
            # Non-text message
            await send_whatsapp_message(from_number, NON_TEXT_MESSAGE_HEBREW)
            return True
    
    except Exception as e:
        logger.error(f"❌ Error handling message: {str(e)}", exc_info=True)
        return False


# Import after defining function to avoid circular import
from database import add_message_to_history

