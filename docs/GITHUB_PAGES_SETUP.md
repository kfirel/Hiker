# הגדרת GitHub Pages למדיניות הפרטיות

## ✅ הקבצים כבר ב-GitHub!

הקבצים `privacy_policy.html` ו-`docs/PRIVACY_POLICY_SETUP.md` כבר נדחפו למאגר שלך ב-GitHub.

## 🚀 שלבים להפעלת GitHub Pages

### שלב 1: הפעל GitHub Pages

1. לך ל: https://github.com/kfirel/Hiker
2. לחץ על **Settings** (בתפריט העליון)
3. בתפריט הצד, לחץ על **Pages** (תחת "Code and automation")
4. תחת **Source**, בחר:
   - **Branch:** `main`
   - **Folder:** `/ (root)`
5. לחץ **Save**

### שלב 2: המתן לפרסום

- GitHub יפרסם את האתר תוך 1-2 דקות
- תראה הודעה ירוקה: "Your site is live at..."

### שלב 3: קבל את ה-URL

ה-URL של מדיניות הפרטיות יהיה:
```
https://kfirel.github.io/Hiker/privacy_policy.html
```

## 📝 הערות חשובות

1. **עדכון פרטי קשר:** לפני השימוש, עדכן את פרטי הקשר ב-`privacy_policy.html` (סעיף 12)

2. **בדיקה:** פתח את ה-URL בדפדפן כדי לוודא שהקובץ נטען נכון

3. **שימוש ב-Meta:** הוסף את ה-URL הזה ב-Meta Developer Console:
   - לך ל: https://developers.facebook.com
   - בחר את האפליקציה שלך
   - App Review > Privacy Policy URL
   - הכנס: `https://kfirel.github.io/Hiker/privacy_policy.html`

## 🔄 עדכון הקובץ בעתיד

כשאתה מעדכן את `privacy_policy.html`:

```bash
git add privacy_policy.html
git commit -m "Update privacy policy"
git push origin main
```

GitHub Pages יעדכן את האתר אוטומטית תוך דקות ספורות.

## ❓ בעיות?

אם האתר לא נטען:
- ודא ש-GitHub Pages מופעל ב-Settings
- המתן 5-10 דקות לפרסום
- בדוק את ה-URL - הוא חייב להיות בדיוק: `https://kfirel.github.io/Hiker/privacy_policy.html`


