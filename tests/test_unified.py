"""
Unified Test Suite for Hiker WhatsApp Bot
Combines all test mechanisms: integration tests, time range tests, and conversation flow tests
Supports multiple users, frozen time, notifications, HTML reports, and logs
"""

import sys
import os
import yaml
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Union
from bson import ObjectId

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
import logging
from freezegun import freeze_time

from tests.integration_report_generator import IntegrationReportGenerator
from tests.conftest import integration_conversation_engine, mock_mongo_client, mongo_db
from tests.mock_whatsapp_client import MockWhatsAppClient

logger = logging.getLogger(__name__)


class UnifiedScenarioTester:
    """Unified tester that supports all test mechanisms"""
    
    def __init__(self, engine, mongo_db, whatsapp_client):
        self.engine = engine
        self.mongo_db = mongo_db
        self.whatsapp_client = whatsapp_client
        self.user_logger = engine.user_logger if hasattr(engine, 'user_logger') else None
        self.scenario_data = {
            'users': {},
            'conversations': [],
            'db_snapshots': [],
            'matches': [],
            'notifications': []
        }
    
    def run_scenario(self, scenario: Dict[str, Any], frozen_time: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Run a complete scenario with optional frozen time
        
        Args:
            scenario: Scenario definition from YAML
            frozen_time: Optional frozen time for this scenario (if None, uses real time)
            
        Returns:
            Dict with scenario results
        """
        scenario_id = scenario.get('id')
        scenario_name = scenario.get('name')
        scenario_description = scenario.get('description')
        users = scenario.get('users', [])
        
        # Reset state
        self.scenario_data = {
            'users': {},
            'conversations': [],
            'db_snapshots': [],
            'matches': [],
            'notifications': []
        }
        
        # Track all user interactions chronologically
        all_interactions = []
        current_time = frozen_time or datetime.now()
        
        # Use freezegun if frozen_time is provided
        freezer = None
        if frozen_time:
            freezer = freeze_time(current_time)
            freezer.start()
        
        try:
            for user_action in users:
                user_id = user_action.get('user_id')
                phone = user_action.get('phone')
                action_type = user_action.get('type')
                setup_messages = user_action.get('setup_messages', [])
                action_messages = user_action.get('action_messages', [])
                time_advance = user_action.get('time_advance', 0)  # Minutes to advance time
                
                # Initialize user if not exists
                if phone not in self.scenario_data['users']:
                    self.scenario_data['users'][phone] = {
                        'user_id': user_id,
                        'phone': phone,
                        'type': action_type,
                        'conversations': []
                    }
                
                # Process setup messages
                for msg in setup_messages:
                    message_text, msg_frozen_time = self._parse_message(msg)
                    
                    # Update frozen time if specified for this message
                    if msg_frozen_time and freezer:
                        freezer.stop()
                        freezer = freeze_time(msg_frozen_time)
                        freezer.start()
                        current_time = msg_frozen_time
                    elif time_advance > 0 and freezer:
                        # Advance time by specified minutes
                        current_time += timedelta(minutes=time_advance)
                        freezer.stop()
                        freezer = freeze_time(current_time)
                        freezer.start()
                    
                    result = self._process_message(phone, message_text, user_id)
                    if result:
                        if isinstance(result, tuple):
                            interaction, notification_interactions = result
                            all_interactions.append(interaction)
                            all_interactions.extend(notification_interactions or [])
                        elif isinstance(result, list):
                            all_interactions.extend(result)
                        else:
                            all_interactions.append(result)
                
                # Process action messages
                for msg in action_messages:
                    message_text, msg_frozen_time = self._parse_message(msg)
                    
                    # Update frozen time if specified for this message
                    if msg_frozen_time and freezer:
                        freezer.stop()
                        freezer = freeze_time(msg_frozen_time)
                        freezer.start()
                        current_time = msg_frozen_time
                    elif time_advance > 0 and freezer:
                        current_time += timedelta(minutes=time_advance)
                        freezer.stop()
                        freezer = freeze_time(current_time)
                        freezer.start()
                    
                    result = self._process_message(phone, message_text, user_id)
                    if result:
                        if isinstance(result, tuple):
                            interaction, notification_interactions = result
                            all_interactions.append(interaction)
                            all_interactions.extend(notification_interactions or [])
                        elif isinstance(result, list):
                            all_interactions.extend(result)
                        else:
                            all_interactions.append(result)
                
                # Advance time after user action if specified
                if time_advance > 0 and freezer:
                    current_time += timedelta(minutes=time_advance)
                    freezer.stop()
                    freezer = freeze_time(current_time)
                    freezer.start()
            
            # Take final database snapshot
            self.scenario_data['db_snapshots'].append(self._take_db_snapshot())
            
        finally:
            if freezer:
                freezer.stop()
        
        # Sort interactions by timestamp
        all_interactions.sort(key=lambda x: x.get('timestamp', datetime.min))
        
        # Get all matches from database snapshot (more complete than scenario_data)
        final_db_snapshot = self.scenario_data['db_snapshots'][-1] if self.scenario_data['db_snapshots'] else {}
        db_matches = final_db_snapshot.get('matches', [])
        
        # Combine matches from scenario_data and db_snapshot (avoid duplicates)
        all_matches = {}
        for match in self.scenario_data['matches']:
            match_id = match.get('match_id') or str(match.get('_id', ''))
            if match_id:
                all_matches[match_id] = match
        for match in db_matches:
            match_id = match.get('match_id', '')
            if match_id and match_id not in all_matches:
                all_matches[match_id] = match
        
        return {
            'scenario_id': scenario_id,
            'scenario_name': scenario_name,
            'scenario_description': scenario_description,
            'interactions': all_interactions,
            'db_snapshot': final_db_snapshot,
            'matches': list(all_matches.values()),
            'notifications': self.scenario_data['notifications'],
            'users': self.scenario_data['users'],
            'log_files': self._get_log_files()
        }
    
    def _parse_message(self, msg: Union[str, Dict[str, Any]]) -> Tuple[str, Optional[datetime]]:
        """
        Parse message that can be either a string or a dict with message + frozen_time
        
        Args:
            msg: Message as string or dict with 'message' and optional 'frozen_time'
            
        Returns:
            Tuple of (message_text, optional_frozen_time)
        """
        if isinstance(msg, dict):
            message_text = msg.get('message', '')
            frozen_time_str = msg.get('frozen_time')
            if frozen_time_str:
                try:
                    frozen_time = datetime.fromisoformat(frozen_time_str.replace('Z', '+00:00'))
                except:
                    try:
                        frozen_time = datetime.strptime(frozen_time_str, '%Y-%m-%d %H:%M:%S')
                    except:
                        frozen_time = None
                return message_text, frozen_time
            return message_text, None
        # Simple string message
        return str(msg), None
    
    def _process_message(self, phone: str, message: str, user_id: str) -> Optional[Union[Dict, Tuple, List]]:
        """Process a single message and return interaction data"""
        try:
            # Clear WhatsApp client messages before processing
            self.whatsapp_client.clear_messages()
            
            # Handle special cases (approval/rejection, name sharing)
            if message.startswith('share_name_yes_') or message.startswith('share_name_no_'):
                return self._handle_name_sharing(phone, message, user_id)
            
            if (message.startswith('approve_') or message.startswith('reject_') or
                message.startswith('1_') or message.startswith('2_') or
                message in ['1', '2']):
                return self._handle_match_response(phone, message, user_id)
            
            # Process message through conversation engine
            bot_response, buttons = self.engine.process_message(phone, message)
            
            # Send response through WhatsApp client (this will automatically log it)
            if bot_response:
                current_state = self.engine.user_db.get_user_state(phone) if self.engine.user_db.user_exists(phone) else None
                self.whatsapp_client.send_message(phone, bot_response, buttons=buttons, state=current_state)
                
                # Process auto-approvals after message is sent
                user_context = self.engine.user_db.get_user_context(phone)
                pending_ride_request_id = user_context.get('pending_auto_approval_ride_request_id')
                if pending_ride_request_id:
                    from bson import ObjectId
                    logger.info(f"🔄 Processing auto-approvals for ride request {pending_ride_request_id} after message sent")
                    self.engine.action_executor._process_auto_approvals(ObjectId(pending_ride_request_id))
                    self.engine.user_db.update_context(phone, 'pending_auto_approval_ride_request_id', None)
            
            # Get sent messages
            sent_messages = self.whatsapp_client.get_sent_messages()
            
            # Check for matches created (both for hitchhiker and driver)
            user_doc = self.mongo_db.mongo.get_collection("users").find_one({"phone_number": phone})
            if user_doc:
                user_id = user_doc.get('_id')
                # Find matches where this user is the hitchhiker
                hitchhiker_matches = list(self.mongo_db.mongo.get_collection("matches").find({
                    "hitchhiker_id": user_id
                }))
                # Find matches where this user is the driver
                driver_matches = list(self.mongo_db.mongo.get_collection("matches").find({
                    "driver_id": user_id
                }))
                # Add all matches (avoid duplicates by match_id)
                existing_match_ids = {m.get('match_id') or str(m.get('_id', '')) for m in self.scenario_data['matches']}
                for match in hitchhiker_matches + driver_matches:
                    match_id = match.get('match_id') or str(match.get('_id', ''))
                    if match_id and match_id not in existing_match_ids:
                        self.scenario_data['matches'].append(match)
                        existing_match_ids.add(match_id)
            
            # Separate messages sent to this user from notifications to other users
            user_messages = [msg for msg in sent_messages if msg['to'] == phone]
            notification_messages = [msg for msg in sent_messages if msg['to'] != phone]
            
            # Create interactions for each message sent to this user
            user_interactions = []
            if user_messages:
                first_bot_response = user_messages[0]['message']
                first_buttons = user_messages[0].get('buttons')
                if bot_response and bot_response != first_bot_response:
                    if bot_response not in [msg['message'] for msg in user_messages]:
                        first_bot_response = bot_response
                
                interaction = {
                    'timestamp': datetime.now(),
                    'user_id': user_id,
                    'user_phone': phone,
                    'user_message': message,
                    'bot_response': first_bot_response,
                    'buttons': first_buttons or buttons,
                    'notifications_sent': []
                }
                user_interactions.append(interaction)
                
                # Additional interactions for subsequent messages
                for additional_msg in user_messages[1:]:
                    additional_interaction = {
                        'timestamp': datetime.now(),
                        'user_id': user_id,
                        'user_phone': phone,
                        'user_message': None,
                        'bot_response': additional_msg['message'],
                        'buttons': additional_msg.get('buttons'),
                        'notifications_sent': []
                    }
                    user_interactions.append(additional_interaction)
            else:
                interaction = {
                    'timestamp': datetime.now(),
                    'user_id': user_id,
                    'user_phone': phone,
                    'user_message': message,
                    'bot_response': bot_response or '',
                    'buttons': buttons,
                    'notifications_sent': []
                }
                user_interactions.append(interaction)
            
            # Create notification interactions
            notifications = []
            notification_interactions = []
            for sent_msg in notification_messages:
                notifications.append({
                    'to': sent_msg['to'],
                    'message': sent_msg['message'],
                    'buttons': sent_msg.get('buttons')
                })
                recipient_phone = sent_msg['to']
                recipient_user_id = None
                if recipient_phone in self.scenario_data['users']:
                    recipient_user_id = self.scenario_data['users'][recipient_phone].get('user_id')
                notification_interaction = {
                    'timestamp': datetime.now(),
                    'user_id': recipient_user_id or recipient_phone,
                    'user_phone': recipient_phone,
                    'user_message': None,
                    'bot_response': sent_msg['message'],
                    'buttons': sent_msg.get('buttons'),
                    'notifications_sent': [],
                    'is_notification': True
                }
                notification_interactions.append(notification_interaction)
            
            # Store interactions
            if phone in self.scenario_data['users']:
                self.scenario_data['users'][phone]['conversations'].extend(user_interactions)
            
            # Return interactions
            all_interactions = user_interactions + notification_interactions
            if len(all_interactions) > 1:
                return all_interactions[0], all_interactions[1:]
            elif len(all_interactions) == 1:
                return all_interactions[0], []
            else:
                return None, []
            
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            return None
    
    def _handle_name_sharing(self, phone: str, message: str, user_id: str) -> Optional[Tuple]:
        """Handle name sharing response"""
        message = self._replace_name_sharing_match_id(phone, message)
        from src.services.approval_service import ApprovalService
        approval_service = ApprovalService(self.mongo_db.mongo, self.whatsapp_client, self.user_logger)
        success = approval_service.handle_name_sharing_response(phone, message)
        if success:
            sent_messages = self.whatsapp_client.get_sent_messages()
            bot_response = None
            buttons = None
            for sent_msg in reversed(sent_messages):
                if sent_msg['to'] == phone:
                    bot_response = sent_msg['message']
                    buttons = sent_msg.get('buttons')
                    break
            if not bot_response:
                bot_response = "✅ הטרמפיסט קיבל את פרטי הקשר שלך."
        else:
            bot_response = "❌ שגיאה בעיבוד הבקשה."
            buttons = None
        if bot_response:
            self.whatsapp_client.send_message(phone, bot_response, state="name_sharing_response")
        sent_messages = self.whatsapp_client.get_sent_messages()
        notifications = []
        notification_interactions = []
        for sent_msg in sent_messages:
            if sent_msg['to'] != phone:
                notifications.append({
                    'to': sent_msg['to'],
                    'message': sent_msg['message'],
                    'buttons': sent_msg.get('buttons')
                })
                recipient_phone = sent_msg['to']
                recipient_user_id = None
                if recipient_phone in self.scenario_data['users']:
                    recipient_user_id = self.scenario_data['users'][recipient_phone].get('user_id')
                notification_interaction = {
                    'timestamp': datetime.now(),
                    'user_id': recipient_user_id or recipient_phone,
                    'user_phone': recipient_phone,
                    'user_message': None,
                    'bot_response': sent_msg['message'],
                    'buttons': sent_msg.get('buttons'),
                    'notifications_sent': [],
                    'is_notification': True
                }
                notification_interactions.append(notification_interaction)
        interaction = {
            'timestamp': datetime.now(),
            'user_id': user_id,
            'user_phone': phone,
            'user_message': message,
            'bot_response': bot_response,
            'buttons': buttons,
            'notifications_sent': notifications
        }
        if phone in self.scenario_data['users']:
            self.scenario_data['users'][phone]['conversations'].append(interaction)
        return interaction, notification_interactions
    
    def _handle_match_response(self, phone: str, message: str, user_id: str) -> Optional[Tuple]:
        """Handle match approval/rejection response"""
        # Extract match_id and is_approval (same logic as test_integration_flows.py)
        if message.startswith('approve_'):
            match_id = message.replace('approve_', '')
            is_approval = True
        elif message.startswith('reject_'):
            match_id = message.replace('reject_', '')
            is_approval = False
        elif message.startswith('1_'):
            match_id = message.replace('1_', '')
            is_approval = True
        elif message.startswith('2_'):
            match_id = message.replace('2_', '')
            is_approval = False
        elif message == '1':
            match_id = None
            is_approval = True
        elif message == '2':
            match_id = None
            is_approval = False
        else:
            logger.error(f"Invalid button ID format: {message}")
            return None
        
        if match_id is None or match_id == 'MATCH_' or message in ['1', '2']:
            driver = self.mongo_db.mongo.get_collection("users").find_one({"phone_number": phone})
            if driver:
                auto_approved_match = self.mongo_db.mongo.get_collection("matches").find_one({
                    "driver_id": driver['_id'],
                    "is_auto_approval": True,
                    "status": "approved"
                })
                if auto_approved_match:
                    return None
                
                matches = list(self.mongo_db.mongo.get_collection("matches").find({
                    "driver_id": driver['_id'],
                    "status": "pending_approval",
                    "notification_sent_to_driver": True
                }).sort("matched_at", -1).limit(1))
                if matches:
                    match_id = matches[0].get('match_id', '')
                elif message in ['1', '2']:
                    bot_response, buttons = self.engine.process_message(phone, message)
                    if bot_response:
                        current_state = self.engine.user_db.get_user_state(phone) if self.engine.user_db.user_exists(phone) else None
                        self.whatsapp_client.send_message(phone, bot_response, buttons=buttons, state=current_state)
                    sent_messages = self.whatsapp_client.get_sent_messages()
                    user_messages = [msg for msg in sent_messages if msg['to'] == phone]
                    if user_messages:
                        interaction = {
                            'timestamp': datetime.now(),
                            'user_id': user_id,
                            'user_phone': phone,
                            'user_message': message,
                            'bot_response': user_messages[0]['message'],
                            'buttons': user_messages[0].get('buttons'),
                            'notifications_sent': []
                        }
                        return interaction, []
                    return None
        
        if match_id:
            from src.services.approval_service import ApprovalService
            approval_service = ApprovalService(self.mongo_db.mongo, self.whatsapp_client, self.user_logger)
            if is_approval:
                approval_service.driver_approve(phone, match_id)
            else:
                approval_service.driver_reject(phone, match_id)
            
            sent_messages = self.whatsapp_client.get_sent_messages()
            bot_response = None
            buttons = None
            for sent_msg in reversed(sent_messages):
                if sent_msg['to'] == phone:
                    bot_response = sent_msg['message']
                    buttons = sent_msg.get('buttons')
                    break
            
            notifications = []
            notification_interactions = []
            for sent_msg in sent_messages:
                if sent_msg['to'] != phone:
                    notifications.append({
                        'to': sent_msg['to'],
                        'message': sent_msg['message'],
                        'buttons': sent_msg.get('buttons')
                    })
                    recipient_phone = sent_msg['to']
                    recipient_user_id = None
                    if recipient_phone in self.scenario_data['users']:
                        recipient_user_id = self.scenario_data['users'][recipient_phone].get('user_id')
                    notification_interaction = {
                        'timestamp': datetime.now(),
                        'user_id': recipient_user_id or recipient_phone,
                        'user_phone': recipient_phone,
                        'user_message': None,
                        'bot_response': sent_msg['message'],
                        'buttons': sent_msg.get('buttons'),
                        'notifications_sent': [],
                        'is_notification': True
                    }
                    notification_interactions.append(notification_interaction)
            
            interaction = {
                'timestamp': datetime.now(),
                'user_id': user_id,
                'user_phone': phone,
                'user_message': message,
                'bot_response': bot_response,
                'buttons': buttons,
                'notifications_sent': notifications
            }
            if phone in self.scenario_data['users']:
                self.scenario_data['users'][phone]['conversations'].append(interaction)
            return interaction, notification_interactions
        
        return None
    
    def _replace_name_sharing_match_id(self, phone: str, message: str) -> str:
        """Replace placeholder match_id in name sharing message"""
        driver = self.mongo_db.mongo.get_collection("users").find_one({"phone_number": phone})
        if driver:
            context = driver.get('state', {}).get('context', {})
            pending_match_id = context.get('pending_name_share_match_id') or driver.get('pending_name_share_match_id')
            if pending_match_id:
                if message.startswith('share_name_yes_'):
                    return f'share_name_yes_{pending_match_id}'
                elif message.startswith('share_name_no_'):
                    return f'share_name_no_{pending_match_id}'
        return message
    
    def _take_db_snapshot(self) -> Dict[str, Any]:
        """Take a snapshot of the current database state"""
        users = list(self.mongo_db.mongo.get_collection("users").find())
        routines = list(self.mongo_db.mongo.get_collection("routines").find())
        ride_requests = list(self.mongo_db.mongo.get_collection("ride_requests").find())
        matches = list(self.mongo_db.mongo.get_collection("matches").find())
        
        return {
            'users': [self._serialize_user(u) for u in users],
            'routines': [self._serialize_routine(r) for r in routines],
            'ride_requests': [self._serialize_ride_request(r) for r in ride_requests],
            'matches': [self._serialize_match(m) for m in matches]
        }
    
    def _serialize_user(self, user: Dict) -> Dict:
        """Serialize user document for JSON"""
        return {
            'phone': user.get('phone_number', ''),
            'name': user.get('full_name') or user.get('whatsapp_name', ''),
            'type': user.get('user_type', ''),
            'state': user.get('state', {}).get('current_state', '')
        }
    
    def _serialize_routine(self, routine: Dict) -> Dict:
        """Serialize routine document for JSON"""
        return {
            'phone': routine.get('driver_phone', ''),
            'destination': routine.get('destination', ''),
            'days': routine.get('days', ''),
            'departure_time': f"{routine.get('departure_time_start', '')} - {routine.get('departure_time_end', '')}"
        }
    
    def _serialize_ride_request(self, request: Dict) -> Dict:
        """Serialize ride request document for JSON"""
        return {
            'request_id': str(request.get('_id', '')),
            'phone': request.get('requester_phone', ''),
            'destination': request.get('destination', ''),
            'status': request.get('status', '')
        }
    
    def _serialize_match(self, match: Dict) -> Dict:
        """Serialize match document for JSON"""
        return {
            'match_id': match.get('match_id', ''),
            'status': match.get('status', ''),
            'driver_response': 'approved' if match.get('status') == 'approved' else 'rejected' if match.get('status') == 'rejected' else 'pending'
        }
    
    def _get_log_files(self) -> List[str]:
        """Get list of log files for this scenario"""
        if not self.user_logger:
            return []
        logs_dir = Path(self.user_logger.logs_dir)
        if not logs_dir.exists():
            return []
        log_files = []
        for log_file in logs_dir.glob("user_*.log"):
            log_files.append(str(log_file.name))
        return sorted(log_files)


def load_unified_scenarios(yaml_file: str = "tests/test_unified_inputs.yml") -> list:
    """Load unified test scenarios from YAML file"""
    scenarios_file = Path(project_root) / yaml_file
    if not scenarios_file.exists():
        logger.warning(f"Unified scenarios file not found: {scenarios_file}")
        return []
    
    try:
        with open(scenarios_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            scenarios = data.get('scenarios', [])
            # Add scenario ID if missing
            for i, scenario in enumerate(scenarios):
                if 'id' not in scenario:
                    scenario['id'] = i + 1
            return scenarios
    except Exception as e:
        logger.error(f"Error loading unified scenarios: {e}", exc_info=True)
        return []


@pytest.fixture(scope="function")
def unified_tester(integration_conversation_engine, mongo_db, temp_logs_dir):
    """Create unified tester with all services initialized"""
    from src.services.matching_service import MatchingService
    from src.services.notification_service import NotificationService
    
    # Create WhatsApp client mock with user logger
    whatsapp_client = MockWhatsAppClient(user_logger=integration_conversation_engine.user_logger)
    
    # Initialize services
    matching_service = MatchingService(mongo_db.mongo)
    notification_service = NotificationService(mongo_db.mongo, whatsapp_client, integration_conversation_engine.user_logger)
    integration_conversation_engine.action_executor.matching_service = matching_service
    integration_conversation_engine.action_executor.notification_service = notification_service
    
    tester = UnifiedScenarioTester(integration_conversation_engine, mongo_db, whatsapp_client)
    return tester


@pytest.fixture(scope="function")
def unified_scenarios():
    """Load all unified scenarios from YAML file"""
    return load_unified_scenarios()


def test_all_unified_scenarios(unified_tester, integration_conversation_engine, mongo_db, unified_scenarios):
    """
    Test all unified scenarios and generate HTML report
    
    This test runs all scenarios and generates a comprehensive HTML report
    showing data persistence, matching, notifications, and time-based behavior
    """
    if not unified_scenarios:
        pytest.skip("No unified scenarios found")
    
    # Create timestamped folder for this test run
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    test_runs_base = Path(project_root) / "test_runs"
    test_run_dir = test_runs_base / f"unified_run_{timestamp}"
    test_run_dir.mkdir(parents=True, exist_ok=True)
    
    # Create/update latest directory structure
    latest_dir = test_runs_base / "latest"
    if latest_dir.exists() and latest_dir.is_symlink():
        latest_dir.unlink()
    if not latest_dir.exists():
        latest_dir.mkdir(exist_ok=True)
    
    # Create symbolic link to unified directory in latest
    import shutil
    latest_unified_link = latest_dir / "unified"
    if latest_unified_link.exists() or latest_unified_link.is_symlink():
        if latest_unified_link.is_symlink():
            latest_unified_link.unlink()
        elif latest_unified_link.is_dir():
            shutil.rmtree(latest_unified_link)
    latest_unified_link.symlink_to(f"../{test_run_dir.name}")
    
    # Create logs subdirectory
    test_logs_dir = test_run_dir / "logs"
    test_logs_dir.mkdir(exist_ok=True)
    
    # Update user logger to use test logs directory
    original_logs_dir = integration_conversation_engine.user_logger.logs_dir
    integration_conversation_engine.user_logger.logs_dir = str(test_logs_dir)
    
    # Create report generator
    report_filename = "unified_test_report.html"
    report_generator = IntegrationReportGenerator(report_filename)
    
    passed_count = 0
    failed_count = 0
    
    # Run each scenario
    for scenario in unified_scenarios:
        # Clear database before each scenario
        if hasattr(mongo_db, '_use_mongo') and mongo_db._use_mongo:
            mongo_db.mongo.get_collection("users").delete_many({})
            mongo_db.mongo.get_collection("routines").delete_many({})
            mongo_db.mongo.get_collection("ride_requests").delete_many({})
            mongo_db.mongo.get_collection("matches").delete_many({})
            mongo_db.mongo.get_collection("notifications").delete_many({})
        
        # Clear WhatsApp client
        unified_tester.whatsapp_client.clear_messages()
        
        # Get frozen time from scenario (if specified)
        frozen_time = None
        frozen_time_str = scenario.get('frozen_time')
        if frozen_time_str:
            try:
                frozen_time = datetime.fromisoformat(frozen_time_str.replace('Z', '+00:00'))
            except:
                try:
                    frozen_time = datetime.strptime(frozen_time_str, '%Y-%m-%d %H:%M:%S')
                except:
                    frozen_time = None
        
        try:
            # Run scenario
            result = unified_tester.run_scenario(scenario, frozen_time)
            
            # Check if scenario succeeded
            success = not any(interaction.get('error') for interaction in result['interactions'])
            
            # Check expected matches if specified
            expected_matches = scenario.get('expected_matches')
            if expected_matches is not None:
                actual_matches = len(result['matches'])
                if actual_matches != expected_matches:
                    success = False
                    result['error'] = f"Expected {expected_matches} matches, got {actual_matches}"
            
            # Check should_match flag if present
            if scenario.get('should_match') is not None:
                actual_matches = len(result['matches'])
                if scenario.get('should_match', True):
                    if actual_matches == 0:
                        success = False
                        result['error'] = "Expected matches but found none"
                else:
                    if actual_matches > 0:
                        success = False
                        result['error'] = f"Expected no matches but found {actual_matches}"
            
            if success:
                passed_count += 1
            else:
                failed_count += 1
            
            # Add to report
            report_generator.add_scenario(result)
            
        except Exception as e:
            failed_count += 1
            logger.error(f"Error running scenario {scenario.get('id')}: {e}", exc_info=True)
            report_generator.add_scenario({
                'scenario_id': scenario.get('id'),
                'scenario_name': scenario.get('name'),
                'scenario_description': scenario.get('description'),
                'interactions': [],
                'db_snapshot': {},
                'matches': [],
                'notifications': [],
                'users': {},
                'error': str(e)
            })
    
    # Restore original logs directory
    integration_conversation_engine.user_logger.logs_dir = original_logs_dir
    
    # Generate and save report
    report_path = report_generator.save_report(output_dir=str(test_run_dir))
    
    # Copy report to latest directory
    import shutil
    latest_report = latest_dir / report_filename
    if report_path and Path(report_path).exists():
        shutil.copy2(report_path, latest_report)
    
    # Create index.html in latest directory
    try:
        from tests.create_latest_index import create_latest_index
        create_latest_index(test_runs_base)
    except Exception as e:
        print(f"Warning: Failed to create latest index: {e}")
    
    # Create summary file
    summary_file = test_run_dir / "summary.txt"
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("="*80 + "\n")
        f.write("UNIFIED TEST RUN SUMMARY\n")
        f.write("="*80 + "\n")
        f.write(f"Run Date/Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total scenarios tested: {len(unified_scenarios)}\n")
        f.write(f"✅ Passed: {passed_count}\n")
        f.write(f"❌ Failed: {failed_count}\n")
        f.write(f"\nTest Run Directory: {test_run_dir}\n")
        f.write(f"Latest Link: {latest_unified_link} -> {test_run_dir.name}\n")
        f.write(f"Report: {report_path}\n")
        f.write(f"Logs: {test_logs_dir}\n")
        f.write("="*80 + "\n")
    
    # Print summary
    total = len(unified_scenarios)
    print(f"\n{'='*80}")
    print(f"📊 UNIFIED TEST SUMMARY")
    print(f"{'='*80}")
    print(f"Run Date/Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total scenarios tested: {total}")
    print(f"✅ Passed: {passed_count}")
    print(f"❌ Failed: {failed_count}")
    print(f"\n📁 Test Run Directory: {test_run_dir}")
    print(f"🔗 Latest Link: {latest_unified_link} -> {test_run_dir.name}")
    print(f"📄 Report: {report_path}")
    print(f"📝 Logs: {test_logs_dir}")
    print(f"📋 Summary: {summary_file}")
    print(f"{'='*80}")
    
    # Assert that all scenarios passed
    assert failed_count == 0, f"{failed_count} out of {total} scenarios failed. See report for details."


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])

