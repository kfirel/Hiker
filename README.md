# 🚗 Hiker - WhatsApp Hitchhiking Bot

<div align="center">

![Python](https://img.shields.io/badge/python-3.10-blue.svg)
![Flask](https://img.shields.io/badge/flask-latest-green.svg)
![WhatsApp](https://img.shields.io/badge/WhatsApp-Cloud%20API-25D366.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

**בוט חכם לטרמפים בישראל** 🇮🇱

מחבר בין טרמפיסטים לנהגים באמצעות WhatsApp

[תיעוד](#-תיעוד) • [התקנה](#-התקנה-מהירה) • [תכונות](#-תכונות) • [הדרכה](#-הדרכה)

</div>

---

## 📖 אודות

**Hiker** הוא בוט WhatsApp חכם המאפשר לטרמפיסטים ונהגים להתחבר בקלות ובמהירות. הבוט משתמש ב-WhatsApp Cloud API של Meta ומציע חוויית משתמש אינטואיטיבית עם כפתורים אינטראקטיביים ותהליך רישום חכם.

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
- 📢 פרסום טרמפים באופן אקטיvi
- 🎯 בחירת העדפות התראות חכמות
- 📊 ניהול מסלולים מרובים

### תכונות מתקדמות ✨
- 🔄 כפתור restart בכל אינטראקציה
- ✅ אימות אוטומטי של ישובים (100+ ישובים)
- 🤖 הצעות חכמות לישובים דומים
- 📅 אימות פורמטים (ימים, שעות, טווחי זמן)
- 💬 מסך עזרה מובנה
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
# הרצת ngrok
python start_ngrok.py

# בטרמינל אחר - הרצת הבוט
python app.py
```

🎉 **הבוט פועל!** עכשיו הגדר את ה-webhook ב-Meta Developer Console.

---

## 📚 תיעוד

### מדריכים מפורטים

- 📖 [**START_HERE.md**](START_HERE.md) - התחל כאן! המדריך הראשי
- 🏗️ [**ARCHITECTURE.md**](ARCHITECTURE.md) - ארכיטקטורת המערכת
- 🔧 [**SETUP_GUIDE.md**](SETUP_GUIDE.md) - מדריך התקנה מפורט
- 🔗 [**FIND_WEBHOOK_IN_META.md**](FIND_WEBHOOK_IN_META.md) - הגדרת webhook
- 🌐 [**NGROK_SETUP.md**](NGROK_SETUP.md) - הגדרת ngrok
- 🔘 [**INTERACTIVE_BUTTONS_GUIDE.md**](INTERACTIVE_BUTTONS_GUIDE.md) - כפתורים אינטראקטיביים
- ✅ [**VALIDATION_GUIDE.md**](VALIDATION_GUIDE.md) - מנגנון האימות
- 🔄 [**RESTART_BUTTON_FEATURE.md**](RESTART_BUTTON_FEATURE.md) - כפתור ה-restart
- 📊 [**CHAT_FLOW_DIAGRAM.md**](CHAT_FLOW_DIAGRAM.md) - תרשים זרימת השיחה
- 💡 [**QUICK_REFERENCE.md**](QUICK_REFERENCE.md) - עזר מהיר

### מסמכי עדכונים
- 🆕 [**WHATS_NEW.md**](WHATS_NEW.md) - מה חדש
- 📝 [**MENU_UPDATE_SUMMARY.md**](MENU_UPDATE_SUMMARY.md) - עדכון התפריט
- 📋 [**TEST_RESULTS.md**](TEST_RESULTS.md) - תוצאות בדיקות

---

## 🏗️ מבנה הפרויקט

```
Hiker/
├── app.py                      # אפליקציה ראשית (Flask)
├── whatsapp_client.py          # לקוח WhatsApp API
├── conversation_engine.py      # מנוע השיחה
├── conversation_flow.json      # הגדרת זרימת השיחה (עברית)
├── user_database.py            # ניהול משתמשים (JSON)
├── validation.py               # אימות קלט
├── timer_manager.py            # ניהול טיימרים
├── config.py                   # הגדרות
├── start_ngrok.py              # הרצת ngrok
├── requirements.txt            # תלויות Python
├── .env.example                # דוגמה למשתני סביבה
└── docs/                       # תיעוד מפורט
```

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
     1. 🚗🚶 גיבור על! (גם נהג וגם טרמפיסט)
     2. 🚶 טרמפיסט
     3. 🚗 נהג
     
משתמש: [בוחר אפשרות 2]
בוט: האם אתה מחפש כרגע טרמפ? 🏃‍♂️💨
     [כפתורים: כן / לא / 🔄 התחל מחדש]
```

### משתמש רשום חוזר

```
משתמש: שלום
בוט: היי דני! 👋😊
     מה תרצה לעשות היום?
     
     1. 🚶 מחפש טרמפ!
     2. 🚗 לתת טרמפ
     3. 📅 לתכנן נסיעה מראש
     4. 🔄 לעדכן שגרת נסיעות
     5. ✏️ לעדכן פרטים אישיים
     6. 💬 עזרה
```

---

## 🧪 בדיקות

הפרויקט כולל סוויטת בדיקות מקיפה:

```bash
# הרצת בדיקות
python test_conversation_flow.py

# הרצת בדיקת debug ספציפית
python debug_test.py
```

**כיסוי בדיקות:** 97.9% (46/47 טסטים עוברים)

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
