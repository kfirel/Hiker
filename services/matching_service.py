"""
Matching service
Logic for matching drivers with hitchhikers
"""

import logging
from typing import Dict, Any, List

from database import get_drivers_by_route, get_hitchhiker_requests

logger = logging.getLogger(__name__)


async def find_matches_for_user(
    role: str,
    role_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Find matches for a user (driver or hitchhiker)
    
    Args:
        role: User role ('driver' or 'hitchhiker')
        role_data: User's role-specific data
    
    Returns:
        Dictionary with matches found
    """
    destination = role_data.get("destination")
    
    if role == "hitchhiker":
        # Find drivers going to same destination
        drivers = await get_drivers_by_route(
            origin="גברעם",
            destination=destination
        )
        return {
            "matches_found": len(drivers),
            "drivers": drivers[:3],  # Return top 3 matches
            "role": "hitchhiker"
        }
    
    elif role == "driver":
        # Find hitchhikers looking for rides to same destination
        hitchhikers = await get_hitchhiker_requests(
            destination=destination
        )
        return {
            "matches_found": len(hitchhikers),
            "hitchhikers": hitchhikers[:3],  # Return top 3 matches
            "role": "driver"
        }
    
    return {
        "matches_found": 0,
        "role": role
    }

