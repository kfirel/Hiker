# תיקונים לסביבת הטסט (Sandbox)

## תאריך: 3 ינואר 2026

## סיכום השינויים

### 1. שליחה אוטומטית של הודעות מהירות ✅

**בעיה:** היה צריך ללחוץ על הודעה מהירה ואז ללחוץ שוב על "שלח".

**פתרון:** הודעות מהירות נשלחות מיד בלחיצה אחת.

**קובץ שונה:** `frontend/src/pages/SandboxPage.jsx`

```javascript
const handleQuickMessage = (text) => {
  setShowQuickMessages(false);
  // Send immediately
  sendMutation.mutate(text);
};
```

---

### 2. תיקון זיהוי התאמות בסביבת טסט ✅

**בעיה:** המערכת לא זיהתה התאמות בסביבת הטסט.

**סיבה:** הפונקציה `handle_update_user_records` ניסתה לקרוא את שם המשתמש מה-production collection במקום מה-test collection.

**פתרון:** שינוי הלוגיקה כך שבסביבת sandbox היא תקרא את שם המשתמש מה-test collection.

**קובץ שונה:** `services/function_handlers/__init__.py`

```python
# Get user name (from the sandbox user data if in sandbox mode)
if collection_prefix:
    # Sandbox mode - get from test collection
    user_data = await get_user_rides_and_requests(phone_number, collection_prefix)
    # Try to get name from first query, or use default
    from database import get_db
    db = get_db()
    if db:
        doc = db.collection(f"{collection_prefix}users").document(phone_number).get()
        if doc.exists:
            user_name = doc.to_dict().get("name", "משתמש")
        else:
            user_name = "משתמש"
    else:
        user_name = "משתמש"
else:
    # Production mode - use regular function
    from database import get_or_create_user
    user_data, _ = await get_or_create_user(phone_number)
    user_name = user_data.get("name", "משתמש")
```

---

### 3. שיפור לוגים לזיהוי בעיות התאמה ✅

**שינויים:**

1. **בפונקציית `find_matches_for_new_record`:**
   - לוגים מפורטים יותר עם כל הפרמטרים
   - ספירת התאמות שנמצאו

2. **בפונקציית `send_match_notifications`:**
   - לוג כשלא נמצאו התאמות
   - לוג מפורט בsandbox mode עם כל ההתאמות שנמצאו (אבל לא נשלחו בוואטסאפ)

**קובץ שונה:** `services/matching_service.py`

```python
if not matches:
    logger.info(f"❌ No matches found")
    return

# Skip WhatsApp messages in sandbox mode
if not send_whatsapp:
    logger.info(f"🧪 Sandbox mode: Found {len(matches)} matches but skipping WhatsApp notifications")
    for match in matches:
        logger.info(f"   Match: {match.get('phone_number')} - {match.get('destination')}")
    return
```

---

### 4. כלי דיבאג חדש: הצגת כל הנסיעות ✅

**תכונה חדשה:** כפתור "📊 הצג כל הנסיעות" בסביבת הטסט.

**מה זה עושה:**
- מציג את כל הנהגים והטרמפיסטים בסביבת הטסט
- מראה סיכום: כמה נהגים וכמה טרמפיסטים
- עוזר לזהות למה אין התאמות (אולי אין מספיק משתמשים, או הזמנים/יעדים לא מתאימים)

**קבצים שונו:**

1. **Backend:** `admin.py` - endpoint חדש `/a/sandbox/all-rides`
2. **Frontend:** `SandboxPage.jsx` - כפתור ו-modal חדשים

**תצוגה:**
- כרטיסים ירוקים לנהגים 🚗
- כרטיסים כחולים לטרמפיסטים 🎒
- כל כרטיס מראה: שם, טלפון, יעד, תאריך, שעה, ימים/גמישות

---

## איך לבדוק שהתיקונים עובדים

### 1. בדיקת שליחה אוטומטית
1. פתח את Sandbox
2. לחץ על "📝 הודעה מהירה"
3. בחר הודעה מהרשימה
4. ✅ **התוצאה המצופה:** ההודעה תישלח מיד ללא צורך ללחוץ "שלח"

### 2. בדיקת התאמות
1. צור 2 משתמשים:
   - **User 1:** "אני נוסע לתל אביב מחר בשעה 10"
   - **User 2:** "מחפש טרמפ לתל אביב מחר בשעה 10"
2. ✅ **התוצאה המצופה:** כל משתמש יקבל הודעה: "נמצאו X התאמות!"

### 3. בדיקת תצוגת כל הנסיעות
1. צור מספר נסיעות/בקשות
2. לחץ על "📊 הצג כל הנסיעות"
3. ✅ **התוצאה המצופה:** תיפתח חלונית עם כל הנסיעות והבקשות בסביבת הטסט

---

## טיפים לפתרון בעיות

### אם עדיין אין התאמות:

1. **בדוק את הנתונים:**
   - לחץ "📊 הצג כל הנסיעות"
   - ודא שיש גם נהג וגם טרמפיסט לאותו יעד

2. **בדוק את הזמנים:**
   - המערכת דורשת התאמה בזמן (לפי רמת הגמישות)
   - טרמפיסטים עם "very_flexible" יכולים להתאים לנהגים עד ±2 שעות

3. **בדוק את התאריכים:**
   - נהג ש"נוסע מחר" יתאים לטרמפיסט ש"מחפש מחר"
   - נהג קבוע (ימים א'-ה') יתאים לכל טרמפיסט באותו יום בשבוע

4. **בדוק את היעדים:**
   - המערכת משתמשת ב-route matching
   - טרמפיסט לירושלים יתאים לנהג לבאר שבע (דרך הדרך)

5. **בדוק את הלוגים:**
   ```bash
   # הפעל את השרת במצב verbose
   python main.py
   
   # חפש שורות עם:
   # 🔍 find_matches_for_new_record
   # 📊 Found X potential drivers/hitchhikers
   # ✅ MATCH FOUND!
   # ❌ Time mismatch / Destination incompatible
   ```

---

## סטטוס הקוד

- ✅ Frontend: ללא שגיאות linter
- ✅ Backend: ללא שגיאות linter
- ✅ כל הפונקציות תומכות ב-collection_prefix
- ✅ Sandbox משתמש בקוד המבצעי (לא בשכפול)

---

## קבצים שהשתנו

1. `frontend/src/pages/SandboxPage.jsx` - שליחה אוטומטית + תצוגת נסיעות
2. `services/function_handlers/__init__.py` - תיקון קריאת שם משתמש
3. `services/matching_service.py` - שיפור לוגים
4. `admin.py` - endpoint חדש לתצוגת נסיעות

---

## להמשך

יש לבדוק את המערכת עם מקרי קצה:
- [ ] נהג קבוע מול טרמפיסט חד-פעמי
- [ ] טרמפיסטים עם רמות גמישות שונות
- [ ] יעדים שנמצאים על המסלול (route matching)
- [ ] הודעות עם שגיאות/חוסר מידע



