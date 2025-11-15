# WhatsApp Chatbot - Complete Conversation Flow

## 📋 Table of Contents
1. [Overview](#overview)
2. [Entry Points](#entry-points)
3. [Main Registration Flow](#main-registration-flow)
4. [Hitchhiker Path](#hitchhiker-path)
5. [Driver Path](#driver-path)
6. [Both Path](#both-path)
7. [Registered User Menu](#registered-user-menu)
8. [Special Commands](#special-commands)
9. [Complete Flow Diagram](#complete-flow-diagram)

---

## Overview

The chatbot has **3 main user types**:
- 🚶 **Hitchhiker** (טרמפיסט) - Looking for rides
- 🚗 **Driver** (נהג) - Offering rides
- 🚶🚗 **Both** (שניהם) - Both hitchhiker and driver

---

## Entry Points

### New User Flow
```
User sends ANY message
        ↓
[Check if registered]
        ↓
    ┌───┴───┐
   NO      YES
    ↓       ↓
Registration  Menu
   Flow
```

### Returning User Flow
```
User sends message
        ↓
[Already registered?]
        ↓
    Show Menu
```

---

## Main Registration Flow

### Step 1-3: Basic Information
```
┌─────────────────────────────────────────────────┐
│  INITIAL STATE                                  │
│  (New user enters)                              │
└─────────────────┬───────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────────┐
│  ASK_FULL_NAME                                  │
│  "היי בורך הבא להייקר הצ'אט בוט לטרמפיסט"     │
│  "מה השם המלא שלך?"                            │
│  Input: TEXT                                    │
│  Saves: full_name                               │
└─────────────────┬───────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────────┐
│  ASK_SETTLEMENT                                 │
│  "באיזה ישוב אתה גר?"                          │
│  Input: TEXT                                    │
│  Saves: home_settlement                         │
└─────────────────┬───────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────────┐
│  ASK_USER_TYPE                                  │
│  "מה אתה?"                                      │
│  Options:                                       │
│    1️⃣ טרמפיסט ונהג (both)                      │
│    2️⃣ טרמפיסט (hitchhiker)                    │
│    3️⃣ נהג (driver)                             │
│    🔄 התחל מחדש (restart)                      │
│  Input: CHOICE                                  │
│  Saves: user_type                               │
└─────────────────┬───────────────────────────────┘
                  ↓
         ┌────────┴────────┐
         │                 │
    Hitchhiker        Both/Driver
      Path              Path
```

---

## Hitchhiker Path

### Looking for Ride Now?
```
┌─────────────────────────────────────────────────┐
│  ASK_LOOKING_FOR_RIDE_NOW                       │
│  "האם אתה מחפש כרגע טרמפ?"                     │
│  Options:                                       │
│    1️⃣ כן (yes)                                  │
│    2️⃣ לא (no)                                   │
│    🔄 התחל מחדש                                │
└─────────────────┬───────────────────────────────┘
                  ↓
          ┌───────┴────────┐
         YES              NO
          ↓                ↓
   [Need Ride Now]   [Set Default Later]
          ↓                ↓
    ASK_DESTINATION   ASK_SET_DEFAULT_DESTINATION
          ↓
          │
          ↓
┌─────────────────────────────────────────────────┐
│  ASK_DESTINATION                                │
│  "לאיזה ישוב?"                                  │
│  Input: TEXT                                    │
│  Saves: destination                             │
└─────────────────┬───────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────────┐
│  ASK_WHEN                                       │
│  "למתי?"                                        │
│  Options:                                       │
│    1️⃣ בזמן הקרוב (soon)                         │
│    2️⃣ בשעה ותאריך מסוים (specific)             │
│    🔄 התחל מחדש                                │
└─────────────────┬───────────────────────────────┘
                  ↓
        ┌─────────┴─────────┐
       SOON              SPECIFIC
        ↓                    ↓
    ASK_TIME_RANGE    ASK_SPECIFIC_DATETIME
        ↓                    ↓
        └─────────┬──────────┘
                  ↓
┌─────────────────────────────────────────────────┐
│  COMPLETE_RIDE_REQUEST                          │
│  "מעולה! הבקשה שלך נשמרה"                      │
│  Action: save_ride_request                      │
└─────────────────┬───────────────────────────────┘
                  ↓
        [Check if also driver?]
                  ↓
         ┌────────┴────────┐
     user_type           user_type
       = both          = hitchhiker
         ↓                  ↓
    [Go to Driver    REGISTRATION_COMPLETE
      questions]
```

### Set Default Destination Path
```
┌─────────────────────────────────────────────────┐
│  ASK_SET_DEFAULT_DESTINATION                    │
│  "רוצה להגדיר יעד קבוע שאליו אתה נוסע?"       │
│  Options:                                       │
│    1️⃣ כן (yes)                                  │
│    2️⃣ לא (no)                                   │
│    🔄 התחל מחדש                                │
└─────────────────┬───────────────────────────────┘
                  ↓
          ┌───────┴────────┐
         YES              NO
          ↓                ↓
    ASK_DEFAULT_      CHECK_IF_ALSO_DRIVER
    DESTINATION_NAME
          ↓
    Saves: default_destination
          ↓
    CHECK_IF_ALSO_DRIVER
```

---

## Driver Path

### Has Driving Routine?
```
┌─────────────────────────────────────────────────┐
│  ASK_HAS_ROUTINE                                │
│  "האם יש לך שגרת נסיעה?"                       │
│  Options:                                       │
│    1️⃣ כן (yes)                                  │
│    2️⃣ לא (no)                                   │
│    🔄 התחל מחדש                                │
└─────────────────┬───────────────────────────────┘
                  ↓
          ┌───────┴────────┐
         YES              NO
          ↓                ↓
   [Routine Flow]    ASK_ALERT_FREQUENCY
```

### Routine Setup Flow
```
┌─────────────────────────────────────────────────┐
│  ASK_ROUTINE_DESTINATION                        │
│  "הקש שם של היעד"                              │
│  Input: TEXT                                    │
│  Saves: routine_destination                     │
└─────────────────┬───────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────────┐
│  ASK_ROUTINE_DAYS                               │
│  "באיזה ימים אתה בדרך כלל נוסע?"               │
│  Input: TEXT (e.g., "א-ה" or "א,ג,ה")          │
│  Saves: routine_days                            │
└─────────────────┬───────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────────┐
│  ASK_ROUTINE_DEPARTURE_TIME                     │
│  "באיזה שעה יוצא מ-{home_settlement}?"          │
│  Input: TEXT (e.g., "07:00")                    │
│  Saves: routine_departure_time                  │
└─────────────────┬───────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────────┐
│  ASK_ROUTINE_RETURN_TIME                        │
│  "באיזה שעה יוצא מ-{routine_destination}?"      │
│  Input: TEXT (e.g., "18:00")                    │
│  Saves: routine_return_time                     │
└─────────────────┬───────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────────┐
│  ASK_ANOTHER_ROUTINE_DESTINATION                │
│  "יש עוד יעד קבוע?"                            │
│  Options:                                       │
│    1️⃣ כן → Back to ASK_ROUTINE_DESTINATION     │
│    2️⃣ לא → ASK_ALERT_PREFERENCE                │
│    🔄 התחל מחדש                                │
└─────────────────┬───────────────────────────────┘
                  ↓
            (Continues to alerts)
```

### Alert Preferences (With Routine)
```
┌─────────────────────────────────────────────────┐
│  ASK_ALERT_PREFERENCE                           │
│  "האם תרצה שאני אתריע:"                         │
│  Options:                                       │
│    1️⃣ על כל בקשה לטרמפ                         │
│    2️⃣ רק על היעדים שאני נוסע                   │
│    3️⃣ רק על היעדים שלי בטווח השעות             │
│    🔄 התחל מחדש                                │
│  Saves: alert_preference                        │
└─────────────────┬───────────────────────────────┘
                  ↓
        REGISTRATION_COMPLETE
```

### Alert Frequency (Without Routine)
```
┌─────────────────────────────────────────────────┐
│  ASK_ALERT_FREQUENCY                            │
│  "מה התדירות שאתה רוצה שאשלח לך התרעות?"       │
│  Options:                                       │
│    1️⃣ טרמפ לכל איזור וכל שעה                   │
│    2️⃣ טרמפ לאיזור מסוים בכל שעה                │
│    3️⃣ טרמפ לאיזור מסוים ושעה מסוימת            │
│    4️⃣ אל תשלח לי בכלל                          │
│    🔄 התחל מחדש                                │
│  Saves: alert_frequency                         │
└─────────────────┬───────────────────────────────┘
                  ↓
        REGISTRATION_COMPLETE
```

---

## Both Path

### Flow for "Both Hitchhiker and Driver"
```
User selects "טרמפיסט ונהג"
        ↓
ASK_LOOKING_FOR_RIDE_NOW
        ↓
   ┌────┴─────┐
  YES        NO
   ↓          ↓
[Ride     [Optional
Request]   Default
 Flow]    Destination]
   ↓          ↓
   └────┬─────┘
        ↓
CHECK_IF_ALSO_DRIVER
 (condition check)
        ↓
  user_type = both?
        ↓
       YES
        ↓
ASK_HAS_ROUTINE
 (Start driver flow)
        ↓
[Complete driver
  questions]
        ↓
REGISTRATION_COMPLETE
```

---

## Registered User Menu

### Main Menu for Returning Users
```
User (registered) sends message
        ↓
┌─────────────────────────────────────────────────┐
│  REGISTERED_USER_MENU                           │
│  "היי {full_name}! 👋"                          │
│  "מה תרצה לעשות?"                               │
│  Options:                                       │
│    1️⃣ אני מחפש טרמפ                            │
│    2️⃣ אני מתכנן יציאה או חזרה                  │
│    3️⃣ אני רוצה לעדכן את השגרה שלי              │
│    4️⃣ עדכון פרטים אישיים                       │
│    🔄 התחל מחדש                                │
└─────────────────┬───────────────────────────────┘
                  ↓
         ┌────────┼────────┐
         │        │        │
    Option 1  Option 2  Option 3  Option 4
         ↓        ↓        ↓        ↓
    Search   Plan Trip  Update   Update
     Ride              Routine  Profile
```

### Option 1: Search Ride
```
ASK_DESTINATION_REGISTERED
  (Has default destination?)
        ↓
   ┌────┴─────┐
  YES        NO
   ↓          ↓
"ליעד הקבוע  ASK_DESTINATION
 שלך?"
   ↓
[Yes/No choice]
   ↓
   └────┬─────┘
        ↓
   ASK_WHEN
        ↓
  [Time flow]
        ↓
COMPLETE_RIDE_REQUEST
```

### Option 2: Plan Trip
```
ASK_TRIP_PLANNING
  "איזו נסיעה אתה מתכנן?"
  Input: Free text
        ↓
Action: save_planned_trip
        ↓
CONFIRM_TRIP_SAVED
  "הנסיעה שלך נשמרה!"
        ↓
      IDLE
```

### Option 3: Update Routine
```
→ Goes directly to ASK_HAS_ROUTINE
  (Driver routine flow)
```

### Option 4: Update Profile
```
ASK_WHAT_TO_UPDATE
  "מה תרצה לעדכן?"
  Options:
    1️⃣ שם → ASK_FULL_NAME
    2️⃣ ישוב → ASK_SETTLEMENT
    3️⃣ יעדים → ASK_ROUTINE_DESTINATION
    4️⃣ התרעות → ASK_ALERT_PREFERENCE
    🔄 התחל מחדש
```

---

## Special Commands

These commands work **at any point** in the conversation:

```
┌─────────────────────────────────────────────────┐
│  SPECIAL COMMANDS (Available Everywhere)         │
├─────────────────────────────────────────────────┤
│  חזור    → Go back one step                     │
│  חדש     → Restart (delete all data)            │
│  מחק     → Delete all data                      │
│  עזרה    → Show help message                    │
│  תפריט   → Show menu (registered users only)    │
│  🔄      → Restart button (in all interactive)  │
└─────────────────────────────────────────────────┘
```

### Command Flow
```
User types "חזור" (back)
        ↓
[Go to previous state]
        ↓
[Show previous message]


User types "חדש" (restart)
        ↓
[Delete all user data]
        ↓
[Show welcome message]
        ↓
ASK_FULL_NAME


User types "תפריט" (menu)
        ↓
[Check if registered]
        ↓
    ┌───┴───┐
   YES      NO
    ↓       ↓
  Show    "Not yet
  Menu    registered"


User clicks 🔄 (restart button)
        ↓
[Delete all user data]
        ↓
[Show welcome message]
        ↓
ASK_FULL_NAME
```

---

## Complete Flow Diagram

### Simplified Overview
```
                    START
                      ↓
              [New or Returning?]
                      ↓
        ┌─────────────┴─────────────┐
       NEW                      RETURNING
        ↓                            ↓
  ┌──────────┐              ┌──────────────┐
  │ WELCOME  │              │ SHOW MENU    │
  │ MESSAGE  │              │              │
  └────┬─────┘              └──────┬───────┘
       ↓                           ↓
  ┌──────────┐              [Menu Options]
  │ ASK NAME │
  └────┬─────┘
       ↓
  ┌──────────────┐
  │ ASK HOME     │
  │ SETTLEMENT   │
  └──────┬───────┘
         ↓
  ┌──────────────┐
  │ ASK USER     │
  │ TYPE         │
  └──────┬───────┘
         ↓
   ┌─────┴──────┬─────────────────┐
   │            │                 │
HITCHHIKER    BOTH             DRIVER
   ↓            ↓                 ↓
[Need ride  [Need ride      [Has routine?]
  now?]      now?]              ↓
   ↓            ↓           ┌────┴────┐
[Ride      [Ride          YES       NO
Request]   Request]         ↓         ↓
   ↓            ↓        [Routine] [Alerts]
   ↓            └──┐     [Setup]     ↓
   ↓               ↓        ↓        ↓
   ↓          [Driver   [Alerts]    ↓
   ↓           Flow]       ↓        ↓
   ↓               ↓       └────┬───┘
   └───────────────┴────────────┘
                   ↓
         ┌──────────────────┐
         │ REGISTRATION     │
         │ COMPLETE         │
         └─────────┬────────┘
                   ↓
              ┌────────┐
              │  IDLE  │
              └────────┘
```

### Data Flow
```
User Information Collected:

BASIC INFO:
  - full_name
  - home_settlement
  - user_type

HITCHHIKER DATA:
  - destination (if immediate ride)
  - time_range or specific_datetime
  - default_destination (optional)

DRIVER DATA:
  - routine_destination(s)
  - routine_days
  - routine_departure_time
  - routine_return_time
  - alert_preference (with routine)
  - alert_frequency (without routine)

SAVED TO:
  user_data.json → User Profile
```

---

## State Transitions Summary

### State Types

1. **Text Input States** (User types free text)
   - `ask_full_name`
   - `ask_settlement`
   - `ask_destination`
   - `ask_routine_destination`
   - `ask_routine_days`
   - `ask_routine_departure_time`
   - `ask_routine_return_time`
   - `ask_time_range`
   - `ask_specific_datetime`
   - `ask_default_destination_name`
   - `ask_trip_planning`

2. **Choice Input States** (User selects from buttons/list)
   - `ask_user_type` (3 options + restart)
   - `ask_looking_for_ride_now` (2 options + restart)
   - `ask_when` (2 options + restart)
   - `ask_set_default_destination` (2 options + restart)
   - `ask_has_routine` (2 options + restart)
   - `ask_another_routine_destination` (2 options + restart)
   - `ask_alert_preference` (3 options + restart)
   - `ask_alert_frequency` (4 options + restart)
   - `registered_user_menu` (4 options + restart)
   - `ask_destination_registered` (2 options + restart)
   - `ask_what_to_update` (4 options + restart)

3. **Conditional States** (Automatic routing)
   - `initial` (routes to `ask_full_name`)
   - `check_if_also_driver` (routes based on user_type)

4. **Action States** (Perform action then transition)
   - `complete_ride_request`
   - `registration_complete`
   - `confirm_trip_saved`

5. **Terminal States** (End of flow)
   - `idle`

---

## User Journey Examples

### Example 1: Simple Hitchhiker
```
1. User: "שלום"
2. Bot: "היי בורך הבא... מה השם המלא שלך?"
3. User: "כפיר"
4. Bot: "באיזה ישוב אתה גר?"
5. User: "תל אביב"
6. Bot: "מה אתה?" [Buttons: טרמפיסט ונהג / טרמפיסט / נהג / 🔄]
7. User: Clicks "טרמפיסט"
8. Bot: "האם מחפש כרגע טרמפ?" [Buttons: כן / לא / 🔄]
9. User: Clicks "כן"
10. Bot: "לאיזה ישוב?"
11. User: "ירושלים"
12. Bot: "למתי?" [Buttons: בזמן הקרוב / בשעה ותאריך / 🔄]
13. User: Clicks "בזמן הקרוב"
14. Bot: "מה טווח השעות?"
15. User: "08:00-10:00"
16. Bot: "מעולה! הבקשה נשמרה"
17. Bot: "ההרשמה הושלמה בהצלחה 🚗"
```

### Example 2: Driver with Routine
```
1. User: "היי"
2. Bot: "מה השם המלא שלך?"
3. User: "יוסי"
4. Bot: "באיזה ישוב אתה גר?"
5. User: "חיפה"
6. Bot: "מה אתה?" [Buttons]
7. User: Clicks "נהג"
8. Bot: "יש לך שגרת נסיעה?" [Buttons: כן / לא / 🔄]
9. User: Clicks "כן"
10. Bot: "הקש שם של היעד"
11. User: "תל אביב"
12. Bot: "באיזה ימים?"
13. User: "א-ה"
14. Bot: "באיזה שעה יוצא מ-חיפה?"
15. User: "07:00"
16. Bot: "באיזה שעה יוצא מ-תל אביב?"
17. User: "18:00"
18. Bot: "יש עוד יעד קבוע?" [Buttons: כן / לא / 🔄]
19. User: Clicks "לא"
20. Bot: "האם תרצה שאני אתריע..." [Buttons with 3 options + 🔄]
21. User: Clicks option
22. Bot: "ההרשמה הושלמה בהצלחה 🚗"
```

### Example 3: Registered User Returns
```
1. User: "שלום"
2. Bot: "היי כפיר! 👋 מה תרצה לעשות?"
   [Buttons: מחפש טרמפ / מתכנן יציאה / עדכון שגרה / עדכון פרטים / 🔄]
3. User: Clicks "מחפש טרמפ"
4. Bot: "ליעד הקבוע שלך (ירושלים)?" [Buttons: כן / לא / 🔄]
5. User: Clicks "כן"
6. Bot: "למתי?" [Buttons]
7. [Continue ride request flow...]
```

### Example 4: Using Restart Button
```
1. User: In middle of registration
2. Bot: "מה אתה?" [Shows buttons including 🔄 התחל מחדש]
3. User: Clicks 🔄 התחל מחדש
4. Bot: [Deletes all user data]
5. Bot: "היי בורך הבא..." (Welcome message)
6. [Starts fresh from beginning]
```

---

## Statistics

- **Total States**: 27
- **Text Input States**: 11
- **Choice Input States**: 10
- **Conditional States**: 2
- **Action States**: 3
- **Terminal States**: 1
- **Special Commands**: 5
- **Restart Buttons**: In all 10 choice states
- **Languages**: Hebrew (עברית)
- **Max Path Length**: ~22 steps (driver with full routine)
- **Min Path Length**: ~10 steps (simple hitchhiker, no immediate ride)

---

## Technical Notes

### Button Limits
- **Reply Buttons**: 1-3 buttons → Now 4 with restart (converts to list)
- **List Messages**: 4-10 items (always includes restart button)

### Data Persistence
- All user data saved to `user_data.json`
- Profile updates happen in real-time
- Conversation state tracked in `current_state`

### State Validation
- Each input validated before transition
- Invalid inputs show error + re-prompt
- Buttons ensure valid choices only

---

**Created**: November 14, 2025
**Version**: 1.0
**Status**: ✅ Production Ready

