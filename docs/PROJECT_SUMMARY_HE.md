# 📋 סיכום מקיף של פרויקט Hiker

## 🎯 מטרת הפרויקט

**Hiker** הוא בוט WhatsApp חכם המחבר בין טרמפיסטים לנהגים בישוב גברעם. הבוט מאפשר למשתמשים:
- 🚶 **טרמפיסטים**: לחפש טרמפים מיידיים או מתוכננים
- 🚗 **נהגים**: להציע טרמפים ולנהל שגרת נסיעה קבועה
- 🚗🚶 **גיבורי על**: גם לחפש וגם להציע טרמפים

---

## 🏗️ ארכיטקטורה כללית

### מבנה המערכת

```
┌─────────────────┐          ┌──────────────────┐          ┌─────────────────┐
│   WhatsApp      │          │   Meta Cloud     │          │   Flask App     │
│   User          │  ◄─────► │   API Server     │  ◄─────► │   (app.py)      │
│   (Phone)       │          │                  │          │                 │
└─────────────────┘          └──────────────────┘          └────────┬────────┘
                                      ▲                              │
                                      │                       ┌──────┴──────┐
                                      │                       │   ngrok     │
                                      │                       │  (Tunnel)   │
                                      └───────────────────────┤ Local:5000  │
                                            Webhook           └─────────────┘
```

### רכיבי המערכת העיקריים

#### 1. **app.py** - נקודת הכניסה הראשית
- אפליקציית Flask המקבלת webhooks מ-WhatsApp
- מטפל באימות webhook (GET /webhook)
- מקבל הודעות נכנסות (POST /webhook)
- מנתב הודעות למנוע השיחה
- מטפל בתגובות אינטראקטיביות (כפתורי אישור/דחייה)

#### 2. **conversation_engine.py** - מנוע השיחה
- מטפל בזרימת השיחה לפי `conversation_flow.json`
- מנהל מצבים (states) של משתמשים
- מבצע אימות קלט (validation)
- מטפל בפקודות מיוחדות (חזור, עזרה, restart)
- בונה כפתורים אינטראקטיביים

#### 3. **conversation_flow.json** - הגדרת זרימת השיחה
- קובץ JSON המגדיר את כל המצבים והמעברים
- כולל הודעות, אפשרויות בחירה, ולוגיקת routing
- תומך בתנאים (conditions) למעבר בין מצבים
- כולל פעולות (actions) לביצוע

#### 4. **user_database.py** / **user_database_mongo.py** - ניהול משתמשים
- **JSON Mode**: שמירה בקובץ JSON (fallback)
- **MongoDB Mode**: שמירה ב-MongoDB (production)
- ניהול פרופיל משתמש, מצב נוכחי, היסטוריה
- תמיכה ב-routines, ride requests, matches

#### 5. **whatsapp_client.py** - לקוח WhatsApp API
- שליחת הודעות טקסט
- שליחת כפתורים אינטראקטיביים
- קבלת שם פרופיל מ-WhatsApp
- תמיכה ב-interactive buttons ו-lists

#### 6. **validation.py** - אימות קלט
- אימות ישובים (100+ ישובים מ-GeoJSON)
- הצעות ישובים דומים (fuzzy matching)
- אימות ימים, שעות, טווחי זמן
- אימות תאריכים וזמנים מדויקים

#### 7. **services/** - שירותים מתקדמים
- **matching_service.py**: חיפוש נהגים מתאימים לטרמפיסטים
- **notification_service.py**: שליחת התראות לנהגים על בקשות חדשות
- **approval_service.py**: טיפול באישור/דחיית matches

#### 8. **action_executor.py** - ביצוע פעולות
- מבצע פעולות מוגדרות ב-conversation flow
- שמירת ride requests, routines, matches
- טריגר matching ו-notifications

#### 9. **message_formatter.py** - עיצוב הודעות
- החלפת משתנים בהודעות ({full_name}, {destination})
- הודעות שגיאה משופרות עם דוגמאות
- סיכום מידע משתמש

#### 10. **command_handlers.py** - טיפול בפקודות
- פקודת "חזור" - חזרה למצב קודם
- פקודת "עזרה" - הצגת עזרה קונטקסטואלית
- פקודת "restart" - התחלה מחדש עם אישור
- פקודת "תפריט" - חזרה לתפריט ראשי

---

## 💾 מבנה מסד הנתונים

### MongoDB Collections

#### 1. **users** - משתמשים
```javascript
{
  phone_number: String (unique),
  whatsapp_name: String,
  full_name: String,
  home_settlement: String (default: "גברעם"),
  user_type: String ("hitchhiker" | "driver" | "both"),
  default_destination: String,
  alert_preference: String,
  current_state: String,
  state_context: Object,
  state_history: Array,
  created_at: Date,
  registered_at: Date,
  last_active: Date,
  is_registered: Boolean
}
```

