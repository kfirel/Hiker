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

logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Initialize components
user_logger = UserLogger()
whatsapp_client = WhatsAppClient(user_logger=user_logger)
timer_manager = TimerManager(whatsapp_client)

# Use MongoDB only - no fallback
try:
    user_db = UserDatabaseMongo()
    logger.info("Using MongoDB database")
except Exception as e:
    logger.error(f"Failed to initialize MongoDB database: {e}")
    raise RuntimeError("MongoDB connection is required. Please ensure MongoDB is running and configured.")

conversation_engine = ConversationEngine(user_db=user_db, user_logger=user_logger)

# Initialize services (MongoDB is always available)
from src.services.matching_service import MatchingService
from src.services.notification_service import NotificationService

matching_service = MatchingService(user_db.mongo)
notification_service = NotificationService(user_db.mongo, whatsapp_client, user_logger)

# Update action executor with services
conversation_engine.action_executor.matching_service = matching_service
conversation_engine.action_executor.notification_service = notification_service

logger.info("Matching and notification services initialized")

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

def handle_match_response(driver_phone: str, button_id: str):
    """
    Handle driver approval/rejection of a match
    
    Args:
        driver_phone: Driver's phone number
        button_id: Button ID (e.g., "approve_MATCH_123" or "reject_MATCH_123")
    """
    try:
        # Extract match_id from button_id
        # Support multiple formats:
        # - Old: "approve_MATCH_xxx" or "reject_MATCH_xxx"
        # - New: "1_MATCH_xxx" or "2_MATCH_xxx"
        # - Simple: "1" or "2" (will be handled by caller)
        if button_id.startswith('approve_'):
            match_id = button_id.replace('approve_', '')
            is_approval = True
        elif button_id.startswith('reject_'):
            match_id = button_id.replace('reject_', '')
            is_approval = False
        elif button_id.startswith('1_'):
            match_id = button_id.replace('1_', '')
            is_approval = True
        elif button_id.startswith('2_'):
            match_id = button_id.replace('2_', '')
            is_approval = False
        else:
            logger.error(f"Invalid button ID format: {button_id}")
            return
        
        # MongoDB is always available now
        
        # Handle case where match_id is empty or just "MATCH_" (from test inputs)
        if not match_id or match_id == 'MATCH_':
            logger.info(f"Empty match_id in button_id: {button_id}, trying to find match from database")
            # Try to find the most recent pending match for this driver
            driver = user_db.mongo.get_collection("users").find_one({"phone_number": driver_phone})
            if driver:
                matches = list(user_db.mongo.get_collection("matches").find({
                    "driver_id": driver['_id'],
                    "status": "pending_approval"
                }).sort("matched_at", -1).limit(1))
                if matches:
                    match_id = matches[0].get('match_id', '')
                    logger.info(f"Found match_id from database: {match_id}")
                else:
                    logger.error(f"No pending matches found for driver {driver_phone}")
                    whatsapp_client.send_message(driver_phone, "מצטער, לא נמצאה בקשה ממתינה לאישור. נסה שוב מאוחר יותר.")
                    return
            else:
                logger.error(f"Driver not found: {driver_phone}")
                whatsapp_client.send_message(driver_phone, "מצטער, לא נמצא משתמש במערכת. נסה שוב מאוחר יותר.")
                return
        
        from src.services.approval_service import ApprovalService
        
        approval_service = ApprovalService(user_db.mongo, whatsapp_client, user_logger)
        
        if is_approval:
            # Check if this is an auto-approval (driver shouldn't receive confirmation message)
            match = user_db.mongo.get_collection("matches").find_one({"match_id": match_id})
            is_auto_approval = match.get('is_auto_approval', False) if match else False
            
            success = approval_service.driver_approve(match_id, driver_phone, is_auto_approval=is_auto_approval)
            if success:
                # Don't send confirmation message if this was an auto-approval
                if is_auto_approval:
                    logger.info(f"Auto-approval for match {match_id} - skipping confirmation message to driver")
                    return
                
                # Check if driver needs to be asked about name sharing
                driver = user_db.mongo.get_collection("users").find_one({"phone_number": driver_phone})
                share_name_preference = driver.get('share_name_with_hitchhiker') if driver else None
                if not share_name_preference and driver:
                    profile = driver.get('profile', {})
                    share_name_preference = profile.get('share_name_with_hitchhiker', 'ask')
                if not share_name_preference:
                    share_name_preference = 'ask'
                
                if share_name_preference == 'ask':
                    # Driver will be asked separately - don't send confirmation yet
                    return
                else:
                    # Get hitchhiker and ride request info for the message
                    ride_request = user_db.mongo.get_collection("ride_requests").find_one({"_id": match['ride_request_id']})
                    hitchhiker = None
                    if ride_request:
                        hitchhiker = user_db.mongo.get_collection("users").find_one({"_id": ride_request['requester_id']})
                    
                    hitchhiker_name = "טרמפיסט"
                    destination = "יעד"
                    if hitchhiker:
                        hitchhiker_name = hitchhiker.get('full_name') or hitchhiker.get('whatsapp_name') or 'טרמפיסט'
                    if ride_request:
                        destination = ride_request.get('destination', 'יעד')
                    
                    message = f"✅ אישרת את הבקשה!\n\nהטרמפיסט {hitchhiker_name} (ל-{destination}) יקבל את פרטי הקשר שלך ויצור איתך קשר בקרוב. 📲"
            else:
                message = "❌ שגיאה באישור הבקשה. נסה שוב או פנה לתמיכה."
        else:
            success = approval_service.driver_reject(match_id, driver_phone)
            if success:
                # Get hitchhiker and ride request info for the message
                match = user_db.mongo.get_collection("matches").find_one({"match_id": match_id})
                ride_request = None
                hitchhiker = None
                if match:
                    ride_request = user_db.mongo.get_collection("ride_requests").find_one({"_id": match['ride_request_id']})
                    if ride_request:
                        hitchhiker = user_db.mongo.get_collection("users").find_one({"_id": ride_request['requester_id']})
                
                hitchhiker_name = "טרמפיסט"
                destination = "יעד"
                if hitchhiker:
                    hitchhiker_name = hitchhiker.get('full_name') or hitchhiker.get('whatsapp_name') or 'טרמפיסט'
                if ride_request:
                    destination = ride_request.get('destination', 'יעד')
                
                message = f"❌ דחית את הבקשה של {hitchhiker_name} (ל-{destination}).\n\nהטרמפיסט ימשיך לחפש נהגים אחרים. 👍"
            else:
                message = "❌ שגיאה בדחיית הבקשה. נסה שוב או פנה לתמיכה."
        
        # Logging is now automatic in WhatsAppClient.send_message (lowest level)
        whatsapp_client.send_message(driver_phone, message, state="match_response")
        
    except Exception as e:
        logger.error(f"Error handling match response: {e}", exc_info=True)
        user_logger.log_error(driver_phone, f"Error handling match response '{button_id}'", e)
        whatsapp_client.send_message(driver_phone, "מצטער, אירעה שגיאה. נסה שוב או הקש 'עזרה'.")

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
    
    # If not found in webhook, try to get from API (with timeout, won't block long)
    # Note: This is still synchronous but has timeout, so it won't hang indefinitely
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
            
            # Check if this is an approval/rejection button
            # Support both old format (approve_/reject_) and new format (1_/2_)
            if (message_text.startswith('approve_') or message_text.startswith('reject_') or
                message_text.startswith('1_') or message_text.startswith('2_')):
                handle_match_response(from_number, message_text)
                return
        elif interactive_type == 'list_reply':
            # User selected from list
            message_text = interactive.get('list_reply', {}).get('id', '')
            
            # Check if this is a name sharing response button (check before approval/rejection)
            if message_text.startswith('share_name_yes_') or message_text.startswith('share_name_no_'):
                from src.services.approval_service import ApprovalService
                approval_service = ApprovalService(user_db.mongo, whatsapp_client, user_logger)
                approval_service.handle_name_sharing_response(from_number, message_text)
                return
            
            # Check if this is an approval/rejection button
            # Support both old format (approve_/reject_) and new format (1_/2_)
            if (message_text.startswith('approve_') or message_text.startswith('reject_') or
                message_text.startswith('1_') or message_text.startswith('2_')):
                handle_match_response(from_number, message_text)
                return
        else:
            logger.info(f"Ignoring interactive type: {interactive_type}")
            return
    else:
        logger.info(f"Ignoring non-text message type: {message_type}")
        return
    
    logger.info(f"Processing message from {from_number}: {message_text}")
    
    # Check if this is a name sharing response (check before approval/rejection)
    if message_text.startswith('share_name_yes_') or message_text.startswith('share_name_no_'):
        from src.services.approval_service import ApprovalService
        approval_service = ApprovalService(user_db.mongo, whatsapp_client, user_logger)
        approval_service.handle_name_sharing_response(from_number, message_text)
        return
    
    # Check if this is an approval/rejection message (even if sent as text, not button)
    # Support both old format (approve_/reject_) and new format (1_/2_)
    if (message_text.startswith('approve_') or message_text.startswith('reject_') or
        message_text.startswith('1_') or message_text.startswith('2_')):
        handle_match_response(from_number, message_text)
        return
    
    # Check if this is a name sharing response (even if sent as text, not button)
    if message_text.startswith('share_name_yes_') or message_text.startswith('share_name_no_'):
        from src.services.approval_service import ApprovalService
        approval_service = ApprovalService(user_db.mongo, whatsapp_client)
        approval_service.handle_name_sharing_response(from_number, message_text)
        return
    
    # Check if user sent "1" or "2" and has a pending match (for simple approval/rejection)
    # Only treat "1"/"2" as approval/rejection if user has a pending match notification
    if message_text in ['1', '2']:
        driver = user_db.mongo.get_collection("users").find_one({"phone_number": from_number})
        if driver:
            matches = list(user_db.mongo.get_collection("matches").find({
                "driver_id": driver['_id'],
                "status": "pending_approval",
                "notification_sent_to_driver": True  # Only if notification was sent
            }).sort("matched_at", -1).limit(1))
            if matches:
                match_id = matches[0].get('match_id', '')
                if match_id:
                    # Convert "1" or "2" to format expected by handle_match_response
                    button_id = f"{message_text}_{match_id}"
                    logger.info(f"Treating '{message_text}' as {'approval' if message_text == '1' else 'rejection'} for match {match_id}")
                    handle_match_response(from_number, button_id)
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

