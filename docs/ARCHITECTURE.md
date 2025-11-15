# WhatsApp Bot Architecture

## System Overview

```
┌─────────────────┐          ┌──────────────────┐          ┌─────────────────┐
│   WhatsApp      │          │   Meta Cloud     │          │   Your Bot      │
│   User          │  ◄─────► │   API Server     │  ◄─────► │  (Flask App)    │
│   (Phone)       │          │                  │          │   app.py        │
└─────────────────┘          └──────────────────┘          └─────────────────┘
                                      ▲                              ▲
                                      │                              │
                                      │                       ┌──────┴──────┐
                                      │                       │   ngrok     │
                                      │                       │  (Tunnel)   │
                                      └───────────────────────┤ Local:5000  │
                                            Webhook           └─────────────┘
```

## Component Details

### 1. Flask App (app.py)
**Purpose:** Main application that receives and processes WhatsApp messages

**Endpoints:**
- `GET /webhook` - Webhook verification (Meta validates your server)
- `POST /webhook` - Receives incoming WhatsApp messages
- `GET /health` - Health check endpoint

**Flow:**
1. Receives webhook POST from Meta with message data
2. Extracts message details (sender, text content)
3. Processes message logic (check if "hello")
4. Triggers timer for follow-up message
5. Sends response via WhatsApp Client

### 2. WhatsApp Client (whatsapp_client.py)
**Purpose:** Handles all outgoing WhatsApp messages via Meta Cloud API

**Key Method:**
- `send_message(phone_number, text)` - Sends text message to recipient

**API Details:**
- Endpoint: `https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages`
- Authentication: Bearer token in headers
- Format: JSON payload with recipient and message

### 3. Timer Manager (timer_manager.py)
**Purpose:** Manages delayed message sending with automatic timer reset

**Key Features:**
- Schedules "are you there" message 10 minutes after receiving message
- Maintains one timer per phone number
- Automatically cancels old timer when new message arrives
- Thread-safe operation using locks

**Logic:**
```
User sends message → Start/Reset 10-min timer
        ↓
   Wait 10 minutes
        ↓
   Timer expires → Send "are you there"
   
   (If user sends another message during wait, timer resets)
```

### 4. Configuration (config.py)
**Purpose:** Centralized configuration management

**Loads from .env:**
- WhatsApp Phone Number ID
- WhatsApp Access Token
- Webhook Verify Token
- Flask Port

**Validation:**
- Ensures all required variables are set before app starts

### 5. ngrok (start_ngrok.py)
**Purpose:** Creates public HTTPS tunnel to your local Flask server

**Why Needed:**
- Meta Cloud API requires publicly accessible HTTPS webhook
- Your local machine (localhost:5000) isn't accessible from internet
- ngrok creates: `https://random-id.ngrok-free.app` → `localhost:5000`

## Message Flow Diagrams

### Incoming Message Flow

```
1. User sends "hello" on WhatsApp
         ↓
2. Meta receives message
         ↓
3. Meta sends POST to your webhook
   POST https://your-ngrok-url/webhook
   Body: {message data, sender, text}
         ↓
4. Flask app receives POST at /webhook
         ↓
5. app.py extracts message details
         ↓
6. Checks if text == "hello"
         ↓
7a. If YES: WhatsApp Client sends "hello to you too"
7b. Always: Timer Manager schedules follow-up (10 min)
         ↓
8. Timer waits 10 minutes
         ↓
9. Timer expires → WhatsApp Client sends "are you there"
```

### Outgoing Message Flow

```
1. Your code calls: whatsapp_client.send_message(phone, text)
         ↓
2. WhatsApp Client creates JSON payload
         ↓
3. Sends POST to Meta Cloud API
   POST https://graph.facebook.com/v18.0/{PHONE_ID}/messages
   Headers: Authorization: Bearer {ACCESS_TOKEN}
   Body: {
     "messaging_product": "whatsapp",
     "to": "1234567890",
     "text": {"body": "hello to you too"}
   }
         ↓
4. Meta Cloud API receives request
         ↓
5. Meta validates token and permissions
         ↓
6. Meta sends message to WhatsApp user
         ↓
7. User receives message on phone
```

## Timer Logic Detail

### Scenario 1: Simple Timer
```
Time 0:00  - User sends "hello"
             Timer starts (expires at 10:00)
             Bot responds "hello to you too"

Time 10:00 - Timer expires
             Bot sends "are you there"
```

### Scenario 2: Timer Reset
```
Time 0:00  - User sends "hello"
             Timer starts (expires at 10:00)
             Bot responds "hello to you too"

Time 5:00  - User sends "how are you"
             Timer CANCELLED
             New timer starts (expires at 15:00)

Time 15:00 - New timer expires
             Bot sends "are you there"
```

### Scenario 3: Multiple Messages
```
Time 0:00  - User sends message
             Timer starts (expires at 10:00)

Time 3:00  - User sends another message
             Timer resets (expires at 13:00)

Time 6:00  - User sends another message
             Timer resets (expires at 16:00)

Time 16:00 - Timer expires
             Bot sends "are you there"
```

## Code Structure

