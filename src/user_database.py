"""
User database module for storing user data and conversation state
Using JSON file for simplicity (can be replaced with real database)
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, Optional

class UserDatabase:
    """Simple JSON-based user database"""
    
    def __init__(self, db_file='user_data.json'):
        self.db_file = db_file
        self._load_database()
    
    def _load_database(self):
        """Load database from file"""
        if os.path.exists(self.db_file):
            with open(self.db_file, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
        else:
            self.data = {'users': {}}
    
    def _save_database(self):
        """Save database to file"""
        with open(self.db_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
    
    def user_exists(self, phone_number: str) -> bool:
        """Check if user exists in database"""
        return phone_number in self.data['users']
    
    def get_user(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """Get user data"""
        return self.data['users'].get(phone_number)
    
    def create_user(self, phone_number: str) -> Dict[str, Any]:
        """Create new user"""
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
        self.data['users'][phone_number] = user_data
        self._save_database()
        return user_data
    
    def update_user(self, phone_number: str, updates: Dict[str, Any]):
        """Update user data"""
        if phone_number not in self.data['users']:
            self.create_user(phone_number)
        
        user = self.data['users'][phone_number]
        
        # Deep update
        for key, value in updates.items():
            if key in user and isinstance(user[key], dict) and isinstance(value, dict):
                user[key].update(value)
            else:
                user[key] = value
        
        self._save_database()
    
    def get_user_state(self, phone_number: str) -> str:
        """Get user's current conversation state"""
        user = self.get_user(phone_number)
        if user:
            return user['state']['current_state']
        return 'initial'
    
    def set_user_state(self, phone_number: str, state: str, context: Dict[str, Any] = None, add_to_history: bool = True):
        """Set user's conversation state
        
        Args:
            phone_number: User's phone number
            state: New state ID
            context: Optional context data
            add_to_history: Whether to add this state to history (default: True)
        """
        if not self.user_exists(phone_number):
            self.create_user(phone_number)
        
        user = self.data['users'][phone_number]
        current_state = user['state']['current_state']
        
        # Only add to history if state actually changed and add_to_history is True
        if add_to_history and current_state != state:
            # Add current state to history before changing
            user['state']['history'].append({
                'state': current_state,
                'timestamp': datetime.now().isoformat(),
                'context': user['state']['context'].copy() if user['state']['context'] else {}
            })
            
            # Limit history to last 10 states to prevent memory issues
            if len(user['state']['history']) > 10:
                user['state']['history'] = user['state']['history'][-10:]
        
        user['state']['current_state'] = state
        
        if context:
            user['state']['context'].update(context)
        
        self._save_database()
    
    def get_state_history(self, phone_number: str) -> list:
        """Get user's state history
        
        Args:
            phone_number: User's phone number
            
        Returns:
            List of state history entries
        """
        user = self.get_user(phone_number)
        if user:
            return user.get('state', {}).get('history', [])
        return []
    
    def pop_state_history(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """Pop the last state from history (for go_back functionality)
        
        Args:
            phone_number: User's phone number
            
        Returns:
            Last state entry or None if history is empty
        """
        user = self.get_user(phone_number)
        if user and user.get('state', {}).get('history'):
            history = user['state']['history']
            if history:
                popped = history.pop()
                self._save_database()
                return popped
        return None
    
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
        
        user = self.data['users'][phone_number]
        if value is None and key in user['state']['context']:
            # Remove key if value is None
            del user['state']['context'][key]
        else:
            user['state']['context'][key] = value
        
        self._save_database()
    
    def save_to_profile(self, phone_number: str, key: str, value: Any):
        """Save data to user profile"""
        if not self.user_exists(phone_number):
            self.create_user(phone_number)
        
        self.data['users'][phone_number]['profile'][key] = value
        self._save_database()
    
    def get_profile_value(self, phone_number: str, key: str, default=None) -> Any:
        """Get value from user profile"""
        user = self.get_user(phone_number)
        if user:
            return user['profile'].get(key, default)
        return default
    
    def complete_registration(self, phone_number: str):
        """Mark user as registered"""
        if self.user_exists(phone_number):
            self.data['users'][phone_number]['registered'] = True
            self.data['users'][phone_number]['registered_at'] = datetime.now().isoformat()
            self._save_database()
    
    def is_registered(self, phone_number: str) -> bool:
        """Check if user is registered"""
        user = self.get_user(phone_number)
        return user and user.get('registered', False)
    
    def add_ride_request(self, phone_number: str, request_data: Dict[str, Any]):
        """Add ride request"""
        if not self.user_exists(phone_number):
            self.create_user(phone_number)
        
        request_data['timestamp'] = datetime.now().isoformat()
        request_data['status'] = 'active'
        
        self.data['users'][phone_number]['ride_requests'].append(request_data)
        self._save_database()
    
    def add_routine(self, phone_number: str, routine_data: Dict[str, Any]):
        """Add driving routine"""
        if not self.user_exists(phone_number):
            self.create_user(phone_number)
        
        routine_data['created_at'] = datetime.now().isoformat()
        
        self.data['users'][phone_number]['routines'].append(routine_data)
        self._save_database()
    
    def delete_user_data(self, phone_number: str):
        """Delete all user data"""
        if phone_number in self.data['users']:
            del self.data['users'][phone_number]
            self._save_database()
            return True
        return False
    
    def reset_user_state(self, phone_number: str):
        """Reset user to initial state"""
        if self.user_exists(phone_number):
            self.data['users'][phone_number]['state'] = {
                'current_state': 'initial',
                'context': {},
                'history': []
            }
            self._save_database()

