#!/usr/bin/env python3
"""Quick debug test"""

import sys
import os
# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.user_database import UserDatabase
from src.conversation_engine import ConversationEngine

# Setup
from src.user_logger import UserLogger
user_db = UserDatabase('debug_user_data.json')
user_logger = UserLogger()
engine = ConversationEngine(user_db=user_db, user_logger=user_logger)
phone = "test_debug"

# Clean start
user_db.delete_user_data(phone)

print("="*80)
print("DEBUG TEST: Text Input State Transitions")
print("="*80)

# Step 1
print("\n>>> User sends: 'Hello'")
response, buttons = engine.process_message(phone, "Hello")
print(f"Bot: {response[:100]}")
state = user_db.get_user_state(phone)
print(f"Current state: {state}")
context = user_db.get_user_context(phone)
print(f"Context: {context}")

# Step 2
print("\n>>> User sends: 'כפיר'")
response, buttons = engine.process_message(phone, "כפיר")
print(f"Bot: {response}")
state = user_db.get_user_state(phone)
print(f"Current state: {state}")
context = user_db.get_user_context(phone)
print(f"Context: {context}")
profile = user_db.get_user(phone)['profile']
print(f"Profile: {profile}")

# Step 3 - THE PROBLEM
print("\n>>> User sends: 'תל אביב'")
response, buttons = engine.process_message(phone, "תל אביב")
print(f"Bot: {response}")
state = user_db.get_user_state(phone)
print(f"Current state: {state}")
context = user_db.get_user_context(phone)
print(f"Context: {context}")
profile = user_db.get_user(phone)['profile']
print(f"Profile: {profile}")

print("\n" + "="*80)
if state == 'ask_user_type':
    print("✅ SUCCESS: State transitioned to ask_user_type")
else:
    print(f"❌ FAIL: State is '{state}', expected 'ask_user_type'")

if profile.get('home_settlement') == 'תל אביב':
    print("✅ SUCCESS: home_settlement saved")
else:
    print(f"❌ FAIL: home_settlement is '{profile.get('home_settlement')}', expected 'תל אביב'")

