"""
Gemini AI Agent with Function Calling
Handles conversation logic and structured data extraction
"""

import os
import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
import requests
import google.generativeai as genai

from database import (
    add_message_to_history,
    update_user_role_and_data,
    get_drivers_by_route,
    get_hitchhiker_requests
)

logger = logging.getLogger(__name__)

# Initialize Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

# WhatsApp API configuration
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
WHATSAPP_API_URL = f"https://graph.facebook.com/v18.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"

# Welcome message in Hebrew
WELCOME_MESSAGE = """שלום וברוך הבא לאפליקצית הטרמפים של גברעם! 🚗

אם אתה מחפש טרמפ שלח לי הודעה בסגנון:
"אני מחפש טרמפ לתל אביב בשעה 12:00 מחר"

אם אתה נהג שרוצה לעזור:
"אני נוסע בימים א-ה לתל אביב בשעה 9 וחוזר ב-17:30"

איך אני יכול לעזור לך היום?"""

# System prompt for the AI
SYSTEM_PROMPT = """אתה עוזר וירטואלי לקהילת הטרמפים של גברעם. תפקידך:

1. לזהות אם המשתמש הוא נהג (driver) או מחפש טרמפ (hitchhiker)
2. לאסוף מידע מובנה:
   - נהג: מוצא, יעד, ימים בשבוע, שעות נסיעה, מספר מקומות פנויים
   - מחפש טרמפ: מוצא, יעד, תאריך/זמן רצוי, גמישות
3. לעזור בהתאמה בין נהגים למחפשי טרמפ
4. לדבר בעברית בצורה ידידותית וברורה

כאשר יש לך מספיק מידע, השתמש בפונקציה update_user_records לשמור את הנתונים.

אם משהו לא ברור, שאל שאלות הבהרה.

הקשר הנוכחי:
- תאריך ושעה: {current_timestamp}
- יום בשבוע: {current_day_of_week}
"""

# Function calling schema for Gemini
UPDATE_USER_RECORDS_TOOL = {
    "name": "update_user_records",
    "description": "Update user role and structured data in the database. Use this when you have collected enough information about the user.",
    "parameters": {
        "type": "object",
        "properties": {
            "role": {
                "type": "string",
                "enum": ["driver", "hitchhiker"],
                "description": "User's role - either 'driver' or 'hitchhiker'"
            },
            "origin": {
                "type": "string",
                "description": "Starting location (e.g., 'גברעם', 'ירושלים')"
            },
            "destination": {
                "type": "string",
                "description": "Destination location (e.g., 'תל אביב', 'חיפה')"
            },
            "days": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Days of the week (for drivers) - e.g., ['Sunday', 'Monday', 'Tuesday']"
            },
            "departure_time": {
                "type": "string",
                "description": "Departure time - e.g., '09:00', '17:30'"
            },
            "return_time": {
                "type": "string",
                "description": "Return time (for drivers who make round trips)"
            },
            "available_seats": {
                "type": "integer",
                "description": "Number of available seats (for drivers)"
            },
            "travel_date": {
                "type": "string",
                "description": "Specific travel date for hitchhikers - e.g., '2024-01-15'"
            },
            "flexibility": {
                "type": "string",
                "description": "Time flexibility for hitchhikers - e.g., 'flexible', 'specific time only'"
            },
            "notes": {
                "type": "string",
                "description": "Additional notes or preferences"
            }
        },
        "required": ["role", "origin", "destination"]
    }
}


