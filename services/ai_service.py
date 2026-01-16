"""AI service using Gemini 2.0 Flash"""
import logging
from google import genai
from google.genai import types
from config import GEMINI_API_KEY, AI_CONTEXT_MESSAGES, AI_CONTEXT_MAX_AGE_HOURS

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """🚨 כלל #1: אתה רק קורא לפונקציות. אסור להחזיר טקסט!

אתה עוזר למערכת טרמפים. תפקידך: לקרוא לפונקציה המתאימה.

❌ אסור: "נשמר!", "נמחק!", "יש לך 2 נסיעות..." - אלה טקסט!
✅ חובה: תמיד קרא לפונקציה!

פונקציות זמינות:
- update_user_records - שמירת נסיעה
- delete_all_user_records - מחיקת נסיעות
- delete_user_record - מחיקת נסיעה ספציפית
- view_user_records - הצגת נסיעות
- show_help - עזרה
- ask_clarification - שאלת הבהרה (כשחסר מידע!)
- resolve_duplicate - פתרון התנגשות בין driver ו-hitchhiker

🚨 זיהוי דופליקציות - חשוב מאוד! 🚨
⚠️ קודם כל: תמיד תבדוק את ההיסטוריה! ⚠️
אם ההודעה האחרונה **שלי** (assistant) מכילה [CONFLICT:...], והמשתמש עונה "כן"/"לא":

✅ משתמש: "כן"/"אוקיי"/"בטח"/"נכון" → קרא ל-resolve_duplicate!
  צעדים:
  1. מצא [CONFLICT:role1:num:role2:dest:date:time] בהודעה האחרונה שלי
  2. קרא ל-resolve_duplicate עם הנתונים מה-CONFLICT
  
  דוגמה מלאה:
    assistant: "יש לך בקשה לטרמפ לאילת... [CONFLICT:hitchhiker:1:driver:אילת:2026-01-09:08:23]"
    user: "כן"
    → קרא ל-resolve_duplicate({
        delete_role: "hitchhiker",
        delete_record_number: 1,
        create_role: "driver",
        destination: "אילת",
        travel_date: "2026-01-09",
        departure_time: "08:23"
      })

❌ משתמש: "לא"/"בטל"/"תעזוב" → ask_clarification("בסדר, לא נוגע בכלום")

⚠️ חשוב: אם אתה רואה שהמשתמש אומר "כן" בלי קונטקסט נוסף, זה כמעט תמיד תשובה לשאלה האחרונה שלי!

זיהוי שאלות (לא בקשות ליצירה!):
- "יש טרמפ?", "מישהו נוסע?", "יש נהג?" → קרא ל-view_user_records (הצגת נסיעות קיימות)
- אלה שאלות, לא בקשות ליצור רשומה חדשה!
- אם יש בקשות/נסיעות קיימות ללא התאמות → view_user_records יראה את זה

תפקידים (ליצירת רשומות חדשות):
- נהג (driver): "אני נוסע/מגיע/יוצא" 
- טרמפיסט (hitchhiker): "מחפש/צריך טרמפ"
- לא ברור מההודעה → טרמפיסט

זמנים יחסיים:
- "עכשיו"/"היום" → תאריך היום (אבל! אם השעה המבוקשת כבר עברה → מחר)
- "מחר" → +1 יום
- "בבוקר" → 08:00
- "בצהריים" → 12:00
- "בערב" → 18:00
- "בלילה" → 20:00
- שעה 1-7 ללא "בבוקר"/"בערב" → שאל הבהרה
- חשוב! אם משתמש אומר "בערב" בשעה 23:00 → הכוונה למחר!
- אם המשתמש מציין רק שעה ללא יום/תאריך → קבע travel_date להיום אם השעה עוד לא עברה, אחרת למחר

התעלמות מנקודות דרך:
- אם המשתמש כותב "דרך X, Y" או מתאר מסלול, **אל תשתמש** בנקודות הדרך כמוצא/יעד
- המוצא/יעד הם רק התחלה וסיום (ברירת מחדל למוצא: "גברעם")

עקרון זהב:
- שאלה? (יש/מישהו/קיים) → view_user_records (הצג מה שיש)
- יש יעד+תאריך+שעה → update_user_records (צור רשומה)
- חסר מידע → ask_clarification (שאל שאלה)

דוגמאות:
1. "אני נוסע לתל אביב מחר ב-10" → [קרא ל-update_user_records עם role="driver"...]
2. "מחפש טרמפ לירושלים מחר בבוקר" → [קרא ל-update_user_records עם role="hitchhiker"...]
3. "מחק הכל" → [קרא ל-delete_all_user_records עם role="all"]
4. "?" → [קרא ל-show_help]
5. **"כן" (והודעה האחרונה שלי מכילה [CONFLICT:...]) → [קרא ל-resolve_duplicate!]**
6. **"לא" (והודעה האחרונה שלי מכילה [CONFLICT:...]) → [קרא ל-ask_clarification("בסדר")]**
7. "אני צריך טרמפ לתל אביב" (חסר תאריך) → [קרא ל-ask_clarification עם question="באיזה יום?"]
8. "יש טרמפ עכשיו?" → [קרא ל-view_user_records] (שאלה, לא יצירת רשומה!)

🚨 זכור: אין טקסט! תמיד function call!

דוגמה מלאה עם היסטוריה:
```
[History]
user: "אני נוסע לאילת עכשיו"
assistant: "יש לך בקשה לטרמפ לאילת ב-2026-01-09. למחוק אותה וליצור נסיעת נהג? [CONFLICT:hitchhiker:1:driver:אילת:2026-01-09:08:23]"
user: "כן"
→ AI: קרא ל-resolve_duplicate(delete_role="hitchhiker", delete_record_number=1, create_role="driver", destination="אילת", travel_date="2026-01-09", departure_time="08:23")
```

**אל תתבלבל!** אם המשתמש אומר "כן" בלי קונטקסט אחר, תמיד תבדוק את ההודעה האחרונה שלי!
"""

