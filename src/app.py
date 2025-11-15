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
conversation_engine = ConversationEngine(user_db=user_db)

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
            # Send response with optional buttons
            success = whatsapp_client.send_message(from_number, response, buttons=buttons)
            if success:
                logger.info(f"Sent response to {from_number} (with buttons: {len(buttons) if buttons else 0})")
            else:
                logger.error(f"Failed to send response to {from_number}")
    
    except Exception as e:
        logger.error(f"Error processing message with conversation engine: {e}", exc_info=True)
        # Fallback response
        whatsapp_client.send_message(from_number, "מצטער, אירעה שגיאה. נסה שוב או הקש 'עזרה'.")

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
        app.run(
            host='0.0.0.0',
            port=Config.FLASK_PORT,
            debug=False
        )
        
    except ValueError as e:
        logger.error(f"Configuration error: {str(e)}")
        logger.error("Please copy .env.example to .env and fill in your credentials")
    except Exception as e:
        logger.error(f"Failed to start application: {str(e)}", exc_info=True)

