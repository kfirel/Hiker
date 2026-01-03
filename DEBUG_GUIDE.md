# 🐛 מדריך Debug מהיר

## הרצת הפרויקט בלחיצת כפתור

### אופציה 1: Full Stack (בקאנד + פרונטאנד)

1. לחץ על סמל ה-Debug בסרגל הצד (🐛) או `Cmd+Shift+D`
2. בחר מהרשימה: **🚀🎨 Full Stack (Backend + Frontend)**
3. לחץ F5 או על הכפתור הירוק ▶️

**זהו! הפרויקט רץ!** 🎉

- Backend: http://localhost:8080
- Frontend: http://localhost:5173
- Admin: http://localhost:8080/admin

---

### אופציה 2: רק Backend או Frontend

בחר מהרשימה:
- **🚀 Backend (FastAPI)** - רק בקאנד
- **🎨 Frontend (Vite)** - רק פרונטאנד

---

## איך לעצור על נקודות בקוד (Breakpoints)

1. פתח קובץ Python (למשל `services/ai_service.py`)
2. **לחץ משמאל למספר השורה** - יופיע עיגול אדום 🔴
3. הרץ את הבקאנד (F5)
4. כשהקוד מגיע לשורה - **הוא נעצר!**
5. תוכל לראות את כל המשתנים בצד שמאל

### כפתורים חשובים:
- **F5** - Start/Continue
- **F9** - הוסף/הסר Breakpoint
- **F10** - Step Over (שורה הבאה)
- **F11** - Step Into (היכנס לפונקציה)
- **Shift+F5** - Stop

---

## Tasks (טאסקים מהירים)

לחץ `Cmd+Shift+P` → `Tasks: Run Task`:

- **🚀🎨 Start Full Stack** - הרץ הכל (ללא debug)
- **🧪 Run All Tests** - הרץ טסטים
- **📦 Install Dependencies** - התקן חבילות
- **🧹 Clean Logs** - נקה לוגים

---

## פתרון בעיות מהיר

### "Python interpreter not found"
```
Cmd+Shift+P → Python: Select Interpreter → בחר ./venv/bin/python
```

### "Port already in use"
```bash
kill -9 $(lsof -ti:8080)
```

### התקנת חבילות
```bash
source venv/bin/activate
pip install -r requirements.txt

cd frontend
npm install
```

---

## 💡 למידע מלא

קרא את: `.vscode/README.md`

---

**בהצלחה! 🚀**
