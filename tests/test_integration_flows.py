"""
Integration tests for Hiker WhatsApp Bot
Tests data persistence, matching, and notifications with MongoDB
"""

import sys
import os
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from bson import ObjectId

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
import logging
from tests.integration_report_generator import IntegrationReportGenerator
from tests.conftest import integration_conversation_engine, mock_mongo_client, mongo_db
from tests.mock_whatsapp_client import MockWhatsAppClient

logger = logging.getLogger(__name__)


class IntegrationScenarioTester:
    """Test integration scenarios with multiple users"""
    
    def __init__(self, engine, mongo_db, whatsapp_client):
        self.engine = engine
        self.mongo_db = mongo_db
        self.whatsapp_client = whatsapp_client
        self.scenario_data = {
            'users': {},
            'conversations': [],
            'db_snapshots': [],
            'matches': [],
            'notifications': []
        }
    
    def run_scenario(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run a complete integration scenario
        
        Args:
            scenario: Scenario definition from YAML
            
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
        
        # Process each user action in order
        for user_action in users:
            user_id = user_action.get('user_id')
            phone = user_action.get('phone')
            action_type = user_action.get('type')
            setup_messages = user_action.get('setup_messages', [])
            action_messages = user_action.get('action_messages', [])
            wait_after = user_action.get('wait_after', 0)
            
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
                interaction = self._process_message(phone, msg, user_id)
                if interaction:
                    all_interactions.append(interaction)
                # No sleep needed - MongoDB operations are synchronous
            
            # Process action messages
            for idx, msg in enumerate(action_messages):
                # Replace placeholder match IDs with actual ones
                if msg.startswith('approve_MATCH_') or msg.startswith('reject_MATCH_'):
                    replaced_msg = self._replace_match_id(phone, msg)
                    # Only use replaced message if we found a match, otherwise log warning
                    if replaced_msg != msg:
                        msg = replaced_msg
                    else:
                        logger.warning(f"Could not find match ID for {phone}, using original message: {msg}")
                
                # Log which message we're processing (for debugging)
                logger.debug(f"Processing action message {idx+1}/{len(action_messages)} for {phone}: '{msg}'")
                
                interaction = self._process_message(phone, msg, user_id)
                if interaction:
                    all_interactions.append(interaction)
                else:
                    logger.warning(f"No interaction returned for message '{msg}' from {phone}")
                
                # No sleep needed - MongoDB operations are synchronous
                # State is updated immediately after each message
            
            # Wait if specified
            if wait_after > 0:
                import time
                time.sleep(wait_after)
        
        # Take final database snapshot
        self._take_db_snapshot()
        
        # Collect matches and notifications
        self._collect_matches_and_notifications()
        
        return {
            'scenario_id': scenario_id,
            'scenario_name': scenario_name,
            'scenario_description': scenario_description,
            'interactions': all_interactions,
            'db_snapshot': self.scenario_data['db_snapshots'][-1] if self.scenario_data['db_snapshots'] else {},
            'matches': self.scenario_data['matches'],
            'notifications': self.scenario_data['notifications'],
            'users': self.scenario_data['users'],
            'log_files': self._get_log_files()  # Add log files info
        }
    
    def _process_message(self, phone: str, message: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Process a single message and return interaction data"""
        try:
            # Clear WhatsApp client messages before processing
            self.whatsapp_client.clear_messages()
            
            # Process message
            bot_response, buttons = self.engine.process_message(phone, message)
            
            # Get sent messages from WhatsApp client
            sent_messages = self.whatsapp_client.get_sent_messages()
            
            # Check if notifications were sent (to other users)
            notifications = []
            for sent_msg in sent_messages:
                if sent_msg['to'] != phone:  # Message to different user
                    notifications.append({
                        'to': sent_msg['to'],
                        'message': sent_msg['message'],
                        'buttons': sent_msg.get('buttons')
                    })
            
            interaction = {
                'timestamp': datetime.now(),
                'user_id': user_id,
                'user_phone': phone,
                'user_message': message,
                'bot_response': bot_response,
                'buttons': buttons,
                'notifications_sent': notifications
            }
            
            # Store in user's conversation history
            if phone in self.scenario_data['users']:
                self.scenario_data['users'][phone]['conversations'].append(interaction)
            
            # Take DB snapshot after important actions
            if any(keyword in message.lower() for keyword in ['approve', 'reject', '1', '2']):
                self._take_db_snapshot()
            
            return interaction
            
        except Exception as e:
            return {
                'timestamp': datetime.now(),
                'user_id': user_id,
                'user_phone': phone,
                'user_message': message,
                'bot_response': f"ERROR: {str(e)}",
                'buttons': None,
                'error': str(e)
            }
    
    def _replace_match_id(self, phone: str, message: str) -> str:
        """Replace placeholder match ID with actual match ID"""
        if not hasattr(self.mongo_db, '_use_mongo') or not self.mongo_db._use_mongo:
            return message
        
        if not (message.startswith('approve_') or message.startswith('reject_')):
            return message
        
        # Extract the prefix (approve_ or reject_)
        prefix = 'approve_' if message.startswith('approve_') else 'reject_'
        original_match_id = message.replace(prefix, '')
        
        # If match_id is already provided and not empty/MATCH_, use it
        if original_match_id and original_match_id != 'MATCH_':
            return message
        
        # Find user
        user = self.mongo_db.mongo.get_collection("users").find_one({"phone_number": phone})
        if not user:
            logger.warning(f"User not found for phone {phone}, cannot replace match_id")
            return message
        
        # Find pending matches for this driver, sorted by creation time (newest first)
        matches = list(self.mongo_db.mongo.get_collection("matches").find({
            "driver_id": user['_id'],
            "status": "pending_approval"
        }).sort("matched_at", -1))
        
        if matches:
            match_id = matches[0].get('match_id', '')
            if match_id:
                logger.info(f"Replacing match_id for {phone}: {prefix}{match_id}")
                return f"{prefix}{match_id}"
            else:
                logger.warning(f"Match found but no match_id field for {phone}")
        else:
            logger.warning(f"No pending matches found for driver {phone}")
        
        return message
    
    def _take_db_snapshot(self):
        """Take a snapshot of database state"""
        if not hasattr(self.mongo_db, '_use_mongo') or not self.mongo_db._use_mongo:
            return
        
        snapshot = {
            'timestamp': datetime.now(),
            'users': [],
            'routines': [],
            'ride_requests': [],
            'matches': []
        }
        
        # Get all users
        users = list(self.mongo_db.mongo.get_collection("users").find({}))
        for user in users:
            snapshot['users'].append({
                'phone': user.get('phone_number'),
                'name': user.get('full_name'),
                'type': user.get('user_type'),
                'state': user.get('current_state')
            })
        
        # Get all routines
        routines = list(self.mongo_db.mongo.get_collection("routines").find({}))
        for routine in routines:
            snapshot['routines'].append({
                'phone': routine.get('phone_number'),
                'destination': routine.get('destination'),
                'days': routine.get('days'),
                'departure_time': routine.get('departure_time')
            })
        
        # Get all ride requests
        ride_requests = list(self.mongo_db.mongo.get_collection("ride_requests").find({}))
        for req in ride_requests:
            snapshot['ride_requests'].append({
                'request_id': req.get('request_id'),
                'phone': req.get('requester_phone'),
                'destination': req.get('destination'),
                'status': req.get('status')
            })
        
        # Get all matches
        matches = list(self.mongo_db.mongo.get_collection("matches").find({}))
        for match in matches:
            snapshot['matches'].append({
                'match_id': match.get('match_id'),
                'status': match.get('status'),
                'driver_response': match.get('driver_response')
            })
        
        self.scenario_data['db_snapshots'].append(snapshot)
    
    def _collect_matches_and_notifications(self):
        """Collect all matches and notifications from database"""
        if not hasattr(self.mongo_db, '_use_mongo') or not self.mongo_db._use_mongo:
            return
        
        # Get all matches
        matches = list(self.mongo_db.mongo.get_collection("matches").find({}))
        for match in matches:
            self.scenario_data['matches'].append({
                'match_id': match.get('match_id'),
                'status': match.get('status'),
                'driver_response': match.get('driver_response'),
                'matched_at': match.get('matched_at')
            })
        
        # Get all notifications (from WhatsApp client)
        sent_messages = self.whatsapp_client.get_sent_messages()
        for msg in sent_messages:
            self.scenario_data['notifications'].append({
                'to': msg['to'],
                'message': msg['message'],
                'buttons': msg.get('buttons'),
                'timestamp': datetime.now()
            })
    
    def _get_log_files(self) -> List[Dict[str, str]]:
        """Get list of log files created during this scenario"""
        import os
        log_files = []
        
        if hasattr(self.engine, 'user_logger'):
            logs_dir = self.engine.user_logger.logs_dir
            if logs_dir and os.path.exists(logs_dir):
                for filename in sorted(os.listdir(logs_dir)):
                    if filename.endswith('.log') and filename.startswith('user_'):
                        phone = filename.replace('user_', '').replace('.log', '')
                        log_files.append({
                            'phone': phone,
                            'filename': filename,
                            'path': os.path.join(logs_dir, filename)
                        })
        
        return log_files


def load_integration_scenarios(yaml_file: str = "tests/test_integration_inputs.yml") -> list:
    """Load integration scenarios from YAML file"""
    yaml_path = Path(project_root) / yaml_file
    
    if not yaml_path.exists():
        pytest.fail(f"Integration test input file not found: {yaml_path}")
    
    with open(yaml_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    return data.get('scenarios', [])


@pytest.fixture(scope="function")
def integration_scenarios():
    """Load all integration scenarios from YAML file"""
    return load_integration_scenarios()


def test_all_integration_scenarios(integration_conversation_engine, mongo_db, integration_scenarios):
    """
    Test all integration scenarios and generate HTML report
    
    This test runs all scenarios and generates a comprehensive HTML report
    showing data persistence, matching, and notifications
    """
    from tests.mock_whatsapp_client import MockWhatsAppClient
    
    # Create timestamped folder for this test run
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    test_runs_base = Path(project_root) / "test_runs"
    test_run_dir = test_runs_base / f"integration_run_{timestamp}"
    test_run_dir.mkdir(parents=True, exist_ok=True)
    
    # Create/update latest directory structure
    latest_dir = test_runs_base / "latest"
    # If latest is a symlink, remove it and create a directory
    if latest_dir.exists() and latest_dir.is_symlink():
        latest_dir.unlink()
    if not latest_dir.exists():
        latest_dir.mkdir(exist_ok=True)
    
    # Create symbolic link to integration directory in latest
    import shutil
    latest_integration_link = latest_dir / "integration"
    if latest_integration_link.exists() or latest_integration_link.is_symlink():
        if latest_integration_link.is_symlink():
            latest_integration_link.unlink()
        elif latest_integration_link.is_dir():
            shutil.rmtree(latest_integration_link)
    latest_integration_link.symlink_to(f"../{test_run_dir.name}")
    
    # Also keep the old symlink for backward compatibility
    latest_link = test_runs_base / "latest_integration"
    if latest_link.exists() or latest_link.is_symlink():
        latest_link.unlink()
    latest_link.symlink_to(test_run_dir.name)
    
    # Create logs subdirectory
    test_logs_dir = test_run_dir / "logs"
    test_logs_dir.mkdir(exist_ok=True)
    
    # Update user logger to use test logs directory
    original_logs_dir = integration_conversation_engine.user_logger.logs_dir
    integration_conversation_engine.user_logger.logs_dir = str(test_logs_dir)
    
    # Create WhatsApp client mock
    whatsapp_client = MockWhatsAppClient()
    
    # Update conversation engine services with mock WhatsApp client
    if hasattr(mongo_db, '_use_mongo') and mongo_db._use_mongo:
        from src.services.matching_service import MatchingService
        from src.services.notification_service import NotificationService
        
        matching_service = MatchingService(mongo_db.mongo)
        notification_service = NotificationService(mongo_db.mongo, whatsapp_client)
        integration_conversation_engine.action_executor.matching_service = matching_service
        integration_conversation_engine.action_executor.notification_service = notification_service
    
    # Create report generator
    report_filename = "integration_test_report.html"
    report_generator = IntegrationReportGenerator(report_filename)
    
    passed_count = 0
    failed_count = 0
    
    # Run each scenario
    for scenario in integration_scenarios:
        # Clear database before each scenario
        if hasattr(mongo_db, '_use_mongo') and mongo_db._use_mongo:
            mongo_db.mongo.get_collection("users").delete_many({})
            mongo_db.mongo.get_collection("routines").delete_many({})
            mongo_db.mongo.get_collection("ride_requests").delete_many({})
            mongo_db.mongo.get_collection("matches").delete_many({})
            mongo_db.mongo.get_collection("notifications").delete_many({})
        
        # Clear WhatsApp client
        whatsapp_client.clear_messages()
        
        # Create tester
        tester = IntegrationScenarioTester(integration_conversation_engine, mongo_db, whatsapp_client)
        
        try:
            # Run scenario
            result = tester.run_scenario(scenario)
            
            # Check if scenario succeeded (no errors)
            success = not any(
                interaction.get('error') for interaction in result['interactions']
            )
            
            if success:
                passed_count += 1
            else:
                failed_count += 1
            
            # Add to report
            report_generator.add_scenario(result)
            
        except Exception as e:
            failed_count += 1
            # Add error scenario to report
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
    
    # Copy integration report to latest directory
    import shutil
    latest_report = latest_dir / "integration_test_report.html"
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
        f.write("INTEGRATION TEST RUN SUMMARY\n")
        f.write("="*80 + "\n")
        f.write(f"Run Date/Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total scenarios tested: {len(integration_scenarios)}\n")
        f.write(f"✅ Passed: {passed_count}\n")
        f.write(f"❌ Failed: {failed_count}\n")
        f.write(f"\nTest Run Directory: {test_run_dir}\n")
        f.write(f"Latest Link: {latest_link} -> {test_run_dir.name}\n")
        f.write(f"Report: {report_path}\n")
        f.write(f"Logs: {test_logs_dir}\n")
        f.write("="*80 + "\n")
    
    # Print summary
    total = len(integration_scenarios)
    print(f"\n{'='*80}")
    print(f"📊 INTEGRATION TEST SUMMARY")
    print(f"{'='*80}")
    print(f"Run Date/Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total scenarios tested: {total}")
    print(f"✅ Passed: {passed_count}")
    print(f"❌ Failed: {failed_count}")
    print(f"\n📁 Test Run Directory: {test_run_dir}")
    print(f"🔗 Latest Link: {latest_link} -> {test_run_dir.name}")
    print(f"📄 Report: {report_path}")
    print(f"📝 Logs: {test_logs_dir}")
    print(f"📋 Summary: {summary_file}")
    print(f"{'='*80}")
    
    # Assert that all scenarios passed
    assert failed_count == 0, f"{failed_count} out of {total} scenarios failed. See report for details."


if __name__ == '__main__':
    # Allow running directly for debugging
    pytest.main([__file__, '-v', '--tb=short'])