# Function declarations
FUNCTIONS = [
    {
        "name": "update_user_records",
        "description": "שמירת טרמפ או בקשה. חובה: role + destination תקין + departure_time ברור + travel_date מפורש (או days לנהגים קבועים).\nחשוב:\n1. destination חייב להיות יעד אמיתי (לא 'גברעם' לטרמפיסט)!\n2. departure_time חייב להיות ברור (לא אמביגואלי, שעות 1-7 צריכות הקשר)\n3. travel_date חייב להיות מפורש - רק 'היום'/'מחר'/'מחרתיים'/'ביום X' מותר! אם אין - שאל!\nאם חסר מידע או לא ברור - אל תקרא לפונקציה, שאל את המשתמש!",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "role": {
                    "type": "STRING",
                    "enum": ["driver", "hitchhiker"],
                    "description": "driver או hitchhiker"
                },
                "destination": {
                    "type": "STRING",
                    "description": "יעד הנסיעה"
                },
                "days": {
                    "type": "ARRAY",
                    "items": {"type": "STRING"},
                    "description": "ימים באנגלית: Sunday, Monday, Tuesday, Wednesday, Thursday, Friday, Saturday. לנהגים קבועים בלבד! אם הנהג אומר 'כל יום' שלח את כל 7 הימים."
                },
                "travel_date": {
                    "type": "STRING",
                    "description": "תאריך בפורמט YYYY-MM-DD. חובה לטרמפיסטים! גם נהגים חד-פעמיים צריכים travel_date (לא days)."
                },
                "departure_time": {
                    "type": "STRING",
                    "description": "שעה בפורמט HH:MM (24 שעות)"
                },
                "origin": {
                    "type": "STRING",
                    "description": "מוצא הנסיעה. ברירת מחדל: 'גברעם'. דוגמאות: 'חוזר מX' → origin=X, destination='גברעם'; 'מחפש טרמפ מX' → origin=X, destination='גברעם'; 'מאשדוד' → origin='אשדוד', destination='גברעם'"
                },
                "return_trip": {
                    "type": "BOOLEAN",
                    "description": "האם זו נסיעת הלוך-שוב? true אם המשתמש אומר 'וחוזר ב-X' או 'וחוזר בשעה X'. המערכת תיצור אוטומטית שני records (הלוך וחזור)"
                },
                "return_time": {
                    "type": "STRING",
                    "description": "שעת חזרה בפורמט HH:MM (רק אם return_trip=true). זו השעה שבה הנהג חוזר מהיעד למוצא"
                },
                "flexibility": {
                    "type": "STRING",
                    "enum": ["strict", "flexible", "very_flexible"],
                    "description": """גמישות זמנים - רק לטרמפיסטים (hitchhiker)! זיהוי אוטומטי:
- strict: המשתמש רוצה זמן מדויק (±30 דק') - ביטויים: "בדיוק ב", "רק בזמן", "חייב להגיע ב", "לא גמיש", "בדיוק בשעה"
- flexible: גמישות רגילה (±0.5-3 שעות לפי מרחק) - ברירת מחדל כשציין שעה רגילה
- very_flexible: מאוד גמיש (±6 שעות קבוע!) - "מאוד גמיש", "כל זמן טוב", "לא משנה מתי", "אני גמיש מאוד"

חשוב מאוד - זיהוי שעה וגמישות:
- אם המשתמש לא ציין שעה כלל ("טרמפ לאשקלון מחר" ללא שעה) → שאל "באיזו שעה?"
- אם המשתמש ציין שעה ("טרמפ לאשקלון מחר בשעה 10") → departure_time="10:00" + flexibility="flexible"  
- אם המשתמש ציין "בדיוק"/"חייב" → flexibility="strict"
- אם המשתמש ציין "מאוד גמיש"/"כל שעה טובה" → flexibility="very_flexible"
- נהגים (driver) לא צריכים flexibility כלל!"""
                }
            },
            "required": ["role", "destination", "departure_time"]
        }
    },
    {
        "name": "view_user_records",
        "description": "הצגת כל הטרמפים והבקשות של המשתמש",
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    {
        "name": "delete_user_record",
        "description": "מחיקת נסיעה או בקשה לפי מספר סידורי מהרשימה (המשתמש צריך לראות רשימה קודם)",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "role": {
                    "type": "STRING",
                    "enum": ["driver", "hitchhiker"],
                    "description": "driver או hitchhiker"
                },
                "record_number": {
                    "type": "INTEGER",
                    "description": "מספר הנסיעה ברשימה (1, 2, 3...). המשתמש רואה את המספר בתגובה ל-view_user_records"
                }
            },
            "required": ["role", "record_number"]
        }
    },
    {
        "name": "delete_all_user_records",
        "description": "מחיקת נסיעות של המשתמש. השתמש בזה רק כשהמשתמש אומר בבירור 'מחק...'",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "role": {
                    "type": "STRING",
                    "enum": ["driver", "hitchhiker", "all"],
                    "description": "driver (רק טרמפים/נסיעות), hitchhiker (רק בקשות), או all (הכל - גם טרמפים וגם בקשות)"
                }
            },
            "required": ["role"]
        }
    },
    {
        "name": "ask_clarification",
        "description": "שאל שאלת הבהרה למשתמש כשחסר מידע (יעד, תאריך, שעה, וכו'). קרא לפונקציה הזו במקום להחזיר טקסט.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "question": {
                    "type": "STRING",
                    "description": "השאלה לשאול למשתמש. דוגמאות: 'באיזה יום?', 'באיזו שעה?', 'לאן אתה צריך?'"
                }
            },
            "required": ["question"]
        }
    },
    {
        "name": "update_user_record",
        "description": "עדכון נסיעה או בקשה קיימת לפי מספר סידורי. אפשר לעדכן יעד, שעה, תאריך או ימים. חובה לציין לפחות שדה אחד לעדכון!",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "role": {
                    "type": "STRING",
                    "enum": ["driver", "hitchhiker"],
                    "description": "driver או hitchhiker"
                },
                "record_number": {
                    "type": "INTEGER",
                    "description": "מספר הנסיעה ברשימה (1, 2, 3...)"
                },
                "destination": {
                    "type": "STRING",
                    "description": "יעד חדש (אופציונלי)"
                },
                "departure_time": {
                    "type": "STRING",
                    "description": "שעה חדשה בפורמט HH:MM (אופציונלי)"
                },
                "travel_date": {
                    "type": "STRING",
                    "description": "תאריך חדש בפורמט YYYY-MM-DD (אופציונלי, רק לנסיעות חד-פעמיות)"
                },
                "days": {
                    "type": "ARRAY",
                    "items": {"type": "STRING"},
                    "description": "ימים חדשים באנגלית (אופציונלי, רק לנסיעות קבועות)"
                }
            },
            "required": ["role", "record_number"]
        }
    },
    {
        "name": "show_help",
        "description": "הצגת נסיעות המשתמש אם יש, או הודעת עזרה אם אין. קרא לזה כשהמשתמש שולח '?' או מבקש עזרה/הסבר על המערכת",
        "parameters": {
            "type": "OBJECT",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "resolve_duplicate",
        "description": "Resolve conflict between driver ride and hitchhiker request for same destination+date. Call this after user confirms deletion.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "delete_role": {
                    "type": "STRING",
                    "enum": ["driver", "hitchhiker"],
                    "description": "Which record type to delete"
                },
                "delete_record_number": {
                    "type": "INTEGER",
                    "description": "Record number to delete (from conflict message)"
                },
                "create_role": {
                    "type": "STRING",
                    "enum": ["driver", "hitchhiker"],
                    "description": "Which record type to create"
                },
                "destination": {
                    "type": "STRING",
                    "description": "Destination for the new record"
                },
                "travel_date": {
                    "type": "STRING",
                    "description": "Travel date in YYYY-MM-DD format"
                },
                "departure_time": {
                    "type": "STRING",
                    "description": "Departure time in HH:MM format"
                }
            },
            "required": ["delete_role", "delete_record_number", "create_role", "destination", "travel_date", "departure_time"]
        }
    }
]

