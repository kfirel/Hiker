# 🧪 Sandbox עם קוד מבצעי אמיתי

## סקירה

סביבת ה-Sandbox עודכנה להשתמש **בקוד המבצעי האמיתי** במקום גרסאות מפושטות. כעת הסביבה מבצעת את כל הפעולות הבאות באופן זהה לייצור:

✅ **חיפוש והתאמות** - מנוע ההתאמות המלא    
✅ **חישוב מסלולים** - OSRM API בזמן אמת  
✅ **Geocoding** - city.geojson עם 2,415 ישובים  
✅ **אלגוריתם דינמי** - Dynamic threshold לפי מרחק  
✅ **Route-based matching** - התאמה לפי מסלול  
✅ **Time flexibility** - גמישות זמנים דינמית  

**ההבדל היחיד:** 
- ❌ לא נשלחות הודעות WhatsApp
- 💾 הנתונים נשמרים ב-collections נפרדות (`test_*`)

---

## שינויים טכניים

### 1. **database/firestore_client.py**

כל הפונקציות תומכות כעת ב-`collection_prefix`:

```python
async def add_user_ride_or_request(
    phone_number: str,
    ride_type: str,
    ride_data: Dict[str, Any],
    collection_prefix: str = ""  # ✨ חדש
) -> Dict[str, Any]:
    collection_name = f"{collection_prefix}users" if collection_prefix else "users"
    doc_ref = _db.collection(collection_name).document(phone_number)
    # ...
```

**פונקציות שעודכנו:**
- ✅ `add_user_ride_or_request()`
- ✅ `get_user_rides_and_requests()`
- ✅ `remove_user_ride_or_request()`
- ✅ `update_user_ride_or_request()`
- ✅ `get_drivers_by_route()`
- ✅ `get_hitchhiker_requests()`
- ✅ `update_ride_route_data()`

### 2. **services/matching_service.py**

מנוע ההתאמות תומך ב-`collection_prefix` ו-`send_whatsapp`:

```python
async def find_matches_for_new_record(
    role: str,
    record_data: Dict,
    collection_prefix: str = ""  # ✨ חדש
) -> List[Dict]:
    if role == "driver":
        return await find_hitchhikers_for_driver(record_data, collection_prefix)
    elif role == "hitchhiker":
        return await find_drivers_for_hitchhiker(record_data, collection_prefix)

async def send_match_notifications(
    role: str,
    matches: List[Dict],
    new_record: Dict,
    send_whatsapp: bool = True  # ✨ חדש
):
    if not send_whatsapp:
        logger.info(f"🧪 Sandbox mode: Skipping WhatsApp notifications")
        return
    # ...
```

### 3. **services/route_service.py**

חישוב מסלולים ברקע תומך ב-`collection_prefix`:

```python
async def calculate_and_save_route_background(
    phone_number: str,
    ride_id: str,
    origin: str,
    destination: str,
    max_retries: int = None,
    collection_prefix: str = ""  # ✨ חדש
):
    # ...
    await update_ride_route_data(
        phone_number,
        ride_id,
        route_data,
        collection_prefix  # ✨ מועבר הלאה
    )
```

### 4. **services/ai_service.py**

`process_message_with_ai_sandbox()` משתמש כעת בפונקציות האמיתיות:

```python
async def process_message_with_ai_sandbox(phone_number: str, message_text: str, user_data: dict, collection_prefix: str = "test_"):
    """
    Process a message with AI for sandbox/testing environment.
    Uses the REAL production code but with test collections and without WhatsApp.
    """
    # ...
    if func_name == "update_user_records":
        # ✨ משתמש בפונקציה האמיתית!
        result = await handle_update_user_records(
            phone_number,
            func_args,
            collection_prefix,  # ✨ test_ collections
            send_whatsapp=False  # ✨ ללא WhatsApp
        )
    # ...
```

**לפני:**
```python
# משתמש בגרסאות מפושטות
handle_update_user_records_sandbox()
handle_view_user_records_sandbox()
# ...
```

**אחרי:**
```python
# משתמש בפונקציות האמיתיות עם פרמטרים
handle_update_user_records(collection_prefix="test_", send_whatsapp=False)
handle_view_user_records(collection_prefix="test_")
# ...
```

### 5. **services/function_handlers/__init__.py**

כל הפונקציות תומכות ב-`collection_prefix` ו-`send_whatsapp`:

```python
async def handle_update_user_records(
    phone_number: str,
    arguments: Dict,
    collection_prefix: str = "",  # ✨ חדש
    send_whatsapp: bool = True  # ✨ חדש
) -> Dict:
    # ...
    result = await add_user_ride_or_request(
        phone_number,
        role,
        record,
        collection_prefix  # ✨ מועבר לDB
    )
    
    matches = await find_matches_for_new_record(
        role,
        record,
        collection_prefix  # ✨ מועבר למנוע התאמות
    )
    
    if matches:
        await send_match_notifications(
            role,
            matches,
            record,
            send_whatsapp  # ✨ שליטה בWhatsApp
        )
```

