# 📁 מבנה הפרויקט - Hiker

מסמך זה מתעד את המבנה המאורגן של פרויקט Hiker לאחר סידור מחדש.

---

## 🎯 עקרונות הארגון

1. **הפרדה ברורה** - קוד, תיעוד, בדיקות, נתונים
2. **נגישות** - קל למצוא כל דבר
3. **תחזוקה** - README בכל תיקייה חשובה
4. **נקיון** - קבצים זמניים מוסתרים או במקומות ייעודיים

---

## 📂 מבנה כללי

```
Hiker/
├── 📂 data/                    # נתונים
├── 📂 database/                # Database client
├── 📂 docs/                    # תיעוד
├── 📂 logs/                    # לוגים
├── 📂 models/                  # מודלים
├── 📂 scripts/                 # סקריפטים
├── 📂 services/                # לוגיקה עסקית
├── 📂 tests/                   # בדיקות
├── 📂 utils/                   # כלי עזר
├── 📂 webhooks/                # Webhook handlers
├── 📂 whatsapp/                # WhatsApp integration
├── 📄 .gitignore               # Git ignore rules
├── 📄 config.py                # הגדרות
├── 📄 main.py                  # Entry point
├── 📄 README.md                # מסמך ראשי
└── 📄 requirements.txt         # תלויות
```

---

## 📁 תיאור תיקיות

### 1. **data/** 📊
נתונים סטטיים של המערכת

```
data/
├── city.geojson          # 2,415 ישובים בישראל
└── README.md             # תיעוד הנתונים
```

**תפקיד:**
- אחסון מסדי נתונים מקומיים
- קבצי GeoJSON, CSV, JSON
- נתונים שלא משתנים בזמן ריצה

**גישה:**
```python
project_root = os.path.dirname(current_dir)
geojson_path = os.path.join(project_root, 'data', 'city.geojson')
```

---

### 2. **database/** 💾
Firestore database client

```
database/
├── __init__.py
└── firestore_client.py   # Firestore operations
```

**תפקיד:**
- חיבור ל-Firestore
- CRUD operations
- Query helpers

---

### 3. **docs/** 📚
תיעוד מלא של הפרויקט

```
docs/
├── README.md                      # מדריך לתיעוד
├── SYSTEM_OVERVIEW.md             # מבט על
└── implementation/                # תיעוד טכני
    ├── GEOCODING_SETUP.md         # Geocoding
    ├── GEOJSON_IMPLEMENTATION.md  # GeoJSON
    ├── IMPLEMENTATION_SUMMARY.md  # סיכום
    ├── TESTING_GUIDE.md          # בדיקות
    └── QUICK_START.md            # התחלה מהירה
```

**תפקיד:**
- תיעוד ארכיטקטורה
- מדריכי שימוש
- תיעוד טכני מפורט

**כללים:**
- כל תיעוד טכני ב-`docs/implementation/`
- מסמכים כלליים ב-`docs/`
- README בכל תיקייה

---

### 4. **logs/** 📝
לוגים ותוצאות ריצה

```
logs/
├── gevaram_full_test.log  # לוג בדיקות
├── gevaram_test_results.txt
└── *.log                  # כל הלוגים
```

**תפקיד:**
- אחסון לוגים
- תוצאות בדיקות טקסטואליות
- ניתוח בעיות

**הערה:** התיקייה הזאת ב-`.gitignore`

---

### 5. **models/** 🗃️
מודלי נתונים

```
models/
├── __init__.py
└── user.py               # User model
```

**תפקיד:**
- הגדרת מבני נתונים
- Validation
- Serialization

---

### 6. **scripts/** 🛠️
סקריפטים עזר

```
scripts/
├── README.md             # תיעוד סקריפטים
├── deploy.sh             # Deployment
├── test_logs.sh          # בדיקת logs
└── test_webhook.sh       # בדיקת webhooks
```

**תפקיד:**
- Deployment
- תחזוקה
- בדיקות ידניות
- כלי עזר למפתחים

**שימוש:**
```bash
chmod +x scripts/<script>.sh
./scripts/<script>.sh
```

---

### 7. **services/** ⚙️
לוגיקה עסקית

```
services/
├── __init__.py
├── ai_service.py              # Gemini AI
├── matching_service.py        # התאמות
├── route_service.py           # מסלולים & geocoding
└── function_handlers/         # טיפול בפעולות
    └── __init__.py
```

**תפקיד:**
- אלגוריתמים עיקריים
- עיבוד נתונים
- אינטגרציות חיצוניות

**עקרון:** כל service הוא עצמאי ויכול לעבוד לבד.

---

### 8. **tests/** 🧪
בדיקות המערכת

