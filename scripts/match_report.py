#!/usr/bin/env python3
"""
Generate detailed matching compatibility report for driver/hitchhiker pairs.

Usage:
    python scripts/match_report.py <driver_phone> <driver_ride_id> <hitchhiker_phone>

Example:
    python scripts/match_report.py 972524297932 9ec43683-6b14-4594-97ff-24ca291fc412 972526565380

This script:
1. Loads driver and hitchhiker data from Firestore
2. Runs through all compatibility checks step-by-step
3. Shows detailed results for each check (date, time, route, etc.)
4. Optionally generates a map visualization
"""

import asyncio
import sys
import os
from datetime import datetime
from typing import Optional, Tuple, Dict

# Setup path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Load service modules directly to avoid circular imports
import importlib.util

def load_module_directly(module_name: str, file_path: str):
    """Load a module directly from file path to avoid circular imports"""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

# Load modules
route_service = load_module_directly(
    "route_service",
    os.path.join(os.path.dirname(__file__), '..', 'services', 'route_service.py')
)
matching_service = load_module_directly(
    "matching_service",
    os.path.join(os.path.dirname(__file__), '..', 'services', 'matching_service.py')
)


class MatchReport:
    """Generate detailed compatibility report"""
    
    def __init__(self, driver: Dict, hitchhiker: Dict):
        self.driver = driver
        self.hitchhiker = hitchhiker
        self.checks = []
    
    def add_check(self, name: str, passed: bool, details: str):
        """Add a compatibility check result"""
        self.checks.append({
            "name": name,
            "passed": passed,
            "details": details
        })
    
    def print_report(self):
        """Print formatted report"""
        print("\n" + "="*80)
        print("📊 MATCHING COMPATIBILITY REPORT")
        print("="*80 + "\n")
        
        # Driver info
        print("🚗 DRIVER:")
        print(f"   Name: {self.driver.get('name', 'Unknown')}")
        print(f"   Route: {self.driver.get('origin', 'גברעם')} → {self.driver['destination']}")
        print(f"   Date: {self.driver.get('travel_date', 'N/A')} (Days: {self.driver.get('days', 'N/A')})")
        print(f"   Time: {self.driver['departure_time']}")
        print(f"   Route: {self.driver.get('route_num_points', 0)} points, {self.driver.get('route_distance_km', 0):.1f} km")
        
        # Hitchhiker info
        print("\n🎒 HITCHHIKER:")
        print(f"   Name: {self.hitchhiker.get('name', 'Unknown')}")
        print(f"   Route: {self.hitchhiker.get('origin', 'גברעם')} → {self.hitchhiker['destination']}")
        print(f"   Date: {self.hitchhiker.get('travel_date', 'N/A')}")
        print(f"   Time: {self.hitchhiker['departure_time']}")
        print(f"   Flexibility: {self.hitchhiker.get('flexibility', 'N/A')}")
        
        # Compatibility checks
        print("\n" + "-"*80)
        print("🔍 COMPATIBILITY CHECKS:")
        print("-"*80)
        
        all_passed = True
        for i, check in enumerate(self.checks, 1):
            status = "✅" if check["passed"] else "❌"
            print(f"\n{i}. {status} {check['name']}")
            print(f"   {check['details']}")
            if not check["passed"]:
                all_passed = False
        
        # Final result
        print("\n" + "="*80)
        if all_passed:
            print("✅ MATCH: All compatibility checks passed!")
        else:
            print("❌ NO MATCH: One or more checks failed")
        print("="*80 + "\n")
        
        return all_passed


async def load_driver(phone: str, ride_id: str) -> Optional[Dict]:
    """Load driver from Firestore"""
    from database import get_user_rides_and_requests
    
    data = await get_user_rides_and_requests(phone)
    for ride in data.get("driver_rides", []):
        if ride.get("id") == ride_id:
            ride["phone_number"] = phone
            return ride
    return None


async def load_hitchhiker(phone: str) -> Optional[Dict]:
    """Load first active hitchhiker request from Firestore"""
    from database import get_user_rides_and_requests
    
    data = await get_user_rides_and_requests(phone)
    requests = data.get("hitchhiker_requests", [])
    if requests:
        hitchhiker = requests[0]
        hitchhiker["phone_number"] = phone
        return hitchhiker
    return None


