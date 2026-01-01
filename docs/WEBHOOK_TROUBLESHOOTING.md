# WhatsApp Webhook Troubleshooting Guide

## 🔴 Error: "The callback URL or verify token couldn't be validated"

This error occurs when Meta tries to verify your webhook but fails. Here's how to fix it:

---

## ✅ **Step-by-Step Solution:**

### **Step 1: Check Your Deployment**

First, verify that your app is deployed and running:

```bash
# Check service status
gcloud run services describe hitchhiking-bot \
  --platform managed \
  --region us-central1

# Check recent logs
gcloud run logs read \
  --service=hitchhiking-bot \
  --region=us-central1 \
  --limit=50
```

### **Step 2: Get Your Service URL**

```bash
# Get the Cloud Run URL
gcloud run services describe hitchhiking-bot \
  --platform managed \
  --region us-central1 \
  --format 'value(status.url)'
```

**Your webhook URL will be:** `<SERVICE_URL>/webhook`

### **Step 3: Test the Webhook Locally**

Run our diagnostic script:

```bash
# Set your verify token first
export VERIFY_TOKEN="your_verify_token_here"

# Run the test
./test_webhook.sh
```

### **Step 4: Manual Test with cURL**

Replace `YOUR_SERVICE_URL` and `YOUR_VERIFY_TOKEN` with your actual values:

```bash
curl "YOUR_SERVICE_URL/webhook?hub.mode=subscribe&hub.verify_token=YOUR_VERIFY_TOKEN&hub.challenge=test123"
```

**Expected Output:** `test123`

If you get anything else, there's a problem!

---

## 🐛 **Common Issues & Fixes:**

### **Issue 1: Verify Token Mismatch** ⭐ (Most Common!)

**Symptom:** Webhook verification fails even though URL is accessible

**Cause:** The `VERIFY_TOKEN` in your Cloud Run environment doesn't match what you entered in Meta

**Fix:**

1. Check what token is set in Cloud Run:
   ```bash
   gcloud run services describe hitchhiking-bot \
     --region=us-central1 \
     --format='value(spec.template.spec.containers[0].env)'
   ```

2. Make sure it matches EXACTLY (case-sensitive, no spaces)

3. If different, redeploy with correct token:
   ```bash
   export VERIFY_TOKEN="your_correct_token"
   ./deploy.sh
   ```

### **Issue 2: Service Not Accessible**

**Symptom:** cURL test fails or times out

**Cause:** Service isn't running or not publicly accessible

**Fix:**

1. Check if service allows unauthenticated access:
   ```bash
   gcloud run services describe hitchhiking-bot \
     --region=us-central1 \
     --format='value(metadata.annotations.run.googleapis.com/ingress)'
   ```
   Should show `all`

2. Make service public:
   ```bash
   gcloud run services add-iam-policy-binding hitchhiking-bot \
     --region=us-central1 \
     --member="allUsers" \
     --role="roles/run.invoker"
   ```

### **Issue 3: Wrong URL in Meta**

**Symptom:** Meta shows error immediately

**Cause:** Typo in webhook URL or wrong format

**Fix:**

The URL must be:
- ✅ `https://your-service-xxx.run.app/webhook`
- ❌ `https://your-service-xxx.run.app/webhook/` (no trailing slash)
- ❌ `http://...` (must be HTTPS)
- ❌ Missing `/webhook` path

### **Issue 4: Environment Variables Not Set**

**Symptom:** Service runs but webhook verification fails

**Cause:** Environment variables didn't deploy correctly

**Fix:**

```bash
# Check all environment variables
gcloud run services describe hitchhiking-bot \
  --region=us-central1 \
  --format='json' | grep -A 5 env

# Redeploy with all variables
export GEMINI_API_KEY="..."
export WHATSAPP_TOKEN="..."
export WHATSAPP_PHONE_NUMBER_ID="..."
export VERIFY_TOKEN="..."
export ADMIN_TOKEN="..."  # Optional

./deploy.sh
```

### **Issue 5: Service Crashed or Not Starting**

**Symptom:** Service shows "Revision failed"

**Cause:** Application error on startup

**Fix:**

