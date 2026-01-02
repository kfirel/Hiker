# 📚 Documentation Directory

תיעוד מלא של פרויקט Hiker

## 📁 מבנה

```
docs/
├── README.md                           # המסמך הזה
├── SYSTEM_OVERVIEW.md                  # מבט על מהמערכת
└── implementation/                     # תיעוד יישום
    ├── GEOCODING_SETUP.md             # הגדרת geocoding
    ├── GEOJSON_IMPLEMENTATION.md      # יישום GeoJSON
    ├── IMPLEMENTATION_SUMMARY.md       # סיכום יישום
    ├── TESTING_GUIDE.md               # מדריך בדיקות
    └── QUICK_START.md                 # התחלה מהירה
```

## 📖 מסמכים עיקריים

### 🎯 [SYSTEM_OVERVIEW.md](SYSTEM_OVERVIEW.md)
מבט על כללי על המערכת:
- ארכיטקטורה
- רכיבים עיקריים
- זרימות עבודה

### ⚡ [implementation/QUICK_START.md](implementation/QUICK_START.md)
מדריך התחלה מהירה:
- התקנה
- הגדרה
- הרצה ראשונה

---

## 🔧 תיעוד טכני

### 📍 [implementation/GEOCODING_SETUP.md](implementation/GEOCODING_SETUP.md)
**מערכת Geocoding מדויקת**

נושאים:
- שימוש ב-city.geojson
- אסטרטגיית geocoding
- Google Maps API (אופציונלי)
- דוגמאות שימוש

### 🗺️ [implementation/GEOJSON_IMPLEMENTATION.md](implementation/GEOJSON_IMPLEMENTATION.md)
**יישום טכני של GeoJSON**

נושאים:
- הבעיה שפתרנו
- פרטי יישום
- ביצועים
- בדיקות

### 📝 [implementation/IMPLEMENTATION_SUMMARY.md](implementation/IMPLEMENTATION_SUMMARY.md)
**סיכום המערכת**

נושאים:
- Route-based matching
- Background processing
- Dynamic threshold
- סיכום כללי

### 🧪 [implementation/TESTING_GUIDE.md](implementation/TESTING_GUIDE.md)
**מדריך בדיקות מקיף**

נושאים:
- סוגי בדיקות
- הרצת בדיקות
- ויזואליזציה
- Debugging

---

## 🎓 מדריכים לפי תפקיד

### למפתחים חדשים 👨‍💻
1. קרא: [SYSTEM_OVERVIEW.md](SYSTEM_OVERVIEW.md)
2. אחר כך: [implementation/QUICK_START.md](implementation/QUICK_START.md)
3. ואז: [implementation/IMPLEMENTATION_SUMMARY.md](implementation/IMPLEMENTATION_SUMMARY.md)

### למפתחים מנוסים 🚀
1. [implementation/IMPLEMENTATION_SUMMARY.md](implementation/IMPLEMENTATION_SUMMARY.md) - סקירה מהירה
2. [implementation/GEOJSON_IMPLEMENTATION.md](implementation/GEOJSON_IMPLEMENTATION.md) - פרטים טכניים
3. [implementation/TESTING_GUIDE.md](implementation/TESTING_GUIDE.md) - בדיקות

### ל-DevOps 🔧
1. [implementation/QUICK_START.md](implementation/QUICK_START.md) - setup
2. [SYSTEM_OVERVIEW.md](SYSTEM_OVERVIEW.md) - ארכיטקטורה
3. `/scripts/` - deployment scripts

---

## 🔍 חיפוש מהיר

### רוצה ללמוד על:

**Geocoding?**
→ [implementation/GEOCODING_SETUP.md](implementation/GEOCODING_SETUP.md)

**Route Matching?**
→ [implementation/IMPLEMENTATION_SUMMARY.md](implementation/IMPLEMENTATION_SUMMARY.md)

**בדיקות?**
→ [implementation/TESTING_GUIDE.md](implementation/TESTING_GUIDE.md)

**התחלה מהירה?**
→ [implementation/QUICK_START.md](implementation/QUICK_START.md)

**ארכיטקטורה?**
→ [SYSTEM_OVERVIEW.md](SYSTEM_OVERVIEW.md)

---

## 📝 תרומה לתיעוד

### הוספת מסמך חדש:

1. צור קובץ חדש ב-`docs/` או `docs/implementation/`
2. השתמש בתבנית:

```markdown
# 📌 Title

תיאור קצר

## 🎯 מטרה

מה המסמך הזה מסביר

## 📖 תוכן

### סעיף 1
...

### סעיף 2
...

## 🔗 קישורים קשורים

- [מסמך 1](...)
- [מסמך 2](...)
```

3. עדכן את ה-README הזה

---

## 🎯 עקרונות תיעוד

1. **בהיר** - קל להבנה
2. **מעודכן** - תמיד עם הקוד
3. **מקיף** - כל הפרטים
4. **דוגמאות** - קוד לדוגמה
5. **עברית** - שפה ברורה

---

## 📞 תמיכה

לשאלות על התיעוד:
1. חפש במסמכים הרלוונטיים
2. בדוק את הקוד עצמו
3. הרץ בדיקות לדוגמה
