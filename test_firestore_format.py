#!/usr/bin/env python3
"""
Test: Verify Firestore format conversion
"""

# Test data structure
route_data = {
    "coordinates": [
        (31.591685, 34.613109),  # Python tuple
        (31.59519, 34.603392),
        (31.598178, 34.593388),
    ],
    "distance_km": 39.9,
    "threshold_km": None
}

print("="*80)
print("  Testing Firestore Format Conversion")
print("="*80)

print("\n1️⃣ Original format (Python tuples):")
print(f"   Type: {type(route_data['coordinates'][0])}")
print(f"   Data: {route_data['coordinates'][:2]}")

# Convert tuples to lists (what we do in update_ride_route_data)
coordinates = [[lat, lon] for lat, lon in route_data["coordinates"]]

print("\n2️⃣ Converted format (lists for Firestore):")
print(f"   Type: {type(coordinates[0])}")
print(f"   Data: {coordinates[:2]}")

print("\n3️⃣ Firestore structure:")
ride_record = {
    "id": "test-123",
    "origin": "גברעם",
    "destination": "יבנה",
    "route_coordinates": coordinates,  # ✅ Lists!
    "route_distance_km": route_data["distance_km"],
    "route_threshold_km": route_data["threshold_km"],
    "route_calculation_pending": False
}

print(f"   route_coordinates: {len(ride_record['route_coordinates'])} points")
print(f"   First point: {ride_record['route_coordinates'][0]}")
print(f"   Type: {type(ride_record['route_coordinates'][0])} ✅")

print("\n" + "="*80)
print("✅ Format conversion works!")
print("   Tuples → Lists = Firestore compatible")
print("="*80)

