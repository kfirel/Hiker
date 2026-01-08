# התחלה מהירה - ממשק ניהול 🚀

## 3 שלבים פשוטים

### 1️⃣ הגדרת Token
ערוך את `.env` והוסף:
```bash
ADMIN_TOKEN=your-secret-token-123
```

### 2️⃣ הרצת השרת
```bash
python main.py
```

### 3️⃣ גישה לAPI
השתמש ב-curl או כלי דומה:
```bash
curl -H "X-Admin-Token: your-secret-token-123" \
     http://localhost:8080/a/stats/overview
```

---

## רוצה את הממשק הגרפי? (אופציונלי)

### אופציה א': Dev Mode
```bash
# Terminal 1
python main.py

# Terminal 2  
cd frontend
npm install
npm run dev
```
גש ל: http://localhost:3000/admin

### אופציה ב': Production
```bash
cd frontend && npm install && npm run build && cd ..
python main.py
```
גש ל: http://localhost:8080/admin

**חשוב:** הגדר token ב-localStorage של הדפדפן:
```javascript
localStorage.setItem('admin_token', 'your-secret-token-123');
```

---

## API Endpoints המרכזיים

| Endpoint | תיאור |
|----------|-------|
| `GET /a/stats/overview` | סטטיסטיקות כלליות |
| `GET /a/users` | רשימת משתמשים |
| `GET /a/rides/active` | נסיעות פעילות |
| `GET /a/logs/errors` | לוג שגיאות |

כל ה-endpoints דורשים header: `X-Admin-Token: your-token`

---

📖 למידע מפורט ראה: [ADMIN_DASHBOARD.md](ADMIN_DASHBOARD.md)



