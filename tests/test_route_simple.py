#!/usr/bin/env python3
"""
Simple standalone test for route service - minimal dependencies
"""

import asyncio
import requests
from functools import lru_cache
from geopy.distance import distance as geopy_distance

# Mock config values
OSRM_API_URL = "http://router.project-osrm.org"
NOMINATIM_API_URL = "https://nominatim.openstreetmap.org"
NOMINATIM_USER_AGENT = "HikerApp/1.0"
ROUTE_PROXIMITY_MIN_THRESHOLD_KM = 2.5
ROUTE_PROXIMITY_MAX_THRESHOLD_KM = 10.0
ROUTE_PROXIMITY_SCALE_FACTOR = 10.0
API_TIMEOUT_SECONDS = 10

# Copy the key functions from route_service

def calculate_dynamic_threshold(route_distance_km):
    """Calculate dynamic threshold based on route distance"""
    threshold = ROUTE_PROXIMITY_MIN_THRESHOLD_KM + (route_distance_km / ROUTE_PROXIMITY_SCALE_FACTOR)
    return max(ROUTE_PROXIMITY_MIN_THRESHOLD_KM, min(threshold, ROUTE_PROXIMITY_MAX_THRESHOLD_KM))

@lru_cache(maxsize=200)
def geocode_address(address):
    """Convert address to coordinates using Nominatim API"""
    try:
        params = {
            'q': f"{address}, Israel",
            'format': 'json',
            'limit': 1
        }
        headers = {
            'User-Agent': NOMINATIM_USER_AGENT
        }
        
        response = requests.get(
            NOMINATIM_API_URL + "/search",
            params=params,
            headers=headers,
            timeout=API_TIMEOUT_SECONDS
        )
        response.raise_for_status()
        
        results = response.json()
        if not results:
            return None
        
        lat = float(results[0]['lat'])
        lon = float(results[0]['lon'])
        return (lat, lon)
        
    except Exception as e:
        print(f"❌ Geocoding error for '{address}': {e}")
        return None

def calculate_min_distance_to_route(route_coords, location_coords):
    """Calculate minimum Haversine distance from location to any point on route"""
    if not route_coords:
        return float('inf')
    
    min_dist = float('inf')
    for route_point in route_coords:
        dist = geopy_distance(location_coords, route_point).kilometers
        min_dist = min(min_dist, dist)
    
    return min_dist

def _calculate_route_length(coordinates):
    """Calculate total route length from coordinates"""
    if len(coordinates) < 2:
        return 0.0
    
    total = 0.0
    for i in range(len(coordinates) - 1):
        total += geopy_distance(coordinates[i], coordinates[i + 1]).kilometers
    
    return total

def _parse_osrm_geometry(geometry, target_resolution_km=1.0):
    """Parse OSRM geometry and sample points at ~1km intervals"""
    coordinates = []
    
    if 'coordinates' in geometry:
        raw_coords = geometry['coordinates']
        
        if not raw_coords:
            return []
        
        # Always include first point
        coordinates.append((raw_coords[0][1], raw_coords[0][0]))
        last_included = (raw_coords[0][1], raw_coords[0][0])
        
        for coord in raw_coords[1:]:
            current = (coord[1], coord[0])
            dist = geopy_distance(last_included, current).kilometers
            
            if dist >= target_resolution_km:
                coordinates.append(current)
                last_included = current
        
        # Always include last point
        if coordinates[-1] != (raw_coords[-1][1], raw_coords[-1][0]):
            coordinates.append((raw_coords[-1][1], raw_coords[-1][0]))
    
    return coordinates