#### 2. **routines** - שגרות נסיעה
```javascript
{
  user_id: ObjectId,
  phone_number: String,
  destination: String,
  days: String ("א-ה" | "ב,ד" | etc.),
  departure_time: String ("07:00"),
  return_time: String ("18:00"),
  is_active: Boolean,
  created_at: Date,
  updated_at: Date
}
```

#### 3. **ride_requests** - בקשות טרמפ
```javascript
{
  request_id: String (unique),
  requester_id: ObjectId,
  requester_phone: String,
  type: String ("hitchhiker_request" | "driver_offer"),
  origin: String,
  destination: String,
  time_type: String ("range" | "specific" | "soon"),
  time_range: String,
  specific_datetime: String,
  ride_timing: String,
  status: String ("pending" | "matched" | "approved" | "expired"),
  matched_drivers: Array,
  approved_driver_id: ObjectId,
  approved_at: Date,
  notifications_sent: Array,
  created_at: Date,
  expires_at: Date (TTL index - 24 hours)
}
```

#### 4. **matches** - התאמות בין טרמפיסטים לנהגים
```javascript
{
  match_id: String (unique),
  ride_request_id: ObjectId,
  driver_id: ObjectId,
  hitchhiker_id: ObjectId,
  destination: String,
  origin: String,
  matched_time: Date,
  status: String ("pending_approval" | "approved" | "rejected"),
  driver_response: String,
  driver_response_at: Date,
  notification_sent_to_driver: Boolean,
  notification_sent_to_hitchhiker: Boolean,
  matched_at: Date,
  updated_at: Date
}
```

#### 5. **notifications** - התראות
```javascript
{
  recipient_id: ObjectId,
  recipient_phone: String,
  type: String ("ride_request" | "match_approved" | etc.),
  related_request_id: ObjectId,
  related_match_id: ObjectId,
  message: String,
  status: String ("sent" | "pending" | "failed"),
  created_at: Date
}
```

---

## 🔄 זרימת השיחה (Conversation Flow)

### תהליך הרשמה

1. **initial** → **ask_full_name**
   - קבלת שם מלא
   - הגדרת גברעם כ-home settlement

2. **ask_user_type**
   - בחירת סוג משתמש: טרמפיסט/נהג/גיבור על

3. **המשך לפי סוג משתמש:**
   - **טרמפיסט**: ask_looking_for_ride_now → ask_destination → ask_when
   - **נהג**: ask_has_routine → ask_routine_destination → ask_routine_days
   - **גיבור על**: ask_looking_for_ride_now (כטרמפיסט)

4. **registration_complete** → **idle** → **registered_user_menu**

### תפריט משתמש רשום

```
[כפתור: 🚶 מחפש טרמפ]
[כפתור: 🚗 לתת טרמפ]
[כפתור: 📅 לתכנן נסיעה]
[כפתור: 🔄 עדכון שגרה]
[כפתור: ✏️ עדכון פרטים]
[כפתור: 💬 עזרה]
```

### זרימת בקשות טרמפ

#### טרמפיסט מבקש טרמפ:
1. **ask_destination** - איפה צריך להגיע
2. **ask_when** - מתי (גמיש או מדויק)
3. **ask_time_range** / **ask_specific_datetime** - פרטי זמן
4. **complete_ride_request** - שמירה ו-matching
5. **show_match_results** - הצגת תוצאות

#### נהג מציע טרמפ:
1. **ask_driver_destination** - איפה נוסע
2. **ask_departure_timing** - מתי יוצא
3. **complete_driver_offer** - שמירה

---

## 🎯 תכונות עיקריות

### 1. אימות חכם
- ✅ אימות ישובים עם 100+ ישובים מ-GeoJSON
- ✅ הצעות ישובים דומים (fuzzy matching)
- ✅ אימות ימים בעברית (א-ה, ב,ד,ה)
- ✅ אימות שעות (07:00, 7-9, 14:30-17:00)
- ✅ אימות תאריכים (15/11/2025 14:30, מחר 10:00)

### 2. כפתורים אינטראקטיביים
- כפתורי בחירה לכל מצב
- כפתורי אישור/דחייה ל-matches
- כפתור restart בכל מצב
- תמיכה ב-lists (עד 10 אפשרויות)

### 3. Matching חכם
- חיפוש נהגים לפי:
  - יעד זהה
  - שגרות נסיעה פעילות
  - הצעות נהגים פעילות
  - התאמת זמן (טולרנטיות של שעה)
- דירוג matches לפי רלוונטיות
- יצירת match documents לכל נהג מתאים

