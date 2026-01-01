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

בואו נתחיל! 😊"""

NON_TEXT_MESSAGE_HEBREW = "סליחה, אני מטפל רק בהודעות טקסט 📝"

def get_welcome_message(name=None):
    return WELCOME_MESSAGE.format(name=name or "חבר")

