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
        days: str,
        departure_time: str,
        return_time: str
    ) -> Dict[str, Any]:
        """Create new routine document"""
        return {
            "user_id": user_id,
            "phone_number": phone_number,  # denormalized for quick access
            "destination": destination,
            "days": days,  # "א-ה" | "ב,ד" | etc.
            "departure_time": departure_time,  # "07:00"
            "return_time": return_time,  # "18:00"
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