async def check_date_compatibility(driver: Dict, hitchhiker: Dict, report: MatchReport) -> bool:
    """Check if dates are compatible"""
    hitchhiker_date = hitchhiker.get("travel_date")
    
    if not hitchhiker_date:
        report.add_check(
            "Date Check",
            False,
            f"Hitchhiker missing travel_date"
        )
        return False
    
    if driver.get("days"):
        # Recurring driver
        day_name = datetime.strptime(hitchhiker_date, "%Y-%m-%d").strftime("%A")
        match = day_name in driver.get("days", [])
        report.add_check(
            "Date Check (Recurring Driver)",
            match,
            f"Hitchhiker date {hitchhiker_date} ({day_name}) {'is' if match else 'is NOT'} in driver's schedule {driver.get('days')}"
        )
        return match
    elif driver.get("travel_date"):
        # One-time driver
        match = driver["travel_date"] == hitchhiker_date
        report.add_check(
            "Date Check (One-time Driver)",
            match,
            f"Driver date {driver['travel_date']} {'matches' if match else 'does NOT match'} hitchhiker date {hitchhiker_date}"
        )
        return match
    else:
        report.add_check(
            "Date Check",
            False,
            f"Driver has no days or travel_date"
        )
        return False


async def check_time_compatibility(driver: Dict, hitchhiker: Dict, report: MatchReport) -> bool:
    """Check if times are compatible with flexibility"""
    driver_time = driver["departure_time"]
    hitchhiker_time = hitchhiker["departure_time"]
    
    # Calculate distance for flexibility
    origin_coords = route_service.geocode_address(hitchhiker.get("origin", "גברעם"))
    dest_coords = route_service.geocode_address(hitchhiker["destination"])
    
    if origin_coords and dest_coords:
        distance_km = route_service.calculate_distance_between_points(origin_coords, dest_coords)
        flexibility_level = hitchhiker.get("flexibility", "flexible")
        tolerance = matching_service._calculate_time_tolerance(flexibility_level, distance_km)
    else:
        tolerance = 30
        distance_km = 0
    
    # Parse times
    h1, m1 = map(int, driver_time.split(":"))
    h2, m2 = map(int, hitchhiker_time.split(":"))
    diff = abs((h1 * 60 + m1) - (h2 * 60 + m2))
    
    match = diff <= tolerance
    report.add_check(
        "Time Check",
        match,
        f"Driver: {driver_time}, Hitchhiker: {hitchhiker_time} (diff: {diff} min)\n"
        f"   Tolerance: ±{tolerance} min (flexibility: {hitchhiker.get('flexibility')}, distance: {distance_km:.1f} km)\n"
        f"   {'Within' if match else 'Outside'} acceptable range"
    )
    return match


async def check_destination_compatibility(driver: Dict, hitchhiker: Dict, report: MatchReport) -> Tuple[bool, Optional[str]]:
    """Check if destinations are compatible (direct or on-route)"""
    from rapidfuzz import fuzz
    
    driver_dest = driver["destination"]
    hitchhiker_dest = hitchhiker["destination"]
    
    # 1. Check direct match
    similarity = fuzz.ratio(driver_dest.lower(), hitchhiker_dest.lower())
    if similarity >= 70:
        report.add_check(
            "Destination Check",
            True,
            f"Direct match: '{driver_dest}' ≈ '{hitchhiker_dest}' (similarity: {similarity}%)"
        )
        return True, "direct"
    
    # 2. Check on-route
    route_coords = driver.get("route_coordinates")
    
    # Convert flat format if needed
    if not route_coords and driver.get("route_coordinates_flat"):
        flat_coords = driver["route_coordinates_flat"]
        route_coords = [(flat_coords[i], flat_coords[i+1]) for i in range(0, len(flat_coords), 2)]
    
    if not route_coords:
        if driver.get("route_calculation_pending"):
            report.add_check(
                "Destination Check",
                False,
                f"Route calculation still pending - cannot check on-route compatibility"
            )
        else:
            report.add_check(
                "Destination Check",
                False,
                f"No direct match and no route data available"
            )
        return False, None
    
    # Geocode destinations
    driver_origin_coords = route_service.geocode_address(driver.get("origin", "גברעם"))
    hitchhiker_coords = route_service.geocode_address(hitchhiker_dest)
    
    if not driver_origin_coords or not hitchhiker_coords:
        report.add_check(
            "Destination Check",
            False,
            f"Failed to geocode: driver_origin={bool(driver_origin_coords)}, hitchhiker={bool(hitchhiker_coords)}"
        )
        return False, None
    
    # Calculate distances
    distance_from_origin = route_service.calculate_distance_between_points(driver_origin_coords, hitchhiker_coords)
    dynamic_threshold = route_service.calculate_dynamic_threshold(distance_from_origin)
    min_distance = route_service.calculate_min_distance_to_route(route_coords, hitchhiker_coords)
    
    match = min_distance <= dynamic_threshold
    report.add_check(
        "Destination Check (On-Route)",
        match,
        f"No direct match, checking if '{hitchhiker_dest}' is on route to '{driver_dest}':\n"
        f"   Distance from origin: {distance_from_origin:.1f} km\n"
        f"   Dynamic threshold: {dynamic_threshold:.1f} km\n"
        f"   Distance from route: {min_distance:.1f} km\n"
        f"   {'Within' if match else 'Outside'} acceptable range"
    )
    
    return match, "on_route" if match else None


