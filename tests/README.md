# 🧪 Tests Directory

תיקיית הבדיקות של פרויקט Hiker

## 📁 מבנה

```
tests/
├── README.md                      # המסמך הזה
├── outputs/                       # תוצאות בדיקות (HTML, מפות)
├── test_geojson_simple.py        # בדיקת geocoding עם GeoJSON
├── test_gevaram_final.py         # בדיקות מקיפות מגברעם
├── test_route_simple.py          # בדיקות route service פשוטות
├── test_route_visual.py          # יצירת מפות ויזואליות
├── test_route_scenarios.py       # תרחישי בדיקה שונים
├── test_route_standalone.py      # בדיקה עצמאית
└── test_route_system.py          # בדיקה מערכתית מלאה
```

## 🎯 סוגי בדיקות

### 1. **בדיקות Geocoding**
- `test_geojson_simple.py` - בדיקה שה-GeoJSON עובד נכון

### 2. **בדיקות Route**
- `test_route_simple.py` - בדיקות בסיסיות
- `test_route_standalone.py` - בדיקה ללא תלויות
- `test_route_system.py` - בדיקה מלאה של המערכת

### 3. **בדיקות ויזואליות**
- `test_route_visual.py` - יצירת מפה בודדת
- `test_gevaram_final.py` - 5 תרחישים מגברעם
- `test_route_scenarios.py` - תרחישים נוספים

## 🚀 הרצת בדיקות

### בדיקה מהירה:
```bash
cd /Users/kelgabsi/privet/Hiker
python3 tests/test_geojson_simple.py
```

### בדיקות ויזואליות:
```bash
python3 tests/test_gevaram_final.py
# פותח 5 מפות HTML בדפדפן
```

### כל הבדיקות:
```bash
python3 -m pytest tests/
```

## 📊 תוצאות

תוצאות הבדיקות (מפות HTML, לוגים) נשמרות בתיקיית `outputs/`.

## 📝 הוספת בדיקה חדשה

1. צור קובץ חדש: `test_<name>.py`
2. ודא שהקובץ מתחיל ב-`test_`
3. הוסף תיעוד למה הבדיקה בודקת
4. עדכן את ה-README הזה

## 🔍 מה לבדוק

- ✅ Geocoding (עם city.geojson)
- ✅ חישוב מסלולים (OSRM)
- ✅ חישוב מרחקים (Haversine)
- ✅ Threshold דינמי
- ✅ Background processing
- ✅ ויזואליזציה על מפות



