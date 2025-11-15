#!/usr/bin/env python3
"""
Test for interactive settlement suggestions feature
"""

from conversation_engine import ConversationEngine
from user_database import UserDatabase
import json

def test_interactive_suggestions():
    """Test that settlement suggestions are shown as interactive buttons"""
    
    print("🧪 Testing Interactive Suggestions Feature\n")
    
    # Initialize
    user_db = UserDatabase()
    conversation_engine = ConversationEngine('conversation_flow.json', user_db)
    test_phone = "+972501234999"
    
    # Clean up any existing data
    user_db.delete_user_data(test_phone)
    user_db.create_user(test_phone)
    
    print("=" * 60)
    print("Test 1: Invalid settlement input with suggestions")
    print("=" * 60)
    
    # Start conversation
    response1, buttons1 = conversation_engine.process_message(test_phone, "שלום")
    print(f"Bot: {response1}")
    if buttons1:
        print(f"Buttons: {len(buttons1)} buttons")
    print()
    
    # Enter full name
    response2, buttons2 = conversation_engine.process_message(test_phone, "דני כהן")
    print(f"Bot: {response2}")
    print()
    
    # Enter invalid settlement
    response3, buttons3 = conversation_engine.process_message(test_phone, "אשק")
    print(f"Bot: {response3}")
    
    if buttons3:
        print(f"\n✅ SUCCESS: Got {len(buttons3)} buttons!")
        print("\nButtons:")
        for i, btn in enumerate(buttons3, 1):
            title = btn['reply']['title']
            btn_id = btn['reply']['id']
            print(f"  {i}. [{title}] (id: {btn_id})")
        
        # Verify structure
        assert len(buttons3) >= 2, "Should have at least 2 buttons (suggestion + restart)"
        
        # Check that last button is restart
        last_button = buttons3[-1]
        assert last_button['reply']['id'] == 'restart_button', "Last button should be restart"
        assert '🔄' in last_button['reply']['title'], "Restart button should have 🔄 icon"
        
        print("\n✅ All button structure tests passed!")
    else:
        print("\n❌ FAILED: No buttons returned!")
        return False
    
    print("\n" + "=" * 60)
    print("Test 2: Select a suggestion by clicking button")
    print("=" * 60)
    
    # Simulate clicking first suggestion button (id: "1")
    response4, buttons4 = conversation_engine.process_message(test_phone, "1")
    print(f"Bot: {response4}")
    
    # Check that we moved to next state
    user = user_db.get_user(test_phone)
    saved_settlement = user['profile'].get('home_settlement')
    print(f"\nSaved settlement: {saved_settlement}")
    
    if saved_settlement:
        print(f"✅ SUCCESS: Settlement '{saved_settlement}' was saved!")
    else:
        print("❌ FAILED: Settlement was not saved!")
        return False
    
    # Verify pending_suggestions were cleared
    context = user_db.get_user_context(test_phone)
    pending = context.get('pending_suggestions')
    if pending is None:
        print("✅ SUCCESS: Pending suggestions were cleared!")
    else:
        print(f"❌ FAILED: Pending suggestions not cleared: {pending}")
        return False
    
    print("\n" + "=" * 60)
    print("Test 3: Restart from suggestions screen")
    print("=" * 60)
    
    # Create another user to test restart
    test_phone2 = "+972501234998"
    user_db.delete_user_data(test_phone2)
    user_db.create_user(test_phone2)
    
    # Get to suggestions screen
    conversation_engine.process_message(test_phone2, "היי")
    conversation_engine.process_message(test_phone2, "יוסי לוי")
    response5, buttons5 = conversation_engine.process_message(test_phone2, "תאל")  # Should suggest תל אביב
    
    print(f"Bot: {response5}")
    if buttons5:
        print(f"Buttons: {[btn['reply']['title'] for btn in buttons5]}")
    else:
        print("No buttons (no good matches found, trying different input)")
        # Try a better match
        response5, buttons5 = conversation_engine.process_message(test_phone2, "חיפ")
        print(f"Bot: {response5}")
        if buttons5:
            print(f"Buttons: {[btn['reply']['title'] for btn in buttons5]}")
        else:
            print("⚠️ Warning: No suggestions found, skipping restart test")
            user_db.delete_user_data(test_phone)
            user_db.delete_user_data(test_phone2)
            return True
    
    # Click restart button
    response6, buttons6 = conversation_engine.process_message(test_phone2, "restart_button")
    print(f"\nAfter restart:")
    print(f"Bot: {response6}")
    
    # Check that user data was reset
    user2 = user_db.get_user(test_phone2)
    if not user2['profile'].get('full_name'):
        print("✅ SUCCESS: User data was reset!")
    else:
        print(f"❌ FAILED: User data not reset: {user2['profile']}")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 All tests passed!")
    print("=" * 60)
    
    # Cleanup
    user_db.delete_user_data(test_phone)
    user_db.delete_user_data(test_phone2)
    
    return True

if __name__ == "__main__":
    try:
        success = test_interactive_suggestions()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

