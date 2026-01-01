"""
AI Service - Gemini AI integration
Handles AI-powered conversation and function calling
"""

import logging
import json
from datetime import datetime
from typing import Dict, Any, List

from google import genai
from google.genai import types

from config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    SYSTEM_PROMPT,
    ERROR_MESSAGE_HEBREW,
    MAX_CONVERSATION_CONTEXT
)
from database import add_message_to_history, get_user_rides_and_requests
from services.whatsapp_service import send_whatsapp_message
from services.matching_service import format_driver_info

logger = logging.getLogger(__name__)


# ============================================================================
# Helper Functions - Build AI Request
# ============================================================================

def build_message_content(role: str, text: str) -> types.Content:
    """
    Build a single message content for Gemini
    
    Args:
        role: "user" or "model"
        text: Message text
    
    Returns:
        Gemini Content object
    """
    return types.Content(
        role=role,
        parts=[types.Part(text=text)]
    )


def build_conversation_history(
    chat_history: List[Dict[str, Any]],
    current_message: str,
    max_messages: int = MAX_CONVERSATION_CONTEXT
) -> List[types.Content]:
    """
    Build conversation history for Gemini API
    Simple and readable format
    
    Args:
        chat_history: List of previous messages from DB
        current_message: Current user message
        max_messages: Maximum number of history messages to include
    
    Returns:
        List of Content objects for Gemini
    """
    contents = []
    
    # Add previous messages (limited to max_messages)
    for msg in chat_history[-max_messages:]:
        if msg["role"] == "user":
            contents.append(build_message_content("user", msg["content"]))
        elif msg["role"] == "assistant":
            contents.append(build_message_content("model", msg["content"]))
    
    # Add current message
    contents.append(build_message_content("user", current_message))
    
    return contents


def check_if_loop_detected(chat_history: List[Dict[str, Any]]) -> bool:
    """
    Check if AI is stuck in a loop (repeating same question)
    
    Args:
        chat_history: List of messages
    
    Returns:
        True if loop detected
    """
    if len(chat_history) < 3:
        return False
    
    # Get last 3 assistant messages
    last_assistant_messages = [
        msg["content"] 
        for msg in chat_history[-3:] 
        if msg["role"] == "assistant"
    ]
    
    # If last 2 assistant messages are identical → loop!
    if len(last_assistant_messages) >= 2:
        return last_assistant_messages[-1] == last_assistant_messages[-2]
    
    return False


# ============================================================================
# Function Tool Definition
# ============================================================================

