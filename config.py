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
MAX_CHAT_HISTORY = 20
DEFAULT_NOTIFICATION_LEVEL = "all"

# Messages
WELCOME_MESSAGE = """שלום {name}! 👋

ברוך הבא למערכת הטרמפים של גברעם! 🚗

🎒 מחפש טרמפ? ספר לי לאן ומתי
🚗 נהג? ספר לי לאן אתה נוסע ובאיזה ימים

💡 לעזרה בכל שלב, פשוט כתוב "עזרה"

בואו נתחיל! 😊"""

HELP_MESSAGE = """📚 מדריך מערכת הטרמפים של גברעם

🚗 אם אתה נהג:
━━━━━━━━━━━━━━
📅 נסיעה קבועה:
   "אני נוסע לירושלים כל יום שלישי בשעה 8"
   "אני נוסע לתל אביב בימים א-ה ב 7:30"

📆 נסיעה חד-פעמית:
   "אני נוסע לאילת מחר בבוקר"
   "אני נוסע לבאר שבע ב-3 בינואר בשעה 10"

🔄 נסיעת הלוך-שוב:
   "אני נוסע לאשדוד מחר ב-8 וחוזר ב-17"

🎒 אם אתה טרמפיסט:
━━━━━━━━━━━━━━
🔍 חיפוש טרמפ:
   "מחפש טרמפ לחיפה מחר בבוקר"
   "צריכה נסיעה מאשקלון לגברעם היום"
   "מבקש טרמפ לירושלים ב-5 בינואר בשעה 9"

📋 ניהול הנסיעות שלך:
━━━━━━━━━━━━━━━━━
👀 צפייה ברשימה:
   "הצג את הנסיעות שלי"
   "מה יש לי?"

✏️ עדכון:
   "עדכן נסיעה 2 לשעה 15:00"
   "שנה נסיעה 1 לתאריך 10 בינואר"

🗑️ מחיקה:
   "מחק נסיעה 3"
   "מחק את כל הטרמפים שלי"
   "מחק את כל הבקשות"
   "מחק הכל"

💡 טיפים:
━━━━━━━
⏰ זמנים יחסיים:
   היום, מחר, מחרתיים
   בבוקר (8:00), בצהריים (12:00)
   אחה"צ (14:00), בערב (18:00)

🔔 התאמות אוטומטיות:
   המערכת מחפשת התאמות אוטומטית
   ומודיעה לך כשיש נהג או טרמפיסט מתאים!

━━━━━━━━━━━━━━━━━━
ℹ️ אודות המערכת:
המערכת פותחה על ידי כפיר אלגבסי 👨‍💻
כתרומה לחברי קהילת גברעם

⚠️ הצהרת אחריות:
המערכת נמצאת בפיתוח פעיל ויתכנו תקלות.
השימוש במערכת הוא באחריות המשתמש בלבד.
המפתח אינו נושא באחריות לנזקים או בעיות
שעלולות להיגרם משימוש במערכת.

❓ שאלות? פשוט כתוב "עזרה" בכל שלב!"""

NON_TEXT_MESSAGE_HEBREW = "סליחה, אני מטפל רק בהודעות טקסט 📝"

def get_welcome_message(name=None):
    return WELCOME_MESSAGE.format(name=name or "חבר")

