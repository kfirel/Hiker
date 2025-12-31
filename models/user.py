"""
User data models with type safety using Pydantic
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class DriverData(BaseModel):
    """Data specific to drivers"""
    origin: str = "גברעם"
    destination: str
    days: List[str] = Field(default_factory=list)
    departure_time: Optional[str] = None
    return_time: Optional[str] = None
    available_seats: int = 3
    notes: str = ""


class HitchhikerData(BaseModel):
    """Data specific to hitchhikers"""
    origin: str = "גברעם"
    destination: str
    travel_date: Optional[str] = None
    departure_time: Optional[str] = None
    flexibility: str = "flexible"
    notes: str = ""


class ChatMessage(BaseModel):
    """Individual chat message"""
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: str


class User(BaseModel):
    """Complete user model"""
    phone_number: str
    role: Optional[str] = None
    notification_level: str = "all"
    driver_data: Optional[DriverData] = None
    hitchhiker_data: Optional[HitchhikerData] = None
    created_at: str
    last_seen: str
    chat_history: List[ChatMessage] = Field(default_factory=list)
    
    class Config:
        json_schema_extra = {
            "example": {
                "phone_number": "972501234567",
                "role": "driver",
                "notification_level": "all",
                "driver_data": {
                    "destination": "תל אביב",
                    "days": ["Sunday", "Monday"],
                    "departure_time": "09:00"
                },
                "created_at": "2025-01-01T10:00:00",
                "last_seen": "2025-01-01T10:00:00"
            }
        }

