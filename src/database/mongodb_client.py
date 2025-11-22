"""
MongoDB connection manager
"""

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


class MongoDBClient:
    """MongoDB connection manager"""
    
    def __init__(self, connection_string: Optional[str] = None, db_name: str = "hiker_db"):
        """
        Initialize MongoDB client
        
        Args:
            connection_string: MongoDB connection string (defaults to env var)
            db_name: Database name
        """
        # Get connection string from env if not provided
        if not connection_string:
            connection_string = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
        
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
            logger.info(f"✅ Connected to MongoDB: {self.db_name}")
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.warning(f"⚠️ MongoDB connection failed: {e}")
            logger.warning("⚠️ Falling back to JSON file storage")
            self.client = None
            self.db = None
    
    def is_connected(self) -> bool:
        """Check if MongoDB is connected"""
        return self.client is not None and self.db is not None
    
    def _create_indexes(self):
        """Create necessary indexes"""
        if not self.is_connected():
            return
        
        try:
            # Users indexes
            self.db.users.create_index("phone_number", unique=True)
            self.db.users.create_index("user_type")
            self.db.users.create_index("home_settlement")
            
            # Routines indexes
            self.db.routines.create_index("user_id")
            self.db.routines.create_index([("destination", 1), ("days", 1), ("is_active", 1)])
            self.db.routines.create_index("is_active")
            
            # Ride requests indexes
            self.db.ride_requests.create_index("request_id", unique=True)
            self.db.ride_requests.create_index("requester_id")
            self.db.ride_requests.create_index([("status", 1), ("destination", 1)])
            self.db.ride_requests.create_index("expires_at", expireAfterSeconds=0)  # TTL index
            
            # Matches indexes
            self.db.matches.create_index([("ride_request_id", 1), ("status", 1)])
            self.db.matches.create_index("driver_id")
            self.db.matches.create_index("hitchhiker_id")
            self.db.matches.create_index("match_id", unique=True)
            
            # Notifications indexes
            self.db.notifications.create_index([("recipient_id", 1), ("status", 1)])
            self.db.notifications.create_index("created_at")
            
            logger.info("✅ MongoDB indexes created")
        except Exception as e:
            logger.error(f"❌ Failed to create indexes: {e}")
    
    def get_collection(self, collection_name: str):
        """Get a collection"""
        if not self.is_connected():
            raise ConnectionError("MongoDB is not connected")
        return self.db[collection_name]
    
    def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")


