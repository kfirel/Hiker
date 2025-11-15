# 🗣️ Conversation Flow System - Complete Guide

## Overview

Your WhatsApp bot now has a sophisticated **conversational flow system** for the hitchhiking (טרמפ) application. The bot can:

- ✅ Register new users with complete profiles
- ✅ Handle different user types (hitchhiker, driver, or both)
- ✅ Manage ride requests
- ✅ Track driving routines
- ✅ Provide context-aware responses
- ✅ Remember user state across conversations

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     WhatsApp Message                        │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                      app.py                                 │
│              (Main Flask Application)                       │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│               conversation_engine.py                        │
│         (Processes messages using flow logic)               │
└──────────┬──────────────────────────────┬───────────────────┘
           ↓                              ↓
┌──────────────────────┐      ┌──────────────────────┐
│ conversation_flow.json│      │   user_database.py  │
│  (Flow definition)    │      │  (User data store)  │
└──────────────────────┘      └──────────────────────┘
           ↓                              ↓
┌─────────────────────────────────────────────────────────────┐
│                  whatsapp_client.py                         │
│                 (Send responses back)                       │
└─────────────────────────────────────────────────────────────┘
```

## 📁 New Files Created

### 1. `conversation_flow.json`
**Purpose:** Defines the complete conversation flow

**Structure:**
```json
{
  "states": {
    "state_id": {
      "message": "Message to user",
      "expected_input": "choice | text",
      "options": { ... },
      "next_state": "next_state_id",
      "save_to": "profile_field"
    }
  },
  "commands": {
    "חזור": "go_back",
    "חדש": "restart",
    ...
  }
}
```

### 2. `user_database.py`
**Purpose:** Stores and manages user data

**Features:**
- User profiles
- Conversation state tracking
- Ride requests
- Driving routines
- Preferences

**Storage:** JSON file (`user_data.json`)

### 3. `conversation_engine.py`
**Purpose:** Processes messages according to the flow

**Key Methods:**
- `process_message()` - Main entry point
- `_handle_choice_input()` - Handles numbered choices
- `_handle_text_input()` - Handles free text
- `_check_condition()` - Evaluates state conditions

### 4. Updated `app.py`
**Changes:**
- Integrated conversation engine
- Stores user database
- Processes all messages through flow

## 🌊 Flow Structure

### Registration Flow (New Users)

```
1. initial
   ↓
2. ask_full_name
   ↓
3. ask_settlement
   ↓
4. ask_user_type
   ├─→ (1) Both → ask_looking_for_ride_now
   ├─→ (2) Hitchhiker → ask_looking_for_ride_now
   └─→ (3) Driver → ask_has_routine
```

### Hitchhiker Path

```
ask_looking_for_ride_now
├─→ (1) Yes
│   ├─→ ask_destination
│   ├─→ ask_when
│   │   ├─→ (1) Soon → ask_time_range
│   │   └─→ (2) Specific → ask_specific_datetime
│   └─→ complete_ride_request
│
└─→ (2) No
    └─→ ask_set_default_destination
        ├─→ (1) Yes → ask_default_destination_name
        └─→ (2) No → (continue)
```

### Driver Path

```
ask_has_routine
├─→ (1) Yes
│   ├─→ ask_routine_destination
│   ├─→ ask_routine_days
│   ├─→ ask_routine_departure_time
│   ├─→ ask_routine_return_time
│   └─→ ask_another_routine_destination
│       ├─→ (1) Yes → (repeat routine)
│       └─→ (2) No → ask_alert_preference
│
└─→ (2) No
    └─→ ask_alert_frequency
```

### Registered User Menu

When a registered user sends a message:

```
registered_user_menu
├─→ (1) מחפש טרמפ → ask_destination_registered
├─→ (2) מתכנן יציאה → ask_trip_planning
├─→ (3) עדכון שגרה → ask_has_routine
└─→ (4) עדכון פרטים → ask_what_to_update
```

## 🎮 Special Commands

Users can use these commands at any time:

| Command | Action | Description |
|---------|--------|-------------|
| `חזור` | Go back | Return to previous step (not yet implemented) |
| `חדש` | Restart | Start registration from beginning |
| `מחק` | Delete data | Delete all user data |
| `עזרה` | Show help | Show available commands |
| `תפריט` | Show menu | Return to main menu (registered users) |

## 💾 Data Storage

### User Data Structure

```json
{
  "users": {
    "972524297932": {
      "phone_number": "972524297932",
      "created_at": "2025-11-15T00:00:00",
      "registered": true,
      "profile": {
        "full_name": "כפיר",
        "home_settlement": "תל אביב",
        "user_type": "both",
        "default_destination": "ירושלים",
        "routine_destination": "ירושלים",
        "routine_days": "א-ה",
        "routine_departure_time": "08:00",
        "routine_return_time": "18:00"
      },
      "state": {
        "current_state": "idle",
        "context": {},
        "history": [...]
      },
      "preferences": {
        "alert_preference": "my_destinations_and_times"
      },
      "ride_requests": [
        {
          "destination": "חיפה",
          "time_range": "14:00-16:00",
          "timestamp": "2025-11-15T14:30:00",
          "status": "active"
        }
      ],
      "routines": [...]
    }
  }
}
```

Stored in: `user_data.json`

## 🔧 How to Customize the Flow

### Adding a New State

Edit `conversation_flow.json`:

```json
"ask_new_question": {
  "id": "ask_new_question",
  "message": "השאלה החדשה שלך?",
  "expected_input": "text",
  "save_to": "new_field",
  "next_state": "next_state_id"
}
```

### Adding a New Choice Option

```json
"ask_with_choices": {
  "message": "בחר אפשרות:",
  "expected_input": "choice",
  "options": {
    "1": {
      "label": "אפשרות 1",
      "value": "option1",
      "next_state": "state_after_option1"
    },
    "2": {
      "label": "אפשרות 2",
      "value": "option2",
      "next_state": "state_after_option2"
    }
  },
  "save_to": "choice_field"
}
```

### Adding Conditional Logic

```json
"check_condition_state": {
  "condition": "user_type_is_both",
  "next_state": "state_if_true",
  "else_next_state": "state_if_false"
}
```

Available conditions:
- `user_not_registered`
- `user_registered`
- `user_type_is_both`
- `has_default_destination`

### Adding Variable Substitution

In any message, use `{variable_name}` to insert values from user profile:

```json
"message": "שלום {full_name}, אתה גר ב{home_settlement}, נכון?"
```

## 🧪 Testing the Flow

### Test New User Registration

```
You: [any message]
Bot: היי בורך הבא להייקר הצ'אט בוט לטרמפיסט...

