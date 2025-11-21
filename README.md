# 🚗 Hiker - WhatsApp Hitchhiking Bot

<div align="center">

![Python](https://img.shields.io/badge/python-3.10-blue.svg)
![Flask](https://img.shields.io/badge/flask-latest-green.svg)
![WhatsApp](https://img.shields.io/badge/WhatsApp-Cloud%20API-25D366.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

**בוט חכם לטרמפים בישוב גברעם** 🇮🇱

מחבר בין טרמפיסטים לנהגים מגברעם באמצעות WhatsApp

[תיעוד](#-תיעוד) • [התקנה](#-התקנה-מהירה) • [תכונות](#-תכונות) • [מבנה](#-מבנה-הפרויקט)

</div>

---

## 📖 אודות

**Hiker** הוא בוט WhatsApp חכם המאפשר לטרמפיסטים ונהגים מישוב גברעם להתחבר בקלות ובמהירות. הבוט משתמש ב-WhatsApp Cloud API של Meta ומציע חוויית משתמש אינטואיטיבית עם כפתורים אינטראקטיביים ותהליך רישום חכם.

### למה Hiker?

✅ **קל לשימוש** - ממשק אינטואיטיבי עם כפתורים אינטראקטיביים  
✅ **חכם** - אימות אוטומטי של ישובים, ימים ושעות  
✅ **גמיש** - תומך בטרמפיסטים, נהגים, ושניהם  
✅ **מאובטח** - שימוש ב-WhatsApp Cloud API הרשמי  
✅ **בעברית** - ממשק מלא בעברית עם הומור וידידותיות  

---

## 🎯 תכונות

### לטרמפיסטים 🚶
- 🎯 בקשת טרמפ מיידית או מתוכננת
- 📍 הגדרת יעדים מועדפים
- ⏰ בחירת טווח שעות גמיש
- 🔔 התראות על נהגים מתאימים

### לנהגים 🚗
- 🗓️ הגדרת שגרת נסיעה קבועה
- 📢 פרסום טרמפים באופן אקטיבי
- 🎯 בחירת העדפות התראות חכמות
- 📊 ניהול מסלולים מרובים

### תכונות מתקדמות ✨
- 🔘 כפתורים אינטראקטיביים לכל פעולה
- ✅ אימות אוטומטי של ישובים (100+ ישובים)
- 🤖 הצעות חכמות לישובים דומים עם כפתורים
- 📅 אימות פורמטים (ימים, שעות, טווחי זמן)
- 💬 מסך עזרה מובנה
- 🔄 כפתור restart בכל אינטראקציה
- 🌐 תמיכה בפקודות מקוצרות (חזור, חדש, תפריט, עזרה)

---

## 🚀 התקנה מהירה

### דרישות מקדימות

- Python 3.10+
- חשבון Meta Developer (חינם)
- חשבון WhatsApp Business
- חשבון ngrok (לפיתוח מקומי)

### שלב 1: שכפול הפרויקט

```bash
git clone https://github.com/YOUR_USERNAME/Hiker.git
cd Hiker
```

### שלב 2: התקנת תלויות

```bash
# יצירת סביבה וירטואלית
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# או: venv\Scripts\activate  # Windows

# התקנת חבילות
pip install -r requirements.txt
```

### שלב 3: הגדרת משתני סביבה

```bash
# העתקת הקובץ לדוגמה
cp .env.example .env

# ערוך את הקובץ .env והוסף את המפתחות שלך:
nano .env
```

הוסף את הפרטים הבאים:
```env
WHATSAPP_API_TOKEN=your_token_here
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
WEBHOOK_VERIFY_TOKEN=your_custom_verify_token
NGROK_AUTHTOKEN=your_ngrok_token
```

### שלב 4: הרצת הבוט

```bash
# הרצת ngrok (בטרמינל נפרד)
python scripts/start_ngrok.py

# הרצת הבוט (עם auto-reload!)
python src/app.py
```

🎉 **הבוט פועל!** עכשיו הגדר את ה-webhook ב-Meta Developer Console.

💡 **Auto-Reload מופעל כברירת מחדל** - הבוט יטען מחדש אוטומטית כשאתה משנה קוד!

---

## 🏗️ מבנה הפרויקט

```
Hiker/
├── README.md                    # המסמך הזה
├── LICENSE                      # רישיון MIT
├── requirements.txt             # תלויות Python
├── .env.example                 # דוגמה למשתני סביבה
├── .gitignore                   # קבצים להתעלם מהם
│
├── src/                         # 📦 קוד מקור
│   ├── __init__.py
│   ├── app.py                   # אפליקציה ראשית (Flask)
│   ├── config.py                # הגדרות
│   ├── whatsapp_client.py       # לקוח WhatsApp API
│   ├── conversation_engine.py   # מנוע השיחה
│   ├── conversation_flow.json   # הגדרת זרימת השיחה
│   ├── user_database.py         # ניהול משתמשים
│   ├── validation.py            # אימות קלט
│   └── timer_manager.py         # ניהול טיימרים
│
├── tests/                       # 🧪 בדיקות
│   ├── __init__.py
│   ├── test_conversation_flow.py
│   ├── test_interactive_suggestions.py
│   └── debug_test.py
│
├── scripts/                     # 🔧 סקריפטים עזר
│   ├── start_ngrok.py           # הרצת ngrok
│   ├── verify_setup.py          # בדיקת התקנה
│   └── push_to_github.sh        # העלאה לגיטהאב
│
└── docs/                        # 📚 תיעוד
    ├── SETUP_GUIDE.md           # מדריך התקנה מפורט
    ├── ARCHITECTURE.md          # ארכיטקטורת המערכת
    ├── CONVERSATION_FLOW_GUIDE.md
    ├── VALIDATION_GUIDE.md
    ├── INTERACTIVE_BUTTONS_GUIDE.md
    └── QUICK_REFERENCE.md
```

---

## 📚 תיעוד

### מדריכים מפורטים

- 📖 [**docs/SETUP_GUIDE.md**](docs/SETUP_GUIDE.md) - מדריך התקנה מפורט
- 🏗️ [**docs/ARCHITECTURE.md**](docs/ARCHITECTURE.md) - ארכיטקטורת המערכת
- 🔧 [**docs/NGROK_SETUP.md**](docs/NGROK_SETUP.md) - הגדרת ngrok
- 🔗 [**docs/FIND_WEBHOOK_IN_META.md**](docs/FIND_WEBHOOK_IN_META.md) - הגדרת webhook
- 🔘 [**docs/INTERACTIVE_BUTTONS_GUIDE.md**](docs/INTERACTIVE_BUTTONS_GUIDE.md) - כפתורים אינטראקטיביים
- ✅ [**docs/VALIDATION_GUIDE.md**](docs/VALIDATION_GUIDE.md) - מנגנון האימות
- 🔄 [**docs/AUTO_RELOAD_GUIDE.md**](docs/AUTO_RELOAD_GUIDE.md) - Auto-reload בפיתוח
- 💡 [**docs/QUICK_REFERENCE.md**](docs/QUICK_REFERENCE.md) - עזר מהיר

---

## 🎨 דוגמאות שימוש

### זרימת טרמפיסט

```
משתמש: היי
בוט: היי! 👋 ברוכים הבאים להייקר 🚗✨
     מה השם המלא שלך?

משתמש: דני כהן
בוט: באיזה ישוב אתה גר? 🏡

משתמש: תל אביב
בוט: מה אתה?
     [כפתור: 🚗🚶 גיבור על]
     [כפתור: 🚶 טרמפיסט]
     [כפתור: 🚗 נהג]
     [כפתור: 🔄 התחל מחדש]
```

### משתמש רשום חוזר

```
משתמש: שלום
בוט: היי דני! 👋😊
     מה תרצה לעשות היום?
     
     [כפתור: 🚶 מחפש טרמפ]
     [כפתור: 🚗 לתת טרמפ]
     [כפתור: 📅 לתכנן נסיעה]
     [כפתור: 🔄 עדכון שגרה]
     [כפתור: ✏️ עדכון פרטים]
     [כפתור: 💬 עזרה]
```

---

## 🧪 בדיקות

הפרויקט כולל סוויטת בדיקות מקיפה:

```bash
# הרצת בדיקות
python tests/test_conversation_flow.py
python tests/test_interactive_suggestions.py

# בדיקת debug ספציפית
python tests/debug_test.py

# בדיקת התקנה
python scripts/verify_setup.py
```

**כיסוי בדיקות:** 97.9% (47/48 טסטים עוברים)

---

## 🔒 אבטחה

- ✅ כל המפתחות ב-`.env` (לא בגיט!)
- ✅ Webhook verification token
- ✅ אימות בקשות מ-WhatsApp
- ✅ נתוני משתמשים לא בגיט
- ✅ לא שומר מספרי טלפון גלויים

---

## 🤝 תרומה

רוצה לתרום? נשמח!

1. Fork the project
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📝 רישיון

MIT License - ראה קובץ [LICENSE](LICENSE) לפרטים

---

## 👨‍💻 יוצר

**Hiker Bot** נוצר על ידי צוות פיתוח מסור 🚀

---

## 🙏 תודות

- [WhatsApp Cloud API](https://developers.facebook.com/docs/whatsapp/cloud-api) - API נהדר של Meta
- [Flask](https://flask.palletsprojects.com/) - פריימוורק web מצוין
- [ngrok](https://ngrok.com/) - כלי מעולה לפיתוח מקומי
- [Python](https://www.python.org/) - השפה הכי טובה 🐍

---

## 📞 יצירת קשר

יש שאלות? בעיות? רעיונות?

- 🐛 [פתח issue](https://github.com/YOUR_USERNAME/Hiker/issues)
- 💡 [הצע feature](https://github.com/YOUR_USERNAME/Hiker/issues/new)
- 📧 Email: your.email@example.com

---

<div align="center">

**עשוי עם ❤️ בישראל 🇮🇱**

⭐ אם הפרויקט עזר לך - תן לנו כוכב! ⭐

[⬆ חזרה למעלה](#-hiker---whatsapp-hitchhiking-bot)

</div>
