# 🗄️ תוכנית מעבר ל-MongoDB - ארכיטקטורה מפורטת

## 📊 ניתוח המצב הנוכחי

### מבנה נתונים נוכחי (JSON)

```json
{
  "users": {
    "phone_number": {
      "profile": {
        "full_name": "...",
        "home_settlement": "גברעם",
        "user_type": "hitchhiker|driver|both",
        "destination": "...",
        "time_range": "...",
        "specific_datetime": "..."
      },
      "state": {
        "current_state": "...",
        "context": {},
        "history": []
      },
      "ride_requests": [],  // ❌ בעיה: נשמר בתוך user
      "routines": []
    }
  }
}
```

### בעיות במבנה הנוכחי

1. **אין Matching Logic** - בקשות נשמרות אבל אין חיפוש התאמות
2. **אין Status Tracking** - אין מעקב אחר מצב בקשות (pending, approved, rejected)
3. **אין Approval System** - אין דרך לנהג לאשר/לדחות בקשות
4. **אין Notifications** - אין מערכת התראות לנהגים/טרמפיסטים
5. **JSON לא מתאים ל-Scale** - אין indexing, חיפושים איטיים
6. **Data Separation** - הכל מעורבב, קשה לשאילתות

---

## 🎯 דרישות מערכת

### 1. Matching Logic
- מציאת התאמה בין טרמפיסט לנהג לפי:
  - **יעד** (destination)
  - **שעה** (time range או specific datetime)
  - **מיקום התחלה** (origin - כרגע רק "גברעם")
  - **זמינות נהג** (routines או ad-hoc offers)

### 2. Approval Flow
```
טרמפיסט מבקש טרמפ
    ↓
מערכת מוצאת נהגים מתאימים
    ↓
שולחת התראה לנהג עם פרטי הבקשה
    ↓
נהג מאשר/דוחה
    ↓
טרמפיסט מקבל התראה על התשובה
```

### 3. Status Management
- **Ride Requests**: `pending`, `matched`, `approved`, `rejected`, `completed`, `cancelled`
- **Driver Offers**: `active`, `matched`, `completed`, `cancelled`

### 4. Real-time Notifications
- התראות לנהגים על בקשות חדשות
- התראות לטרמפיסטים על אישורים/דחיות
- התראות על התאמות חדשות

---

## 🏗️ ארכיטקטורה מוצעת - MongoDB

### Collections Structure

#### 1. **users** Collection
```javascript
{
  _id: ObjectId,
  phone_number: String (unique, indexed),
  whatsapp_name: String,
  full_name: String,
  home_settlement: String,
  user_type: String, // "hitchhiker" | "driver" | "both"
  
  // Profile data
  default_destination: String,
  alert_preference: String, // "all" | "my_destinations" | "my_destinations_and_times" | "none"
  
  // State management
  current_state: String,
  state_context: Object,
  state_history: Array,
  
  // Metadata
  created_at: ISODate,
  registered_at: ISODate,
  last_active: ISODate,
  is_registered: Boolean,
  
  // Indexes
  // phone_number: unique
  // user_type: index
  // home_settlement: index
}
```

#### 2. **routines** Collection (שגרות נסיעה)
```javascript
{
  _id: ObjectId,
  user_id: ObjectId (ref: users),
  phone_number: String, // denormalized for quick access
  
  // Routine details
  destination: String,
  days: String, // "א-ה" | "ב,ד" | etc.
  departure_time: String, // "07:00"
  return_time: String, // "18:00"
  
  // Status
  is_active: Boolean,
  
  // Metadata
  created_at: ISODate,
  updated_at: ISODate,
  
  // Indexes
  // user_id: index
  // destination: index
  // days: index
  // is_active: index
  // Compound: {destination, days, is_active}
}
```

