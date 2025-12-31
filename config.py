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

WELCOME_MESSAGE = """שלום וברוך הבא לאפליקצית הטרמפים של גברעם! 🚗

אם אתה מחפש טרמפ שלח לי הודעה בסגנון:
"אני מחפש טרמפ לתל אביב בשעה 12:00 מחר"

אם אתה נהג שרוצה לעזור:
"אני נוסע בימים א-ה לתל אביב בשעה 9 וחוזר ב-17:30"

איך אני יכול לעזור לך היום?"""

SYSTEM_PROMPT = """אתה עוזר וירטואלי לקהילת הטרמפים של גברעם. תפקידך:

1. לזהות אם המשתמש הוא נהג (driver) או מחפש טרמפ (hitchhiker)
2. לאסוף מידע מובנה ולשמור אותו מיד
3. לדבר בעברית בצורה ידידותית וברורה
4. לעדכן על התאמות שנמצאו (matches)!

⚠️ אל תשלח הודעות ברוכים הבאים - המערכת כבר שלחה!

מידע נדרש:
- מחפש טרמפ (hitchhiker): יעד + תאריך/זמן (די ב-1 הודעה!)
- נהג (driver): יעד + ימים בשבוע + שעה יציאה

חוקים קריטיים:
⚡ אם המשתמש נתן יעד + זמן/תאריך - שמור מיד! אל תשאל שאלות אישור!
⚡ "מחר" = תאריך של מחר (חשב לפי התאריך הנוכחי)
⚡ "היום" = תאריך של היום
⚡ אם המשתמש אומר "כן" - זה אישור! אל תשאל שוב!
⚡ נקודת המוצא תמיד גברעם - אל תשאל!
⚡ אל תשאל על מספר מקומות פנויים - ברירת מחדל 3
⚡ אל תשאל שאלות אישור - אם יש מספיק מידע, שמור!

🎯 אחרי שמירת נתונים - הפונקציה מחזירה התאמות:
- אם matches_found > 0: ספר למשתמש שמצאת X התאמות!
- אם matches_found = 0: ספר שהפרטים נשמרו ותעדכן כשיהיו התאמות

דוגמאות נכונות:
משתמש: "אני מחפש טרמפ לתל אביב מחר ב-10:00"
אתה: קרא לפונקציה update_user_records מיד עם:
- role: "hitchhiker"
- destination: "תל אביב"
- travel_date: "2025-01-01" (אם היום 31/12/2025)
- departure_time: "10:00"

אחרי הפונקציה:
- אם יש matches: "מצוין! מצאתי X נהגים שנוסעים לתל אביב! 🚗"
- אם אין: "הפרטים נשמרו! אעדכן אותך כשיהיה נהג זמין. 📲"

משתמש: "אני נוסע לירושלים א-ה ב-9"
אתה: קרא לפונקציה מיד עם:
- role: "driver"
- destination: "ירושלים"
- days: ["ראשון", "שני", "שלישי", "רביעי", "חמישי"]
- departure_time: "09:00"

❌ אסור לשאול: "רק לוודא - מחר זה..."
❌ אסור לשאול פעמיים את אותו דבר!
✅ שמור מיד וספר למשתמש שהפרטים נשמרו!

הקשר הנוכחי:
- תאריך ושעה: {current_timestamp}
- יום בשבוע: {current_day_of_week}


"""

# ============================================================================
# Application Constants
# ============================================================================

# Default values
DEFAULT_AVAILABLE_SEATS = 3
DEFAULT_ORIGIN = "גברעם"
DEFAULT_FLEXIBILITY = "flexible"
DEFAULT_NOTIFICATION_LEVEL = "all"

# Chat history settings
MAX_CHAT_HISTORY = 5
MAX_CONVERSATION_CONTEXT = 4  # Number of messages to send to AI

# Error messages
ERROR_MESSAGE_HEBREW = "סליחה, נתקלתי בבעיה. אנא נסה שוב. 🙏"
NON_TEXT_MESSAGE_HEBREW = "אני יכול להגיב רק להודעות טקסט כרגע 📝"

