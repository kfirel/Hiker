# 🚀 הרצה מקומית - מדריך פשוט

## קצר וקולע:

```bash
./dev.sh
```

**זהו!** 🎉

הסקריפט יעשה הכל בשבילך:
- ✅ ייצור virtual environment (אם צריך)
- ✅ יתקין dependencies
- ✅ ייצור .env template (אם צריך)
- ✅ יריץ Backend (port 8080)
- ✅ יריץ Frontend (port 3000)
- ✅ יפתח דפדפן אוטומטית

---

## 📍 URLs:

| שירות | כתובת |
|-------|--------|
| **Admin UI** | http://localhost:3000/admin |
| **Backend API** | http://localhost:8080 |
| **API Docs** | http://localhost:8080/docs |

---

## ⚙️ הגדרות ראשוניות (פעם אחת):

### 1. וודא שיש לך:
- Python 3.11+
- Node.js 18+

### 2. ערוך את `.env`:
```bash
# הסקריפט יוצר .env template בשבילך
# פשוט ערוך את הערכים:

GOOGLE_CLOUD_PROJECT=your-project-id
GEMINI_API_KEY=your-gemini-key
ADMIN_TOKEN=local-dev-token-123
```

---

## 🔧 פקודות שימושיות:

### הרצה מלאה:
```bash
./dev.sh
```

### הרצה ידנית (Backend בלבד):
```bash
source venv/bin/activate
python main.py
```

### הרצה ידנית (Frontend בלבד):
```bash
cd frontend
npm run dev
```

### צפייה בלוגים:
```bash
# Backend logs
tail -f logs/backend.log

# Frontend logs
tail -f logs/frontend.log
```

### עצירת כל השירותים:
לחץ `Ctrl+C` בטרמינל שבו רץ `dev.sh`

---

## 🐛 Debug טיפים:

### שינוי בBackend:
1. שמור את הקובץ
2. הbackend יעשה reload אוטומטית (uvicorn hot reload)
3. רענן דפדפן

### שינוי בFrontend:
1. שמור את הקובץ
2. Vite יעשה hot reload אוטומטית
3. הדפדפן יתעדכן מיד!

### בעיות נפוצות:

#### Port already in use:
```bash
# הרוג תהליכים על port 8080
lsof -ti:8080 | xargs kill -9

# או על port 3000
lsof -ti:3000 | xargs kill -9

# הסקריפט עושה את זה אוטומטית
```

#### Dependencies לא מעודכנים:
```bash
# Python
pip install -r requirements.txt

# Frontend
cd frontend && npm install
```

#### .env לא מוגדר:
```bash
# הסקריפט יוצר template
# ערוך את .env עם הערכים שלך
```

---

## 📁 מבנה הפרויקט:

```
Hiker/
├── dev.sh              # 🚀 סקריפט ההרצה
├── main.py             # Backend entry point
├── admin.py            # Admin routes
├── config.py           # Configuration
├── .env                # Environment variables (אתה יוצר)
├── frontend/           # React app
│   ├── src/
│   ├── package.json
│   └── vite.config.js
├── logs/               # Development logs
│   ├── backend.log
│   └── frontend.log
└── venv/               # Python virtual environment
```

---

## 🎯 Workflow מומלץ:

### 1. התחלת יום:
```bash
./dev.sh
```

### 2. פיתוח:
- ערוך קבצים ב-`frontend/src/` או Python files
- הכל יתעדכן אוטומטית
- בדוק ב-browser: http://localhost:3000/admin

### 3. בדיקת API:
- פתח http://localhost:8080/docs
- נסה endpoints ישירות

### 4. סיום יום:
- `Ctrl+C` לעצירת dev.sh
- commit + push

---

## 🚢 Deploy לענן:

כשמוכן ל-production:

```bash
git add .
git commit -m "your message"
git push

# Cloud Build יעשה את השאר אוטומטית!
```

---

## 💡 עצות:

### Hot Reload עובד!
- שמור קובץ → רענון אוטומטי
- לא צריך לעצור/להתחיל מחדש

### Sandbox לבדיקות:
- פתח http://localhost:3000/admin/sandbox
- 4 משתמשי טסט מוכנים לשימוש
- בחר Test environment

### Logs:
- `logs/backend.log` - כל מה שקורה בשרת
- `logs/frontend.log` - Vite output
- `tail -f logs/*.log` - צפה בשניהם

### Environment:
- מקומי = Test environment by default
- Production = רק בענן

---

## ❓ שאלות נפוצות:

**Q: צריך Docker?**
A: לא! הכל רץ ישירות על המק.

**Q: צריך npm install כל פעם?**
A: לא, רק בפעם הראשונה. הסקריפט בודק אוטומטית.

**Q: איך לעצור?**
A: Ctrl+C בטרמינל של dev.sh

**Q: איך לראות שגיאות?**
A: `tail -f logs/backend.log` או פתח Console בדפדפן (F12)

**Q: Frontend לא מתחבר לBackend?**
A: ודא שbackend רץ על port 8080. Vite proxy מטפל בשאר.

---

**זהו! קל ופשוט** ✨

פשוט תריץ `./dev.sh` ותתחיל לעבוד!



