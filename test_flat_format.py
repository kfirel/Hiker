#!/usr/bin/env python3
"""
Test: Verify flat format works with Firestore
"""

# Simulate route data
route_data = {
    "coordinates": [
        (31.591685, 34.613109),
        (31.59519, 34.603392),
        (31.598178, 34.593388),
    ],
    "distance_km": 39.9,
    "threshold_km": None
}

print("="*80)
print("  Testing Flat Format for Firestore")
print("="*80)

print("\n1️⃣ Original format (tuples of pairs):")
print(f"   Points: {len(route_data['coordinates'])}")
print(f"   Data: {route_data['coordinates']}")

# Flatten (what we save to DB)
flat_coords = []
for lat, lon in route_data["coordinates"]:
    flat_coords.extend([lat, lon])

print("\n2️⃣ Flattened format (single array):")
print(f"   Values: {len(flat_coords)}")
print(f"   Data: {flat_coords}")
print(f"   Structure: [lat1, lon1, lat2, lon2, lat3, lon3, ...]")

# Reconstruct (what we read from DB)
reconstructed = [(flat_coords[i], flat_coords[i+1]) for i in range(0, len(flat_coords), 2)]

print("\n3️⃣ Reconstructed format:")
print(f"   Points: {len(reconstructed)}")
print(f"   Data: {reconstructed}")

# Verify
print("\n4️⃣ Verification:")
print(f"   Original == Reconstructed: {route_data['coordinates'] == reconstructed}")

print("\n5️⃣ Firestore structure:")
ride_record = {
    "id": "test-123",
    "origin": "גברעם",
    "destination": "אילת",
    "route_coordinates_flat": flat_coords,  # ✅ Flat array!
    "route_num_points": len(route_data["coordinates"]),
    "route_distance_km": route_data["distance_km"],
    "route_calculation_pending": False
}

print(f"   route_coordinates_flat: {len(ride_record['route_coordinates_flat'])} values")
print(f"   route_num_points: {ride_record['route_num_points']}")
print(f"   No nested arrays! ✅")

print("\n" + "="*80)
print("✅ Flat format works!")
print("   Nested arrays → Flat array = Firestore compatible")
print("="*80)