You: כפיר אלגבסי
Bot: באיזה ישוב אתה גר?

You: תל אביב
Bot: מה אתה?
     1. טרמפיסט ונהג
     2. טרמפיסט
     3. נהג

You: 1
Bot: מעולה! האם אתה מחפש כרגע טרמפ?
     1. כן
     2. לא
```

### Test Registered User

```
You: היי
Bot: היי כפיר! 👋
     מה תרצה לעשות?
     1. אני מחפש טרמפ
     2. אני עומד מתכנן יציאה או חזרה
     3. אני רוצה לעדכן את השגרה שלי
     4. עדכון פרטים אישיים
```

### Test Commands

```
You: חדש
Bot: [Restarts from beginning]

You: תפריט
Bot: [Shows main menu]

You: עזרה
Bot: פקודות זמינות:
     - חזור: חזרה שלב אחורה
     - חדש: התחלה מחדש
     ...
```

## 📊 Monitoring User Data

### View User Database

```bash
cat user_data.json | python -m json.tool
```

### View User States

```bash
# Install jq for better JSON viewing (optional)
brew install jq  # macOS
# or
apt-get install jq  # Linux

# View all users and their states
cat user_data.json | jq '.users | to_entries[] | {phone: .key, state: .value.state.current_state, registered: .value.registered}'
```

### Check Ride Requests

```bash
cat user_data.json | jq '.users | to_entries[] | {phone: .key, requests: .value.ride_requests}'
```

## 🐛 Debugging

### Enable Debug Logging

Edit `app.py`:

```python
logging.basicConfig(
    level=logging.DEBUG,  # Changed from INFO
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### Check Conversation State

Add this endpoint to `app.py` for debugging:

```python
@app.route('/debug/user/<phone_number>', methods=['GET'])
def debug_user(phone_number):
    """Debug endpoint to view user data"""
    user = user_db.get_user(phone_number)
    if user:
        return jsonify(user), 200
    return jsonify({'error': 'User not found'}), 404
```

Access: `http://localhost:5000/debug/user/972524297932`

### Common Issues

**Issue: Bot doesn't respond**
- Check logs for errors
- Verify conversation_flow.json is valid JSON
- Check state exists in flow

**Issue: Bot stuck in a state**
- User can send `חדש` to restart
- Or manually reset: `user_db.reset_user_state(phone_number)`

**Issue: Wrong state transitions**
- Check `next_state` in flow definition
- Verify conditions are correctly evaluated
- Check logs for state transitions

## 🚀 Advanced Features

### Adding Custom Actions

Edit `conversation_engine.py`, add to `_perform_action()`:

```python
elif action == 'my_custom_action':
    # Your custom logic here
    logger.info(f"Performing custom action for {phone_number}")
```

Then use in flow:

```json
{
  "state_id": {
    "message": "Message",
    "action": "my_custom_action",
    "next_state": "next"
  }
}
```

### Adding Custom Conditions

Edit `conversation_engine.py`, add to `_check_condition()`:

```python
elif condition == 'my_custom_condition':
    # Your condition logic
    return user_db.get_profile_value(phone_number, 'some_field') == 'some_value'
```

### Integrating with External Services

You can call external APIs in actions:

```python
elif action == 'find_matching_drivers':
    ride_request = data
    # Call matching service
    matches = matching_service.find_drivers(ride_request)
    # Notify user
    whatsapp_client.send_message(phone_number, f"נמצאו {len(matches)} נהגים!")
```

## 📝 Best Practices

1. **Keep messages concise** - WhatsApp users prefer short messages
2. **Use numbered choices** - Easier for users to select
3. **Validate input** - Check for expected format before saving
4. **Provide fallbacks** - Handle unexpected input gracefully
5. **Log everything** - Helps with debugging
6. **Test all paths** - Try every possible user journey
7. **Back up user_data.json** - Don't lose user data!

## 🎯 Next Steps

Potential enhancements:

1. **Matching Algorithm** - Match hitchhikers with drivers
2. **Notifications** - Send alerts when matches are found
3. **Real Database** - Replace JSON with PostgreSQL/MongoDB
4. **Admin Panel** - Web interface to manage users/requests
5. **Analytics** - Track usage patterns
6. **Localization** - Support multiple languages
7. **Media Support** - Handle images/locations
8. **Payment Integration** - Optional ride payments

## 📞 Support

- **Flow issues:** Check `conversation_flow.json` syntax
- **State issues:** View `user_data.json`
- **Logic issues:** Check logs in terminal
- **Data issues:** Use debug endpoint

Your bot is now ready for sophisticated conversations! 🚀

