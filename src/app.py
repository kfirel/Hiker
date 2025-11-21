import sys
import os
# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, request, jsonify
import logging
from src.config import Config
from src.whatsapp_client import WhatsAppClient
from src.timer_manager import TimerManager
from src.user_database import UserDatabase
from src.conversation_engine import ConversationEngine
from src.user_logger import UserLogger

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Initialize components
whatsapp_client = WhatsAppClient()
timer_manager = TimerManager(whatsapp_client)
user_db = UserDatabase()
user_logger = UserLogger()
conversation_engine = ConversationEngine(user_db=user_db, user_logger=user_logger)

@app.route('/webhook', methods=['GET'])
def webhook_verify():
    """
    Webhook verification endpoint for WhatsApp Cloud API
    Meta will call this endpoint to verify your webhook
    """
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')
    
    if mode == 'subscribe' and token == Config.WEBHOOK_VERIFY_TOKEN:
        logger.info('Webhook verified successfully!')
        return challenge, 200
    else:
        logger.warning('Webhook verification failed')
        return 'Forbidden', 403

@app.route('/webhook', methods=['POST'])
def webhook_handler():
    """
    Webhook endpoint to receive incoming WhatsApp messages
    """
    try:
        data = request.get_json()
        logger.info(f"Received webhook data: {data}")
        
        # Parse incoming message
        if data.get('object') == 'whatsapp_business_account':
            for entry in data.get('entry', []):
                for change in entry.get('changes', []):
                    value = change.get('value', {})
                    
                    # Check if this is a message
                    if 'messages' in value:
                        for message in value['messages']:
                            process_message(message, value)
        
        return jsonify({'status': 'success'}), 200
        
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500

def process_message(message, value):
    """
    Process incoming WhatsApp message using conversation engine
    
    Args:
        message (dict): Message data
        value (dict): Value data containing metadata
    """
    message_type = message.get('type')
    
    # Extract message details
    from_number = message.get('from')
    message_id = message.get('id')
    
    # Try to get user's profile name from contacts in webhook data
    # WhatsApp sometimes includes contact info in the webhook
    profile_name = None
    try:
        if 'contacts' in value:
            contacts = value.get('contacts', [])
            if isinstance(contacts, list):
                for contact in contacts:
                    if isinstance(contact, dict) and contact.get('wa_id') == from_number:
                        profile_name = contact.get('profile', {}).get('name')
                        if profile_name:
                            logger.info(f"Found profile name from webhook for {from_number}: {profile_name}")
                            # Save to user profile if user exists
                            if user_db.user_exists(from_number):
                                # Only save if not already set (don't override user's entered name)
                                if not user_db.get_profile_value(from_number, 'full_name'):
                                    user_db.save_to_profile(from_number, 'whatsapp_name', profile_name)
                                    # Use WhatsApp name as full_name if no name was entered
                                    user_db.save_to_profile(from_number, 'full_name', profile_name)
                            break
    except Exception as e:
        logger.debug(f"Error extracting profile name from webhook for {from_number}: {e}")
    
    # If not found in webhook, try to get from API (async, won't block)
    if not profile_name:
        try:
            profile_name = whatsapp_client.get_user_profile_name(from_number)
            if profile_name:
                # Ensure user exists
                if not user_db.user_exists(from_number):
                    user_db.create_user(from_number)
                # Save WhatsApp name separately, don't override user's entered name
                if not user_db.get_profile_value(from_number, 'full_name'):
                    user_db.save_to_profile(from_number, 'whatsapp_name', profile_name)
                    user_db.save_to_profile(from_number, 'full_name', profile_name)
        except Exception as e:
            logger.debug(f"Could not fetch profile name for {from_number}: {e}")
    
    # Handle different message types
    if message_type == 'text':
        message_text = message.get('text', {}).get('body', '').strip()
    elif message_type == 'interactive':
        # Handle button/list responses
        interactive = message.get('interactive', {})
        interactive_type = interactive.get('type')
        
        if interactive_type == 'button_reply':
            # User clicked a button
            message_text = interactive.get('button_reply', {}).get('id', '')
        elif interactive_type == 'list_reply':
            # User selected from list
            message_text = interactive.get('list_reply', {}).get('id', '')
        else:
            logger.info(f"Ignoring interactive type: {interactive_type}")
            return
    else:
        logger.info(f"Ignoring non-text message type: {message_type}")
        return
    
    logger.info(f"Processing message from {from_number}: {message_text}")
    
    # Reset timer for this user (since they sent a message)
    timer_manager.schedule_followup(from_number, delay_seconds=600)
    
    # Process message through conversation engine
    try:
        response, buttons = conversation_engine.process_message(from_number, message_text)
        
        if response:
            # Log the response and buttons
            if buttons:
                logger.info(f"Response with {len(buttons)} buttons: {response[:100]}...")
                logger.debug(f"Buttons: {buttons}")
            else:
                logger.info(f"Response without buttons: {response[:100]}...")
            
            # Send response with optional buttons
            success = whatsapp_client.send_message(from_number, response, buttons=buttons)
            if success:
                logger.info(f"Sent response to {from_number} (with buttons: {len(buttons) if buttons else 0})")
            else:
                logger.error(f"Failed to send response to {from_number}")
    
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        error_msg = f"Error processing message '{message_text}' from {from_number}"
        
        # Log to both system logger and user logger
        logger.error(error_msg, exc_info=True)
        user_logger.log_error(from_number, error_msg, exception=e, traceback_str=error_traceback)
        
        # Fallback response
        error_response = "מצטער, אירעה שגיאה. נסה שוב או הקש 'עזרה'."
        whatsapp_client.send_message(from_number, error_response)
        # Also log the error response to user log
        user_logger.log_bot_response(from_number, error_response, state=None, buttons=None)

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'message': 'WhatsApp Bot is running'
    }), 200

if __name__ == '__main__':
    try:
        # Validate configuration
        Config.validate()
        logger.info("Configuration validated successfully")
        
        # Start Flask app
        logger.info(f"Starting WhatsApp Bot on port {Config.FLASK_PORT}")
        # Run Flask with auto-reload enabled by default
        # Set FLASK_DEBUG=False in .env to disable for production
        app.run(
            host='0.0.0.0',
            port=Config.FLASK_PORT,
            debug=Config.FLASK_DEBUG,
            use_reloader=Config.FLASK_DEBUG  # Auto-reload on file changes
        )
        
    except ValueError as e:
        logger.error(f"Configuration error: {str(e)}")
        logger.error("Please copy .env.example to .env and fill in your credentials")
    except Exception as e:
        logger.error(f"Failed to start application: {str(e)}", exc_info=True)

