# ngrok Authtoken Setup Guide

## Do You Need an Authtoken?

**Short answer:** It's optional but **highly recommended**.

### Without Authtoken (Free, No Sign-up):
- ✅ Works immediately
- ⚠️ Limited features
- ⚠️ Shorter session times
- ⚠️ Rate limits
- ⚠️ Random URLs only

### With Authtoken (Free Account):
- ✅ Longer session times
- ✅ More concurrent tunnels
- ✅ Higher rate limits
- ✅ Access to ngrok dashboard
- ✅ Better reliability
- ✅ **Still FREE!**

## How to Get Your ngrok Authtoken (2 minutes)

### Step 1: Sign Up for Free ngrok Account

1. Go to: https://dashboard.ngrok.com/signup
2. Sign up with:
   - Email and password, OR
   - GitHub account, OR
   - Google account
3. It's completely **FREE**! No credit card needed.

### Step 2: Get Your Authtoken

1. After signing up, you'll be redirected to: https://dashboard.ngrok.com/get-started/your-authtoken
2. Or manually go to: Dashboard → Getting Started → Your Authtoken
3. You'll see something like this:

```
Your Authtoken
2abcDEF123XYZ_4ghiJKL567MNO8pqrSTU
```

4. Click "Copy" button to copy your authtoken

### Step 3: Add Authtoken to Your Project

**Option 1: Add to .env file (Recommended)**

1. Open your `.env` file:
   ```bash
   nano .env
   # or
   code .env
   ```

2. Add this line at the end:
   ```
   NGROK_AUTHTOKEN=2abcDEF123XYZ_4ghiJKL567MNO8pqrSTU
   ```
   (Replace with YOUR actual token)

3. Save the file

4. Done! The script will automatically use it.

**Your complete .env should look like:**
```bash
# WhatsApp Cloud API Configuration
WHATSAPP_PHONE_NUMBER_ID=123456789012345
WHATSAPP_ACCESS_TOKEN=EAAabc123...
WEBHOOK_VERIFY_TOKEN=my_secret_token

# Flask Configuration
FLASK_PORT=5000

# ngrok Configuration (Optional - but recommended)
NGROK_AUTHTOKEN=2abcDEF123XYZ_4ghiJKL567MNO8pqrSTU
```

**Option 2: Set via Command Line (One-time setup)**

Run this command once:
```bash
ngrok authtoken 2abcDEF123XYZ_4ghiJKL567MNO8pqrSTU
```

This saves the token to ngrok's config file (`~/.ngrok2/ngrok.yml`), and you won't need to set it again.

## Verify It's Working

When you run the bot with authtoken configured, you'll see:

```bash
python start_ngrok.py
```

Output:
```
INFO:__main__:Setting ngrok authtoken from .env file...
INFO:__main__:================================================================================
INFO:__main__:Ngrok tunnel established successfully!
INFO:__main__:Public URL: https://abc-123-xyz.ngrok-free.app
...
```

Without authtoken, you'll see a warning:
```
WARNING:__main__:No ngrok authtoken found. Using free tier (limited features).
WARNING:__main__:Get your free authtoken at: https://dashboard.ngrok.com/get-started/your-authtoken
```

## Which Method Should You Use?

| Method | Pros | Cons | Recommended For |
|--------|------|------|-----------------|
| **.env file** | Project-specific, portable, secure | Need to set per project | **✅ This project** |
| **Command line** | One-time setup, global | Used for all ngrok tunnels | Global development |
| **No authtoken** | No setup needed | Limited features | Quick tests only |

**For this project, use the .env file method!** ✅

## Benefits of Using Authtoken

### 1. Longer Session Times
- **Without:** Tunnel may disconnect after ~2 hours
- **With:** Longer, more stable sessions

### 2. More Concurrent Tunnels
- **Without:** 1 tunnel at a time
- **With:** Multiple tunnels (if needed for other projects)

### 3. Better Rate Limits
- **Without:** Very limited requests per minute
- **With:** Higher limits for testing

### 4. Dashboard Access
- **Without:** No visibility
- **With:** See all your tunnels, traffic, and requests at https://dashboard.ngrok.com/

### 5. Better Reliability
- **Without:** May experience disconnections
- **With:** More stable connections

## Common Issues

### Issue: "Invalid authtoken"
**Solution:**
- Check you copied the full token (no spaces)
- Get a fresh token from ngrok dashboard
- Make sure no quotes around the token in .env

### Issue: "Authtoken not being recognized"
**Solution:**
- Make sure the line in .env is: `NGROK_AUTHTOKEN=your_token` (no spaces around =)
- Check .env file is in the project root directory
- Restart the start_ngrok.py script

### Issue: Token expired
**Solution:**
- ngrok authtokens don't expire for free accounts
- If you see this, get a fresh token from the dashboard

## Testing Without Authtoken

If you want to test quickly without setting up an account:

1. Skip the authtoken setup
2. Run `python start_ngrok.py`
3. You'll see a warning, but it will still work
4. Your tunnel will have limited features but sufficient for testing

## Security Note

⚠️ **Keep your authtoken secret!**

- Never commit .env to git (it's already in .gitignore)
- Don't share your authtoken publicly
- Don't paste it in chat/forums
- If exposed, regenerate it at: https://dashboard.ngrok.com/get-started/your-authtoken

## ngrok Dashboard Features (With Authtoken)

Once you have an account, you can access: https://dashboard.ngrok.com/

Features:
- 📊 See all active tunnels
- 📈 View request/response traffic
- 🔍 Inspect webhook requests
- 📝 Request history
- ⚙️ Configure custom domains (paid)
- 🎯 Reserve URLs (paid)

The free tier gives you access to traffic inspection, which is great for debugging!

## Summary

### Quick Setup (2 minutes):
```bash
# 1. Sign up at ngrok
https://dashboard.ngrok.com/signup

# 2. Copy your authtoken from dashboard

# 3. Add to .env file
echo "NGROK_AUTHTOKEN=your_token_here" >> .env

# 4. Run your bot
python start_ngrok.py
```

That's it! 🎉

---

**Bottom line:** Get the free authtoken - it takes 2 minutes and gives you a much better experience!

