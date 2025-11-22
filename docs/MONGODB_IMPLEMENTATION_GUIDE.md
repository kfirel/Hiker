# 🛠️ מדריך Implementation - מעבר ל-MongoDB

## 📋 Flow Diagram

### Ride Request Flow
```
┌─────────────────┐
│  טרמפיסט מבקש  │
│     טרמפ        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ שמירה ב-DB      │
│ ride_requests    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ חיפוש נהגים     │
│   מתאימים       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ יצירת matches   │
│ לכל נהג          │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ שליחת התראות    │
│   לנהגים        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ נהג מאשר/דוחה   │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌────────┐ ┌────────┐
│ מאשר   │ │ דוחה   │
└───┬────┘ └───┬────┘
    │          │
    ▼          ▼
┌────────┐ ┌────────┐
│ התראה  │ │ המשך   │
│ לטרמפיסט│ │ חיפוש  │
└────────┘ └────────┘
```

---

## 💻 Code Implementation

### 1. MongoDB Client Setup

```python
# src/database/mongodb_client.py
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class MongoDBClient:
    """MongoDB connection manager"""
    
    def __init__(self, connection_string: str, db_name: str = "hiker_db"):
        """
        Initialize MongoDB client
        
        Args:
            connection_string: MongoDB connection string
            db_name: Database name
        """
        self.connection_string = connection_string
        self.db_name = db_name
        self.client: Optional[MongoClient] = None
        self.db = None
        self._connect()
        self._create_indexes()
    
    def _connect(self):
        """Establish MongoDB connection"""
        try:
            self.client = MongoClient(
                self.connection_string,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000
            )
            # Test connection
            self.client.admin.command('ping')
            self.db = self.client[self.db_name]
            logger.info(f"Connected to MongoDB: {self.db_name}")
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"MongoDB connection failed: {e}")
            raise
    
    def _create_indexes(self):
        """Create necessary indexes"""
        # Users indexes
        self.db.users.create_index("phone_number", unique=True)
        self.db.users.create_index("user_type")
        self.db.users.create_index("home_settlement")
        
        # Routines indexes
        self.db.routines.create_index("user_id")
        self.db.routines.create_index([("destination", 1), ("days", 1), ("is_active", 1)])
        
        # Ride requests indexes
        self.db.ride_requests.create_index("request_id", unique=True)
        self.db.ride_requests.create_index("requester_id")
        self.db.ride_requests.create_index([("status", 1), ("destination", 1)])
        self.db.ride_requests.create_index("expires_at", expireAfterSeconds=0)
        
        # Matches indexes
        self.db.matches.create_index([("ride_request_id", 1), ("status", 1)])
        self.db.matches.create_index("driver_id")
        self.db.matches.create_index("hitchhiker_id")
        
        logger.info("MongoDB indexes created")
    
    def get_collection(self, collection_name: str):
        """Get a collection"""
        return self.db[collection_name]
    
    def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")
```

### 2. Database Models

