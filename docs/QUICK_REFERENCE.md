# Quick Reference Card

## 🚀 Starting the Bot

### First Time Setup
```bash
# 1. Install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
nano .env  # Fill in your credentials

# 3. Verify setup
python verify_setup.py
```

### Every Time You Run
```bash
# Terminal 1: Start ngrok
source venv/bin/activate
python start_ngrok.py
# Copy the webhook URL

# Terminal 2: Start bot
source venv/bin/activate
python app.py
```

## 📝 Configuration Files

### .env (Your Credentials)
```bash
WHATSAPP_PHONE_NUMBER_ID=123456789012345
WHATSAPP_ACCESS_TOKEN=EAAabc123...
WEBHOOK_VERIFY_TOKEN=my_secret_token
FLASK_PORT=5000
```

### Where to Get Credentials
- **Phone Number ID**: Meta Dashboard → WhatsApp → API Setup
- **Access Token**: Same page, click "Copy" on temporary token
- **Verify Token**: Your own custom secret string

## 🔧 Common Commands

### Check Setup
```bash
python verify_setup.py
```

### Start ngrok Only
```bash
python start_ngrok.py
```

### Run Bot
```bash
python app.py
```

### View Logs
```bash
# Logs appear in terminal where app.py is running
# Look for:
# - "Processing message from..."
# - "Responded to 'hello'..."
# - "Scheduled follow-up..."
```

### Stop Everything
```bash
# In ngrok terminal: Press Enter
# In app.py terminal: Ctrl+C
```

## 🎯 Testing Checklist

- [ ] Send "hello" → Receive "hello to you too"
- [ ] Wait 10 minutes → Receive "are you there"
- [ ] Send message, wait 5 min, send another → Timer resets
- [ ] Check logs show all events

## 📱 Bot Behavior

| User Action | Bot Response | Timing |
|-------------|--------------|--------|
| Sends "hello" | "hello to you too" | Immediate |
| Sends any message | Starts/resets 10-min timer | Silent |
| 10 minutes of silence | "are you there" | After 10 min |
| Sends another message | Timer resets | Silent |

## 🐛 Quick Troubleshooting

### Bot not receiving messages?
```bash
# Check:
✓ ngrok is running
✓ Flask app is running
✓ Webhook configured in Meta Dashboard
✓ Subscribed to "messages" event
```

### Bot not sending messages?
```bash
# Check:
✓ Access token not expired (24h limit)
✓ Phone number in test recipients
✓ Check logs for API errors
```

### Webhook verification failed?
```bash
# Check:
✓ Verify token in .env matches Meta Dashboard
✓ ngrok URL is correct
✓ No typos in webhook URL
```

## ✏️ Quick Edits

### Change Response Message
**File:** `app.py`
**Line:** ~80

```python
# Change "hello to you too" to something else
whatsapp_client.send_message(from_number, "Your new message here")
```

### Change Timer Duration
**File:** `app.py`
**Line:** ~75

```python
# Change 600 (10 minutes) to different seconds
timer_manager.schedule_followup(from_number, delay_seconds=300)  # 5 min
timer_manager.schedule_followup(from_number, delay_seconds=1800)  # 30 min
```

### Change Follow-up Message
**File:** `timer_manager.py`
**Line:** ~41

```python
# Change "are you there" to something else
success = self.whatsapp_client.send_message(phone_number, "Your follow-up message")
```

### Add New Command
**File:** `app.py`
**Function:** `process_message()`

```python
# Add after the "hello" check:
elif message_text == 'help':
    whatsapp_client.send_message(from_number, "I can help you!")
elif message_text == 'bye':
    whatsapp_client.send_message(from_number, "Goodbye!")
```

## 📂 Project Structure

```
Hiker/
├── app.py                 ← Main bot logic (edit this most)
├── whatsapp_client.py     ← Sending messages
├── timer_manager.py       ← Timer logic
├── config.py              ← Configuration
├── start_ngrok.py         ← Helper script
├── verify_setup.py        ← Setup checker
├── requirements.txt       ← Dependencies
├── .env                   ← Your credentials (create this)
├── .env.example          ← Template
├── .gitignore            ← Git ignore rules
├── README.md             ← Full documentation
├── SETUP_GUIDE.md        ← Step-by-step setup
├── ARCHITECTURE.md       ← Technical details
└── QUICK_REFERENCE.md    ← This file
```

## 🔗 Important URLs

### During Development
- Local Flask: `http://localhost:5000`
- ngrok URL: `https://xxxx.ngrok-free.app` (changes each restart)
- Webhook: `https://xxxx.ngrok-free.app/webhook`
- Health check: `https://xxxx.ngrok-free.app/health`

### Meta Resources
- Developer Dashboard: https://developers.facebook.com/apps
- WhatsApp Docs: https://developers.facebook.com/docs/whatsapp/cloud-api
- API Reference: https://developers.facebook.com/docs/whatsapp/cloud-api/reference

## 💡 Tips

1. **Keep both terminals open** - ngrok and Flask app
2. **Token expires in 24h** - Get new one from Meta Dashboard
3. **ngrok URL changes** - Update webhook after ngrok restart
4. **Check logs first** - Most issues show in terminal
5. **Test recipient list** - Add your number in Meta Dashboard
6. **Case sensitive** - "hello" works, "Hello" won't (unless you modify code)

## 🎓 Learning Path

1. ✅ Get bot working with basic "hello" response
2. ✅ Verify 10-minute timer works
3. 📚 Read ARCHITECTURE.md to understand how it works
4. ✏️ Try changing response messages
5. ✏️ Add new commands
6. ✏️ Modify timer duration
7. 🚀 Add more complex features (database, AI, etc.)

## 🆘 Getting Help

1. Read error messages in terminal
2. Check SETUP_GUIDE.md for detailed instructions
3. Review ARCHITECTURE.md for technical details
4. Look at code comments in .py files
5. Check Meta's WhatsApp documentation

## 📋 Production Checklist

When ready to deploy:

- [ ] Get permanent access token (not temporary)
- [ ] Deploy to cloud server (AWS, DigitalOcean, etc.)
- [ ] Use real domain with SSL
- [ ] Switch to production WSGI server (Gunicorn)
- [ ] Add database for user data
- [ ] Implement error monitoring
- [ ] Apply for WhatsApp Business API access
- [ ] Add logging and monitoring
- [ ] Implement rate limiting
- [ ] Add automated tests

---

**Pro Tip:** Bookmark this file for quick access while developing! 🚀