async def check_auto_approve(driver: Dict, report: MatchReport) -> bool:
    """Check if driver auto-approves matches"""
    auto_approve = driver.get("auto_approve_matches", True)
    report.add_check(
        "Auto-Approve Check",
        auto_approve,
        f"Driver {'DOES' if auto_approve else 'does NOT'} auto-approve matches"
    )
    return auto_approve


async def generate_map(driver: Dict, hitchhiker: Dict, output_file: str = "match_report_map.html"):
    """Generate HTML map visualization"""
    import folium
    
    # Create map centered on driver origin
    driver_origin_coords = route_service.geocode_address(driver.get("origin", "גברעם"))
    if not driver_origin_coords:
        logger.warning("Failed to geocode driver origin, cannot generate map")
        return None
    
    m = folium.Map(location=driver_origin_coords, zoom_start=10)
    
    # Add driver route
    route_coords = driver.get("route_coordinates")
    if not route_coords and driver.get("route_coordinates_flat"):
        flat_coords = driver["route_coordinates_flat"]
        route_coords = [(flat_coords[i], flat_coords[i+1]) for i in range(0, len(flat_coords), 2)]
    
    if route_coords:
        folium.PolyLine(
            route_coords,
            color="blue",
            weight=3,
            opacity=0.7,
            popup=f"Driver: {driver.get('origin', 'גברעם')} → {driver['destination']}"
        ).add_to(m)
    
    # Add driver markers
    folium.Marker(
        driver_origin_coords,
        popup=f"🚗 Start: {driver.get('origin', 'גברעם')}",
        icon=folium.Icon(color="green", icon="play")
    ).add_to(m)
    
    driver_dest_coords = route_service.geocode_address(driver["destination"])
    if driver_dest_coords:
        folium.Marker(
            driver_dest_coords,
            popup=f"🚗 End: {driver['destination']}",
            icon=folium.Icon(color="red", icon="stop")
        ).add_to(m)
    
    # Add hitchhiker destination
    hitchhiker_coords = route_service.geocode_address(hitchhiker["destination"])
    if hitchhiker_coords:
        folium.Marker(
            hitchhiker_coords,
            popup=f"🎒 Hitchhiker to: {hitchhiker['destination']}",
            icon=folium.Icon(color="orange", icon="user")
        ).add_to(m)
    
    # Save map
    output_path = os.path.join(os.path.dirname(__file__), "..", "tests", "outputs", output_file)
    m.save(output_path)
    logger.info(f"💾 Map saved to: {output_path}")
    
    return output_path


async def main():
    """Main entry point"""
    if len(sys.argv) < 4:
        print("Usage: python scripts/match_report.py <driver_phone> <driver_ride_id> <hitchhiker_phone> [--map]")
        print("\nExample:")
        print("  python scripts/match_report.py 972524297932 9ec43683-6b14-4594-97ff-24ca291fc412 972526565380")
        print("  python scripts/match_report.py 972524297932 9ec43683-6b14-4594-97ff-24ca291fc412 972526565380 --map")
        sys.exit(1)
    
    # Initialize database
    from database import initialize_db
    initialize_db()
    
    driver_phone = sys.argv[1]
    driver_ride_id = sys.argv[2]
    hitchhiker_phone = sys.argv[3]
    generate_map_flag = "--map" in sys.argv
    
    # Load data
    logger.info(f"📥 Loading driver: {driver_phone}, ride: {driver_ride_id}")
    driver = await load_driver(driver_phone, driver_ride_id)
    
    logger.info(f"📥 Loading hitchhiker: {hitchhiker_phone}")
    hitchhiker = await load_hitchhiker(hitchhiker_phone)
    
    if not driver:
        logger.error(f"❌ Driver not found: {driver_phone}, ride: {driver_ride_id}")
        sys.exit(1)
    
    if not hitchhiker:
        logger.error(f"❌ Hitchhiker not found: {hitchhiker_phone}")
        sys.exit(1)
    
    # Generate report
    report = MatchReport(driver, hitchhiker)
    
    # Run all checks
    date_ok = await check_date_compatibility(driver, hitchhiker, report)
    time_ok = await check_time_compatibility(driver, hitchhiker, report)
    dest_ok, match_type = await check_destination_compatibility(driver, hitchhiker, report)
    auto_ok = await check_auto_approve(driver, report)
    
    # Print report
    match = report.print_report()
    
    # Generate map if requested
    if generate_map_flag:
        logger.info("🗺️ Generating map visualization...")
        map_path = await generate_map(driver, hitchhiker)
        if map_path:
            print(f"\n📍 Map saved to: {map_path}")
            print(f"   Open in browser: file://{os.path.abspath(map_path)}")
    
    # Exit code indicates match status
    sys.exit(0 if match else 1)


if __name__ == "__main__":
    asyncio.run(main())