```
tests/
├── README.md                  # מדריך בדיקות
├── outputs/                   # תוצאות בדיקות
│   ├── gevaram_1_tel_aviv.html
│   ├── gevaram_2_jerusalem.html
│   └── *.html                # כל המפות
├── test_geojson_simple.py    # בדיקת GeoJSON
├── test_gevaram_final.py     # בדיקות מגברעם
├── test_route_simple.py      # בדיקות route
├── test_route_visual.py      # מפות ויזואליות
└── test_*.py                 # בדיקות נוספות
```

**תפקיד:**
- בדיקות unit
- בדיקות integration
- בדיקות ויזואליות
- תוצאות HTML

**הרצה:**
```bash
python tests/test_<name>.py
```

---

### 9. **utils/** 🔧
כלי עזר כלליים

```
utils/
├── __init__.py
└── timezone_utils.py     # Timezone helpers
```

**תפקיד:**
- פונקציות עזר
- קוד משותף
- כלים כלליים

---

### 10. **webhooks/** 🔗
Webhook handlers

```
webhooks/
└── __init__.py           # Webhook logic
```

**תפקיד:**
- קבלת webhooks
- Verification
- Routing

---

### 11. **whatsapp/** 💬
WhatsApp integration

```
whatsapp/
├── __init__.py
├── whatsapp_handler.py   # Message handling
└── whatsapp_service.py   # API calls
```

**תפקיד:**
- שליחת הודעות
- קבלת הודעות
- פורמט הודעות

---

## 📄 קבצים ראשיים

### config.py ⚙️
הגדרות המערכת:
- API keys
- Constants
- Configuration

### main.py 🚀
Entry point:
- Flask app
- Routes
- Server startup

### requirements.txt 📦
תלויות Python:
```
Flask
google-genai
google-cloud-firestore
geopy
folium
python-dotenv
requests
```

### .gitignore 🚫
קבצים להתעלם:
- `__pycache__/`
- `.env`
- `logs/`
- `tests/outputs/*.html`

---

## 🔄 שינויים שבוצעו

### לפני הסידור:

```
❌ קבצי בדיקה בשורש
❌ HTML outputs בשורש
❌ תיעוד מפוזר
❌ city.geojson בשורש
❌ סקריפטים בשורש
❌ לוגים בשורש
```

### אחרי הסידור:

```
✅ tests/ - כל הבדיקות
✅ tests/outputs/ - תוצאות HTML
✅ docs/implementation/ - תיעוד
✅ data/ - city.geojson
✅ scripts/ - סקריפטים
✅ logs/ - לוגים
```

---

## 📋 Checklist לתיקייה חדשה

כשיוצרים תיקייה חדשה:

- [ ] יצירת `README.md` עם תיאור
- [ ] הוספה ל-`.gitignore` אם נדרש
- [ ] עדכון `PROJECT_STRUCTURE.md`
- [ ] עדכון `README.md` הראשי
- [ ] בדיקת imports בקוד

---

## 🎯 כללי ארגון

### DO ✅

1. **קבצי קוד** → תיקיות לפי תפקיד (`services/`, `models/`, etc.)
2. **בדיקות** → `tests/`
3. **תיעוד** → `docs/`
4. **נתונים** → `data/`
5. **תוצאות** → `tests/outputs/` או `logs/`
6. **README** → בכל תיקייה חשובה

### DON'T ❌

1. ❌ קבצי בדיקה בשורש
2. ❌ HTML outputs בשורש
3. ❌ תיעוד מפוזר
4. ❌ לוגים בשורש
5. ❌ קבצים זמניים ב-Git

---

## 🔍 איך למצוא דברים?

| מחפש... | איפה? |
|---------|-------|
| **קוד עיקרי** | `services/` |
| **בדיקות** | `tests/` |
| **תיעוד** | `docs/` |
| **נתונים** | `data/` |
| **סקריפטים** | `scripts/` |
| **הגדרות** | `config.py` |
| **Entry point** | `main.py` |
| **תלויות** | `requirements.txt` |

---

## 📊 סטטיסטיקות

- **תיקיות ראשיות:** 11
- **קבצי README:** 6
- **קבצי בדיקה:** 7
- **מסמכי תיעוד:** 6
- **סקריפטים:** 3

---

## 🎉 יתרונות המבנה החדש

1. ✅ **נקי** - קל למצוא דברים
2. ✅ **מסודר** - כל דבר במקומו
3. ✅ **מתועד** - README בכל מקום
4. ✅ **ניתן לתחזוקה** - קל להוסיף דברים חדשים
5. ✅ **מקצועי** - נראה טוב ב-GitHub

---

## 📞 לעזרה

- 📖 תיעוד: [`docs/README.md`](docs/README.md)
- 🧪 בדיקות: [`tests/README.md`](tests/README.md)
- 📊 נתונים: [`data/README.md`](data/README.md)
- 🛠️ סקריפטים: [`scripts/README.md`](scripts/README.md)

---

**מבנה מסודר = קוד מסודר = פרויקט מצליח! 🚀**



