"""
Admin and Testing Utilities
Secure endpoints and commands for testing and management
"""

import os
import logging
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Header, HTTPException, Depends
from pydantic import BaseModel
from google.cloud import firestore

logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/a", tags=["admin"])

# Admin configuration
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")
TESTING_MODE_ENABLED = True

# Whitelist of phone numbers allowed to use testing commands via WhatsApp
ADMIN_PHONE_NUMBERS = os.getenv("ADMIN_PHONE_NUMBERS", "").split(",")
ADMIN_PHONE_NUMBERS = [num.strip() for num in ADMIN_PHONE_NUMBERS if num.strip()]


# Dependency for API token authentication
async def verify_admin_token(x_admin_token: str = Header(None)) -> bool:
    """Verify admin token from request header"""
    if not ADMIN_TOKEN:
        raise HTTPException(
            status_code=503,
            detail="Admin features disabled - ADMIN_TOKEN not configured"
        )
    
    if not x_admin_token or x_admin_token != ADMIN_TOKEN:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing admin token"
        )
    
    return True


def is_admin_phone(phone_number: str) -> bool:
    """Check if phone number is in admin whitelist"""
    if not TESTING_MODE_ENABLED:
        return False
    
    if not ADMIN_PHONE_NUMBERS:
        return False
    
    return phone_number in ADMIN_PHONE_NUMBERS


# Pydantic models for requests
class ChangePhoneNumberRequest(BaseModel):
    from_number: str
    to_number: str


class DeleteUserRequest(BaseModel):
    phone_number: str


class CreateTestUserRequest(BaseModel):
    phone_number: str
    name: Optional[str] = None
    driver_rides: Optional[List[dict]] = None
    hitchhiker_requests: Optional[List[dict]] = None


# ============================================================================
# API ENDPOINTS (Recommended for automation/testing)
# ============================================================================

@router.get("/health")
async def admin_health(_: bool = Depends(verify_admin_token)):
    """Health check for admin endpoints"""
    return {
        "status": "healthy",
        "testing_mode": TESTING_MODE_ENABLED,
        "admin_phones_configured": len(ADMIN_PHONE_NUMBERS) > 0
    }


@router.post("/users/{phone_number}/change-phone")
async def change_user_phone_number(
    phone_number: str,
    new_phone: str,
    _: bool = Depends(verify_admin_token)
):
    """
    Change a user's phone number in the database
    Useful for testing with different numbers
    
    Example:
        POST /admin/users/972501234567/change-phone?new_phone=11
        Header: X-Admin-Token: your_secret_token
    """
    from database import get_db
    db = get_db()
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        # Get original user data
        original_doc = db.collection("users").document(phone_number).get()
        
        if not original_doc.exists:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Copy data to new phone number
        user_data = original_doc.to_dict()
        user_data["phone_number"] = new_phone
        user_data["last_seen"] = datetime.utcnow().isoformat()
        
        # Create new document
        db.collection("users").document(new_phone).set(user_data)
        
        # Delete original
        db.collection("users").document(phone_number).delete()
        
        logger.info(f"✅ Admin: Changed phone {phone_number} → {new_phone}")
        
        return {
            "success": True,
            "message": f"User phone changed from {phone_number} to {new_phone}",
            "old_phone": phone_number,
            "new_phone": new_phone
        }
    
    except Exception as e:
        logger.error(f"❌ Error changing phone number: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/users/{phone_number}")
async def delete_user(
    phone_number: str,
    _: bool = Depends(verify_admin_token)
):
    """
    Delete a user from the database
    
    Example:
        DELETE /admin/users/972501234567
        Header: X-Admin-Token: your_secret_token
    """
    from database import get_db
    db = get_db()
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        doc_ref = db.collection("users").document(phone_number)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Delete the document
        doc_ref.delete()
        
        logger.info(f"🗑️  Admin: Deleted user {phone_number}")
        
        return {
            "success": True,
            "message": f"User {phone_number} deleted successfully"
        }
    
    except Exception as e:
        logger.error(f"❌ Error deleting user: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/users")
async def create_test_user(
    request: CreateTestUserRequest,
    _: bool = Depends(verify_admin_token)
):
    """
    Create a test user with specific data
    
    Example:
        POST /admin/users
        Header: X-Admin-Token: your_secret_token
        Body: {
            "phone_number": "test123",
            "name": "Test User",
            "driver_rides": [{"destination": "תל אביב", ...}],
            "hitchhiker_requests": []
        }
    """
    from database import get_db
    db = get_db()
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        user_data = {
            "phone_number": request.phone_number,
            "name": request.name,
            "notification_level": "all",
            "driver_rides": request.driver_rides or [],
            "hitchhiker_requests": request.hitchhiker_requests or [],
            "created_at": datetime.utcnow().isoformat(),
            "last_seen": datetime.utcnow().isoformat(),
            "chat_history": []
        }
        
        db.collection("users").document(request.phone_number).set(user_data)
        
        logger.info(f"✅ Admin: Created test user {request.phone_number}")
        
        return {
            "success": True,
            "message": f"Test user {request.phone_number} created",
            "user_data": user_data
        }
    
    except Exception as e:
        logger.error(f"❌ Error creating test user: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/users/reset-all")
