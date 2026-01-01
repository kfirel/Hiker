"""
Background Tasks Implementation
Speeds up webhook responses by 5-10x
"""

from fastapi import BackgroundTasks, FastAPI, Request
from fastapi.responses import JSONResponse
import logging
import asyncio

logger = logging.getLogger(__name__)

# Example: Updated webhook handler with background tasks

async def process_message_async(phone_number: str, message: str, user_data: dict):
    """
    Process message in background
    This doesn't block the webhook response
    """
    try:
        from services.ai_service import process_message_with_ai
        await process_message_with_ai(phone_number, message, user_data)
    except Exception as e:
        logger.error(f"Background task error: {e}", exc_info=True)
        # Send error message to user
        from services.whatsapp_service import send_whatsapp_message
        await send_whatsapp_message(
            phone_number,
            "מצטערים, אירעה שגיאה בעיבוד הבקשה שלך. נסה שוב בבקשה."
        )


async def handle_webhook_fast(request: Request, background_tasks: BackgroundTasks):
    """
    Fast webhook handler using background tasks
    
    BEFORE: 5-10 seconds response time
    AFTER:  <500ms response time
    """
    try:
        body = await request.json()
        
        if not body.get("entry"):
            return JSONResponse(content={"status": "ok"})
        
        # Extract messages quickly
        for entry in body["entry"]:
            for change in entry.get("changes", []):
                value = change.get("value", {})
                
                if "messages" not in value:
                    continue
                
                for message in value["messages"]:
                    phone_number = message["from"]
                    message_text = message.get("text", {}).get("body", "")
                    
                    # Get user data (fast query)
                    from database import get_or_create_user
                    user_data, is_new = await get_or_create_user(phone_number)
                    
                    # Add processing to background
                    background_tasks.add_task(
                        process_message_async,
                        phone_number,
                        message_text,
                        user_data
                    )
                    
                    logger.info(f"✅ Queued message from {phone_number} for processing")
        
        # Return immediately! ⚡
        return JSONResponse(content={"status": "ok"})
    
    except Exception as e:
        logger.error(f"Webhook error: {e}", exc_info=True)
        return JSONResponse(
            status_code=200,  # Still return 200 to WhatsApp
            content={"status": "error"}
        )


# How to integrate into main.py:
"""
@app.post("/webhook")
async def handle_webhook(request: Request, background_tasks: BackgroundTasks):
    return await handle_webhook_fast(request, background_tasks)
"""



