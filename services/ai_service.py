"""AI service using Gemini 2.0 Flash"""
import logging
from google import genai
from google.genai import types
from config import GEMINI_API_KEY

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """אתה עוזר חכם למערכת טרמפים של גברעם.

תפקידך: לעזור למשתמשים להזין מידע בצורה טבעית.

זיהוי תפקידים - חשוב מאוד!
- נהג (driver): משתמש שאומר "אני נוסע", "אני מגיע", "אני יוצא" - הוא מציע נסיעה!
  * נסיעה קבועה: destination, days ["Sunday", "Monday"...], departure_time
  * נסיעה חד-פעמית: destination, travel_date (YYYY-MM-DD), departure_time
- טרמפיסט (hitchhiker): משתמש שאומר "מחפש/מחפשת טרמפ", "צריך/צריכה נסיעה", "מבקש/מבקשת טרמפ"
  * תמיד חד-פעמי: destination, travel_date (YYYY-MM-DD), departure_time

זמנים יחסיים (חשב לפי התאריך והשעה הנוכחית):
תאריכים:
- "עכשיו"/"בזמן הקרוב"/"בשעה הקרובה"/"בקרוב" → תאריך של היום
- "היום" → תאריך של היום
- "מחר" → תאריך של מחר (+1 יום)
- "מחרתיים" → (+2 ימים)
- "יום ראשון הבא" → חשב את התאריך

שעות:
- "עכשיו"/"בזמן הקרוב"/"בשעה הקרובה"/"בקרוב" → השעה הנוכחית (עיגול כלפי מעלה)
- "בבוקר" → 08:00
- "בצהריים"/"צהריים" → 12:00
- "אחרי הצהריים"/"אחה״צ" → 14:00
- "בערב" → 18:00
- "בלילה" → 20:00

ימים בשבוע (תרגם לאנגלית):
- ראשון → Sunday, שני → Monday, שלישי → Tuesday, וכו'
- "כל יום" / "כל הימים" → [Sunday, Monday, Tuesday, Wednesday, Thursday, Friday, Saturday]
- "ימים א-ה" → [Sunday, Monday, Tuesday, Wednesday, Thursday]

כללי זיהוי חשובים:
1. "אני נוסע/נוסעת/מגיע/מגיעה/יוצא/יוצאת" = נהג (driver)
2. "מחפש/מחפשת/מבקש/מבקשת/צריך/צריכה טרמפ/נסיעה" = טרמפיסט (hitchhiker)
3. "חוזר/חוזרת לקיבוץ/לגברעם מX" = נהג עם origin=X, destination="גברעם" (רק נהגים!)
4. "וחוזר ב-X" / "וחוזר בשעה X" = return_trip=true, return_time=X (יוצר 2 נסיעות)
5. ביטויי זמן יחסי:
   - "בזמן הקרוב"/"בקרוב"/"עכשיו"/"בשעה הקרובה" = היום (travel_date=היום)
   - אם לא צוינה שעה מפורשת → השתמש בברירת מחדל 08:00

הבדל חשוב בין טרמפ לבקשה:
- טרמפ/נסיעה = driver (נהג שמציע נסיעה)
- בקשה = hitchhiker (טרמפיסט שמחפש נסיעה)
כשהמשתמש אומר "מחק את הנסיעה/טרמפ לX" → role="driver"
כשהמשתמש אומר "מחק את הבקשה לX" → role="hitchhiker"

התנהגות - חשוב מאוד!
1. לטרמפיסטים: **חובה** לשלוח travel_date (אף פעם לא days)
2. לנהגים חד-פעמיים: **חובה** לשלוח travel_date (לא days)
3. לנהגים קבועים: **חובה** לשלוח days (לא travel_date)
4. אם יש את כל המידע → **קרא מיד ל-update_user_records ללא אישורים!**
5. אם חסר מידע → שאל רק את מה שחסר

זיהוי origin ו-destination:
- אם אומרים "מX" או "מאיזורX" → origin=X
- אם אומרים "לY" → destination=Y
- אם אומרים רק "מX" בלי יעד → origin=X, destination="גברעם" (ברירת מחדל)
- אם אומרים רק "לY" בלי מוצא → origin="גברעם" (ברירת מחדל), destination=Y
- דוגמאות:
  * "מאשדוד" = origin="אשדוד", destination="גברעם"
  * "לירושלים" = origin="גברעם", destination="ירושלים"
  * "מתל אביב לחיפה" = origin="תל אביב", destination="חיפה"

דבר בעברית, ידידותי וקצר.

עכשיו דוגמאות למידה:

דוגמה 1:
משתמש: "מבקש טרמפ למחר בבוקר לאשקלון"
אתה: [קורא ל-update_user_records עם: role="hitchhiker", destination="אשקלון", travel_date="2026-01-02", departure_time="08:00"]

דוגמה 2:
משתמש: "אני נוסע לירושלים בימים א-ה בשעה 8"
אתה: [קורא ל-update_user_records עם: role="driver", destination="ירושלים", days=["Sunday","Monday","Tuesday","Wednesday","Thursday"], departure_time="08:00"]

דוגמה 3:
משתמש: "אני נוסע מחרתיים לאילת בשעה 10"
אתה: [קורא ל-update_user_records עם: role="driver", destination="אילת", travel_date="2026-01-03", departure_time="10:00"]

דוגמה 4 - צפייה ברשימה:
משתמש: "איזה נסיעות יש לי?"
אתה: [קורא ל-view_user_records]

דוגמה 5 - עדכון:
משתמש: "תעדכן נסיעה 2 לשעה 15"
אתה: [קורא ל-update_user_record עם: role="driver", record_number=2, departure_time="15:00"]

דוגמה 6 - מחיקה:
משתמש: "תמחק נסיעה 1"
אתה: [קורא ל-delete_user_record עם: role="driver", record_number=1]

דוגמה 7 - מחיקת הכל:
משתמש: "מחק את כל הבקשות"
אתה: [קורא ל-delete_all_user_records עם: role="hitchhiker"]

דוגמה 7.1 - מחיקת הכל (שגיאה נפוצה!):
משתמש: "מחק את הבקשה לאילת" (אבל בבדיקה ברשימה - אילת היא טרמפ, לא בקשה!)
אתה: [קורא ל-delete_user_record עם: role="driver", record_number=1]
חשוב: תמיד תבדוק ברשימה אם זה באמת טרמפ או בקשה!

דוגמה 8 - נהג חוזר (כיוון הפוך):
משתמש: "אני חוזר לקיבוץ מאשקלון מחר בשעה 10"
אתה: [קורא ל-update_user_records עם: role="driver", origin="אשקלון", destination="גברעם", travel_date="2026-01-03", departure_time="10:00"]

דוגמה 9 - נהג הלוך-שוב חד-פעמי:
משתמש: "אני נוסע לבאר שבע מחר בשעה 8 וחוזר ב-10"
אתה: [קורא ל-update_user_records עם: role="driver", origin="גברעם", destination="באר שבע", travel_date="2026-01-03", departure_time="08:00", return_trip=true, return_time="10:00"]

דוגמה 10 - נהג הלוך-שוב קבוע:
משתמש: "אני נוסע לבאר שבע כל יום בשעה 8 וחוזר ב-10"
אתה: [קורא ל-update_user_records עם: role="driver", origin="גברעם", destination="באר שבע", days=["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"], departure_time="08:00", return_trip=true, return_time="10:00"]

דוגמה 11 - טרמפיסט מחפש "מX" (origin מפורש):
משתמש: "מחפשת טרמפ בזמן הקרוב מאשדוד"
אתה: [קורא ל-update_user_records עם: role="hitchhiker", origin="אשדוד", destination="גברעם", travel_date="2026-01-02", departure_time="08:00"]
הסבר: "מאשדוד" = origin, "גברעם" = destination (ברירת מחדל)

דוגמה 12 - טרמפיסט מחפש "לY" (destination מפורש):
משתמש: "מחפש טרמפ לירושלים מחר בבוקר"
אתה: [קורא ל-update_user_records עם: role="hitchhiker", origin="גברעם", destination="ירושלים", travel_date="2026-01-03", departure_time="08:00"]
הסבר: "לירושלים" = destination, "גברעם" = origin (ברירת מחדל)

דוגמה 13 - טרמפיסט מחפש "בזמן הקרוב/בקרוב":
משתמש: "מחפשת טרמפ בזמן הקרוב מאשדוד"
אתה: [קורא ל-update_user_records עם: role="hitchhiker", origin="אשדוד", destination="גברעם", travel_date="2026-01-02", departure_time="08:00"]
הסבר: "בזמן הקרוב" = היום, שעה קרובה (ברירת מחדל 08:00 אם לא צוין). "מאשדוד" = origin

חשוב: 
- אל תכתב את שם הפונקציה בטקסט! תקרא לפונקציה ישירות!
- לעדכון ומחיקה: המשתמש צריך לדעת את המספר מהרשימה (view_user_records)
- "חוזר" רק לנהגים! טרמפיסטים צריכים להגיד מפורש "מחפש טרמפ מX לY"
- כש-return_trip=true, המערכת תיצור אוטומטית 2 נסיעות (הלוך וחזור)
"""

