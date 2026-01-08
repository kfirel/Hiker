#!/usr/bin/env python3
"""
Check what data exists in Firestore for specific users
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


async def check_user(phone: str):
    """Check what rides/requests exist for a user"""
    from database import get_user_rides_and_requests
    
    logger.info(f"\n{'='*80}")
    logger.info(f"📱 Checking user: {phone}")
    logger.info(f"{'='*80}")
    
    data = await get_user_rides_and_requests(phone)
    
    driver_rides = data.get("driver_rides", [])
    hitchhiker_requests = data.get("hitchhiker_requests", [])
    
    logger.info(f"\n🚗 Driver Rides: {len(driver_rides)}")
    for i, ride in enumerate(driver_rides, 1):
        logger.info(f"\n   {i}. ID: {ride.get('id')}")
        logger.info(f"      Active: {ride.get('active')}")
        logger.info(f"      Origin: {ride.get('origin', 'N/A')}")
        logger.info(f"      Destination: {ride.get('destination')}")
        logger.info(f"      Date: {ride.get('travel_date', 'N/A')}")
        logger.info(f"      Days: {ride.get('days', 'N/A')}")
        logger.info(f"      Time: {ride.get('departure_time')}")
        logger.info(f"      Route points: {ride.get('route_num_points', 0)}")
        logger.info(f"      Route distance: {ride.get('route_distance_km', 0):.1f} km")
        logger.info(f"      Route pending: {ride.get('route_calculation_pending', False)}")
        logger.info(f"      Has flat coords: {bool(ride.get('route_coordinates_flat'))}")
    
    logger.info(f"\n🎒 Hitchhiker Requests: {len(hitchhiker_requests)}")
    for i, req in enumerate(hitchhiker_requests, 1):
        logger.info(f"\n   {i}. ID: {req.get('id')}")
        logger.info(f"      Active: {req.get('active')}")
        logger.info(f"      Origin: {req.get('origin', 'N/A')}")
        logger.info(f"      Destination: {req.get('destination')}")
        logger.info(f"      Date: {req.get('travel_date')}")
        logger.info(f"      Time: {req.get('departure_time')}")
        logger.info(f"      Flexibility: {req.get('flexibility', 'N/A')}")


async def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/check_firestore_data.py <phone1> [phone2] [phone3]...")
        print("\nExample:")
        print("  python scripts/check_firestore_data.py 972524297932 972526565380")
        sys.exit(1)
    
    phones = sys.argv[1:]
    
    for phone in phones:
        await check_user(phone)
    
    logger.info(f"\n{'='*80}\n")


if __name__ == "__main__":
    asyncio.run(main())



