# Database Mode Switching Guide

## Overview

The Hiker bot supports **two database modes**:

1. **Production Mode (MongoDB)** - Full-featured mode with matching, notifications, and all services
2. **Test Mode (JSON)** - Simple file-based storage for testing without MongoDB

The system automatically switches between modes based on configuration and MongoDB availability.

---

## Database Modes

### 1. Production Mode (MongoDB) ✅

**Features:**
- Full MongoDB database support
- Matching service enabled
- Notification service enabled
- Approval service enabled
- All features available

**When Used:**
- MongoDB is available and connected
- `USE_JSON_MODE` is not set or `false`
- Default mode when MongoDB is running

### 2. Test Mode (JSON) 🧪

**Features:**
- JSON file-based storage (`user_data.json`)
- Basic user management
- Conversation flow works
- **Matching service disabled** (requires MongoDB)
- **Notification service disabled** (requires MongoDB)
- **Approval service disabled** (requires MongoDB)

**When Used:**
- `USE_JSON_MODE=true` is set (forced test mode)
- MongoDB is unavailable and `REQUIRE_MONGODB=false` (automatic fallback)

---

## Environment Variables

Add these to your `.env` file to control database mode:

### MongoDB Configuration

```bash
# MongoDB connection string
MONGODB_URI=mongodb://localhost:27017/
# Or for MongoDB Atlas:
# MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/

# Database name
MONGODB_DB_NAME=hiker_db
```

### Mode Control Variables

```bash
# Force JSON mode (test mode) - set to 'true' to force JSON, 'false' or unset to use MongoDB
USE_JSON_MODE=false

# Require MongoDB - set to 'true' to raise error if MongoDB unavailable, 'false' to allow JSON fallback
REQUIRE_MONGODB=false
```

---

## How to Switch Between Modes

### Option 1: Use Test Mode (JSON) - For Testing

**Step 1:** Edit `.env` file:

```bash
# Force JSON mode
USE_JSON_MODE=true

# MongoDB config not needed (will be ignored)
# MONGODB_URI=mongodb://localhost:27017/
# MONGODB_DB_NAME=hiker_db
```

**Step 2:** Restart the application:

```bash
python src/app.py
```

**Result:**
```
🧪 TEST MODE: Using JSON database (USE_JSON_MODE=true)
✅ JSON mode enabled - MongoDB disabled
⚠️ Services initialized without MongoDB - matching features disabled
```

**Data Storage:**
- User data stored in `user_data.json` (in project root)
- No MongoDB required
- Basic features work, matching/notifications disabled

---

### Option 2: Use Production Mode (MongoDB) - Default

**Step 1:** Ensure MongoDB is running:

```bash
# Local MongoDB
mongod

# Or using Docker
docker run -d -p 27017:27017 --name mongodb mongo

# Or using Homebrew (macOS)
brew services start mongodb-community
```

**Step 2:** Edit `.env` file:

```bash
# Use MongoDB (default)
USE_JSON_MODE=false
# Or simply don't set USE_JSON_MODE

# MongoDB configuration
MONGODB_URI=mongodb://localhost:27017/
MONGODB_DB_NAME=hiker_db

# Optional: Require MongoDB (raise error if unavailable)
REQUIRE_MONGODB=false
```

**Step 3:** Restart the application:

```bash
python src/app.py
```

**Result:**
```
✅ PRODUCTION MODE: Using MongoDB database
✅ Services initialized with MongoDB
```

**Data Storage:**
- User data stored in MongoDB
- All features enabled
- Matching, notifications, approvals work

---

### Option 3: Automatic Fallback Mode

**When MongoDB is unavailable but you want automatic fallback:**

**Step 1:** Edit `.env` file:

```bash
# Don't force JSON mode
USE_JSON_MODE=false

# Don't require MongoDB (allows fallback)
REQUIRE_MONGODB=false

# MongoDB config (will try to connect)
MONGODB_URI=mongodb://localhost:27017/
MONGODB_DB_NAME=hiker_db
```

**Step 2:** Start app (MongoDB can be running or not):

```bash
python src/app.py
```

**Result if MongoDB available:**
```
✅ PRODUCTION MODE: Using MongoDB database
✅ Services initialized with MongoDB
```

**Result if MongoDB unavailable:**
```
⚠️ FALLBACK MODE: MongoDB unavailable, using JSON database
⚠️ Services initialized without MongoDB - matching features disabled
```

**Behavior:**
- Tries MongoDB first
- Falls back to JSON if MongoDB unavailable
- No error raised (unless `REQUIRE_MONGODB=true`)

---

### Option 4: Require MongoDB (Strict Mode)

**When you want to ensure MongoDB is always used:**

**Step 1:** Edit `.env` file:

```bash
# Don't force JSON mode
USE_JSON_MODE=false

# Require MongoDB (raise error if unavailable)
REQUIRE_MONGODB=true

# MongoDB configuration
MONGODB_URI=mongodb://localhost:27017/
MONGODB_DB_NAME=hiker_db
```

**Step 2:** Start app:

```bash
python src/app.py
```