```
Hiker/
│
├── app.py                    # Main Flask application
│   ├── webhook_verify()      # GET /webhook - verification
│   ├── webhook_handler()     # POST /webhook - receive messages
│   └── process_message()     # Message processing logic
│
├── whatsapp_client.py        # WhatsApp API client
│   └── WhatsAppClient
│       └── send_message()    # Send messages via API
│
├── timer_manager.py          # Timer management
│   └── TimerManager
│       ├── schedule_followup()    # Start/reset timer
│       └── _send_followup()       # Send delayed message
│
├── config.py                 # Configuration management
│   └── Config
│       └── validate()        # Validate environment vars
│
├── start_ngrok.py            # ngrok tunnel helper
│   └── start_ngrok_tunnel()  # Start tunnel, display URL
│
└── verify_setup.py           # Setup verification
    └── main()                # Run all checks
```

## Threading Model

The bot uses Python threading for timer management:

```
Main Thread (Flask)
   │
   ├── Handles HTTP requests
   │   └── Processes webhooks
   │
   └── Creates Timer Threads
       │
       ├── Timer Thread 1 (User A)
       │   └── Waits 10 min → Send message
       │
       ├── Timer Thread 2 (User B)
       │   └── Waits 10 min → Send message
       │
       └── Timer Thread 3 (User C)
           └── Waits 10 min → Send message
```

Each timer runs in its own daemon thread:
- Daemon threads automatically close when main app stops
- Thread-safe operations using locks (prevents race conditions)
- One active timer per phone number (tracked in dictionary)

## Security Considerations

### 1. Webhook Verification
- Meta sends verify token during setup
- Your app checks token matches before responding
- Prevents unauthorized webhook access

### 2. Access Token
- Stored in .env file (not in code)
- .gitignore prevents committing to git
- Bearer token authentication for API calls

### 3. Request Validation
- Webhook signature validation (can be added)
- Check message structure before processing
- Logging all events for audit

## API Rate Limits

Meta WhatsApp Cloud API has limits:
- **Free tier:** 1,000 conversations per month
- **Message rate:** Unlimited within conversation window
- **Business initiated:** Limited based on tier

Conversation window:
- Opens when user sends message
- Stays open 24 hours
- You can reply freely during window
- After 24h, need template message (not covered in this basic bot)

## Extension Points

### Add More Commands
Edit `process_message()` in app.py:

```python
if message_text == 'hello':
    whatsapp_client.send_message(from_number, "hello to you too")
elif message_text == 'help':
    whatsapp_client.send_message(from_number, "Available commands: hello, help")
elif message_text.startswith('echo '):
    text = message_text[5:]  # Remove 'echo ' prefix
    whatsapp_client.send_message(from_number, f"You said: {text}")
```

### Change Timer Delay
Edit `process_message()` in app.py:

```python
# Change 600 to different seconds value
timer_manager.schedule_followup(from_number, delay_seconds=300)  # 5 minutes
timer_manager.schedule_followup(from_number, delay_seconds=1800)  # 30 minutes
```

### Add Database
Store user conversations, timer states:

```python
# Example with SQLite
import sqlite3

def save_message(user_id, message_text, timestamp):
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO messages (user_id, text, timestamp) VALUES (?, ?, ?)",
        (user_id, message_text, timestamp)
    )
    conn.commit()
    conn.close()
```

### Add AI/NLP
Integrate with OpenAI, DialogFlow, or similar:

```python
import openai

def generate_ai_response(message_text):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": message_text}]
    )
    return response.choices[0].message.content
```

## Production Deployment

For production (beyond testing):

1. **Get Permanent Access Token**
   - Temporary tokens expire in 24 hours
   - Generate system user token (doesn't expire)

2. **Deploy to Server**
   - AWS EC2, DigitalOcean, Heroku, etc.
   - Use real domain with SSL certificate
   - Remove ngrok dependency

3. **Use Production WSGI Server**
   - Replace Flask dev server with Gunicorn or uWSGI
   - Add nginx as reverse proxy

4. **Add Database**
   - PostgreSQL or MySQL for user data
   - Redis for timer state persistence

5. **Add Monitoring**
   - Logging service (CloudWatch, Papertrail)
   - Error tracking (Sentry)
   - Uptime monitoring

6. **Apply for WhatsApp Business**
   - Required for >1000 users/month
   - Business verification process
   - Display name approval

## Troubleshooting Guide

### Messages Not Received
**Check:**
1. ngrok tunnel is running
2. Webhook URL is correct in Meta Dashboard
3. Subscribed to "messages" webhook event
4. Flask app is running and no errors in logs

### Messages Not Sent
**Check:**
1. Access token is valid (not expired)
2. Phone number is in test recipients list
3. API response in logs for error details
4. Phone Number ID is correct

### Timer Not Working
**Check:**
1. Logs show "Scheduled follow-up" message
2. Wait full 10 minutes (600 seconds)
3. Check for threading errors in logs
4. Ensure Flask app stays running

## Resources

- Meta WhatsApp Cloud API: https://developers.facebook.com/docs/whatsapp/cloud-api
- Flask Documentation: https://flask.palletsprojects.com/
- ngrok Documentation: https://ngrok.com/docs
- Python Threading: https://docs.python.org/3/library/threading.html