```python
# src/database/models.py
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from bson import ObjectId
import uuid

class UserModel:
    """User data model"""
    
    @staticmethod
    def create(phone_number: str, whatsapp_name: str = None) -> Dict[str, Any]:
        """Create new user document"""
        return {
            "phone_number": phone_number,
            "whatsapp_name": whatsapp_name,
            "full_name": None,
            "home_settlement": "גברעם",
            "user_type": None,
            "default_destination": None,
            "alert_preference": None,
            "current_state": "initial",
            "state_context": {},
            "state_history": [],
            "created_at": datetime.now(),
            "registered_at": None,
            "last_active": datetime.now(),
            "is_registered": False
        }
    
    @staticmethod
    def update_last_active(phone_number: str, db):
        """Update user's last active timestamp"""
        db.users.update_one(
            {"phone_number": phone_number},
            {"$set": {"last_active": datetime.now()}}
        )

class RideRequestModel:
    """Ride request data model"""
    
    @staticmethod
    def create(
        requester_id: ObjectId,
        requester_phone: str,
        request_type: str,
        destination: str,
        origin: str = "גברעם",
        time_type: str = None,
        time_range: str = None,
        specific_datetime: str = None,
        ride_timing: str = None
    ) -> Dict[str, Any]:
        """Create new ride request"""
        request_id = f"RR_{uuid.uuid4().hex[:12]}"
        
        # Calculate expiration (24 hours from now)
        expires_at = datetime.now() + timedelta(hours=24)
        
        return {
            "request_id": request_id,
            "requester_id": requester_id,
            "requester_phone": requester_phone,
            "type": request_type,  # "hitchhiker_request" | "driver_offer"
            "origin": origin,
            "destination": destination,
            "time_type": time_type,  # "range" | "specific" | "soon"
            "time_range": time_range,
            "specific_datetime": specific_datetime,
            "ride_timing": ride_timing,
            "status": "pending",
            "matched_drivers": [],
            "approved_driver_id": None,
            "approved_at": None,
            "notifications_sent": [],
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "expires_at": expires_at
        }

class MatchModel:
    """Match data model"""
    
    @staticmethod
    def create(
        ride_request_id: ObjectId,
        driver_id: ObjectId,
        hitchhiker_id: ObjectId,
        destination: str,
        origin: str
    ) -> Dict[str, Any]:
        """Create new match"""
        match_id = f"MATCH_{uuid.uuid4().hex[:12]}"
        
        return {
            "match_id": match_id,
            "ride_request_id": ride_request_id,
            "driver_id": driver_id,
            "hitchhiker_id": hitchhiker_id,
            "destination": destination,
            "origin": origin,
            "matched_time": None,
            "status": "pending_approval",
            "driver_response": None,
            "driver_response_at": None,
            "notification_sent_to_driver": False,
            "notification_sent_to_hitchhiker": False,
            "matched_at": datetime.now(),
            "updated_at": datetime.now()
        }
```

### 3. Matching Service