def get_function_tool():
    """Get the function calling tool for Gemini"""
    return types.Tool(
        function_declarations=[
            types.FunctionDeclaration(
                name="update_user_records",
                description="""SAVE TRAVEL DATA - Call immediately when user provides destination + time!

DO NOT ASK PERMISSION! Just call this function!

Examples of INSTANT call:
"אני נוסעת כל יום לאשקלון ב8" → CALL NOW!
"מחפש טרמפ לתל אביב מחר" → CALL NOW!

The function will:
1. Save to database
2. Find matches
3. Send notifications
4. Return ready message for user

Your job: Extract params → Call function → Return the 'message' field.""",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "role": types.Schema(
                            type=types.Type.STRING,
                            description="Type of travel - 'driver' (offering ride) or 'hitchhiker' (looking for ride). Users can be BOTH simultaneously!",
                            enum=["driver", "hitchhiker"]
                        ),
                        "origin": types.Schema(
                            type=types.Type.STRING,
                            description="Starting location - USUALLY 'גברעם' (going out from kibbutz), BUT can be another city if user wants to go back HOME to גברעם (e.g., origin='תל אביב', destination='גברעם')"
                        ),
                        "destination": types.Schema(
                            type=types.Type.STRING,
                            description="Destination location - can be any city including 'גברעם' if going home (e.g., 'תל אביב', 'חיפה', 'גברעם')"
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
                        ),
                        "auto_approve_matches": types.Schema(
                            type=types.Type.BOOLEAN,
                            description="FOR DRIVERS ONLY: If true (default), automatically send driver details to matching hitchhikers. If false, system will return 'pending_approval=True' and you MUST ask driver: 'רוצה שאשלח את הפרטים שלך ל-X טרמפיסטים?' and wait for confirmation."
                        )
                    },
                    required=["role", "destination"]
                )
            ),
            types.FunctionDeclaration(
                name="get_user_info",
                description="Get the user's current information from the database. Use when user asks 'what's my info', 'show my details', or similar.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={}
                )
            ),
            types.FunctionDeclaration(
                name="delete_user_data",
                description="Delete all user data from the database. Use ONLY when user explicitly requests to delete their data or account.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "confirmation": types.Schema(
                            type=types.Type.STRING,
                            description="User's confirmation message"
                        )
                    },
                    required=["confirmation"]
                )
            ),
            types.FunctionDeclaration(
                name="remove_request",
                description="Remove or cancel the user's hitchhiking/driver request. Use when user wants to cancel their request. Can optionally specify destination.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "destination": types.Schema(
                            type=types.Type.STRING,
                            description="Optional: Specific destination to remove (e.g., 'אשקלון', 'תל אביב')"
                        )
                    }
                )
            ),
            types.FunctionDeclaration(
                name="modify_request",
                description="Modify specific fields of the user's existing request without creating a new one.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "destination": types.Schema(
                            type=types.Type.STRING,
                            description="New destination (optional)"
                        ),
                        "departure_time": types.Schema(
                            type=types.Type.STRING,
                            description="New departure time (optional)"
                        ),
                        "travel_date": types.Schema(
                            type=types.Type.STRING,
                            description="New travel date (optional, for hitchhikers)"
                        ),
                        "days": types.Schema(
                            type=types.Type.ARRAY,
                            description="New days of week (optional, for drivers)",
                            items=types.Schema(type=types.Type.STRING)
                        )
                    }
                )
            ),
            types.FunctionDeclaration(
                name="show_matching_hitchhikers",
                description="Show matching hitchhikers for a driver's routes. Use when driver asks 'מי הם?', 'תראה לי', 'who are they?'. IMPORTANT: This ONLY shows details to the driver - does NOT send notifications to hitchhikers. To actually send, use 'approve_and_send_to_hitchhikers' after driver confirms.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "ride_index": types.Schema(
                            type=types.Type.INTEGER,
                            description="Optional: Index of specific ride to check (0-based). If not provided, checks all active rides."
                        )
                    }
                )
            ),
            types.FunctionDeclaration(
                name="approve_and_send_to_hitchhikers",
                description="DRIVER APPROVAL: Send driver's contact details to matching hitchhikers. Use ONLY when: (1) You previously asked driver to approve, AND (2) Driver says 'yes'/'כן'/'שלח'/'בטח'/'אישור'. This SENDS the actual notifications to hitchhikers.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "ride_index": types.Schema(
                            type=types.Type.INTEGER,
                            description="Optional: Index of specific ride (0-based). If not provided, sends for all active rides."
                        )
                    }
                )
            )
        ]
    )


async def notify_hitchhikers_about_new_driver(
    driver_phone: str,
    driver_data: Dict[str, Any],
    hitchhikers: List[Dict[str, Any]]
) -> None:
    """
    Send WhatsApp notifications to hitchhikers about a new matching driver
    
    Args:
        driver_phone: Driver's phone number
        driver_data: Driver's route information
        hitchhikers: List of matching hitchhikers
    """
    if not hitchhikers:
        return
    
    # Filter out the driver's own phone number (in case they're also a hitchhiker)
    filtered_hitchhikers = [h for h in hitchhikers if h.get("phone_number") != driver_phone]
    
    if not filtered_hitchhikers:
        return
    
    # Get driver's name from database
    from database import get_or_create_user
    driver_user_data, _ = await get_or_create_user(driver_phone)
    driver_name = driver_user_data.get("name", "")
    
    # Format driver information for the notification
    driver_info_dict = {
        "phone_number": driver_phone,
        "name": driver_name,
        "destination": driver_data.get("destination"),
        "departure_time": driver_data.get("departure_time"),
        "days": driver_data.get("days", []),
        "return_time": driver_data.get("return_time")
    }
    
    formatted_driver = format_driver_info(driver_info_dict)
    
    # Create notification message
    destination = driver_data.get("destination", "")
    driver_name_display = f"{driver_name} " if driver_name else ""
    notification = f"""🚗 נהג חדש נוסע ל{destination}!

{driver_name_display}מציע נסיעה:
{formatted_driver}

צור קשר ישירות! 📲"""
    
    # Send notification to each hitchhiker
    sent_count = 0
    failed = []
    
    for hitchhiker in filtered_hitchhikers:
        hitchhiker_phone = hitchhiker.get("phone_number")
        if hitchhiker_phone:
            try:
                await send_whatsapp_message(hitchhiker_phone, notification)
                sent_count += 1
            except Exception as e:
                failed.append(hitchhiker_phone)
    
    # Single summary log
    logger.info(f"📤 נשלחו התראות: {sent_count}/{len(filtered_hitchhikers)} טרמפיסטים | נהג: {driver_phone} → {destination}")
    if failed:
        logger.error(f"❌ כשלון בשליחה ל-{len(failed)} טרמפיסטים: {failed}")