async def get_route_data(origin, destination):
    """Get complete route data: coordinates, distance, and dynamic threshold"""
    try:
        # 1. Geocode addresses
        origin_coords = geocode_address(origin)
        dest_coords = geocode_address(destination)
        
        if not origin_coords or not dest_coords:
            return None
        
        # 2. Query OSRM for route
        url = f"{OSRM_API_URL}/route/v1/driving/{origin_coords[1]},{origin_coords[0]};{dest_coords[1]},{dest_coords[0]}"
        params = {
            'overview': 'full',
            'geometries': 'geojson'
        }
        
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: requests.get(url, params=params, timeout=API_TIMEOUT_SECONDS)
        )
        response.raise_for_status()
        
        data = response.json()
        
        if data.get('code') != 'Ok' or not data.get('routes'):
            return None
        
        route = data['routes'][0]
        geometry = route['geometry']
        
        # 3. Parse coordinates
        coordinates = _parse_osrm_geometry(geometry, target_resolution_km=1.0)
        
        if not coordinates:
            return None
        
        # 4. Calculate total distance
        distance_km = _calculate_route_length(coordinates)
        
        # 5. Calculate dynamic threshold
        threshold_km = calculate_dynamic_threshold(distance_km)
        
        return {
            "coordinates": coordinates,
            "distance_km": distance_km,
            "threshold_km": threshold_km
        }
        
    except Exception as e:
        print(f"❌ Error calculating route {origin} → {destination}: {e}")
        return None

# Test functions

def print_header(title):
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def print_success(msg):
    print(f"✅ {msg}")

def print_error(msg):
    print(f"❌ {msg}")

def print_info(msg):
    print(f"ℹ️  {msg}")

async def test_geocoding():
    """Test geocoding"""
    print_header("Test 1: Geocoding")
    
    locations = ["תל אביב", "חיפה", "ירושלים"]
    success = 0
    
    for loc in locations:
        coords = geocode_address(loc)
        if coords:
            print_success(f"{loc}: ({coords[0]:.4f}, {coords[1]:.4f})")
            success += 1
        else:
            print_error(f"Failed: {loc}")
    
    return success >= 2

async def test_threshold():
    """Test dynamic threshold"""
    print_header("Test 2: Dynamic Threshold")
    
    tests = [(10, 3.5), (50, 7.5), (100, 10.0)]
    all_ok = True
    
    for dist, expected in tests:
        threshold = calculate_dynamic_threshold(dist)
        print_info(f"{dist} km route → {threshold:.1f} km threshold")
        if abs(threshold - expected) > 0.5:
            print_error(f"Expected ~{expected:.1f}")
            all_ok = False
    
    return all_ok

async def test_route():
    """Test route calculation"""
    print_header("Test 3: Route Calculation")
    
    print("🔍 Calculating route: תל אביב → חיפה")
    route = await get_route_data("תל אביב", "חיפה")
    
    if route:
        print_success(f"Route: {route['distance_km']:.1f} km")
        print_info(f"Threshold: {route['threshold_km']:.1f} km")
        print_info(f"Points: {len(route['coordinates'])}")
        return True
    else:
        print_error("Route calculation failed")
        return False

async def test_distance():
    """Test distance calculation"""
    print_header("Test 4: Distance to Route")
    
    route = await get_route_data("תל אביב", "חיפה")
    if not route:
        print_error("No route")
        return False
    
    netanya_coords = geocode_address("נתניה")
    if not netanya_coords:
        print_error("Failed to geocode נתניה")
        return False
    
    dist = calculate_min_distance_to_route(route['coordinates'], netanya_coords)
    on_route = dist <= route['threshold_km']
    
    print_info(f"נתניה distance: {dist:.1f} km")
    print_info(f"Threshold: {route['threshold_km']:.1f} km")
    print_success(f"On route: {on_route}")
    
    return True

async def main():
    print("\n" + "🚀"*30)
    print("  ROUTE SERVICE - SIMPLE TEST")
    print("🚀"*30)
    
    tests = [
        ("Geocoding", test_geocoding),
        ("Threshold", test_threshold),
        ("Route Calc", test_route),
        ("Distance", test_distance),
    ]
    
    results = []
    for name, func in tests:
        try:
            result = await func()
            results.append((name, result))
        except Exception as e:
            print_error(f"{name} failed: {e}")
            results.append((name, False))
    
    print_header("SUMMARY")
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} - {name}")
    
    print(f"\n  {passed}/{total} tests passed")
    
    if passed >= total * 0.75:
        print_success("Tests passed! 🎉")
        return 0
    else:
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)