```python
# src/services/matching_service.py
from datetime import datetime, timedelta
from typing import List, Dict, Any
import logging
from bson import ObjectId

logger = logging.getLogger(__name__)

class MatchingService:
    """Service for matching hitchhikers with drivers"""
    
    def __init__(self, db):
        self.db = db
    
    def find_matching_drivers(self, ride_request: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Find matching drivers for a ride request
        
        Args:
            ride_request: Ride request document
            
        Returns:
            List of matching driver documents
        """
        destination = ride_request['destination']
        time_info = self._parse_time_info(ride_request)
        
        matching_drivers = []
        
        # 1. Search in routines
        routines = self._search_routines(destination, time_info)
        for routine in routines:
            driver = self.db.users.find_one({"_id": routine['user_id']})
            if driver and driver.get('user_type') in ['driver', 'both']:
                matching_drivers.append({
                    'driver_id': driver['_id'],
                    'driver_phone': driver['phone_number'],
                    'match_type': 'routine',
                    'routine_id': routine['_id'],
                    'score': self._calculate_match_score(routine, time_info)
                })
        
        # 2. Search in active driver offers
        active_offers = self._search_active_offers(destination, time_info)
        for offer in active_offers:
            driver = self.db.users.find_one({"_id": offer['requester_id']})
            if driver:
                matching_drivers.append({
                    'driver_id': driver['_id'],
                    'driver_phone': driver['phone_number'],
                    'match_type': 'offer',
                    'offer_id': offer['_id'],
                    'score': self._calculate_offer_score(offer, time_info)
                })
        
        # Remove duplicates and sort by score
        unique_drivers = self._deduplicate_drivers(matching_drivers)
        return sorted(unique_drivers, key=lambda x: x['score'], reverse=True)
    
    def _parse_time_info(self, ride_request: Dict[str, Any]) -> Dict[str, Any]:
        """Parse time information from ride request"""
        time_info = {
            'type': ride_request.get('time_type'),
            'time_range': ride_request.get('time_range'),
            'specific_datetime': ride_request.get('specific_datetime'),
            'ride_timing': ride_request.get('ride_timing')
        }
        
        # Parse specific datetime if exists
        if time_info['specific_datetime']:
            parsed = self._parse_datetime_string(time_info['specific_datetime'])
            time_info['parsed_datetime'] = parsed
        
        return time_info
    
    def _parse_datetime_string(self, datetime_str: str) -> Dict[str, Any]:
        """
        Parse datetime string like "מחר 15:00" or "15/11/2025 14:30"
        Returns dict with date and time info
        """
        # TODO: Implement datetime parsing
        # For now, return basic structure
        return {
            'is_tomorrow': 'מחר' in datetime_str,
            'is_today': 'היום' in datetime_str,
            'raw': datetime_str
        }
    
    def _search_routines(self, destination: str, time_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search for matching routines"""
        query = {
            "destination": destination,
            "is_active": True
        }
        
        # Add day filter if we have specific datetime
        if time_info.get('parsed_datetime'):
            # TODO: Map datetime to Hebrew days
            # For now, return all active routines for destination
            pass
        
        routines = list(self.db.routines.find(query))
        return routines
    
    def _search_active_offers(self, destination: str, time_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search for active driver offers"""
        query = {
            "type": "driver_offer",
            "destination": destination,
            "status": "active"
        }
        
        offers = list(self.db.ride_requests.find(query))
        return offers
    
    def _calculate_match_score(self, routine: Dict[str, Any], time_info: Dict[str, Any]) -> float:
        """Calculate match score for a routine"""
        score = 1.0
        
        # Exact destination match
        if routine.get('destination') == time_info.get('destination'):
            score += 1.0
        
        # Time matching (simplified)
        # TODO: Implement proper time matching logic
        
        return score
    
    def _calculate_offer_score(self, offer: Dict[str, Any], time_info: Dict[str, Any]) -> float:
        """Calculate match score for an offer"""
        score = 1.0
        
        # Exact destination match
        if offer.get('destination') == time_info.get('destination'):
            score += 1.0
        
        return score
    
    def _deduplicate_drivers(self, drivers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate drivers, keep highest score"""
        seen = {}
        for driver in drivers:
            driver_id = str(driver['driver_id'])
            if driver_id not in seen or driver['score'] > seen[driver_id]['score']:
                seen[driver_id] = driver
        
        return list(seen.values())
    
    def create_matches(self, ride_request_id: ObjectId, hitchhiker_id: ObjectId, 
                      matching_drivers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Create match documents for all matching drivers
        
        Args:
            ride_request_id: Ride request ID
            hitchhiker_id: Hitchhiker user ID
            matching_drivers: List of matching driver info
            
        Returns:
            List of created match documents
        """
        ride_request = self.db.ride_requests.find_one({"_id": ride_request_id})
        if not ride_request:
            logger.error(f"Ride request not found: {ride_request_id}")
            return []
        
        matches = []
        matched_drivers_info = []
        
        for driver_info in matching_drivers:
            match_doc = MatchModel.create(
                ride_request_id=ride_request_id,
                driver_id=driver_info['driver_id'],
                hitchhiker_id=hitchhiker_id,
                destination=ride_request['destination'],
                origin=ride_request['origin']
            )
            
            result = self.db.matches.insert_one(match_doc)
            match_doc['_id'] = result.inserted_id
            matches.append(match_doc)
            
            matched_drivers_info.append({
                "driver_id": driver_info['driver_id'],
                "driver_phone": driver_info['driver_phone'],
                "matched_at": datetime.now(),
                "status": "pending"
            })
        
        # Update ride request with matched drivers
        self.db.ride_requests.update_one(
            {"_id": ride_request_id},
            {
                "$set": {
                    "status": "matched",
                    "matched_drivers": matched_drivers_info,
                    "updated_at": datetime.now()
                }
            }
        )
        
        logger.info(f"Created {len(matches)} matches for ride request {ride_request_id}")
        return matches
```

### 4. Approval Service

