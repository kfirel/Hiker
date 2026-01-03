# 🎯 ממשק ניהול Hiker - מדריך מלא

## 📖 תוכן עניינים
1. [סקירה כללית](#סקירה-כללית)
2. [תכונות](#תכונות)
3. [התקנה ועדכון](#התקנה-ועדכון)
4. [שימוש](#שימוש)
5. [API Documentation](#api-documentation)
6. [פתרון בעיות](#פתרון-בעיות)

---

## 🌟 סקירה כללית

ממשק ניהול Hiker הוא פאנל אדמין מלא לניהול מערכת הטרמפים.  
הממשק בנוי עם **React** בצד הלקוח ו-**FastAPI** בצד השרת, ורץ על **Google Cloud Run**.

### טכנולוגיות:
- **Frontend**: React 18, Vite, Tailwind CSS, Recharts, TanStack Table, React Query
- **Backend**: FastAPI, Python 3.11, Firestore
- **Cloud**: Google Cloud Run, Cloud Build, Container Registry
- **Authentication**: Token-based (X-Admin-Token header)

---

## ✨ תכונות

### 📊 Dashboard
- סטטיסטיקות כלליות (משתמשים, נסיעות, התאמות)
- גרפים של מגמות (משתמשים חדשים, נסיעות, יעדים פופולריים)
- שעות שיא לפעילות
- עדכון אוטומטי כל 30 שניות

### 👥 ניהול משתמשים
- **טבלה מפורטת** עם:
  - טלפון, שם, נסיעות, בקשות טרמפ, הודעות
  - נראה לאחרונה, תאריך הצטרפות
- **חיפוש וסינון**: לפי שם או טלפון
- **מיון**: לפי כל עמודה
- **ייצוא CSV**: כל הנתונים
- **🆕 לחיצה על משתמש**: פותח Modal עם:
  - **היסטוריית צ'אט**: 100 הודעות אחרונות
  - **פרטים**: מידע מפורט על המשתמש
- **🆕 מחיקת משתמש**: כפתור 🗑️ עם אישור

### 🚗 ניהול נסיעות
- **🆕 2 טבלאות באותו מסך**:
  - **נהגים פעילים** (רקע כחול)
  - **טרמפיסטים פעילים** (רקע ירוק)
- **פרטים מלאים**:
  - שם, טלפון, מקור, יעד
  - זמנים, תאריכים, גמישות
  - הערות
- **🆕 לחיצה על נסיעה**: פותח Modal עם:
  - פרטי הנסיעה המלאים
  - מרחק המסלול בק"מ
  - טווח התאמה (threshold)
  - קישור ל-Google Maps
- **ייצוא CSV נפרד**: לנהגים ולטרמפיסטים
- **סינון**: לפי יעד

### 🐛 לוגים ושגיאות
- **שגיאות**: כל השגיאות במערכת עם stack trace
- **פעילות**: לוג של פעולות מערכת
- **סינון**: לפי חומרה, תאריך
- **ניקוי**: מחיקת לוגים ישנים

---

## 🚀 התקנה ועדכון

### דרישות מקדימות:
- Python 3.11+
- Node.js 18+ (רק לפיתוח מקומי)
- Google Cloud Project עם Firestore
- ADMIN_TOKEN (סיסמת ניהול)

### התקנה מקומית:

#### 1. Clone הפרויקט
```bash
git clone [YOUR_REPO_URL]
cd Hiker
```

#### 2. התקנת Backend
```bash
python3 -m venv venv
source venv/bin/activate  # או: venv\Scripts\activate ב-Windows
pip install -r requirements.txt
```

#### 3. הגדרת משתני סביבה
צור קובץ `.env`:
```bash
GOOGLE_CLOUD_PROJECT=your-project-id
ADMIN_TOKEN=your-secret-token
```

#### 4. התקנת Frontend (אופציונלי - לפיתוח)
```bash
cd frontend
npm install
npm run dev  # רק לפיתוח
npm run build  # לייצור
```

#### 5. הרצת השרת
```bash
python3 main.py
```

גש ל: `http://localhost:8080/admin`

---

### עדכון בענן (Google Cloud Run)

#### דרך 1: Google Cloud Console (מומלץ!)
1. פתח [Cloud Console](https://console.cloud.google.com)
2. עבור ל-**Cloud Build** → **Triggers**
3. לחץ על ה-Trigger הקיים
4. לחץ **RUN**
5. המערכת תתעדכן אוטומטית תוך 5-10 דקות

#### דרך 2: Cloud Shell
```bash
# 1. Clone/Pull
git clone [YOUR_REPO_URL] || (cd Hiker && git pull)
cd Hiker

# 2. Build
gcloud builds submit --tag gcr.io/[PROJECT_ID]/hiker

# 3. Deploy
gcloud run deploy hiker \
  --image gcr.io/[PROJECT_ID]/hiker \
  --platform managed \
  --region europe-west1 \
  --set-env-vars GOOGLE_CLOUD_PROJECT=[PROJECT_ID],ADMIN_TOKEN=[YOUR_TOKEN]
```

החלף:
- `[PROJECT_ID]` - ה-ID של הפרויקט שלך
- `[YOUR_TOKEN]` - ה-ADMIN_TOKEN שלך

---

## 💡 שימוש

### כניסה לממשק
1. גש ל-URL של האפליקציה: `https://your-app.run.app/admin`
2. הזן את ה-`ADMIN_TOKEN` שלך
3. לחץ "התחבר"

### עמוד Dashboard
- **סטטיסטיקות**: צפה בסטטיסטיקות כלליות
- **גרפים**: מגמות לאורך זמן
- **שעות שיא**: מתי המערכת הכי פעילה

### עמוד משתמשים
- **חיפוש**: הקלד שם או טלפון בשדה החיפוש
- **מיון**: לחץ על כותרת עמודה למיון
- **🆕 צפייה בפרטים**: לחץ על שורה לפתיחת Modal עם:
  - היסטוריית צ'אט (100 הודעות אחרונות)
  - פרטי משתמש מלאים
- **🆕 מחיקת משתמש**: לחץ על 🗑️ → אשר
- **ייצוא**: לחץ "ייצוא CSV" להורדת כל הנתונים

### עמוד נסיעות
- **🆕 2 טבלאות**: גלול למעלה/למטה לראות נהגים וטרמפיסטים
- **🆕 צפייה במסלול**: לחץ על נסיעה לפתיחת Modal עם:
  - פרטי הנסיעה
  - מרחק ואזור התאמה
  - קישור ל-Google Maps
- **סינון**: הקלד יעד בשדה החיפוש
- **ייצוא**: כל טבלה עם כפתור ייצוא משלה

### עמוד שגיאות
- **צפייה בשגיאות**: כל השגיאות עם stack trace
- **סינון**: לפי חומרה (ERROR, WARNING, INFO)
- **ניקוי**: מחק לוגים ישנים

---

## 📡 API Documentation

### Authentication
כל ה-endpoints דורשים header:
```
X-Admin-Token: your_secret_token
```

### Endpoints

#### Statistics
```
GET /a/stats/overview
GET /a/stats/trends?days=30
GET /a/stats/peak-hours
```

#### Users
```
GET /a/users?search=...&sort_by=...&order=...
GET /a/users/{phone_number}/details
GET /a/users/{phone_number}/history?limit=100
DELETE /a/users/{phone_number}
GET /a/users/export/csv
```

#### Rides
```
GET /a/rides/active?destination=...
DELETE /a/rides/{phone_number}/{ride_id}?ride_type=...
GET /a/rides/export/csv?ride_type=driver|hitchhiker
```

#### Logs
```
GET /a/logs/errors?severity=...&start_date=...&end_date=...
GET /a/logs/activity?...
DELETE /a/logs/cleanup?days=90
```

---

## 🐛 פתרון בעיות

### בעיה: "401 Unauthorized"
**פתרון**: 
- ודא ש-`ADMIN_TOKEN` נכון
- נקה את ה-localStorage ונסה שוב
- בדוק ש-`ADMIN_TOKEN` מוגדר ב-Environment Variables

### בעיה: "404 על קבצי assets"
**פתרון**:
```bash
cd frontend
npm run build
cd ..
# Deploy מחדש
```

### בעיה: "Modal לא נפתח"
**פתרון**:
- פתח Console (F12) ובדוק שגיאות
- ודא ש-React Query עובד
- רענן את הדף

### בעיה: "לא רואה נתונים"
**פתרון**:
- ודא ש-Backend רץ
- בדוק את הלוגים ב-Cloud Run Console
- ודא שיש נתונים ב-Firestore

### בעיה: "מחיקת משתמש לא עובדת"
**פתרון**:
- ודא ש-`ADMIN_TOKEN` תקין
- בדוק שהמשתמש קיים
- בדוק את הלוגים

---

## 📊 מבנה הפרויקט

```
Hiker/
├── main.py                 # FastAPI main app
├── admin.py                # Admin routes
├── config.py               # Configuration (MAX_CHAT_HISTORY=100)
├── database/
│   ├── firestore_client.py
│   ├── analytics.py        # Statistics functions
│   └── logging.py          # Logging functions
├── middleware/
│   └── logging_middleware.py
├── frontend/
│   ├── package.json
│   ├── vite.config.js      # base: '/admin/'
│   ├── src/
│   │   ├── main.jsx
│   │   ├── App.jsx
│   │   ├── api/
│   │   │   └── client.js   # API client
│   │   ├── components/
│   │   │   ├── Layout/
│   │   │   ├── Dashboard/
│   │   │   ├── Users/
│   │   │   │   └── UserDetailsModal.jsx  # 🆕
│   │   │   └── Rides/
│   │   │       └── RideMapModal.jsx      # 🆕
│   │   └── pages/
│   │       ├── DashboardPage.jsx
│   │       ├── UsersPage.jsx             # 🔄 עודכן
│   │       ├── RidesPage.jsx             # 🔄 עודכן
│   │       └── ErrorsPage.jsx
│   └── dist/               # Built files
├── Dockerfile              # Multi-stage build
├── cloudbuild.yaml         # Cloud Build config
└── docs/
    ├── ADMIN_FEATURES_UPDATE.md
    ├── UPDATE_GUIDE.md
    ├── FEATURES_SUMMARY.md
    ├── CHANGELOG.md
    └── ADMIN_README.md     # זה הקובץ
```

---

## 🔐 אבטחה

### Best Practices:
- ✅ שמור את `ADMIN_TOKEN` בסוד
- ✅ אל תשתף את ה-Token
- ✅ החלף את ה-Token מעת לעת
- ✅ השתמש ב-HTTPS בלבד
- ✅ הגבל גישה ל-IP ספציפי (אופציונלי)

### CORS:
המערכת מוגדרת ל-`allow_origins=["*"]` לפיתוח.  
**בייצור**: שנה ל-domain ספציפי ב-`main.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-domain.com"],
    ...
)
```

---

## 📈 ביצועים

### Caching:
- React Query מבצע caching אוטומטי
- Refetch כל 30 שניות (Dashboard)
- Refetch on window focus

### Database:
- Firestore indexes אוטומטיים
- Pagination ב-API (limit=100)
- Efficient queries עם filters

### Frontend:
- Lazy loading של Modals
- Code splitting עם Vite
- Tailwind CSS purging

---

## 🆕 מה חדש בגרסה 2.1.0?

1. **היסטוריית צ'אט מורחבת** - 100 הודעות במקום 20
2. **Modal משתמש** - לחיצה על משתמש מציגה פרטים והיסטוריה
3. **Modal נסיעה** - לחיצה על נסיעה מציגה מסלול ומפה
4. **מחיקת משתמש** - כפתור 🗑️ בטבלת המשתמשים
5. **נהגים וטרמפיסטים יחד** - 2 טבלאות באותו מסך

ראה [CHANGELOG.md](CHANGELOG.md) לפרטים מלאים.

---

## 📞 תמיכה

### יש בעיה?
1. בדוק את [פתרון בעיות](#פתרון-בעיות)
2. בדוק את הלוגים ב-Cloud Run Console
3. בדוק את Console של הדפדפן (F12)

### רוצה להוסיף תכונה?
1. פתח Issue ב-GitHub
2. תאר את התכונה המבוקשת
3. נשקול להוסיף בגרסה הבאה

---

## 📝 רישיון

© 2026 Hiker Team. All rights reserved.

---

**גרסה**: 2.1.0  
**תאריך**: 3 ינואר 2026  
**מפתחים**: צוות Hiker

