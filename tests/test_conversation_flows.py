"""
Comprehensive test suite for conversation flows
Tests all flows defined in test_inputs.yml and generates HTML report
"""

import sys
import os
import yaml
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
from tests.report_generator import HTMLReportGenerator
from tests.conftest import conversation_engine, test_phone_number

class ConversationFlowTester:
    """Test conversation flows from YAML input file"""
    
    def __init__(self, engine, phone_number):
        self.engine = engine
        self.phone_number = phone_number
        self.conversation_history = []
        self.current_exchanges = []
    
    def run_flow(self, flow_name: str, flow_description: str, messages: list, continue_from_flow_id: int = None) -> dict:
        """
        Run a single conversation flow
        
        Args:
            flow_name: Name of the flow
            flow_description: Description of the flow
            messages: List of user messages to send
            continue_from_flow_id: Optional flow ID to continue from (reuse that flow's user)
            
        Returns:
            Dict with flow results
        """
        # Reset conversation history
        self.conversation_history = []
        self.current_exchanges = []
        
        # If continuing from another flow, don't clear user data
        if continue_from_flow_id is None:
            # Clear user data for fresh start
            self.engine.user_db.delete_user_data(self.phone_number)
        else:
            # Set user to idle state so they can continue conversation
            if self.engine.user_db.user_exists(self.phone_number):
                self.engine.user_db.set_user_state(self.phone_number, 'idle')
        
        # Log test start
        self.engine.user_logger.log_event(
            self.phone_number, 
            'test_flow_start', 
            {
                'flow_name': flow_name, 
                'flow_description': flow_description,
                'continue_from': continue_from_flow_id
            }
        )
        
        success = True
        error_message = None
        
        try:
            for idx, user_message in enumerate(messages, 1):
                # Send user message
                exchange = {
                    'user_message': user_message,
                    'bot_message': None,
                    'buttons': None,
                    'step': idx
                }
                
                try:
                    # Process message through conversation engine
                    # This will automatically log via user_logger
                    bot_response, buttons = self.engine.process_message(
                        self.phone_number, 
                        user_message
                    )
                    
                    exchange['bot_message'] = bot_response
                    exchange['buttons'] = buttons
                    
                    # Store exchange
                    self.current_exchanges.append(exchange)
                    
                except Exception as e:
                    # Error processing message
                    success = False
                    error_message = f"Error at step {idx} (message: '{user_message}'): {str(e)}"
                    exchange['bot_message'] = f"ERROR: {str(e)}"
                    self.current_exchanges.append(exchange)
                    
                    # Log error
                    self.engine.user_logger.log_event(
                        self.phone_number,
                        'test_error',
                        {'step': idx, 'message': user_message, 'error': str(e)}
                    )
                    break
            
            # Store completed conversation
            self.conversation_history.append({
                'exchanges': self.current_exchanges
            })
            
            # Log test completion
            self.engine.user_logger.log_event(
                self.phone_number,
                'test_flow_complete',
                {'flow_name': flow_name, 'success': success, 'steps': len(messages)}
            )
            
        except Exception as e:
            success = False
            error_message = f"Flow failed with error: {str(e)}"
            
            # Log flow failure
            self.engine.user_logger.log_event(
                self.phone_number,
                'test_flow_failed',
                {'flow_name': flow_name, 'error': str(e)}
            )
        
        return {
            'flow_name': flow_name,
            'flow_description': flow_description,
            'messages': self.conversation_history,
            'success': success,
            'error_message': error_message
        }

