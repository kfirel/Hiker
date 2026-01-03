"""
Admin and Testing Utilities
Secure endpoints and commands for testing and management
"""

import os
import logging
from typing import Optional, List
from fastapi import APIRouter, Header, HTTPException, Depends
from pydantic import BaseModel
from google.cloud import firestore
from utils.timezone_utils import israel_now_isoformat

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
        user_data["last_seen"] = israel_now_isoformat()
        
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
            "created_at": israel_now_isoformat(),
            "last_seen": israel_now_isoformat(),
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
# STATISTICS & ANALYTICS ENDPOINTS
# ============================================================================

@router.get("/stats/overview")
async def get_stats_overview(_: bool = Depends(verify_admin_token)):
    """
    Get overview statistics for dashboard
    
    Returns comprehensive statistics including:
    - Total users, new users (7d), active users (30d)
    - Active rides (drivers + hitchhikers)
    - Matches (today, week, month)
    """
    from database import get_db
    from database.analytics import get_overview_stats
    
    db = get_db()
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        stats = await get_overview_stats(db)
        return stats
    except Exception as e:
        logger.error(f"❌ Error getting overview stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/trends")
async def get_stats_trends(
    days: int = 30,
    _: bool = Depends(verify_admin_token)
):
    """
    Get trend statistics for charts
    
    Query params:
        days: Number of days to look back (default 30)
    
    Returns:
        - new_users_by_day: Daily new user counts
        - new_rides_by_day: Daily new ride counts
        - popular_destinations: Top destinations
    """
    from database import get_db
    from database.analytics import get_trends_stats
    
    db = get_db()
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        trends = await get_trends_stats(db, days=days)
        return trends
    except Exception as e:
        logger.error(f"❌ Error getting trends: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/peak-hours")
