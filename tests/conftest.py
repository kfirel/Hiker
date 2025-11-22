"""
Pytest configuration and fixtures
"""

import pytest
import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.user_database_mongo import UserDatabaseMongo
from src.database.mongodb_client import MongoDBClient
from src.conversation_engine import ConversationEngine
from src.user_logger import UserLogger
from tests.mock_whatsapp_client import MockWhatsAppClient

@pytest.fixture(scope="function")
def temp_db(mock_mongo_client):
    """Create a temporary MongoDB database for each test"""
    db = UserDatabaseMongo(mongo_client=mock_mongo_client)
    yield db

@pytest.fixture(scope="function")
def temp_logs_dir():
    """Create a temporary logs directory for each test"""
    # Use the project's logs directory instead of temp, so logs persist
    project_root = Path(__file__).parent.parent
    logs_dir = project_root / 'logs'
    logs_dir.mkdir(exist_ok=True)
    
    yield str(logs_dir)
    
    # Don't cleanup - keep logs for inspection

@pytest.fixture(scope="function")
def mock_whatsapp_client(temp_logs_dir):
    """Create a mock WhatsApp client with user logger"""
    user_logger = UserLogger(logs_dir=temp_logs_dir)
    return MockWhatsAppClient(user_logger=user_logger)

@pytest.fixture(scope="function")
def conversation_engine(temp_db, temp_logs_dir):
    """Create a conversation engine with temporary database and logs"""
    user_logger = UserLogger(logs_dir=temp_logs_dir)
    engine = ConversationEngine(user_db=temp_db, user_logger=user_logger)
    return engine

@pytest.fixture(scope="function")
def test_phone_number():
    """Generate a unique test phone number"""
    import random
    return f"test_{random.randint(100000000, 999999999)}"

@pytest.fixture(scope="function")
def mock_mongo_client():
    """Create a MongoDB mock client using mongomock"""
    try:
        import mongomock
        # Create a mock MongoDB client
        mock_client = mongomock.MongoClient()
        # Create a mock MongoDBClient wrapper
        mock_mongo = MongoDBClient.__new__(MongoDBClient)
        mock_mongo.client = mock_client
        mock_mongo.db_name = "test_hiker_db"
        mock_mongo.db = mock_client[mock_mongo.db_name]
        mock_mongo.connection_string = "mongomock://localhost"
        # Create indexes (handle errors gracefully for mongomock)
        try:
            mock_mongo._create_indexes()
        except Exception:
            pass  # mongomock may not support all index operations
        yield mock_mongo
        # Cleanup - mongomock doesn't need explicit cleanup
    except ImportError:
        pytest.skip("mongomock not installed - run: pip install mongomock")

@pytest.fixture(scope="function")
def mongo_db(mock_mongo_client):
    """Create a MongoDB-based user database for integration tests"""
    db = UserDatabaseMongo(mongo_client=mock_mongo_client)
    yield db

@pytest.fixture(scope="function")
def integration_conversation_engine(mongo_db, temp_logs_dir):
    """Create a conversation engine with MongoDB for integration tests"""
    user_logger = UserLogger(logs_dir=temp_logs_dir)
    engine = ConversationEngine(user_db=mongo_db, user_logger=user_logger)
    
    # Services will be initialized in the test itself with the mock WhatsApp client
    return engine

