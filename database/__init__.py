"""
Database operations
"""

from .firestore_client import (
    initialize_db,
    get_db,
    get_or_create_user,
    add_message_to_history,
    update_user_role_and_data,
    add_user_ride_or_request,
    get_user_rides_and_requests,
    remove_user_ride_or_request,
    get_drivers_by_route,
    get_hitchhiker_requests
)

__all__ = [
    "initialize_db",
    "get_db",
    "get_or_create_user",
    "add_message_to_history",
    "update_user_role_and_data",
    "add_user_ride_or_request",
    "get_user_rides_and_requests",
    "remove_user_ride_or_request",
    "get_drivers_by_route",
    "get_hitchhiker_requests"
]

