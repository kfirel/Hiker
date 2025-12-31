"""
AI Service - Gemini AI integration
Handles AI-powered conversation and function calling
"""

import logging
import json
from datetime import datetime
from typing import Dict, Any

from google import genai
from google.genai import types

from config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    SYSTEM_PROMPT,
    ERROR_MESSAGE_HEBREW,
    MAX_CONVERSATION_CONTEXT,
    DEFAULT_AVAILABLE_SEATS,
    DEFAULT_ORIGIN
)
from database import add_message_to_history, update_user_role_and_data
from services.whatsapp_service import send_whatsapp_message
from services.matching_service import find_matches_for_user

logger = logging.getLogger(__name__)


def get_function_tool():
    """Get the function calling tool for Gemini"""
    return types.Tool(
        function_declarations=[
            types.FunctionDeclaration(
                name="update_user_records",
                description="Update user role and structured data in the database. Use this when you have collected enough information about the user.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "role": types.Schema(
                            type=types.Type.STRING,
                            description="User's role - either 'driver' or 'hitchhiker'",
                            enum=["driver", "hitchhiker"]
                        ),
                        "origin": types.Schema(
                            type=types.Type.STRING,
                            description="Starting location - always 'גברעם' (default)"
                        ),
                        "destination": types.Schema(
                            type=types.Type.STRING,
                            description="Destination location (e.g., 'תל אביב', 'חיפה')"
                        ),
                        "days": types.Schema(
                            type=types.Type.ARRAY,
                            description="Days of the week (for drivers)",
                            items=types.Schema(type=types.Type.STRING)
                        ),
                        "departure_time": types.Schema(
                            type=types.Type.STRING,
                            description="Departure time - e.g., '09:00', '17:30'"
                        ),
                        "return_time": types.Schema(
                            type=types.Type.STRING,
                            description="Return time (for drivers who make round trips)"
                        ),
                        "available_seats": types.Schema(
                            type=types.Type.INTEGER,
                            description="Number of available seats (for drivers) - optional, default to 3"
                        ),
                        "travel_date": types.Schema(
                            type=types.Type.STRING,
                            description="Specific travel date for hitchhikers"
                        ),
                        "flexibility": types.Schema(
                            type=types.Type.STRING,
                            description="Time flexibility for hitchhikers"
                        ),
                        "notes": types.Schema(
                            type=types.Type.STRING,
                            description="Additional notes or preferences"
                        )
                    },
                    required=["role", "destination"]
                )
            )
        ]
    )


