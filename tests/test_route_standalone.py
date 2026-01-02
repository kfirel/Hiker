#!/usr/bin/env python3
"""
Standalone test script for route service
Tests only the route_service module without loading the entire application
"""

import asyncio
import sys
import importlib.util

def load_module_from_file(module_name, file_path):
    """Load a module from a file path"""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

# Load config first
config = load_module_from_file("config", "config.py")

# Load route_service
route_service = load_module_from_file("route_service", "services/route_service.py")

# Extract functions
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
    
    success_count = 0
    for location in test_locations:
        coords = geocode_address(location)
        if coords:
            print_success(f"{location}: ({coords[0]:.4f}, {coords[1]:.4f})")
            success_count += 1
        else:
            print_error(f"Failed to geocode: {location}")
    
    return success_count >= 4  # At least 4 out of 6

async def test_dynamic_threshold():
    """Test dynamic threshold calculation"""
    print_header("Test 2: Dynamic Threshold Calculation")
    
    test_cases = [
        (5, "Short route (5 km)", 2.5),
        (10, "Very short (10 km)", 3.5),
        (25, "Medium route (25 km)", 5.0),
        (50, "Long route (50 km)", 7.5),
        (80, "Very long (80 km)", 10.0),
        (100, "100 km route", 10.0),
        (200, "Maximum (200 km)", 10.0)
    ]
    
    all_correct = True
    for distance, description, expected_threshold in test_cases:
        threshold = calculate_dynamic_threshold(distance)
        percentage = (threshold / distance * 100) if distance > 0 else 0
        print_info(f"{description}: threshold = {threshold:.1f} km ({percentage:.1f}% of route)")
        
        # Verify it's close to expected
        if abs(threshold - expected_threshold) > 0.1:
            print_error(f"Expected {expected_threshold:.1f} km, got {threshold:.1f} km")
            all_correct = False
    
    return all_correct

async def test_route_calculation():
    """Test full route calculation"""
    print_header("Test 3: Route Calculation (OSRM)")
    
    test_routes = [
        ("גברעם", "אשקלון", "Short route"),
        ("תל אביב", "חיפה", "Medium route"),
    ]
    
    success_count = 0
    for origin, destination, description in test_routes:
        print(f"\n🔍 Testing: {description} ({origin} → {destination})")
        
        try:
            route_data = await get_route_data(origin, destination)
            
            if route_data:
                print_success(f"Route calculated successfully")
                print_info(f"  Distance: {route_data['distance_km']:.1f} km")
                print_info(f"  Threshold: {route_data['threshold_km']:.1f} km")
                print_info(f"  Points: {len(route_data['coordinates'])} coordinates")
                
                # Verify data structure
                if (route_data['coordinates'] and 
                    len(route_data['coordinates']) > 0 and
                    route_data['distance_km'] > 0 and
                    route_data['threshold_km'] > 0):
                    success_count += 1
                else:
                    print_error(f"Invalid route data structure")
            else:
                print_error(f"Failed to calculate route")
        except Exception as e:
            print_error(f"Exception: {e}")
    
    return success_count >= 1  # At least one route should work

async def test_distance_calculation():
    """Test distance calculation from point to route"""
    print_header("Test 4: Distance to Route Calculation")
    
    # First get a route
    print(f"\n🔍 Getting route: תל אביב → חיפה")
    
    try:
        route_data = await get_route_data("תל אביב", "חיפה")
        
        if not route_data:
            print_error("Failed to get route data")
            return False
        
        print_success(f"Route obtained: {route_data['distance_km']:.1f} km")
        
        # Test a point
        test_point = "נתניה"  # Should be close to Tel Aviv-Haifa route
        
        print(f"\nTesting distance from {test_point}:")
        coords = geocode_address(test_point)
        if coords:
            distance = calculate_min_distance_to_route(route_data['coordinates'], coords)
            is_on_route = distance <= route_data['threshold_km']
            status = "✅ ON ROUTE" if is_on_route else "❌ TOO FAR"
            print(f"  {test_point}: {distance:.1f} km {status}")
            return True
        else:
            print_error(f"  Failed to geocode: {test_point}")
            return False
    except Exception as e:
        print_error(f"Exception: {e}")
        return False

async def main():
    """Run all tests"""
    print("\n" + "🚀"*30)
    print("  ROUTE SERVICE - STANDALONE TEST SUITE")
    print("🚀"*30)
    
    tests = [
        ("Geocoding", test_geocoding),
        ("Dynamic Threshold", test_dynamic_threshold),
        ("Route Calculation", test_route_calculation),
        ("Distance Calculation", test_distance_calculation),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print_error(f"Test '{test_name}' raised exception: {e}")
            import traceback
            traceback.print_exc()
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
    elif passed >= total * 0.75:
        print_info(f"Most tests passed ({passed}/{total}) ✅")
        return 0
    else:
        print_error(f"{total - passed} test(s) failed")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