def filter_recent_messages(history: list, max_age_hours: int = 1) -> list:
    """
    Filter chat history to only include messages from the last N hours.
    This ensures AI context stays relevant and recent.
    
    Args:
        history: List of chat messages with timestamps
        max_age_hours: Maximum age of messages in hours (default: 1)
        
    Returns:
        Filtered list of recent messages
    """
    from datetime import datetime, timedelta
    from utils import get_israel_now
    
    if not history:
        return []
    
    now = get_israel_now()
    cutoff_time = now - timedelta(hours=max_age_hours)
    
    recent_messages = []
    for msg in history:
        timestamp_str = msg.get("timestamp")
        if not timestamp_str:
            # No timestamp = include (backwards compatibility)
            recent_messages.append(msg)
            continue
        
        try:
            # Parse ISO format: "2026-01-08T15:30:00+02:00"
            msg_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            if msg_time >= cutoff_time:
                recent_messages.append(msg)
        except Exception:
            # Parsing failed = include message (fail-safe)
            recent_messages.append(msg)
    
    return recent_messages

async def process_message_with_ai(phone_number: str, message_text: str, user_data: dict, is_new_user: bool = False):
    """Process message with Gemini AI"""
    from database import add_message_to_history
    from whatsapp.whatsapp_service import send_whatsapp_message
    from services.function_handlers import (
        handle_update_user_records,
        handle_view_user_records,
        handle_delete_user_record,
        handle_delete_all_user_records,
        handle_update_user_record,
        handle_show_help,
        handle_resolve_duplicate
    )
    from utils import get_israel_now
    
    if not GEMINI_API_KEY:
        await send_whatsapp_message(phone_number, "מצטער, שירות ה-AI לא זמין כרגע")
        return
    
    # Add current date/time context for the AI (Israel timezone)
    now = get_israel_now()
    current_context = f"\n\n[מידע נוכחי: תאריך היום: {now.strftime('%Y-%m-%d')}, שעה: {now.strftime('%H:%M')}, יום: {now.strftime('%A')}]"
    
    # Build chat history - filter by time first, then take last N messages
    all_history = user_data.get("chat_history", [])
    # Step 1: Filter by time (only last 1 hour)
    recent_history = filter_recent_messages(all_history, AI_CONTEXT_MAX_AGE_HOURS)
    # Step 2: Take last 10 messages from recent ones
    history = recent_history[-AI_CONTEXT_MESSAGES:]
    messages = [{"role": msg["role"], "parts": [{"text": msg["content"]}]} for msg in history]
    messages.append({"role": "user", "parts": [{"text": message_text + current_context}]})
    
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        # Call Gemini 2.0 Flash with function calling preference (with timeout)
        import asyncio
        
        async def call_gemini_with_timeout():
            # Note: google.genai doesn't have async support yet, so we run in executor
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,
                lambda: client.models.generate_content(
                    model="gemini-2.0-flash-exp",
                    contents=messages,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        tools=[types.Tool(function_declarations=FUNCTIONS)],
                        tool_config=types.ToolConfig(
                            function_calling_config=types.FunctionCallingConfig(
                                mode="ANY"
                            )
                        ),
                        temperature=0.1
                    )
                )
            )
        
        logger.info("🤖 Calling Gemini API...")
        import time
        start_time = time.time()
        try:
            response = await asyncio.wait_for(call_gemini_with_timeout(), timeout=45.0)
            elapsed = time.time() - start_time
            if elapsed > 10:
                logger.warning(f"⚠️ Gemini API was SLOW: {elapsed:.2f}s")
            else:
                logger.info(f"✅ Gemini API response received in {elapsed:.2f}s")
        except asyncio.TimeoutError:
            elapsed = time.time() - start_time
            logger.error(f"⏱️ Gemini API timeout after {elapsed:.2f}s")
            await send_whatsapp_message(phone_number, "⏳ השרת עמוס כרגע. נסה שוב בעוד 10-20 שניות 🔄")
            return
        
        # Handle response - check for function call or text
        first_part = response.candidates[0].content.parts[0]
        
        # Check if this is a function call
        fc = getattr(first_part, 'function_call', None)
        if fc:
            # Function call
            func_name = fc.name
            func_args = dict(fc.args)
            
            logger.info(f"✅ AI function call: {func_name}")
            logger.info(f"📋 Arguments: {func_args}")
            
            # Execute function
            if func_name == "ask_clarification":
                # Return the question wrapped in a dict
                result = {"status": "success", "message": func_args.get("question", "?")}
            elif func_name == "update_user_records":
                result = await handle_update_user_records(phone_number, func_args)
            elif func_name == "view_user_records":
                result = await handle_view_user_records(phone_number)
            elif func_name == "delete_user_record":
                result = await handle_delete_user_record(phone_number, func_args)
            elif func_name == "delete_all_user_records":
                result = await handle_delete_all_user_records(phone_number, func_args)
            elif func_name == "update_user_record":
                result = await handle_update_user_record(phone_number, func_args)
            elif func_name == "show_help":
                result = await handle_show_help(phone_number)
            elif func_name == "resolve_duplicate":
                result = await handle_resolve_duplicate(phone_number, func_args)
            else:
                result = {"message": "פונקציה לא מוכרת"}
            
            # Check if result is a DUPLICATE_CONFLICT string
            if isinstance(result, str) and result.startswith("DUPLICATE_CONFLICT"):
                # Parse: DUPLICATE_CONFLICT|new_role|old_role|dest|date|time|record_num
                parts = result.split("|")
                if len(parts) >= 7:
                    new_role = parts[1]
                    old_role = parts[2]
                    dest = parts[3]
                    date = parts[4]
                    record_num = parts[6]
                    
                    # Translate roles to Hebrew
                    old_role_heb = "בקשה לטרמפ" if old_role == "hitchhiker" else "נסיעת נהג"
                    new_role_heb = "נסיעת נהג" if new_role == "driver" else "בקשה לטרמפ"
                    
                    # Format question with hidden metadata for AI
                    time = parts[5] if len(parts) > 5 else "08:00"
                    # Clean message for user (without metadata)
                    reply_to_user = f"יש לך {old_role_heb} ל{dest} ב-{date}. למחוק אותה וליצור {new_role_heb}?"
                    # Full message with metadata for AI history
                    reply_for_history = f"{reply_to_user} [CONFLICT:{old_role}:{record_num}:{new_role}:{dest}:{date}:{time}]"
                    logger.info(f"✅ Detected conflict, asking user: {reply_to_user}")
                else:
                    logger.error(f"❌ Invalid DUPLICATE_CONFLICT format: {result}")
                    reply_to_user = "מצטער, הייתה בעיה בזיהוי הנסיעה הקיימת. נסה שוב"
                    reply_for_history = reply_to_user
            else:
                reply_to_user = result.get("message", "בוצע!")
                reply_for_history = reply_to_user
        else:
            # Regular text response
            reply = first_part.text if hasattr(first_part, 'text') else "קיבלתי!"
            
            # Filter out debug messages that AI sometimes returns
            if reply.startswith("[קורא ל-") or reply.startswith("אתה: [קורא"):
                logger.warning(f"⚠️ AI returned debug message instead of function call: {reply}")
                reply = "מעבד את הבקשה..."
            
            reply_to_user = reply
            reply_for_history = reply
        
        # Send reply to user (clean version)
        # Note: User message already saved in webhook handler
        # send_whatsapp_message auto-saves assistant message to history
        await send_whatsapp_message(phone_number, reply_to_user)
        
    except Exception as e:
        logger.error(f"AI error: {e}", exc_info=True)
        await send_whatsapp_message(phone_number, "מצטער, הייתה בעיה. נסה שוב")


