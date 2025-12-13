# מדריך הגדרת מדיניות הפרטיות

## סקירה כללית

קובץ `privacy_policy.html` מכיל את מדיניות הפרטיות של Hiker. כדי לפרסם את האפליקציה ב-Meta, תצטרך לארח את הקובץ הזה בכתובת URL ציבורית.

## אפשרויות אירוח

### אפשרות 1: GitHub Pages (מומלץ - חינם)

1. **העלה את הקובץ למאגר GitHub שלך:**
   ```bash
   git add privacy_policy.html
   git commit -m "Add privacy policy"
   git push
   ```

2. **הפעל GitHub Pages:**
   - לך ל-Settings > Pages במאגר שלך
   - בחר branch (למשל `main`)
   - בחר תיקייה `/ (root)`
   - לחץ Save

3. **קבל את ה-URL:**
   - ה-URL יהיה: `https://YOUR_USERNAME.github.io/Hiker/privacy_policy.html`
   - זה יכול לקחת כמה דקות עד שהדף יהיה זמין

### אפשרות 2: Netlify (חינם)

1. **הירשם ל-Netlify:** https://www.netlify.com
2. **גרור ושחרר את הקובץ** `privacy_policy.html` ל-Netlify
3. **קבל את ה-URL:** Netlify ייתן לך URL כמו `https://random-name-123.netlify.app/privacy_policy.html`

### אפשרות 3: Vercel (חינם)

1. **הירשם ל-Vercel:** https://vercel.com
2. **העלה את הקובץ** דרך הממשק או CLI
3. **קבל את ה-URL:** Vercel ייתן לך URL אוטומטי

### אפשרות 4: שרת משלך

אם יש לך שרת משלך:
1. העלה את `privacy_policy.html` לשרת שלך
2. ודא שהקובץ נגיש דרך HTTP/HTTPS
3. ה-URL יהיה: `https://yourdomain.com/privacy_policy.html`

## עדכון הקובץ

לפני העלאה, ודא שעדכנת:

1. **פרטי קשר:** עדכן את פרטי הקשר ב-`privacy_policy.html` (סעיף 12)
2. **קישור ל-GitHub:** עדכן את `YOUR_USERNAME` בקישור למאגר GitHub
3. **תאריך עדכון:** עדכן את התאריך בכותרת אם עשית שינויים

## שימוש ב-Meta Developer Console

1. לך ל-Meta Developer Console: https://developers.facebook.com
2. בחר את האפליקציה שלך
3. לך ל-App Review > Privacy Policy URL
4. הכנס את ה-URL של מדיניות הפרטיות
5. שמור

## הערות חשובות

- ✅ ה-URL חייב להיות נגיש פומבית (לא דורש אימות)
- ✅ ה-URL חייב להיות HTTPS (לא HTTP)
- ✅ הקובץ חייב להיות בפורמט HTML או PDF
- ✅ התוכן חייב להיות בעברית (או בשפה שבה האפליקציה פועלת)
- ✅ ודא שהקובץ נטען נכון במכשירים ניידים

## בדיקת הקובץ

לפני הגשת הבקשה, בדוק:

1. פתח את ה-URL בדפדפן - האם הקובץ נטען?
2. פתח את ה-URL בטלפון - האם הוא נראה טוב?
3. בדוק שהקישורים עובדים
4. ודא שהתוכן מלא ומדויק

## תמיכה

אם יש לך שאלות או בעיות, פתח issue ב-GitHub או פנה לתמיכה של Meta.

