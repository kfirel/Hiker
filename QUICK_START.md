# התחלה מהירה - מערכת טרמפים גברעם

## התקנה ⚡

### 1. התקנת Dependencies
```bash
pip install -r requirements.txt
```

### 2. הגדרת משתני סביבה

צור קובץ `.env` בתיקיית הפרויקט:

```env
# WhatsApp
WHATSAPP_TOKEN=your_whatsapp_token
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
VERIFY_TOKEN=your_verify_token

# Gemini AI
GEMINI_API_KEY=your_gemini_api_key

# Firestore
GOOGLE_CLOUD_PROJECT=your_project_id

# Optional
PORT=8080
```

### 3. הרצה מקומית
```bash
python main.py
```

השרת יעלה על `http://localhost:8080`

## בדיקה מהירה 🧪

בדוק את Intent Detector:
```bash
python3 test_intent_detector.py
```

## שימוש דרך WhatsApp 📱

### משתמש חדש
שלח הודעה ראשונה → תקבל ברוכים הבאים

### טרמפיסט מחפש נסיעה
```
"מחפש טרמפ לתל אביב מחר בשעה 9"
"מבקש טרמפ למחר בבוקר לאשקלון"
"צריך נסיעה לירושלים היום בערב"
```
→ המערכת תשמור ותחפש נהגים מתאימים

💡 **תמיכה בביטויי זמן:** בבוקר (08:00), אחה״צ (14:00), בערב (18:00), בלילה (20:00)

### נהג מציע נסיעה קבועה
```
"אני נוסע לירושלים בימים א-ה בשעה 8"
```
→ המערכת תשמור ותחפש טרמפיסטים מתאימים

### צפייה ברשומות שלך
```
"תראה לי מה יש לי"
```

## תכונות מרכזיות ✨

🎯 **זיהוי אוטומטי** - המערכת מזהה אם אתה נהג או טרמפיסט  
🔄 **התאמות דו-כיווניות** - נהג ← → טרמפיסט  
⚡ **מיידי** - התראות אוטומטיות כשנמצאה התאמה  
🛡️ **אמין** - Safety Net חזק + AI לגיבוי  

## פקודות אדמין 🔧

אם מוגדר ב-`ADMIN_PHONE_NUMBERS`:

```
/a/help - עזרה
/a/c/NEW_NUMBER - שינוי מספר טלפון
/a/d - מחיקת משתמש
/a/r - איפוס משתמש
```

## Deploy ל-Cloud Run ☁️

```bash
./deploy.sh
```

## בעיות נפוצות 🔍

### "AI לא זמין"
→ בדוק שיש `GEMINI_API_KEY` ב-.env

### "Database לא זמין"
→ בדוק `GOOGLE_CLOUD_PROJECT` ו-Firestore credentials

### "WhatsApp לא מגיב"
→ בדוק `WHATSAPP_TOKEN` ו-`WHATSAPP_PHONE_NUMBER_ID`

## מבנה הפרויקט 📁

```
Hiker/
├── config.py                    # משתני סביבה
├── main.py                      # FastAPI app
├── database/                    # Firestore operations
├── services/
│   ├── intent_detector.py      # Safety Net
│   ├── matching_service.py     # מנוע התאמות
│   ├── function_handlers/      # טיפול בפונקציות
│   ├── ai_service.py           # Gemini 2.0
│   └── approval_service.py     # תשתית לעתיד
├── whatsapp/
│   ├── whatsapp_handler.py     # טיפול בהודעות
│   └── whatsapp_service.py     # שליחת הודעות
└── webhooks/                    # Webhook handlers
```

## תמיכה 💬

- קרא `IMPLEMENTATION_SUMMARY.md` לפרטים מלאים
- קרא `docs/SYSTEM_OVERVIEW.md` לארכיטקטורה
- הרץ `test_intent_detector.py` לבדיקות

---

**בהצלחה! 🚗**