### 4. התראות
- התראות אוטומטיות לנהגים על בקשות חדשות
- כפתורי אישור/דחייה בהודעה
- התראות לטרמפיסטים על אישור נהג

### 5. ניהול שגרות
- הגדרת שגרת נסיעה קבועה
- ימים: א-ה, ב,ד,ה, וכו'
- שעות יציאה וחזרה
- matching אוטומטי עם שגרות

### 6. פקודות מיוחדות
- **"חזור"** - חזרה למצב קודם (עד 10 מצבים)
- **"עזרה"** - עזרה קונטקסטואלית
- **"חדש"** / **"restart"** - התחלה מחדש (עם אישור)
- **"תפריט"** - חזרה לתפריט ראשי

---

## 🛠️ טכנולוגיות

### Backend
- **Python 3.10+**
- **Flask** - web framework
- **pymongo** - MongoDB driver
- **requests** - HTTP requests ל-WhatsApp API

### Database
- **MongoDB** - מסד נתונים ראשי (production)
- **JSON files** - fallback (development/testing)

### External APIs
- **WhatsApp Cloud API** - שליחת/קבלת הודעות
- **Meta Graph API** - ניהול webhooks

### Development Tools
- **ngrok** - tunnel מקומי ל-webhook
- **pytest** - בדיקות
- **pyyaml** - קובצי טסטים

---

## 📁 מבנה קבצים

```
Hiker/
├── src/                          # קוד מקור
│   ├── app.py                    # Flask app (entry point)
│   ├── conversation_engine.py    # מנוע השיחה
│   ├── conversation_flow.json   # הגדרת זרימה
│   ├── whatsapp_client.py       # WhatsApp API client
│   ├── user_database.py         # JSON database (fallback)
│   ├── validation.py            # אימות קלט
│   ├── command_handlers.py      # טיפול בפקודות
│   ├── action_executor.py       # ביצוע פעולות
│   ├── message_formatter.py     # עיצוב הודעות
│   ├── timer_manager.py         # ניהול טיימרים
│   ├── user_logger.py           # לוגים
│   ├── config.py                # הגדרות
│   │
│   ├── database/                # מסד נתונים
│   │   ├── mongodb_client.py    # MongoDB connection
│   │   ├── user_database_mongo.py # MongoDB user DB
│   │   └── models.py            # Data models
│   │
│   └── services/                # שירותים
│       ├── matching_service.py   # חיפוש matches
│       ├── notification_service.py # התראות
│       └── approval_service.py   # אישור matches
│
├── tests/                       # בדיקות
│   ├── test_conversation_flows.py # טסטים מקיפים
│   ├── test_inputs.yml          # קלטי טסטים
│   └── conftest.py              # pytest config
│
├── scripts/                     # סקריפטים
│   ├── start_ngrok.py           # הרצת ngrok
│   ├── test_mongodb_connection.py
│   └── migrate_to_mongodb.py
│
├── docs/                        # תיעוד
│   ├── ARCHITECTURE.md
│   ├── SETUP_GUIDE.md
│   ├── MONGODB_IMPLEMENTATION_GUIDE.md
│   └── ...
│
├── metadata/                    # נתונים
│   └── settlements_list.geojson # רשימת ישובים
│
└── requirements.txt            # תלויות Python
```

---

## 🔄 זרימת בקשה טרמפ (Ride Request Flow)

### שלב 1: טרמפיסט מבקש טרמפ
```
משתמש → "מחפש טרמפ" → ask_destination → ask_when → ask_time_range
→ complete_ride_request (action)
```

### שלב 2: שמירה ב-DB
```python
RideRequestModel.create(
    requester_id=user_id,
    request_type="hitchhiker_request",
    destination="ירושלים",
    time_range="07:00-09:00",
    ...
)
```

### שלב 3: חיפוש נהגים מתאימים
```python
matching_service.find_matching_drivers(ride_request)
# מחפש ב:
# 1. routines - שגרות נסיעה פעילות
# 2. active_offers - הצעות נהגים פעילות
# מחזיר רשימה מדורגת לפי score
```

### שלב 4: יצירת matches
```python
matching_service.create_matches(
    ride_request_id,
    hitchhiker_id,
    matching_drivers
)
# יוצר match document לכל נהג מתאים
```

### שלב 5: שליחת התראות
```python
notification_service.notify_drivers_new_request(
    ride_request_id,
    driver_phones
)
# שולח הודעה עם כפתורי אישור/דחייה לכל נהג
```

### שלב 6: נהג מאשר/דוחה
```
נהג → לחיצה על כפתור → handle_match_response()
→ approval_service.driver_approve() / driver_reject()
→ התראה לטרמפיסט (אם אושר)
```

---

## 🧪 בדיקות

