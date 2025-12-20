import sys
import os
# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, request, jsonify
import logging
import threading

# Configure logging first (before other imports)
from src.logging_config import setup_logging
setup_logging(level=logging.INFO)

from src.config import Config
from src.whatsapp_client import WhatsAppClient
from src.timer_manager import TimerManager
from src.database.user_database_mongo import UserDatabaseMongo
from src.conversation_engine import ConversationEngine
from src.user_logger import UserLogger
from src.handlers.match_response_handler import MatchResponseHandler
from src.utils.button_parser import ButtonParser

logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Initialize components
user_logger = UserLogger()
whatsapp_client = WhatsAppClient(user_logger=user_logger)
timer_manager = TimerManager(whatsapp_client)

# Initialize database with mode switching support
# Mode is determined by environment variables:
# - USE_JSON_MODE=true: Force JSON mode (test mode)
# - REQUIRE_MONGODB=true: Require MongoDB, raise error if unavailable
# - Default: Use MongoDB with JSON fallback
try:
    user_db = UserDatabaseMongo()
    if Config.USE_JSON_MODE:
        logger.info("🧪 TEST MODE: Using JSON database (USE_JSON_MODE=true)")
    elif user_db._use_mongo:
        logger.info("✅ PRODUCTION MODE: Using MongoDB database")
    else:
        logger.info("⚠️ FALLBACK MODE: MongoDB unavailable, using JSON database")
        if Config.REQUIRE_MONGODB:
            raise RuntimeError("MongoDB connection is required (REQUIRE_MONGODB=true) but MongoDB is not available. Please ensure MongoDB is running and configured.")
except Exception as e:
    if Config.REQUIRE_MONGODB:
        logger.error(f"Failed to initialize MongoDB database: {e}")
        raise RuntimeError("MongoDB connection is required (REQUIRE_MONGODB=true). Please ensure MongoDB is running and configured.")
    else:
        logger.warning(f"MongoDB initialization failed: {e}, falling back to JSON")
        # Create database instance in JSON mode
        user_db = UserDatabaseMongo(mongo_client=None)
        user_db._use_mongo = False

conversation_engine = ConversationEngine(user_db=user_db, user_logger=user_logger)

# Initialize services (only if MongoDB is available)
from src.services.matching_service import MatchingService
from src.services.notification_service import NotificationService

if user_db._use_mongo and user_db.mongo:
    matching_service = MatchingService(user_db.mongo)
    notification_service = NotificationService(user_db.mongo, whatsapp_client, user_logger)
    logger.info("✅ Services initialized with MongoDB")
else:
    matching_service = None
    notification_service = None
    logger.warning("⚠️ Services initialized without MongoDB - matching features disabled")

# Update action executor with services (if available)
conversation_engine.action_executor.matching_service = matching_service
conversation_engine.action_executor.notification_service = notification_service

# Initialize handlers
match_response_handler = MatchResponseHandler(user_db, whatsapp_client, user_logger)
button_parser = ButtonParser()

logger.info("Matching and notification services initialized")
logger.info("Handlers initialized")

def handle_webhook_verification():
    """
    Handle webhook verification (used by both / and /webhook routes)
    """
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')
    
    # Log verification attempt for debugging
    logger.info(f"Webhook verification attempt - mode: {mode}, token received: {bool(token)}, challenge: {bool(challenge)}")
    logger.debug(f"Expected token: {Config.WEBHOOK_VERIFY_TOKEN[:10]}..." if Config.WEBHOOK_VERIFY_TOKEN else "Expected token: None")
    logger.debug(f"Received token: {token[:10]}..." if token else "Received token: None")
    
    if mode == 'subscribe' and token == Config.WEBHOOK_VERIFY_TOKEN:
        logger.info('✅ Webhook verified successfully!')
        return challenge, 200
    else:
        logger.warning(f'❌ Webhook verification failed - mode: {mode}, token match: {token == Config.WEBHOOK_VERIFY_TOKEN if token else False}')
        if not Config.WEBHOOK_VERIFY_TOKEN:
            logger.error('WEBHOOK_VERIFY_TOKEN is not set in environment variables!')
        return 'Forbidden', 403

@app.route('/', methods=['GET'])
def root_webhook_verify():
    """
    Handle webhook verification at root path (Meta sometimes sends to / instead of /webhook)
    """
    # Check if this is a webhook verification request
    if request.args.get('hub.mode') == 'subscribe':
        return handle_webhook_verification()
    # Otherwise return health check or simple response
    return jsonify({
        'status': 'healthy',
        'message': 'WhatsApp Bot is running',
        'webhook_endpoint': '/webhook'
    }), 200