**פונקציות שעודכנו:**
- ✅ `handle_update_user_records()` - תומך ב-2 פרמטרים חדשים
- ✅ `handle_view_user_records()` - תומך ב-collection_prefix
- ✅ `handle_delete_user_record()` - תומך ב-collection_prefix
- ✅ `handle_delete_all_user_records()` - תומך ב-collection_prefix
- ✅ `handle_update_user_record()` - תומך ב-2 פרמטרים חדשים
- ✅ `handle_show_help()` - תומך ב-collection_prefix

---

## זרימת עבודה ב-Sandbox

### דוגמה: משתמש טסט מוסיף נסיעה

```
1. Frontend: "אני נוסע לתל אביב מחר בשעה 8"
   ↓
2. Admin API: POST /a/sandbox/send
   {
     phone_number: "972500000001",
     message: "אני נוסע לתל אביב מחר בשעה 8",
     environment: "test"
   }
   ↓
3. process_message_with_ai_sandbox()
   - collection_prefix = "test_"
   - send_whatsapp = False
   ↓
4. AI Service (Gemini 2.0)
   - מזהה: role="driver"
   - מפרש: destination="תל אביב", travel_date="2026-01-04", departure_time="08:00"
   ↓
5. handle_update_user_records(collection_prefix="test_", send_whatsapp=False)
   ↓
6. Database: test_users collection
   - שומר ב-test_users (לא users!)
   ↓
7. Route Service (Background)
   - מחשב מסלול אמיתי ב-OSRM
   - Geocoding עם city.geojson
   - שומר ב-test_users collection
   ↓
8. Matching Service
   - מחפש טרמפיסטים ב-test_users collection
   - בודק אם הם על המסלול (route-based matching)
   - מוצא התאמות (אם קיימות)
   ↓
9. send_match_notifications(send_whatsapp=False)
   - 🚫 לא שולח WhatsApp (send_whatsapp=False)
   - ✅ מחזיר את התוצאות
   ↓
10. Frontend: מציג תגובה
   "מעולה! הטרמפ שלך ל-תל אביב נשמר 🚗
   
   נמצאו 2 טרמפיסטים מתאימים!
   
   📋 הנסיעות שלך עכשיו:
   
   🚗 אני נוסע:
   1) מגברעם לתל אביב - תאריך: 2026-01-04 בשעה 08:00"
```

---

## Firestore Collections

### Production (environment="production")
```
users/
  972501234567/
    driver_rides: [...]
    hitchhiker_requests: [...]
```

### Test (environment="test")
```
test_users/
  972500000001/
    driver_rides: [...]
    hitchhiker_requests: [...]
```

---

## יתרונות

### 1. **בדיקות אמיתיות** ✅
- אותו קוד כמו בייצור
- התנהגות זהה לחלוטין
- אין סיכוי לפערים בין Sandbox לייצור

### 2. **ניפוי באגים מהיר** 🐛
- ניתן לבדוק את כל הזרימה מקצה לקצה
- לראות את התאמות בזמן אמת
- לבדוק edge cases בקלות

### 3. **פיתוח מהיר** 🚀
- אין צורך לשכפל קוד
- שינויים בקוד האמיתי משתקפים מיד
- קל לבדוק תכונות חדשות

### 4. **בטיחות** 🔒
- נתונים מבודדים (test_* collections)
- לא משפיע על משתמשים אמיתיים
- אפשר לאפס בכל רגע

---

## שימוש

### Frontend (Sandbox Page)

1. גש ל-`/admin/sandbox`
2. בחר סביבה: **Test** (כחול) או **Production** (כתום)
3. שלח הודעות מ-4 משתמשי טסט
4. צפה בהתאמות בזמן אמת
5. אפס הכל עם כפתור "🗑️ אפס הכל"

### דוגמאות לבדיקה

**נהג:**
```
אני נוסע לתל אביב מחר בשעה 8
```

**טרמפיסט:**
```
מחפש טרמפ לתל אביב מחר בשעה 8
```

**התאמה:**
המערכת תמצא אוטומטית את ההתאמה ותציג הודעה!

---

## איפוס Sandbox

```bash
# דרך Frontend
לחץ על "🗑️ אפס הכל" (זמין רק ב-Test mode)

# או דרך API
DELETE /a/sandbox/reset?environment=test
Header: X-Admin-Token: your_token
```

---

## סיכום

הסביבה עודכנה מ**sandbox מפושט** ל**סביבת טסט מלאה**:

| תכונה | לפני | אחרי |
|------|------|------|
| **Matching** | ❌ מפושט | ✅ קוד אמיתי |
| **Route calculation** | ❌ לא היה | ✅ OSRM מלא |
| **Geocoding** | ❌ לא היה | ✅ city.geojson |
| **Dynamic threshold** | ❌ לא היה | ✅ מלא |
| **WhatsApp** | ❌ לא שולח | ❌ לא שולח |
| **Collections** | ✅ test_* | ✅ test_* |

**התוצאה:** סביבת בדיקות מדויקת שמשתמשת בקוד המבצעי, ללא השפעה על הייצור! 🎉

---

**תאריך עדכון:** 3 בינואר 2026  
**גרסה:** 2.1.0



