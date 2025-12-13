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
                # Use PreferenceHelper for consistent name handling
                from src.utils.preference_helper import PreferenceHelper
                driver_name = PreferenceHelper.get_driver_name(driver) or 'נהג'
                matching_drivers.append({
                    'driver_id': driver['_id'],
                    'driver_phone': driver['phone_number'],
                    'driver_name': driver_name,
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
                # Use PreferenceHelper for consistent name handling
                from src.utils.preference_helper import PreferenceHelper
                driver_name = PreferenceHelper.get_driver_name(driver) or 'נהג'
                matching_drivers.append({
                    'driver_id': driver['_id'],
                    'driver_phone': driver['phone_number'],
                    'driver_name': driver_name,
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
            days = routine.get('days', [])
            # Handle both array and string formats (backward compatibility)
            if isinstance(days, str):
                from src.validation import parse_days_to_array
                days = parse_days_to_array(days)
            if not self._is_day_in_routine_days(current_day, days):
                logger.debug(f"Routine {routine.get('_id')} not active for current day {current_day} (days: {days})")
                continue
            
            # Get routine departure time range
            departure_start = routine.get('departure_time_start')
            departure_end = routine.get('departure_time_end')
            
            if departure_start and departure_end:
                # If request has time range, check if ranges overlap
                # For routines, we need to normalize the dates to the request's date since routines are daily
                # Routines are stored with generic date (1900-01-01) - we normalize to request date
                if request_start_time and request_end_time:
                    # Normalize routine times to the request's date
                    request_date = request_start_time.date()
                    
                    # Extract time from routine (routines use generic date 1900-01-01)
                    routine_start_time = departure_start.time()
                    routine_end_time = departure_end.time()
                    
                    # Create normalized datetimes with request's date
                    routine_start_normalized = datetime.combine(request_date, routine_start_time)
                    routine_end_normalized = datetime.combine(request_date, routine_end_time)
                    
                    # Handle routines that cross midnight (e.g., 23:40 - 00:40)
                    # If routine_end_time < routine_start_time, it means the time crosses midnight
                    # In this case, we need to add a day to routine_end after normalization
                    if routine_end_time < routine_start_time:
                        # Original routine crosses midnight - add a day to normalized end time
                        routine_end_normalized = routine_end_normalized + timedelta(days=1)
                        logger.debug(f"🕐 Routine {routine.get('_id')} crosses midnight - adjusted end time to {routine_end_normalized}")
                    
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
                    # Normalize routine times to today's date first
                    today = now.date()
                    routine_start_time = departure_start.time()
                    routine_end_time = departure_end.time()
                    
                    routine_start_today = datetime.combine(today, routine_start_time)
                    routine_end_today = datetime.combine(today, routine_end_time)
                    
                    # Handle routines that cross midnight
                    if routine_end_time < routine_start_time:
                        routine_end_today = routine_end_today + timedelta(days=1)
                    
                    if is_current_time_in_range(routine_start_today, routine_end_today):
                        logger.info(f"✅ Routine {routine.get('_id')} matches: current time {now} is within routine range [{routine_start_today} - {routine_end_today}]")
                        matching_routines.append(routine)
                    else:
                        logger.debug(f"⏰ Routine {routine.get('_id')} time range [{routine_start_today} - {routine_end_today}] does not include current time {now}")
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
    
    def _is_day_in_routine_days(self, current_day: int, days: Any) -> bool:
        """
        Check if current day (0=Monday, 6=Sunday) is in routine days array
        
        Args:
            current_day: Current weekday (0=Monday, 6=Sunday)
            days: Days array like ["א", "ב", "ג", "ד", "ה"] or string for backward compatibility
        
        Returns:
            True if current day matches routine days
        """
        if not days:
            return False
        
        # Handle string format (backward compatibility)
        if isinstance(days, str):
            from src.validation import parse_days_to_array
            days = parse_days_to_array(days)
        
        # Handle array format
        if isinstance(days, list):
            # Hebrew day mapping: א=Sunday(6), ב=Monday(0), ג=Tuesday(1), ד=Wednesday(2), ה=Thursday(3), ו=Friday(4), ש=Saturday(5)
            hebrew_days = {'א': 6, 'ב': 0, 'ג': 1, 'ד': 2, 'ה': 3, 'ו': 4, 'ש': 5}
            
            # Check if current day is in the days array
            for day_char in days:
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
        Create matched drivers entries in ride_requests.matched_drivers array
        
        Args:
            ride_request_id: Ride request ID
            hitchhiker_id: Hitchhiker user ID
            matching_drivers: List of matching driver info
            
        Returns:
            List of created matched driver entries
        """
        ride_request = self.db.get_collection("ride_requests").find_one({"_id": ride_request_id})
        if not ride_request:
            logger.error(f"Ride request not found: {ride_request_id}")
            return []
        
        matched_drivers_entries = []
        
        for driver_info in matching_drivers:
            from src.database.models import create_matched_driver_entry
            
            # Check driver's preference for auto-approval
            driver = self.db.get_collection("users").find_one({"_id": driver_info['driver_id']})
            auto_approve = False
            if driver:
                share_name_preference = driver.get('share_name_with_hitchhiker')
                if not share_name_preference:
                    profile = driver.get('profile', {})
                    share_name_preference = profile.get('share_name_with_hitchhiker')
                if share_name_preference == 'always':
                    auto_approve = True
            
            matched_driver_entry = create_matched_driver_entry(
                driver_id=driver_info['driver_id'],
                driver_phone=driver_info['driver_phone'],
                status="pending_approval",
                auto_approve=auto_approve
            )
            
            matched_drivers_entries.append(matched_driver_entry)
        
        # Update ride request with matched drivers array
        self.db.get_collection("ride_requests").update_one(
            {"_id": ride_request_id},
            {
                "$set": {
                    "status": "matched",
                    "matched_drivers": matched_drivers_entries,
                    "updated_at": datetime.now()
                }
            }
        )
        
        logger.info(f"Created {len(matched_drivers_entries)} matched drivers for ride request {ride_request_id}")
        return matched_drivers_entries

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
                                         days: Any = None) -> float:
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
        Add matched driver entries to ride_requests.matched_drivers array
        
        Args:
            driver_id: Driver's user ID
            driver_phone: Driver's phone number
            matching_requests: List of matching hitchhiker request info
            routine_id: Optional routine ID (if matching from routine)
            offer_id: Optional offer ID (if matching from driver offer)
            
        Returns:
            List of created matched driver entries
        """
        matched_drivers_entries = []
        
        for request_info in matching_requests:
            ride_request_id = request_info['ride_request_id']
            hitchhiker_id = request_info['hitchhiker_id']
            
            # Get ride request to check if driver already matched
            ride_request = self.db.get_collection("ride_requests").find_one({"_id": ride_request_id})
            if not ride_request:
                logger.error(f"Ride request not found: {ride_request_id}")
                continue
            
            # Check if driver already in matched_drivers array
            matched_drivers = ride_request.get('matched_drivers', [])
            existing_driver = next(
                (d for d in matched_drivers if str(d.get('driver_id')) == str(driver_id)),
                None
            )
            
            if existing_driver:
                logger.info(f"Driver {driver_phone} already matched for request {ride_request_id}")
                matched_drivers_entries.append(existing_driver)
                continue
            
            # Check if driver has 'always' preference for sharing name
            driver = self.db.get_collection("users").find_one({"_id": driver_id})
            auto_approve = False
            if driver:
                share_name_preference = driver.get('share_name_with_hitchhiker')
                if not share_name_preference:
                    profile = driver.get('profile', {})
                    share_name_preference = profile.get('share_name_with_hitchhiker')
                if share_name_preference == 'always':
                    auto_approve = True
            
            from src.database.models import create_matched_driver_entry
            
            matched_driver_entry = create_matched_driver_entry(
                driver_id=driver_id,
                driver_phone=driver_phone,
                status="pending_approval",
                auto_approve=auto_approve
            )
            
            # Add routine/offer reference if available (store in entry for reference)
            if routine_id:
                matched_driver_entry['routine_id'] = routine_id
            if offer_id:
                matched_driver_entry['offer_id'] = offer_id
            
            # Add to matched_drivers array in ride_request
            self.db.get_collection("ride_requests").update_one(
                {"_id": ride_request_id},
                {
                    "$push": {"matched_drivers": matched_driver_entry},
                    "$set": {
                        "status": "matched",
                        "updated_at": datetime.now()
                    }
                }
            )
            
            if auto_approve:
                logger.info(f"✅ Marked matched driver for auto-approval (driver {driver_phone} has 'always' preference)")
            
            matched_drivers_entries.append(matched_driver_entry)
        
        logger.info(f"Created {len(matched_drivers_entries)} matched drivers for driver {driver_phone}")
        return matched_drivers_entries


