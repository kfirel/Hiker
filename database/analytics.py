"""
Analytics and Statistics Functions
Calculate various metrics for the admin dashboard
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta, timezone
from collections import Counter
from google.cloud import firestore

logger = logging.getLogger(__name__)

def _parse_iso_to_utc(value: str) -> Optional[datetime]:
    """Parse ISO datetime and return UTC-aware datetime."""
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


async def get_overview_stats(db: firestore.Client) -> Dict[str, Any]:
    """
    Get overview statistics for dashboard
    
    Returns:
        - total_users: Total number of users
        - new_users_7d: New users in last 7 days
        - active_users_30d: Active users in last 30 days
        - active_driver_rides: Number of active driver rides
        - active_hitchhiker_requests: Number of active hitchhiker requests
        - matches_today: Matches created today (estimated from activity)
        - matches_week: Matches this week
        - matches_month: Matches this month
    """
    try:
        now = datetime.now(timezone.utc)
        seven_days_ago = now - timedelta(days=7)
        thirty_days_ago = now - timedelta(days=30)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = now - timedelta(days=7)
        month_start = now - timedelta(days=30)
        
        # Get all users
        users_docs = db.collection("users").stream()
        
        total_users = 0
        new_users_7d = 0
        active_users_30d = 0
        active_driver_rides = 0
        active_hitchhiker_requests = 0
        
        for doc in users_docs:
            user_data = doc.to_dict()
            total_users += 1
            
            # Check if new user (created in last 7 days)
            created_at = user_data.get("created_at", "")
            created_date = _parse_iso_to_utc(created_at)
            if created_date and created_date >= seven_days_ago:
                new_users_7d += 1
            
            # Check if active (last_seen in last 30 days)
            last_seen = user_data.get("last_seen", "")
            last_seen_date = _parse_iso_to_utc(last_seen)
            if last_seen_date and last_seen_date >= thirty_days_ago:
                active_users_30d += 1
            
            # Count active rides
            driver_rides = user_data.get("driver_rides", [])
            for ride in driver_rides:
                if ride.get("active", True):
                    active_driver_rides += 1
            
            hitchhiker_requests = user_data.get("hitchhiker_requests", [])
            for request in hitchhiker_requests:
                if request.get("active", True):
                    active_hitchhiker_requests += 1
        
        # For now, we don't have a matches collection, so we estimate based on activity
        # In the future, we can track matches explicitly
        matches_today = 0
        matches_week = 0
        matches_month = 0
        
        return {
            "total_users": total_users,
            "new_users_7d": new_users_7d,
            "active_users_30d": active_users_30d,
            "active_driver_rides": active_driver_rides,
            "active_hitchhiker_requests": active_hitchhiker_requests,
            "matches_today": matches_today,
            "matches_week": matches_week,
            "matches_month": matches_month,
            "timestamp": now.isoformat()
        }
    
    except Exception as e:
        logger.error(f"❌ Error calculating overview stats: {e}")
        return {
            "total_users": 0,
            "new_users_7d": 0,
            "active_users_30d": 0,
            "active_driver_rides": 0,
            "active_hitchhiker_requests": 0,
            "matches_today": 0,
            "matches_week": 0,
            "matches_month": 0,
            "error": str(e)
        }


async def get_trends_stats(db: firestore.Client, days: int = 30) -> Dict[str, Any]:
    """
    Get trend statistics for charts
    
    Args:
        days: Number of days to look back
    
    Returns:
        - new_users_by_day: List of {date, count} for new users
        - new_rides_by_day: List of {date, count} for new rides
        - popular_destinations: List of {destination, count} for top destinations
    """
    try:
        now = datetime.now(timezone.utc)
        start_date = now - timedelta(days=days)
        
        # Initialize counters
        users_by_day = Counter()
        rides_by_day = Counter()
        destination_counter = Counter()
        
        # Get all users
        users_docs = db.collection("users").stream()
        
        for doc in users_docs:
            user_data = doc.to_dict()
            
            # Count users by creation date
            created_at = user_data.get("created_at", "")
            created_date = _parse_iso_to_utc(created_at)
            if created_date and created_date >= start_date:
                day_key = created_date.strftime("%Y-%m-%d")
                users_by_day[day_key] += 1
            
            # Count rides by creation date and destinations
            driver_rides = user_data.get("driver_rides", [])
            for ride in driver_rides:
                ride_created = ride.get("created_at", "")
                ride_date = _parse_iso_to_utc(ride_created)
                if ride_date and ride_date >= start_date:
                    day_key = ride_date.strftime("%Y-%m-%d")
                    rides_by_day[day_key] += 1
                
                # Count destinations (only active rides)
                if ride.get("active", True):
                    dest = ride.get("destination", "")
                    if dest:
                        destination_counter[dest] += 1
            
            hitchhiker_requests = user_data.get("hitchhiker_requests", [])
            for request in hitchhiker_requests:
                request_created = request.get("created_at", "")
                request_date = _parse_iso_to_utc(request_created)
                if request_date and request_date >= start_date:
                    day_key = request_date.strftime("%Y-%m-%d")
                    rides_by_day[day_key] += 1
                
                # Count destinations (only active requests)
                if request.get("active", True):
                    dest = request.get("destination", "")
                    if dest:
                        destination_counter[dest] += 1
        
        # Format data for charts
        new_users_by_day = []
        for i in range(days):
            date = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
            new_users_by_day.append({
                "date": date,
                "count": users_by_day.get(date, 0)
            })
        
        new_rides_by_day = []
        for i in range(days):
            date = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
            new_rides_by_day.append({
                "date": date,
                "count": rides_by_day.get(date, 0)
            })
        
        # Get top 10 destinations
        popular_destinations = [
            {"destination": dest, "count": count}
            for dest, count in destination_counter.most_common(10)
        ]
        
        return {
            "new_users_by_day": new_users_by_day,
            "new_rides_by_day": new_rides_by_day,
            "popular_destinations": popular_destinations,
            "timestamp": now.isoformat()
        }
    
    except Exception as e:
        logger.error(f"❌ Error calculating trends: {e}")
        return {
            "new_users_by_day": [],
            "new_rides_by_day": [],
            "popular_destinations": [],
            "error": str(e)
        }


async def get_peak_hours(db: firestore.Client) -> List[Dict[str, Any]]:
    """
    Calculate peak hours based on ride departure times
    
    Returns:
        List of {hour, count} for each hour of the day
    """
    try:
        hour_counter = Counter()
        
        users_docs = db.collection("users").stream()
        
        for doc in users_docs:
            user_data = doc.to_dict()
            
            # Count driver departure times
            driver_rides = user_data.get("driver_rides", [])
            for ride in driver_rides:
                if ride.get("active", True):
                    time_str = ride.get("departure_time", "")
                    if time_str:
                        try:
                            hour = int(time_str.split(":")[0])
                            hour_counter[hour] += 1
                        except:
                            pass
            
            # Count hitchhiker departure times
            hitchhiker_requests = user_data.get("hitchhiker_requests", [])
            for request in hitchhiker_requests:
                if request.get("active", True):
                    time_str = request.get("departure_time", "")
                    if time_str:
                        try:
                            hour = int(time_str.split(":")[0])
                            hour_counter[hour] += 1
                        except:
                            pass
        
        # Format as list of hours
        peak_hours = [
            {"hour": hour, "count": hour_counter.get(hour, 0)}
            for hour in range(24)
        ]
        
        return peak_hours
    
    except Exception as e:
        logger.error(f"❌ Error calculating peak hours: {e}")
        return []



