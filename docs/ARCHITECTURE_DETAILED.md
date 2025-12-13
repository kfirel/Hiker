# Hiker Bot - Detailed Architecture Documentation

## Table of Contents
1. [System Overview](#system-overview)
2. [Architecture Layers](#architecture-layers)
3. [Core Modules](#core-modules)
4. [Module Communication Flow](#module-communication-flow)
5. [Data Flow](#data-flow)
6. [Key Design Patterns](#key-design-patterns)
7. [State Machine Architecture](#state-machine-architecture)
8. [Service Layer](#service-layer)

---

## System Overview

Hiker is a WhatsApp-based ride-sharing bot that connects hitchhikers with drivers in the Gevaram settlement. The system is built as a Flask web application that receives webhook events from WhatsApp Cloud API and processes conversations through a state machine-based conversation engine.

### High-Level Architecture

```
┌─────────────────┐
│  WhatsApp API   │
└────────┬────────┘
         │ Webhook Events
         ▼
┌─────────────────┐
│   Flask App     │  (app.py)
│  - Webhook      │
│  - Health Check │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Conversation    │  (conversation_engine.py)
│    Engine       │
│  - State Machine│
│  - Flow Control │
└────────┬────────┘
         │
    ┌────┴────┬──────────────┬──────────────┐
    ▼         ▼              ▼              ▼
┌────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│Action  │ │Validation│ │Message   │ │Command   │
│Executor│ │          │ │Formatter │ │Handler   │
└───┬────┘ └──────────┘ └──────────┘ └──────────┘
    │
    ▼
┌─────────────────────────────────────┐
│         Service Layer              │
│  - MatchingService                 │
│  - NotificationService              │
│  - ApprovalService                 │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│      Database Layer                 │
│  - MongoDB (Primary)                │
│  - JSON (Fallback)                  │
└─────────────────────────────────────┘
```

---

## Architecture Layers

### 1. **Presentation Layer** (`app.py`)
- **Responsibility**: HTTP endpoint handling, webhook verification, message routing
- **Key Components**:
  - Flask application with `/webhook` endpoints (GET for verification, POST for messages)
  - Background thread processing for async message handling
  - Interactive button response handling (approval/rejection)

### 2. **Conversation Layer** (`conversation_engine.py`)
- **Responsibility**: State machine execution, conversation flow management
- **Key Components**:
  - State transitions based on user input
  - Input validation routing
  - Action execution coordination
  - Command handling delegation

### 3. **Business Logic Layer**
- **Action Executor** (`action_executor.py`): Executes business actions (save ride requests, create matches, etc.)
- **Validation** (`validation.py`): Input validation (settlements, times, names, etc.)
- **Message Formatter** (`message_formatter.py`): Message templating and variable substitution
- **Command Handler** (`command_handlers.py`): Special command processing (back, restart, help, menu)

### 4. **Service Layer** (`services/`)
- **MatchingService**: Finds matching drivers/hitchhikers based on destination, time ranges, and routines
- **NotificationService**: Sends WhatsApp notifications for matches and approvals
- **ApprovalService**: Handles driver approval/rejection workflow and name sharing preferences

### 5. **Data Access Layer** (`database/`)
- **UserDatabaseMongo**: User data CRUD operations with MongoDB/JSON fallback
- **MongoDBClient**: MongoDB connection management and collection access
- **Models**: Data models for Users, Routines, RideRequests, Matches

### 6. **Infrastructure Layer**
- **WhatsAppClient** (`whatsapp_client.py`): WhatsApp Cloud API integration
- **UserLogger** (`user_logger.py`): Per-user interaction logging
- **TimerManager** (`timer_manager.py`): Scheduled follow-up messages
- **TimeUtils** (`time_utils.py`): Time parsing and range calculations

---

## Core Modules

### `app.py` - Application Entry Point

**Responsibilities:**
- Initialize all system components (database, services, conversation engine)
- Handle WhatsApp webhook verification (GET `/webhook`)
- Receive incoming messages (POST `/webhook`)
- Process messages in background threads for fast response
- Handle interactive button responses (match approvals/rejections)

**Key Functions:**
- `webhook_verify()`: Meta webhook verification
- `webhook_handler()`: Receives webhook events, spawns background threads
- `process_message()`: Main message processing logic
- `handle_match_response()`: Processes driver approval/rejection buttons

**Dependencies:**
- `ConversationEngine`: Processes user messages
- `WhatsAppClient`: Sends messages
- `UserDatabaseMongo`: User data access
- `TimerManager`: Follow-up scheduling
- `MatchingService`, `NotificationService`: Business logic services

---

### `conversation_engine.py` - Conversation State Machine

**Responsibilities:**
- Load and execute conversation flow from JSON
- Manage user state transitions
- Validate user input based on state
- Execute actions defined in flow
- Build interactive buttons for choices
- Handle routing states (states without messages that auto-advance)

**Key Classes:**
- `ConversationEngine`: Main state machine engine

**Key Methods:**
- `process_message()`: Main entry point - processes user message and returns response
- `_process_state()`: Processes current state with user input
- `_handle_choice_input()`: Processes choice-based input (buttons)
- `_handle_text_input()`: Processes text input with validation
- `_validate_input()`: Routes to appropriate validation function
- `_get_next_state()`: Determines next state based on conditions
- `_check_condition()`: Evaluates state conditions (user type, registration status, etc.)
- `_build_buttons()`: Creates WhatsApp button/list structures

**State Types:**
- **Initial States**: Entry points (e.g., `initial`, `ask_full_name`)
- **Input States**: Require user input (`expected_input: "text"` or `"choice"`)
- **Routing States**: Auto-advance without user input (no `message`, no `expected_input`)
- **Action States**: Execute actions without input (`action` defined, no `expected_input`)

**Flow Control:**
- States can have `condition` and `else_next_state` for conditional routing
- States can have `next_state` for linear flow
- Choices can have `next_state` for branching
- Actions are executed when entering states (if defined)

---

### `action_executor.py` - Business Action Execution

**Responsibilities:**
- Execute actions defined in conversation flow JSON
- Save user data (profiles, ride requests, routines)
- Trigger matching when ride requests/routines are created
- Process auto-approvals for drivers with "always" preference

**Key Methods:**
- `execute()`: Generic action dispatcher (maps action names to methods)
- `_execute_save_hitchhiker_ride_request()`: Creates hitchhiker request and triggers matching
- `_execute_save_driver_ride_offer()`: Creates driver offer and triggers matching
- `_execute_save_routine_and_match()`: Saves routine and finds matching hitchhikers
- `_process_auto_approvals()`: Processes auto-approvals for drivers with "always" preference

**Action Types:**
- `complete_registration`: Marks user as registered
- `save_hitchhiker_ride_request`: Creates hitchhiker request → triggers matching
- `save_driver_ride_offer`: Creates driver offer → triggers matching
- `save_routine_and_match`: Saves routine → triggers matching
- `set_gevaram_as_home`: Sets default home settlement

---

### `validation.py` - Input Validation

**Responsibilities:**
- Validate user input based on state type
- Normalize input values
- Provide suggestions for invalid inputs (e.g., settlement names)
- Return detailed error messages

**Key Functions:**
- `validate_settlement()`: Validates Israeli settlement names with fuzzy matching
- `validate_time()`: Validates time format (HH:MM or H:MM)
- `validate_time_range()`: Validates time ranges (HH:MM-HH:MM or H-H)
- `validate_days()`: Validates Hebrew day formats (א-ה, א,ג,ה, etc.)
- `validate_name()`: Validates name input (length, characters)
- `validate_datetime()`: Validates specific datetime formats
- `validate_text_input()`: Generic text validation

**Validation Flow:**
1. User input received in conversation engine
2. Engine calls `_validate_input()` with state ID
3. Engine routes to appropriate validation function
4. Validation returns `(is_valid, normalized_value, error_message, suggestions)`
5. If invalid, error message shown with suggestions (if available)
6. If valid, normalized value saved to profile

---

### `message_formatter.py` - Message Formatting

**Responsibilities:**
- Format messages with variable substitution (`{full_name}`, `{destination}`, etc.)
- Generate user summaries for display
- Provide enhanced error messages with examples

**Key Methods:**
- `format_message()`: Substitutes variables in state messages
- `get_user_summary()`: Generates comprehensive user profile summary
- `get_enhanced_error_message()`: Adds examples and context to error messages

**Variable Substitution:**
- Variables like `{full_name}`, `{destination}` are replaced with user profile values
- Special variable `{user_summary}` generates full user summary
- Fallback values used if variables not found

---

### `command_handlers.py` - Special Commands

**Responsibilities:**
- Handle special commands (`חזור`, `חדש`, `עזרה`, `תפריט`)
- Manage state history for "go back" functionality
- Provide contextual help based on current state

**Key Methods:**
- `handle_go_back()`: Returns user to previous state
- `handle_restart()`: Restarts conversation (with confirmation for registered users)
- `handle_show_help()`: Shows help menu with contextual tips
- `handle_show_menu()`: Returns user to main menu
- `handle_delete_data()`: Deletes all user data

---

## Module Communication Flow

### Message Processing Flow

```
1. WhatsApp Webhook → app.py::webhook_handler()
   │
   ├─→ Extract message data (phone, text, type)
   ├─→ Get user profile name from WhatsApp API
   └─→ Spawn background thread → process_message()
       │
       ├─→ Handle interactive buttons (approval/rejection)
       │   └─→ approval_service.driver_approve/reject()
       │
       ├─→ Handle special commands
       │   └─→ command_handler.handle_*()
       │
       └─→ conversation_engine.process_message()
           │
           ├─→ Get current state from database
           ├─→ Load state definition from flow JSON
           ├─→ _process_state()
           │   │
           │   ├─→ If first time: Show state message
           │   │   └─→ message_formatter.format_message()
           │   │
           │   ├─→ If input expected: Validate input
           │   │   └─→ validation.validate_*()
           │   │
           │   ├─→ Save input to profile
           │   │   └─→ user_db.save_to_profile()
           │   │
           │   ├─→ Execute action if defined
           │   │   └─→ action_executor.execute()
           │   │       │
           │   │       ├─→ Save ride request/routine
           │   │       ├─→ Trigger matching
           │   │       │   └─→ matching_service.find_matching_*()
           │   │       │       └─→ Create matches
           │   │       │       └─→ notification_service.notify_*()
           │   │       │
           │   │       └─→ Process auto-approvals
           │   │           └─→ approval_service.driver_approve()
           │   │
           │   └─→ Determine next state
           │       └─→ Update user state in database
           │
           └─→ Return (response_message, buttons)
               │
               └─→ whatsapp_client.send_message()
                   └─→ user_logger.log_bot_response()
```

### Matching Flow

```
1. User creates ride request/routine
   │
   └─→ action_executor._execute_save_*()
       │
       ├─→ Save to database (ride_requests/routines collection)
       │
       └─→ matching_service.find_matching_*()
           │
           ├─→ Search routines/offers/requests
           ├─→ Filter by destination
           ├─→ Filter by time range overlap
           ├─→ Filter by day of week (for routines)
           ├─→ Calculate match scores
           └─→ Return sorted matches
           │
           └─→ matching_service.create_matches()
               │
               ├─→ Create match documents
               ├─→ Check for auto-approval (driver preference = "always")
               └─→ notification_service.notify_drivers_new_request()
                   │
                   ├─→ Check driver preference
                   │   │
                   │   ├─→ If "always": Mark for auto-approval
                   │   │   └─→ Process after hitchhiker confirmation
                   │   │
                   │   └─→ If "ask": Send notification with buttons
                   │       └─→ Driver clicks approve/reject
                   │           └─→ approval_service.driver_approve/reject()
                   │               │
                   │               ├─→ Update match status
                   │               ├─→ Reject other pending matches
                   │               └─→ notification_service.notify_hitchhiker_approved()
                   │                   └─→ Send driver contact details
```

### Auto-Approval Flow

```
1. Driver has preference "always" for name sharing
   │
   └─→ Match created with auto_approve=True flag
       │
       └─→ After hitchhiker receives confirmation message
           │
           └─→ action_executor._process_auto_approvals()
               │
               ├─→ Find matches with auto_approve=True
               ├─→ Use atomic operations to prevent duplicates
               ├─→ approval_service.driver_approve(is_auto_approval=True)
               │   │
               │   ├─→ Update match status to "approved"
               │   ├─→ Skip confirmation message to driver
               │   └─→ notification_service.notify_hitchhiker_approved()
               │       └─→ Send driver contact details
               │
               └─→ Send notification to driver (details sent automatically)
```

---

## Data Flow

### User Registration Flow

```
1. User sends first message
   │
   └─→ user_db.create_user(phone_number)
       │
       ├─→ Create user document in MongoDB
       │   - phone_number, created_at, current_state="initial"
       │   - state_context={}, state_history=[]
       │
       └─→ conversation_engine.process_message()
           │
           └─→ State: "initial" → "ask_full_name"
               │
               ├─→ Show welcome message
               ├─→ Wait for name input
               ├─→ Validate name
               ├─→ Save to profile: full_name
               └─→ Next state: "ask_user_type"
                   │
                   ├─→ Show user type options
                   ├─→ Wait for choice
                   ├─→ Save to profile: user_type
                   └─→ Next state: Based on user_type
                       │
                       ├─→ If hitchhiker/both: "ask_looking_for_ride_now"
                       └─→ If driver: "ask_has_routine"
```

### Ride Request Creation Flow

```
1. Hitchhiker completes ride request form
   │
   └─→ State: "confirm_hitchhiker_ride_request"
       │
       └─→ Action: "save_hitchhiker_ride_request"
           │
           └─→ action_executor._execute_save_hitchhiker_ride_request()
               │
               ├─→ Get user data from MongoDB
               │   - hitchhiker_destination
               │   - ride_timing / time_range / specific_datetime
               │
               ├─→ Parse time to range
               │   └─→ time_utils.parse_time_to_range()
               │
               ├─→ Create ride request document
               │   └─→ RideRequestModel.create()
               │       - requester_id, destination, origin
               │       - start_time_range, end_time_range
               │       - type="hitchhiker_request", status="pending"
               │
               ├─→ Save to MongoDB (ride_requests collection)
               │
               └─→ matching_service.find_matching_drivers()
                   │
                   ├─→ Search routines matching destination
                   │   └─→ Filter by time range overlap
                   │   └─→ Filter by day of week
                   │
                   ├─→ Search active driver offers
                   │   └─→ Filter by destination and time range
                   │
                   ├─→ Calculate match scores
                   └─→ Return sorted matches
                   │
                   └─→ matching_service.create_matches()
                       │
                       ├─→ Create match documents for each driver
                       │   └─→ MatchModel.create()
                       │       - ride_request_id, driver_id, hitchhiker_id
                       │       - status="pending_approval"
                       │       - auto_approve=True if driver preference="always"
                       │
                       └─→ notification_service.notify_drivers_new_request()
                           │
                           ├─→ For each driver:
                           │   ├─→ Check share_name_preference
                           │   │
                           │   ├─→ If "always": Mark for auto-approval
                           │   │   └─→ Process after confirmation message
                           │   │
                           │   └─→ If "ask": Send notification with buttons
                           │       └─→ Wait for driver response
```

### Routine Creation Flow

```
1. Driver creates routine
   │
   └─→ State: "confirm_routine"
       │
       └─→ Action: "save_routine_and_match"
           │
           └─→ action_executor._execute_save_routine_and_match()
               │
               ├─→ Get routine data from MongoDB
               │   - routine_destination
               │   - routine_days
               │   - routine_departure_time
               │   - routine_return_time
               │
               ├─→ Parse times to ranges
               │   └─→ time_utils.parse_routine_departure_time()
               │       └─→ Creates 30-minute window around departure time
               │
               ├─→ Create routine document
               │   └─→ RoutineModel.create()
               │       - user_id, destination, days
               │       - departure_time_start, departure_time_end
               │       - return_time_start, return_time_end
               │       - is_active=True
               │
               ├─→ Save to MongoDB (routines collection)
               │
               └─→ matching_service.find_matching_hitchhikers()
                   │
                   ├─→ Search active hitchhiker requests
                   │   └─→ Filter by destination
                   │   └─→ Filter by time range overlap
                   │   └─→ Filter by day of week match
                   │
                   ├─→ Calculate match scores
                   └─→ Return sorted matches
                   │
                   └─→ matching_service.create_matches_for_driver()
                       │
                       ├─→ Create match documents
                       ├─→ Check for auto-approval
                       └─→ notification_service.notify_hitchhikers()
                           └─→ Send notification about new driver routine
```

---

## Key Design Patterns

### 1. **State Machine Pattern**
- **Implementation**: `ConversationEngine` with JSON-defined states
- **Benefits**: 
  - Easy to modify conversation flow without code changes
  - Clear separation between flow logic and business logic
  - Supports conditional routing and branching

### 2. **Strategy Pattern**
- **Implementation**: Different validation strategies based on state type
- **Example**: `_validate_input()` routes to appropriate validator function
- **Benefits**: Easy to add new validation types

### 3. **Template Method Pattern**
- **Implementation**: `ActionExecutor.execute()` dispatches to specific action methods
- **Benefits**: Consistent action execution interface

### 4. **Repository Pattern**
- **Implementation**: `UserDatabaseMongo` abstracts data access
- **Benefits**: 
  - Can switch between MongoDB and JSON without changing business logic
  - Centralized data access logic

### 5. **Service Layer Pattern**
- **Implementation**: Separate services for matching, notifications, approvals
- **Benefits**: 
  - Separation of concerns
  - Reusable business logic
  - Easier testing

### 6. **Observer Pattern** (Implicit)
- **Implementation**: Actions trigger matching and notifications automatically
- **Example**: Saving ride request automatically triggers matching

---

## State Machine Architecture

### State Definition Structure

```json
{
  "id": "state_id",
  "message": "Message with {variables}",
  "expected_input": "text" | "choice" | null,
  "save_to": "profile_key",
  "action": "action_name",
  "condition": "condition_name",
  "next_state": "next_state_id",
  "else_next_state": "alternative_state_id",
  "options": {
    "1": {
      "label": "Option Label",
      "value": "option_value",
      "next_state": "next_state_id",
      "action": "optional_action"
    }
  }
}
```

### State Types

1. **Initial States**: Entry points (`initial`)
2. **Input States**: Require user input
   - Text input: `expected_input: "text"`
   - Choice input: `expected_input: "choice"` with `options`
3. **Routing States**: Auto-advance (no `message`, no `expected_input`)
4. **Action States**: Execute actions (has `action`, no `expected_input`)

### State Transitions

- **Linear**: `next_state` → moves to next state
- **Conditional**: `condition` + `next_state` / `else_next_state`
- **Branching**: Choice `options` with different `next_state` values
- **Auto-advance**: Routing states automatically move to next state

### State History

- States are tracked in `state_history` array (last 10 states)
- Used for "go back" functionality
- Includes timestamp and context snapshot

---

## Service Layer

### MatchingService

**Purpose**: Find matching drivers/hitchhikers based on destination, time ranges, and routines

**Key Methods:**
- `find_matching_drivers(ride_request)`: Finds drivers for hitchhiker request
  - Searches routines matching destination and time range
  - Searches active driver offers
  - Calculates match scores
  - Returns sorted list of matches

- `find_matching_hitchhikers(driver_info, ...)`: Finds hitchhikers for driver routine/offer
  - Searches active hitchhiker requests
  - Filters by destination and time range overlap
  - Checks day of week match for routines
  - Returns sorted list of matches

- `create_matches(...)`: Creates match documents in database
- `create_matches_for_driver(...)`: Creates matches for driver with hitchhikers

**Matching Logic:**
- **Destination Match**: Exact match required
- **Time Range Overlap**: Uses `_time_ranges_overlap()` to check if ranges intersect
- **Day Match**: For routines, checks if current day matches routine days (Hebrew format: א-ה, ב,ד, etc.)
- **Scoring**: Base score + destination match bonus + time overlap bonus

### NotificationService

**Purpose**: Send WhatsApp notifications for matches and approvals

**Key Methods:**
- `notify_drivers_new_request(ride_request_id, driver_phones)`: Notifies drivers about new hitchhiker request
  - Checks driver preference (`always` vs `ask`)
  - If `always`: Marks for auto-approval
  - If `ask`: Sends notification with approve/reject buttons

- `notify_hitchhiker_matches_found(ride_request_id, num_matches)`: Notifies hitchhiker that matches were found
- `_build_driver_notification_message(...)`: Builds notification message with request details

**Notification Flow:**
1. Match created → NotificationService called
2. Check driver preference
3. Send appropriate notification (with/without buttons)
4. Mark notification as sent in match document

### ApprovalService

**Purpose**: Handle driver approval/rejection workflow

**Key Methods:**
- `driver_approve(match_id, driver_phone, is_auto_approval)`: Processes driver approval
  - Updates match status to "approved"
  - Rejects other pending matches for same request
  - Checks name sharing preference
  - Notifies hitchhiker with driver contact details

- `driver_reject(match_id, driver_phone)`: Processes driver rejection
  - Updates match status to "rejected"

- `handle_name_sharing_response(driver_phone, button_id)`: Handles driver's name sharing choice
  - If yes: Sends driver name + phone to hitchhiker
  - If no: Sends only phone number

- `_notify_hitchhiker_approved(...)`: Sends approval notification to hitchhiker
  - Includes driver contact details (name based on preference)
  - Includes destination and time range

**Approval Flow:**
1. Driver clicks approve button
2. `driver_approve()` called
3. Check name sharing preference:
   - `always`: Send name + phone immediately
   - `ask`: Ask driver first, then send based on response
   - `never`: Send only phone number
4. Update match status
5. Reject other pending matches
6. Notify hitchhiker

---

## Database Schema

### Collections

1. **users**: User profiles and state
   - `phone_number` (unique index)
   - `full_name`, `whatsapp_name`
   - `user_type`: "hitchhiker" | "driver" | "both"
   - `current_state`: Current conversation state
   - `state_context`: Context variables
   - `state_history`: State history array
   - `home_settlement`, `default_destination`
   - `alert_preference`, `share_name_with_hitchhiker`

2. **routines**: Driver routines
   - `user_id`, `phone_number`
   - `destination`, `days` (Hebrew format)
   - `departure_time_start`, `departure_time_end` (datetime)
   - `return_time_start`, `return_time_end` (datetime)
   - `is_active`: Boolean

3. **ride_requests**: Ride requests and offers
   - `request_id` (unique)
   - `requester_id`, `requester_phone`
   - `type`: "hitchhiker_request" | "driver_offer"
   - `origin`, `destination`
   - `start_time_range`, `end_time_range` (datetime)
   - `status`: "pending" | "matched" | "approved" | "rejected"
   - `matched_drivers`: Array of driver info
   - `approved_driver_id`
   - `expires_at`: TTL index (24 hours)

4. **matches**: Match documents
   - `match_id` (unique)
   - `ride_request_id`, `driver_id`, `hitchhiker_id`
   - `destination`, `origin`
   - `status`: "pending_approval" | "approved" | "rejected"
   - `auto_approve`: Boolean (for drivers with "always" preference)
   - `notification_sent_to_driver`: Boolean
   - `matched_at`, `driver_response_at`

5. **notifications**: Notification log
   - `recipient_id`, `recipient_phone`
   - `type`: "ride_request" | "approval" | etc.
   - `ride_request_id`, `match_id`
   - `status`: "sent"
   - `sent_at`, `created_at`

### Indexes

- `users.phone_number`: Unique index
- `users.user_type`: Index for filtering
- `routines.user_id`: Index for user's routines
- `routines.destination + days + is_active`: Compound index
- `ride_requests.request_id`: Unique index
- `ride_requests.requester_id`: Index for user's requests
- `ride_requests.status + destination`: Compound index
- `matches.match_id`: Unique index
- `matches.ride_request_id + status`: Compound index
- `matches.driver_id`, `matches.hitchhiker_id`: Indexes for lookups

---

## Error Handling

### Validation Errors
- Invalid input → Error message with examples
- Settlement not found → Suggestions with fuzzy matching
- Invalid format → Enhanced error message with format examples

### Database Errors
- MongoDB connection failure → Falls back to JSON file storage
- Query errors → Logged, user sees generic error message

### WhatsApp API Errors
- Timeout → Logged, retry not attempted (WhatsApp handles retries)
- API errors → Logged with response details

### State Machine Errors
- Invalid state → Fallback to "idle" state
- Missing state definition → Error message, user can restart

---

## Logging Architecture

### System Logging
- Python `logging` module with INFO/DEBUG/ERROR levels
- Logs to console and files (if configured)

### User Interaction Logging
- Per-user log files in `logs/` directory
- Format: `user_{phone_number}.log`
- Logs all incoming/outgoing messages with timestamps
- Logs events (restart, registration, errors)
- Human-readable format with emojis for quick scanning

### Log Levels
- **INFO**: Normal operations (state transitions, matches created, etc.)
- **DEBUG**: Detailed information (validation details, API calls)
- **ERROR**: Errors with tracebacks

---

## Configuration

### Environment Variables (`.env`)
- `WHATSAPP_PHONE_NUMBER_ID`: WhatsApp Business Phone Number ID
- `WHATSAPP_ACCESS_TOKEN`: WhatsApp Cloud API access token
- `WEBHOOK_VERIFY_TOKEN`: Token for webhook verification
- `FLASK_PORT`: Flask server port (default: 5000)
- `FLASK_DEBUG`: Enable auto-reload (default: True)
- `MONGODB_URI`: MongoDB connection string
- `MONGODB_DB_NAME`: Database name (default: hiker_db)

### Configuration Class (`config.py`)
- `Config.validate()`: Validates required environment variables
- Centralized configuration access

---

## Threading and Concurrency

### Background Processing
- Webhook handler returns immediately (200 OK)
- Message processing happens in background thread
- Prevents WhatsApp from retrying due to slow response

### Timer Management
- `TimerManager` uses Python `threading.Timer` for scheduled messages
- Thread-safe with locks for timer cancellation
- Daemon threads (don't prevent app shutdown)

### Database Operations
- MongoDB operations are thread-safe (PyMongo handles connection pooling)
- JSON file operations use file locking (implicit in Python)

---

## Testing Considerations

### Testability Features
- Dependency injection (services passed to constructors)
- Separation of concerns (validation, formatting, business logic)
- Database abstraction (can use in-memory MongoDB or JSON)
- Mockable external dependencies (WhatsApp API)

### Test Structure
- Unit tests for validation functions
- Integration tests for conversation flow
- Mock WhatsApp client for testing without API calls

---

## Future Extensibility

### Adding New States
1. Add state definition to `conversation_flow.json`
2. Add validation function if needed (in `validation.py`)
3. Add action handler if needed (in `action_executor.py`)

### Adding New Actions
1. Add action name to conversation flow JSON
2. Implement `_execute_{action_name}()` in `ActionExecutor`

### Adding New Services
1. Create service class in `services/` directory
2. Initialize in `app.py`
3. Pass to `ActionExecutor` or use directly

### Adding New Validation Types
1. Add validation function to `validation.py`
2. Add state ID to appropriate constant list in `ConversationEngine`
3. Add routing in `_validate_input()`

---

## Summary

The Hiker bot architecture follows a layered, modular design with clear separation of concerns:

1. **Presentation Layer** handles HTTP/webhook communication
2. **Conversation Layer** manages state machine and flow
3. **Business Logic Layer** handles validation, formatting, and actions
4. **Service Layer** provides reusable business services
5. **Data Layer** abstracts database access

The system is designed for:
- **Maintainability**: Clear module boundaries, easy to modify
- **Extensibility**: Easy to add new states, actions, validations
- **Reliability**: Error handling, fallback mechanisms, logging
- **Performance**: Background processing, efficient database queries
- **Testability**: Dependency injection, separation of concerns










