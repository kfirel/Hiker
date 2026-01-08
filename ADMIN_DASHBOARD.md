# ממשק ניהול למערכת הטרמפים של גברעם 🚗

מערכת ניהול מלאה עם React Dashboard ו-FastAPI Backend למעקב אחר המערכת, משתמשים, נסיעות, ושגיאות.

## 📋 תוכן עניינים

- [תכונות](#תכונות)
- [ארכיטקטורה](#ארכיטקטורה)
- [התקנה](#התקנה)
- [הרצה מקומית](#הרצה-מקומית)
- [Deploy לענן](#deploy-לענן)
- [API Documentation](#api-documentation)
- [Screenshots](#screenshots)

## ✨ תכונות

### דשבורד ראשי
- 📊 סטטיסטיקות כלליות (משתמשים, נסיעות, התאמות)
- 📈 גרפים של משתמשים חדשים ונסיעות (30 ימים)
- 🎯 טבלת יעדים פופולריים
- 🔄 עדכון אוטומטי כל 30 שניות

### ניהול משתמשים
- 👥 רשימת כל המשתמשים
- 🔍 חיפוש לפי טלפון או שם
- 📊 מיון לפי תאריך, שם, או פעילות
- 📥 ייצוא ל-CSV
- 📱 צפייה בפרטים מלאים + היסטוריית צ'אט

### ניהול נסיעות
- 🚗 טאב נהגים - כל הנסיעות הפעילות
- 🎒 טאב טרמפיסטים - כל הבקשות הפעילות
- 🔍 סינון לפי יעד
- 📥 ייצוא ל-CSV
- 🗑️ מחיקת נסיעות (ניהול)

### לוגים ושגיאות
- ⚠️ מעקב אחר שגיאות המערכת
- 📝 לוג פעילות כללי
- 🎨 צבעים לפי רמת חומרה (error, warning, info)
- 📋 Stack trace מלא
- 🔍 סינון לפי רמת חומרה ותאריך

## 🏗️ ארכיטקטורה

```
┌─────────────────┐
│  Admin Browser  │
└────────┬────────┘
         │ HTTPS + Token
         ↓
┌─────────────────────────┐
│   Google Cloud Run      │
│  ┌──────────────────┐   │
│  │  React Dashboard │   │
│  │  (Static Files)  │   │
│  └──────────────────┘   │
│  ┌──────────────────┐   │
│  │  FastAPI Backend │   │
│  │  - Admin API     │   │
│  │  - Webhook API   │   │
│  │  - WhatsApp Bot  │   │
│  └──────────────────┘   │
└───────────┬─────────────┘
            │
            ↓
    ┌───────────────┐
    │   Firestore   │
    │   Database    │
    └───────────────┘
```

## 📦 התקנה

### דרישות
- Python 3.11+
- Node.js 18+ (לפיתוח Frontend)
- Google Cloud Project עם Firestore
- ADMIN_TOKEN (לאימות)

### 1. Clone והגדרת Backend

```bash
cd /path/to/Hiker

# התקנת dependencies של Python
pip install -r requirements.txt

# הגדרת משתני סביבה
cp .env.example .env
# ערוך .env והוסף:
# - ADMIN_TOKEN=your-secret-token
# - GOOGLE_CLOUD_PROJECT=your-project-id
# - WHATSAPP_TOKEN=...
# - VERIFY_TOKEN=...
# - GEMINI_API_KEY=...
```

### 2. התקנת Frontend (אופציונלי - לפיתוח)

```bash
cd frontend
npm install
```

## 🚀 הרצה מקומית

### אופציה 1: Backend בלבד (ללא Dashboard)
```bash
python main.py
```
הגישה ל-API: http://localhost:8080

### אופציה 2: Backend + Frontend Dev Mode

Terminal 1 - Backend:
```bash
python main.py
```

Terminal 2 - Frontend:
```bash
cd frontend
npm run dev
```
גישה ל-Dashboard: http://localhost:3000/admin

### אופציה 3: Production Build מקומי

```bash
# Build frontend
cd frontend
npm run build
cd ..

# Run backend (מגיש גם את הדשבורד)
python main.py
```
גישה ל-Dashboard: http://localhost:8080/admin

## ☁️ Deploy לענן (Google Cloud Run)

### דרך 1: סקריפט אוטומטי
```bash
./deploy.sh
```

### דרך 2: ידני
```bash
# Set project
export PROJECT_ID=your-project-id
export REGION=us-central1

# Build and push
gcloud builds submit --tag gcr.io/$PROJECT_ID/hiker-bot

# Deploy
gcloud run deploy hiker-bot \
  --image gcr.io/$PROJECT_ID/hiker-bot \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=$PROJECT_ID,ADMIN_TOKEN=your-token" \
  --memory 512Mi
```

לאחר Deploy:
- Bot API: https://your-service-url.run.app
- Admin Dashboard: https://your-service-url.run.app/admin

## 📚 API Documentation

### Authentication
כל ה-API endpoints מחייבים header:
```
X-Admin-Token: your-admin-token
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
GET /a/users?search=&sort_by=last_seen&order=desc&limit=100
GET /a/users/{phone_number}/details
GET /a/users/{phone_number}/history?limit=50
GET /a/users/export/csv
DELETE /a/users/{phone_number}
```

#### Rides
```
GET /a/rides/active?ride_type=&destination=
DELETE /a/rides/{phone_number}/{ride_id}?ride_type=driver
GET /a/rides/export/csv?ride_type=driver
```

#### Logs
```
GET /a/logs/errors?severity=error&limit=100&start_date=&end_date=
GET /a/logs/activity?activity_type=&limit=100
DELETE /a/logs/cleanup?days=90
```

### דוגמת קריאה
```bash
curl -H "X-Admin-Token: your-token" \
     https://your-service.run.app/a/stats/overview
```

## 🔧 פיתוח

### מבנה הפרויקט

```
Hiker/
├── frontend/               # React Dashboard
│   ├── src/
│   │   ├── api/           # API client
│   │   ├── components/    # React components
│   │   ├── pages/         # Page components
│   │   └── styles/        # CSS styles
│   ├── package.json
│   └── vite.config.js
├── database/
│   ├── analytics.py       # Statistics functions
│   ├── logging.py         # Logging functions
│   └── firestore_client.py
├── middleware/
│   └── logging_middleware.py
├── admin.py               # Admin API endpoints
├── main.py                # FastAPI app
├── Dockerfile             # Multi-stage build
└── deploy.sh              # Deploy script
```

### הוספת Endpoint חדש

1. הוסף פונקציה ב-`admin.py`:
```python
@router.get("/my-endpoint")
async def my_endpoint(_: bool = Depends(verify_admin_token)):
    return {"data": "something"}
```

2. הוסף ל-API client (`frontend/src/api/client.js`):
```javascript
export const myAPI = {
  getData: () => apiClient.get('/my-endpoint'),
};
```

3. השתמש ב-React עם React Query:
```javascript
const { data } = useQuery({
  queryKey: ['myData'],
  queryFn: () => myAPI.getData().then(res => res.data),
});
```

## 🎨 עיצוב

הדשבורד משתמש ב-Tailwind CSS עם:
- **צבעים**: כחול (#3B82F6), ירוק (#10B981), אדום (#EF4444)
- **פונט**: Heebo (תומך עברית מלא)
- **כיוון**: RTL (ימין לשמאל)
- **Responsive**: תומך במובייל וטאבלט

## 🐛 Troubleshooting

### הדשבורד לא מופיע
```bash
# בדוק שה-frontend נבנה
ls frontend/dist

# אם לא - בנה אותו
cd frontend && npm run build
```

### שגיאת אימות
```bash
# בדוק שה-token נכון
echo $ADMIN_TOKEN

# בדוק ב-localStorage של הדפדפן
localStorage.getItem('admin_token')
```

### CORS Errors
ודא ש-CORS מוגדר נכון ב-`main.py`

### Database Connection
בדוק שמשתני הסביבה של Firestore מוגדרים:
```bash
echo $GOOGLE_CLOUD_PROJECT
```

## 📝 Changelog

### Version 1.0.0 (2026-01-02)
- ✨ דשבורד ראשי עם סטטיסטיקות וגרפים
- 👥 ניהול משתמשים מלא
- 🚗 ניהול נסיעות ונהגים
- ⚠️ מערכת לוגים ושגיאות
- 📦 Docker multi-stage build
- 🔐 אימות מאובטח עם token
- 🌐 Deploy אוטומטי ל-Cloud Run

## 👨‍💻 פיתוח

פותח על ידי: כפיר אלגבסי  
תרומה לקהילת גברעם

## 📄 License

שימוש פנימי עבור קהילת גברעם בלבד.