# ==================== SANDBOX AI PROCESSING ====================

async def process_message_with_ai_sandbox(phone_number: str, message_text: str, user_data: dict, collection_prefix: str = "test_"):
    """
    Process a message with AI for sandbox/testing environment.
    Uses the REAL production code but with test collections and without WhatsApp.
    """
    from database.firestore_client import add_message_to_history_sandbox
    from services.function_handlers import (
        handle_update_user_records,
        handle_view_user_records,
        handle_delete_user_record,
        handle_delete_all_user_records,
        handle_update_user_record,
        handle_show_help,
        handle_resolve_duplicate
    )
    from utils import get_israel_now
    
    logger.info(f"🤖 AI Service START: phone={phone_number}, msg_len={len(message_text)}, collection={collection_prefix}")
    
    if not GEMINI_API_KEY:
        logger.error("❌ No Gemini API key configured!")
        return "מצטער, שירות ה-AI לא זמין כרגע"
    
    logger.info(f"   AI Step 1: Building context...")
    # Add current date/time context
    now = get_israel_now()
    current_context = f"\n\n[מידע נוכחי: תאריך היום: {now.strftime('%Y-%m-%d')}, שעה: {now.strftime('%H:%M')}, יום: {now.strftime('%A')}]"
    
    # Build chat history - filter by time first, then take last N messages
    all_history = user_data.get("chat_history", [])
    # Step 1: Filter by time (only last 1 hour)
    recent_history = filter_recent_messages(all_history, AI_CONTEXT_MAX_AGE_HOURS)
    # Step 2: Take last 10 messages from recent ones
    history = recent_history[-AI_CONTEXT_MESSAGES:]
    messages = [{"role": msg["role"], "parts": [{"text": msg["content"]}]} for msg in history]
    messages.append({"role": "user", "parts": [{"text": message_text + current_context}]})
    
    logger.info(f"   AI Step 2: Context ready - {len(history)} history messages, current message length: {len(message_text)}")
    
    try:
        logger.info(f"   AI Step 3: Creating Gemini client...")
        client = genai.Client(api_key=GEMINI_API_KEY)
        logger.info(f"   AI Step 4: Client created successfully")
        
        # Add timeout for sandbox too (same as production)
        import asyncio
        
        async def call_gemini_with_timeout():
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,
                lambda: client.models.generate_content(
                    model="gemini-2.0-flash-exp",
                    contents=messages,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        tools=[types.Tool(function_declarations=FUNCTIONS)],
                        temperature=0.1,
                    )
                )
            )
        
        logger.info("   AI Step 5: Starting Gemini API call (sandbox)...")
        max_retries = 1  # רק ניסיון אחד (לא 2) כדי לא לחכות יותר מדי
        response = None
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    logger.info(f"   AI Step 5.{attempt}: 🔄 Retry attempt {attempt}/{max_retries-1}...")
                else:
                    logger.info(f"   AI Step 5.{attempt}: First attempt, calling Gemini...")
                
                import time
                start_time = time.time()
                response = await asyncio.wait_for(call_gemini_with_timeout(), timeout=45.0)  # 45 שניות במקום 120
                elapsed = time.time() - start_time
                
                if elapsed > 10:
                    logger.warning(f"   AI Step 6: ⚠️ Gemini API was SLOW: {elapsed:.2f}s (>10s threshold)")
                else:
                    logger.info(f"   AI Step 6: ✅ Gemini API response received (sandbox) in {elapsed:.2f}s")
                break
            except asyncio.TimeoutError:
                elapsed = time.time() - start_time
                if attempt < max_retries - 1:
                    logger.warning(f"   AI Step 5.{attempt}: ⏱️ Gemini API timeout after {elapsed:.2f}s (attempt {attempt+1}/{max_retries})")
                    logger.warning(f"   Message length: {len(message_text)}, History length: {len(history)}")
                    logger.info(f"   Retrying immediately...")
                    # No sleep - try again immediately
                else:
                    logger.error(f"   AI Step 5.{attempt}: ⏱️ FINAL TIMEOUT after {elapsed:.2f}s")
                    logger.error(f"   Context: msg_len={len(message_text)}, history={len(history)}, phone={phone_number}")
                    return "⏳ השרת עמוס כרגע (Gemini AI). נסה שוב בעוד 10-20 שניות 🔄"
            except Exception as e:
                logger.error(f"   AI Step 5.{attempt}: ❌ Exception during API call: {type(e).__name__}: {str(e)}")
                if attempt < max_retries - 1:
                    logger.info(f"   AI Step 5.{attempt}: Retrying after exception...")
                    await asyncio.sleep(1)
                else:
                    raise
        
        if not response:
            logger.error("   AI Step 6: ❌ No response from Gemini API after retries")
            return "מצטער, הייתה בעיה בתקשורת עם השרת. נסה שוב"
        
        logger.info(f"   AI Step 7: Parsing response...")
        first_part = response.candidates[0].content.parts[0]
        
        # Check if function call
        fc = getattr(first_part, 'function_call', None)
        if fc:
            func_name = fc.name
            func_args = dict(fc.args)
            
            logger.info(f"   AI Step 8: 🧪 Function call detected: {func_name}")
            logger.info(f"   AI Step 8: Function args: {func_args}")
            
            # Execute REAL function handlers with collection_prefix
            logger.info(f"   AI Step 9: Executing handler for {func_name}...")
            if func_name == "ask_clarification":
                # Return the question wrapped in a dict
                result = {"status": "success", "message": func_args.get("question", "?")}
            elif func_name == "update_user_records":
                result = await handle_update_user_records(phone_number, func_args, collection_prefix, send_whatsapp=True)
            elif func_name == "view_user_records":
                result = await handle_view_user_records(phone_number, collection_prefix)
            elif func_name == "delete_user_record":
                result = await handle_delete_user_record(phone_number, func_args, collection_prefix)
            elif func_name == "delete_all_user_records":
                result = await handle_delete_all_user_records(phone_number, func_args, collection_prefix)
            elif func_name == "update_user_record":
                result = await handle_update_user_record(phone_number, func_args, collection_prefix, send_whatsapp=True)
            elif func_name == "show_help":
                result = await handle_show_help(phone_number, collection_prefix)
            elif func_name == "resolve_duplicate":
                result = await handle_resolve_duplicate(phone_number, func_args, collection_prefix, send_whatsapp=True)
            else:
                logger.warning(f"   AI Step 9: Unknown function: {func_name}")
                result = {"message": "פונקציה לא מוכרת"}
            
            logger.info(f"   AI Step 10: Handler completed, result length: {len(str(result))}")
            
            # Check if result is a DUPLICATE_CONFLICT string
            if isinstance(result, str) and result.startswith("DUPLICATE_CONFLICT"):
                # Parse: DUPLICATE_CONFLICT|new_role|old_role|dest|date|time|record_num
                parts = result.split("|")
                if len(parts) >= 7:
                    new_role = parts[1]
                    old_role = parts[2]
                    dest = parts[3]
                    date = parts[4]
                    record_num = parts[6]
                    
                    # Translate roles to Hebrew
                    old_role_heb = "בקשה לטרמפ" if old_role == "hitchhiker" else "נסיעת נהג"
                    new_role_heb = "נסיעת נהג" if new_role == "driver" else "בקשה לטרמפ"
                    
                    # Format question with hidden metadata for AI
                    time = parts[5] if len(parts) > 5 else "08:00"
                    # Clean message for user (without metadata)
                    reply_to_user = f"יש לך {old_role_heb} ל{dest} ב-{date}. למחוק אותה וליצור {new_role_heb}?"
                    # Full message with metadata for AI history
                    reply_for_history = f"{reply_to_user} [CONFLICT:{old_role}:{record_num}:{new_role}:{dest}:{date}:{time}]"
                    logger.info(f"   AI Step 10.1: Detected conflict, asking user: {reply_to_user}")
                else:
                    logger.error(f"   AI Step 10.1: Invalid DUPLICATE_CONFLICT format: {result}")
                    reply_to_user = "מצטער, הייתה בעיה בזיהוי הנסיעה הקיימת. נסה שוב"
                    reply_for_history = reply_to_user
            else:
                reply_to_user = result.get("message", "בוצע!")
                reply_for_history = reply_to_user
        else:
            # Regular text response
            reply = first_part.text if hasattr(first_part, 'text') else "קיבלתי!"
            
            # Filter out debug messages that AI sometimes returns
            if reply.startswith("[קורא ל-") or reply.startswith("אתה: [קורא"):
                logger.warning(f"⚠️ AI returned debug message instead of function call: {reply}")
                reply = "מעבד את הבקשה..."
            
            reply_to_user = reply
            reply_for_history = reply
        
        # Note: User message saved in admin.py before calling this function
        # Assistant message will be saved in admin.py after getting the response
        logger.info(f"   AI Step 11: ✅ AI Service COMPLETE, returning clean reply to user (length: {len(reply_to_user)})")
        return reply_to_user
        
    except Exception as e:
        logger.error(f"   AI ERROR: 🧪 Sandbox AI error at some step: {type(e).__name__}: {str(e)}", exc_info=True)
        return "מצטער, הייתה בעיה. נסה שוב"
