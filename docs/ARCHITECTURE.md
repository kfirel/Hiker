# Architecture Documentation 🏗️

## Overview

The Gvar'am Hitchhiking Bot has been refactored from a monolithic structure (783 lines in one file) to a clean, modular architecture following best practices.

---

## 📁 Project Structure

```
Hiker/
├── main.py                      # FastAPI app & routes (165 lines) ⬇️ 79% reduction
├── admin.py                     # Admin API & testing (356 lines)
├── config.py                    # Configuration & constants (110 lines)
│
├── models/                      # Data models with type safety
│   ├── __init__.py
│   └── user.py                  # Pydantic models (User, DriverData, etc.)
│
├── database/                    # Data persistence layer
│   ├── __init__.py
│   └── firestore_client.py      # Firestore operations
│
├── services/                    # Business logic
│   ├── __init__.py
│   ├── ai_service.py            # Gemini AI integration
│   ├── whatsapp_service.py      # WhatsApp messaging
│   └── matching_service.py      # Driver-hitchhiker matching
│
├── webhooks/                    # Webhook handlers
│   ├── __init__.py
│   └── whatsapp_handler.py      # WhatsApp webhook processing
│
├── docs/                        # Documentation
│   ├── README.md
│   ├── ARCHITECTURE.md          # This file
│   ├── ADMIN_GUIDE.md
│   ├── CHANGES_SUMMARY.md
│   └── MIGRATION_GUIDE.md
│
├── test_admin_api.py            # Admin API tests
├── requirements.txt
├── Dockerfile
└── README.md
```

---

## 🎯 Design Principles

### 1. **Separation of Concerns**
Each module has a single, well-defined responsibility:

- **main.py**: HTTP routing and app lifecycle
- **config.py**: Configuration management
- **models/**: Data structure definitions
- **database/**: Data persistence
- **services/**: Business logic
- **webhooks/**: External API integration

### 2. **Dependency Flow**

```
main.py
  ├─> webhooks/whatsapp_handler
  │     ├─> services/ai_service
  │     │     ├─> database/firestore_client
  │     │     ├─> services/whatsapp_service
  │     │     └─> services/matching_service
  │     └─> services/whatsapp_service
  ├─> database/firestore_client
  └─> admin

All modules depend on:
  ├─> config
  └─> models
```

**Rules:**
- No circular dependencies
- Services don't import from webhooks
- Database layer is independent of services
- All modules can use config and models

### 3. **Type Safety**
Using Pydantic models for all data structures:

```python
from models import User, DriverData, HitchhikerData

# Type-safe data handling
driver_data = DriverData(
    destination="תל אביב",
    days=["Sunday", "Monday"],
    departure_time="09:00"
)
```

### 4. **Testability**
Each module can be tested independently:

```python
# Test AI service without WhatsApp
from services.ai_service import process_message_with_ai

# Test database without HTTP layer
from database import get_or_create_user

# Test matching logic in isolation
from services.matching_service import find_matches_for_user
```

---

## 📦 Module Details

### **main.py** (165 lines)

**Responsibility**: FastAPI application setup and HTTP routing

**Contains**:
- FastAPI app initialization
- Startup/shutdown event handlers
- Route definitions (`/`, `/webhook`, `/users`)
- Minimal business logic

**Dependencies**: All other modules

**Example**:
```python
@app.post("/webhook")
async def handle_webhook(request: Request):
    body = await request.json()
    for entry in body["entry"]:
        for message in entry["changes"][0]["value"]["messages"]:
            await handle_whatsapp_message(message)
```

---

### **config.py** (110 lines)

**Responsibility**: Centralized configuration management

**Contains**:
- Environment variables
- System prompts (Hebrew messages)
- Default values
- Application constants

**Benefits**:
- Single source of truth
- Easy to modify prompts
- Environment-specific configs
- No hardcoded values in business logic

**Example**:
```python
from config import WELCOME_MESSAGE, DEFAULT_AVAILABLE_SEATS

# Use anywhere in the app
await send_message(phone, WELCOME_MESSAGE)
seats = function_args.get("available_seats", DEFAULT_AVAILABLE_SEATS)
```

---

### **models/** (User Data Models)

**Responsibility**: Type-safe data structures

**Files**:
- `user.py`: User, DriverData, HitchhikerData, ChatMessage

**Benefits**:
- Type checking at runtime
- Auto-validation
- IDE autocomplete
- Self-documenting code

**Example**:
```python
from models import User, DriverData

# Validated at creation
driver_data = DriverData(
    destination="תל אביב",
    days=["Sunday"],
    departure_time="09:00",
    available_seats=3  # Type-checked as int
)

# Invalid data raises ValidationError
driver_data = DriverData(
    destination="תל אביב",
    available_seats="three"  # ❌ Error: must be int
)
```

---

### **database/** (Data Layer)

**Responsibility**: All Firestore operations

**Files**:
- `firestore_client.py`: CRUD operations for users

**Functions**:
- `initialize_db()`: Setup Firestore client
- `get_or_create_user()`: User management
- `add_message_to_history()`: Chat history
- `update_user_role_and_data()`: Update user records
- `get_drivers_by_route()`: Search drivers
- `get_hitchhiker_requests()`: Search hitchhikers

**Benefits**:
- Database logic isolated
- Easy to swap database (Redis, PostgreSQL, etc.)
- Consistent error handling
- Reusable across services

**Example**:
```python
from database import get_or_create_user, update_user_role_and_data

# Get user
user_data, is_new = await get_or_create_user("972501234567")

# Update role
await update_user_role_and_data(
    "972501234567",
    "driver",
    {"destination": "תל אביב", ...}
)
```

---

### **services/** (Business Logic)

**Responsibility**: Core application logic

#### **ai_service.py** (230 lines)

Gemini AI integration with function calling

**Functions**:
- `get_function_tool()`: Define AI functions
- `process_message_with_ai()`: Main AI pipeline
- `execute_function_call()`: Handle AI function calls

**Flow**:
1. Receive user message
2. Build conversation context
3. Call Gemini API with function tools
4. Execute function calls (update database, find matches)
5. Get AI response
6. Send to user

---

#### **whatsapp_service.py** (50 lines)

WhatsApp Cloud API messaging

**Functions**:
- `send_whatsapp_message()`: Send text messages

**Benefits**:
- Centralized message sending
- Consistent error handling
- Easy to add features (media, buttons, etc.)

---

#### **matching_service.py** (55 lines)

Driver-hitchhiker matching logic

**Functions**:
- `find_matches_for_user()`: Find compatible rides

**Current Logic**:
- Simple destination matching
- Returns top 3 matches

**Future Enhancements**:
- Fuzzy string matching
- Time-based compatibility
- Route optimization
- Distance calculation

---

### **webhooks/** (External Integration)

**Responsibility**: Process incoming webhooks

#### **whatsapp_handler.py** (60 lines)

WhatsApp webhook processing

**Functions**:
- `handle_whatsapp_message()`: Process single message

**Flow**:
1. Parse message from webhook
2. Check for admin commands
3. Get/create user
4. Send welcome if new user
5. Process with AI
6. Handle errors

---

### **admin.py** (356 lines)

**Responsibility**: Admin features and testing

**Features**:
- REST API with token authentication
- WhatsApp admin commands
- User management (create, delete, modify)
- Phone number whitelisting

See [ADMIN_GUIDE.md](ADMIN_GUIDE.md) for details.

---

## 🔄 Request Flow

### **Incoming WhatsApp Message**

```
1. WhatsApp Cloud API
   ↓
2. POST /webhook (main.py)
   ↓
3. handle_whatsapp_message() (webhooks/)
   ↓
4. Check admin commands
   ├─> YES: admin.handle_admin_whatsapp_command()
   └─> NO: Continue
   ↓
5. get_or_create_user() (database/)
   ↓
6. send_whatsapp_message() if new user (services/)
   ↓
7. process_message_with_ai() (services/)
   ├─> Build conversation context
   ├─> Call Gemini API
   ├─> execute_function_call()
   │   ├─> update_user_role_and_data() (database/)
   │   └─> find_matches_for_user() (services/)
   └─> send_whatsapp_message() (services/)
   ↓
8. Return 200 OK
```

---

## 🧪 Testing Strategy

### **Unit Tests** (Isolated Testing)

```python
# Test AI service
def test_function_tool_schema():
    tool = get_function_tool()
    assert tool.function_declarations[0].name == "update_user_records"

# Test matching service
@pytest.mark.asyncio
async def test_find_matches():
    matches = await find_matches_for_user(
        "hitchhiker",
        {"destination": "תל אביב"}
    )
    assert "matches_found" in matches
```

### **Integration Tests**

```python
# Test full message flow
@pytest.mark.asyncio
async def test_message_processing():
    message = {
        "from": "test_user",
        "type": "text",
        "text": {"body": "אני מחפש טרמפ לתל אביב מחר"}
    }
    
    result = await handle_whatsapp_message(message)
    assert result == True
```

### **Admin API Tests**

See `test_admin_api.py` for examples.

---

## 📊 Metrics

### **Before Refactoring**

| Metric | Value |
|--------|-------|
| Files | 1 (main.py) |
| Lines | 783 |
| Functions | 15+ |
| Testability | Low |
| Maintainability | Low |
| Reusability | Low |

### **After Refactoring**

| Metric | Value |
|--------|-------|
| Files | 11 modules |
| Main file | 165 lines (79% reduction) |
| Modularity | High |
| Testability | High |
| Maintainability | High |
| Reusability | High |
| Type Safety | ✅ Pydantic models |
| Documentation | ✅ Comprehensive |

---

## 🚀 Benefits

### **1. Maintainability**
- Changes are localized to specific modules
- Easy to understand what each file does
- Reduced cognitive load

### **2. Testability**
- Each module can be tested independently
- Mock dependencies easily
- Higher test coverage possible

### **3. Reusability**
- Services can be used in different contexts
- Database layer can be reused in scripts
- Models ensure consistency

### **4. Scalability**
- Easy to add new features
- Can split into microservices if needed
- Team can work on different modules simultaneously

### **5. Type Safety**
- Catch errors at development time
- Better IDE support
- Self-documenting code

---

## 🔧 Adding New Features

### **Example: Add Email Notifications**

1. **Create service**:
```python
# services/email_service.py
async def send_email_notification(to: str, message: str):
    # Implementation
    pass
```

2. **Update config**:
```python
# config.py
EMAIL_API_KEY = os.getenv("EMAIL_API_KEY")
```

3. **Use in matching service**:
```python
# services/matching_service.py
from services.email_service import send_email_notification

async def notify_matches(user_phone, matches):
    # Send WhatsApp
    await send_whatsapp_message(...)
    
    # Send Email
    await send_email_notification(...)
```

4. **No changes needed in**:
- main.py
- webhooks/
- database/
- models/

---

## 📚 Related Documentation

- **[README.md](../README.md)**: Project overview
- **[ADMIN_GUIDE.md](ADMIN_GUIDE.md)**: Admin features
- **[CHANGES_SUMMARY.md](CHANGES_SUMMARY.md)**: Recent changes
- **[MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)**: Migration from old system

---

## 🎓 Best Practices Applied

✅ **Separation of Concerns**: Each module has one responsibility  
✅ **DRY (Don't Repeat Yourself)**: No code duplication  
✅ **SOLID Principles**: Especially Single Responsibility  
✅ **Type Safety**: Pydantic models throughout  
✅ **Documentation**: Comprehensive docstrings  
✅ **Error Handling**: Consistent patterns  
✅ **Configuration Management**: Centralized in config.py  
✅ **Dependency Management**: Clear dependency flow  

---

## 🔄 Migration from Old Structure

See [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) for detailed migration instructions.

**Quick Summary**:
- Old: 1 file (main.py) with 783 lines
- New: 11 modules with clear responsibilities
- Backup: `main_old.py.backup`

**Breaking Changes**: None! The API remains the same.

---

**Questions?** Check the other documentation files or review the code - each module is well-documented!

