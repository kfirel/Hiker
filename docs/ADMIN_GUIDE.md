# Admin & Testing Guide 🔧

This guide explains how to use the new secure admin and testing features.

## 🔒 Security Features

The new admin system provides **three layers of security**:

1. **Admin API Endpoints** - Secure REST API with token authentication
2. **WhatsApp Admin Commands** - Convenient commands with phone whitelist
3. **Environment-Based Controls** - Enable/disable features per environment

---

## ⚙️ Configuration

### Step 1: Generate Admin Token

Generate a strong random token:

```bash
openssl rand -hex 32
```

### Step 2: Configure Environment Variables

Add to your `.env` file:

```bash
# Admin token for API authentication (required for API access)
ADMIN_TOKEN=your_generated_token_here

# Enable/disable testing mode (default: false)
TESTING_MODE=true

# Whitelist phone numbers for WhatsApp admin commands (comma-separated)
ADMIN_PHONE_NUMBERS=972501234567,972509876543
```

### Step 3: Restart Server

```bash
python main.py
```

---

## 🌐 Method 1: Admin API Endpoints (RECOMMENDED)

Best for automation, CI/CD, and remote management.

### Authentication

All admin endpoints require the `X-Admin-Token` header:

```bash
curl -H "X-Admin-Token: your_admin_token_here" \
  https://your-server.com/admin/health
```

### Available Endpoints

#### 1. Health Check

```bash
GET /admin/health
```

**Example:**
```bash
curl -H "X-Admin-Token: abc123" \
  http://localhost:8080/admin/health
```

**Response:**
```json
{
  "status": "healthy",
  "testing_mode": true,
  "admin_phones_configured": 2
}
```

---

#### 2. Change Phone Number

```bash
POST /admin/users/{phone_number}/change-phone?new_phone=NEW_NUMBER
```

**Example:**
```bash
curl -X POST \
  -H "X-Admin-Token: abc123" \
  "http://localhost:8080/admin/users/972501234567/change-phone?new_phone=test123"
```

**Response:**
```json
{
  "success": true,
  "message": "User phone changed from 972501234567 to test123",
  "old_phone": "972501234567",
  "new_phone": "test123"
}
```

**Use Case:** Testing with different phone numbers without creating new users

---

#### 3. Delete User

```bash
DELETE /admin/users/{phone_number}
```

**Example:**
```bash
curl -X DELETE \
  -H "X-Admin-Token: abc123" \
  http://localhost:8080/admin/users/test123
```

**Response:**
```json
{
  "success": true,
  "message": "User test123 deleted successfully"
}
```

---

#### 4. Create Test User

```bash
POST /admin/users
```

**Example:**
```bash
curl -X POST \
  -H "X-Admin-Token: abc123" \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "test_driver_1",
    "role": "driver",
    "driver_data": {
      "origin": "גברעם",
      "destination": "תל אביב",
      "days": ["Sunday", "Monday"],
      "departure_time": "09:00",
      "available_seats": 3
    }
  }' \
  http://localhost:8080/admin/users
```

**Response:**
```json
{
  "success": true,
  "message": "Test user test_driver_1 created",
  "user_data": {...}
}
```

---

#### 5. Reset All Users (⚠️ DANGEROUS)

```bash
POST /admin/users/reset-all?confirm=DELETE_ALL_USERS
```

**Example:**
```bash
curl -X POST \
  -H "X-Admin-Token: abc123" \
  "http://localhost:8080/admin/users/reset-all?confirm=DELETE_ALL_USERS"
```

**Response:**
```json
{
  "success": true,
  "message": "Deleted all 15 users",
  "deleted_count": 15
}
```

⚠️ **Use with extreme caution!** This deletes ALL users from the database.

---

## 📱 Method 2: WhatsApp Admin Commands

Convenient commands you can send via WhatsApp (requires configuration).

### Prerequisites

1. Set `TESTING_MODE=true` in environment
2. Add your phone number to `ADMIN_PHONE_NUMBERS`
3. Restart the server

### Available Commands

#### Show Help

```
/admin:help
```

**Response:**
```
🔧 Admin Commands Available:

/admin:change:NEW_NUMBER
  Change your phone number in DB
  Example: /admin:change:test123

/admin:delete:CONFIRM
  Delete your user data
  Example: /admin:delete:CONFIRM

/admin:reset
  Reset to fresh user state

/admin:help
  Show this help message

⚠️ Testing mode is enabled
📱 Your number is whitelisted
```

---

#### Change Your Phone Number

```
/admin:change:NEW_NUMBER
```

**Example:**
```
/admin:change:test_user_1
```

**Response:**
```
✅ Phone number changed!
Old: 972501234567
New: test_user_1

⚠️ Note: You'll need to message from the OLD number to get this response.
```

**Use Case:** Testing the bot with a simple phone number like "test1" instead of your real number

---

#### Delete Your Data

```
/admin:delete:CONFIRM
```

**Example:**
```
/admin:delete:CONFIRM
```

**Response:**
```
✅ Your data has been deleted!
Send any message to start fresh.
```

---

#### Reset to Fresh State

```
/admin:reset
```

**Response:**
```
✅ Your data has been reset!
You can start fresh now.
```

**Use Case:** Testing the onboarding flow again without losing your phone number

---

## 🛡️ Security Notes

### ✅ What's Secure:

1. **Admin API requires authentication** - Can't be called without the token
2. **WhatsApp commands require whitelist** - Only specific numbers can use them
3. **Testing mode must be enabled** - Production can have it disabled
4. **Non-admins get no feedback** - Commands are silently ignored (stealth)
5. **All actions are logged** - Audit trail of admin actions

### ⚠️ Security Recommendations:

1. **Never commit `.env` file** - Keep tokens secret
2. **Use strong random tokens** - Generate with `openssl rand -hex 32`
3. **Disable testing mode in production** - Set `TESTING_MODE=false`
4. **Limit admin phone numbers** - Only add trusted numbers
5. **Rotate tokens regularly** - Change `ADMIN_TOKEN` periodically
6. **Monitor logs** - Watch for suspicious admin activity

---

## 🧪 Testing Workflows

### Workflow 1: Quick Testing with Different Phone Numbers

```bash
# 1. Change to test number via WhatsApp
/admin:change:test1

# 2. Test your feature

# 3. Reset when done
/admin:reset
```

### Workflow 2: Automated Testing via API

```python
import requests

BASE_URL = "http://localhost:8080"
ADMIN_TOKEN = "your_token_here"

headers = {"X-Admin-Token": ADMIN_TOKEN}

# Create test driver
requests.post(
    f"{BASE_URL}/admin/users",
    headers=headers,
    json={
        "phone_number": "driver1",
        "role": "driver",
        "driver_data": {
            "destination": "תל אביב",
            "days": ["Sunday"],
            "departure_time": "09:00"
        }
    }
)

# Create test hitchhiker
requests.post(
    f"{BASE_URL}/admin/users",
    headers=headers,
    json={
        "phone_number": "hitchhiker1",
        "role": "hitchhiker",
        "hitchhiker_data": {
            "destination": "תל אביב",
            "travel_date": "2025-01-15",
            "departure_time": "09:00"
        }
    }
)

# Test matching logic...

# Cleanup
requests.delete(f"{BASE_URL}/admin/users/driver1", headers=headers)
requests.delete(f"{BASE_URL}/admin/users/hitchhiker1", headers=headers)
```

### Workflow 3: CI/CD Testing

```bash
#!/bin/bash
# test_script.sh

# Create test users
curl -X POST -H "X-Admin-Token: $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "test_driver"}' \
  http://localhost:8080/admin/users

# Run tests...

# Cleanup
curl -X POST -H "X-Admin-Token: $ADMIN_TOKEN" \
  "http://localhost:8080/admin/users/reset-all?confirm=DELETE_ALL_USERS"
```

---

## 🐛 Troubleshooting

### Issue: Admin API returns 401 Unauthorized

**Cause:** Missing or invalid `X-Admin-Token` header

**Solution:**
1. Check that `ADMIN_TOKEN` is set in `.env`
2. Make sure you're sending the correct header
3. Verify token matches exactly (no extra spaces)

```bash
# Check current token
grep ADMIN_TOKEN .env

# Test with curl
curl -v -H "X-Admin-Token: your_token" http://localhost:8080/admin/health
```

---

### Issue: Admin API returns 503 Service Unavailable

**Cause:** `ADMIN_TOKEN` not configured in environment

**Solution:**
1. Add `ADMIN_TOKEN=your_token_here` to `.env`
2. Restart the server

---

### Issue: WhatsApp admin commands not working

**Cause:** Multiple possible reasons

**Solution Checklist:**
1. ✅ Is `TESTING_MODE=true` in `.env`?
2. ✅ Is your phone number in `ADMIN_PHONE_NUMBERS`?
3. ✅ Did you restart the server after changing `.env`?
4. ✅ Are you using the correct command format?

```bash
# Check configuration
grep "TESTING_MODE\|ADMIN_PHONE_NUMBERS" .env

# Restart server
pkill -f "python main.py"
python main.py
```

---

### Issue: Commands are silently ignored

**Expected behavior!** For security, non-admin users get no feedback when trying admin commands.

Check logs:
```bash
tail -f server.log | grep "Non-admin"
```

If you see: `⚠️  Non-admin {number} tried command`, then your number isn't whitelisted.

---

## 📊 Comparison: Old vs New System

| Feature | Old System (❌) | New System (✅) |
|---------|----------------|----------------|
| **Security** | None - anyone can use | Token auth + whitelist |
| **Discovery** | Easy to guess (`----`) | Hidden unless admin |
| **Production Safe** | ❌ Always enabled | ✅ Can be disabled |
| **Logging** | Basic | Comprehensive audit trail |
| **Flexibility** | WhatsApp only | API + WhatsApp |
| **Automation** | Not possible | Full API support |
| **Phone Validation** | None | Whitelist required |

---

## 📝 Best Practices

1. **Development**: Enable `TESTING_MODE=true`, use WhatsApp commands
2. **Staging**: Enable API, use automation scripts
3. **Production**: Disable `TESTING_MODE=false`, keep API for emergencies
4. **CI/CD**: Use API endpoints in test scripts
5. **Security**: Rotate `ADMIN_TOKEN` every 90 days

---

## 🚀 Next Steps

After implementing this system, consider:

1. **Add rate limiting** - Prevent admin API abuse
2. **Add audit logging** - Store admin actions in database
3. **Add 2FA** - Extra security layer for admin commands
4. **Add admin dashboard** - Web UI for managing users
5. **Add user impersonation** - Test as specific user without changing DB

---

Built with security in mind 🔒

