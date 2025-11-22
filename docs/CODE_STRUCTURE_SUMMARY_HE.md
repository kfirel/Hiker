# סיכום מבנה הקוד והזרימה - Hiker Bot

## תוכן עניינים
1. [סקירה כללית](#סקירה-כללית)
2. [מבנה הקבצים](#מבנה-הקבצים)
3. [זרימת הנתונים](#זרימת-הנתונים)
4. [רכיבי הליבה](#רכיבי-הליבה)
5. [תהליך עיבוד הודעה](#תהליך-עיבוד-הודעה)
6. [מסד הנתונים](#מסד-הנתונים)
7. [שירותים](#שירותים)
8. [דיאגרמת זרימה](#דיאגרמת-זרימה)

---

## סקירה כללית

**Hiker** הוא בוט WhatsApp חכם לניהול טרמפים בקהילה. המערכת בנויה על Flask ומתקשרת עם WhatsApp Cloud API.

### ארכיטקטורה כללית:
- **שכבת קלט**: Flask webhook מקבל הודעות מ-WhatsApp
- **שכבת עיבוד**: Conversation Engine מטפל בזרימת השיחה
- **שכבת נתונים**: MongoDB (עם fallback ל-JSON)
- **שכבת פלט**: WhatsApp Client שולח תגובות

---

## מבנה הקבצים

### קבצים ראשיים (`src/`)

#### 1. `app.py` - נקודת הכניסה הראשית
**תפקיד**: אפליקציית Flask הראשית, מטפלת ב-webhooks מ-WhatsApp

**פונקציות מרכזיות**:
- `webhook_verify()` - אימות webhook מ-Meta
- `webhook_handler()` - נקודת כניסה להודעות נכנסות
- `process_message()` - עיבוד הודעות טקסט ואינטראקטיביות
- `handle_match_response()` - טיפול באישור/דחיית התאמות

**זרימה**:
```
WhatsApp → webhook_handler → process_message → ConversationEngine → WhatsApp
```

#### 2. `conversation_engine.py` - מנוע השיחה המרכזי
**תפקיד**: מנוע המצב (State Machine) המנהל את זרימת השיחה

**מחלקות ופונקציות מרכזיות**:
- `ConversationEngine` - המחלקה הראשית
- `process_message()` - עיבוד הודעה נכנסת
- `_process_state()` - עיבוד מצב נוכחי
- `_handle_choice_input()` - טיפול בבחירות (כפתורים)
- `_handle_text_input()` - טיפול בקלט טקסט
- `_validate_input()` - אימות קלט משתמש
- `_get_next_state()` - קביעת המצב הבא
- `_check_condition()` - בדיקת תנאים למעבר בין מצבים

**מצבים מיוחדים**:
- `NAME_STATES` - מצבים לאימות שם
- `SETTLEMENT_STATES` - מצבים לאימות ישוב
- `DAYS_STATES` - מצבים לאימות ימים
- `TIME_STATES` - מצבים לאימות שעה
- `TIME_RANGE_STATES` - מצבים לאימות טווח שעות

#### 3. `conversation_flow.json` - הגדרת זרימת השיחה
**תפקיד**: קובץ JSON המגדיר את כל מצבי השיחה והמעברים ביניהם

**מבנה**:
```json
{
  "states": {
    "state_id": {
      "id": "state_id",
      "message": "הודעה למשתמש",
      "expected_input": "choice|text",
      "options": {...},  // אם choice
      "save_to": "profile_key",
      "action": "action_name",
      "next_state": "next_state_id",
      "condition": "condition_name"
    }
  },
  "commands": {
    "פקודה": "command_handler"
  }
}
```

#### 4. `action_executor.py` - מבצע פעולות
**תפקיד**: מבצע פעולות המוגדרות ב-conversation_flow.json

**פעולות עיקריות**:
- `complete_registration` - השלמת רישום
- `save_ride_request` - שמירת בקשת טרמפ
- `save_hitchhiker_ride_request` - שמירת בקשת טרמפיסט + התאמה
- `save_driver_ride_offer` - שמירת הצעת נהג
- `use_default_destination` - שימוש ביעד ברירת מחדל

**זרימה**:
```
State עם action → ActionExecutor.execute() → _execute_{action}() → UserDatabase/Services
```

#### 5. `message_formatter.py` - עיצוב הודעות
**תפקיד**: עיצוב הודעות עם החלפת משתנים וסיכומי משתמש

**פונקציות**:
- `format_message()` - החלפת משתנים ב-`{variable}` patterns
- `get_user_summary()` - יצירת סיכום מידע משתמש
- `get_enhanced_error_message()` - הודעות שגיאה משופרות עם דוגמאות

**משתנים נתמכים**:
- `{full_name}` - שם מלא
- `{destination}` - יעד
- `{user_summary}` - סיכום מלא של המשתמש

#### 6. `command_handlers.py` - מטפל בפקודות
**תפקיד**: מטפל בפקודות מיוחדות כמו "חזור", "חדש", "עזרה"

**פקודות נתמכות**:
- `go_back` - חזרה למצב קודם
- `restart` - איפוס מלא
- `show_help` - הצגת עזרה
- `show_menu` - חזרה לתפריט
- `delete_data` - מחיקת נתונים

#### 7. `validation.py` - אימות קלט
**תפקיד**: אימות כל סוגי הקלט מהמשתמש

**פונקציות אימות**:
- `validate_settlement()` - אימות ישוב (עם הצעות דומות)
- `validate_days()` - אימות ימים (א-ה, א,ג,ה וכו')
- `validate_time()` - אימות שעה (08:00, 7:00, 6)
- `validate_time_range()` - אימות טווח שעות (7-9, 08:00-10:00)
- `validate_name()` - אימות שם
- `validate_datetime()` - אימות תאריך ושעה (מחר 15:00, 15/11/2025 14:30)
- `validate_text_input()` - אימות טקסט כללי

**מאפיינים מיוחדים**:
- התאמה חלקית לישובים עם הצעות
- נרמול קלט (7 → 07:00)
- תמיכה בפורמטים גמישים

#### 8. `whatsapp_client.py` - לקוח WhatsApp
**תפקיד**: תקשורת עם WhatsApp Cloud API

**פונקציות**:
- `send_message()` - שליחת הודעה (טקסט/כפתורים/רשימה)
- `send_button_message()` - שליחת כפתורים אינטראקטיביים (עד 3)
- `send_list_message()` - שליחת רשימה (4-10 אפשרויות)
- `get_user_profile_name()` - קבלת שם פרופיל מ-WhatsApp

#### 9. `user_database.py` - מסד נתונים JSON
**תפקיד**: מסד נתונים JSON פשוט (fallback)

**פונקציות**:
- `create_user()` - יצירת משתמש חדש
- `get_user()` - קבלת נתוני משתמש
- `set_user_state()` - עדכון מצב שיחה
- `save_to_profile()` - שמירה לפרופיל
- `complete_registration()` - השלמת רישום

#### 10. `user_logger.py` - לוגר משתמשים
**תפקיד**: רישום כל האינטראקציות לכל משתמש

**פונקציות**:
- `log_user_message()` - רישום הודעת משתמש
- `log_bot_response()` - רישום תגובת בוט
- `log_event()` - רישום אירוע מיוחד
- `log_error()` - רישום שגיאות

**פורמט לוג**:
```
────────────────────────────────────────
⏰ 2025-11-22T10:30:00
📥 INCOMING
💬 Message: שלום
────────────────────────────────────────
```

#### 11. `timer_manager.py` - מנהל טיימרים
**תפקיד**: ניהול טיימרים להודעות מעקב

**פונקציות**:
- `schedule_followup()` - תזמון הודעת מעקב (ברירת מחדל: 10 דקות)
- `cancel_timer()` - ביטול טיימר

#### 12. `config.py` - הגדרות
**תפקיד**: ניהול הגדרות מהסביבה

**הגדרות**:
- `WHATSAPP_PHONE_NUMBER_ID`
- `WHATSAPP_ACCESS_TOKEN`
- `WEBHOOK_VERIFY_TOKEN`
- `MONGODB_URI`
- `FLASK_PORT`
- `FLASK_DEBUG`

---

## מסד הנתונים

### מבנה מסד הנתונים

#### 1. `database/mongodb_client.py` - לקוח MongoDB
**תפקיד**: ניהול חיבור ל-MongoDB

**פונקציות**:
- `_connect()` - התחברות ל-MongoDB
- `is_connected()` - בדיקת חיבור
- `get_collection()` - קבלת collection
- `_create_indexes()` - יצירת אינדקסים

**Collections**:
- `users` - משתמשים
- `routines` - שגרות נסיעה
- `ride_requests` - בקשות טרמפ
- `matches` - התאמות
- `notifications` - התראות

#### 2. `database/user_database_mongo.py` - מסד נתונים MongoDB
**תפקיד**: מימוש מסד נתונים עם MongoDB + fallback ל-JSON

**מאפיינים**:
- ניסיון חיבור ל-MongoDB
- אם נכשל → fallback ל-JSON
- ממשק אחיד לשני המקורות

**פונקציות**:
- אותן פונקציות כמו `user_database.py` אבל עם תמיכה ב-MongoDB

#### 3. `database/models.py` - מודלים
**תפקיד**: הגדרת מבנה מסמכי MongoDB

**מודלים**:
- `UserModel` - מודל משתמש
- `RoutineModel` - מודל שגרה
- `RideRequestModel` - מודל בקשת טרמפ
- `MatchModel` - מודל התאמה

---

## שירותים

### 1. `services/matching_service.py` - שירות התאמה
**תפקיד**: מציאת נהגים מתאימים לטרמפיסטים

**פונקציות**:
- `find_matching_drivers()` - חיפוש נהגים מתאימים
- `create_matches()` - יצירת מסמכי התאמה
- `_search_routines()` - חיפוש בשגרות
- `_search_active_offers()` - חיפוש בהצעות פעילות
- `_calculate_routine_match_score()` - חישוב ציון התאמה לשגרה
- `_calculate_offer_match_score()` - חישוב ציון התאמה להצעה

**אלגוריתם התאמה**:
1. חיפוש בשגרות נסיעה (`routines`)
2. חיפוש בהצעות נהגים פעילות (`ride_requests`)
3. חישוב ציון התאמה (יעד + זמן)
4. מיון לפי ציון
5. יצירת מסמכי התאמה (`matches`)

### 2. `services/notification_service.py` - שירות התראות
**תפקיד**: שליחת התראות לנהגים על בקשות חדשות

**פונקציות**:
- `notify_drivers_new_request()` - התראה לנהגים על בקשה חדשה
- `_build_driver_notification_message()` - בניית הודעת התראה
- `_log_notification()` - רישום התראה במסד הנתונים

**תהליך**:
1. קבלת רשימת נהגים מתאימים
2. בניית הודעת התראה
3. שליחת הודעה עם כפתורי אישור/דחייה
4. רישום במסד הנתונים

### 3. `services/approval_service.py` - שירות אישורים
**תפקיד**: טיפול באישור/דחיית התאמות

**פונקציות**:
- `driver_approve()` - נהג מאשר התאמה
- `driver_reject()` - נהג דוחה התאמה
- `_notify_hitchhiker_approved()` - התראה לטרמפיסט על אישור

**תהליך אישור**:
1. נהג לוחץ "✅ מאשר"
2. עדכון מצב ההתאמה ל-"approved"
3. עדכון בקשת הטרמפ ל-"approved"
4. דחיית כל ההתאמות האחרות
5. התראה לטרמפיסט

---

## תהליך עיבוד הודעה

### זרימה מלאה:

```
1. WhatsApp → webhook_handler (app.py)
   ↓
2. process_message (app.py)
   ├─ חילוץ פרטי הודעה
   ├─ קבלת שם פרופיל מ-WhatsApp
   └─ זיהוי סוג הודעה (text/interactive)
   ↓
3. conversation_engine.process_message()
   ├─ בדיקת פקודות מיוחדות (_check_commands)
   ├─ קבלת מצב נוכחי (get_user_state)
   ├─ טיפול במצב רשום (idle → registered_user_menu)
   └─ _process_state()
   ↓
4. _process_state()
   ├─ בדיקת תנאים (_check_condition)
   ├─ זיהוי routing states (ללא message/input)
   ├─ בדיקת first_time
   └─ עיבוד קלט לפי סוג:
      ├─ choice → _handle_choice_input()
      │  ├─ אימות בחירה
      │  ├─ שמירה לפרופיל (אם save_to)
      │  ├─ ביצוע action (אם action)
      │  └─ קביעת next_state
      │
      └─ text → _handle_text_input()
         ├─ אימות קלט (_validate_input)
         │  ├─ validate_settlement (עם הצעות)
         │  ├─ validate_time
         │  ├─ validate_days
         │  └─ וכו'
         ├─ שמירה לפרופיל
         ├─ ביצוע action
         └─ קביעת next_state
   ↓
5. ActionExecutor.execute() (אם יש action)
   ├─ _execute_save_hitchhiker_ride_request()
   │  ├─ יצירת RideRequestModel
   │  ├─ שמירה ל-MongoDB
   │  ├─ MatchingService.find_matching_drivers()
   │  ├─ MatchingService.create_matches()
   │  └─ NotificationService.notify_drivers_new_request()
   │
   └─ _execute_complete_registration()
      └─ user_db.complete_registration()
   ↓
6. MessageFormatter.format_message()
   ├─ החלפת משתנים ({full_name}, {destination})
   └─ יצירת user_summary (אם נדרש)
   ↓
7. _build_buttons() (אם יש options)
   ├─ בניית כפתורים מ-options
   └─ הוספת כפתור "התחל מחדש"
   ↓
8. whatsapp_client.send_message()
   ├─ בחירת סוג הודעה (text/button/list)
   └─ שליחה ל-WhatsApp API
   ↓
9. user_logger.log_bot_response()
   └─ רישום ללוג משתמש
```

### דוגמה: טרמפיסט מחפש טרמפ

```
1. משתמש: "מחפש טרמפ"
   ↓
2. State: registered_hitchhiker_menu
   Option: "1" → ask_hitchhiker_when_need_ride
   ↓
3. State: ask_hitchhiker_when_need_ride
   Option: "1" (ממש עכשיו) → ask_hitchhiker_destination
   save_to: "ride_timing" = "now"
   ↓
4. State: ask_hitchhiker_destination
   Input: "תל אביב"
   Validation: validate_settlement("תל אביב") ✓
   save_to: "hitchhiker_destination" = "תל אביב"
   ↓
5. State: confirm_hitchhiker_ride_request
   Action: save_hitchhiker_ride_request
   ↓
6. ActionExecutor:
   - יצירת RideRequestModel
   - שמירה ל-MongoDB (ride_requests)
   - MatchingService.find_matching_drivers()
     ├─ חיפוש ב-routines (יעד: תל אביב)
     └─ חיפוש ב-ride_requests (driver_offer)
   - MatchingService.create_matches()
     └─ יצירת מסמכי MatchModel
   - NotificationService.notify_drivers_new_request()
     └─ שליחת התראות לנהגים עם כפתורים
   ↓
7. תגובה למשתמש: "הבקשה נרשמה..."
```

---

## דיאגרמת זרימה

### זרימת רישום משתמש חדש:

```
initial
  ↓
ask_full_name (text input)
  ↓
ask_user_type (choice: 1/2/3)
  ├─ 1: both → ask_looking_for_ride_now
  ├─ 2: hitchhiker → ask_looking_for_ride_now
  └─ 3: driver → ask_has_routine
```

### זרימת טרמפיסט:

```
ask_looking_for_ride_now
  ├─ 1: yes → ask_destination → ask_when → ask_time_range/ask_specific_datetime
  │                                                          ↓
  │                                              complete_ride_request
  │                                                          ↓
  │                                              check_if_also_driver
  │                                                          ↓
  │                                              (if both) ask_has_routine
  │                                                          ↓
  │                                              (else) idle
  │
  └─ 2: no → ask_set_default_destination → check_if_also_driver
```

### זרימת נהג:

```
ask_has_routine
  ├─ 1: yes → ask_routine_destination → ask_routine_days
  │                                      ↓
  │                           ask_routine_departure_time
  │                                      ↓
  │                           ask_routine_return_time
  │                                      ↓
  │                           ask_another_routine_destination
  │                                      ↓
  │                           ask_alert_preference
  │                                      ↓
  │                           registration_complete
  │
  └─ 2: no → ask_alert_frequency → registration_complete
```

### זרימת משתמש רשום:

```
idle / registration_complete
  ↓
registered_user_menu (routing)
  ├─ user_type_is_both → registered_both_menu
  ├─ user_is_driver → registered_driver_menu
  └─ user_is_hitchhiker → registered_hitchhiker_menu
```

---

## נקודות חשובות

### 1. ניהול מצבים
- כל משתמש נמצא במצב אחד בכל זמן
- מצבים נשמרים ב-`user.state.current_state`
- היסטוריה נשמרת ב-`user.state.history` (עד 10 מצבים)

### 2. Routing States
- מצבים ללא `message` ו-`expected_input` = routing states
- עוברים אוטומטית למצב הבא
- משמשים לניתוב לפי תנאים

### 3. First Time Detection
- בדיקה אם זה הפעם הראשונה במצב
- אם כן → הצגת הודעה
- אם לא → עיבוד קלט

### 4. Validation עם הצעות
- אם יש שגיאת אימות → הצעות דומות
- הצעות נשמרות ב-`context.pending_suggestions`
- מוצגות ככפתורים אינטראקטיביים

### 5. Actions
- פעולות מוגדרות ב-conversation_flow.json
- מבוצעות על ידי ActionExecutor
- יכולות לגשת ל-MongoDB ולשירותים

### 6. Matching Algorithm
- חיפוש בשגרות נסיעה
- חיפוש בהצעות נהגים פעילות
- חישוב ציון התאמה (יעד + זמן)
- יצירת מסמכי התאמה

### 7. Notifications
- התראות לנהגים על בקשות חדשות
- כפתורי אישור/דחייה
- התראות לטרמפיסטים על אישור

---

## סיכום

המערכת בנויה בצורה מודולרית עם הפרדה ברורה של אחריות:

1. **app.py** - נקודת כניסה, webhooks
2. **conversation_engine.py** - לוגיקת שיחה, ניהול מצבים
3. **conversation_flow.json** - הגדרת זרימה (declarative)
4. **validation.py** - אימות קלט
5. **action_executor.py** - ביצוע פעולות
6. **message_formatter.py** - עיצוב הודעות
7. **whatsapp_client.py** - תקשורת WhatsApp
8. **database/** - שכבת נתונים (MongoDB + JSON fallback)
9. **services/** - שירותים עסקיים (matching, notifications, approvals)

הזרימה היא **event-driven** - כל הודעה מפעילה שרשרת עיבוד שמביאה לתגובה מתאימה.