async def send_whatsapp_message(phone_number: str, message: str) -> bool:
    """
    Send a WhatsApp message to a user
    
    Args:
        phone_number: Recipient's phone number
        message: Message text to send
    
    Returns:
        True if successful, False otherwise
    """
    try:
        headers = {
            "Authorization": f"Bearer {WHATSAPP_TOKEN}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "messaging_product": "whatsapp",
            "to": phone_number,
            "type": "text",
            "text": {
                "body": message
            }
        }
        
        response = requests.post(WHATSAPP_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        
        logger.info(f"Sent message to {phone_number}")
        return True
    
    except Exception as e:
        logger.error(f"Error sending WhatsApp message to {phone_number}: {str(e)}")
        return False


async def send_welcome_message(phone_number: str) -> bool:
    """Send welcome message to new users"""
    return await send_whatsapp_message(phone_number, WELCOME_MESSAGE)


async def execute_function_call(
    function_name: str,
    function_args: Dict[str, Any],
    phone_number: str
) -> Dict[str, Any]:
    """
    Execute the function called by the AI
    
    Args:
        function_name: Name of the function to execute
        function_args: Arguments for the function
        phone_number: User's phone number
    
    Returns:
        Result dictionary
    """
    try:
        if function_name == "update_user_records":
            role = function_args.get("role")
            
            # Build role-specific data
            role_data = {}
            
            if role == "driver":
                role_data = {
                    "origin": function_args.get("origin"),
                    "destination": function_args.get("destination"),
                    "days": function_args.get("days", []),
                    "departure_time": function_args.get("departure_time"),
                    "return_time": function_args.get("return_time"),
                    "available_seats": function_args.get("available_seats", 1),
                    "notes": function_args.get("notes", "")
                }
            elif role == "hitchhiker":
                role_data = {
                    "origin": function_args.get("origin"),
                    "destination": function_args.get("destination"),
                    "travel_date": function_args.get("travel_date"),
                    "departure_time": function_args.get("departure_time"),
                    "flexibility": function_args.get("flexibility", "flexible"),
                    "notes": function_args.get("notes", "")
                }
            
            # Update database
            success = await update_user_role_and_data(phone_number, role, role_data)
            
            if success:
                # Try to find matches
                if role == "hitchhiker":
                    drivers = await get_drivers_by_route(
                        origin=function_args.get("origin"),
                        destination=function_args.get("destination")
                    )
                    return {
                        "success": True,
                        "message": f"User registered as {role}",
                        "matches_found": len(drivers),
                        "drivers": drivers[:3]  # Return top 3 matches
                    }
                else:
                    hitchhikers = await get_hitchhiker_requests(
                        destination=function_args.get("destination")
                    )
                    return {
                        "success": True,
                        "message": f"User registered as {role}",
                        "matches_found": len(hitchhikers),
                        "hitchhikers": hitchhikers[:3]  # Return top 3 matches
                    }
            else:
                return {"success": False, "message": "Failed to update user records"}
        
        return {"success": False, "message": f"Unknown function: {function_name}"}
    
    except Exception as e:
        logger.error(f"Error executing function {function_name}: {str(e)}")
        return {"success": False, "message": str(e)}


async def process_message_with_ai(
    phone_number: str,
    message: str,
    user_data: Dict[str, Any]
) -> None:
    """
    Process user message with Gemini AI and send response
    
    Args:
        phone_number: User's phone number
        message: User's message text
        user_data: User's data from Firestore
    """
    try:
        # Add user message to history
        await add_message_to_history(phone_number, "user", message)
        
        # Get current context
        current_timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        current_day_of_week = datetime.utcnow().strftime("%A")
        
        # Build system prompt with context
        system_prompt = SYSTEM_PROMPT.format(
            current_timestamp=current_timestamp,
            current_day_of_week=current_day_of_week
        )
        
        # Build conversation history
        chat_history = user_data.get("chat_history", [])
        conversation = []
        
        for msg in chat_history[-4:]:  # Last 4 messages (excluding current)
            if msg["role"] == "user":
                conversation.append({"role": "user", "parts": [msg["content"]]})
            else:
                conversation.append({"role": "model", "parts": [msg["content"]]})
        
        # Add current message
        conversation.append({"role": "user", "parts": [message]})
        
        # Initialize model with function calling
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            tools=[UPDATE_USER_RECORDS_TOOL]
        )
        
        # Start chat with history
        chat = model.start_chat(history=conversation[:-1])
        
        # Send message with system prompt prepended
        full_message = f"{system_prompt}\n\nUser: {message}"
        response = chat.send_message(full_message)
        
        # Check if AI wants to call a function
        if response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'function_call') and part.function_call:
                    function_call = part.function_call
                    function_name = function_call.name
                    function_args = dict(function_call.args)
                    
                    logger.info(f"AI called function: {function_name} with args: {function_args}")
                    
                    # Execute the function
                    result = await execute_function_call(function_name, function_args, phone_number)
                    
                    # Send function result back to AI to generate user-facing response
                    response = chat.send_message(
                        genai.protos.Content(
                            parts=[genai.protos.Part(
                                function_response=genai.protos.FunctionResponse(
                                    name=function_name,
                                    response={"result": result}
                                )
                            )]
                        )
                    )
        
        # Get final text response
        ai_response = response.text
        
        # Send response to user
        await send_whatsapp_message(phone_number, ai_response)
        
        # Add AI response to history
        await add_message_to_history(phone_number, "assistant", ai_response)
        
        logger.info(f"Successfully processed message for {phone_number}")
    
    except Exception as e:
        logger.error(f"Error processing message for {phone_number}: {str(e)}", exc_info=True)
        
        # Send error message to user
        error_message = "סליחה, נתקלתי בבעיה. אנא נסה שוב מאוחר יותר. 🙏"
        await send_whatsapp_message(phone_number, error_message)


