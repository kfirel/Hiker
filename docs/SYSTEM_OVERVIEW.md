# מערכת טרמפים גברעם - סקירת מערכת

## ארכיטקטורה

המערכת בנויה על 3 שכבות עיקריות:

### 1. **Intent Detector** (Safety Net)
- זיהוי כוונות ברורות בקוד
- מטפל ב-80%+ מהמקרים הפשוטים
- כפיית function calls מבלי לפנות ל-AI
- קובץ: `services/intent_detector.py`

### 2. **AI Service** (Gemini 2.0 Flash)
- טיפול בשיחות מורכבות
- חילוץ מידע מהודעות מפוזרות
- קריאות לפונקציות כשיש מספיק מידע
- קובץ: `services/ai_service.py`

### 3. **Matching Engine** (מנוע התאמות)
- **חיפוש דו-כיווני:**
  - נהג מוסיף נסיעה → חיפוש טרמפיסטים מתאימים
  - טרמפיסט מוסיף בקשה → חיפוש נהגים מתאימים
- התאמה חכמה: יעד (fuzzy 80%), יום, שעה (±30 דק')
- קובץ: `services/matching_service.py`

## זרימת הודעה

```
הודעה מ-WhatsApp
    ↓
בדיקת משתמש חדש? → הודעת ברוכים הבאים
    ↓
פקודת אדמין? → Admin Handler
    ↓
תגובת אישור? → Approval Service
    ↓
Intent Detector (Safety Net)
    ├─ כוונה ברורה? → Function Handler
    └─ לא ברור? → AI Service → Function Handler
                      ↓
               Matching Engine
                      ↓
            התראות לטרמפיסטים/נהגים
```

## קבצים חדשים

| קובץ | תפקיד |
|------|-------|
| `config.py` | משתני סביבה וקבועים |
| `services/intent_detector.py` | זיהוי כוונות ברורות |
| `services/matching_service.py` | מנוע התאמות דו-כיווני |
| `services/function_handlers/__init__.py` | טיפול בפונקציות AI |
| `services/ai_service.py` | שירות Gemini 2.0 |
| `services/approval_service.py` | תשתית לעתיד |
| `services/__init__.py` | ייצוא מרכזי |
| `webhooks/__init__.py` | ייצוא webhook handler |

## דוגמאות שימוש

### נהג מציע נסיעה:
```
משתמש: "אני נוסע לתל אביב בימים א-ה בשעה 8"
→ Intent Detector מזהה
→ שמירה ב-DB
→ חיפוש טרמפיסטים שמחפשים ת"א בימים א-ה בשעה 8
→ שליחת הודעות לטרמפיסטים: "נמצא נהג! [פרטים]"
```

### טרמפיסט מחפש:
```
משתמש: "מחפש טרמפ לירושלים מחר בשעה 9"
→ Intent Detector מזהה
→ שמירה ב-DB
→ חיפוש נהגים שנוסעים לירושלים ביום מחר בשעה 9
→ שליחת הודעה למשתמש: "נמצא נהג! [פרטים]"
```

## התקנה והרצה

```bash
# התקנת dependencies
pip install -r requirements.txt

# הרצה מקומית
python main.py

# Deploy ל-Cloud Run
./deploy.sh
```

## משתני סביבה נדרשים

```env
WHATSAPP_TOKEN=your_token
WHATSAPP_PHONE_NUMBER_ID=your_phone_id
GEMINI_API_KEY=your_gemini_key
GOOGLE_CLOUD_PROJECT=your_project
VERIFY_TOKEN=your_verify_token
```

## תכונות עיקריות

✅ **אמינות מקסימלית** - הקוד אחראי על כל הלוגיקה הקריטית  
✅ **התאמות דו-כיווניות** - נהג ↔ טרמפיסט  
✅ **Safety Net חזק** - Intent Detector לכוונות ברורות  
✅ **שליחה אוטומטית** - התראות מיידיות על התאמות  
✅ **AI כעוזר** - רק לשיחות מורכבות  

## עדכונים עתידיים

- [ ] אישור ידני לנהגים (approval_service)
- [ ] התראות מתקדמות (SMS/Email)
- [ ] ניהול מספרי טלפון חוזרים
- [ ] דירוג משתמשים



