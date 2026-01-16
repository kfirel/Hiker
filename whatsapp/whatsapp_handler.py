"""
WhatsApp webhook handler
Processes incoming WhatsApp messages
"""

import logging
from typing import Dict, Any
import asyncio
from datetime import datetime, timedelta

from config import get_welcome_message, NON_TEXT_MESSAGE_HEBREW
from database import get_or_create_user, get_db
from services import send_whatsapp_message, process_message_with_ai
import admin

logger = logging.getLogger(__name__)

# Track users currently being processed (prevent duplicate processing)
_processing_users = {}
_processing_lock = asyncio.Lock()


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
        
        # 🔒 Check if this user is already being processed
        async with _processing_lock:
            if from_number in _processing_users:
                time_diff = (datetime.now() - _processing_users[from_number]).total_seconds()
                if time_diff < 60:  # Still processing if less than 60 seconds
                    logger.warning(f"⏳ User {from_number} already being processed ({time_diff:.1f}s ago), skipping duplicate message")
                    await send_whatsapp_message(from_number, "רגע, אני עדיין מעבד את ההודעה הקודמת שלך... 🔄")
                    return True
                else:
                    # Old processing (probably timed out), allow new one
                    logger.warning(f"⚠️ Stale processing entry for {from_number} ({time_diff:.1f}s), allowing new processing")
                    del _processing_users[from_number]
            
            # Mark user as being processed
            _processing_users[from_number] = datetime.now()
        
        if message_type == "text":
            message_text = message["text"]["body"]
            logger.info(f"💬 Text: {message_text}")
            
            # Save incoming user message to history
            # (admin commands and new user handling will send responses via send_whatsapp_message which auto-saves)
            await add_message_to_history(from_number, "user", message_text)
            
            # Check for admin commands (new secure system)
            db = get_db()
            if db and message_text.startswith("/a"):
                admin_response = await admin.handle_admin_whatsapp_command(
                    from_number, message_text, db
                )
                
                if admin_response:
                    await send_whatsapp_message(from_number, admin_response)
                    # Remove from processing
                    async with _processing_lock:
                        if from_number in _processing_users:
                            del _processing_users[from_number]
                    return True
            
            # Get or create user (with name)
            user_data, is_new_user = await get_or_create_user(from_number, user_name)
            
            # Send welcome message to new users and skip AI processing
            if is_new_user:
                welcome_msg = get_welcome_message(user_name)
                # Save the user's first message so history is complete
                await add_message_to_history(from_number, "user", message_text)
                # send_whatsapp_message now auto-saves to history (test users)
                await send_whatsapp_message(from_number, welcome_msg)
                await add_message_to_history(from_number, "assistant", welcome_msg)
                logger.info(f"👋 משתמש חדש: {user_display}")
                # Remove from processing
                async with _processing_lock:
                    if from_number in _processing_users:
                        del _processing_users[from_number]
                # Don't process first message with AI - welcome is enough
                return True
            
            # Process with AI for existing users
            try:
                await process_message_with_ai(from_number, message_text, user_data, is_new_user=False)
                return True
            finally:
                # 🔓 Remove user from processing set
                async with _processing_lock:
                    if from_number in _processing_users:
                        del _processing_users[from_number]
                        logger.debug(f"✅ Released processing lock for {from_number}")
        
        else:
            # Non-text message
            await send_whatsapp_message(from_number, NON_TEXT_MESSAGE_HEBREW)
            # Remove from processing
            async with _processing_lock:
                if from_number in _processing_users:
                    del _processing_users[from_number]
            return True
    
    except Exception as e:
        logger.error(f"❌ Error handling message: {str(e)}", exc_info=True)
        # Clean up processing lock on error
        async with _processing_lock:
            if from_number in _processing_users:
                del _processing_users[from_number]
        return False


# Import after defining function to avoid circular import
from database import add_message_to_history

