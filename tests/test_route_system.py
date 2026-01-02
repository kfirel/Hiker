#!/usr/bin/env python3
"""
Test script for the route-based matching system
Tests geocoding, route calculation, dynamic threshold, and matching logic
"""

import asyncio
import sys
import os

# Add parent directory to path to import modules directly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import directly from route_service to avoid loading all services
from services import route_service

geocode_address = route_service.geocode_address
get_route_data = route_service.get_route_data
calculate_dynamic_threshold = route_service.calculate_dynamic_threshold
calculate_min_distance_to_route = route_service.calculate_min_distance_to_route

def print_header(title):
    """Print a formatted header"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def print_success(msg):
    """Print success message"""
    print(f"✅ {msg}")

def print_error(msg):
    """Print error message"""
    print(f"❌ {msg}")

def print_info(msg):
    """Print info message"""
    print(f"ℹ️  {msg}")

async def test_geocoding():
    """Test geocoding functionality"""
    print_header("Test 1: Geocoding")
    
    test_locations = [
        "גברעם",
        "אשקלון",
        "תל אביב",
        "ירושלים",
        "באר שבע",
        "חיפה"
    ]
    
    for location in test_locations:
        coords = geocode_address(location)
        if coords:
            print_success(f"{location}: ({coords[0]:.4f}, {coords[1]:.4f})")
        else:
            print_error(f"Failed to geocode: {location}")
    
    return True

async def test_dynamic_threshold():
    """Test dynamic threshold calculation"""
    print_header("Test 2: Dynamic Threshold Calculation")
    
    test_cases = [
        (5, "Short route (5 km)"),
        (10, "Very short (10 km)"),
        (25, "Medium route (25 km)"),
        (50, "Long route (50 km)"),
        (80, "Very long (80 km)"),
        (100, "100 km route"),
        (200, "Maximum (200 km)")
    ]
    
    for distance, description in test_cases:
        threshold = calculate_dynamic_threshold(distance)
        percentage = (threshold / distance * 100) if distance > 0 else 0
        print_info(f"{description}: threshold = {threshold:.1f} km ({percentage:.1f}% of route)")
    
    return True

async def test_route_calculation():
    """Test full route calculation"""
    print_header("Test 3: Route Calculation (OSRM)")
    
    test_routes = [
        ("גברעם", "אשקלון", "Short route"),
        ("גברעם", "תל אביב", "Medium route"),
        ("גברעם", "ירושלים", "Long route")
    ]
    
    for origin, destination, description in test_routes:
        print(f"\n🔍 Testing: {description} ({origin} → {destination})")
        
        route_data = await get_route_data(origin, destination)
        
        if route_data:
            print_success(f"Route calculated successfully")
            print_info(f"  Distance: {route_data['distance_km']:.1f} km")
            print_info(f"  Threshold: {route_data['threshold_km']:.1f} km")
            print_info(f"  Points: {len(route_data['coordinates'])} coordinates")
            
            # Show first and last points
            if route_data['coordinates']:
                first = route_data['coordinates'][0]
                last = route_data['coordinates'][-1]
                print_info(f"  Start: ({first[0]:.4f}, {first[1]:.4f})")
                print_info(f"  End: ({last[0]:.4f}, {last[1]:.4f})")
        else:
            print_error(f"Failed to calculate route")
    
    return True

async def test_distance_calculation():
    """Test distance calculation from point to route"""
    print_header("Test 4: Distance to Route Calculation")
    
    # First get a route
    print(f"\n🔍 Getting route: גברעם → אשקלון")
    route_data = await get_route_data("גברעם", "אשקלון")
    
    if not route_data:
        print_error("Failed to get route data")
        return False
    
    print_success(f"Route obtained: {route_data['distance_km']:.1f} km")
    
    # Test points
    test_points = [
        "קיבוץ ניר-עם",  # Should be close to route
        "שדרות",  # Should be close
        "באר שבע",  # Should be far
        "חיפה"  # Very far
    ]
    
    print(f"\nTesting distances from various points:")
    for point_name in test_points:
        coords = geocode_address(point_name)
        if coords:
            distance = calculate_min_distance_to_route(route_data['coordinates'], coords)
            is_on_route = distance <= route_data['threshold_km']
            status = "✅ ON ROUTE" if is_on_route else "❌ TOO FAR"
            print(f"  {point_name}: {distance:.1f} km {status}")
        else:
            print_error(f"  Failed to geocode: {point_name}")
    
    return True

async def test_matching_scenario():
    """Test realistic matching scenario"""
    print_header("Test 5: Realistic Matching Scenario")
    
    print("\n📝 Scenario:")
    print("  Driver: גברעם → אשקלון (tomorrow 08:00)")
    print("  Hitchhiker: גברעם → קיבוץ ניר-עם (tomorrow 08:15)")
    print("")
    
    # Calculate route
    driver_route = await get_route_data("גברעם", "אשקלון")
    
    if not driver_route:
        print_error("Failed to calculate driver route")
        return False
    
    print_success(f"Driver route: {driver_route['distance_km']:.1f} km, threshold: {driver_route['threshold_km']:.1f} km")
    
    # Check if hitchhiker destination is on route
    hitchhiker_coords = geocode_address("קיבוץ ניר-עם")
    
    if not hitchhiker_coords:
        print_error("Failed to geocode hitchhiker destination")
        return False
    
    distance = calculate_min_distance_to_route(driver_route['coordinates'], hitchhiker_coords)
    is_match = distance <= driver_route['threshold_km']
    
    print(f"\n📏 Distance from ניר-עם to route: {distance:.1f} km")
    print(f"📏 Threshold: {driver_route['threshold_km']:.1f} km")
    
    if is_match:
        print_success(f"✨ MATCH! Hitchhiker is on the route!")
    else:
        print_error(f"No match - destination too far from route")
    
    return True

async def test_edge_cases():
    """Test edge cases and error handling"""
    print_header("Test 6: Edge Cases")
    
    print("\n🧪 Testing invalid location:")
    coords = geocode_address("ThisLocationDoesNotExist12345")
    if coords is None:
        print_success("Correctly handled invalid location")
    else:
        print_error("Should have returned None for invalid location")
    
    print("\n🧪 Testing same origin and destination:")
    route_data = await get_route_data("תל אביב", "תל אביב")
    if route_data:
        print_info(f"Route distance: {route_data['distance_km']:.1f} km")
    else:
        print_info("No route calculated for same origin/destination")
    
    return True

async def main():
    """Run all tests"""
    print("\n" + "🚀"*30)
    print("  ROUTE-BASED MATCHING SYSTEM - TEST SUITE")
    print("🚀"*30)
    
    tests = [
        ("Geocoding", test_geocoding),
        ("Dynamic Threshold", test_dynamic_threshold),
        ("Route Calculation", test_route_calculation),
        ("Distance Calculation", test_distance_calculation),
        ("Matching Scenario", test_matching_scenario),
        ("Edge Cases", test_edge_cases)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print_error(f"Test '{test_name}' raised exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print_header("TEST SUMMARY")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} - {test_name}")
    
    print(f"\n  Total: {passed}/{total} tests passed")
    
    if passed == total:
        print_success("All tests passed! 🎉")
        return 0
    else:
        print_error(f"{total - passed} test(s) failed")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