# Function declarations
FUNCTIONS = [
    {
        "name": "update_user_records",
        "description": "שמירת טרמפ של נהג או בקשה של טרמפיסט. חובה לשלוח role + destination + departure_time + (travel_date או days). אל תשאל אישורים - פשוט קרא לפונקציה!",
        "parameters": {
            "type": "object",
            "properties": {
                "role": {
                    "type": "string",
                    "enum": ["driver", "hitchhiker"],
                    "description": "driver או hitchhiker"
                },
                "destination": {
                    "type": "string",
                    "description": "יעד הנסיעה"
                },
                "days": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "ימים באנגלית: Sunday, Monday, Tuesday, Wednesday, Thursday, Friday, Saturday. לנהגים קבועים בלבד! אם הנהג אומר 'כל יום' שלח את כל 7 הימים."
                },
                "travel_date": {
                    "type": "string",
                    "description": "תאריך בפורמט YYYY-MM-DD. חובה לטרמפיסטים! גם נהגים חד-פעמיים צריכים travel_date (לא days)."
                },
                "departure_time": {
                    "type": "string",
                    "description": "שעה בפורמט HH:MM (24 שעות)"
                },
                "origin": {
                    "type": "string",
                    "description": "מוצא הנסיעה. ברירת מחדל: 'גברעם'. דוגמאות: 'חוזר מX' → origin=X, destination='גברעם'; 'מחפש טרמפ מX' → origin=X, destination='גברעם'; 'מאשדוד' → origin='אשדוד', destination='גברעם'"
                },
                "return_trip": {
                    "type": "boolean",
                    "description": "האם זו נסיעת הלוך-שוב? true אם המשתמש אומר 'וחוזר ב-X' או 'וחוזר בשעה X'. המערכת תיצור אוטומטית שני records (הלוך וחזור)"
                },
                "return_time": {
                    "type": "string",
                    "description": "שעת חזרה בפורמט HH:MM (רק אם return_trip=true). זו השעה שבה הנהג חוזר מהיעד למוצא"
                }
            },
            "required": ["role", "destination", "departure_time"]
        }
    },
    {
        "name": "view_user_records",
        "description": "הצגת כל הטרמפים והבקשות של המשתמש",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "delete_user_record",
        "description": "מחיקת נסיעה או בקשה לפי מספר סידורי מהרשימה (המשתמש צריך לראות רשימה קודם)",
        "parameters": {
            "type": "object",
            "properties": {
                "role": {
                    "type": "string",
                    "enum": ["driver", "hitchhiker"],
                    "description": "driver או hitchhiker"
                },
                "record_number": {
                    "type": "integer",
                    "description": "מספר הנסיעה ברשימה (1, 2, 3...). המשתמש רואה את המספר בתגובה ל-view_user_records"
                }
            },
            "required": ["role", "record_number"]
        }
    },
    {
        "name": "delete_all_user_records",
        "description": "מחיקת כל הטרמפים או כל הבקשות של המשתמש. השתמש בזה רק כשהמשתמש אומר בבירור 'מחק את כל...'",
        "parameters": {
            "type": "object",
            "properties": {
                "role": {
                    "type": "string",
                    "enum": ["driver", "hitchhiker"],
                    "description": "driver (טרמפים/נסיעות) או hitchhiker (בקשות)"
                }
            },
            "required": ["role"]
        }
    },
    {
        "name": "update_user_record",
        "description": "עדכון נסיעה או בקשה קיימת לפי מספר סידורי. אפשר לעדכן יעד, שעה, תאריך או ימים. חובה לציין לפחות שדה אחד לעדכון!",
        "parameters": {
            "type": "object",
            "properties": {
                "role": {
                    "type": "string",
                    "enum": ["driver", "hitchhiker"],
                    "description": "driver או hitchhiker"
                },
                "record_number": {
                    "type": "integer",
                    "description": "מספר הנסיעה ברשימה (1, 2, 3...)"
                },
                "destination": {
                    "type": "string",
                    "description": "יעד חדש (אופציונלי)"
                },
                "departure_time": {
                    "type": "string",
                    "description": "שעה חדשה בפורמט HH:MM (אופציונלי)"
                },
                "travel_date": {
                    "type": "string",
                    "description": "תאריך חדש בפורמט YYYY-MM-DD (אופציונלי, רק לנסיעות חד-פעמיות)"
                },
                "days": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "ימים חדשים באנגלית (אופציונלי, רק לנסיעות קבועות)"
                }
            },
            "required": ["role", "record_number"]
        }
    }
]

