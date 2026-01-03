"""
Debug specific matching scenario from production:
- Driver: Gvar'am → Tel Aviv, 16:40, 2026-01-02 (ride ID: 9ec43683-6b14-4594-97ff-24ca291fc412)
- Hitchhiker: Gvar'am → Ashdod, 17:00, 2026-01-02, flexible

This script loads actual data from Firestore and runs the matching logic locally
to debug why the match isn't happening in production.
"""

import asyncio
import sys
import os
import logging

# Setup path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    datefmt='%H:%M:%S'
)

logger = logging.getLogger(__name__)


async def load_driver_from_firestore(phone_number: str, ride_id: str):
    """Load driver data from Firestore"""
    from database import get_user_rides_and_requests
    
    logger.info(f"📥 Loading driver data from Firestore...")
    data = await get_user_rides_and_requests(phone_number)
    driver_rides = data.get("driver_rides", [])
    
    for ride in driver_rides:
        if ride.get("id") == ride_id:
            logger.info(f"✅ Found driver ride: {ride.get('destination')}")
            logger.info(f"   Route points: {ride.get('route_num_points')}")
            logger.info(f"   Route distance: {ride.get('route_distance_km')} km")
            logger.info(f"   Route calculation pending: {ride.get('route_calculation_pending')}")
            return ride
    
    logger.error(f"❌ Driver ride not found: {ride_id}")
    return None


async def load_hitchhiker_from_firestore(phone_number: str):
    """Load hitchhiker data from Firestore"""
    from database import get_user_rides_and_requests
    
    logger.info(f"📥 Loading hitchhiker data from Firestore...")
    data = await get_user_rides_and_requests(phone_number)
    hitchhiker_requests = data.get("hitchhiker_requests", [])
    
    if hitchhiker_requests:
        hitchhiker = hitchhiker_requests[0]
        logger.info(f"✅ Found hitchhiker request: {hitchhiker.get('destination')}")
        logger.info(f"   Departure time: {hitchhiker.get('departure_time')}")
        logger.info(f"   Flexibility: {hitchhiker.get('flexibility')}")
        return hitchhiker
    
    logger.error(f"❌ No hitchhiker requests found")
    return None


async def test_driver_to_hitchhiker_match():
    """
    Test if driver (Gvar'am→Tel Aviv, 16:40) matches hitchhiker (Gvar'am→Ashdod, 17:00, flexible)
    """
    logger.info("\n" + "="*80)
    logger.info("🧪 Testing Driver → Hitchhiker Match")
    logger.info("="*80 + "\n")
    
    # Load actual data from Firestore
    driver_phone = "972524297932"  # Kfir
    driver_ride_id = "9ec43683-6b14-4594-97ff-24ca291fc412"
    hitchhiker_phone = "972526565380"  # Erez
    
    driver = await load_driver_from_firestore(driver_phone, driver_ride_id)
    hitchhiker = await load_hitchhiker_from_firestore(hitchhiker_phone)
    
    if not driver or not hitchhiker:
        logger.error("❌ Failed to load data from Firestore")
        return
    
    # Add required fields for matching
    driver["phone_number"] = driver_phone
    driver["name"] = driver.get("name", "Test Driver")
    
    logger.info("\n" + "-"*80)
    logger.info("📋 Driver Data:")
    logger.info("-"*80)
    logger.info(f"   Origin: {driver.get('origin', 'גברעם')}")
    logger.info(f"   Destination: {driver['destination']}")
    logger.info(f"   Date: {driver.get('travel_date')}")
    logger.info(f"   Time: {driver['departure_time']}")
    logger.info(f"   Route points: {driver.get('route_num_points')}")
    logger.info(f"   Route distance: {driver.get('route_distance_km')} km")
    logger.info(f"   Has flat coords: {bool(driver.get('route_coordinates_flat'))}")
    
    logger.info("\n" + "-"*80)
    logger.info("📋 Hitchhiker Data:")
    logger.info("-"*80)
    logger.info(f"   Origin: {hitchhiker.get('origin', 'גברעם')}")
    logger.info(f"   Destination: {hitchhiker['destination']}")
    logger.info(f"   Date: {hitchhiker.get('travel_date')}")
    logger.info(f"   Time: {hitchhiker['departure_time']}")
    logger.info(f"   Flexibility: {hitchhiker.get('flexibility')}")
    
    # Run the matching logic
    logger.info("\n" + "-"*80)
    logger.info("🔍 Running Matching Logic...")
    logger.info("-"*80 + "\n")
    
    from services.matching_service import find_hitchhikers_for_driver
    
    try:
        matches = await find_hitchhikers_for_driver(driver)
        
        logger.info("\n" + "="*80)
        if matches:
            logger.info(f"✅ SUCCESS! Found {len(matches)} match(es)")
            for i, match in enumerate(matches, 1):
                logger.info(f"   {i}. {match.get('name')} to {match['destination']}")
        else:
            logger.error(f"❌ NO MATCHES FOUND")
            logger.error(f"   Expected to match: {hitchhiker.get('name')} to {hitchhiker['destination']}")
        logger.info("="*80 + "\n")
        
    except Exception as e:
        logger.error(f"\n❌ EXCEPTION during matching: {e}", exc_info=True)


async def test_hitchhiker_to_driver_match():
    """
    Test reverse: if hitchhiker (Gvar'am→Ashdod, 17:00, flexible) finds driver (Gvar'am→Tel Aviv, 16:40)
    """
    logger.info("\n" + "="*80)
    logger.info("🧪 Testing Hitchhiker → Driver Match (Reverse)")
    logger.info("="*80 + "\n")
    
    # Load actual data from Firestore
    driver_phone = "972524297932"  # Kfir
    driver_ride_id = "9ec43683-6b14-4594-97ff-24ca291fc412"
    hitchhiker_phone = "972526565380"  # Erez
    
    hitchhiker = await load_hitchhiker_from_firestore(hitchhiker_phone)
    
    if not hitchhiker:
        logger.error("❌ Failed to load hitchhiker data from Firestore")
        return
    
    # Add required fields for matching
    hitchhiker["phone_number"] = hitchhiker_phone
    hitchhiker["name"] = hitchhiker.get("name", "Test Hitchhiker")
    
    logger.info(f"📋 Looking for drivers for: {hitchhiker['destination']}, {hitchhiker.get('travel_date')}, {hitchhiker['departure_time']}")
    
    # Run the matching logic
    from services.matching_service import find_drivers_for_hitchhiker
    
    try:
        matches = await find_drivers_for_hitchhiker(hitchhiker)
        
        logger.info("\n" + "="*80)
        if matches:
            logger.info(f"✅ SUCCESS! Found {len(matches)} match(es)")
            for i, match in enumerate(matches, 1):
                logger.info(f"   {i}. {match.get('name')} to {match['destination']}")
        else:
            logger.error(f"❌ NO MATCHES FOUND")
        logger.info("="*80 + "\n")
        
    except Exception as e:
        logger.error(f"\n❌ EXCEPTION during matching: {e}", exc_info=True)


async def main():
    """Run all tests"""
    logger.info("\n" + "="*80)
    logger.info("🚀 Starting Match Debug Tests")
    logger.info("="*80)
    
    # Test both directions
    await test_driver_to_hitchhiker_match()
    await test_hitchhiker_to_driver_match()
    
    logger.info("\n" + "="*80)
    logger.info("✅ Tests complete")
    logger.info("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())