#### 3. **ride_requests** Collection (בקשות טרמפ)
```javascript
{
  _id: ObjectId,
  request_id: String (unique, indexed), // UUID or custom format
  
  // Requester info
  requester_id: ObjectId (ref: users),
  requester_phone: String, // denormalized
  
  // Ride details
  type: String, // "hitchhiker_request" | "driver_offer"
  origin: String, // "גברעם"
  destination: String,
  
  // Timing
  time_type: String, // "range" | "specific" | "soon"
  time_range: String, // "08:00-10:00" (for range)
  specific_datetime: String, // "מחר 15:00" or "15/11/2025 14:30"
  ride_timing: String, // "now" | "30min" | "1hour" | "2-5hours"
  
  // Status & Matching
  status: String, // "pending" | "matched" | "approved" | "rejected" | "completed" | "cancelled"
  matched_drivers: Array, // [{driver_id, driver_phone, matched_at, status}]
  approved_driver_id: ObjectId, // Final approved driver
  approved_at: ISODate,
  
  // Notifications
  notifications_sent: Array, // [{driver_phone, sent_at, notification_type}]
  
  // Metadata
  created_at: ISODate,
  updated_at: ISODate,
  expires_at: ISODate, // Auto-expire old requests
  
  // Indexes
  // request_id: unique
  // requester_id: index
  // status: index
  // destination: index
  // created_at: index
  // Compound: {status, destination, time_type}
  // TTL: expires_at (auto-delete expired requests)
}
```

#### 4. **matches** Collection (התאמות)
```javascript
{
  _id: ObjectId,
  match_id: String (unique),
  
  // Parties
  ride_request_id: ObjectId (ref: ride_requests),
  driver_id: ObjectId (ref: users),
  hitchhiker_id: ObjectId (ref: users),
  
  // Match details
  destination: String,
  origin: String,
  matched_time: String, // The matched time
  
  // Status
  status: String, // "pending_approval" | "approved" | "rejected" | "completed" | "cancelled"
  
  // Driver response
  driver_response: String, // "approved" | "rejected" | null
  driver_response_at: ISODate,
  
  // Notifications
  notification_sent_to_driver: Boolean,
  notification_sent_to_hitchhiker: Boolean,
  
  // Metadata
  matched_at: ISODate,
  updated_at: ISODate,
  
  // Indexes
  // match_id: unique
  // ride_request_id: index
  // driver_id: index
  // hitchhiker_id: index
  // status: index
  // Compound: {ride_request_id, status}
}
```

#### 5. **notifications** Collection (היסטוריית התראות)
```javascript
{
  _id: ObjectId,
  
  // Recipient
  recipient_id: ObjectId (ref: users),
  recipient_phone: String,
  
  // Notification details
  type: String, // "ride_request" | "match_found" | "approval" | "rejection" | "reminder"
  title: String,
  message: String,
  
  // Related entities
  ride_request_id: ObjectId,
  match_id: ObjectId,
  
  // Status
  status: String, // "pending" | "sent" | "failed" | "read"
  sent_at: ISODate,
  read_at: ISODate,
  
  // Metadata
  created_at: ISODate,
  
  // Indexes
  // recipient_id: index
  // status: index
  // created_at: index
  // Compound: {recipient_id, status}
}
```

---

## 🔄 Matching Algorithm

### שלב 1: טרמפיסט יוצר בקשה
```python
# 1. שמירת בקשה ב-ride_requests
ride_request = {
    "type": "hitchhiker_request",
    "requester_id": hitchhiker_id,
    "destination": "תל אביב",
    "time_type": "specific",
    "specific_datetime": "מחר 15:00",
    "status": "pending"
}

# 2. חיפוש נהגים מתאימים
matching_drivers = find_matching_drivers(
    destination="תל אביב",
    datetime="מחר 15:00",
    origin="גברעם"
)
```

