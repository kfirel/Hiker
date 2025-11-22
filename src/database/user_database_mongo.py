"""
MongoDB-based user database implementation
Hybrid approach: Uses MongoDB if available, falls back to JSON
"""

import json
import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from bson import ObjectId

from .mongodb_client import MongoDBClient
from .models import UserModel, RoutineModel

logger = logging.getLogger(__name__)


class UserDatabaseMongo:
    """MongoDB-based user database with JSON fallback"""
    
    def __init__(self, db_file='user_data.json', mongo_client: Optional[MongoDBClient] = None):
        """
        Initialize database
        
        Args:
            db_file: JSON file path for fallback
            mongo_client: Optional MongoDB client (will create if not provided)
        """
        self.db_file = db_file
        self._load_json_database()  # Always load JSON as fallback
        
        # Initialize MongoDB client
        if mongo_client:
            self.mongo = mongo_client
        else:
            try:
                from src.config import Config
                self.mongo = MongoDBClient(
                    connection_string=Config.MONGODB_URI,
                    db_name=Config.MONGODB_DB_NAME
                )
            except Exception as e:
                logger.warning(f"Failed to initialize MongoDB: {e}")
                self.mongo = None
        
        self._use_mongo = self.mongo and self.mongo.is_connected()
        
        if self._use_mongo:
            logger.info("✅ Using MongoDB for data storage")
        else:
            logger.info("⚠️ Using JSON file for data storage (MongoDB not available)")
    
    def _load_json_database(self):
        """Load JSON database as fallback"""
        if os.path.exists(self.db_file):
            with open(self.db_file, 'r', encoding='utf-8') as f:
                self.json_data = json.load(f)
        else:
            self.json_data = {'users': {}}
    
    def _save_json_database(self):
        """Save JSON database"""
        with open(self.db_file, 'w', encoding='utf-8') as f:
            json.dump(self.json_data, f, ensure_ascii=False, indent=2)
    
    def _get_user_from_mongo(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """Get user from MongoDB"""
        if not self._use_mongo:
            return None
        
        user = self.mongo.get_collection("users").find_one({"phone_number": phone_number})
        if user:
            # Convert ObjectId to string for compatibility
            user['_id'] = str(user['_id'])
        return user
    
    def _get_user_from_json(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """Get user from JSON"""
        return self.json_data['users'].get(phone_number)
    
    def user_exists(self, phone_number: str) -> bool:
        """Check if user exists"""
        if self._use_mongo:
            return self.mongo.get_collection("users").count_documents({"phone_number": phone_number}) > 0
        return phone_number in self.json_data['users']
    
    def get_user(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """Get user data"""
        if self._use_mongo:
            user = self._get_user_from_mongo(phone_number)
            if user:
                return self._convert_mongo_user_to_json_format(user)
        
        return self._get_user_from_json(phone_number)
    
    def _convert_mongo_user_to_json_format(self, mongo_user: Dict[str, Any]) -> Dict[str, Any]:
        """Convert MongoDB user format to JSON format for compatibility"""
        return {
            "phone_number": mongo_user.get("phone_number"),
            "created_at": mongo_user.get("created_at").isoformat() if isinstance(mongo_user.get("created_at"), datetime) else mongo_user.get("created_at"),
            "registered": mongo_user.get("is_registered", False),
            "profile": {
                "whatsapp_name": mongo_user.get("whatsapp_name"),
                "full_name": mongo_user.get("full_name"),
                "home_settlement": mongo_user.get("home_settlement"),
                "user_type": mongo_user.get("user_type"),
                "default_destination": mongo_user.get("default_destination"),
                "alert_preference": mongo_user.get("alert_preference"),
                "share_name_with_hitchhiker": mongo_user.get("share_name_with_hitchhiker"),
            },
            "state": {
                "current_state": mongo_user.get("current_state", "initial"),
                "context": mongo_user.get("state_context", {}),
                "history": mongo_user.get("state_history", [])
            },
            "preferences": {},
            "ride_requests": [],  # Will be loaded separately if needed
            "routines": []  # Will be loaded separately if needed
        }
    
    def create_user(self, phone_number: str) -> Dict[str, Any]:
        """Create new user"""
        if self._use_mongo:
            # Check if user already exists
            if self.user_exists(phone_number):
                return self.get_user(phone_number)
            
            user_doc = UserModel.create(phone_number)
            result = self.mongo.get_collection("users").insert_one(user_doc)
            user_doc['_id'] = str(result.inserted_id)
            return self._convert_mongo_user_to_json_format(user_doc)
        
        # JSON fallback
        user_data = {
            'phone_number': phone_number,
            'created_at': datetime.now().isoformat(),
            'registered': False,
            'profile': {},
            'state': {
                'current_state': 'initial',
                'context': {},
                'history': []
            },
            'preferences': {},
            'ride_requests': [],
            'routines': []
        }
        self.json_data['users'][phone_number] = user_data
        self._save_json_database()
        return user_data
    
    def update_user(self, phone_number: str, updates: Dict[str, Any]):
        """Update user data"""
        if not self.user_exists(phone_number):
            self.create_user(phone_number)
        
        if self._use_mongo:
            # Convert updates to MongoDB format
            mongo_updates = {}
            if 'profile' in updates:
                # Merge profile fields
                for key, value in updates['profile'].items():
                    mongo_updates[key] = value
            if 'state' in updates:
                if 'current_state' in updates['state']:
                    mongo_updates['current_state'] = updates['state']['current_state']
                if 'context' in updates['state']:
                    mongo_updates['state_context'] = updates['state']['context']
            
            # Update other fields
            for key, value in updates.items():
                if key not in ['profile', 'state']:
                    mongo_updates[key] = value
            
            self.mongo.get_collection("users").update_one(
                {"phone_number": phone_number},
                {"$set": mongo_updates}
            )
        else:
            # JSON fallback
            user = self.json_data['users'][phone_number]
            for key, value in updates.items():
                if key in user and isinstance(user[key], dict) and isinstance(value, dict):
                    user[key].update(value)
                else:
                    user[key] = value
            self._save_json_database()
    
    def get_user_state(self, phone_number: str) -> str:
        """Get user's current conversation state"""
        user = self.get_user(phone_number)
        if user:
            return user['state']['current_state']
        return 'initial'
    
    def set_user_state(self, phone_number: str, state: str, context: Dict[str, Any] = None, add_to_history: bool = True):
        """Set user's conversation state"""
        if not self.user_exists(phone_number):
            self.create_user(phone_number)
        
        if self._use_mongo:
            user = self.mongo.get_collection("users").find_one({"phone_number": phone_number})
            if user:
                current_state = user.get('current_state', 'initial')
                
                # Add to history if needed
                if add_to_history and current_state != state:
                    history_entry = {
                        'state': current_state,
                        'timestamp': datetime.now().isoformat(),
                        'context': user.get('state_context', {}).copy()
                    }
                    update_doc = {
                        "$set": {
                            "current_state": state,
                            "state_context": context or {}
                        },
                        "$push": {"state_history": {"$each": [history_entry], "$slice": -10}}
                    }
                    self.mongo.get_collection("users").update_one(
                        {"phone_number": phone_number},
                        update_doc
                    )
                else:
                    update = {"$set": {"current_state": state}}
                    if context:
                        update["$set"]["state_context"] = context
                    self.mongo.get_collection("users").update_one(
                        {"phone_number": phone_number},
                        update
                    )
        else:
            # JSON fallback
            user = self.json_data['users'][phone_number]
            current_state = user['state']['current_state']
            
            if add_to_history and current_state != state:
                user['state']['history'].append({
                    'state': current_state,
                    'timestamp': datetime.now().isoformat(),
                    'context': user['state']['context'].copy() if user['state']['context'] else {}
                })
                if len(user['state']['history']) > 10:
                    user['state']['history'] = user['state']['history'][-10:]
            
            user['state']['current_state'] = state
            if context:
                user['state']['context'].update(context)
            self._save_json_database()
    
    def get_user_context(self, phone_number: str) -> Dict[str, Any]:
        """Get user's conversation context"""
        user = self.get_user(phone_number)
        if user:
            return user['state'].get('context', {})
        return {}
    
    def update_context(self, phone_number: str, key: str, value: Any):
        """Update a specific key in user's context"""
        if not self.user_exists(phone_number):
            self.create_user(phone_number)
        
        if self._use_mongo:
            if value is None:
                self.mongo.get_collection("users").update_one(
                    {"phone_number": phone_number},
                    {"$unset": {f"state_context.{key}": ""}}
                )
            else:
                self.mongo.get_collection("users").update_one(
                    {"phone_number": phone_number},
                    {"$set": {f"state_context.{key}": value}}
                )
        else:
            user = self.json_data['users'][phone_number]
            if value is None and key in user['state']['context']:
                del user['state']['context'][key]
            else:
                user['state']['context'][key] = value
            self._save_json_database()
    
    def save_to_profile(self, phone_number: str, key: str, value: Any):
        """Save data to user profile"""
        if not self.user_exists(phone_number):
            self.create_user(phone_number)
        
        if self._use_mongo:
            self.mongo.get_collection("users").update_one(
                {"phone_number": phone_number},
                {"$set": {key: value}}
            )
        else:
            self.json_data['users'][phone_number]['profile'][key] = value
            self._save_json_database()
    
    def get_profile_value(self, phone_number: str, key: str, default=None) -> Any:
        """Get value from user profile"""
        user = self.get_user(phone_number)
        if user:
            return user['profile'].get(key, default)
        return default
    
    def complete_registration(self, phone_number: str):
        """Mark user as registered"""
        if self._use_mongo:
            self.mongo.get_collection("users").update_one(
                {"phone_number": phone_number},
                {
                    "$set": {
                        "is_registered": True,
                        "registered_at": datetime.now()
                    }
                }
            )
        else:
            if self.user_exists(phone_number):
                self.json_data['users'][phone_number]['registered'] = True
                self.json_data['users'][phone_number]['registered_at'] = datetime.now().isoformat()
                self._save_json_database()
    
    def is_registered(self, phone_number: str) -> bool:
        """Check if user is registered"""
        user = self.get_user(phone_number)
        if user:
            return user.get('registered', False) or user.get('is_registered', False)
        return False
    
    def add_ride_request(self, phone_number: str, request_data: Dict[str, Any]):
        """Add ride request (for now, just log - will be implemented in matching service)"""
        logger.info(f"Ride request added for {phone_number}: {request_data}")
        # TODO: Implement proper ride request storage in MongoDB
    
    def add_routine(self, phone_number: str, routine_data: Dict[str, Any]):
        """Add driving routine with time ranges"""
        if not self.user_exists(phone_number):
            self.create_user(phone_number)
        
        if self._use_mongo:
            user = self.mongo.get_collection("users").find_one({"phone_number": phone_number})
            if user:
                routine_doc = RoutineModel.create(
                    user_id=ObjectId(user['_id']) if isinstance(user['_id'], str) else user['_id'],
                    phone_number=phone_number,
                    destination=routine_data.get('routine_destination'),
                    days=routine_data.get('routine_days'),
                    departure_time_start=routine_data.get('departure_time_start'),
                    departure_time_end=routine_data.get('departure_time_end'),
                    return_time_start=routine_data.get('return_time_start'),
                    return_time_end=routine_data.get('return_time_end')
                )
                self.mongo.get_collection("routines").insert_one(routine_doc)
        else:
            routine_data['created_at'] = datetime.now().isoformat()
            self.json_data['users'][phone_number]['routines'].append(routine_data)
            self._save_json_database()
    
    def delete_user_data(self, phone_number: str):
        """Delete all user data"""
        if self._use_mongo:
            self.mongo.get_collection("users").delete_one({"phone_number": phone_number})
            self.mongo.get_collection("routines").delete_many({"phone_number": phone_number})
        else:
            if phone_number in self.json_data['users']:
                del self.json_data['users'][phone_number]
                self._save_json_database()
                return True
        return False
    
    def reset_user_state(self, phone_number: str):
        """Reset user to initial state"""
        if self._use_mongo:
            self.mongo.get_collection("users").update_one(
                {"phone_number": phone_number},
                {
                    "$set": {
                        "current_state": "initial",
                        "state_context": {},
                        "state_history": []
                    }
                }
            )
        else:
            if self.user_exists(phone_number):
                self.json_data['users'][phone_number]['state'] = {
                    'current_state': 'initial',
                    'context': {},
                    'history': []
                }
                self._save_json_database()