def load_test_flows(yaml_file: str = "tests/test_inputs.yml") -> list:
    """Load test flows from YAML file"""
    yaml_path = Path(project_root) / yaml_file
    
    if not yaml_path.exists():
        pytest.fail(f"Test input file not found: {yaml_path}")
    
    with open(yaml_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    return data.get('flows', [])

@pytest.fixture(scope="session")
def test_flows():
    """Load all test flows from YAML file"""
    return load_test_flows()

def test_all_flows(conversation_engine, test_phone_number, test_flows):
    """
    Test all conversation flows and generate HTML report
    
    This test runs all flows and generates a comprehensive HTML report
    """
    # Create timestamped folder for this test run
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    test_runs_base = Path(project_root) / "test_runs"
    test_run_dir = test_runs_base / f"run_{timestamp}"
    test_run_dir.mkdir(parents=True, exist_ok=True)
    
    # Create symbolic link to latest run
    latest_link = test_runs_base / "latest"
    # Remove existing link if it exists
    if latest_link.exists() or latest_link.is_symlink():
        latest_link.unlink()
    # Create new symbolic link pointing to current run
    latest_link.symlink_to(test_run_dir.name)
    
    # Create logs subdirectory for this run
    test_logs_dir = test_run_dir / "logs"
    test_logs_dir.mkdir(exist_ok=True)
    
    # Create report generator with simple filename (no timestamp)
    report_filename = "test_report.html"
    report_generator = HTMLReportGenerator(report_filename)
    
    passed_count = 0
    failed_count = 0
    
    # Track phone numbers for flows that continue from others
    flow_phone_numbers = {}
    
    # Update conversation engine to use test run logs directory
    original_logs_dir = conversation_engine.user_logger.logs_dir
    conversation_engine.user_logger.logs_dir = str(test_logs_dir)
    
    # Run each flow
    for flow_idx, flow in enumerate(test_flows, 1):
        # Use flow ID if available, otherwise use index
        flow_id = flow.get('id', flow_idx)
        flow_name = flow.get('name', f'Unnamed Flow {flow_id}')
        flow_description = flow.get('description', 'No description')
        messages = flow.get('messages', [])
        continue_from = flow.get('continue_from')
        
        # Determine phone number for this flow
        import random
        if continue_from and continue_from in flow_phone_numbers:
            # Reuse phone number from the flow we're continuing from
            flow_phone = flow_phone_numbers[continue_from]
        else:
            # Generate unique phone number for this flow
            # Use format: test_<flow_id>_<random> for better log organization
            flow_phone = f"test_{flow_id:02d}_{random.randint(1000, 9999)}"
            flow_phone_numbers[flow_id] = flow_phone
        
        # Create tester for this flow
        tester = ConversationFlowTester(conversation_engine, flow_phone)
        
        # Run the flow
        result = tester.run_flow(flow_name, flow_description, messages, continue_from)
        
        # Track success/failure
        if result['success']:
            passed_count += 1
        else:
            failed_count += 1
        
        # Add to report
        report_generator.add_conversation(
            result['flow_name'],
            result['flow_description'],
            result['messages'],
            result['success'],
            result.get('error_message'),
            user_id=flow_phone  # Add user ID (phone number) to report
        )
    
    # Restore original logs directory
    conversation_engine.user_logger.logs_dir = original_logs_dir
    
    # Generate and save report to test run directory
    report_path = report_generator.save_report(output_dir=str(test_run_dir))
    
    # Create summary file
    summary_file = test_run_dir / "summary.txt"
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("="*80 + "\n")
        f.write("TEST RUN SUMMARY\n")
        f.write("="*80 + "\n")
        f.write(f"Run Date/Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total flows tested: {len(test_flows)}\n")
        f.write(f"✅ Passed: {passed_count}\n")
        f.write(f"❌ Failed: {failed_count}\n")
        f.write(f"\nTest Run Directory: {test_run_dir}\n")
        f.write(f"Latest Link: {latest_link} -> {test_run_dir.name}\n")
        f.write(f"Report: {report_path}\n")
        f.write(f"Logs: {test_logs_dir}\n")
        f.write("="*80 + "\n")
    
    # Print summary
    total = len(test_flows)
    print(f"\n{'='*80}")
    print(f"📊 TEST SUMMARY")
    print(f"{'='*80}")
    print(f"Run Date/Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total flows tested: {total}")
    print(f"✅ Passed: {passed_count}")
    print(f"❌ Failed: {failed_count}")
    print(f"\n📁 Test Run Directory: {test_run_dir}")
    print(f"🔗 Latest Link: {latest_link} -> {test_run_dir.name}")
    print(f"📄 Report: {report_path}")
    print(f"📝 Logs: {test_logs_dir}")
    print(f"📋 Summary: {summary_file}")
    print(f"{'='*80}")
    
    # Assert that all flows passed
    assert failed_count == 0, f"{failed_count} out of {total} flows failed. See report for details."

@pytest.mark.parametrize("flow_index", range(20))  # Adjust range based on number of flows
def test_individual_flow(conversation_engine, test_phone_number, flow_index):
    """
    Test individual flows (parametrized)
    This allows running flows separately for better debugging
    """
    test_flows = load_test_flows()
    
    if flow_index >= len(test_flows):
        pytest.skip(f"Flow index {flow_index} out of range")
    
    flow = test_flows[flow_index]
    flow_id = flow.get('id', flow_index + 1)
    flow_name = flow.get('name', f'Flow {flow_id}')
    flow_description = flow.get('description', 'No description')
    messages = flow.get('messages', [])
    continue_from = flow.get('continue_from')
    
    # Generate unique phone number for this flow
    import random
    flow_phone = f"test_{flow_id:02d}_{random.randint(1000, 9999)}"
    
    # Create tester
    tester = ConversationFlowTester(conversation_engine, flow_phone)
    
    # Run the flow
    result = tester.run_flow(flow_name, flow_description, messages, continue_from)
    
    # Assert success
    assert result['success'], f"Flow '{flow_name}' failed: {result.get('error_message', 'Unknown error')}"

if __name__ == '__main__':
    # Allow running directly for debugging
    pytest.main([__file__, '-v', '--tb=short'])

