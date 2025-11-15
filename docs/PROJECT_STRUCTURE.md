# 📁 Project Structure

## Overview

הפרויקט מאורגן בצורה מקצועית עם הפרדה ברורה בין קוד, טסטים, סקריפטים ותיעוד.

---

## Directory Structure

```
Hiker/
├── README.md                    # Main documentation
├── LICENSE                      # MIT License
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment variables template
├── .gitignore                   # Git ignore rules
│
├── src/                         # 📦 Source Code
│   ├── __init__.py              # Package init
│   ├── app.py                   # Flask application (main entry point)
│   ├── config.py                # Configuration management
│   ├── whatsapp_client.py       # WhatsApp API client
│   ├── conversation_engine.py   # Conversation flow engine
│   ├── conversation_flow.json   # Flow definition (Hebrew)
│   ├── user_database.py         # User data management
│   ├── validation.py            # Input validation
│   └── timer_manager.py         # Timer management
│
├── tests/                       # 🧪 Tests
│   ├── __init__.py              # Package init
│   ├── test_conversation_flow.py          # Main flow tests
│   ├── test_interactive_suggestions.py    # Interactive features tests
│   └── debug_test.py            # Debug test helper
│
├── scripts/                     # 🔧 Helper Scripts
│   ├── start_ngrok.py           # Start ngrok tunnel
│   ├── verify_setup.py          # Verify project setup
│   └── push_to_github.sh        # GitHub deployment script
│
└── docs/                        # 📚 Documentation
    ├── SETUP_GUIDE.md           # Detailed setup instructions
    ├── ARCHITECTURE.md          # System architecture
    ├── CONVERSATION_FLOW_GUIDE.md    # Flow documentation
    ├── VALIDATION_GUIDE.md      # Validation system docs
    ├── INTERACTIVE_BUTTONS_GUIDE.md  # Interactive UI docs
    ├── NGROK_SETUP.md           # Ngrok configuration
    ├── FIND_WEBHOOK_IN_META.md  # Webhook setup guide
    ├── WHERE_TO_PUT_AUTHTOKEN.md
    ├── SCREENSHOTS_GUIDE.md
    ├── START_HERE.md            # Getting started guide
    └── QUICK_REFERENCE.md       # Quick command reference
```

---

## Key Files

### Root Directory

| File | Purpose |
|------|---------|
| `README.md` | Main project documentation |
| `LICENSE` | MIT License |
| `requirements.txt` | Python package dependencies |
| `.env.example` | Template for environment variables |
| `.gitignore` | Files to ignore in git |

### src/ - Source Code

| File | Purpose |
|------|---------|
| `app.py` | Flask application - main entry point |
| `config.py` | Configuration management |
| `whatsapp_client.py` | WhatsApp Cloud API client |
| `conversation_engine.py` | Core conversation logic |
| `conversation_flow.json` | Flow definition (Hebrew) |
| `user_database.py` | User data management (JSON) |
| `validation.py` | Input validation (settlements, dates, times) |
| `timer_manager.py` | Timer management for follow-ups |

### tests/ - Tests

| File | Purpose |
|------|---------|
| `test_conversation_flow.py` | Comprehensive flow tests (47 tests) |
| `test_interactive_suggestions.py` | Interactive suggestions tests |
| `debug_test.py` | Quick debug test helper |

### scripts/ - Helper Scripts

| File | Purpose |
|------|---------|
| `start_ngrok.py` | Start ngrok tunnel for local development |
| `verify_setup.py` | Verify project setup and dependencies |
| `push_to_github.sh` | Automated GitHub deployment |

### docs/ - Documentation

| File | Purpose |
|------|---------|
| `SETUP_GUIDE.md` | Complete setup instructions |
| `ARCHITECTURE.md` | System architecture overview |
| `CONVERSATION_FLOW_GUIDE.md` | Conversation flow documentation |
| `VALIDATION_GUIDE.md` | Validation system explanation |
| `INTERACTIVE_BUTTONS_GUIDE.md` | Interactive buttons feature docs |
| `NGROK_SETUP.md` | Ngrok setup and configuration |
| `QUICK_REFERENCE.md` | Quick command reference |

---

## Running the Project

### From Project Root

```bash
# Run the application
python src/app.py

# Run tests
python tests/test_conversation_flow.py
python tests/test_interactive_suggestions.py

# Run helper scripts
python scripts/start_ngrok.py
python scripts/verify_setup.py
bash scripts/push_to_github.sh
```

### Imports

All imports use the `src.` prefix:

```python
from src.config import Config
from src.whatsapp_client import WhatsAppClient
from src.user_database import UserDatabase
from src.conversation_engine import ConversationEngine
```

Path setup is automatically handled in each file:
```python
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
```

---

## Development Workflow

### 1. Local Development

```bash
# Terminal 1: Start ngrok
python scripts/start_ngrok.py

# Terminal 2: Start Flask app
python src/app.py
```

### 2. Testing

```bash
# Run all tests
python tests/test_conversation_flow.py
python tests/test_interactive_suggestions.py

# Verify setup
python scripts/verify_setup.py
```

### 3. Deployment

```bash
# Push to GitHub
bash scripts/push_to_github.sh
# or manually:
git add .
git commit -m "Your message"
git push
```

---

## File Organization Best Practices

### ✅ DO:
- Keep all source code in `src/`
- Keep all tests in `tests/`
- Keep all scripts in `scripts/`
- Keep all docs in `docs/`
- Use `src.` prefix for imports
- Add `__init__.py` to Python packages

### ❌ DON'T:
- Don't put `.py` files in root directory
- Don't put `.md` files (except README) in root
- Don't commit `.env` or `user_data.json`
- Don't mix test and source code
- Don't use relative imports across packages

---

## Clean Root Directory

The root directory should only contain:
- Configuration files (`.env.example`, `.gitignore`)
- Documentation entry point (`README.md`)
- License (`LICENSE`)
- Dependencies (`requirements.txt`)
- Directories (`src/`, `tests/`, `scripts/`, `docs/`)

Everything else belongs in a subdirectory!

---

## Benefits of This Structure

1. **Professional** - Industry standard layout
2. **Scalable** - Easy to add new features
3. **Clear** - Obvious where everything belongs
4. **Testable** - Tests separated from code
5. **Navigable** - Easy to find files
6. **Maintainable** - Clean separation of concerns
7. **Portable** - Easy to deploy and share

---

## Migration Notes

If you're coming from the old flat structure:
- All `.py` files moved to `src/`
- All `test_*.py` files moved to `tests/`
- All scripts moved to `scripts/`
- Documentation moved to `docs/`
- Imports updated to use `src.` prefix
- Path handling added to each entry point

**No functionality changes** - just better organization! ✨

---

**Last Updated:** November 2025