async def execute_function_call(
    function_name: str,
    function_args: Dict[str, Any],
    phone_number: str
) -> Dict[str, Any]:
    """
    Execute AI function call - routes to appropriate handler
    
    Args:
        function_name: Name of the function to execute
        function_args: Arguments for the function
        phone_number: User's phone number
    
    Returns:
        Result dictionary
    """
    from services.function_handlers import (
        handle_get_user_info,
        handle_delete_user_data,
        handle_update_user_records,
        handle_modify_request,
        handle_remove_request,
        handle_show_matching_hitchhikers,
        handle_approve_and_send
    )
    
    try:
        # Route to appropriate handler
        if function_name == "update_user_records":
            return await handle_update_user_records(phone_number, function_args)
        
        elif function_name == "get_user_info":
            return await handle_get_user_info(phone_number, function_args)
        
        elif function_name == "delete_user_data":
            return await handle_delete_user_data(phone_number, function_args)
        
        elif function_name == "modify_request":
            return await handle_modify_request(phone_number, function_args)
        
        elif function_name == "remove_request":
            return await handle_remove_request(phone_number, function_args)
        
        elif function_name == "show_matching_hitchhikers":
            return await handle_show_matching_hitchhikers(phone_number, function_args)
        
        elif function_name == "approve_and_send_to_hitchhikers":
            return await handle_approve_and_send(phone_number, function_args)
        
        # Unknown function
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
        
        # Get current context
        now = datetime.utcnow()
        current_timestamp = now.strftime("%Y-%m-%d %H:%M:%S UTC")
        current_day_of_week = now.strftime("%A")
        
        # Get user's name for personalization
        user_name = user_data.get("name")
        if user_name:
            user_name_instruction = f"- שם המשתמש: {user_name} - השתמש בשם באופן טבעי בשיחה (לא בכל משפט)"
        else:
            user_name_instruction = "- המשתמש לא שיתף את שמו - לא צריך להשתמש בשם"
        
        # Build system prompt with context
        system_prompt = SYSTEM_PROMPT.format(
            current_timestamp=current_timestamp,
            current_day_of_week=current_day_of_week,
            user_name_instruction=user_name_instruction
        )
        
        # ================================================================
        # Step 1: Check for loop & build conversation history
        # ================================================================
        chat_history = user_data.get("chat_history", [])
        
        # Detect if AI is stuck repeating same question
        if check_if_loop_detected(chat_history):
            logger.warning(f"⚠️ AI loop detected! Clearing history to reset conversation")
            chat_history = []  # Clear history, start fresh
        
        # Build conversation contents for Gemini API
        contents = build_conversation_history(
            chat_history=chat_history,
            current_message=message,
            max_messages=MAX_CONVERSATION_CONTEXT
        )
        
        # ================================================================
        # Step 2: Build config & initialize client
        # ================================================================
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            tools=[get_function_tool()],
            tool_config=types.ToolConfig(
                function_calling_config=types.FunctionCallingConfig(
                    mode="AUTO"  # AI decides when to use functions
                )
            ),
            temperature=0.1  # Low = consistent, high = creative
        )
        
        # ================================================================
        # Step 3: Log request (readable format)
        # ================================================================
        history_count = len(contents) - 1  # -1 for current message
        
        logger.info(f"🤖 ═══ SENDING TO GEMINI ═══")
        logger.info(f"📱 User: {phone_number}")
        logger.info(f"💬 Message: {message}")
        logger.info(f"📚 History: {history_count} previous messages")
        logger.info(f"🕐 Context: {current_timestamp} ({current_day_of_week})")
        
        # ================================================================
        # Step 4: Call Gemini API
        # ================================================================
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=contents,
            config=config
        )
        
        # Log AI response structure
        logger.info(f"🤖 ═══ RECEIVED FROM GEMINI ═══")
        
        # Validate response has candidates
        if not response.candidates or len(response.candidates) == 0:
            logger.error(f"❌ No candidates in Gemini response. Response: {response}")
            logger.error(f"🔍 Response attributes: {dir(response)}")
            if hasattr(response, 'prompt_feedback'):
                logger.error(f"⚠️ Prompt feedback: {response.prompt_feedback}")
            return "מצטער, התקבלה שגיאה בעיבוד ההודעה. אנא נסה שוב."
        
        logger.info(f"📥 Candidates: {len(response.candidates)}")
        logger.info(f"📦 Parts in response: {len(response.candidates[0].content.parts)}")
        
        # Check for function calls
        function_calls_found = []
        if response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'function_call') and part.function_call:
                    function_calls_found.append(part.function_call)
                    logger.info(f"🔧 Function call detected: {part.function_call.name}")
                elif hasattr(part, 'text') and part.text:
                    logger.info(f"📝 Text response: {part.text[:100]}..." if len(part.text) > 100 else f"📝 Text response: {part.text}")
        
        # If function calls were made, execute them and get final response
        if function_calls_found:
            logger.info(f"⚡ ═══ EXECUTING {len(function_calls_found)} FUNCTION(S) ═══")
            # Collect all function responses
            function_responses = []
            
            for idx, function_call in enumerate(function_calls_found, 1):
                function_name = function_call.name
                function_args = dict(function_call.args)
                
                # Convert RepeatedComposite (protobuf) to list for JSON serialization
                for key, value in function_args.items():
                    if hasattr(value, '__iter__') and not isinstance(value, (str, dict)):
                        function_args[key] = list(value)
                
                # Detailed function call log
                logger.info(f"🔧 [{idx}] Function: {function_name}")
                logger.info(f"📋 [{idx}] Arguments: {json.dumps(function_args, ensure_ascii=False)}")
                
                # Execute function
                result = await execute_function_call(function_name, function_args, phone_number)
                
                # Log result
                logger.info(f"✅ [{idx}] Result: {json.dumps(result, ensure_ascii=False)[:200]}...")
                
                # Add to function responses
                function_responses.append(types.Part(
                    function_response=types.FunctionResponse(
                        name=function_name,
                        response={"result": result}
                    )
                ))
            
            # Send all function results back to AI for continuation
            contents.append(response.candidates[0].content)
            contents.append(types.Content(
                role="user",
                parts=function_responses
            ))
            
            logger.info(f"🤖 ═══ SENDING FUNCTION RESULTS TO GEMINI ═══")
            logger.info(f"📤 Sending {len(function_responses)} function result(s) back to AI")
            
            # Get final response from AI
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=contents,
                config=config
            )
            
            logger.info(f"🤖 ═══ FINAL RESPONSE FROM GEMINI ═══")
            
            # Validate final response has candidates
            if not response.candidates or len(response.candidates) == 0:
                logger.error(f"❌ No candidates in final Gemini response. Response: {response}")
                if hasattr(response, 'prompt_feedback'):
                    logger.error(f"⚠️ Prompt feedback: {response.prompt_feedback}")
                return "מצטער, התקבלה שגיאה בעיבוד התשובה הסופית. אנא נסה שוב."
        
        # Get final text response
        try:
            ai_response = response.text if hasattr(response, 'text') and response.text else ""
        except Exception as e:
            logger.warning(f"⚠️ Could not extract text from response: {e}")
            ai_response = ""
        
        # Check if function results contain ready-made response
        # If so, use it instead of AI's text!
        ready_made_response = None
        if function_calls_found:
            # Check the last function result for 'message' field
            for fc in function_calls_found:
                fname = fc.name
                if fname == "update_user_records":
                    # The function returned a ready-made message
                    # Extract it from the result (stored earlier)
                    # We need to re-execute to get the message (or store it)
                    pass  # We'll use the result we already have
        
        # For now, just use AI response but log if it's different
        # TODO: In future, prefer function message over AI text
        
        # Log final AI response
        logger.info(f"💬 ═══ AI FINAL TEXT ═══")
        logger.info(f"📤 Response to user: {ai_response if ai_response else '(empty - using fallback)'}")
        
        # Send response to user
        if ai_response:
            await send_whatsapp_message(phone_number, ai_response)
            await add_message_to_history(phone_number, "assistant", ai_response)
            logger.info(f"✅ Message sent successfully to {phone_number}")
        else:
            # Send a default message
            default_message = "הבקשה שלך התקבלה ונשמרה במערכת! ✅"
            await send_whatsapp_message(phone_number, default_message)
            await add_message_to_history(phone_number, "assistant", default_message)
            logger.info(f"✅ Default message sent to {phone_number}")
    
    except Exception as e:
        logger.error(f"❌ Error in AI processing: {str(e)}", exc_info=True)
        await send_whatsapp_message(phone_number, ERROR_MESSAGE_HEBREW)
