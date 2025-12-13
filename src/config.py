import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Configuration class for WhatsApp Bot"""
    
    # WhatsApp Cloud API Configuration
    WHATSAPP_PHONE_NUMBER_ID = os.getenv('WHATSAPP_PHONE_NUMBER_ID')
    WHATSAPP_ACCESS_TOKEN = os.getenv('WHATSAPP_ACCESS_TOKEN')
    WEBHOOK_VERIFY_TOKEN = os.getenv('WEBHOOK_VERIFY_TOKEN')
    
    # Flask Configuration
    # Cloud Run sets PORT env var, fallback to FLASK_PORT or 8080
    FLASK_PORT = int(os.getenv('PORT') or os.getenv('FLASK_PORT', 8080))
    # Debug mode: default to False in production (when PORT is set by Cloud Run), True in development
    _flask_debug_default = 'False' if os.getenv('PORT') else 'True'
    FLASK_DEBUG = os.getenv('FLASK_DEBUG', _flask_debug_default).lower() == 'true'
    
    # MongoDB Configuration
    MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
    MONGODB_DB_NAME = os.getenv('MONGODB_DB_NAME', 'hiker_db')
    
    # Database Mode Configuration
    # Set to 'true' to force JSON mode (test mode), 'false' or unset to use MongoDB with JSON fallback
    USE_JSON_MODE = os.getenv('USE_JSON_MODE', 'false').lower() == 'true'
    # Set to 'true' to require MongoDB (raise error if not available), 'false' to allow JSON fallback
    REQUIRE_MONGODB = os.getenv('REQUIRE_MONGODB', 'false').lower() == 'true'
    
    # WhatsApp API URL
    WHATSAPP_API_URL = f"https://graph.facebook.com/v18.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    
    @staticmethod
    def validate():
        """Validate that all required configuration is present"""
        required_vars = [
            'WHATSAPP_PHONE_NUMBER_ID',
            'WHATSAPP_ACCESS_TOKEN',
            'WEBHOOK_VERIFY_TOKEN'
        ]
        
        missing = []
        for var in required_vars:
            if not os.getenv(var):
                missing.append(var)
        
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
        
        return True

