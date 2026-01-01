# 📋 Google Cloud Run - Logging Guide

## 🔴 Problem: Logs Not Appearing in Cloud Console

### **Why This Happens:**

1. **Wrong Log Format:** Cloud Run expects JSON structured logs
2. **Wrong Log Level:** Logs below INFO might be filtered
3. **Buffered Output:** Logs not flushed to stdout
4. **Wrong Service/Region:** Looking at wrong deployment
5. **Time Delay:** Logs take 10-30 seconds to appear

---

## ✅ **Solution 1: Use JSON Logging (RECOMMENDED)**

### **Already Applied in `main.py`!**

```python
import json
import sys
import logging

class CloudRunFormatter(logging.Formatter):
    """Format logs as JSON for Cloud Run"""
    def format(self, record):
        log_obj = {
            "severity": record.levelname,
            "message": record.getMessage(),
            "timestamp": self.formatTime(record, self.datefmt),
            "logger": record.name,
        }
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj)

# Configure logging
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(CloudRunFormatter())

logging.basicConfig(
    level=logging.INFO,
    handlers=[handler]
)
```

---

## 🔍 **How to View Logs in Cloud Console:**

### **Method 1: Web Console (Easiest)**

1. Go to: https://console.cloud.google.com/run
2. Select your service: `hiker` or `hitchhiking-bot`
3. Click **"LOGS"** tab at the top
4. Wait 10-30 seconds for logs to appear

**Filter options:**
- Severity: INFO, WARNING, ERROR
- Time range: Last 1 hour, 24 hours, etc.
- Search: Filter by text

---

### **Method 2: gcloud CLI (Recommended)**

#### **A. Real-time logs (tail):**
```bash
gcloud run services logs read hiker \
  --region=europe-west1 \
  --limit=50 \
  --format="table(timestamp, severity, textPayload)"
```

#### **B. Tail logs (follow):**
```bash
gcloud run services logs tail hiker \
  --region=europe-west1 \
  --format=json
```

#### **C. Filter by severity:**
```bash
gcloud run services logs read hiker \
  --region=europe-west1 \
  --log-filter='severity>=ERROR' \
  --limit=100
```

#### **D. Filter by time:**
```bash
gcloud run services logs read hiker \
  --region=europe-west1 \
  --log-filter='timestamp>"2025-12-31T20:00:00Z"' \
  --limit=50
```

#### **E. Search for specific text:**
```bash
gcloud run services logs read hiker \
  --region=europe-west1 \
  --log-filter='textPayload:"webhook"' \
  --limit=20
```

---

## 🐛 **Troubleshooting:**

### **Issue 1: "No logs found"**

**Check if service exists:**
```bash
gcloud run services list --region=europe-west1
```

**Check service name:**
```bash
# Your service might be called differently
gcloud run services list
```

**Try different regions:**
```bash
gcloud run services list --region=us-central1
gcloud run services list --region=europe-west1
```

---

### **Issue 2: Logs appear but cut off**

**Increase limit:**
```bash
gcloud run services logs read hiker \
  --region=europe-west1 \
  --limit=500
```

---

### **Issue 3: Logs delayed**

**Solution:** Logs can take 10-30 seconds to appear. Be patient!

**Force refresh in web console:**
- Click "Jump to now" button
- Reload the page

---

### **Issue 4: Can't see structured logs**

**Check JSON output:**
```bash
gcloud run services logs read hiker \
  --region=europe-west1 \
  --format=json \
  --limit=10
```

**Should see:**
```json
{
  "severity": "INFO",
  "message": "🚀 Application started",
  "timestamp": "2025-12-31T20:00:00Z",
  "logger": "__main__"
}
```

---

## 📊 **Log Levels Explained:**

| Level | When to Use | Cloud Run Display |
|-------|-------------|-------------------|
| DEBUG | Development only | Not shown by default |
| INFO | Normal operations | ℹ️ Blue |
| WARNING | Potential issues | ⚠️ Yellow |
| ERROR | Errors that need attention | ❌ Red |
| CRITICAL | System failures | 🔴 Red (urgent) |

---

## 🔧 **Advanced: Filter Logs by Field**

### **Filter by request path:**
```bash
gcloud logging read "resource.type=cloud_run_revision \
  AND resource.labels.service_name=hiker \
  AND httpRequest.requestUrl=~'/webhook'" \
  --limit=50 \
  --format=json
```

### **Filter by HTTP status:**
```bash
gcloud logging read "resource.type=cloud_run_revision \
  AND resource.labels.service_name=hiker \
  AND httpRequest.status=200" \
  --limit=50
```

