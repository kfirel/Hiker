# 🔘 Interactive Buttons Guide

## Overview

Your WhatsApp bot now supports **interactive buttons and lists** instead of requiring users to type numbers!

Users can tap buttons directly in WhatsApp instead of typing "1", "2", "3", etc.

---

## 🎯 What Changed?

### Before (Typing Numbers)
```
Bot: מה אתה?

     1. טרמפיסט ונהג
     2. טרמפיסט
     3. נהג

You: 1     ← User had to type "1"
```

### After (Tapping Buttons)
```
Bot: מה אתה?

     [טרמפיסט ונהג] [טרמפיסט] [נהג]
     ↑ User taps the button directly!
```

---

## 📱 How It Works

### For 1-3 Options: Reply Buttons
WhatsApp shows **clickable reply buttons** below the message.

**Example:**
```
Message: מה אתה?

┌─────────────────────┐
│ טרמפיסט ונהג         │  ← Button 1
├─────────────────────┤
│ טרמפיסט              │  ← Button 2
├─────────────────────┤
│ נהג                  │  ← Button 3
└─────────────────────┘
```

### For 4+ Options: List Message
WhatsApp shows a **"בחר אפשרות" button** that opens a list.

**Example:**
```
Message: מה התדירות שאתה רוצה?

[בחר אפשרות]  ← User taps this
       ↓
┌──────────────────────────────┐
│ אפשרויות                     │
├──────────────────────────────┤
│ 1. כל איזור וכל שעה          │
│ 2. איזור מסוים בכל שעה       │
│ 3. איזור מסוים ושעה מסוימת   │
│ 4. אל תשלח                   │
└──────────────────────────────┘
```

---

## 🔧 How It's Implemented

### 1. WhatsApp Client (`whatsapp_client.py`)

Added two new methods:

#### `send_button_message()`
- For 1-3 buttons
- Creates reply buttons below message
- Max 20 characters per button title

#### `send_list_message()`
- For 4-10 items
- Creates list with "בחר אפשרות" button
- Max 24 characters per title
- Optional 72-character descriptions

### 2. Conversation Engine (`conversation_engine.py`)

Added `_build_buttons()` method:
- Automatically extracts options from conversation flow
- Converts them to button format
- Returns button list or None

### 3. App (`app.py`)

Updated `process_message()`:
- Handles `interactive` message type (button clicks)
- Extracts button ID from response
- Passes buttons to WhatsApp client

---

## 📝 Conversation Flow Format

Your `conversation_flow.json` **doesn't need to change!**

The system automatically converts your existing options into buttons:

```json
{
  "ask_user_type": {
    "message": "מה אתה?",
    "expected_input": "choice",
    "options": {
      "1": {
        "label": "טרמפיסט ונהג",
        "value": "both",
        "next_state": "..."
      },
      "2": {
        "label": "טרמפיסט",
        "value": "hitchhiker",
        "next_state": "..."
      },
      "3": {
        "label": "נהג",
        "value": "driver",
        "next_state": "..."
      }
    }
  }
}
```

**Result:** 3 buttons are automatically created!

---

## 🎨 Button Behavior

### Automatic Selection

The bot **automatically** chooses the right format:

| Number of Options | Format Used | WhatsApp Component |
|-------------------|-------------|--------------------|
| 1-3 options | Reply Buttons | `interactive` → `button` |
| 4-10 options | List Message | `interactive` → `list` |
| Text input | No buttons | Regular text message |

### Button Limits

**Reply Buttons:**
- Max 3 buttons
- Max 20 characters per button title
- Buttons appear below message

**List Messages:**
- Max 10 items
- Max 24 characters per title
- Max 72 characters per description (optional)
- Appears as scrollable list

---

## 🧪 Testing

### Test Reply Buttons (1-3 Options)

**States that will show buttons:**
- `ask_user_type` (3 options)
- `ask_looking_for_ride_now` (2 options: כן/לא)
- `ask_when` (2 options)
- `ask_set_default_destination` (2 options)
- `ask_has_routine` (2 options)
- `ask_another_routine_destination` (2 options)