### שלב 2: חיפוש נהגים מתאימים
```python
def find_matching_drivers(destination, datetime, origin):
    """
    מוצא נהגים מתאימים לפי:
    1. שגרות נסיעה (routines) - יעד + ימים + שעות
    2. הצעות פעילות (active driver offers)
    """
    
    # 1. חיפוש בשגרות נסיעה
    routines = db.routines.find({
        "destination": destination,
        "is_active": True,
        # Check if datetime matches routine days
        # Check if time matches departure_time
    })
    
    # 2. חיפוש בהצעות פעילות
    active_offers = db.ride_requests.find({
        "type": "driver_offer",
        "destination": destination,
        "status": "active",
        # Check time matching
    })
    
    # 3. Combine and rank results
    return combine_and_rank(routines, active_offers)
```

### שלב 3: יצירת התאמות
```python
# לכל נהג מתאים:
for driver in matching_drivers:
    match = {
        "ride_request_id": ride_request_id,
        "driver_id": driver.id,
        "hitchhiker_id": hitchhiker_id,
        "status": "pending_approval",
        "matched_at": datetime.now()
    }
    
    # שמירת התאמה
    db.matches.insert_one(match)
    
    # עדכון ride_request
    db.ride_requests.update_one(
        {"_id": ride_request_id},
        {"$push": {"matched_drivers": {
            "driver_id": driver.id,
            "status": "pending"
        }}}
    )
    
    # שליחת התראה לנהג
    send_notification_to_driver(driver, ride_request)
```

### שלב 4: אישור/דחייה של נהג
```python
# נהג מאשר/דוחה
def driver_responds(match_id, driver_id, response):
    """
    response: "approved" | "rejected"
    """
    
    # עדכון match
    db.matches.update_one(
        {"_id": match_id, "driver_id": driver_id},
        {
            "$set": {
                "status": response,
                "driver_response": response,
                "driver_response_at": datetime.now()
            }
        }
    )
    
    if response == "approved":
        # עדכון ride_request
        db.ride_requests.update_one(
            {"_id": ride_request_id},
            {
                "$set": {
                    "status": "approved",
                    "approved_driver_id": driver_id,
                    "approved_at": datetime.now()
                }
            }
        )
        
        # שליחת התראה לטרמפיסט
        send_notification_to_hitchhiker(hitchhiker_id, "approved")
        
        # דחיית התאמות אחרות
        db.matches.update_many(
            {
                "ride_request_id": ride_request_id,
                "_id": {"$ne": match_id},
                "status": "pending_approval"
            },
            {"$set": {"status": "rejected"}}
        )
```

---

## 📝 Implementation Plan

### Phase 1: MongoDB Setup & Migration
1. ✅ התקנת pymongo
2. ✅ יצירת MongoDB connection module
3. ✅ יצירת Database models (schemas)
4. ✅ Migration script מ-JSON ל-MongoDB
5. ✅ עדכון UserDatabase class להשתמש ב-MongoDB

### Phase 2: Matching System
1. ✅ יצירת RideMatchingService
2. ✅ Implementation של find_matching_drivers
3. ✅ יצירת matches אוטומטית
4. ✅ Testing של matching logic

### Phase 3: Approval Flow
1. ✅ יצירת MatchApprovalService
2. ✅ WhatsApp buttons לאישור/דחייה
3. ✅ עדכון statuses
4. ✅ Notifications

### Phase 4: Notifications System
1. ✅ יצירת NotificationService
2. ✅ Integration עם WhatsApp
3. ✅ Queue system להתראות
4. ✅ Retry logic

### Phase 5: Testing & Optimization
1. ✅ Unit tests
2. ✅ Integration tests
3. ✅ Performance testing
4. ✅ Index optimization

---

## 🔧 Technical Details

### MongoDB Connection
```python
# src/database/mongodb_client.py
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

class MongoDBClient:
    def __init__(self, connection_string, db_name):
        self.client = MongoClient(connection_string)
        self.db = self.client[db_name]
        self._verify_connection()
    
    def _verify_connection(self):
        try:
            self.client.admin.command('ping')
        except ConnectionFailure:
            raise Exception("MongoDB connection failed")
```

