# 🚀 START HERE - Your WhatsApp Bot Project

Welcome! Your WhatsApp chatbot project is ready. This bot will:
- ✅ Respond "hello to you too" when someone sends "hello"
- ✅ Send "are you there" after 10 minutes of receiving any message
- ✅ Reset the timer when a new message arrives

## 📚 Documentation Files

Your project includes comprehensive documentation:

| File | Purpose | Read This If... |
|------|---------|-----------------|
| **SETUP_GUIDE.md** | Step-by-step setup instructions | You're setting up for the first time ⭐ |
| **QUICK_REFERENCE.md** | Quick commands and tips | You need a quick reminder |
| **README.md** | Complete documentation | You want full technical details |
| **ARCHITECTURE.md** | Technical architecture | You want to understand how it works |
| **START_HERE.md** | This file - overview | You're just starting 👈 |

## 🎯 Quick Start (5 Steps)

### Step 1: Install Dependencies (5 minutes)
```bash
cd /Users/kelgabsi/privet/Hiker
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Step 2: Get Meta WhatsApp Credentials (10 minutes)
1. Go to https://developers.facebook.com/
2. Create an App → Choose "Business" type
3. Add "WhatsApp" product
4. Copy these 3 things:
   - Phone Number ID (15 digits)
   - Access Token (starts with EAA...)
   - Create your own Verify Token (any random string)

**Detailed instructions:** See SETUP_GUIDE.md Section 2

### Step 3: Configure Environment (2 minutes)
```bash
cp .env.example .env
nano .env  # or use your favorite editor
```

Fill in your credentials:
```
WHATSAPP_PHONE_NUMBER_ID=<your 15-digit ID>
WHATSAPP_ACCESS_TOKEN=<your EAA... token>
WEBHOOK_VERIFY_TOKEN=<your custom secret>
FLASK_PORT=5000
```

### Step 4: Verify Setup (1 minute)
```bash
python verify_setup.py
```

This checks if everything is configured correctly.

### Step 5: Run the Bot (5 minutes)

**Terminal 1 - Start ngrok:**
```bash
source venv/bin/activate
python start_ngrok.py
```
Copy the webhook URL that appears.

**Terminal 2 - Start bot:**
```bash
source venv/bin/activate
python app.py
```

**In Browser - Configure webhook:**
1. Go to Meta App Dashboard
2. WhatsApp → Configuration → Webhook
3. Paste the ngrok webhook URL
4. Enter your verify token
5. Click "Verify and Save"
6. Subscribe to "messages" event

**📍 Can't find webhook configuration?** See detailed visual guide: `SCREENSHOTS_GUIDE.md` or `FIND_WEBHOOK_IN_META.md`

## 🧪 Test Your Bot

1. Open WhatsApp on your phone
2. Send "hello" to the test number → Receive "hello to you too"
3. Wait 10 minutes → Receive "are you there"
4. Done! 🎉

## 📁 Project Files

### Core Application Files
```
app.py              - Main bot logic (you'll edit this most)
whatsapp_client.py  - Sends WhatsApp messages
timer_manager.py    - Manages the 10-minute timer
config.py           - Configuration management
```

### Helper Files
```
start_ngrok.py      - Starts ngrok tunnel
verify_setup.py     - Checks if setup is correct
requirements.txt    - Python dependencies
.env                - Your credentials (you create this)
.env.example        - Template for .env
.gitignore          - Git ignore rules
```

### Documentation Files
```
README.md           - Full documentation
SETUP_GUIDE.md      - Step-by-step setup
QUICK_REFERENCE.md  - Quick commands & tips
ARCHITECTURE.md     - Technical architecture
START_HERE.md       - This file
```

## 🎨 Customizing Your Bot

### Change "hello to you too" Message
**File:** `app.py` (around line 80)

```python
# Find this line:
whatsapp_client.send_message(from_number, "hello to you too")

# Change to:
whatsapp_client.send_message(from_number, "Hey! Nice to hear from you!")
```

### Change "are you there" Message
**File:** `timer_manager.py` (around line 41)

```python
# Find this line:
success = self.whatsapp_client.send_message(phone_number, "are you there")

# Change to:
success = self.whatsapp_client.send_message(phone_number, "Still interested?")
```

### Change 10-Minute Timer
**File:** `app.py` (around line 75)

```python
# Find this line:
timer_manager.schedule_followup(from_number, delay_seconds=600)

# Change to 5 minutes:
timer_manager.schedule_followup(from_number, delay_seconds=300)

# Or 30 minutes:
timer_manager.schedule_followup(from_number, delay_seconds=1800)
```

### Add New Commands
**File:** `app.py` in the `process_message()` function

```python
# Add after the "hello" check:
if message_text == 'hello':
    whatsapp_client.send_message(from_number, "hello to you too")
elif message_text == 'help':
    whatsapp_client.send_message(from_number, "Commands: hello, help, time")
elif message_text == 'time':
    from datetime import datetime
    current_time = datetime.now().strftime("%H:%M")
    whatsapp_client.send_message(from_number, f"Current time is {current_time}")
```

## ❗ Common Issues & Solutions

### Issue: "Webhook verification failed"
**Solution:** 
- Check that WEBHOOK_VERIFY_TOKEN in .env matches Meta Dashboard
- Ensure ngrok is running
- Try again

### Issue: "Messages not being received"
**Solution:**
- Verify both ngrok AND Flask app are running
- Check you subscribed to "messages" webhook event
- Look at Flask app logs for errors

### Issue: "Failed to send message"
**Solution:**
- Access token might be expired (24h limit for test tokens)
- Get new token from Meta Dashboard
- Update .env file
- Restart Flask app

### Issue: "ngrok URL changed"
**Solution:**
- Free ngrok URLs change on restart
- Copy new URL from ngrok terminal
- Update webhook URL in Meta Dashboard
- Click "Verify and Save" again

## 🎓 Learning Path

Follow this path to master your bot:

1. ✅ **Get it working** - Follow Quick Start above
2. 📚 **Understand it** - Read ARCHITECTURE.md
3. ✏️ **Customize it** - Change response messages
4. 🎯 **Extend it** - Add new commands
5. 🚀 **Deploy it** - Move to production server

## 🛠️ Development Workflow

### Every time you work on the bot:

1. **Start ngrok** (Terminal 1)
   ```bash
   cd /Users/kelgabsi/privet/Hiker
   source venv/bin/activate
   python start_ngrok.py
   ```

2. **Start bot** (Terminal 2)
   ```bash
   cd /Users/kelgabsi/privet/Hiker
   source venv/bin/activate
   python app.py
   ```

3. **Make changes** - Edit files, save
4. **Restart bot** - Ctrl+C in Terminal 2, then `python app.py` again
5. **Test** - Send messages on WhatsApp

### When done:
- Press Enter in Terminal 1 (stops ngrok)
- Press Ctrl+C in Terminal 2 (stops Flask)

## 📊 What's Happening Behind the Scenes

```
You send "hello" on WhatsApp
    ↓
WhatsApp → Meta Cloud API → Your ngrok URL → Flask app
    ↓
Flask receives message
    ↓
Checks if text == "hello"
    ↓
Sends "hello to you too" via Meta API
    ↓
Starts 10-minute timer
    ↓
After 10 minutes (if no new messages)
    ↓
Sends "are you there" via Meta API
    ↓
You receive message on WhatsApp
```

## 🔒 Security Notes

- ✅ .env file is in .gitignore (credentials won't be committed to git)
- ✅ Never share your Access Token
- ✅ Verify Token prevents unauthorized webhook access
- ⚠️ Temporary tokens expire in 24 hours (fine for testing)
- ⚠️ For production, get permanent token

## 💰 Cost

- **Meta WhatsApp Cloud API:** FREE for first 1,000 conversations/month
- **ngrok:** FREE tier (URL changes on restart)
- **Python/Flask:** FREE and open source
- **Total:** $0 for testing! 🎉

## 🚀 Next Steps

Now that you have the basics:

1. **Test thoroughly** - Make sure everything works
2. **Read ARCHITECTURE.md** - Understand how it works
3. **Customize** - Change messages, add commands
4. **Extend** - Add database, AI, more features
5. **Deploy** - Move to production when ready

## 📞 Support Resources

- **Setup issues:** Read SETUP_GUIDE.md
- **Quick commands:** Check QUICK_REFERENCE.md
- **Technical details:** See ARCHITECTURE.md
- **Meta WhatsApp Docs:** https://developers.facebook.com/docs/whatsapp/cloud-api

## ✨ Features to Add Later

Some ideas for enhancement:
- 🤖 AI chatbot integration (OpenAI, DialogFlow)
- 💾 Database to store user data
- 📊 Analytics and message history
- 🖼️ Support for images and media
- 🌐 Multi-language support
- 📅 Appointment scheduling
- 🛒 E-commerce integration
- 📧 Email notifications

---

## 🎯 Right Now: Start Here!

**Your immediate next step:**

```bash
cd /Users/kelgabsi/privet/Hiker
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python verify_setup.py
```

Then read **SETUP_GUIDE.md** for detailed Meta WhatsApp setup.

Good luck! 🚀 You've got this! 💪