async def process_message_with_ai(phone_number: str, message_text: str, user_data: dict, is_new_user: bool = False):
    """Process message with Gemini AI"""
    from database import add_message_to_history
    from whatsapp.whatsapp_service import send_whatsapp_message
    from services.function_handlers import (
        handle_update_user_records,
        handle_view_user_records,
        handle_delete_user_record,
        handle_delete_all_user_records,
        handle_update_user_record
    )
    from datetime import datetime
    
    if not GEMINI_API_KEY:
        await send_whatsapp_message(phone_number, "מצטער, שירות ה-AI לא זמין כרגע")
        return
    
    # Add current date/time context for the AI
    now = datetime.now()
    current_context = f"\n\n[מידע נוכחי: תאריך היום: {now.strftime('%Y-%m-%d')}, שעה: {now.strftime('%H:%M')}, יום: {now.strftime('%A')}]"
    
    # Build chat history
    history = user_data.get("chat_history", [])[-10:]  # Last 10 messages
    messages = [{"role": msg["role"], "parts": [{"text": msg["content"]}]} for msg in history]
    messages.append({"role": "user", "parts": [{"text": message_text + current_context}]})
    
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        # Call Gemini with function calling preference
        response = client.models.generate_content(
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
            if func_name == "update_user_records":
                result = await handle_update_user_records(phone_number, func_args)
            elif func_name == "view_user_records":
                result = await handle_view_user_records(phone_number)
            elif func_name == "delete_user_record":
                result = await handle_delete_user_record(phone_number, func_args)
            elif func_name == "delete_all_user_records":
                result = await handle_delete_all_user_records(phone_number, func_args)
            elif func_name == "update_user_record":
                result = await handle_update_user_record(phone_number, func_args)
            else:
                result = {"message": "פונקציה לא מוכרת"}
            
            reply = result.get("message", "בוצע!")
        else:
            # Regular text response
            reply = first_part.text if hasattr(first_part, 'text') else "קיבלתי!"
        
        # Send reply
        await send_whatsapp_message(phone_number, reply)
        
        # Save to history
        await add_message_to_history(phone_number, "user", message_text)
        await add_message_to_history(phone_number, "assistant", reply)
        
    except Exception as e:
        logger.error(f"AI error: {e}", exc_info=True)
        await send_whatsapp_message(phone_number, "מצטער, הייתה בעיה. נסה שוב")
