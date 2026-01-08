# מדריך התקנה מהיר - ממשק ניהול

## הרצה מהירה (5 דקות) ⚡

### שלב 1: הגדרת Admin Token
```bash
# הוסף ל-.env
echo "ADMIN_TOKEN=my-secret-admin-token-123" >> .env
```

### שלב 2: הרץ את הBackend
```bash
python main.py
```

✅ ה-API זמין ב-http://localhost:8080

### שלב 3: (אופציונלי) בנה והרץ Frontend

אם אין לך Node.js מותקן, דלג על זה - ה-API יעבוד גם בלי הממשק הגרפי.

```bash
cd frontend
npm install
npm run dev
```

✅ הדשבורד זמין ב-http://localhost:3000/admin

### שלב 4: גישה לדשבורד

1. פתח את הדשבורד בדפדפן
2. פתח Console (F12)
3. הגדר את הtoken:
```javascript
localStorage.setItem('admin_token', 'my-secret-admin-token-123');
```
4. רענן את הדף (F5)

✅ אתה אמור לראות את הדשבורד!

---

## בדיקת API ידנית (ללא Frontend)

אם אתה לא רוצה להריץ את הFrontend, אתה יכול לבדוק את הAPI ישירות:

### דוגמה 1: קבל סטטיסטיקות
```bash
curl -H "X-Admin-Token: my-secret-admin-token-123" \
     http://localhost:8080/a/stats/overview
```

### דוגמה 2: רשימת משתמשים
```bash
curl -H "X-Admin-Token: my-secret-admin-token-123" \
     http://localhost:8080/a/users
```

### דוגמה 3: נסיעות פעילות
```bash
curl -H "X-Admin-Token: my-secret-admin-token-123" \
     http://localhost:8080/a/rides/active
```

---

## Production Build (עם Frontend)

אם אתה רוצה לבנות את הFrontend ל-production:

```bash
# 1. Build Frontend
cd frontend
npm install
npm run build
cd ..

# 2. Run Backend (יגיש גם את הFrontend)
python main.py
```

עכשיו הדשבורד זמין ב-http://localhost:8080/admin

---

## Deploy ל-Cloud Run

```bash
# הגדר project
export GOOGLE_CLOUD_PROJECT=your-project-id

# Deploy (בונה את הכל אוטומטית)
./deploy.sh
```

או ידני:
```bash
gcloud builds submit --tag gcr.io/$GOOGLE_CLOUD_PROJECT/hiker-bot
gcloud run deploy hiker-bot \
  --image gcr.io/$GOOGLE_CLOUD_PROJECT/hiker-bot \
  --region us-central1 \
  --set-env-vars="ADMIN_TOKEN=your-token"
```

---

## בעיות נפוצות

### "Database not available"
פתרון: הגדר את `GOOGLE_CLOUD_PROJECT` ב-.env

### "Invalid or missing admin token"
פתרון: ודא שהtoken זהה ב-.env וב-localStorage

### "npm: command not found"
פתרון: אין צורך ב-Node.js אם אתה משתמש רק ב-API. אם אתה רוצה את הדשבורד, התקן Node.js מ-https://nodejs.org

### Frontend לא נטען
פתרון: בדוק ש-`frontend/dist` קיים. אם לא, הרץ `cd frontend && npm run build`

---

## סיכום מהיר

**רק API (ללא דשבורד):**
1. הוסף `ADMIN_TOKEN` ל-.env
2. `python main.py`
3. השתמש ב-curl או Postman

**עם דשבורד (dev):**
1. הוסף `ADMIN_TOKEN` ל-.env
2. Terminal 1: `python main.py`
3. Terminal 2: `cd frontend && npm run dev`
4. גש ל-http://localhost:3000/admin

**Production:**
1. `cd frontend && npm run build && cd ..`
2. `python main.py`
3. גש ל-http://localhost:8080/admin



