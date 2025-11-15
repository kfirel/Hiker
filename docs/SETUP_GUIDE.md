# Quick Setup Guide

## Step-by-Step Instructions

### 1. Install Python Dependencies (5 minutes)

```bash
# Navigate to project directory
cd /Users/kelgabsi/privet/Hiker

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Get Meta WhatsApp API Credentials (10-15 minutes)

#### 2.1 Create Meta Developer Account
1. Go to https://developers.facebook.com/
2. Sign up or log in
3. Click "My Apps" → "Create App"
4. Choose "Business" type
5. Fill in app name and details

#### 2.2 Add WhatsApp to Your App
1. In app dashboard, click "Add Product"
2. Find "WhatsApp" → "Set Up"
3. You'll see WhatsApp API Setup page

#### 2.3 Get Your Three Required Credentials

**Credential 1: Phone Number ID**
- Location: WhatsApp → API Setup
- Look for "Phone number ID" (15-digit number)
- Example: `123456789012345`
- Action: Copy this number

**Credential 2: Access Token**
- Location: Same page, "Temporary access token"
- Starts with `EAA...`
- Action: Click "Copy" button
- ⚠️ Note: This expires in 24 hours (for production, you'll need permanent token)

**Credential 3: Verify Token**
- This is YOUR custom secret string
- Example: `my_secret_webhook_token_12345`
- Action: Create any random string you want
- Make it memorable but secure

#### 2.4 Add Test Phone Number
- On the same page, find "To" section
- Click "Add phone number"
- Enter your personal WhatsApp number (with country code)
- You'll get a verification code on WhatsApp
- Enter the code to verify

### 3. Configure Your Bot (2 minutes)

```bash
# Create .env file from example
cp .env.example .env

# Edit .env file (use your favorite editor)
nano .env
# OR
vim .env
# OR
code .env  # If using VS Code
```

Fill in the three credentials:

```
WHATSAPP_PHONE_NUMBER_ID=<paste your 15-digit phone number ID>
WHATSAPP_ACCESS_TOKEN=<paste your EAA... token>
WEBHOOK_VERIFY_TOKEN=<your custom secret string>
FLASK_PORT=5000
```

Save and close the file.

### 4. Start ngrok (Webhook Tunnel)

Open **Terminal Window 1**:

```bash
# Activate virtual environment if not already active
source venv/bin/activate

# Start ngrok
python start_ngrok.py
```

You'll see output like:
```
================================================================================
Ngrok tunnel established successfully!
Public URL: https://abcd-1234-5678-efgh.ngrok-free.app
Webhook URL: https://abcd-1234-5678-efgh.ngrok-free.app/webhook
================================================================================

IMPORTANT: Copy the Webhook URL above and paste it in your Meta App Dashboard
Keep this script running while testing your bot
================================================================================

Press Enter to stop ngrok tunnel...
```

**IMPORTANT:** 
- Keep this terminal window open!
- Copy the Webhook URL (ending with `/webhook`)

### 5. Configure Webhook in Meta Dashboard (3 minutes)

1. Go back to Meta App Dashboard
2. Navigate to: WhatsApp → Configuration
3. Find "Webhook" section → Click "Edit"
4. Paste your Webhook URL: `https://your-ngrok-url.ngrok-free.app/webhook`
5. Enter your Verify Token (the one from your .env file)
6. Click "Verify and Save"
   - ✅ Success: You'll see "Webhook verified"
   - ❌ Failed: Double-check your verify token matches .env

7. Still in Webhook section → Click "Manage"
8. Find "messages" → Check the box to subscribe
9. Click "Save"

### 6. Start Your Bot

Open **Terminal Window 2** (new window):

```bash
# Navigate to project
cd /Users/kelgabsi/privet/Hiker

# Activate virtual environment
source venv/bin/activate

# Run the bot
python app.py
```

You should see:
```
Configuration validated successfully
Starting WhatsApp Bot on port 5000
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:5000
```

**Keep both terminal windows open!**

### 7. Test Your Bot! 🎉

#### Test 1: Hello Response
1. Open WhatsApp on your phone
2. Send message to the test number: `hello`
3. You should receive: `hello to you too`

#### Test 2: 10-Minute Timer
1. Send any message to the bot
2. Wait 10 minutes ⏰
3. You should receive: `are you there`

#### Test 3: Timer Reset
1. Send a message
2. Wait 5 minutes
3. Send another message (timer resets)
4. Wait 10 minutes from the second message
5. You should receive: `are you there`

## Troubleshooting

### Problem: "Webhook verification failed"
**Solution:**
- Check that WEBHOOK_VERIFY_TOKEN in .env matches what you entered in Meta Dashboard
- Ensure ngrok is running
- Try clicking "Verify and Save" again

### Problem: "Configuration error: Missing required environment variables"
**Solution:**
- Open .env file
- Make sure all three variables are filled in
- No quotes needed around values
- No spaces around = sign

### Problem: "Messages not being received"
**Solution:**
- Check both terminal windows for errors
- Verify you subscribed to "messages" webhook in Meta Dashboard
- Ensure your phone number is added as test recipient
- Check ngrok is still running (URL might change if restarted)

### Problem: "Failed to send message"
**Solution:**
- Check your ACCESS_TOKEN is valid (expires after 24 hours)
- Verify PHONE_NUMBER_ID is correct
- Look at terminal logs for detailed error message
- Ensure recipient number is in test recipients list

### Problem: ngrok URL changed
**Solution:**
- Free ngrok URLs change each time you restart
- Copy new URL from Terminal Window 1
- Update webhook URL in Meta Dashboard
- Click "Verify and Save" again

## What's Next?

Your bot is now running! Here are some ideas to enhance it:

1. **Add more message responses**
   - Edit `app.py`, function `process_message()`
   - Add more `if` conditions for different messages

2. **Change the timer delay**
   - In `app.py`, line with `schedule_followup(..., delay_seconds=600)`
   - Change 600 to different value (in seconds)

3. **Customize responses**
   - Edit the response messages in `app.py`
   - Make it more conversational!

4. **Add more features**
   - Store user data
   - Handle media messages
   - Create menu-based interaction
   - Add AI/NLP for smarter responses

## Need Help?

Check the full README.md for detailed documentation.

Common files to edit:
- `app.py` - Main bot logic and message handling
- `config.py` - Configuration settings
- `whatsapp_client.py` - Sending messages
- `timer_manager.py` - Timer functionality

Happy coding! 🚀

