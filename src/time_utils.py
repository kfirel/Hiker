"""
Time utility functions for converting various time formats to time ranges
"""
from datetime import datetime, timedelta
from typing import Tuple, Optional
import logging
import re

logger = logging.getLogger(__name__)


def parse_time_to_range(time_input: str, time_type: str = None) -> Tuple[Optional[datetime], Optional[datetime]]:
    """
    Convert various time inputs to a time range (start_time, end_time)
    
    Args:
        time_input: Time input string (can be ride_timing, time_range, specific_datetime, etc.)
        time_type: Optional type hint ("soon", "range", "specific", "now", "30min", etc.)
    
    Returns:
        Tuple of (start_datetime, end_datetime) or (None, None) if parsing fails
    """
    now = datetime.now()
    
    # Handle ride_timing values (from ask_hitchhiker_when_need_ride)
    if time_type == "soon" or time_input in ["now", "1"]:
        # "ממש עכשיו" - now to now + 30 minutes
        return now, now + timedelta(minutes=30)
    
    if time_input in ["30min", "2"]:
        # "בחצי שעה הקרובה" - now to now + 30 minutes
        return now, now + timedelta(minutes=30)
    
    if time_input in ["1hour", "3"]:
        # "בשעה הקרובה" - now to now + 1 hour
        return now, now + timedelta(hours=1)
    
    if time_input in ["2-5hours", "4"]:
        # "בשעות הקרובות (2-5 שעות)" - now + 2 hours to now + 5 hours
        return now + timedelta(hours=2), now + timedelta(hours=5)
    
    # Handle time_range format (e.g., "08:00-10:00" or "7-9")
    if time_type == "range" or (time_input and '-' in time_input and ':' in time_input.split('-')[0]):
        return parse_time_range_string(time_input, now)
    
    # Handle specific_datetime format (e.g., "15/11/2025 14:30" or "מחר 10:00")
    if time_type == "specific" or (time_input and ('/' in time_input or 'מחר' in time_input or 'היום' in time_input)):
        return parse_specific_datetime(time_input, now)
    
    # Default: if no specific format, assume "now" to "now + 30 minutes"
    logger.warning(f"Could not parse time input '{time_input}' with type '{time_type}', defaulting to now + 30min")
    return now, now + timedelta(minutes=30)


def parse_time_range_string(time_range: str, base_date: datetime = None) -> Tuple[datetime, datetime]:
    """
    Parse time range string like "08:00-10:00" or "7-9" to datetime range
    
    Args:
        time_range: Time range string (e.g., "08:00-10:00", "7-9", "14:30-17:00")
        base_date: Base date to use (defaults to today)
    
    Returns:
        Tuple of (start_datetime, end_datetime)
    """
    if base_date is None:
        base_date = datetime.now()
    
    # Use today's date
    today = base_date.date()
    
    # Split by '-'
    parts = time_range.split('-')
    if len(parts) != 2:
        raise ValueError(f"Invalid time range format: {time_range}")
    
    start_str = parts[0].strip()
    end_str = parts[1].strip()
    
    # Parse start time
    start_time = parse_time_string(start_str)
    start_datetime = datetime.combine(today, start_time)
    
    # Parse end time
    end_time = parse_time_string(end_str)
    end_datetime = datetime.combine(today, end_time)
    
    # If end time is before start time, assume it's next day
    if end_datetime < start_datetime:
        end_datetime += timedelta(days=1)
    
    return start_datetime, end_datetime


def parse_time_string(time_str: str):
    """
    Parse time string like "08:00", "8:00", "7", "14:30" to time object
    
    Args:
        time_str: Time string
    
    Returns:
        time object
    """
    from datetime import time
    
    time_str = time_str.strip()
    
    # Handle formats like "7" or "8" (just hour)
    if ':' not in time_str:
        hour = int(time_str)
        return time(hour=hour, minute=0)
    
    # Handle formats like "08:00" or "14:30"
    parts = time_str.split(':')
    hour = int(parts[0])
    minute = int(parts[1]) if len(parts) > 1 else 0
    
    return time(hour=hour, minute=minute)


