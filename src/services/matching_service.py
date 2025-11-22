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
        logger.info(f"🔍 find_matching_drivers called: ride_request_id={ride_request.get('_id')}, destination={ride_request.get('destination')}")
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

    def find_matching_hitchhikers(self, driver_info: Dict[str, Any], destination: str, 
                                 departure_time: str = None, days: str = None) -> List[Dict[str, Any]]:
        """
        Find matching hitchhikers for a driver routine or offer
        
        Args:
            driver_info: Driver information dict with driver_id, driver_phone, etc.
            destination: Destination of the driver's route
            departure_time: Optional departure time (for routines)
            days: Optional days of week (for routines)
            
        Returns:
            List of matching hitchhiker ride requests with match scores
        """
        logger.info(f"🔍 find_matching_hitchhikers called: driver={driver_info.get('driver_phone')}, destination={destination}, departure_time={departure_time}, days={days}")
        matching_requests = []
        
        # Search for active hitchhiker requests matching this destination
        query = {
            "type": "hitchhiker_request",
            "destination": destination,
            "status": {"$in": ["pending", "matched"]}  # Include matched but not yet approved
        }
        
        active_requests = list(self.db.get_collection("ride_requests").find(query))
        logger.info(f"🔍 Found {len(active_requests)} active hitchhiker requests for destination '{destination}'")
        
        for request in active_requests:
            # Skip if already approved
            if request.get('status') == 'approved':
                continue
            
            hitchhiker = self.db.get_collection("users").find_one({"_id": request['requester_id']})
            if not hitchhiker:
                continue
            
            # Calculate match score
            score = self._calculate_hitchhiker_match_score(
                request, destination, departure_time, days
            )
            
            matching_requests.append({
                'ride_request_id': request['_id'],
                'hitchhiker_id': request['requester_id'],
                'hitchhiker_phone': request['requester_phone'],
                'hitchhiker_name': hitchhiker.get('full_name') or hitchhiker.get('whatsapp_name'),
                'score': score,
                'destination': request.get('destination'),
                'time_range': request.get('time_range'),
                'specific_datetime': request.get('specific_datetime'),
                'ride_timing': request.get('ride_timing')
            })
        
        # Sort by score (highest first)
        sorted_requests = sorted(matching_requests, key=lambda x: x['score'], reverse=True)
        logger.info(f"✅ Found {len(sorted_requests)} matching hitchhikers (after scoring)")
        return sorted_requests
    
    def _calculate_hitchhiker_match_score(self, request: Dict[str, Any], destination: str,
                                         departure_time: str = None, days: str = None) -> float:
        """Calculate match score for a hitchhiker request"""
        score = 1.0
        
        # Exact destination match
        if request.get('destination') == destination:
            score += 2.0
        
        # Time matching for routines
        if departure_time:
            request_time = None
            
            # Try to extract time from request
            if request.get('specific_datetime'):
                parsed = self._parse_datetime_string(request['specific_datetime'])
                request_time = parsed.get('time')
            elif request.get('time_range'):
                # Extract start time from range (e.g., "07:00-09:00" -> "07:00")
                time_range = request['time_range']
                if '-' in time_range:
                    request_time = time_range.split('-')[0].strip()
            
            if request_time and self._times_match(request_time, departure_time, tolerance_hours=1):
                score += 1.5
        
        # Timing match for offers (now, 30min, 1hour, etc.)
        if request.get('ride_timing'):
            # If driver is offering "now" and hitchhiker needs "now", it's a good match
            # This is simplified - can be improved
            score += 0.5
        
        return score
    
    def create_matches_for_driver(self, driver_id: ObjectId, driver_phone: str,
                                 matching_requests: List[Dict[str, Any]],
                                 routine_id: ObjectId = None, offer_id: ObjectId = None) -> List[Dict[str, Any]]:
        """
        Create match documents for a driver with matching hitchhiker requests
        
        Args:
            driver_id: Driver's user ID
            driver_phone: Driver's phone number
            matching_requests: List of matching hitchhiker request info
            routine_id: Optional routine ID (if matching from routine)
            offer_id: Optional offer ID (if matching from driver offer)
            
        Returns:
            List of created match documents
        """
        matches = []
        
        for request_info in matching_requests:
            ride_request_id = request_info['ride_request_id']
            hitchhiker_id = request_info['hitchhiker_id']
            
            # Check if match already exists
            existing_match = self.db.get_collection("matches").find_one({
                "ride_request_id": ride_request_id,
                "driver_id": driver_id,
                "status": {"$in": ["pending_approval", "approved"]}
            })
            
            if existing_match:
                logger.info(f"Match already exists for driver {driver_phone} and request {ride_request_id}")
                continue
            
            from src.database.models import MatchModel
            
            match_doc = MatchModel.create(
                ride_request_id=ride_request_id,
                driver_id=driver_id,
                hitchhiker_id=hitchhiker_id,
                destination=request_info['destination'],
                origin=request_info.get('origin', 'גברעם')
            )
            
            # Add routine/offer reference if available
            if routine_id:
                match_doc['routine_id'] = routine_id
            if offer_id:
                match_doc['offer_id'] = offer_id
            
            result = self.db.get_collection("matches").insert_one(match_doc)
            match_doc['_id'] = result.inserted_id
            matches.append(match_doc)
            
            # Update ride request status if needed
            ride_request = self.db.get_collection("ride_requests").find_one({"_id": ride_request_id})
            if ride_request and ride_request.get('status') == 'pending':
                self.db.get_collection("ride_requests").update_one(
                    {"_id": ride_request_id},
                    {
                        "$set": {
                            "status": "matched",
                            "updated_at": datetime.now()
                        },
                        "$push": {
                            "matched_drivers": {
                                "driver_id": driver_id,
                                "driver_phone": driver_phone,
                                "matched_at": datetime.now(),
                                "status": "pending"
                            }
                        }
                    }
                )
        
        logger.info(f"Created {len(matches)} matches for driver {driver_phone}")
        return matches


