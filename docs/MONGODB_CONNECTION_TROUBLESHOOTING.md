# 🔧 פתרון בעיות חיבור ל-MongoDB

## ❌ שגיאת Authentication

אם אתה רואה את השגיאה:
```
bad auth : authentication failed
```

זה אומר שהקוד מנסה להתחבר אבל ה-credentials לא נכונים.

---

## ✅ פתרון

### 1. בדוק את ה-.env file

הוסף או עדכן את ה-.env file:

```bash
# MongoDB Atlas Connection String
MONGODB_URI=mongodb+srv://username:password@cluster0.xxxxx.mongodb.net/
MONGODB_DB_NAME=hiker_db
```

**חשוב:**
- החלף `username` ב-username שיצרת ב-Atlas
- החלף `password` ב-password שיצרת ב-Atlas
- החלף `cluster0.xxxxx.mongodb.net` ב-cluster URL שלך מ-Atlas

### 2. איך לקבל Connection String מ-Atlas

1. לך ל-[MongoDB Atlas](https://cloud.mongodb.com/)
2. בחר את ה-Cluster שלך
3. לחץ על "Connect"
4. בחר "Connect your application"
5. העתק את ה-Connection String
6. החלף `<password>` ב-password שיצרת

### 3. בדוק Network Access

ב-Atlas:
1. Security → Network Access
2. ודא שה-IP שלך מורשה (או 0.0.0.0/0 לבדיקה)

### 4. בדוק Database User

ב-Atlas:
1. Security → Database Access
2. ודא שיש לך user עם password
3. ודא שה-user יש לו permissions (Atlas admin)

---

## 🧪 בדיקה מהירה

לאחר עדכון ה-.env:

```bash
python scripts/test_mongodb_connection.py
```

אם הכל תקין, תראה:
```
✅ Connected to MongoDB
✅ All tests passed!
```

---

## 📝 דוגמה ל-.env

```bash
# WhatsApp Configuration
WHATSAPP_PHONE_NUMBER_ID=123456789
WHATSAPP_ACCESS_TOKEN=your_token_here
WEBHOOK_VERIFY_TOKEN=your_verify_token

# MongoDB Configuration
MONGODB_URI=mongodb+srv://myuser:mypassword@cluster0.abc123.mongodb.net/
MONGODB_DB_NAME=hiker_db
```

---

## ⚠️ הערות חשובות

1. **אל תעלה את ה-.env ל-Git!** (הוא כבר ב-.gitignore)
2. **Password צריך להיות URL-encoded** אם יש בו תווים מיוחדים
3. **Connection String צריך להסתיים ב-`/`**

---

## 🔍 Debug Mode

אם אתה רוצה לראות יותר פרטים:

```python
from src.database.mongodb_client import MongoDBClient
from src.config import Config

print(f"URI: {Config.MONGODB_URI}")
print(f"DB: {Config.MONGODB_DB_NAME}")

client = MongoDBClient()
print(f"Connected: {client.is_connected()}")
```


