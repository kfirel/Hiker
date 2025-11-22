"""
Matching Service - Finds matching drivers for hitchhiker requests
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging
from bson import ObjectId

logger = logging.getLogger(__name__)


class MatchingService:
    """Service for matching hitchhikers with drivers"""
    
    def __init__(self, db):
        """
        Initialize matching service
        
        Args:
            db: MongoDBClient instance
        """
        self.db = db
    
    def find_matching_drivers(self, ride_request: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Find matching drivers for a ride request
        
        Args:
            ride_request: Ride request document
            
        Returns:
            List of matching driver documents with match scores
        """
        destination = ride_request.get('destination')
        origin = ride_request.get('origin', 'גברעם')
        time_info = self._parse_time_info(ride_request)
        
        matching_drivers = []
        
        # 1. Search in routines
        routines = self._search_routines(destination, time_info, origin)
        for routine in routines:
            driver = self.db.get_collection("users").find_one({"_id": routine['user_id']})
            if driver and driver.get('user_type') in ['driver', 'both']:
                score = self._calculate_routine_match_score(routine, time_info, destination)
                matching_drivers.append({
                    'driver_id': driver['_id'],
                    'driver_phone': driver['phone_number'],
                    'driver_name': driver.get('full_name') or driver.get('whatsapp_name'),
                    'match_type': 'routine',
                    'routine_id': routine['_id'],
                    'score': score,
                    'departure_time': routine.get('departure_time'),
                    'days': routine.get('days')
                })
        
        # 2. Search in active driver offers
        active_offers = self._search_active_offers(destination, time_info, origin)
        for offer in active_offers:
            driver = self.db.get_collection("users").find_one({"_id": offer['requester_id']})
            if driver:
                score = self._calculate_offer_match_score(offer, time_info, destination)
                matching_drivers.append({
                    'driver_id': driver['_id'],
                    'driver_phone': driver['phone_number'],
                    'driver_name': driver.get('full_name') or driver.get('whatsapp_name'),
                    'match_type': 'offer',
                    'offer_id': offer['_id'],
                    'score': score,
                    'departure_timing': offer.get('departure_timing')
                })
        
        # Remove duplicates and sort by score
        unique_drivers = self._deduplicate_drivers(matching_drivers)
        return sorted(unique_drivers, key=lambda x: x['score'], reverse=True)
    
    def _parse_time_info(self, ride_request: Dict[str, Any]) -> Dict[str, Any]:
        """Parse time information from ride request"""
        time_info = {
            'type': ride_request.get('time_type'),
            'time_range': ride_request.get('time_range'),
            'specific_datetime': ride_request.get('specific_datetime'),
            'ride_timing': ride_request.get('ride_timing')
        }
        
        # Parse specific datetime if exists
        if time_info['specific_datetime']:
            parsed = self._parse_datetime_string(time_info['specific_datetime'])
            time_info['parsed_datetime'] = parsed
        
        return time_info
    
    def _parse_datetime_string(self, datetime_str: str) -> Dict[str, Any]:
        """
        Parse datetime string like "מחר 15:00" or "15/11/2025 14:30"
        Returns dict with date and time info
        """
        from datetime import datetime as dt
        
        result = {
            'is_tomorrow': False,
            'is_today': False,
            'raw': datetime_str
        }
        
        # Check for "מחר" (tomorrow)
        if 'מחר' in datetime_str:
            result['is_tomorrow'] = True
            # Extract time if present
            import re
            time_match = re.search(r'(\d{1,2}):?(\d{2})?', datetime_str)
            if time_match:
                hours = int(time_match.group(1))
                minutes = int(time_match.group(2)) if time_match.group(2) else 0
                result['time'] = f"{hours:02d}:{minutes:02d}"
        
        # Check for "היום" (today)
        elif 'היום' in datetime_str:
            result['is_today'] = True
            import re
            time_match = re.search(r'(\d{1,2}):?(\d{2})?', datetime_str)
            if time_match:
                hours = int(time_match.group(1))
                minutes = int(time_match.group(2)) if time_match.group(2) else 0
                result['time'] = f"{hours:02d}:{minutes:02d}"
        
        # Check for exact date format "DD/MM/YYYY HH:MM"
        elif '/' in datetime_str:
            import re
            date_match = re.match(r'(\d{1,2})/(\d{1,2})/(\d{4})\s+(\d{1,2}):(\d{2})', datetime_str)
            if date_match:
                result['date'] = datetime_str.split()[0]
                result['time'] = datetime_str.split()[1]
        
        return result
    
    def _search_routines(self, destination: str, time_info: Dict[str, Any], origin: str) -> List[Dict[str, Any]]:
        """Search for matching routines"""
        query = {
            "destination": destination,
            "is_active": True
        }
        
        # TODO: Add day matching if we have specific datetime
        # For now, return all active routines for destination
        
        routines = list(self.db.get_collection("routines").find(query))
        return routines
    
    def _search_active_offers(self, destination: str, time_info: Dict[str, Any], origin: str) -> List[Dict[str, Any]]:
        """Search for active driver offers"""
        query = {
            "type": "driver_offer",
            "destination": destination,
            "status": "active"
        }
        
        offers = list(self.db.get_collection("ride_requests").find(query))
        return offers
    
    def _calculate_routine_match_score(self, routine: Dict[str, Any], time_info: Dict[str, Any], destination: str) -> float:
        """Calculate match score for a routine"""
        score = 1.0
        
        # Exact destination match
        if routine.get('destination') == destination:
            score += 2.0
        
        # Time matching (simplified - can be improved)
        if time_info.get('parsed_datetime'):
            parsed = time_info['parsed_datetime']
            if parsed.get('time') and routine.get('departure_time'):
                # Simple time comparison (within 1 hour)
                request_time = parsed['time']
                routine_time = routine['departure_time']
                if self._times_match(request_time, routine_time, tolerance_hours=1):
                    score += 1.5
        
        return score
    
    def _calculate_offer_match_score(self, offer: Dict[str, Any], time_info: Dict[str, Any], destination: str) -> float:
        """Calculate match score for an offer"""
        score = 1.0
        
        # Exact destination match
        if offer.get('destination') == destination:
            score += 2.0
        
        # Time matching
        if time_info.get('ride_timing') and offer.get('departure_timing'):
            if time_info['ride_timing'] == offer['departure_timing']:
                score += 1.5
        
        return score
    
    def _times_match(self, time1: str, time2: str, tolerance_hours: int = 1) -> bool:
        """Check if two times match within tolerance"""
        try:
            from datetime import datetime
            t1 = datetime.strptime(time1, "%H:%M")
            t2 = datetime.strptime(time2, "%H:%M")
            diff = abs((t1 - t2).total_seconds() / 3600)
            return diff <= tolerance_hours
        except:
            return False
    
    def _deduplicate_drivers(self, drivers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate drivers, keep highest score"""
        seen = {}
        for driver in drivers:
            driver_id = str(driver['driver_id'])
            if driver_id not in seen or driver['score'] > seen[driver_id]['score']:
                seen[driver_id] = driver
        
        return list(seen.values())
    
    def create_matches(self, ride_request_id: ObjectId, hitchhiker_id: ObjectId, 
                      matching_drivers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Create match documents for all matching drivers
        
        Args:
            ride_request_id: Ride request ID
            hitchhiker_id: Hitchhiker user ID
            matching_drivers: List of matching driver info
            
        Returns:
            List of created match documents
        """
        ride_request = self.db.get_collection("ride_requests").find_one({"_id": ride_request_id})
        if not ride_request:
            logger.error(f"Ride request not found: {ride_request_id}")
            return []
        
        matches = []
        matched_drivers_info = []
        
        for driver_info in matching_drivers:
            from src.database.models import MatchModel
            
            match_doc = MatchModel.create(
                ride_request_id=ride_request_id,
                driver_id=driver_info['driver_id'],
                hitchhiker_id=hitchhiker_id,
                destination=ride_request['destination'],
                origin=ride_request.get('origin', 'גברעם')
            )
            
            result = self.db.get_collection("matches").insert_one(match_doc)
            match_doc['_id'] = result.inserted_id
            matches.append(match_doc)
            
            matched_drivers_info.append({
                "driver_id": driver_info['driver_id'],
                "driver_phone": driver_info['driver_phone'],
                "matched_at": datetime.now(),
                "status": "pending"
            })
        
        # Update ride request with matched drivers
        self.db.get_collection("ride_requests").update_one(
            {"_id": ride_request_id},
            {
                "$set": {
                    "status": "matched",
                    "matched_drivers": matched_drivers_info,
                    "updated_at": datetime.now()
                }
            }
        )
        
        logger.info(f"Created {len(matches)} matches for ride request {ride_request_id}")
        return matches


