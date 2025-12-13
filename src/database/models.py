"""
Database models for MongoDB collections
"""

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
            "user_type": None,  # "hitchhiker" | "driver" | "both"
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
        if not db.is_connected():
            return
        db.get_collection("users").update_one(
            {"phone_number": phone_number},
            {"$set": {"last_active": datetime.now()}}
        )


class RoutineModel:
    """Routine data model"""
    
    @staticmethod
    def create(
        user_id: ObjectId,
        phone_number: str,
        destination: str,
        days: list,  # Array of day strings: ["א", "ב", "ג", "ד", "ה"]
        departure_time_start: datetime = None,
        departure_time_end: datetime = None,
        return_time_start: datetime = None,
        return_time_end: datetime = None
    ) -> Dict[str, Any]:
        """Create new routine document with time ranges"""
        return {
            "user_id": user_id,
            "phone_number": phone_number,  # denormalized for quick access
            "destination": destination,
            "days": days,  # Array: ["א", "ב", "ג", "ד", "ה"] | ["ב", "ד"] | etc.
            "departure_time_start": departure_time_start,  # datetime object
            "departure_time_end": departure_time_end,  # datetime object
            "return_time_start": return_time_start,  # datetime object
            "return_time_end": return_time_end,  # datetime object
            "is_active": True,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }


class RideRequestModel:
    """Ride request data model"""
    
    @staticmethod
    def create(
        requester_id: ObjectId,
        requester_phone: str,
        request_type: str,
        destination: str,
        origin: str = "גברעם",
        start_time_range: datetime = None,
        end_time_range: datetime = None
    ) -> Dict[str, Any]:
        """Create new ride request with time range"""
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
            "start_time_range": start_time_range,  # datetime object
            "end_time_range": end_time_range,  # datetime object
            "status": "pending",
            # Matched drivers array (replaces matches collection)
            "matched_drivers": [],  # Array of {driver_id, driver_phone, status, driver_response_at, notification_sent_to_driver, auto_approve, matched_at}
            "approval_notification_driver_count": 0,
            "approval_notification_sending": False,
            "found_at": None,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "expires_at": expires_at
        }


# MatchModel removed - matches are now stored as matched_drivers array in ride_requests
# Use helper function to create matched_driver entry instead
def create_matched_driver_entry(
    driver_id: ObjectId,
    driver_phone: str,
    status: str = "pending_approval",
    auto_approve: bool = False
) -> Dict[str, Any]:
    """Create a matched driver entry for ride_requests.matched_drivers array"""
    match_id = f"MATCH_{uuid.uuid4().hex[:12]}"  # Generate match_id for button identification
    return {
        "match_id": match_id,  # Used for button identification (approve_MATCH_xxx)
        "driver_id": driver_id,
        "driver_phone": driver_phone,
        "status": status,  # "pending_approval" | "approved" | "rejected"
        "driver_response": None,  # "approved" | "rejected" | None
        "driver_response_at": None,
        "notification_sent_to_driver": False,
        "auto_approve": auto_approve,
        "matched_at": datetime.now()
    }



