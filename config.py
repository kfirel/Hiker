"""Configuration and constants for Hiker bot"""
import os
from dotenv import load_dotenv

load_dotenv()

# WhatsApp
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
WHATSAPP_API_URL = f"https://graph.facebook.com/v18.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "my_verify_token")

# Gemini AI
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Firestore
GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")

# App settings
PORT = int(os.getenv("PORT", 8080))
MAX_CHAT_HISTORY = 100  # Store last 100 messages in database (for admin view)
AI_CONTEXT_MESSAGES = 10  # Send up to last 10 messages to AI
AI_CONTEXT_MAX_AGE_HOURS = 1  # Only include messages from last 1 hour
DEFAULT_NOTIFICATION_LEVEL = "all"

# Test Users - These users use test collections and messages appear in Sandbox UI
TEST_USERS = [
    '972500000001',
    '972500000002', 
    '972500000003',
    '972500000004'
]

# Route Matching - Dynamic Threshold Configuration
ROUTE_PROXIMITY_MIN_THRESHOLD_KM = 1  # Minimum threshold for short routes
ROUTE_PROXIMITY_MAX_THRESHOLD_KM = 10.0  # Maximum threshold for long routes
ROUTE_PROXIMITY_SCALE_FACTOR = 4.0  # Every X km of route adds 1 km to threshold

# API Configuration
OSRM_API_URL = "http://router.project-osrm.org"
NOMINATIM_API_URL = "https://nominatim.openstreetmap.org"
NOMINATIM_USER_AGENT = "HikerApp/1.0"

# Google Maps API (optional, for better geocoding accuracy in Israel)
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")  # Add to .env for accurate geocoding

# Background Processing
ROUTE_CALC_MAX_RETRIES = 3  # Number of retry attempts
ROUTE_CALC_RETRY_DELAY = 2  # Seconds between retries

# Performance
GEOCODE_CACHE_SIZE = 200  # Number of addresses to cache
API_TIMEOUT_SECONDS = 10

# Messages
WELCOME_MESSAGE = """היי {name}! 👋
ברוך הבא לצ'אטבוט ה‑AI של גברעם 🚗🤖
אני כאן כדי לעזור לגברעמניקים למצוא ולתת טרמפים—בקלות.
דבר איתי טבעי, ואני אסדר את השאר ✨

דוגמאות זריזות:
• "נוסע לירושלים בימים א-ה ב-8 וחוזר ב-17:30"
• "נוסע מחר לתל אביב ב-10"
• "עוד רגע נוסע לאשקלון"
• "צריך טרמפ לתל אביב מחר ב-13"

נהגים? תכניסו את השגרה המשוערת ותעזרו לכולם 🙌

💡 עזרה → כתוב "עזרה"

בואו נתחיל! 😊"""

HELP_MESSAGE = """📚 מדריך טרמפים - גברעם

🚗 נהג:
  קבוע: "אני נוסע לירושלים כל יום ראשון ב-8"
  חד-פעמי: "אני נוסע לאילת מחר בבוקר"
  הלוך-שוב: "אני נוסע לאשדוד מחר ב-8 וחוזר ב-17"

🎒 טרמפיסט:
  "מחפש טרמפ לחיפה מחר בבוקר"
  "צריכה נסיעה לתל אביב היום"

❓ שואל אם יש טרמפ?
  כתוב בקשה ברורה כדי שאחפש עבורך, למשל:
  "צריך טרמפ לאילת מחר ב-9"
  או הצע נסיעה: "נוסע לאילת מחר ב-9"

📋 ניהול:
  ראה רשימה: "?" או "מה יש לי"
  עדכן: "עדכן נסיעה 2 לשעה 15:00"
  מחק: "מחק נסיעה 3" או "מחק הכל"

💡 זמנים: היום, מחר, מחרתיים, בבוקר, בערב

🔔 המערכת מחפשת התאמות אוטומטית ומודיעה לך!

━━━━━━━━━━━━━━━━━━
ℹ️ פותח ע"י כפיר אלגבסי לקהילת גברעם
⚠️ המערכת בפיתוח - השימוש באחריות המשתמש"""

NON_TEXT_MESSAGE_HEBREW = "סליחה, אני מטפל רק בהודעות טקסט 📝"

def get_welcome_message(name=None):
    return WELCOME_MESSAGE.format(name=name or "חבר")