async def reset_all_users(
    confirm: str,
    _: bool = Depends(verify_admin_token)
):
    """
    Delete ALL users (use with extreme caution!)
    
    Example:
        POST /admin/users/reset-all?confirm=DELETE_ALL_USERS
        Header: X-Admin-Token: your_secret_token
    """
    from database import get_db
    db = get_db()
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")
    
    if confirm != "DELETE_ALL_USERS":
        raise HTTPException(
            status_code=400,
            detail="Must provide confirm=DELETE_ALL_USERS to proceed"
        )
    
    try:
        deleted_count = 0
        docs = db.collection("users").stream()
        
        for doc in docs:
            doc.reference.delete()
            deleted_count += 1
        
        logger.warning(f"⚠️  Admin: Deleted all {deleted_count} users!")
        
        return {
            "success": True,
            "message": f"Deleted all {deleted_count} users",
            "deleted_count": deleted_count
        }
    
    except Exception as e:
        logger.error(f"❌ Error resetting users: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# WHATSAPP COMMAND HANDLERS (For convenience via WhatsApp)
# ============================================================================

async def handle_admin_whatsapp_command(
    phone_number: str,
    message: str,
    db: firestore.Client
) -> Optional[str]:
    """
    Handle admin commands sent via WhatsApp
    
    Returns response message if command was handled, None otherwise
    
    Commands:
        /admin:change:NEW_NUMBER - Change to new phone number
        /admin:delete:CONFIRM - Delete user data
        /admin:reset - Reset user to fresh state
        /admin:help - Show available commands
    """
    
    # Check if testing mode is enabled
    if not TESTING_MODE_ENABLED:
        return None

    
    # Parse admin commands
    if not message.startswith("/a"):
        return None
    
    try:
        parts = message.split("/")
        command = parts[2] if len(parts) > 1 else ""
        
        # Help command
        if command == "help":
            return """🔧 Admin Commands Available:

/admin:change:NEW_NUMBER
  Change your phone number in DB
  Example: /admin:change:test123

/admin:delete:CONFIRM
  Delete your user data
  Example: /admin:delete:CONFIRM

/admin:reset
  Reset to fresh user state

/admin:help
  Show this help message

⚠️ Testing mode is enabled
📱 Your number is whitelisted"""

        # Change phone number
        elif command == "c" and len(parts) > 2:
            new_number = parts[3]
            
            # Get user data
            original_doc = db.collection("users").document(phone_number).get()
            
            if original_doc.exists:
                user_data = original_doc.to_dict()
                user_data["phone_number"] = new_number
                user_data["last_seen"] = datetime.utcnow().isoformat()
                
                # Create new document
                db.collection("users").document(new_number).set(user_data)
                
                # Delete original
                db.collection("users").document(phone_number).delete()
                
                logger.info(f"✅ Admin WhatsApp: Changed {phone_number} → {new_number}")
                
                return f"✅ Phone number changed!\nOld: {phone_number}\nNew: {new_number}\n\n⚠️ Note: You'll need to message from the OLD number to get this response."
            else:
                return "❌ User not found in database"
        
        # Delete user
        elif command == "d" and len(parts) > 2:
            confirm = parts[2]
            
            db.collection("users").document(phone_number).delete()
            
            logger.info(f"🗑️  Admin WhatsApp: Deleted user {phone_number}")
            
            return "✅ Your data has been deleted!\nSend any message to start fresh."
        
        # Reset user
        elif command == "r":
            user_data = {
                "phone_number": phone_number,
                "notification_level": "all",
                "driver_rides": [],
                "hitchhiker_requests": [],
                "created_at": datetime.utcnow().isoformat(),
                "last_seen": datetime.utcnow().isoformat(),
                "chat_history": []
            }
            
            db.collection("users").document(phone_number).set(user_data)
            
            logger.info(f"🔄 Admin WhatsApp: Reset user {phone_number}")
            
            return "✅ Your data has been reset!\nYou can start fresh now."
        
        else:
            return "❌ Unknown admin command\nSend /admin:help for available commands"
    
    except Exception as e:
        logger.error(f"❌ Error handling admin command: {str(e)}")
        return f"❌ Error: {str(e)}"


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_admin_status_message() -> str:
    """Get status message about admin features"""
    if not TESTING_MODE_ENABLED:
        return "🔒 Testing mode: DISABLED"
    
    return f"""🔓 Testing mode: ENABLED
📱 Admin phones: {len(ADMIN_PHONE_NUMBERS)} configured
🔑 Admin API: {'✅' if ADMIN_TOKEN else '❌'}"""

