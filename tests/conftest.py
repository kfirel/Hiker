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

from src.user_database import UserDatabase
from src.conversation_engine import ConversationEngine
from src.user_logger import UserLogger
from tests.mock_whatsapp_client import MockWhatsAppClient

@pytest.fixture(scope="function")
def temp_db():
    """Create a temporary database file for each test"""
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
    # Write initial empty JSON structure
    temp_file.write('{"users": {}}')
    temp_file.close()
    
    db = UserDatabase(temp_file.name)
    yield db
    
    # Cleanup
    if os.path.exists(temp_file.name):
        os.remove(temp_file.name)

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
def mock_whatsapp_client():
    """Create a mock WhatsApp client"""
    return MockWhatsAppClient()

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