@app.route('/webhook', methods=['GET'])
def webhook_verify():
    """
    Webhook verification endpoint for WhatsApp Cloud API
    Meta will call this endpoint to verify your webhook
    """
    return handle_webhook_verification()

@app.route('/webhook', methods=['POST'])
def webhook_handler():
    """
    Webhook endpoint to receive incoming WhatsApp messages
    Returns immediately and processes messages in background thread for faster response
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
                            # Process message in background thread to return webhook response quickly
                            # This prevents WhatsApp from retrying due to slow response
                            thread = threading.Thread(
                                target=process_message,
                                args=(message, value),
                                daemon=True
                            )
                            thread.start()
                            logger.info(f"Started background thread to process message from {message.get('from')}")
        
        # Return success immediately - message processing happens in background
        return jsonify({'status': 'success'}), 200
        
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Removed handle_match_response - now using MatchResponseHandler

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
                            # Ensure user exists
                            if not user_db.user_exists(from_number):
                                user_db.create_user(from_number)
                            # Save WhatsApp name BUT DON'T save as full_name yet
                            # Wait for user confirmation in confirm_whatsapp_name state
                            if not user_db.get_profile_value(from_number, 'whatsapp_name'):
                                user_db.save_to_profile(from_number, 'whatsapp_name', profile_name)
                                logger.info(f"Saved WhatsApp name '{profile_name}' from webhook for {from_number}")
                            
                            # Only save as full_name if user already has full_name (backward compatibility)
                            # OR if user is already registered (don't interfere with confirmation flow)
                            existing_full_name = user_db.get_profile_value(from_number, 'full_name')
                            is_registered = user_db.is_registered(from_number)
                            if existing_full_name or is_registered:
                                # User already has a name or is registered - safe to save as full_name
                                if not existing_full_name:
                                    user_db.save_to_profile(from_number, 'full_name', profile_name)
                                    logger.info(f"Saved WhatsApp name '{profile_name}' as full_name for registered user {from_number}")
                            break
    except Exception as e:
        logger.debug(f"Error extracting profile name from webhook for {from_number}: {e}")
    
    # If not found in webhook, try to get from API (with timeout, won't block long)
    # Note: This is still synchronous but has timeout, so it won't hang indefinitely
    if not profile_name:
        try:
            profile_name = whatsapp_client.get_user_profile_name(from_number)
            if profile_name:
                # Ensure user exists
                if not user_db.user_exists(from_number):
                    user_db.create_user(from_number)
                # Save WhatsApp name BUT DON'T save as full_name yet
                # Wait for user confirmation in confirm_whatsapp_name state
                if not user_db.get_profile_value(from_number, 'whatsapp_name'):
                    user_db.save_to_profile(from_number, 'whatsapp_name', profile_name)
                    logger.info(f"Saved WhatsApp name '{profile_name}' for {from_number}")
                
                # Only save as full_name if user already has full_name (backward compatibility)
                # OR if user is already registered (don't interfere with confirmation flow)
                existing_full_name = user_db.get_profile_value(from_number, 'full_name')
                is_registered = user_db.is_registered(from_number)
                if existing_full_name or is_registered:
                    # User already has a name or is registered - safe to save as full_name
                    if not existing_full_name:
                        user_db.save_to_profile(from_number, 'full_name', profile_name)
                        logger.info(f"Saved WhatsApp name '{profile_name}' as full_name for registered user {from_number}")
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
            
            # Check current state FIRST - don't treat as match response if user is in registration/flow states
            current_state = user_db.get_user_state(from_number)
            
            # Registration/flow states where "1" or "2" are valid choices, not match approvals
            registration_states = [
                'confirm_restart', 'confirm_whatsapp_name', 'ask_full_name',
                'ask_user_type', 'ask_has_routine', 'ask_looking_for_ride_now',
                'ask_hitchhiker_when_need_ride', 'ask_set_default_destination',
                'ask_driver_destination', 'ask_driver_days', 'ask_driver_times',
                'ask_alert_preference', 'ask_share_name_preference'
            ]
            
            # Check if this is a match response button
            # BUT: Skip this check if user is in a registration/flow state OR if no pending match exists
            if current_state not in registration_states and button_parser.is_match_response(message_text):
                # Before calling handler, check if there's actually a pending match
                # This prevents false positives for "1" or "2" in regular conversation
                driver = user_db.mongo.get_collection("users").find_one({"phone_number": from_number})
                if driver:
                    # Find ride requests with pending matches for this driver
                    ride_requests = list(user_db.mongo.get_collection("ride_requests").find({
                        "matched_drivers.driver_id": driver['_id'],
                        "matched_drivers.status": "pending_approval",
                        "matched_drivers.notification_sent_to_driver": True
                    }).sort("created_at", -1).limit(1))
                    if ride_requests:
                        match_response_handler.handle(from_number, message_text)
                        return
                # No pending match - treat as regular conversation choice
                logger.debug(f"User {from_number} sent '{message_text}' in state '{current_state}' but no pending match - treating as conversation choice")
        elif interactive_type == 'list_reply':
            # User selected from list
            message_text = interactive.get('list_reply', {}).get('id', '')
            
            # Check if this is a name sharing response button (check before approval/rejection)
            if button_parser.is_name_sharing(message_text):
                from src.services.approval_service import ApprovalService
                approval_service = ApprovalService(user_db.mongo, whatsapp_client, user_logger)
                approval_service.handle_name_sharing_response(from_number, message_text)
                return
            
            # Check current state FIRST - don't treat as match response if user is in registration/flow states
            current_state = user_db.get_user_state(from_number)
            
            # Registration/flow states where "1" or "2" are valid choices, not match approvals
            registration_states = [
                'confirm_restart', 'confirm_whatsapp_name', 'ask_full_name',
                'ask_user_type', 'ask_has_routine', 'ask_looking_for_ride_now',
                'ask_hitchhiker_when_need_ride', 'ask_set_default_destination',
                'ask_driver_destination', 'ask_driver_days', 'ask_driver_times',
                'ask_alert_preference', 'ask_share_name_preference'
            ]
            
            # Check if this is a match response button
            # BUT: Skip this check if user is in a registration/flow state OR if no pending match exists
            if current_state not in registration_states and button_parser.is_match_response(message_text):
                # Before calling handler, check if there's actually a pending match
                # This prevents false positives for "1" or "2" in regular conversation
                driver = user_db.mongo.get_collection("users").find_one({"phone_number": from_number})
                if driver:
                    # Find ride requests with pending matches for this driver
                    ride_requests = list(user_db.mongo.get_collection("ride_requests").find({
                        "matched_drivers.driver_id": driver['_id'],
                        "matched_drivers.status": "pending_approval",
                        "matched_drivers.notification_sent_to_driver": True
                    }).sort("created_at", -1).limit(1))
                    if ride_requests:
                        match_response_handler.handle(from_number, message_text)
                        return
                # No pending match - treat as regular conversation choice
                logger.debug(f"User {from_number} sent '{message_text}' in state '{current_state}' but no pending match - treating as conversation choice")
        else:
            logger.info(f"Ignoring interactive type: {interactive_type}")
            return
    else:
        logger.info(f"Ignoring non-text message type: {message_type}")
        return
    
    logger.info(f"Processing message from {from_number}: {message_text}")
    
    # Log incoming message to user logger BEFORE processing
    # This ensures all messages are logged, even if they're handled by special handlers
    user_logger.log_user_message(from_number, message_text)
    
    # Check current state FIRST - don't treat as match response if user is confirming restart
    current_state = user_db.get_user_state(from_number)
    
    # Check if this is a name sharing response (check before approval/rejection)
    if button_parser.is_name_sharing(message_text):
        from src.services.approval_service import ApprovalService
        approval_service = ApprovalService(user_db.mongo, whatsapp_client, user_logger)
        approval_service.handle_name_sharing_response(from_number, message_text)
        return
    
    # Check if this is a match response message (even if sent as text, not button)
    # BUT: Skip this check if user is in registration/flow states
    registration_states = [
        'confirm_restart', 'confirm_whatsapp_name', 'ask_full_name',
        'ask_user_type', 'ask_has_routine', 'ask_looking_for_ride_now',
        'ask_hitchhiker_when_need_ride', 'ask_set_default_destination',
        'ask_driver_destination', 'ask_driver_days', 'ask_driver_times',
        'ask_alert_preference', 'ask_share_name_preference'
    ]
    
    if current_state not in registration_states and button_parser.is_match_response(message_text):
        # Before calling handler, check if there's actually a pending match
        # This prevents false positives for "1" or "2" in regular conversation
        driver = user_db.mongo.get_collection("users").find_one({"phone_number": from_number})
        if driver:
            # Find ride requests with pending matches for this driver
            ride_requests = list(user_db.mongo.get_collection("ride_requests").find({
                "matched_drivers.driver_id": driver['_id'],
                "matched_drivers.status": "pending_approval",
                "matched_drivers.notification_sent_to_driver": True
            }).sort("created_at", -1).limit(1))
            if ride_requests:
                match_response_handler.handle(from_number, message_text)
                return
        # No pending match - treat as regular conversation choice
        logger.debug(f"User {from_number} sent '{message_text}' in state '{current_state}' but no pending match - treating as conversation choice")
    
    # Check if user sent "1" or "2" and has a pending match (for simple approval/rejection)
    # Only treat "1"/"2" as approval/rejection if user has a pending match notification
    # BUT: Skip this check if user is in registration/flow states (they're answering questions, not approving matches)
    if message_text in ['1', '2']:
        # Registration/flow states where "1" or "2" are valid choices, not match approvals
        registration_states = [
            'confirm_restart', 'confirm_whatsapp_name', 'ask_full_name',
            'ask_user_type', 'ask_has_routine', 'ask_looking_for_ride_now',
            'ask_hitchhiker_when_need_ride', 'ask_set_default_destination',
            'ask_driver_destination', 'ask_driver_days', 'ask_driver_times',
            'ask_alert_preference', 'ask_share_name_preference'
        ]
        
        # Only treat as match approval if user is NOT in a registration/flow state
        if current_state not in registration_states:
            driver = user_db.mongo.get_collection("users").find_one({"phone_number": from_number})
            if driver:
                # Find ride requests with pending matches for this driver
                ride_requests = list(user_db.mongo.get_collection("ride_requests").find({
                    "matched_drivers.driver_id": driver['_id'],
                    "matched_drivers.status": "pending_approval",
                    "matched_drivers.notification_sent_to_driver": True
                }).sort("created_at", -1).limit(1))
                if ride_requests:
                    # Find the most recent matched driver entry
                    ride_request = ride_requests[0]
                    matched_drivers = ride_request.get('matched_drivers', [])
                    matched_driver = None
                    for md in sorted(matched_drivers, key=lambda x: x.get('matched_at', ''), reverse=True):
                        if (str(md.get('driver_id')) == str(driver['_id']) and 
                            md.get('status') == 'pending_approval' and 
                            md.get('notification_sent_to_driver')):
                            matched_driver = md
                            break
                    
                    if matched_driver:
                        match_id = matched_driver.get('match_id', '')
                        if match_id:
                            # Convert "1" or "2" to format expected by handler
                            button_id = f"{message_text}_{match_id}"
                            logger.info(f"Treating '{message_text}' as {'approval' if message_text == '1' else 'rejection'} for match {match_id}")
                            match_response_handler.handle(from_number, button_id)
                            return
    
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
            # Logging is now automatic in WhatsAppClient.send_message (lowest level)
            success = whatsapp_client.send_message(from_number, response, buttons=buttons, state=log_state if 'log_state' in locals() else None)
            if success:
                logger.info(f"Sent response to {from_number} (with buttons: {len(buttons) if buttons else 0})")
                
                # After message is sent, check if we need to process auto-approvals
                # This ensures hitchhiker gets confirmation message first, then approval notification
                user_context = user_db.get_user_context(from_number)
                pending_ride_request_id = user_context.get('pending_auto_approval_ride_request_id')
                if pending_ride_request_id:
                    from bson import ObjectId
                    
                    logger.info(f"🔄 Processing auto-approvals for ride request {pending_ride_request_id} after message sent")
                    conversation_engine.action_executor._process_auto_approvals(ObjectId(pending_ride_request_id))
                    
                    # Clear the pending flag
                    user_db.update_context(from_number, 'pending_auto_approval_ride_request_id', None)
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
        # Logging is now automatic in WhatsAppClient.send_message (lowest level)
        error_response = "מצטער, אירעה שגיאה. נסה שוב או הקש 'עזרה'."
        whatsapp_client.send_message(from_number, error_response)

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'message': 'WhatsApp Bot is running'
    }), 200

if __name__ == '__main__':
    # Validate configuration (but don't fail startup - log warning instead)
    try:
        Config.validate()
        logger.info("Configuration validated successfully")
    except ValueError as e:
        logger.warning(f"Configuration warning: {str(e)}")
        logger.warning("Some features may not work. Please set required environment variables.")
        # Continue anyway - app should still start for health checks
    
    # Always start Flask app - Cloud Run needs the port to be listening
    try:
        port = Config.FLASK_PORT
        logger.info(f"Starting WhatsApp Bot on port {port} (PORT env: {os.getenv('PORT', 'not set')})")
        logger.info(f"Debug mode: {Config.FLASK_DEBUG}")
        
        # Run Flask with auto-reload enabled by default
        # Set FLASK_DEBUG=False in .env to disable for production
        app.run(
            host='0.0.0.0',
            port=port,
            debug=Config.FLASK_DEBUG,
            use_reloader=Config.FLASK_DEBUG  # Auto-reload on file changes
        )
    except Exception as e:
        logger.error(f"Failed to start application: {str(e)}", exc_info=True)
        # Re-raise to ensure Cloud Run sees the failure
        raise