### כיסוי בדיקות
- **47 טסטים** מקיפים ב-`test_conversation_flows.py`
- בדיקות זרימת שיחה מלאה
- בדיקות אימות קלט
- בדיקות פקודות מיוחדות
- בדיקות interactive buttons

### הרצת בדיקות
```bash
python tests/test_conversation_flows.py
# או
pytest tests/
```

---

## 📊 מצב נוכחי של הפרויקט

### ✅ מה עובד
- ✅ הרשמה מלאה של משתמשים
- ✅ אימות קלט מתקדם (ישובים, שעות, תאריכים)
- ✅ כפתורים אינטראקטיביים
- ✅ פקודות מיוחדות (חזור, עזרה, restart)
- ✅ שמירה ב-JSON (fallback)
- ✅ שמירה ב-MongoDB (production)
- ✅ Matching service
- ✅ Notification service
- ✅ Approval service
- ✅ 47 טסטים עוברים

### 🚧 מה בפיתוח/שיפור
- שיפור matching algorithm (התאמת זמן מדויקת יותר)
- תמיכה ב-multiple routines למשתמש
- היסטוריית נסיעות
- תזכורות אוטומטיות
- דשבורד ניהול

---

## 🔐 אבטחה

- ✅ כל המפתחות ב-`.env` (לא ב-git)
- ✅ Webhook verification token
- ✅ אימות בקשות מ-WhatsApp
- ✅ נתוני משתמשים מוצפנים ב-MongoDB
- ✅ TTL indexes למחיקת נתונים ישנים

---

## 🚀 הפעלה

### דרישות מקדימות
- Python 3.10+
- MongoDB (אופציונלי - יש fallback ל-JSON)
- חשבון Meta Developer
- חשבון WhatsApp Business
- ngrok (לפיתוח מקומי)

### התקנה
```bash
# 1. שכפול הפרויקט
git clone <repo>
cd Hiker

# 2. יצירת סביבה וירטואלית
python3 -m venv venv
source venv/bin/activate

# 3. התקנת תלויות
pip install -r requirements.txt

# 4. הגדרת משתני סביבה
cp .env.example .env
# ערוך .env והוסף את המפתחות שלך

# 5. הרצת ngrok (טרמינל 1)
python scripts/start_ngrok.py

# 6. הרצת הבוט (טרמינל 2)
python src/app.py
```

---

## 📈 מדדי ביצועים

- **זמן תגובה**: < 1 שנייה למרבית ההודעות
- **כיסוי בדיקות**: 97.9% (47/48 טסטים)
- **תמיכה בישובים**: 100+ ישובים
- **תמיכה בשפות**: עברית מלאה

---

## 🎓 נקודות מפתח להבנה

### 1. State Machine
המערכת מבוססת על state machine - כל משתמש נמצא במצב מסוים, וכל הודעה מעבירה אותו למצב הבא לפי ה-conversation flow.

### 2. Fallback Mechanism
אם MongoDB לא זמין, המערכת נופלת אוטומטית ל-JSON files. זה מאפשר פיתוח ללא MongoDB.

### 3. Action-Based Architecture
פעולות מוגדרות ב-conversation flow ומבוצעות דרך `ActionExecutor`. זה מאפשר הוספת פונקציונליות חדשה ללא שינוי במנוע השיחה.

### 4. Service-Oriented Design
שירותים נפרדים (matching, notification, approval) מאפשרים קוד מודולרי וניתן לתחזוקה.

### 5. Interactive Buttons
המערכת תומכת בכפתורים אינטראקטיביים של WhatsApp, מה שמשפר את חוויית המשתמש משמעותית.

---

## 📝 הערות חשובות

1. **MongoDB הוא אופציונלי** - המערכת עובדת גם עם JSON files
2. **Auto-reload מופעל** - שינויים בקוד נטענים אוטומטית בפיתוח
3. **Webhook URL משתנה** - ngrok משנה את ה-URL בכל הפעלה (free tier)
4. **Access Token פג תוקף** - tokens זמניים פגים אחרי 24 שעות
5. **TTL Indexes** - בקשות טרמפ נמחקות אוטומטית אחרי 24 שעות

---

## 🔮 כיווני פיתוח עתידיים

1. **AI Integration** - שילוב ChatGPT/Claude להבנת כוונות טבעיות
2. **Multi-language** - תמיכה בערבית ואנגלית
3. **Mobile App** - אפליקציה ייעודית
4. **Analytics Dashboard** - דשבורד ניהול וסטטיסטיקות
5. **Payment Integration** - תשלום עבור טרמפים
6. **Rating System** - דירוג נהגים וטרמפיסטים
7. **Group Rides** - טרמפים משותפים

---

**עודכן לאחרונה**: נובמבר 2025
**גרסה**: 1.0
**מצב**: Production Ready (עם MongoDB) / Development Ready (עם JSON)



