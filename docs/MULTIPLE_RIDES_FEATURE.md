# Multiple Rides & Requests Feature

## 🎯 Overview

Users can now have **multiple active driver rides** and **multiple hitchhiker requests** simultaneously. This allows:
- Drivers to offer rides on different routes/schedules
- Hitchhikers to look for rides to different destinations
- Users to be both a driver AND a hitchhiker

---

## ✨ What's New

### 1. **Multiple Rides/Requests Support**
- Each user can have unlimited active rides (as driver)
- Each user can have unlimited active requests (as hitchhiker)
- Each ride/request gets a unique ID
- Role can be "driver", "hitchhiker", or "both"

### 2. **Duplicate Prevention**
- System automatically detects and prevents duplicate entries
- Duplicates are identified by: destination + time
- If user tries to add same ride twice, it's rejected

### 3. **List Management**
Users can:
- **List** all their active rides/requests: "הראה לי את הנסיעות שלי"
- **Remove** specific rides/requests: "מחק את הנסיעה הראשונה שלי"
- **Add** new rides/requests anytime

### 4. **Active/Inactive Status**
- Each ride/request has an `active` flag
- Removing = setting `active: false` (soft delete)
- Only active entries are shown to users and used for matching

---

## 📊 Database Structure

### New Fields in User Document:

```json
{
  "phone_number": "972501234567",
  "role": "both",  // Can be "driver", "hitchhiker", or "both"
  
  // NEW: Multiple rides
  "driver_rides": [
    {
      "id": "uuid-1",
      "origin": "גברעם",
      "destination": "תל אביב",
      "days": ["ראשון", "שני"],
      "departure_time": "09:00",
      "return_time": "17:30",
      "notes": "",
      "created_at": "2025-01-01T10:00:00",
      "active": true
    },
    {
      "id": "uuid-2",
      "origin": "גברעם",
      "destination": "חיפה",
      "days": ["רביעי"],
      "departure_time": "14:00",
      "return_time": null,
      "notes": "דרך הכביש המהיר",
      "created_at": "2025-01-01T11:00:00",
      "active": true
    }
  ],
  
  // NEW: Multiple requests
  "hitchhiker_requests": [
    {
      "id": "uuid-3",
      "origin": "גברעם",
      "destination": "ירושלים",
      "travel_date": "2025-01-05",
      "departure_time": "10:00",
      "flexibility": "flexible",
      "notes": "",
      "created_at": "2025-01-01T12:00:00",
      "active": true
    }
  ],
  
  // Legacy fields (kept for backward compatibility)
  "driver_data": {},
  "hitchhiker_data": {}
}
```

---

## 🤖 AI Commands

### Adding Rides/Requests

```
User: "אני נוסע לתל אביב א-ה ב-9"
Bot: "מעולה! הנסיעה נשמרה..."

User: "אני גם נוסע לחיפה בימי ד' ב-14:00"
Bot: "מעולה! הוספתי עוד נסיעה. עכשיו יש לך 2 נסיעות פעילות!"
```

### Listing Rides/Requests

```
User: "הראה לי את הנסיעות שלי"
Bot: Shows all active rides and requests

User: "מה הבקשות שלי?"
Bot: Lists hitchhiker requests
```

### Removing Rides/Requests

```
User: "מחק את הנסיעה הראשונה שלי"
Bot: Removes ride #1

User: "תמחק את הבקשה לירושלים"
Bot: Finds and removes the request
```

---

## 🔧 Technical Implementation

### Files Modified:

1. **`models/user.py`**
   - Added `driver_rides: List[DriverData]`
   - Added `hitchhiker_requests: List[HitchhikerData]`
   - Added `id`, `created_at`, `active` to data models

2. **`database/firestore_client.py`**
   - New: `add_user_ride_or_request()` - adds to list with deduplication
   - New: `get_user_rides_and_requests()` - retrieves all active entries
   - New: `remove_user_ride_or_request()` - soft deletes by ID
   - Updated: `get_drivers_by_route()` - searches through lists
   - Updated: `get_hitchhiker_requests()` - searches through lists

3. **`services/ai_service.py`**
   - Updated: `update_user_records` generates unique IDs
   - New function: `list_my_rides_requests` - lists all entries
   - New function: `remove_ride_request` - removes by index
   - Import new database functions