```python
# src/services/approval_service.py
from datetime import datetime
from typing import Dict, Any, Optional
import logging
from bson import ObjectId

logger = logging.getLogger(__name__)

class ApprovalService:
    """Service for handling driver approvals"""
    
    def __init__(self, db, whatsapp_client):
        self.db = db
        self.whatsapp_client = whatsapp_client
    
    def driver_approve(self, match_id: str, driver_phone: str) -> bool:
        """
        Driver approves a match
        
        Args:
            match_id: Match ID
            driver_phone: Driver's phone number
            
        Returns:
            True if successful
        """
        match = self.db.matches.find_one({"match_id": match_id})
        if not match:
            logger.error(f"Match not found: {match_id}")
            return False
        
        # Verify driver
        driver = self.db.users.find_one({"phone_number": driver_phone})
        if not driver or str(driver['_id']) != str(match['driver_id']):
            logger.error(f"Driver verification failed for match {match_id}")
            return False
        
        # Update match
        self.db.matches.update_one(
            {"match_id": match_id},
            {
                "$set": {
                    "status": "approved",
                    "driver_response": "approved",
                    "driver_response_at": datetime.now(),
                    "updated_at": datetime.now()
                }
            }
        )
        
        # Update ride request
        ride_request = self.db.ride_requests.find_one({"_id": match['ride_request_id']})
        if ride_request:
            self.db.ride_requests.update_one(
                {"_id": match['ride_request_id']},
                {
                    "$set": {
                        "status": "approved",
                        "approved_driver_id": match['driver_id'],
                        "approved_at": datetime.now(),
                        "updated_at": datetime.now()
                    }
                }
            )
            
            # Reject other pending matches for this request
            self.db.matches.update_many(
                {
                    "ride_request_id": match['ride_request_id'],
                    "match_id": {"$ne": match_id},
                    "status": "pending_approval"
                },
                {
                    "$set": {
                        "status": "rejected",
                        "driver_response": "rejected",
                        "updated_at": datetime.now()
                    }
                }
            )
            
            # Notify hitchhiker
            hitchhiker = self.db.users.find_one({"_id": match['hitchhiker_id']})
            if hitchhiker:
                self._notify_hitchhiker_approved(hitchhiker['phone_number'], match)
        
        logger.info(f"Match {match_id} approved by driver {driver_phone}")
        return True
    
    def driver_reject(self, match_id: str, driver_phone: str) -> bool:
        """
        Driver rejects a match
        
        Args:
            match_id: Match ID
            driver_phone: Driver's phone number
            
        Returns:
            True if successful
        """
        match = self.db.matches.find_one({"match_id": match_id})
        if not match:
            logger.error(f"Match not found: {match_id}")
            return False
        
        # Verify driver
        driver = self.db.users.find_one({"phone_number": driver_phone})
        if not driver or str(driver['_id']) != str(match['driver_id']):
            logger.error(f"Driver verification failed for match {match_id}")
            return False
        
        # Update match
        self.db.matches.update_one(
            {"match_id": match_id},
            {
                "$set": {
                    "status": "rejected",
                    "driver_response": "rejected",
                    "driver_response_at": datetime.now(),
                    "updated_at": datetime.now()
                }
            }
        )
        
        logger.info(f"Match {match_id} rejected by driver {driver_phone}")
        return True
    
    def _notify_hitchhiker_approved(self, hitchhiker_phone: str, match: Dict[str, Any]):
        """Send approval notification to hitchhiker"""
        driver = self.db.users.find_one({"_id": match['driver_id']})
        ride_request = self.db.ride_requests.find_one({"_id": match['ride_request_id']})
        
        message = f"""🎉 מעולה! נהג אישר את הבקשה שלך!

🚗 נהג: {driver.get('full_name', 'נהג')}
📍 יעד: {ride_request.get('destination')}
⏰ זמן: {ride_request.get('specific_datetime') or ride_request.get('time_range')}

הנהג יצור איתך קשר בקרוב! 📲"""
        
        self.whatsapp_client.send_message(hitchhiker_phone, message)
```

### 5. Notification Service

