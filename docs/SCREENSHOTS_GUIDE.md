# 📸 Visual Guide: Finding Webhook in Meta Dashboard

## 🎯 You're Looking For This Path:

```
Meta Dashboard → Your App → WhatsApp → Configuration → Webhook Section
```

---

## Step-by-Step with Visual Descriptions

### STEP 1: Open Meta Apps Dashboard

**URL:** https://developers.facebook.com/apps

**What you see:**
- List of your apps (or empty if first time)
- Button to "Create App" if you haven't already

**Action:** Click on your app name

---

### STEP 2: Identify the Left Sidebar

After clicking your app, you should see:

**LEFT SIDE of screen = Navigation Sidebar**

It looks something like this:

```
╔══════════════════════════╗
║ Your App Name            ║
╠══════════════════════════╣
║ 📱 Dashboard             ║
║ ⚙️  App Settings          ║
║    ├─ Basic              ║
║    └─ Advanced           ║
║ 📊 Analytics             ║
║ 💬 WhatsApp              ║  ← LOOK FOR THIS!
║    ├─ API Setup          ║
║    ├─ Configuration      ║  ← YOU NEED THIS!
║    ├─ Analytics          ║
║    └─ Phone Numbers      ║
║ 🔧 Build                 ║
╚══════════════════════════╝
```

**Key things to look for:**
- Text says "WhatsApp" (might have a chat bubble icon 💬)
- May be collapsed (click to expand)
- Under it, you should see "Configuration"

---

### STEP 3: What If You DON'T See "WhatsApp"?

**This means WhatsApp hasn't been added to your app yet.**

#### Look for "Add Products" or "Add Product"

The button is usually:
- In the middle of the dashboard (big tiles)
- Or at the bottom of the left sidebar
- Or under a "Products" section

**What you'll see:**

```
┌─────────────────────────────────────────┐
│  Add products to your app               │
│                                         │
│  ┌──────────┐  ┌──────────┐           │
│  │ WhatsApp │  │ Facebook │           │
│  │    💬    │  │    👍    │           │
│  │ [Set Up] │  │ [Set Up] │           │
│  └──────────┘  └──────────┘           │
└─────────────────────────────────────────┘
```

**Action:**
1. Find "WhatsApp" product
2. Click **"Set Up"** button
3. Wait 5-10 seconds for setup
4. Now "WhatsApp" should appear in left sidebar

---

### STEP 4: Click "WhatsApp" in Left Sidebar

**Where:** Left sidebar

**What happens:** 
- The WhatsApp item expands
- Shows sub-menu items:
  - API Setup (or "Getting Started")
  - **Configuration** ← This is what you need!
  - Analytics
  - Phone Numbers

**Visual:**

```
Before clicking:
║ 💬 WhatsApp          ►  ║

After clicking:
║ 💬 WhatsApp          ▼  ║
║    ├─ API Setup         ║
║    ├─ Configuration     ║ ← Click this!
║    ├─ Analytics         ║
║    └─ Phone Numbers     ║
```

---

### STEP 5: Click "Configuration"

**Where:** Under WhatsApp in left sidebar

**What loads:** Configuration page

**What you should see on this page:**

```
═══════════════════════════════════════════
Configuration
═══════════════════════════════════════════

Phone Numbers
┌─────────────────────────────────────────┐
│ Test Phone Number                       │
│ +1 555-0100                            │
└─────────────────────────────────────────┘

Webhook                    ← YOU'RE LOOKING FOR THIS!
┌─────────────────────────────────────────┐
│ Callback URL                            │
│ Not configured                          │
│ [Edit]                    ← Click this! │
│                                         │
│ Verify Token                            │
│ Not configured                          │
└─────────────────────────────────────────┘

Webhook fields
┌─────────────────────────────────────────┐
│ ☐ messages           [Subscribe]        │
│ ☐ message_status                        │
│ ☐ message_echoes                        │
└─────────────────────────────────────────┘
```

**If you see this, you're in the RIGHT PLACE!** ✅

---

### STEP 6: Configure Webhook

**Action: Click [Edit] button** next to "Callback URL"

**A popup or inline form appears with two fields:**

```
┌────────────────────────────────────────┐
│  Edit Webhook                          │
├────────────────────────────────────────┤
│                                        │
│  Callback URL                          │
│  ┌──────────────────────────────────┐ │
│  │                                  │ │
│  └──────────────────────────────────┘ │
│                                        │
│  Verify Token                          │
│  ┌──────────────────────────────────┐ │
│  │                                  │ │
│  └──────────────────────────────────┘ │
│                                        │
│  [Cancel]     [Verify and Save]       │
└────────────────────────────────────────┘
```

**Fill in:**
1. **Callback URL:** Your ngrok URL + `/webhook`
   - Example: `https://abc-123-xyz.ngrok-free.app/webhook`
   - Get this from running `python start_ngrok.py`

2. **Verify Token:** Your custom secret from .env
   - Example: `my_secret_webhook_token_12345`
   - This is `WEBHOOK_VERIFY_TOKEN` from your .env file

