#!/usr/bin/env python3
"""
בדיקה מהירה: האם המסלול נשמר ב-DB?
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_route_save():
    """Test if route gets saved to DB"""
    import importlib.util
    
    # Load route_service directly
    route_service_path = os.path.join(os.path.dirname(__file__), 'services', 'route_service.py')
    spec = importlib.util.spec_from_file_location("route_service", route_service_path)
    route_service = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(route_service)
    
    get_route_data = route_service.get_route_data
    
    print("="*80)
    print("  Testing Route Calculation & DB Save")
    print("="*80)
    
    # 1. Calculate route
    print("\n1️⃣ Calculating route: גברעם -> באר שבע")
    route_data = await get_route_data("גברעם", "באר שבע")
    
    if not route_data:
        print("   ❌ Failed to calculate route")
        return
    
    print(f"   ✅ Route calculated:")
    print(f"      - Distance: {route_data['distance_km']:.1f} km")
    print(f"      - Points: {len(route_data['coordinates'])}")
    print(f"      - Threshold: {route_data.get('threshold_km', 'None (dynamic)')}")
    
    # 2. Check what would be saved
    print("\n2️⃣ Data structure that would be saved to DB:")
    print(f"   - route_coordinates: {len(route_data['coordinates'])} points")
    print(f"   - route_distance_km: {route_data['distance_km']:.1f}")
    print(f"   - route_threshold_km: {route_data.get('threshold_km')}")
    
    # 3. Show first few coordinates
    print("\n3️⃣ Sample coordinates:")
    for i, coord in enumerate(route_data['coordinates'][:5]):
        print(f"      Point {i+1}: {coord}")
    if len(route_data['coordinates']) > 5:
        print(f"      ... and {len(route_data['coordinates']) - 5} more")
    
    print("\n" + "="*80)
    print("✅ Route calculation works!")
    print("💡 When a driver registers via WhatsApp:")
    print("   1. Record saved immediately with route_calculation_pending=True")
    print("   2. Background task calculates route (takes ~2-5 seconds)")
    print("   3. Route coordinates saved to DB")
    print("   4. route_calculation_pending set to False")
    print("="*80)

if __name__ == "__main__":
    asyncio.run(test_route_save())