**Result if MongoDB available:**
```
✅ PRODUCTION MODE: Using MongoDB database
✅ Services initialized with MongoDB
```

**Result if MongoDB unavailable:**
```
❌ RuntimeError: MongoDB connection is required (REQUIRE_MONGODB=true) but MongoDB is not available.
```

**Behavior:**
- Raises error if MongoDB unavailable
- No fallback to JSON
- Ensures production environment always uses MongoDB

---

## Mode Detection Logic

The system determines mode using this logic:

```
1. Check USE_JSON_MODE environment variable
   ├─→ If true → Force JSON mode (test mode)
   └─→ If false/unset → Continue to step 2

2. Try to connect to MongoDB
   ├─→ If connected → Use MongoDB (production mode)
   └─→ If not connected → Continue to step 3

3. Check REQUIRE_MONGODB environment variable
   ├─→ If true → Raise error (MongoDB required)
   └─→ If false/unset → Use JSON fallback (fallback mode)
```

---

## Quick Reference

### Test Mode (JSON)
```bash
USE_JSON_MODE=true
```
- ✅ No MongoDB needed
- ✅ Basic features work
- ❌ Matching disabled
- ❌ Notifications disabled
- ❌ Approvals disabled

### Production Mode (MongoDB)
```bash
USE_JSON_MODE=false
MONGODB_URI=mongodb://localhost:27017/
MONGODB_DB_NAME=hiker_db
```
- ✅ All features enabled
- ✅ Matching works
- ✅ Notifications work
- ✅ Approvals work
- ⚠️ Requires MongoDB running

### Fallback Mode (Auto)
```bash
USE_JSON_MODE=false
REQUIRE_MONGODB=false
MONGODB_URI=mongodb://localhost:27017/
```
- ✅ Tries MongoDB first
- ✅ Falls back to JSON if unavailable
- ✅ No error if MongoDB down
- ⚠️ Features disabled in fallback

### Strict Mode (MongoDB Required)
```bash
USE_JSON_MODE=false
REQUIRE_MONGODB=true
MONGODB_URI=mongodb://localhost:27017/
```
- ✅ Always uses MongoDB
- ✅ Raises error if unavailable
- ✅ Ensures production environment
- ❌ No fallback

---

## Checking Current Mode

When the app starts, check the logs to see which mode is active:

```
✅ PRODUCTION MODE: Using MongoDB database          # MongoDB mode
🧪 TEST MODE: Using JSON database                   # JSON mode
⚠️ FALLBACK MODE: MongoDB unavailable, using JSON # Fallback mode
```

You can also check the database instance:

```python
# In Python console or debug script
from src.database.user_database_mongo import UserDatabaseMongo
db = UserDatabaseMongo()
print(f"MongoDB enabled: {db._use_mongo}")
print(f"Mode: {'MongoDB' if db._use_mongo else 'JSON'}")
```

---

## Data Migration

### From JSON to MongoDB

If you have data in `user_data.json` and want to migrate to MongoDB:

```bash
# 1. Ensure MongoDB is running
# 2. Set MongoDB config in .env
# 3. Run migration script
python scripts/migrate_to_mongodb.py user_data.json
```

### From MongoDB to JSON

To export MongoDB data to JSON (if needed):

```python
# Use MongoDB export tools or write custom script
mongodump --uri="mongodb://localhost:27017/" --db=hiker_db
```

---

## Troubleshooting

### Issue: "MongoDB connection is required" error

**Solution:**
- Set `REQUIRE_MONGODB=false` to allow JSON fallback
- Or ensure MongoDB is running
- Or set `USE_JSON_MODE=true` for test mode

### Issue: Matching/notifications not working

**Solution:**
- Check if MongoDB is connected: Look for "PRODUCTION MODE" in logs
- Ensure `USE_JSON_MODE` is not set to `true`
- Check MongoDB connection string in `.env`

### Issue: Want to test without MongoDB

**Solution:**
- Set `USE_JSON_MODE=true` in `.env`
- Restart application
- Note: Matching features will be disabled

---

## Code Implementation

The mode switching is implemented in:

1. **`src/config.py`** - Environment variable configuration
2. **`src/database/user_database_mongo.py`** - Database initialization logic
3. **`src/app.py`** - Application startup and service initialization

**Key Code Locations:**

- Mode detection: `src/database/user_database_mongo.py::__init__()`
- Service initialization: `src/app.py` (lines 33-75)
- Config variables: `src/config.py` (lines 19-23)

---

## Summary

| Mode | USE_JSON_MODE | REQUIRE_MONGODB | MongoDB Status | Result |
|------|---------------|------------------|----------------|--------|
| Test | `true` | any | any | JSON mode (forced) |
| Production | `false`/unset | any | Connected | MongoDB mode |
| Fallback | `false`/unset | `false`/unset | Not connected | JSON fallback |
| Strict | `false`/unset | `true` | Not connected | Error raised |

**Recommended Settings:**

- **Development/Testing:** `USE_JSON_MODE=true`
- **Production:** `USE_JSON_MODE=false`, `REQUIRE_MONGODB=true`
- **Flexible:** `USE_JSON_MODE=false`, `REQUIRE_MONGODB=false`