def parse_specific_datetime(datetime_str: str, base_date: datetime = None) -> Tuple[datetime, datetime]:
    """
    Parse specific datetime string like "15/11/2025 14:30" or "מחר 10:00"
    
    Args:
        datetime_str: Datetime string
        base_date: Base date for relative dates like "מחר"
    
    Returns:
        Tuple of (start_datetime, end_datetime) - end is start + 1 hour
    """
    if base_date is None:
        base_date = datetime.now()
    
    datetime_str = datetime_str.strip()
    
    # Handle "מחר" (tomorrow)
    if 'מחר' in datetime_str:
        date = base_date.date() + timedelta(days=1)
        # Extract time
        time_match = re.search(r'(\d{1,2}):?(\d{2})?', datetime_str)
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2)) if time_match.group(2) else 0
        else:
            hour = 10
            minute = 0
        start_datetime = datetime.combine(date, datetime.time(hour=hour, minute=minute))
        return start_datetime, start_datetime + timedelta(hours=1)
    
    # Handle "היום" (today)
    if 'היום' in datetime_str:
        date = base_date.date()
        # Extract time
        time_match = re.search(r'(\d{1,2}):?(\d{2})?', datetime_str)
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2)) if time_match.group(2) else 0
        else:
            hour = 10
            minute = 0
        start_datetime = datetime.combine(date, datetime.time(hour=hour, minute=minute))
        # If time has passed today, assume tomorrow
        if start_datetime < base_date:
            start_datetime += timedelta(days=1)
        return start_datetime, start_datetime + timedelta(hours=1)
    
    # Handle format "DD/MM/YYYY HH:MM" or "DD/MM/YYYY HH:MM:SS"
    date_time_match = re.match(r'(\d{1,2})/(\d{1,2})/(\d{4})\s+(\d{1,2}):?(\d{2})?', datetime_str)
    if date_time_match:
        day = int(date_time_match.group(1))
        month = int(date_time_match.group(2))
        year = int(date_time_match.group(3))
        hour = int(date_time_match.group(4))
        minute = int(date_time_match.group(5)) if date_time_match.group(5) else 0
        
        start_datetime = datetime(year=year, month=month, day=day, hour=hour, minute=minute)
        return start_datetime, start_datetime + timedelta(hours=1)
    
    # Default: parse as time only, use today
    time_match = re.search(r'(\d{1,2}):?(\d{2})?', datetime_str)
    if time_match:
        hour = int(time_match.group(1))
        minute = int(time_match.group(2)) if time_match.group(2) else 0
        start_datetime = datetime.combine(base_date.date(), datetime.time(hour=hour, minute=minute))
        # If time has passed today, assume tomorrow
        if start_datetime < base_date:
            start_datetime += timedelta(days=1)
        return start_datetime, start_datetime + timedelta(hours=1)
    
    # Fallback: use base_date + 1 hour
    logger.warning(f"Could not parse datetime string '{datetime_str}', using base_date + 1 hour")
    return base_date, base_date + timedelta(hours=1)


def is_current_time_in_range(start_time: datetime, end_time: datetime) -> bool:
    """
    Check if current time is within the given time range
    
    Args:
        start_time: Start datetime
        end_time: End datetime
    
    Returns:
        True if current time is within range, False otherwise
    """
    from datetime import datetime as dt
    now = dt.now()
    
    # Handle FakeDatetime from freezegun - convert to regular datetime if needed
    if hasattr(start_time, 'year'):  # It's a datetime-like object
        try:
            # Try to compare directly
            return start_time <= now <= end_time
        except TypeError:
            # If comparison fails, convert FakeDatetime to regular datetime
            start_time = dt(start_time.year, start_time.month, start_time.day, 
                          start_time.hour, start_time.minute, start_time.second)
            end_time = dt(end_time.year, end_time.month, end_time.day,
                        end_time.hour, end_time.minute, end_time.second)
            return start_time <= now <= end_time
    
    return start_time <= now <= end_time


def parse_routine_departure_time(departure_time_str: str, days: str = None) -> Tuple[Optional[datetime], Optional[datetime]]:
    """
    Parse routine departure time to a time range for today
    
    Args:
        departure_time_str: Time string like "07:00" or "7:00"
        days: Days string like "א-ה" (optional, for future use)
    
    Returns:
        Tuple of (start_datetime, end_datetime) - creates 1 hour window around departure time
    """
    if not departure_time_str:
        return None, None
    
    try:
        time_obj = parse_time_string(departure_time_str)
        today = datetime.now().date()
        start_datetime = datetime.combine(today, time_obj)
        
        # Create 30 minute window before and after departure time
        start_range = start_datetime - timedelta(minutes=30)
        end_range = start_datetime + timedelta(minutes=30)
        
        return start_range, end_range
    except Exception as e:
        logger.error(f"Error parsing routine departure time '{departure_time_str}': {e}")
        return None, None

