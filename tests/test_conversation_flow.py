#!/usr/bin/env python3
"""
Comprehensive test suite for conversation flow
Tests full scenarios from start to finish
"""

import sys
import os
# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import logging

# Configure logging to see matching service calls
from src.logging_config import setup_logging
setup_logging(level=logging.INFO)

from src.database.user_database_mongo import UserDatabaseMongo
from src.conversation_engine import ConversationEngine

class ConversationTester:
    """Test conversation flow scenarios"""
    
    def __init__(self):
        """Initialize tester with MongoDB mock (required)"""
        # Use MongoDB mock (required - no JSON fallback)
        try:
            import mongomock
            from src.database.mongodb_client import MongoDBClient
            
            # Create mock MongoDB client
            mock_client = mongomock.MongoClient()
            mock_mongo = MongoDBClient.__new__(MongoDBClient)
            mock_mongo.client = mock_client
            mock_mongo.db_name = "test_hiker_db"
            mock_mongo.db = mock_client[mock_mongo.db_name]
            mock_mongo.connection_string = "mongomock://localhost"
            
            # Create indexes (handle errors gracefully for mongomock)
            try:
                mock_mongo._create_indexes()
            except Exception:
                pass  # mongomock may not support all index operations
            
            # Create UserDatabaseMongo with mock
            self.user_db = UserDatabaseMongo(mongo_client=mock_mongo)
            
            print("✅ Using MongoDB mock for testing (matching service enabled)")
        except ImportError:
            raise ImportError("mongomock is required for tests. Install with: pip install mongomock")
        
        from src.user_logger import UserLogger
        self.user_logger = UserLogger()
        self.conversation_engine = ConversationEngine(user_db=self.user_db, user_logger=self.user_logger)
        
        # If using MongoDB, ensure matching service is initialized
        if hasattr(self.user_db, '_use_mongo') and self.user_db._use_mongo:
            from src.services.matching_service import MatchingService
            from src.services.notification_service import NotificationService
            from tests.mock_whatsapp_client import MockWhatsAppClient
            
            matching_service = MatchingService(self.user_db.mongo)
            self.whatsapp_client = MockWhatsAppClient(user_logger=self.user_logger)
            notification_service = NotificationService(self.user_db.mongo, self.whatsapp_client, self.user_logger)
            
            # Update action executor with services
            self.conversation_engine.action_executor.matching_service = matching_service
            self.conversation_engine.action_executor.notification_service = notification_service
        else:
            # Fallback: create a mock WhatsApp client even if MongoDB is not available
            from tests.mock_whatsapp_client import MockWhatsAppClient
            self.whatsapp_client = MockWhatsAppClient(user_logger=self.user_logger)
            
            print("✅ Matching and notification services initialized")
        
        self.test_phone = "test_972500000000"
        self.results = []
    
    def clean_start(self):
        """Clean test environment"""
        self.user_db.delete_user_data(self.test_phone)
        print("\n" + "="*80)
        print("🧪 STARTING NEW TEST SCENARIO")
        print("="*80)
    
    def send_message(self, message: str, step_num: int, expected_contains: str = None):
        """
        Send a message and verify response
        
        Args:
            message: Message to send
            step_num: Step number for display
            expected_contains: String that should be in response
        """
        print(f"\n📱 Step {step_num}: User sends: \"{message}\"")
        
        response, buttons = self.conversation_engine.process_message(self.test_phone, message)
        
        # Send response through WhatsApp client (this will automatically log it)
        # This mimics the behavior in app.py where messages are sent after processing
        if response:
            current_state = self.conversation_engine.user_db.get_user_state(self.test_phone) if self.conversation_engine.user_db.user_exists(self.test_phone) else None
            self.whatsapp_client.send_message(self.test_phone, response, buttons=buttons, state=current_state)
        
        print(f"🤖 Bot responds:")
        print(f"   Message: {response[:100]}..." if len(response) > 100 else f"   Message: {response}")
        if buttons:
            print(f"   Buttons: {len(buttons)} button(s)")
            for btn in buttons:
                print(f"      - [{btn['id']}] {btn['title']}")
        
        # Verify expected content
        if expected_contains:
            if expected_contains in response:
                print(f"   ✅ PASS: Response contains '{expected_contains}'")
                self.results.append(("PASS", step_num, message))
            else:
                print(f"   ❌ FAIL: Expected '{expected_contains}' not found in response")
                self.results.append(("FAIL", step_num, message))
        else:
            self.results.append(("INFO", step_num, message))
        
        return response, buttons
    
    def verify_user_data(self, field: str, expected_value: str, step_num: int):
        """Verify user profile data"""
        actual_value = self.user_db.get_profile_value(self.test_phone, field)
        
        if actual_value == expected_value:
            print(f"   ✅ PASS: {field} = '{expected_value}'")
            self.results.append(("PASS", step_num, f"Verify {field}"))
        else:
            print(f"   ❌ FAIL: {field} = '{actual_value}' (expected '{expected_value}')")
            self.results.append(("FAIL", step_num, f"Verify {field}"))
    
    def test_hitchhiker_scenario(self):
        """
        Test Scenario 1: New hitchhiker looking for ride
        """
        self.clean_start()
        print("\n🎬 SCENARIO 1: New Hitchhiker Looking for Ride")
        print("-" * 80)
        
        # Step 1: Initial message
        response, buttons = self.send_message(
            "Hello", 1, 
            "היי בורך הבא"
        )
        
        # Step 2: Provide name
        response, buttons = self.send_message(
            "כפיר אלגבסי", 2,
            "באיזה ישוב"
        )
        self.verify_user_data("full_name", "כפיר אלגבסי", 2)
        
        # Step 3: Provide settlement
        response, buttons = self.send_message(
            "תל אביב", 3,
            "מה אתה"
        )
        self.verify_user_data("home_settlement", "תל אביב", 3)
        
        # Step 4: Choose hitchhiker
        response, buttons = self.send_message(
            "2", 4,
            "מחפש כרגע טרמפ"
        )
        self.verify_user_data("user_type", "hitchhiker", 4)
        
        # Step 5: Looking for ride now - Yes
        response, buttons = self.send_message(
            "1", 5,
            "למתי אתה צריך את הטרמפ"
        )
        
        # Step 6: When - Now (uses new flow with matching)
        response, buttons = self.send_message(
            "1", 6,
            "לאן אתה צריך להגיע"
        )
        self.verify_user_data("ride_timing", "now", 6)
        
        # Step 7: Destination (this should trigger save_hitchhiker_ride_request with matching)
        print("\n   🔍 Step 7: This should trigger 'save_hitchhiker_ride_request' action with matching")
        response, buttons = self.send_message(
            "תל אביב", 7,
            "הבקשה שלך נרשמה"
        )
        self.verify_user_data("hitchhiker_destination", "תל אביב", 7)
        
        # Verify that matching service was called
        if hasattr(self.conversation_engine.action_executor, 'matching_service') and \
           self.conversation_engine.action_executor.matching_service:
            print("   ✅ Matching service is available - check logs above for 'find_matching_drivers' call")
            self.results.append(("PASS", 7, "Matching service available"))
        else:
            print("   ⚠️ Matching service not available - matching won't occur")
            self.results.append(("FAIL", 7, "Matching service not available"))
        
        print("\n✅ Scenario 1 Complete: Hitchhiker registration with ride request")
    
    def test_driver_scenario(self):
        """
        Test Scenario 2: New driver with routine
        """
        self.clean_start()
        print("\n🎬 SCENARIO 2: New Driver with Routine")
        print("-" * 80)
        
        # Step 1: Initial message
        self.send_message("שלום", 1, "היי בורך הבא")
        
        # Step 2: Provide name
        self.send_message("יוסי נהג", 2, "באיזה ישוב")
        self.verify_user_data("full_name", "יוסי נהג", 2)
        
        # Step 3: Provide settlement
        self.send_message("חיפה", 3, "מה אתה")
        self.verify_user_data("home_settlement", "חיפה", 3)
        
        # Step 4: Choose driver
        self.send_message("3", 4, "שגרת נסיעה")
        self.verify_user_data("user_type", "driver", 4)
        
        # Step 5: Has routine - Yes
        self.send_message("1", 5, "שם של היעד")
        
        # Step 6: Routine destination
        self.send_message("תל אביב", 6, "באיזה ימים")
        self.verify_user_data("routine_destination", "תל אביב", 6)
        
        # Step 7: Days
        self.send_message("א-ה", 7, "באיזה שעה")
        self.verify_user_data("routine_days", "א-ה", 7)
        
        # Step 8: Departure time
        self.send_message("07:00", 8, "באיזה שעה אתה יוצא מ")
        self.verify_user_data("routine_departure_time", "07:00", 8)
        
        # Step 9: Return time (this should trigger save_routine_and_match action)
        print("\n   🔍 Step 9: This should trigger 'save_routine_and_match' action")
        print(f"   🔍 Matching service available: {hasattr(self.conversation_engine.action_executor, 'matching_service') and self.conversation_engine.action_executor.matching_service is not None}")
        print(f"   🔍 User DB uses MongoDB: {hasattr(self.user_db, '_use_mongo') and getattr(self.user_db, '_use_mongo', False)}")
        
        response, buttons = self.send_message("18:00", 9, "עוד יעד")
        self.verify_user_data("routine_return_time", "18:00", 9)
        
        # Verify that matching service was called (check logs or matching happened)
        # The action should have been executed - we can check if matching_service exists
        if hasattr(self.conversation_engine.action_executor, 'matching_service') and \
           self.conversation_engine.action_executor.matching_service:
            print("   ✅ Matching service is available - check logs above for 'find_matching_hitchhikers' call")
            self.results.append(("PASS", 9, "Matching service available"))
        else:
            print("   ⚠️ Matching service not available - matching won't occur")
            print("   ⚠️ This means find_matching_hitchhikers won't be called")
            self.results.append(("FAIL", 9, "Matching service not available"))
        
        # Step 10: No more destinations
        self.send_message("2", 10, "האם תרצה שאני אתריע")
        
        # Step 11: Alert preference - destinations and times
        self.send_message("3", 11, "ההרשמה הושלמה")
        
        print("\n✅ Scenario 2 Complete: Driver registration with routine")
    
    def test_matching_scenario(self):
        """
        Test Scenario: Driver creates routine, then hitchhiker requests ride to same destination
        This should find a match!
        """
        self.clean_start()
        print("\n🎬 SCENARIO: Matching Test - Driver Routine + Hitchhiker Request")
        print("-" * 80)
        
        # First: Create a driver with routine to Tel Aviv
        print("\n📋 PART 1: Creating Driver with Routine")
        print("-" * 40)
        
        driver_phone = "test_driver_001"
        self.user_db.delete_user_data(driver_phone)
        self.user_db.create_user(driver_phone)
        
        # Register driver
        self.conversation_engine.process_message(driver_phone, "שלום")
        self.conversation_engine.process_message(driver_phone, "יוסי נהג")
        self.conversation_engine.process_message(driver_phone, "חיפה")
        self.conversation_engine.process_message(driver_phone, "3")  # Driver
        self.conversation_engine.process_message(driver_phone, "1")  # Has routine
        self.conversation_engine.process_message(driver_phone, "תל אביב")
        self.conversation_engine.process_message(driver_phone, "א-ה")
        self.conversation_engine.process_message(driver_phone, "07:00")
        response, buttons = self.conversation_engine.process_message(driver_phone, "18:00")
        
        print(f"   ✅ Driver routine created: תל אביב, א-ה, 07:00")
        
        # Check if routine was saved
        routines = list(self.user_db.mongo.get_collection("routines").find({"phone_number": driver_phone}))
        if routines:
            print(f"   ✅ Found {len(routines)} routine(s) in database")
        else:
            print("   ❌ No routines found in database!")
        
        # Second: Create a hitchhiker requesting ride to Tel Aviv
        print("\n📋 PART 2: Creating Hitchhiker Request")
        print("-" * 40)
        
        hitchhiker_phone = "test_hitchhiker_001"
        self.user_db.delete_user_data(hitchhiker_phone)
        self.user_db.create_user(hitchhiker_phone)
        
        # Register hitchhiker
        self.conversation_engine.process_message(hitchhiker_phone, "שלום")
        self.conversation_engine.process_message(hitchhiker_phone, "דני טרמפיסט")
        self.conversation_engine.process_message(hitchhiker_phone, "תל אביב")
        self.conversation_engine.process_message(hitchhiker_phone, "2")  # Hitchhiker
        self.conversation_engine.process_message(hitchhiker_phone, "1")  # Looking now
        self.conversation_engine.process_message(hitchhiker_phone, "1")  # Now
        print("\n   🔍 Sending destination - should trigger matching...")
        response, buttons = self.conversation_engine.process_message(hitchhiker_phone, "תל אביב")
        
        print(f"   ✅ Hitchhiker request created: תל אביב")
        
        # Check if ride request was saved
        ride_requests = list(self.user_db.mongo.get_collection("ride_requests").find({"requester_phone": hitchhiker_phone}))
        if ride_requests:
            print(f"   ✅ Found {len(ride_requests)} ride request(s) in database")
            for req in ride_requests:
                print(f"      - Destination: {req.get('destination')}, Type: {req.get('type')}")
        else:
            print("   ❌ No ride requests found in database!")
        
        # Check if matches were created
        print("\n📋 PART 3: Checking for Matches")
        print("-" * 40)
        
        matches = list(self.user_db.mongo.get_collection("matches").find({}))
        if matches:
            print(f"   ✅ Found {len(matches)} match(es) in database!")
            for match in matches:
                print(f"      - Match ID: {match.get('match_id')}, Status: {match.get('status')}")
            self.results.append(("PASS", 1, "Matches found"))
        else:
            print("   ❌ No matches found!")
            print("   ⚠️ This means matching didn't work")
            self.results.append(("FAIL", 1, "No matches found"))
        
        # Cleanup
        self.user_db.delete_user_data(driver_phone)
        self.user_db.delete_user_data(hitchhiker_phone)
        
        print("\n✅ Matching Test Complete")
    
    def test_both_scenario(self):
        """
        Test Scenario 3: User who is both hitchhiker and driver
        """
        self.clean_start()
        print("\n🎬 SCENARIO 3: Both Hitchhiker and Driver")
        print("-" * 80)
        
        # Step 1-3: Initial registration
        self.send_message("היי", 1)
        self.send_message("דני כהן", 2)
        self.send_message("רעננה", 3)
        
        # Step 4: Choose both
        self.send_message("1", 4)
        self.verify_user_data("user_type", "both", 4)
        
        # Step 5: Not looking for ride now
        self.send_message("2", 5, "יעד קבוע")
        
        # Step 6: No default destination
        response, buttons = self.send_message("2", 6)
        
        # Should now ask about routine (driver path)
        if "שגרת נסיעה" in response:
            print("   ✅ Correctly transitioned to driver questions")
            self.results.append(("PASS", 6, "Transition to driver path"))
        else:
            print("   ❌ Did not transition to driver questions")
            self.results.append(("FAIL", 6, "Transition to driver path"))
        
        print("\n✅ Scenario 3 Complete: Both user type flow")
    
    def test_registered_user_menu(self):
        """
        Test Scenario 4: Registered user returning
        """
        self.clean_start()
        print("\n🎬 SCENARIO 4: Registered User Menu")
        print("-" * 80)
        
        # First complete registration
        self.send_message("היי", 1)
        self.send_message("שרה לוי", 2)
        self.send_message("באר שבע", 3)
        self.send_message("2", 4)  # Hitchhiker
        self.send_message("2", 5)  # Not looking now
        self.send_message("2", 6)  # No default destination
        
        # Mark as registered
        self.user_db.complete_registration(self.test_phone)
        
        # Set to idle
        self.user_db.set_user_state(self.test_phone, 'idle')
        
        # Now send new message - should show menu
        response, buttons = self.send_message("שלום", 7)
        
        if "מה תרצה לעשות" in response:
            print("   ✅ Registered user menu displayed")
            self.results.append(("PASS", 7, "Registered user menu"))
        else:
            print("   ❌ Menu not displayed")
            self.results.append(("FAIL", 7, "Registered user menu"))
        
        if buttons and len(buttons) >= 4:
            print(f"   ✅ Menu has {len(buttons)} options")
            self.results.append(("PASS", 7, "Menu buttons"))
        else:
            print(f"   ❌ Menu should have 4+ options, got {len(buttons) if buttons else 0}")
            self.results.append(("FAIL", 7, "Menu buttons"))
        
        print("\n✅ Scenario 4 Complete: Registered user menu")
    
    def test_special_commands(self):
        """
        Test Scenario 5: Special commands
        """
        self.clean_start()
        print("\n🎬 SCENARIO 5: Special Commands")
        print("-" * 80)
        
        # Start registration
        self.send_message("test", 1)
        self.send_message("טסט יוזר", 2)
        
        # Test restart command
        response, buttons = self.send_message("חדש", 3)
        
        if "היי בורך הבא" in response:
            print("   ✅ Restart command works")
            self.results.append(("PASS", 3, "Restart command"))
        else:
            print("   ❌ Restart command failed")
            self.results.append(("FAIL", 3, "Restart command"))
        
        # Test help command
        response, buttons = self.send_message("עזרה", 4)
        
        if "פקודות זמינות" in response:
            print("   ✅ Help command works")
            self.results.append(("PASS", 4, "Help command"))
        else:
            print("   ❌ Help command failed")
            self.results.append(("FAIL", 4, "Help command"))
        
        print("\n✅ Scenario 5 Complete: Special commands")
    
    def test_buttons_generation(self):
        """
        Test Scenario 6: Button generation
        """
        self.clean_start()
        print("\n🎬 SCENARIO 6: Button Generation")
        print("-" * 80)
        
        # Get to a choice question
        self.send_message("test", 1)
        self.send_message("בדיקה", 2)
        response, buttons = self.send_message("עיר בדיקה", 3)
        
        # Should show buttons for user type (3 options + 1 restart button = 4 total)
        if buttons and len(buttons) == 4:
            print(f"   ✅ Generated 4 buttons (3 options + restart)")
            self.results.append(("PASS", 3, "Button generation"))
            
            # Check button format
            if all('id' in btn and 'title' in btn for btn in buttons):
                print("   ✅ Buttons have correct format")
                self.results.append(("PASS", 3, "Button format"))
            else:
                print("   ❌ Buttons missing required fields")
                self.results.append(("FAIL", 3, "Button format"))
            
            # Verify restart button exists
            restart_btn = next((btn for btn in buttons if btn['id'] == 'restart_button'), None)
            if restart_btn:
                print(f"   ✅ Restart button present: {restart_btn['title']}")
                self.results.append(("PASS", 3, "Restart button"))
            else:
                print("   ❌ Restart button not found")
                self.results.append(("FAIL", 3, "Restart button"))
        else:
            print(f"   ❌ Expected 4 buttons, got {len(buttons) if buttons else 0}")
            self.results.append(("FAIL", 3, "Button generation"))
        
        print("\n✅ Scenario 6 Complete: Button generation")
    
    def test_restart_button_functionality(self):
        """
        Test Scenario 7: Restart button functionality
        Verify that the restart button restarts conversation at any point
        """
        self.clean_start()
        print("\n🎬 SCENARIO 7: Restart Button Functionality")
        print("-" * 80)
        
        # Start conversation
        self.send_message("Hello", 1)
        self.send_message("כפיר", 2)
        response, buttons = self.send_message("תל אביב", 3)
        
        # At this point, we're at "ask_user_type" with buttons
        print(f"\n📍 Step 4: At user type question with {len(buttons)} buttons")
        
        # Find and click restart button
        restart_btn = next((btn for btn in buttons if btn['id'] == 'restart_button'), None)
        if restart_btn:
            print(f"   ✅ Found restart button: {restart_btn['title']}")
            self.results.append(("PASS", 4, "Find restart button"))
            
            # Click restart button
            response, buttons = self.send_message("restart_button", 5, "היי בורך הבא")
            
            # Verify user data was reset
            full_name = self.user_db.get_profile_value(self.test_phone, "full_name")
            home_settlement = self.user_db.get_profile_value(self.test_phone, "home_settlement")
            
            if full_name is None and home_settlement is None:
                print("   ✅ User data was reset")
                self.results.append(("PASS", 5, "Data reset"))
            else:
                print(f"   ❌ User data not reset: name={full_name}, settlement={home_settlement}")
                self.results.append(("FAIL", 5, "Data reset"))
            
            # Verify we're back at the beginning (ask_full_name)
            if "היי בורך הבא" in response and "שם מלא" in response:
                print("   ✅ Conversation restarted from beginning")
                self.results.append(("PASS", 5, "Restart to beginning"))
            else:
                print(f"   ❌ Did not restart to beginning. Response: {response[:200]}")
                self.results.append(("FAIL", 5, "Restart to beginning"))
        else:
            print("   ❌ Restart button not found")
            self.results.append(("FAIL", 4, "Find restart button"))
        
        # Test restart button from a different state
        print("\n📍 Step 6: Testing restart from mid-registration")
        self.send_message("דני", 6)
        self.send_message("חיפה", 7)
        response, buttons = self.send_message("hitchhiker", 8)
        
        # Should be at "ask_want_ride_now" with buttons
        if buttons and any(btn['id'] == 'restart_button' for btn in buttons):
            response, buttons = self.send_message("restart_button", 9, "היי בורך הבא")
            
            if "היי בורך הבא" in response:
                print("   ✅ Restart works from different state")
                self.results.append(("PASS", 9, "Restart from different state"))
            else:
                print("   ❌ Restart failed from different state")
                self.results.append(("FAIL", 9, "Restart from different state"))
        
        print("\n✅ Scenario 7 Complete: Restart button functionality")
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*80)
        print("📊 TEST SUMMARY")
        print("="*80)
        
        passed = sum(1 for r in self.results if r[0] == "PASS")
        failed = sum(1 for r in self.results if r[0] == "FAIL")
        total = passed + failed
        
        print(f"\n✅ Passed: {passed}/{total}")
        print(f"❌ Failed: {failed}/{total}")
        
        if failed > 0:
            print("\n❌ Failed Tests:")
            for result, step, desc in self.results:
                if result == "FAIL":
                    print(f"   Step {step}: {desc}")
        
        print("\n" + "="*80)
        
        if failed == 0:
            print("🎉 ALL TESTS PASSED! 🎉")
        else:
            print(f"⚠️  {failed} TEST(S) FAILED")
        print("="*80)
        
        return failed == 0

def main():
    """Run all tests"""
    tester = ConversationTester()
    
    try:
        # Run all scenarios
        tester.test_hitchhiker_scenario()
        tester.test_driver_scenario()
        tester.test_matching_scenario()  # Test actual matching
        tester.test_both_scenario()
        tester.test_registered_user_menu()
        tester.test_special_commands()
        tester.test_buttons_generation()
        tester.test_restart_button_functionality()
        
        # Print summary
        all_passed = tester.print_summary()
        
        # Exit with appropriate code
        sys.exit(0 if all_passed else 1)
        
    except Exception as e:
        print(f"\n❌ TEST SUITE FAILED WITH ERROR:")
        print(f"   {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(2)

if __name__ == '__main__':
    main()