### Database Models
```python
# src/database/models.py
from pymongo import IndexModel

class UserModel:
    collection_name = "users"
    
    indexes = [
        IndexModel([("phone_number", 1)], unique=True),
        IndexModel([("user_type", 1)]),
        IndexModel([("home_settlement", 1)]),
    ]

class RideRequestModel:
    collection_name = "ride_requests"
    
    indexes = [
        IndexModel([("request_id", 1)], unique=True),
        IndexModel([("requester_id", 1)]),
        IndexModel([("status", 1), ("destination", 1)]),
        IndexModel([("expires_at", 1)], expireAfterSeconds=0),  # TTL
    ]
```

### Matching Service
```python
# src/services/matching_service.py
class MatchingService:
    def __init__(self, db):
        self.db = db
    
    def find_matching_drivers(self, ride_request):
        """
        מוצא נהגים מתאימים לבקשה
        """
        # 1. Parse ride request details
        destination = ride_request['destination']
        datetime_info = self._parse_datetime(ride_request)
        
        # 2. Search in routines
        routines = self._search_routines(destination, datetime_info)
        
        # 3. Search in active offers
        offers = self._search_active_offers(destination, datetime_info)
        
        # 4. Combine and rank
        return self._combine_results(routines, offers)
    
    def create_matches(self, ride_request_id, drivers):
        """
        יוצר התאמות לכל נהג מתאים
        """
        matches = []
        for driver in drivers:
            match = {
                "ride_request_id": ride_request_id,
                "driver_id": driver['_id'],
                "status": "pending_approval",
                "matched_at": datetime.now()
            }
            matches.append(match)
        
        if matches:
            self.db.matches.insert_many(matches)
            self._notify_drivers(drivers, ride_request_id)
        
        return matches
```

---

## 📊 Indexes Strategy

### Critical Indexes
```javascript
// users
db.users.createIndex({phone_number: 1}, {unique: true})
db.users.createIndex({user_type: 1})
db.users.createIndex({home_settlement: 1})

// routines
db.routines.createIndex({user_id: 1})
db.routines.createIndex({destination: 1, days: 1, is_active: 1})
db.routines.createIndex({is_active: 1})

// ride_requests
db.ride_requests.createIndex({request_id: 1}, {unique: true})
db.ride_requests.createIndex({requester_id: 1})
db.ride_requests.createIndex({status: 1, destination: 1})
db.ride_requests.createIndex({expires_at: 1}, {expireAfterSeconds: 0})

// matches
db.matches.createIndex({ride_request_id: 1, status: 1})
db.matches.createIndex({driver_id: 1})
db.matches.createIndex({hitchhiker_id: 1})
```

---

## 🚀 Migration Strategy

### Step 1: Parallel Run
- שמירה כפולה: JSON + MongoDB
- בדיקת consistency
- Gradual migration

### Step 2: Read from MongoDB
- עדכון כל הקריאות ל-MongoDB
- JSON נשאר ל-backup

### Step 3: Full Migration
- הסרת JSON dependency
- Cleanup של קוד ישן

---

## 📈 Benefits

1. **Scalability** - MongoDB מתאים ל-scale
2. **Performance** - Indexes מהירים יותר
3. **Flexibility** - קל להוסיף fields חדשים
4. **Query Power** - חיפושים מורכבים
5. **Real-time** - Change streams להתראות
6. **Reliability** - Replication & sharding

---

## ⚠️ Considerations

1. **Connection Pooling** - חשוב לניהול connections
2. **Error Handling** - טיפול ב-connection failures
3. **Data Validation** - Schema validation
4. **Backup Strategy** - Regular backups
5. **Monitoring** - Track performance metrics

---

## 📋 Next Steps

1. Review והסכמה על המבנה
2. Setup MongoDB environment
3. Start Phase 1 implementation
4. Testing & iteration



