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
        """Parse time information from ride request - now uses time ranges"""
        time_info = {
            'start_time_range': ride_request.get('start_time_range'),
            'end_time_range': ride_request.get('end_time_range')
        }
        
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
        """Search for matching routines - check if request time range overlaps with routine time range"""
        from src.time_utils import is_current_time_in_range
        
        query = {
            "destination": destination,
            "is_active": True
        }
        
        # Get all routines for destination
        routines = list(self.db.get_collection("routines").find(query))
        
        # Filter routines where request time range overlaps with routine departure time range
        # Also check if today matches the routine's days
        matching_routines = []
        now = datetime.now()
        current_day = now.weekday()  # 0=Monday, 6=Sunday
        
        # Get request time range
        request_start_time = time_info.get('start_time_range')
        request_end_time = time_info.get('end_time_range')
        
        for routine in routines:
            # Check if routine is active for today
            days = routine.get('days', '')
            if not self._is_day_in_routine_days(current_day, days):
                logger.debug(f"Routine {routine.get('_id')} not active for current day {current_day} (days: {days})")
                continue
            
            # Get routine departure time range
            departure_start = routine.get('departure_time_start')
            departure_end = routine.get('departure_time_end')
            
            if departure_start and departure_end:
                # If request has time range, check if ranges overlap
                # For routines, we need to normalize the dates to the request's date since routines are daily
                if request_start_time and request_end_time:
                    # Normalize routine times to the request's date
                    request_date = request_start_time.date()
                    routine_start_normalized = departure_start.replace(year=request_date.year, month=request_date.month, day=request_date.day)
                    routine_end_normalized = departure_end.replace(year=request_date.year, month=request_date.month, day=request_date.day)
                    
                    if self._time_ranges_overlap(
                        request_start_time, request_end_time,
                        routine_start_normalized, routine_end_normalized
                    ):
                        logger.info(f"✅ Routine {routine.get('_id')} matches: request range [{request_start_time} - {request_end_time}] overlaps with routine range [{routine_start_normalized} - {routine_end_normalized}]")
                        matching_routines.append(routine)
                    else:
                        logger.debug(f"⏰ Routine {routine.get('_id')} time range [{routine_start_normalized} - {routine_end_normalized}] does not overlap with request range [{request_start_time} - {request_end_time}]")
                else:
                    # If request has no time range, check if current time is within routine range
                    if is_current_time_in_range(departure_start, departure_end):
                        logger.info(f"✅ Routine {routine.get('_id')} matches: current time {now} is within routine range [{departure_start} - {departure_end}]")
                        matching_routines.append(routine)
                    else:
                        logger.debug(f"⏰ Routine {routine.get('_id')} time range [{departure_start} - {departure_end}] does not include current time {now}")
            else:
                # Fallback: if no time range, include routine (backward compatibility)
                logger.warning(f"⚠️ Routine {routine.get('_id')} has no time range, including anyway (backward compatibility)")
                matching_routines.append(routine)
        
        logger.info(f"🔍 Found {len(matching_routines)} matching routines out of {len(routines)} total routines for destination '{destination}'")
        return matching_routines
    
    def _search_active_offers(self, destination: str, time_info: Dict[str, Any], origin: str) -> List[Dict[str, Any]]:
        """Search for active driver offers - check if current time is within offer time range"""
        from src.time_utils import is_current_time_in_range
        
        query = {
            "type": "driver_offer",
            "destination": destination,
            "status": "pending"  # Changed from "active" to "pending" to match model
        }
        
        offers = list(self.db.get_collection("ride_requests").find(query))
        
        # Filter offers where current time is within time range
        matching_offers = []
        request_start_time = time_info.get('start_time_range')
        request_end_time = time_info.get('end_time_range')
        
        for offer in offers:
            offer_start = offer.get('start_time_range')
            offer_end = offer.get('end_time_range')
            
            if offer_start and offer_end and request_start_time and request_end_time:
                # Check if time ranges overlap
                if self._time_ranges_overlap(
                    request_start_time, request_end_time,
                    offer_start, offer_end
                ):
                    matching_offers.append(offer)
            elif offer_start and offer_end:
                # If request has no time range, check if current time is within offer range
                if is_current_time_in_range(offer_start, offer_end):
                    matching_offers.append(offer)
            else:
                # Fallback: if no time range, include offer (backward compatibility)
                matching_offers.append(offer)
        
        return matching_offers
    
    def _is_day_in_routine_days(self, current_day: int, days_str: str) -> bool:
        """
        Check if current day (0=Monday, 6=Sunday) is in routine days string
        
        Args:
            current_day: Current weekday (0=Monday, 6=Sunday)
            days_str: Days string like "א-ה", "ב,ד", "כל יום"
        
        Returns:
            True if current day matches routine days
        """
        if not days_str:
            return False
        
        # Hebrew day mapping: א=Sunday(6), ב=Monday(0), ג=Tuesday(1), ד=Wednesday(2), ה=Thursday(3), ו=Friday(4), ש=Saturday(5)
        hebrew_days = {'א': 6, 'ב': 0, 'ג': 1, 'ד': 2, 'ה': 3, 'ו': 4, 'ש': 5}
        
        # Check for "כל יום" or "כל הימים"
        if 'כל' in days_str:
            return True
        
        # Check for range like "א-ה"
        if '-' in days_str:
            parts = days_str.split('-')
            if len(parts) == 2:
                start_day = hebrew_days.get(parts[0].strip())
                end_day = hebrew_days.get(parts[1].strip())
                if start_day is not None and end_day is not None:
                    # Handle wrap-around (e.g., ו-ב)
                    if start_day <= end_day:
                        return start_day <= current_day <= end_day
                    else:
                        return current_day >= start_day or current_day <= end_day
        
        # Check for comma-separated days like "ב,ד"
        if ',' in days_str:
            day_list = [d.strip() for d in days_str.split(',')]
            for day_char in day_list:
                if hebrew_days.get(day_char) == current_day:
                    return True
        
        return False
    
    def _time_ranges_overlap(self, start1: datetime, end1: datetime, start2: datetime, end2: datetime) -> bool:
        """
        Check if two time ranges overlap
        
        Args:
            start1, end1: First time range
            start2, end2: Second time range
        
        Returns:
            True if ranges overlap
        """
        return start1 <= end2 and start2 <= end1
    
    def _calculate_routine_match_score(self, routine: Dict[str, Any], time_info: Dict[str, Any], destination: str) -> float:
        """Calculate match score for a routine"""
        score = 1.0
        
        # Exact destination match
        if routine.get('destination') == destination:
            score += 2.0
        
        # Time range matching - check if ranges overlap
        request_start = time_info.get('start_time_range')
        request_end = time_info.get('end_time_range')
        routine_start = routine.get('departure_time_start')
        routine_end = routine.get('departure_time_end')
        
        if request_start and request_end and routine_start and routine_end:
            if self._time_ranges_overlap(request_start, request_end, routine_start, routine_end):
                score += 1.5
        
        return score
    
    def _calculate_offer_match_score(self, offer: Dict[str, Any], time_info: Dict[str, Any], destination: str) -> float:
        """Calculate match score for an offer"""
        score = 1.0
        
        # Exact destination match
        if offer.get('destination') == destination:
            score += 2.0
        
        # Time range matching - check if ranges overlap
        request_start = time_info.get('start_time_range')
        request_end = time_info.get('end_time_range')
        offer_start = offer.get('start_time_range')
        offer_end = offer.get('end_time_range')
        
        if request_start and request_end and offer_start and offer_end:
            if self._time_ranges_overlap(request_start, request_end, offer_start, offer_end):
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
                                 departure_time_start: datetime = None, departure_time_end: datetime = None,
                                 days: str = None, offer_start_time: datetime = None, offer_end_time: datetime = None) -> List[Dict[str, Any]]:
        """
        Find matching hitchhikers for a driver routine or offer
        
        Args:
            driver_info: Driver information dict with driver_id, driver_phone, etc.
            destination: Destination of the driver's route
            departure_time_start: Optional departure time range start (for routines)
            departure_time_end: Optional departure time range end (for routines)
            days: Optional days of week (for routines)
            offer_start_time: Optional offer time range start (for driver offers)
            offer_end_time: Optional offer time range end (for driver offers)
            
        Returns:
            List of matching hitchhiker ride requests with match scores
        """
        from src.time_utils import is_current_time_in_range
        
        logger.info(f"🔍 find_matching_hitchhikers called: driver={driver_info.get('driver_phone')}, destination={destination}, departure_time_start={departure_time_start}, departure_time_end={departure_time_end}, days={days}, offer_start_time={offer_start_time}, offer_end_time={offer_end_time}")
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
            
            # Check time range matching
            request_start = request.get('start_time_range')
            request_end = request.get('end_time_range')
            
            if request_start and request_end:
                # If driver has an offer with time range, check if ranges overlap
                if offer_start_time and offer_end_time:
                    if not self._time_ranges_overlap(
                        request_start, request_end,
                        offer_start_time, offer_end_time
                    ):
                        logger.info(f"⏰ Skipping request {request.get('_id')} - time ranges don't overlap")
                        continue
                # If driver has a routine with time range, check if ranges overlap
                elif departure_time_start and departure_time_end:
                    # Normalize routine time range to the date of the hitchhiker's request
                    # This allows routines to match requests on different days
                    from datetime import datetime, timedelta
                    request_date = request_start.date()
                    routine_start_normalized = datetime.combine(request_date, departure_time_start.time())
                    routine_end_normalized = datetime.combine(request_date, departure_time_end.time())
                    
                    # If routine end time is before start time (e.g., 23:30-00:30), it spans midnight
                    if routine_end_normalized < routine_start_normalized:
                        routine_end_normalized += timedelta(days=1)
                    
                    if not self._time_ranges_overlap(
                        request_start, request_end,
                        routine_start_normalized, routine_end_normalized
                    ):
                        logger.info(f"⏰ Skipping request {request.get('_id')} - time ranges don't overlap (request: {request_start}-{request_end}, routine normalized: {routine_start_normalized}-{routine_end_normalized})")
                        continue
                    else:
                        logger.info(f"✅ Request {request.get('_id')} matches routine: request range [{request_start} - {request_end}] overlaps with routine range [{routine_start_normalized} - {routine_end_normalized}]")
                # Otherwise, check if current time is within request time range
                else:
                    if not is_current_time_in_range(request_start, request_end):
                        logger.info(f"⏰ Skipping request {request.get('_id')} - current time not in range")
                        continue
            
            hitchhiker = self.db.get_collection("users").find_one({"_id": request['requester_id']})
            if not hitchhiker:
                continue
            
            # Calculate match score
            score = self._calculate_hitchhiker_match_score(
                request, destination, departure_time_start, departure_time_end, days
            )
            
            matching_requests.append({
                'ride_request_id': request['_id'],
                'hitchhiker_id': request['requester_id'],
                'hitchhiker_phone': request['requester_phone'],
                'hitchhiker_name': hitchhiker.get('full_name') or hitchhiker.get('whatsapp_name'),
                'score': score,
                'destination': request.get('destination'),
                'start_time_range': request.get('start_time_range'),
                'end_time_range': request.get('end_time_range')
            })
        
        # Sort by score (highest first)
        sorted_requests = sorted(matching_requests, key=lambda x: x['score'], reverse=True)
        logger.info(f"✅ Found {len(sorted_requests)} matching hitchhikers (after scoring)")
        return sorted_requests
    
    def _calculate_hitchhiker_match_score(self, request: Dict[str, Any], destination: str,
                                         departure_time_start: datetime = None, departure_time_end: datetime = None,
                                         days: str = None) -> float:
        """Calculate match score for a hitchhiker request"""
        score = 1.0
        
        # Exact destination match
        if request.get('destination') == destination:
            score += 2.0
        
        # Time range matching - check if ranges overlap
        request_start = request.get('start_time_range')
        request_end = request.get('end_time_range')
        
        if departure_time_start and departure_time_end and request_start and request_end:
            if self._time_ranges_overlap(request_start, request_end, departure_time_start, departure_time_end):
                score += 1.5
        
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
            
            # Check if driver has 'always' preference for sharing name
            # If so, mark match for auto-approval
            driver = self.db.get_collection("users").find_one({"_id": driver_id})
            if driver:
                share_name_preference = driver.get('share_name_with_hitchhiker')
                if not share_name_preference:
                    profile = driver.get('profile', {})
                    share_name_preference = profile.get('share_name_with_hitchhiker')
                
                if share_name_preference == 'always':
                    # Mark match for auto-approval
                    self.db.get_collection("matches").update_one(
                        {"_id": match_doc['_id']},
                        {"$set": {"auto_approve": True}}
                    )
                    logger.info(f"✅ Marked match {match_doc.get('match_id', '')} for auto-approval (driver {driver_phone} has 'always' preference)")
            
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


