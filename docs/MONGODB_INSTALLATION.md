# 🗄️ התקנת MongoDB - מדריך

## 📊 מצב נוכחי

הקוד מוכן להתחברות ל-MongoDB, אבל **שרת MongoDB עצמו לא מותקן**.

כרגע המערכת עובדת עם **JSON fallback** (עובד מצוין!).

---

## 🚀 אפשרויות התקנה

### Option 1: MongoDB מקומי (Local)

#### macOS (Homebrew)
```bash
# התקנה
brew tap mongodb/brew
brew install mongodb-community

# הפעלה
brew services start mongodb-community

# בדיקה שהשרת רץ
mongosh  # או mongo (תלוי בגרסה)
```

#### Linux (Ubuntu/Debian)
```bash
# הוסף את ה-repository
wget -qO - https://www.mongodb.org/static/pgp/server-7.0.asc | sudo apt-key add -
echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list

# התקן
sudo apt-get update
sudo apt-get install -y mongodb-org

# הפעל
sudo systemctl start mongod
sudo systemctl enable mongod
```

#### Windows
1. הורד מ-[MongoDB Download Center](https://www.mongodb.com/try/download/community)
2. הרץ את ה-installer
3. בחר "Complete" installation
4. השרת יתחיל אוטומטית

---

### Option 2: MongoDB Atlas (Cloud) - מומלץ! ☁️

**יתרונות:**
- ✅ אין צורך בהתקנה מקומית
- ✅ זמין מכל מקום
- ✅ חינמי עד 512MB
- ✅ אוטומטית backup ו-monitoring

**צעדים:**

1. **צור חשבון**:
   - לך ל-[MongoDB Atlas](https://www.mongodb.com/cloud/atlas/register)
   - הירשם (חינמי)

2. **צור Cluster**:
   - בחר "Build a Database"
   - בחר "FREE" tier (M0)
   - בחר Cloud Provider ו-Region
   - לחץ "Create"

3. **הגדר Database User**:
   - Security → Database Access
   - Add New Database User
   - בחר Password
   - Database User Privileges: "Atlas admin"

4. **הגדר Network Access**:
   - Security → Network Access
   - Add IP Address
   - Allow Access from Anywhere (0.0.0.0/0) - לבדיקה
   - או הוסף את ה-IP שלך

5. **קבל Connection String**:
   - Database → Connect
   - בחר "Connect your application"
   - העתק את ה-Connection String
   - החלף `<password>` בסיסמה שיצרת

6. **הגדר ב-.env**:
   ```bash
   MONGODB_URI=mongodb+srv://username:password@cluster0.xxxxx.mongodb.net/
   MONGODB_DB_NAME=hiker_db
   ```

---

### Option 3: Docker (קל ומהיר) 🐳

```bash
# הרץ MongoDB ב-Docker
docker run -d \
  --name mongodb \
  -p 27017:27017 \
  -e MONGO_INITDB_ROOT_USERNAME=admin \
  -e MONGO_INITDB_ROOT_PASSWORD=password \
  mongo:latest

# בדיקה
docker ps | grep mongodb
```

**Connection String:**
```bash
MONGODB_URI=mongodb://admin:password@localhost:27017/
```

---

## ✅ בדיקה שהכל עובד

לאחר התקנה:

```bash
# בדוק שהשרת רץ
# macOS
brew services list | grep mongodb

# Linux
sudo systemctl status mongod

# Docker
docker ps | grep mongodb
```

**בדיקה מהקוד:**
```python
from src.database.mongodb_client import MongoDBClient

client = MongoDBClient()
print(f"MongoDB Connected: {client.is_connected()}")
```

---

## 🔧 הגדרות ב-.env

```bash
# Option 1: Local MongoDB
MONGODB_URI=mongodb://localhost:27017/
MONGODB_DB_NAME=hiker_db

# Option 2: MongoDB Atlas
MONGODB_URI=mongodb+srv://username:password@cluster0.xxxxx.mongodb.net/
MONGODB_DB_NAME=hiker_db

# Option 3: Docker MongoDB
MONGODB_URI=mongodb://admin:password@localhost:27017/
MONGODB_DB_NAME=hiker_db
```

---

## 📝 Migration לאחר התקנה

לאחר ש-MongoDB רץ:

```bash
# העתק נתונים מ-JSON ל-MongoDB
python scripts/migrate_to_mongodb.py user_data.json
```

---

## ⚠️ הערות חשובות

1. **JSON Fallback עובד מצוין** - אין חובה להתקין MongoDB עכשיו
2. **MongoDB נדרש רק ל-Matching Features** (Phase 2)
3. **לפיתוח מקומי** - JSON מספיק
4. **ל-Production** - מומלץ MongoDB Atlas

---

## 🎯 המלצה

**לפיתוח מקומי**: JSON fallback מספיק (כבר עובד!)

**ל-Production**: MongoDB Atlas (חינמי, קל, אמין)

---

## 🐛 Troubleshooting

### Connection Refused?
```bash
# ודא שהשרת רץ
# macOS
brew services start mongodb-community

# Linux
sudo systemctl start mongod

# Docker
docker start mongodb
```

### Authentication Failed?
- ודא שה-username ו-password נכונים
- ב-Atlas: ודא ש-Network Access מאפשר את ה-IP שלך

### Port Already in Use?
```bash
# מצא מה משתמש ב-port 27017
lsof -i :27017

# או שנה port ב-MongoDB config
```

---

## 📚 משאבים

- [MongoDB Installation Guide](https://www.mongodb.com/docs/manual/installation/)
- [MongoDB Atlas Setup](https://www.mongodb.com/docs/atlas/getting-started/)
- [Docker MongoDB](https://hub.docker.com/_/mongo)