**Click "Verify and Save"**

---

### STEP 7: Success or Error?

**✅ SUCCESS Message:**
```
Webhook verified successfully!
```

**❌ ERROR Message:**
```
Failed to verify webhook
The callback URL or verify token couldn't be verified
```

**If you get an error:**
1. Make sure ngrok is running: `python start_ngrok.py`
2. Check your verify token matches .env exactly
3. Make sure URL ends with `/webhook`
4. Try again

---

### STEP 8: Subscribe to "messages"

**Still on Configuration page, scroll to "Webhook fields" section**

You'll see checkboxes:
```
Webhook fields
☐ messages           [Subscribe]
☐ message_status
☐ message_echoes
```

**Action:**
1. Find "messages" row
2. Click **[Subscribe]** button next to it
3. It should change to show "Subscribed" with a checkmark

```
✅ messages           [Manage]  ← Success!
```

---

## 🆘 Troubleshooting: Can't Find It?

### Problem 1: No "WhatsApp" in Left Sidebar

**Solution:** You need to add WhatsApp product

**Where to find "Add Product":**

**Option A:** Look in the main area (center of screen) when on Dashboard:
```
┌────────────────────────────────────┐
│  Products                          │
│  ─────────────────────────────     │
│  Add products to enhance your app  │
│                                    │
│  💬 WhatsApp    [+ Add]            │ ← Click Add
│  📧 Email       [+ Add]            │
└────────────────────────────────────┘
```

**Option B:** Look for "Add to App" button (top right or in dashboard)

**Option C:** Scroll down in left sidebar, look for "+ Add Product"

---

### Problem 2: See "WhatsApp" But No "Configuration"

**Possible reasons:**
- WhatsApp item is not expanded (click on it to expand)
- Page hasn't fully loaded (refresh browser)
- Different name in your region/version

**Solutions:**
1. **Click directly on "WhatsApp" text** to expand
2. **Look for alternative names:**
   - "Settings"
   - "Webhook Setup"
   - "Configure"
3. **Try going to API Setup first**, then look for Configuration link there

---

### Problem 3: Different Dashboard Layout

**Meta sometimes changes their UI.** Here are alternative navigation paths:

**Path A: Via Quick Access**
1. Dashboard → WhatsApp → API Setup
2. On API Setup page, look for "Configuration" tab at top
3. Or look for "Configure Webhooks" link

**Path B: Via Direct URL**
Use this URL format (replace YOUR_APP_ID):
```
https://developers.facebook.com/apps/YOUR_APP_ID/whatsapp-business/wa-settings/
```

**To find your App ID:**
- Look at the URL when in your app dashboard
- Or: App Settings → Basic → App ID

---

## 🎯 Quick Visual Checklist

Follow this exact path:

```
1. https://developers.facebook.com/apps
        ↓
2. Click your app name
        ↓
3. Left sidebar: Find "WhatsApp" 💬
        ↓
4. Click "WhatsApp" to expand
        ↓
5. Click "Configuration"
        ↓
6. Scroll to "Webhook" section
        ↓
7. Click [Edit] button
        ↓
8. Fill in Callback URL and Verify Token
        ↓
9. Click "Verify and Save"
        ↓
10. Subscribe to "messages" field
        ↓
✅ DONE!
```

---

## 📱 Alternative: Mobile Instructions

If accessing from mobile device, the layout is different:

1. Tap hamburger menu (☰) to open sidebar
2. Tap "WhatsApp"
3. Tap "Configuration"
4. Rest is the same

---

## 🔗 Useful Direct Links

Try these URLs (replace `YOUR_APP_ID` with your actual app ID):

**API Setup (where you got credentials):**
```
https://developers.facebook.com/apps/YOUR_APP_ID/whatsapp-business/wa-getting-started/
```

**Configuration (where webhook is):**
```
https://developers.facebook.com/apps/YOUR_APP_ID/whatsapp-business/wa-settings/
```

**Your Apps List:**
```
https://developers.facebook.com/apps/
```

---

## ✅ Confirmation: You're in the Right Place When...

You know you found the right page when you see ALL of these:

✅ Page title says "Configuration"  
✅ Section heading says "Webhook"  
✅ Fields for "Callback URL" and "Verify Token"  
✅ "[Edit]" button to configure webhook  
✅ "Webhook fields" section with "messages" checkbox below

If you see all of these, **you found it!** 🎉

---

## 💬 Still Stuck? 

**Describe what you see:**
1. What options are in your left sidebar?
2. Do you see "WhatsApp" anywhere?
3. What's the current page title?
4. Take a screenshot if possible

This will help identify where you are in the dashboard.

**Also check:**
- ✅ You created a **Business** type app (not Consumer/Gaming)
- ✅ You're logged into the correct Facebook account
- ✅ Your account has access to the app

---

**I've also created `FIND_WEBHOOK_IN_META.md` with even more detailed troubleshooting!**