```python
# src/services/notification_service.py
from datetime import datetime
from typing import Dict, Any, List
import logging
from bson import ObjectId

logger = logging.getLogger(__name__)

class NotificationService:
    """Service for sending notifications"""
    
    def __init__(self, db, whatsapp_client):
        self.db = db
        self.whatsapp_client = whatsapp_client
    
    def notify_drivers_new_request(self, ride_request_id: ObjectId, driver_phones: List[str]):
        """
        Notify drivers about new ride request
        
        Args:
            ride_request_id: Ride request ID
            driver_phones: List of driver phone numbers
        """
        ride_request = self.db.ride_requests.find_one({"_id": ride_request_id})
        hitchhiker = self.db.users.find_one({"_id": ride_request['requester_id']})
        
        if not ride_request or not hitchhiker:
            logger.error(f"Ride request or hitchhiker not found: {ride_request_id}")
            return
        
        message = self._build_driver_notification_message(ride_request, hitchhiker)
        
        for driver_phone in driver_phones:
            # Find match for this driver
            driver = self.db.users.find_one({"phone_number": driver_phone})
            if not driver:
                continue
            
            match = self.db.matches.find_one({
                "ride_request_id": ride_request_id,
                "driver_id": driver['_id']
            })
            
            if match:
                # Send notification with approval buttons
                buttons = [
                    {
                        "type": "reply",
                        "reply": {
                            "id": f"approve_{match['match_id']}",
                            "title": "✅ מאשר"
                        }
                    },
                    {
                        "type": "reply",
                        "reply": {
                            "id": f"reject_{match['match_id']}",
                            "title": "❌ דוחה"
                        }
                    }
                ]
                
                self.whatsapp_client.send_interactive_buttons(
                    driver_phone,
                    message,
                    buttons
                )
                
                # Update match
                self.db.matches.update_one(
                    {"_id": match['_id']},
                    {"$set": {"notification_sent_to_driver": True}}
                )
                
                # Log notification
                self._log_notification(
                    driver['_id'],
                    driver_phone,
                    "ride_request",
                    ride_request_id,
                    match['_id']
                )
    
    def _build_driver_notification_message(self, ride_request: Dict[str, Any], 
                                          hitchhiker: Dict[str, Any]) -> str:
        """Build notification message for driver"""
        return f"""🚗 בקשה חדשה לטרמפ!

👤 טרמפיסט: {hitchhiker.get('full_name', 'טרמפיסט')}
📍 מ: {ride_request.get('origin')}
🎯 ל: {ride_request.get('destination')}
⏰ זמן: {ride_request.get('specific_datetime') or ride_request.get('time_range') or 'גמיש'}

האם אתה יכול לעזור?"""
    
    def _log_notification(self, recipient_id: ObjectId, recipient_phone: str,
                         notification_type: str, ride_request_id: ObjectId = None,
                         match_id: ObjectId = None):
        """Log notification to database"""
        notification = {
            "recipient_id": recipient_id,
            "recipient_phone": recipient_phone,
            "type": notification_type,
            "ride_request_id": ride_request_id,
            "match_id": match_id,
            "status": "sent",
            "sent_at": datetime.now(),
            "created_at": datetime.now()
        }
        
        self.db.notifications.insert_one(notification)
```

---

## 🔄 Integration with Existing Code

### Update ActionExecutor

```python
# src/action_executor.py - Add to existing class
def _execute_save_hitchhiker_ride_request(self, phone_number: str, data: Dict[str, Any]):
    """Save hitchhiker ride request and trigger matching"""
    profile = self.user_db.get_user(phone_number).get('profile', {})
    
    # Get user from MongoDB
    user = self.mongo_db.users.find_one({"phone_number": phone_number})
    if not user:
        logger.error(f"User not found in MongoDB: {phone_number}")
        return
    
    # Create ride request
    ride_request = RideRequestModel.create(
        requester_id=user['_id'],
        requester_phone=phone_number,
        request_type="hitchhiker_request",
        destination=profile.get('hitchhiker_destination'),
        origin='גברעם',
        ride_timing=profile.get('ride_timing'),
        specific_datetime=profile.get('specific_datetime'),
        time_range=profile.get('time_range')
    )
    
    # Save to MongoDB
    result = self.mongo_db.ride_requests.insert_one(ride_request)
    ride_request['_id'] = result.inserted_id
    
    # Find matching drivers
    matching_service = MatchingService(self.mongo_db)
    matching_drivers = matching_service.find_matching_drivers(ride_request)
    
    # Create matches
    if matching_drivers:
        matches = matching_service.create_matches(
            ride_request['_id'],
            user['_id'],
            matching_drivers
        )
        
        # Send notifications
        notification_service = NotificationService(self.mongo_db, self.whatsapp_client)
        driver_phones = [d['driver_phone'] for d in matching_drivers]
        notification_service.notify_drivers_new_request(ride_request['_id'], driver_phones)
    
    logger.info(f"Saved ride request and created {len(matching_drivers)} matches")
```

---

## 📦 Dependencies

Add to `requirements.txt`:
```
pymongo==4.6.0
```

---

## 🚀 Next Steps

1. **Setup MongoDB** - Install and configure MongoDB
2. **Create modules** - Implement all services
3. **Migration script** - Migrate existing JSON data
4. **Testing** - Test matching and approval flows
5. **Integration** - Integrate with existing code
6. **Deployment** - Deploy and monitor



