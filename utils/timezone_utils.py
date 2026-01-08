"""
Timezone utilities for Israel time
Ensures all datetime operations use Asia/Jerusalem timezone
"""

from datetime import datetime
from zoneinfo import ZoneInfo

# Israel timezone
ISRAEL_TZ = ZoneInfo("Asia/Jerusalem")


def get_israel_now() -> datetime:
    """
    Get current datetime in Israel timezone
    
    Returns:
        datetime object with Israel timezone
    """
    return datetime.now(ISRAEL_TZ)


def get_israel_time() -> datetime:
    """
    Alias for get_israel_now() for backward compatibility
    
    Returns:
        datetime object with Israel timezone
    """
    return get_israel_now()


def israel_now_isoformat() -> str:
    """
    Get current Israel time as ISO format string
    
    Returns:
        ISO format string with timezone info
    """
    return get_israel_now().isoformat()