```bash
# Check logs for errors
gcloud run logs read \
  --service=hitchhiking-bot \
  --region=us-central1 \
  --limit=100

# Look for Python errors or missing dependencies
```

Common startup issues:
- Missing Firestore setup
- Invalid API keys
- Import errors

---

## 📋 **Meta Configuration Checklist:**

When setting up the webhook in Meta Developer Console:

1. **URL Format:**
   - ✅ Must start with `https://`
   - ✅ Must end with `/webhook` (no trailing slash)
   - ✅ Must be publicly accessible

2. **Verify Token:**
   - ✅ Must match EXACTLY (case-sensitive)
   - ✅ No extra spaces
   - ✅ Recommended: Use a random string (20+ characters)

3. **Webhook Fields:**
   - ✅ Subscribe to `messages` field
   - ✅ (Optional) Subscribe to `messaging_postbacks`

4. **App Review:**
   - ⚠️ For testing, use test phone numbers
   - ⚠️ For production, submit app for review

---

## 🔍 **Debug Commands:**

### Check if webhook endpoint exists:
```bash
curl -I https://your-service.run.app/webhook
# Should return HTTP 403 or 422 (not 404)
```

### Test webhook verification:
```bash
curl "https://your-service.run.app/webhook?hub.mode=subscribe&hub.verify_token=YOUR_TOKEN&hub.challenge=HELLO"
# Should return: HELLO
```

### Check Cloud Run logs in real-time:
```bash
gcloud run logs tail \
  --service=hitchhiking-bot \
  --region=us-central1
```

Then trigger webhook verification in Meta and watch for logs.

### Test POST endpoint (simulate message):
```bash
curl -X POST https://your-service.run.app/webhook \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'
```

---

## 🚀 **Quick Fix Script:**

If you're still having issues, try this:

```bash
#!/bin/bash

# Quick webhook fix script

# 1. Set your verify token
export VERIFY_TOKEN="my_secure_token_12345"

# 2. Get service URL
SERVICE_URL=$(gcloud run services describe hitchhiking-bot \
  --region=us-central1 \
  --format='value(status.url)')

echo "Service URL: $SERVICE_URL"

# 3. Test webhook
RESPONSE=$(curl -s "$SERVICE_URL/webhook?hub.mode=subscribe&hub.verify_token=$VERIFY_TOKEN&hub.challenge=test")

if [ "$RESPONSE" = "test" ]; then
    echo "✅ Webhook works!"
    echo ""
    echo "Use these values in Meta:"
    echo "  Callback URL: $SERVICE_URL/webhook"
    echo "  Verify Token: $VERIFY_TOKEN"
else
    echo "❌ Webhook failed!"
    echo "Got response: $RESPONSE"
    echo ""
    echo "Check logs:"
    echo "  gcloud run logs read --service=hitchhiking-bot --region=us-central1 --limit=20"
fi
```

---

## 📞 **Still Not Working?**

If you've tried everything above and it still doesn't work:

1. **Check Meta Status:** https://metastatus.com/
   - Meta services might be down

2. **Try a Different Region:**
   ```bash
   # Deploy to a different region
   gcloud run deploy hitchhiking-bot \
     --region=europe-west1 \
     ...
   ```

3. **Enable Debug Logging:**
   - Add `--set-env-vars LOG_LEVEL=DEBUG` to deploy command
   - Redeploy and check logs

4. **Use a Test Tool:**
   - https://webhook.site/
   - Set this as your webhook URL temporarily
   - See what Meta is sending

---

## ✅ **Success Checklist:**

Once everything works, you should see:

- ✅ Service URL returns HTTP 200 on root path
- ✅ `/webhook` returns the challenge when tested with cURL
- ✅ Meta shows green checkmark after verification
- ✅ Logs show: "✅ Webhook verified successfully!"
- ✅ Test message from WhatsApp appears in logs

---

## 📚 **Additional Resources:**

- [Meta Webhook Documentation](https://developers.facebook.com/docs/graph-api/webhooks)
- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [WhatsApp Business API Setup](https://developers.facebook.com/docs/whatsapp/cloud-api/get-started)

---

**Last Updated:** 2025-12-31  
**Version:** 2.0