### **Filter by user (phone number):**
```bash
gcloud logging read "resource.type=cloud_run_revision \
  AND resource.labels.service_name=hiker \
  AND jsonPayload.phone_number='972501234567'" \
  --limit=50
```

---

## 📝 **Best Practices:**

### **1. Always Use Structured Logging:**

```python
# ✅ Good - structured
logger.info("User registered", extra={
    "phone": phone_number,
    "role": role,
    "destination": destination
})

# ❌ Bad - unstructured
logger.info(f"User {phone_number} registered as {role}")
```

### **2. Include Context:**

```python
# Add fields that help debugging
logger.info("Processing message", extra={
    "phone": phone_number,
    "message_id": message_id,
    "request_id": request_id,
    "user_role": user.role
})
```

### **3. Use Appropriate Levels:**

```python
logger.debug("Detailed debug info")     # Development only
logger.info("Normal operation")         # Default
logger.warning("Something unexpected")  # Needs attention
logger.error("Error occurred")          # Must fix
logger.critical("System failure")       # Emergency
```

### **4. Always Log Exceptions:**

```python
try:
    result = risky_operation()
except Exception as e:
    logger.error("Operation failed", exc_info=True, extra={
        "operation": "risky_operation",
        "user": phone_number
    })
```

---

## 🚀 **Quick Commands Reference:**

```bash
# View latest 50 logs
gcloud run services logs read hiker --region=europe-west1 --limit=50

# Tail logs (real-time)
gcloud run services logs tail hiker --region=europe-west1

# View errors only
gcloud run services logs read hiker --region=europe-west1 --log-filter='severity>=ERROR'

# Search for text
gcloud run services logs read hiker --region=europe-west1 --log-filter='textPayload:"webhook"'

# View as JSON
gcloud run services logs read hiker --region=europe-west1 --format=json --limit=10

# View specific time range
gcloud run services logs read hiker \
  --region=europe-west1 \
  --log-filter='timestamp>="2025-12-31T20:00:00Z"'
```

---

## 🔍 **Debug Mode (Verbose Logging):**

### **Enable in Cloud Run:**

```bash
# Redeploy with DEBUG level
gcloud run deploy hiker \
  --image gcr.io/PROJECT_ID/hiker \
  --region=europe-west1 \
  --set-env-vars LOG_LEVEL=DEBUG \
  --update-env-vars LOG_LEVEL=DEBUG
```

### **In code:**

```python
# config.py
import os

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# main.py
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    handlers=[handler]
)
```

---

## 📈 **Monitoring & Alerts:**

### **Set up log-based alerts:**

1. Go to Cloud Logging: https://console.cloud.google.com/logs
2. Click "Create Metric"
3. Add filter: `severity>=ERROR`
4. Create alert when count > 10 in 5 minutes

---

## 💡 **Pro Tips:**

1. **Use Request IDs:** Track a request through multiple services
2. **Add Timestamps:** Cloud Run adds them, but you can add custom ones
3. **Log Performance:** Add execution time to logs
4. **Use Labels:** Add service version, environment, etc.
5. **Export Logs:** Send to BigQuery for analysis

---

## 🧪 **Test Your Logging:**

```bash
# 1. Deploy with JSON logging
./deploy.sh

# 2. Send a test message to WhatsApp

# 3. View logs immediately
gcloud run services logs read hiker \
  --region=europe-west1 \
  --limit=50 \
  --format="table(timestamp, severity, textPayload)"

# 4. Should see:
# 2025-12-31 20:00:00  INFO  📥 Received webhook
# 2025-12-31 20:00:01  INFO  📨 Message from: 972501234567
# 2025-12-31 20:00:02  INFO  🤖 AI called function: update_user_records
```

---

## ❓ **Still Not Working?**

### **Check these:**

1. **Service name correct?**
   ```bash
   gcloud run services list
   ```

2. **Region correct?**
   ```bash
   gcloud run services describe hiker --region=europe-west1
   ```

3. **Logs enabled?**
   ```bash
   gcloud run services describe hiker \
     --region=europe-west1 \
     --format="get(spec.template.spec.containers[0].env)"
   ```

4. **Try web console:**
   https://console.cloud.google.com/run

5. **Check audit logs:**
   ```bash
   gcloud logging read "resource.type=cloud_run_revision" \
     --limit=10 \
     --format=json
   ```

---

**Last Updated:** 2025-12-31  
**Tested With:** Cloud Run, Python 3.11+



