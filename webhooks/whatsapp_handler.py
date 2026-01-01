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
            
            # Check for pending approval responses (BEFORE AI processing)
            # This handles simple "כן"/"לא" responses automatically
            from services.approval_service import check_and_handle_approval_response
            approval_response = await check_and_handle_approval_response(from_number, message_text)
            
            if approval_response:
                # Response was handled by approval system, no need for AI
                await send_whatsapp_message(from_number, approval_response)
                logger.info(f"✅ Approval handled automatically: {from_number}")
                return True
            
            # SAFETY NET: Check if message has clear travel intent
            # If AI fails to call function, we force it from code
            from services.intent_detector import should_force_function_call, detect_travel_intent
            
            if should_force_function_call(message_text):
                logger.warning(f"⚠️ SAFETY NET: Forcing function call for: {message_text}")
                intent = detect_travel_intent(message_text)
                
                if intent:
                    from services.function_handlers import handle_update_user_records
                    
                    try:
                        result = await handle_update_user_records(from_number, intent)
                        response_message = result.get("message", "נשמר!")
                        
                        await send_whatsapp_message(from_number, response_message)
                        await add_message_to_history(from_number, "user", message_text)
                        await add_message_to_history(from_number, "assistant", response_message)
                        
                        logger.info(f"✅ Safety net handled: {from_number}")
                        return True
                    except Exception as e:
                        logger.error(f"❌ Safety net failed: {e}")
                        # Fall through to AI processing
            
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

