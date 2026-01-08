# 📊 Data Directory

תיקיית נתונים של פרויקט Hiker

## 📁 קבצים

### `city.geojson` 🗺️

**מסד נתונים מקומי של כל הישובים בישראל**

#### מידע כללי:
- **מספר ישובים:** 2,415
- **פורמט:** GeoJSON
- **קידוד:** UTF-8
- **גודל:** ~2MB

#### מבנה הנתונים:

```json
{
  "type": "Feature",
  "properties": {
    "OBJECTID_1": 689,
    "SETL_CODE": 342,
    "MGLSDE_LOC": "גברעם",              // שם בעברית
    "MGLSDE_L_4": "GEVAR'AM",           // שם באנגלית
    "MGLSDE_L_3": "קיבוצים",           // סוג ישוב
    "MGLSDE_L_1": 311,                  // אוכלוסייה
    "MGLSDE_L_2": 33                    // קוד סוג ישוב
  },
  "geometry": {
    "type": "Point",
    "coordinates": [34.612915, 31.591891]  // [longitude, latitude]
  }
}
```

#### שימוש:

הקובץ משמש את `services/route_service.py` לגיאוקודינג מדויק:

```python
from services.route_service import geocode_address

coords = geocode_address("גברעם")
# → (31.591891, 34.612915)
```

#### יתרונות:

- ✅ **דיוק מקסימלי** - קואורדינטות רשמיות
- ✅ **מהירות** - ללא צורך ב-API חיצוני
- ✅ **אמינות** - עובד גם ללא אינטרנט
- ✅ **כיסוי מלא** - כל הישובים בישראל
- ✅ **חינמי** - ללא עלויות

#### עדכון:

לעדכן את מסד הנתונים:

1. קבל קובץ GeoJSON מעודכן
2. החלף את `city.geojson`
3. הפעל מחדש את השרת

#### מקור:

נתונים רשמיים של הישובים בישראל.

#### קישורים:

- [תיעוד מלא](../docs/implementation/GEOCODING_SETUP.md)
- [יישום טכני](../docs/implementation/GEOJSON_IMPLEMENTATION.md)