4. **`config.py`**
   - Updated AI instructions about multiple rides
   - Added warnings about duplicate detection

---

## 🎨 User Experience Examples

### Scenario 1: Driver with Multiple Routes

```
Day 1:
User: "אני נוסע לתל אביב כל יום ב-8:00"
Bot: ✅ "מעולה! הנסיעה נשמרה"

Day 2:
User: "אני גם נוסע לחיפה בימי ה' ב-15:00"
Bot: ✅ "מצוין! עכשיו יש לך 2 נסיעות פעילות"

Later:
User: "הראה לי את הנסיעות שלי"
Bot: 
"יש לך 2 נסיעות פעילות:
1. תל אביב - 8:00 (כל יום)
2. חיפה - 15:00 (ימי ה')"
```

### Scenario 2: User is Both Driver and Hitchhiker

```
User: "אני נוסע לתל אביב כל יום ב-9"
Bot: ✅ "נרשמת כנהג"

User: "אני צריך טרמפ לחיפה מחר ב-14:00"
Bot: ✅ "נרשמת גם כמחפש טרמפ. יש לך עכשיו תפקידים של נהג ומחפש טרמפ"
[Shows matching drivers for Haifa]
```

### Scenario 3: Removing Old Rides

```
User: "הראה לי את הנסיעות שלי"
Bot: Lists 3 rides

User: "מחק את הנסיעה השנייה"
Bot: ✅ "הנסיעה לחיפה נמחקה. נשארו לך 2 נסיעות פעילות"
```

---

## 🚨 Duplicate Prevention

The system checks for duplicates based on:

**For Drivers:**
- Same `destination`
- Same `departure_time`
- Status is `active: true`

**For Hitchhikers:**
- Same `destination`
- Same `travel_date`
- Same `departure_time`
- Status is `active: true`

### Example:

```
User: "אני נוסע לתל אביב ב-9:00"
Bot: ✅ "נרשם!"

User: "אני נוסע לתל אביב ב-9:00"
Bot: ⚠️ "כבר יש לך נסיעה זהה. רוצה לשנות משהו?"
```

---

## 🔍 Matching Logic

When matching:
1. System searches through ALL active rides/requests
2. Each ride/request is matched independently
3. Users with role "both" are checked in both categories
4. Only `active: true` entries are considered
5. Legacy `driver_data`/`hitchhiker_data` still work for old users

### Example:

```
Driver has 2 rides:
  - Tel Aviv, 9:00
  - Haifa, 14:00

Hitchhiker looking for Tel Aviv:
  → Will match with the first ride only
  
Hitchhiker looking for Haifa:
  → Will match with the second ride only
```

---

## ✅ Backward Compatibility

- Old users with `driver_data`/`hitchhiker_data` still work
- Matching functions check BOTH old and new structures
- System automatically migrates when user adds new rides
- No data loss or breaking changes

---

## 📈 Benefits

1. **Flexibility**: Users can manage multiple commutes/trips
2. **Accuracy**: Better matching with more specific rides
3. **Control**: Users can add/remove rides as needed
4. **Scalability**: Supports complex use cases
5. **Safety**: Duplicate prevention avoids confusion

---

## 🐛 Troubleshooting

### Issue: Duplicate rides appearing

**Cause**: AI might interpret one message as multiple rides
**Example**: "אני נוסע לתל אביב וחיפה" → 2 rides created

**Solution**: System now has duplicate detection that prevents identical rides

### Issue: Can't remove a ride

**Check**:
1. List all rides first: "הראה לי את הנסיעות"
2. Note the number (0-based index)
3. Say: "מחק את הנסיעה מספר X"

### Issue: Matches not showing

**Cause**: Old ride is inactive
**Solution**: Add a new ride, or check with "הראה לי את הנסיעות שלי"

---

## 🚀 Future Enhancements

Potential additions:
- [ ] Edit specific ride without removing
- [ ] Set expiration dates for rides
- [ ] Bulk operations (remove all, activate all)
- [ ] Ride templates/favorites
- [ ] Statistics (most popular routes, times)

---

## 📝 Notes

- IDs are generated as UUIDs
- Timestamps are in ISO format (UTC)
- Soft delete preserves history
- Maximum rides per user: unlimited
- Matching happens in real-time

---

**Last Updated**: 2025-12-31
**Version**: 2.0
**Status**: Production Ready ✅