**How to test:**
1. Start registration
2. Progress to a choice question
3. **Look for buttons** below the message
4. **Tap a button** (don't type)
5. Bot should respond correctly

### Test List Messages (4+ Options)

**States that will show lists:**
- `ask_alert_preference` (3 options, but can be extended)
- `ask_alert_frequency` (4 options) ✅
- `registered_user_menu` (4 options) ✅

**How to test:**
1. Complete registration
2. Send a message after idle
3. **Look for "בחר אפשרות" button**
4. **Tap it** to open list
5. **Select an option**
6. Bot should respond correctly

---

## 🔍 Debugging

### Check Logs

When a button is clicked, you'll see:

```bash
INFO:__main__:Processing message from 972524297932: 1
INFO:__main__:Sent response to 972524297932 (with buttons: 3)
```

### Button Not Appearing?

**Check:**
1. Is `expected_input` set to `"choice"`?
2. Does the state have `options`?
3. Are there 1-10 options? (0 or 11+ won't work)
4. Check logs for errors

### User Can Still Type

**That's intentional!** Users can:
- Tap the button (preferred)
- OR type the number (fallback)

Both work the same way.

---

## 💡 Customization

### Change Button Text

Edit `conversation_flow.json`:

```json
"options": {
  "1": {
    "label": "Your Custom Button Text",  ← Change this
    "value": "...",
    "next_state": "..."
  }
}
```

**Character limits:**
- Reply buttons: 20 characters max
- List items: 24 characters max

### Add Button Descriptions (Lists Only)

For list messages, you can add descriptions:

```json
"options": {
  "1": {
    "label": "כל איזור וכל שעה",
    "description": "קבל התרעות על כל טרמפ שמתבקש",  ← Optional
    "value": "all",
    "next_state": "..."
  }
}
```

**Note:** Descriptions only work for lists (4+ options), not reply buttons.

### Disable Buttons for a State

If you want text-only for a specific state:

**Option 1:** Change `expected_input` to `"text"`:
```json
{
  "expected_input": "text",  ← No buttons
  "save_to": "field_name"
}
```

**Option 2:** Leave as-is, users can still type numbers.

---

## 🎯 User Experience

### Advantages

✅ **Faster** - One tap vs typing  
✅ **Clearer** - Visual buttons are easier to understand  
✅ **Less errors** - No typos ("1 " vs "1")  
✅ **More professional** - Modern WhatsApp UX  
✅ **Backward compatible** - Typing numbers still works  

### Limitations

⚠️ Reply buttons max: 3  
⚠️ List items max: 10  
⚠️ Button text length limited  
⚠️ No custom styling/colors  

---

## 📊 Message Format Examples

### Reply Button Payload (Sent to WhatsApp)

```json
{
  "messaging_product": "whatsapp",
  "recipient_type": "individual",
  "to": "972524297932",
  "type": "interactive",
  "interactive": {
    "type": "button",
    "body": {
      "text": "מה אתה?"
    },
    "action": {
      "buttons": [
        {
          "type": "reply",
          "reply": {
            "id": "1",
            "title": "טרמפיסט ונהג"
          }
        },
        {
          "type": "reply",
          "reply": {
            "id": "2",
            "title": "טרמפיסט"
          }
        }
      ]
    }
  }
}
```

### List Message Payload (Sent to WhatsApp)

```json
{
  "messaging_product": "whatsapp",
  "recipient_type": "individual",
  "to": "972524297932",
  "type": "interactive",
  "interactive": {
    "type": "list",
    "body": {
      "text": "מה התדירות?"
    },
    "action": {
      "button": "בחר אפשרות",
      "sections": [
        {
          "title": "אפשרויות",
          "rows": [
            {
              "id": "1",
              "title": "כל איזור וכל שעה"
            },
            {
              "id": "2",
              "title": "איזור מסוים"
            }
          ]
        }
      ]
    }
  }
}
```

### Button Response (Received from WhatsApp)

When user clicks a button:

```json
{
  "type": "interactive",
  "interactive": {
    "type": "button_reply",
    "button_reply": {
      "id": "1",
      "title": "טרמפיסט ונהג"
    }
  }
}
```

App extracts: `"1"` and processes as if user typed it.

---

## 🔧 Advanced Customization

### Custom Button Ordering

Buttons appear in the order defined in `options` dict:

```json
"options": {
  "1": {...},  ← First button
  "2": {...},  ← Second button
  "3": {...}   ← Third button
}
```

### Dynamic Buttons Based on User Data

You can modify `_build_buttons()` in `conversation_engine.py` to create conditional buttons:

```python
def _build_buttons(self, state: Dict[str, Any]) -> Optional[list]:
    # ... existing code ...
    
    # Example: Add button based on user type
    user_type = self.user_db.get_profile_value(phone_number, 'user_type')
    if user_type == 'driver':
        buttons.append({
            'id': 'special',
            'title': 'אפשרות מיוחדת לנהגים'
        })
    
    return buttons
```

### Multi-Section Lists

For very complex lists, you can modify `send_list_message()` to support multiple sections:

```python
'sections': [
    {
        'title': 'מיקומים',
        'rows': [...]
    },
    {
        'title': 'זמנים',
        'rows': [...]
    }
]
```

---

## ✅ Testing Checklist

- [ ] Start registration flow
- [ ] See buttons for user type question
- [ ] Tap button (don't type)
- [ ] Bot responds correctly
- [ ] Continue through flow with buttons
- [ ] Test registered user menu (4 options = list)
- [ ] Tap "בחר אפשרות" button
- [ ] Select from list
- [ ] Verify bot processes selection
- [ ] Try typing numbers (should still work)
- [ ] Check logs show button clicks

---

## 🆘 Troubleshooting

### Buttons Not Showing

**1. Check WhatsApp Version**
- Interactive messages require WhatsApp Business API
- Works on all modern WhatsApp versions

**2. Check Meta Dashboard**
- Ensure your app has interactive message permissions
- Go to: WhatsApp → Settings → Permissions

**3. Check Logs**
```bash
# Should see:
INFO:whatsapp_client:Button message sent successfully
# or
INFO:whatsapp_client:List message sent successfully
```

### Buttons Show But Don't Work

**Check webhook is receiving interactive messages:**
```bash
# Logs should show:
INFO:__main__:Processing message from ...: 1
```

**If you see error:**
```bash
ERROR:whatsapp_client:Failed to send button message
```

Check the API response for details.

### API Returns Error 400

**Common causes:**
1. Button title too long (>20 chars for buttons, >24 for lists)
2. Too many buttons (>3 for reply, >10 for list)
3. Invalid payload format

**Fix:** Check character limits in `whatsapp_client.py`:
```python
'title': btn['title'][:20]  # Truncates at 20 chars
```

---

## 📚 Learn More

**WhatsApp Cloud API Documentation:**
- [Interactive Messages](https://developers.facebook.com/docs/whatsapp/cloud-api/guides/send-messages#interactive-messages)
- [Reply Buttons](https://developers.facebook.com/docs/whatsapp/cloud-api/reference/messages#interactive-object)
- [List Messages](https://developers.facebook.com/docs/whatsapp/cloud-api/reference/messages#interactive-list-messages)

---

## 🎉 Summary

Your bot now automatically creates interactive buttons for all choice-based questions!

**Features:**
- ✅ Automatic button generation
- ✅ Reply buttons (1-3 options)
- ✅ List messages (4-10 options)
- ✅ Backward compatible (typing still works)
- ✅ No changes needed to conversation flow
- ✅ Full Hebrew support

**Just restart your bot and test it!** 🚀

```bash
# Restart bot
python app.py

# Send message and look for buttons!
```