async def get_stats_peak_hours(_: bool = Depends(verify_admin_token)):
    """
    Get peak hours based on ride departure times
    
    Returns list of {hour, count} for visualization
    """
    from database import get_db
    from database.analytics import get_peak_hours
    
    db = get_db()
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        peak_hours = await get_peak_hours(db)
        return {"peak_hours": peak_hours}
    except Exception as e:
        logger.error(f"❌ Error getting peak hours: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# LOGS & ERRORS ENDPOINTS
# ============================================================================

@router.get("/logs/errors")
async def get_errors(
    severity: Optional[str] = None,
    limit: int = 100,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    _: bool = Depends(verify_admin_token)
):
    """
    Get error logs from Firestore
    
    Query params:
        severity: Filter by severity ('error', 'warning', 'info')
        limit: Maximum number of logs (default 100)
        start_date: Start date (ISO format)
        end_date: End date (ISO format)
    """
    from database import get_db
    from database.logging import get_error_logs
    
    db = get_db()
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        logs = await get_error_logs(
            db=db,
            severity=severity,
            limit=limit,
            start_date=start_date,
            end_date=end_date
        )
        return {"logs": logs, "count": len(logs)}
    except Exception as e:
        logger.error(f"❌ Error getting error logs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/logs/activity")
async def get_activity(
    activity_type: Optional[str] = None,
    limit: int = 100,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    _: bool = Depends(verify_admin_token)
):
    """
    Get activity logs from Firestore
    
    Query params:
        activity_type: Filter by activity type
        limit: Maximum number of logs (default 100)
        start_date: Start date (ISO format)
        end_date: End date (ISO format)
    """
    from database import get_db
    from database.logging import get_activity_logs
    
    db = get_db()
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        logs = await get_activity_logs(
            db=db,
            activity_type=activity_type,
            limit=limit,
            start_date=start_date,
            end_date=end_date
        )
        return {"logs": logs, "count": len(logs)}
    except Exception as e:
        logger.error(f"❌ Error getting activity logs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/logs/cleanup")
async def cleanup_logs(
    days: int = 90,
    _: bool = Depends(verify_admin_token)
):
    """
    Delete logs older than specified days
    
    Query params:
        days: Number of days to keep logs (default 90)
    """
    from database import get_db
    from database.logging import clean_old_logs
    
    db = get_db()
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        deleted_count = await clean_old_logs(db, days=days)
        return {
            "success": True,
            "message": f"Deleted {deleted_count} logs older than {days} days",
            "deleted_count": deleted_count
        }
    except Exception as e:
        logger.error(f"❌ Error cleaning logs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# USERS ENDPOINTS (Extended)
# ============================================================================

@router.get("/users")
async def list_users(
    limit: int = 100,
    offset: int = 0,
    sort_by: str = "last_seen",
    order: str = "desc",
    search: Optional[str] = None,
    _: bool = Depends(verify_admin_token)
):
    """
    List all users with filtering, sorting, and pagination
    
    Query params:
        limit: Number of users to return (default 100)
        offset: Number of users to skip (default 0)
        sort_by: Field to sort by (default 'last_seen')
        order: Sort order 'asc' or 'desc' (default 'desc')
        search: Search in phone number or name
    """
    from database import get_db
    
    db = get_db()
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        users = []
        docs = db.collection("users").stream()
        
        for doc in docs:
            user_data = doc.to_dict()
            driver_rides = user_data.get("driver_rides", [])
            hitchhiker_requests = user_data.get("hitchhiker_requests", [])
            
            user_info = {
                "phone_number": user_data.get("phone_number"),
                "name": user_data.get("name"),
                "active_driver_rides": len([r for r in driver_rides if r.get("active", True)]),
                "active_hitchhiker_requests": len([r for r in hitchhiker_requests if r.get("active", True)]),
                "message_count": len(user_data.get("chat_history", [])),
                "last_seen": user_data.get("last_seen"),
                "created_at": user_data.get("created_at")
            }
            
            # Apply search filter
            if search:
                search_lower = search.lower()
                phone = user_info.get("phone_number", "").lower()
                name = user_info.get("name", "").lower()
                if search_lower not in phone and search_lower not in name:
                    continue
            
            users.append(user_info)
        
        # Sort users
        reverse = (order == "desc")
        users.sort(key=lambda x: x.get(sort_by, ""), reverse=reverse)
        
        # Pagination
        total_count = len(users)
        users_page = users[offset:offset + limit]
        
        return {
            "users": users_page,
            "count": len(users_page),
            "total": total_count,
            "offset": offset,
            "limit": limit
        }
    
    except Exception as e:
        logger.error(f"Error listing users: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/{phone_number}/details")
async def get_user_details(
    phone_number: str,
    _: bool = Depends(verify_admin_token)
):
    """
    Get complete user details including rides and chat history
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
        
        user_data = doc.to_dict()
        return user_data
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user details: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/{phone_number}/history")
async def get_user_history(
    phone_number: str,
    limit: int = 50,
    _: bool = Depends(verify_admin_token)
):
    """
    Get user's chat history
    
    Query params:
        limit: Number of messages to return (default 50)
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
        
        user_data = doc.to_dict()
        chat_history = user_data.get("chat_history", [])
        
        # Return last N messages
        recent_history = chat_history[-limit:] if len(chat_history) > limit else chat_history
        
        return {
            "phone_number": phone_number,
            "chat_history": recent_history,
            "total_messages": len(chat_history)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/export/csv")
async def export_users_csv(_: bool = Depends(verify_admin_token)):
    """
    Export users to CSV format
    """
    from database import get_db
    from fastapi.responses import StreamingResponse
    import io
    import csv
    
    db = get_db()
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        users_docs = db.collection("users").stream()
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            "Phone Number", "Name", "Created At", "Last Seen",
            "Active Driver Rides", "Active Hitchhiker Requests", "Total Messages"
        ])
        
        # Write data
        for doc in users_docs:
            user_data = doc.to_dict()
            driver_rides = user_data.get("driver_rides", [])
            hitchhiker_requests = user_data.get("hitchhiker_requests", [])
            
            writer.writerow([
                user_data.get("phone_number", ""),
                user_data.get("name", ""),
                user_data.get("created_at", ""),
                user_data.get("last_seen", ""),
                len([r for r in driver_rides if r.get("active", True)]),
                len([r for r in hitchhiker_requests if r.get("active", True)]),
                len(user_data.get("chat_history", []))
            ])
        
        # Prepare response
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=users_export.csv"}
        )
    
    except Exception as e:
        logger.error(f"Error exporting users: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# RIDES & MATCHES ENDPOINTS
# ============================================================================

@router.get("/rides/active")
async def get_active_rides(
    ride_type: Optional[str] = None,
    destination: Optional[str] = None,
    _: bool = Depends(verify_admin_token)
):
    """
    Get all active rides (drivers and hitchhikers)
    
    Query params:
        ride_type: Filter by 'driver' or 'hitchhiker'
        destination: Filter by destination
    """
    from database import get_db
    
    db = get_db()
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        users_docs = db.collection("users").stream()
        
        drivers = []
        hitchhikers = []
        
        for doc in users_docs:
            user_data = doc.to_dict()
            phone = user_data.get("phone_number")
            name = user_data.get("name")
            
            # Get driver rides
            if not ride_type or ride_type == "driver":
                driver_rides = user_data.get("driver_rides", [])
                for ride in driver_rides:
                    if not ride.get("active", True):
                        continue
                    
                    # Apply destination filter
                    if destination and destination.lower() not in ride.get("destination", "").lower():
                        continue
                    
                    drivers.append({
                        "id": ride.get("id"),
                        "phone_number": phone,
                        "name": name,
                        "origin": ride.get("origin", "גברעם"),
                        "destination": ride.get("destination"),
                        "days": ride.get("days", []),
                        "travel_date": ride.get("travel_date"),
                        "departure_time": ride.get("departure_time"),
                        "return_time": ride.get("return_time"),
                        "notes": ride.get("notes", ""),
                        "created_at": ride.get("created_at"),
                        "route_coordinates": ride.get("route_coordinates"),
                        "route_distance_km": ride.get("route_distance_km"),
                        "route_threshold_km": ride.get("route_threshold_km")
                    })
            
            # Get hitchhiker requests
            if not ride_type or ride_type == "hitchhiker":
                hitchhiker_requests = user_data.get("hitchhiker_requests", [])
                for request in hitchhiker_requests:
                    if not request.get("active", True):
                        continue
                    
                    # Apply destination filter
                    if destination and destination.lower() not in request.get("destination", "").lower():
                        continue
                    
                    hitchhikers.append({
                        "id": request.get("id"),
                        "phone_number": phone,
                        "name": name,
                        "origin": request.get("origin", "גברעם"),
                        "destination": request.get("destination"),
                        "travel_date": request.get("travel_date"),
                        "departure_time": request.get("departure_time"),
                        "flexibility": request.get("flexibility", "flexible"),
                        "notes": request.get("notes", ""),
                        "created_at": request.get("created_at"),
                        "route_coordinates": request.get("route_coordinates"),
                        "route_distance_km": request.get("route_distance_km"),
                        "route_threshold_km": request.get("route_threshold_km")
                    })
        
        return {
            "drivers": drivers,
            "hitchhikers": hitchhikers,
            "total_drivers": len(drivers),
            "total_hitchhikers": len(hitchhikers)
        }
    
    except Exception as e:
        logger.error(f"Error getting active rides: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/rides/{phone_number}/{ride_id}")
async def delete_ride(
    phone_number: str,
    ride_id: str,
    ride_type: str,
    _: bool = Depends(verify_admin_token)
):
    """
    Delete (deactivate) a specific ride
    
    Query params:
        ride_type: 'driver' or 'hitchhiker'
    """
    from database import remove_user_ride_or_request
    
    try:
        success = await remove_user_ride_or_request(
            phone_number=phone_number,
            role=ride_type,
            ride_id=ride_id
        )
        
        if success:
            return {
                "success": True,
                "message": f"Ride {ride_id} deleted successfully"
            }
        else:
            raise HTTPException(status_code=404, detail="Ride not found")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting ride: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rides/export/csv")
async def export_rides_csv(
    ride_type: Optional[str] = None,
    _: bool = Depends(verify_admin_token)
):
    """
    Export rides to CSV format
    
    Query params:
        ride_type: Filter by 'driver' or 'hitchhiker'
    """
    from database import get_db
    from fastapi.responses import StreamingResponse
    import io
    import csv
    
    db = get_db()
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        users_docs = db.collection("users").stream()
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            "Type", "Phone Number", "Name", "Origin", "Destination",
            "Days", "Travel Date", "Departure Time", "Return Time",
            "Flexibility", "Notes", "Created At"
        ])
        
        # Write data
        for doc in users_docs:
            user_data = doc.to_dict()
            phone = user_data.get("phone_number", "")
            name = user_data.get("name", "")
            
            # Export drivers
            if not ride_type or ride_type == "driver":
                driver_rides = user_data.get("driver_rides", [])
                for ride in driver_rides:
                    if ride.get("active", True):
                        writer.writerow([
                            "Driver",
                            phone,
                            name,
                            ride.get("origin", "גברעם"),
                            ride.get("destination", ""),
                            ", ".join(ride.get("days", [])),
                            ride.get("travel_date", ""),
                            ride.get("departure_time", ""),
                            ride.get("return_time", ""),
                            "",
                            ride.get("notes", ""),
                            ride.get("created_at", "")
                        ])
            
            # Export hitchhikers
            if not ride_type or ride_type == "hitchhiker":
                hitchhiker_requests = user_data.get("hitchhiker_requests", [])
                for request in hitchhiker_requests:
                    if request.get("active", True):
                        writer.writerow([
                            "Hitchhiker",
                            phone,
                            name,
                            request.get("origin", "גברעם"),
                            request.get("destination", ""),
                            "",
                            request.get("travel_date", ""),
                            request.get("departure_time", ""),
                            "",
                            request.get("flexibility", ""),
                            request.get("notes", ""),
                            request.get("created_at", "")
                        ])
        
        # Prepare response
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=rides_export.csv"}
        )
    
    except Exception as e:
        logger.error(f"Error exporting rides: {str(e)}")
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
                user_data["last_seen"] = israel_now_isoformat()
                
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
                "created_at": israel_now_isoformat(),
                "last_seen": israel_now_isoformat(),
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

