# Integration Tests - Hiker WhatsApp Bot

## 📋 Overview

Integration tests verify the complete flow of the Hiker bot including:
- ✅ **Data Persistence** - Users, routines, ride requests saved to MongoDB
- ✅ **Matching Algorithm** - Finding matching drivers for hitchhiker requests
- ✅ **Notifications** - Sending WhatsApp notifications to drivers
- ✅ **Approval Flow** - Driver approval/rejection of matches

## 🏗️ Architecture

### Test Structure

```
tests/
├── test_integration_inputs.yml    # Test scenarios (YAML)
├── test_integration_flows.py      # Test runner
├── integration_report_generator.py # HTML report generator
└── conftest.py                    # MongoDB mock fixtures
```

### Test Flow

1. **Load Scenarios** - Read from `test_integration_inputs.yml`
2. **Setup MongoDB Mock** - Use `mongomock` for in-memory database
3. **Run Scenarios** - Execute user interactions chronologically
4. **Collect Data** - Capture database state, matches, notifications
5. **Generate Report** - Create HTML report with:
   - Database state tables
   - Chronological conversation table (multi-user)
   - Match and notification details

## 🧪 Running Tests

### Install Dependencies

```bash
pip install -r requirements.txt
# Includes: mongomock==4.1.2
```

### Run All Integration Tests

```bash
# Using pytest
pytest tests/test_integration_flows.py -v

# Or directly
python tests/test_integration_flows.py
```

### Run Specific Scenario

```bash
pytest tests/test_integration_flows.py::test_all_integration_scenarios -v
```

## 📊 Test Scenarios

### Scenario 1: Complete Matching Flow - Morning Routine
- Driver creates morning routine (Tel Aviv, 07:00)
- Hitchhiker requests ride to same destination
- Matching occurs
- Driver approves match

### Scenario 2: Complete Matching Flow - Afternoon Routine
- Driver creates afternoon routine (Tel Aviv, 14:00)
- Hitchhiker requests ride
- Matching occurs
- Driver approves match

### Scenario 3: Multiple Drivers Matching
- Two drivers with same destination
- One hitchhiker requests ride
- Both drivers get matched
- First driver approves, second rejects

### Scenario 4: Driver Rejection Flow
- Driver rejects match
- Hitchhiker continues searching

### Scenario 5: Specific DateTime Request
- Hitchhiker requests ride for specific future date/time
- Matching occurs
- Driver approves

### Scenario 6: Driver Offer Flow
- Driver offers one-time ride (not routine)
- Hitchhiker requests ride
- Matching occurs
- Driver approves

## 📄 Test Input Format

Each scenario in `test_integration_inputs.yml` follows this structure:

```yaml
scenarios:
  - id: 1
    name: "Scenario Name"
    description: "What this scenario tests"
    users:
      - user_id: "driver_001"
        phone: "0501111111"
        type: "driver"
        setup_messages:
          - "היי"
          - "יוסי נהג"
          # ... more messages
        wait_after: 0
        
      - user_id: "hitchhiker_001"
        phone: "0502222222"
        type: "hitchhiker"
        action_messages:
          - "שלום"
          - "1"  # Looking for ride
          # ... more messages
        wait_after: 0
```

### User Actions

- **setup_messages**: Messages to set up user profile/routine
- **action_messages**: Messages that trigger the main test flow
- **wait_after**: Seconds to wait after this user's actions (for timing tests)

### Special Message Placeholders

- `"approve_MATCH_"` - Will be replaced with actual match ID for approval
- `"reject_MATCH_"` - Will be replaced with actual match ID for rejection

## 📈 Report Structure

### HTML Report Sections

1. **Summary** - Total scenarios, passed/failed counts
2. **Database State Tables**:
   - Users table
   - Routines table
   - Ride Requests table
   - Matches table
3. **Chronological Conversations**:
   - Multi-column table (one column per user)
   - Shows all interactions in chronological order
   - Color-coded by user
   - Shows notifications sent between users

### Report Location

Reports are saved to:
```
test_runs/integration_run_YYYYMMDD_HHMMSS/
├── integration_test_report.html
├── summary.txt
└── logs/
```

Latest report link: `test_runs/latest_integration`

## 🔍 What Gets Tested

### Data Persistence
- ✅ User profiles saved to MongoDB
- ✅ Routines saved correctly
- ✅ Ride requests created with proper structure
- ✅ Matches created for each matching driver

### Matching Algorithm
- ✅ Finds drivers by destination match
- ✅ Matches routines by time overlap
- ✅ Matches active driver offers
- ✅ Scores matches correctly
- ✅ Creates match documents for all matches

### Notifications
- ✅ Sends notifications to matched drivers
- ✅ Includes approval/rejection buttons
- ✅ Button IDs contain correct match IDs
- ✅ Notifications sent to correct phone numbers

### Approval Flow
- ✅ Driver can approve match
- ✅ Driver can reject match
- ✅ Approval updates match status
- ✅ Approval updates ride request status
- ✅ Rejection updates match status
- ✅ Other matches rejected when one approved

## 🛠️ MongoDB Mock

Tests use `mongomock` for in-memory MongoDB:
- No external database required
- Fast execution
- Isolated test runs
- Automatic cleanup

### Mock Setup

```python
@pytest.fixture
def mock_mongo_client():
    import mongomock
    mock_client = mongomock.MongoClient()
    # ... setup MongoDBClient wrapper
```

## 📝 Adding New Scenarios

1. **Add to YAML** - Add new scenario to `test_integration_inputs.yml`
2. **Define Users** - List all users and their messages
3. **Set Actions** - Define what each user does
4. **Run Test** - Execute and check report
5. **Verify** - Check database state and conversations

### Example: Adding a New Scenario

```yaml
scenarios:
  - id: 7
    name: "My New Scenario"
    description: "Tests something new"
    users:
      - user_id: "user_001"
        phone: "0511111111"
        type: "driver"
        setup_messages:
          - "היי"
          # ... setup
        wait_after: 0
```

## 🐛 Debugging

### View Database State

Add debug prints in test:
```python
# In test_integration_flows.py
print(f"Users: {list(mongo_db.mongo.get_collection('users').find())}")
print(f"Matches: {list(mongo_db.mongo.get_collection('matches').find())}")
```

### Check WhatsApp Messages

```python
# In test
sent_messages = whatsapp_client.get_sent_messages()
print(f"Sent {len(sent_messages)} messages")
for msg in sent_messages:
    print(f"To: {msg['to']}, Message: {msg['message']}")
```

### View Report

Open the HTML report in browser:
```bash
open test_runs/latest_integration/integration_test_report.html
```

## ✅ Best Practices

1. **Isolate Scenarios** - Each scenario clears database before running
2. **Use Realistic Data** - Use real Israeli settlements, times, names
3. **Test Edge Cases** - Rejections, multiple matches, etc.
4. **Verify State** - Check database after each important action
5. **Clear Messages** - Clear WhatsApp client between interactions

## 📚 Related Files

- `src/services/matching_service.py` - Matching algorithm
- `src/services/notification_service.py` - Notification sending
- `src/services/approval_service.py` - Approval/rejection handling
- `src/action_executor.py` - Action execution (triggers matching)
- `src/database/models.py` - Data models

---

**Last Updated**: November 2025



