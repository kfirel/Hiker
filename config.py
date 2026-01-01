"""
Configuration and Constants
Central place for all configuration, environment variables, and system prompts
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ============================================================================
# Environment Variables
# ============================================================================

# WhatsApp Configuration
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "my_test_token_123")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
WHATSAPP_API_URL = f"https://graph.facebook.com/v18.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"

# Gemini AI Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-2.0-flash-exp"

# Google Cloud Configuration
GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")

# Server Configuration
PORT = int(os.getenv("PORT", 8080))

# ============================================================================
# System Messages
# ============================================================================

def get_welcome_message(name: str = None) -> str:
    """Generate personalized welcome message"""
    greeting = f"שלום {name}! 👋" if name else "שלום וברוך הבא! 🚗"
    
    return f"""{greeting}
ברוך הבא לאפליקצית הטרמפים של גברעם!

אם אתה מחפש טרמפ שלח לי הודעה בסגנון:
"אני מחפש טרמפ לתל אביב בשעה 12:00 מחר"

אם אתה נהג שרוצה לעזור:
"אני נוסע בימים א-ה לתל אביב בשעה 9 וחוזר ב-17:30"

איך אני יכול לעזור לך היום?"""

# Legacy constant for backward compatibility
WELCOME_MESSAGE = get_welcome_message()

SYSTEM_PROMPT = """אתה מנתח כוונות (Intent Parser) לאפליקציית טרמפים.
{user_name_instruction}

🎯 **תפקיד יחיד:**
זהה כוונה → קרא לפונקציה → העבר תשובה

🚨 **אסור לך:**
❌ לשאול "האם תרצה שאעדכן?"
❌ לשאול "זה נכון?"
❌ לבקש אישור למשהו שהמשתמש אמר במפורש
✅ **רק תקרא לפונקציה מיד!**

📌 **כוונות:**
"אני נוסע/ת לX" = driver → קרא update_user_records INSTANTLY
"מחפש טרמפ לX" = hitchhiker → קרא update_user_records INSTANTLY

📋 **פרמטרים:**
- destination: שם עיר (חובה)
- departure_time: "HH:MM" format
- days: ["Sunday",...] אם "כל יום" → כל 7
- travel_date: "YYYY-MM-DD" אם טרמפיסט
- origin: ברירת מחדל "גברעם"

⚡ **דוגמאות:**

משתמש: "אני נוסעת כל יום לאשקלון ב8"
אתה: [קורא לפונקציה מיד]
```
update_user_records(
  role="driver",
  destination="אשקלון", 
  departure_time="08:00",
  days=["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"]
)
```
[מחכה לתשובה מהפונקציה]
[מעביר למשתמש את ה-message שחזר]

משתמש: "מחפש טרמפ לתל אביב מחר ב9"
אתה: [קורא לפונקציה מיד]
```
update_user_records(
  role="hitchhiker",
  destination="תל אביב",
  travel_date="{current_timestamp} + 1 day",
  departure_time="09:00"
)
```

🔥 **חוקים:**
1. יעד + זמן = קריאה לפונקציה מיד (לא שאלות!)
2. התשובה מהפונקציה = התשובה למשתמש (לא לשנות!)
3. אם חסר מידע = שאל רק את החסר

הקשר: {current_timestamp} | {current_day_of_week}
"""

# ============================================================================
# Application Constants
# ============================================================================

# Default values
DEFAULT_ORIGIN = "גברעם"
DEFAULT_FLEXIBILITY = "flexible"
DEFAULT_NOTIFICATION_LEVEL = "all"

# Chat history settings
MAX_CHAT_HISTORY = 20  # Maximum messages stored in database
MAX_CONVERSATION_CONTEXT = 20  # Number of messages to send to AI

# Error messages
ERROR_MESSAGE_HEBREW = "סליחה, נתקלתי בבעיה. אנא נסה שוב. 🙏"
NON_TEXT_MESSAGE_HEBREW = "אני יכול להגיב רק להודעות טקסט כרגע 📝"