async def execute_function_call(
    function_name: str,
    function_args: Dict[str, Any],
    phone_number: str
) -> Dict[str, Any]:
    """
    Execute AI function call
    
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
            
            # Build role data (origin is always גברעם)
            role_data = {}
            if role == "driver":
                role_data = {
                    "origin": DEFAULT_ORIGIN,
                    "destination": function_args.get("destination"),
                    "days": function_args.get("days", []),
                    "departure_time": function_args.get("departure_time"),
                    "return_time": function_args.get("return_time"),
                    "available_seats": function_args.get("available_seats", DEFAULT_AVAILABLE_SEATS),
                    "notes": function_args.get("notes", "")
                }
            elif role == "hitchhiker":
                role_data = {
                    "origin": DEFAULT_ORIGIN,
                    "destination": function_args.get("destination"),
                    "travel_date": function_args.get("travel_date"),
                    "departure_time": function_args.get("departure_time"),
                    "flexibility": function_args.get("flexibility", "flexible"),
                    "notes": function_args.get("notes", "")
                }
            
            # Update database
            success = await update_user_role_and_data(phone_number, role, role_data)
            
            if not success:
                return {"success": False, "message": "Failed to update user records"}
            
            # Find matches
            matches = await find_matches_for_user(role, role_data)
            
            return {
                "success": True,
                "message": f"User registered as {role}",
                "role": role,
                "data": role_data,
                **matches
            }
        
        return {"success": False, "message": f"Unknown function: {function_name}"}
    
    except Exception as e:
        logger.error(f"❌ Error executing function: {str(e)}")
        return {"success": False, "message": str(e)}


async def process_message_with_ai(
    phone_number: str,
    message: str,
    user_data: Dict[str, Any],
    is_new_user: bool = False
) -> None:
    """
    Process user message with Gemini AI
    
    Args:
        phone_number: User's phone number
        message: User's message text
        user_data: User's data from database
        is_new_user: Whether this is a new user
    """
    try:
        if not GEMINI_API_KEY:
            # Fallback without AI
            response = f"קיבלתי: {message}\n(AI לא מופעל)"
            await send_whatsapp_message(phone_number, response)
            return
        
        # Add user message to history
        await add_message_to_history(phone_number, "user", message)
        
        # If new user, refresh user_data to include the welcome message we just added
        if is_new_user:
            from database import get_or_create_user
            user_data, _ = await get_or_create_user(phone_number)
        
        # Get current context
        now = datetime.utcnow()
        current_timestamp = now.strftime("%Y-%m-%d %H:%M:%S UTC")
        current_day_of_week = now.strftime("%A")
        
        # Build system prompt with context
        system_prompt = SYSTEM_PROMPT.format(
            current_timestamp=current_timestamp,
            current_day_of_week=current_day_of_week
        )
        
        # Build conversation history
        chat_history = user_data.get("chat_history", [])
        conversation = []
        
        for msg in chat_history[-MAX_CONVERSATION_CONTEXT:]:  # Last N messages
            if msg["role"] == "user":
                conversation.append({"role": "user", "parts": [msg["content"]]})
            elif msg["role"] == "assistant":
                conversation.append({"role": "model", "parts": [msg["content"]]})
        
        # Initialize Gemini client
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        # Create config with tools
        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            tools=[get_function_tool()],
            temperature=0.7
        )
        
        # Build message history for API
        history = []
        for msg in conversation[:-1]:
            history.append(types.Content(
                role=msg["role"],
                parts=[types.Part(text=msg["parts"][0])]
            ))
        
        # Add current message
        history.append(types.Content(
            role="user",
            parts=[types.Part(text=message)]
        ))
        
        # Generate response with function calling
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=history,
            config=config
        )
        
        # Check for function calls
        if response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'function_call') and part.function_call:
                    function_call = part.function_call
                    function_name = function_call.name
                    function_args = dict(function_call.args)
                    
                    # Convert RepeatedComposite (protobuf) to list for JSON serialization
                    for key, value in function_args.items():
                        if hasattr(value, '__iter__') and not isinstance(value, (str, dict)):
                            function_args[key] = list(value)
                    
                    logger.info(f"🤖 AI called function: {function_name}")
                    logger.info(f"   Args: {json.dumps(function_args, ensure_ascii=False)}")
                    
                    # Execute function
                    result = await execute_function_call(function_name, function_args, phone_number)
                    
                    # Send function result back to AI for continuation
                    history.append(response.candidates[0].content)
                    history.append(types.Content(
                        role="user",
                        parts=[types.Part(
                            function_response=types.FunctionResponse(
                                name=function_name,
                                response={"result": result}
                            )
                        )]
                    ))
                    
                    # Get final response from AI
                    response = client.models.generate_content(
                        model=GEMINI_MODEL,
                        contents=history,
                        config=config
                    )
        
        # Get final text response
        ai_response = response.text
        logger.info(f"🤖 AI response: {ai_response[:100]}...")
        
        # Send to user
        await send_whatsapp_message(phone_number, ai_response)
        
        # Add to history
        await add_message_to_history(phone_number, "assistant", ai_response)
    
    except Exception as e:
        logger.error(f"❌ Error in AI processing: {str(e)}", exc_info=True)
        await send_whatsapp_message(phone_number, ERROR_MESSAGE_HEBREW)

