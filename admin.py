"""
Admin and Testing Utilities
Secure endpoints and commands for testing and management
"""

import os
import logging
import asyncio
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
    # In testing mode, bypass authentication for easier local development
    if TESTING_MODE_ENABLED:
        logger.debug("🔓 Testing mode: Bypassing admin token verification")
        return True
    
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


class UpdateRideRequest(BaseModel):
    origin: Optional[str] = None
    destination: Optional[str] = None
    travel_date: Optional[str] = None
    departure_time: Optional[str] = None
    return_time: Optional[str] = None
    days: Optional[List[str]] = None
    notes: Optional[str] = None
    flexibility: Optional[str] = None


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
                    
                    # Get route coordinates - support multiple formats
                    route_coords = ride.get("route_coordinates_flat") or ride.get("route_coordinates")
                    
                    # Handle old format: dict with numeric keys {0: lat, 1: lon, 2: lat, ...}
                    if isinstance(route_coords, dict) and route_coords:
                        try:
                            # Sort by numeric keys and create flat list
                            sorted_keys = sorted([int(k) for k in route_coords.keys()])
                            route_coords = [route_coords[str(k)] for k in sorted_keys]
                            logger.info(f"✅ Converted dict format to flat list: {len(route_coords)} values")
                        except (ValueError, KeyError, TypeError) as e:
                            logger.warning(f"⚠️ Failed to convert route_coords dict: {e}")
                            route_coords = None
                    
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
                        "route_coordinates": route_coords,
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
                    
                    # Get route coordinates - support multiple formats
                    route_coords = request.get("route_coordinates_flat") or request.get("route_coordinates")
                    
                    # Handle old format: dict with numeric keys
                    if isinstance(route_coords, dict) and route_coords:
                        try:
                            sorted_keys = sorted([int(k) for k in route_coords.keys()])
                            route_coords = [route_coords[str(k)] for k in sorted_keys]
                        except (ValueError, KeyError, TypeError):
                            route_coords = None
                    
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
                        "route_coordinates": route_coords,
                        "route_distance_km": request.get("route_distance_km"),
                        "route_threshold_km": request.get("route_threshold_km"),
                        # Add origin/destination coordinates for map display
                        "origin_coordinates": request.get("origin_coordinates"),
                        "destination_coordinates": request.get("destination_coordinates")
                    })
        
        # Import matching algorithm parameters
        from config import (
            ROUTE_PROXIMITY_MIN_THRESHOLD_KM,
            ROUTE_PROXIMITY_MAX_THRESHOLD_KM,
            ROUTE_PROXIMITY_SCALE_FACTOR
        )
        
        return {
            "drivers": drivers,
            "hitchhikers": hitchhikers,
            "total_drivers": len(drivers),
            "total_hitchhikers": len(hitchhikers),
            "matching_params": {
                "min_threshold_km": ROUTE_PROXIMITY_MIN_THRESHOLD_KM,
                "max_threshold_km": ROUTE_PROXIMITY_MAX_THRESHOLD_KM,
                "scale_factor": ROUTE_PROXIMITY_SCALE_FACTOR
            }
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


@router.put("/rides/{phone_number}/{ride_id}")
async def update_ride(
    phone_number: str,
    ride_id: str,
    ride_type: str,
    request: UpdateRideRequest,
    _: bool = Depends(verify_admin_token)
):
    """
    Update a specific ride (driver or hitchhiker).
    """
    from database import get_db, update_user_ride_or_request
    from services.route_service import calculate_and_save_route_background, geocode_address
    import asyncio

    if ride_type not in ("driver", "hitchhiker"):
        raise HTTPException(status_code=400, detail="Invalid ride_type")

    updates = {k: v for k, v in request.dict().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    db = get_db()
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        doc_ref = db.collection("users").document(phone_number)
        doc = doc_ref.get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="User not found")

        user_data = doc.to_dict()
        rides_list = user_data.get(
            "driver_rides" if ride_type == "driver" else "hitchhiker_requests",
            []
        )
        ride = next((r for r in rides_list if r.get("id") == ride_id), None)
        if not ride:
            raise HTTPException(status_code=404, detail="Ride not found")

        origin_val = updates.get("origin", ride.get("origin", "גברעם"))
        dest_val = updates.get("destination", ride.get("destination"))

        # Handle route recalculation for drivers if route details change
        route_changed = ride_type == "driver" and (
            "origin" in updates or "destination" in updates
        )
        if route_changed:
            updates["route_calculation_pending"] = True
            updates["route_coordinates_flat"] = None
            updates["route_num_points"] = None
            updates["route_distance_km"] = None
            updates["route_threshold_km"] = None

        # Update coordinates for hitchhikers when origin/destination changes
        if ride_type == "hitchhiker" and ("origin" in updates or "destination" in updates):
            if origin_val and dest_val:
                origin_coords = geocode_address(origin_val)
                dest_coords = geocode_address(dest_val)
                if origin_coords and dest_coords:
                    updates["origin_coordinates"] = list(origin_coords)
                    updates["destination_coordinates"] = list(dest_coords)

        success = await update_user_ride_or_request(
            phone_number, ride_type, ride_id, updates
        )
        if not success:
            raise HTTPException(status_code=500, detail="Update failed")

        # Kick off route calculation in background for drivers
        if route_changed and origin_val and dest_val:
            asyncio.create_task(
                calculate_and_save_route_background(
                    phone_number,
                    ride_id,
                    origin_val,
                    dest_val
                )
            )

        return {"success": True, "message": "Ride updated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating ride: {str(e)}")
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


@router.get("/matches")
async def list_matches(
    limit: int = 100,
    offset: int = 0,
    match_type: Optional[str] = None,
    destination: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    _: bool = Depends(verify_admin_token)
):
    """
    List match logs with optional filters.
    """
    from database import get_db

    db = get_db()
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        query = db.collection("matches").order_by("timestamp", direction=firestore.Query.DESCENDING)

        if match_type in ("driver", "hitchhiker"):
            query = query.where("match_type", "==", match_type)
        if start_date and start_date != "undefined":
            query = query.where("timestamp", ">=", start_date)
        if end_date and end_date != "undefined":
            query = query.where("timestamp", "<=", end_date)

        docs = query.stream()
        matches = []
        destination_filter = None
        if destination and destination != "undefined":
            destination_filter = destination.strip().lower()

        for doc in docs:
            data = doc.to_dict()
            data["id"] = doc.id

            if destination_filter:
                dest = (data.get("destination") or "").lower()
                matched_dest = (data.get("matched_destination") or "").lower()
                if destination_filter not in dest and destination_filter not in matched_dest:
                    continue

            matches.append(data)

        total = len(matches)
        matches_page = matches[offset:offset + limit]

        return {
            "matches": matches_page,
            "count": len(matches_page),
            "total": total,
            "offset": offset,
            "limit": limit
        }

    except Exception as e:
        logger.error(f"Error listing matches: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# WHATSAPP COMMAND HANDLERS (For convenience via WhatsApp)
# ============================================================================

async def handle_admin_whatsapp_command(
    phone_number: str,
    message: str,
    db: firestore.Client,
    collection_prefix: str = ""
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
            collection_name = f"{collection_prefix}users"
            original_doc = db.collection(collection_name).document(phone_number).get()
            
            if original_doc.exists:
                user_data = original_doc.to_dict()
                user_data["phone_number"] = new_number
                user_data["last_seen"] = israel_now_isoformat()
                
                # Create new document
                db.collection(collection_name).document(new_number).set(user_data)
                
                # Delete original
                db.collection(collection_name).document(phone_number).delete()
                
                logger.info(f"✅ Admin WhatsApp: Changed {phone_number} → {new_number}")
                
                return f"✅ Phone number changed!\nOld: {phone_number}\nNew: {new_number}\n\n⚠️ Note: You'll need to message from the OLD number to get this response."
            else:
                return "❌ User not found in database"
        
        # Delete user
        elif command == "d" and len(parts) > 2:
            confirm = parts[2]
            
            collection_name = f"{collection_prefix}users"
            db.collection(collection_name).document(phone_number).delete()
            
            logger.info(f"🗑️  Admin WhatsApp: Deleted user {phone_number} from {collection_name}")
            
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
            
            collection_name = f"{collection_prefix}users"
            db.collection(collection_name).document(phone_number).set(user_data)
            
            logger.info(f"🔄 Admin WhatsApp: Reset user {phone_number}")
            
            return "✅ Your data has been reset!\nYou can start fresh now."
        
        else:
            return "❌ Unknown admin command\nSend /admin:help for available commands"
    
    except Exception as e:
        logger.error(f"❌ Error handling admin command: {str(e)}")
        return f"❌ Error: {str(e)}"


# ============================================================================
# UTILITY ENDPOINTS
# ============================================================================

@router.post("/utils/trigger-match")
async def trigger_match_for_ride(
    phone_number: str,
    ride_id: str,
    ride_type: str,  # 'driver' or 'hitchhiker'
    collection_prefix: str = "",
    _: bool = Depends(verify_admin_token)
):
    """
    Manually trigger matching for a specific ride
    Useful for rides created through admin panel
    
    Example:
        POST /admin/utils/trigger-match?phone_number=972524297932&ride_id=abc123&ride_type=hitchhiker
    """
    from database import get_db
    from services.matching_service import find_matches_for_new_record
    
    db = get_db()
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        # Get user data
        collection_name = f"{collection_prefix}users" if collection_prefix else "users"
        doc = db.collection(collection_name).document(phone_number).get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail=f"User {phone_number} not found")
        
        user_data = doc.to_dict()
        
        # Find the specific ride
        rides_list = user_data.get("driver_rides" if ride_type == "driver" else "hitchhiker_requests", [])
        ride = None
        for r in rides_list:
            if r.get("id") == ride_id:
                ride = r.copy()
                ride["phone_number"] = phone_number
                ride["name"] = user_data.get("name", "Unknown")
                break
        
        if not ride:
            raise HTTPException(status_code=404, detail=f"Ride {ride_id} not found")
        
        # Run matching
        logger.info(f"🔍 Admin: Triggering match for {ride_type} {ride_id} ({phone_number})")
        matches = await find_matches_for_new_record(ride_type, ride, collection_prefix)
        
        logger.info(f"✅ Admin: Found {len(matches)} matches")
        
        return {
            "success": True,
            "matches_found": len(matches),
            "matches": matches
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error triggering match: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/utils/update-hitchhiker-coordinates")
async def update_hitchhiker_coordinates(
    collection_prefix: str = "",
    _: bool = Depends(verify_admin_token)
):
    """
    Update all hitchhiker requests with origin/destination coordinates
    Useful for adding map support to old hitchhiker requests
    """
    from database import get_db
    from services.route_service import geocode_address
    
    db = get_db()
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        collection_name = f"{collection_prefix}users"
        users_docs = db.collection(collection_name).stream()
        
        updated_count = 0
        skipped_count = 0
        error_count = 0
        
        for doc in users_docs:
            user_data = doc.to_dict()
            phone = user_data.get("phone_number")
            
            hitchhiker_requests = user_data.get("hitchhiker_requests", [])
            if not hitchhiker_requests:
                continue
            
            updated = False
            
            for request in hitchhiker_requests:
                # Skip if already has coordinates
                if request.get("origin_coordinates") and request.get("destination_coordinates"):
                    skipped_count += 1
                    continue
                
                origin = request.get("origin", "גברעם")
                destination = request.get("destination")
                
                if not destination:
                    error_count += 1
                    continue
                
                # Geocode
                try:
                    origin_coords = geocode_address(origin)
                    dest_coords = geocode_address(destination)
                    
                    if origin_coords and dest_coords:
                        request["origin_coordinates"] = list(origin_coords)
                        request["destination_coordinates"] = list(dest_coords)
                        updated = True
                        updated_count += 1
                    else:
                        error_count += 1
                except Exception as e:
                    logger.error(f"Error geocoding for {phone}: {e}")
                    error_count += 1
            
            # Save if updated
            if updated:
                doc.reference.update({"hitchhiker_requests": hitchhiker_requests})
        
        return {
            "success": True,
            "updated": updated_count,
            "skipped": skipped_count,
            "errors": error_count,
            "collection": collection_name
        }
    
    except Exception as e:
        logger.error(f"Error updating coordinates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# SANDBOX / TESTING ENDPOINTS
# ============================================================================

class SandboxMessageRequest(BaseModel):
    phone_number: str
    message: str
    environment: str = "test"  # "test" or "production"

@router.post("/sandbox/send")
async def send_sandbox_message(
    request: SandboxMessageRequest,
    _: bool = Depends(verify_admin_token)
):
    """
    Send a message to the bot as if from a WhatsApp user (for testing)
    
    Test users use the same collections and logic as regular users,
    but messages appear in the Sandbox UI instead of WhatsApp
    """
    from database import get_db, get_or_create_user, add_message_to_history
    from services.ai_service import process_message_with_ai
    from config import get_welcome_message
    
    try:
        db = get_db()
        if not db:
            raise HTTPException(status_code=503, detail="Database not available")
        
        logger.info(f"🧪 Sandbox message from {request.phone_number} [{request.environment}]: {request.message}")
        logger.info(f"   Step 1: Getting or creating user...")
        
        # Get or create user (same as regular users)
        user_data, is_new_user = await get_or_create_user(request.phone_number)
        logger.info(f"   Step 2: User loaded, is_new={is_new_user}")
        
        # If new user, send welcome
        if is_new_user:
            logger.info(f"   Step 3: New user, sending welcome...")
            welcome_msg = get_welcome_message(user_data.get("name"))
            await add_message_to_history(
                request.phone_number,
                "user",
                request.message
            )
            await add_message_to_history(
                request.phone_number, 
                "assistant", 
                welcome_msg
            )
            logger.info(f"   Step 4: Welcome sent, returning response")
            return {
                "status": "success",
                "phone_number": request.phone_number,
                "message": request.message,
                "environment": request.environment,
                "response": welcome_msg,
                "is_new_user": True
            }
        
        # Check for admin commands
        logger.info(f"   Step 3: Checking for admin commands...")
        if request.message.startswith("/a"):
            logger.info(f"   Step 4: Admin command detected")
            admin_response = await handle_admin_whatsapp_command(
                request.phone_number, 
                request.message, 
                db,
                collection_prefix=""  # Regular collections
            )
            
            if admin_response:
                logger.info(f"   Step 5: Admin command handled, saving to history...")
                await add_message_to_history(
                    request.phone_number, 
                    "user", 
                    request.message
                )
                await add_message_to_history(
                    request.phone_number, 
                    "assistant", 
                    admin_response
                )
                logger.info(f"   Step 6: Admin response ready, returning")
                return {
                    "status": "success",
                    "phone_number": request.phone_number,
                    "message": request.message,
                    "environment": request.environment,
                    "response": admin_response,
                    "is_new_user": False
                }
        
        # Process with AI (same as regular users)
        logger.info(f"   Step 4: Saving user message and calling AI service...")
        logger.info(f"   User data keys: {list(user_data.keys())}")
        logger.info(f"   Chat history length: {len(user_data.get('chat_history', []))}")
        
        # Save user message to history before AI processing
        await add_message_to_history(request.phone_number, "user", request.message)
        
        # Use regular AI processing - WhatsApp messages are handled automatically
        # (test users will have messages saved to history instead of WhatsApp)
        await process_message_with_ai(
            request.phone_number, 
            request.message, 
            user_data,
            is_new_user=False
        )
        
        logger.info(f"   Step 5: AI processing complete")
        
        # Get the latest response from chat history
        updated_user = await get_or_create_user(request.phone_number)
        updated_user_data = updated_user[0]
        chat_history = updated_user_data.get("chat_history", [])
        
        # Get last assistant message
        response = "מעבד..."
        for msg in reversed(chat_history):
            if msg.get("role") == "assistant":
                response = msg.get("content", "")
                break
        
        # Clean metadata from response (meant for AI only, not for user display)
        import re
        response = re.sub(r'\s*\[CONFLICT:[^\]]+\]\s*$', '', response)
        
        response_preview = response[:200] if response and len(response) > 200 else response
        logger.info(f"   Step 6: Retrieved response from history (length: {len(response)})")
        logger.info(f"   Response preview: {response_preview}{'...' if response and len(response) > 200 else ''}")
        
        logger.info(f"   Step 7: Preparing final response...")
        result = {
            "status": "success",
            "phone_number": request.phone_number,
            "message": request.message,
            "environment": request.environment,
            "response": response,
            "is_new_user": False
        }
        logger.info(f"   Step 8: ✅ ENDPOINT COMPLETE - returning response to frontend")
        return result
    
    except Exception as e:
        logger.error(f"❌ EXCEPTION in sandbox endpoint: {type(e).__name__}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sandbox/users")
async def get_sandbox_users(
    environment: str = "test",
    _: bool = Depends(verify_admin_token)
):
    """Get test users for the sandbox (from regular users collection)"""
    from database import get_db
    from config import TEST_USERS
    
    try:
        db = get_db()
        if not db:
            raise HTTPException(status_code=503, detail="Database not available")
        
        # Test users are in the regular 'users' collection
        users = []
        for phone in TEST_USERS:
            doc = db.collection("users").document(phone).get()
            if doc.exists:
                user_data = doc.to_dict()
                chat_history = user_data.get("chat_history", [])[-10:]  # Last 10 messages
                logger.info(f"📊 User {phone}: {len(chat_history)} messages in history")
                users.append({
                    "phone_number": user_data.get("phone_number"),
                    "name": user_data.get("name"),
                    "chat_history": chat_history,
                    "message_count": len(user_data.get("chat_history", []))
                })
        
        logger.info(f"✅ Returning {len(users)} sandbox users")
        return {
            "environment": environment,
            "users": users,
            "count": len(users)
        }
    
    except Exception as e:
        logger.error(f"Error getting sandbox users: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sandbox/all-rides")
async def get_sandbox_all_rides(
    environment: str = "test",
    _: bool = Depends(verify_admin_token)
):
    """Get all rides and requests for test users (from regular collections)"""
    from database import get_db
    from config import TEST_USERS
    
    try:
        db = get_db()
        if not db:
            raise HTTPException(status_code=503, detail="Database not available")
        
        # Test users are in the regular 'users' collection
        all_drivers = []
        all_hitchhikers = []
        
        for phone in TEST_USERS:
            doc = db.collection("users").document(phone).get()
            if not doc.exists:
                continue
                
            user_data = doc.to_dict()
            name = user_data.get("name")
            
            # Get driver rides
            driver_rides = user_data.get("driver_data", {}).get("rides", [])
            for ride in driver_rides:
                all_drivers.append({
                    "phone": phone,
                    "name": name,
                    "destination": ride.get("destination"),
                    "origin": ride.get("origin"),
                    "date": ride.get("travel_date"),
                    "time": ride.get("departure_time"),
                    "days": ride.get("days")
                })
            
            # Get hitchhiker requests
            hitchhiker_requests = user_data.get("hitchhiker_data", {}).get("requests", [])
            for request in hitchhiker_requests:
                all_hitchhikers.append({
                    "phone": phone,
                    "name": name,
                    "destination": request.get("destination"),
                    "origin": request.get("origin"),
                    "date": request.get("travel_date"),
                    "time": request.get("departure_time"),
                    "flexibility": request.get("flexibility")
                })
        
        return {
            "environment": environment,
            "drivers": all_drivers,
            "hitchhikers": all_hitchhikers,
            "driver_count": len(all_drivers),
            "hitchhiker_count": len(all_hitchhikers)
        }
    
    except Exception as e:
        logger.error(f"Error getting sandbox rides: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sandbox/reset")
async def reset_sandbox(
    environment: str = "test",
    _: bool = Depends(verify_admin_token)
):
    """Reset test users data (clear rides, requests, and chat history)"""
    from database import get_db
    from config import TEST_USERS
    
    if environment == "production":
        raise HTTPException(status_code=403, detail="Cannot reset production data via API")
    
    try:
        db = get_db()
        if not db:
            raise HTTPException(status_code=503, detail="Database not available")
        
        # Clear data for test users only
        cleared_count = 0
        
        for phone in TEST_USERS:
            doc_ref = db.collection("users").document(phone)
            doc = doc_ref.get()
            
            if doc.exists:
                # Clear rides, requests, and chat history but keep the user
                doc_ref.update({
                    "driver_rides": [],
                    "hitchhiker_requests": [],
                    "chat_history": []
                })
                cleared_count += 1
        
        logger.info(f"🧹 Sandbox reset: cleared data for {cleared_count} test users")
        
        return {
            "status": "success",
            "cleared_users": cleared_count,
            "message": "Test users data has been reset"
        }
    
    except Exception as e:
        logger.error(f"Error resetting sandbox: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rides/calculate-routes")
async def calculate_routes_for_rides(
    _: bool = Depends(verify_admin_token)
):
    """
    Manually trigger route calculation for all rides that don't have route data yet.
    This is useful for existing rides created before route calculation was implemented.
    """
    from database import get_db
    from services.route_service import calculate_and_save_route_background
    
    try:
        db = get_db()
        if not db:
            raise HTTPException(status_code=503, detail="Database not available")
        
        # Get all users
        users_ref = db.collection("users").stream()
        
        tasks_created = 0
        rides_processed = 0
        
        for user_doc in users_ref:
            user_data = user_doc.to_dict()
            phone_number = user_data.get("phone_number")
            
            # Process driver rides
            driver_rides = user_data.get("driver_rides", [])
            for ride in driver_rides:
                rides_processed += 1
                
                # Check if route data exists
                if not ride.get("route_coordinates"):
                    origin = ride.get("origin")
                    destination = ride.get("destination")
                    ride_id = ride.get("id")
                    
                    if origin and destination and ride_id:
                        logger.info(f"🔄 Starting route calc for ride {ride_id}: {origin} → {destination}")
                        
                        # Start background calculation
                        asyncio.create_task(calculate_and_save_route_background(
                            phone_number,
                            ride_id,
                            origin,
                            destination
                        ))
                        tasks_created += 1
        
        logger.info(f"✅ Created {tasks_created} route calculation tasks for {rides_processed} rides")
        
        return {
            "status": "success",
            "rides_processed": rides_processed,
            "calculations_started": tasks_created,
            "message": f"Route calculations started for {tasks_created} rides"
        }
    
    except Exception as e:
        logger.error(f"Error calculating routes: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


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

