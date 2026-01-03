#!/usr/bin/env python3
"""
List ALL rides and requests in Firestore (including inactive)
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from database import initialize_db, get_db


async def main():
    # Initialize database first
    initialize_db()
    db = get_db()
    if not db:
        print("❌ Database not initialized")
        return
    
    print("\n" + "="*80)
    print("📊 All Users in Firestore")
    print("="*80)
    
    docs = db.collection("users").stream()
    user_count = 0
    driver_count = 0
    hitchhiker_count = 0
    
    for doc in docs:
        user_count += 1
        user_data = doc.to_dict()
        phone = user_data.get("phone_number", "Unknown")
        name = user_data.get("name", "Unknown")
        
        driver_rides = user_data.get("driver_rides", [])
        hitchhiker_requests = user_data.get("hitchhiker_requests", [])
        
        if driver_rides or hitchhiker_requests:
            print(f"\n{'─'*80}")
            print(f"👤 {name} ({phone})")
            print(f"{'─'*80}")
            
            if driver_rides:
                print(f"\n🚗 Driver Rides ({len(driver_rides)}):")
                for i, ride in enumerate(driver_rides, 1):
                    driver_count += 1
                    active = "✅" if ride.get("active", True) else "❌"
                    print(f"   {i}. {active} {ride.get('origin', 'גברעם')} → {ride['destination']}")
                    print(f"      ID: {ride.get('id')}")
                    print(f"      Date: {ride.get('travel_date', 'N/A')}, Days: {ride.get('days', 'N/A')}")
                    print(f"      Time: {ride['departure_time']}")
                    print(f"      Route: {ride.get('route_num_points', 0)} points, {ride.get('route_distance_km', 0):.1f} km")
            
            if hitchhiker_requests:
                print(f"\n🎒 Hitchhiker Requests ({len(hitchhiker_requests)}):")
                for i, req in enumerate(hitchhiker_requests, 1):
                    hitchhiker_count += 1
                    active = "✅" if req.get("active", True) else "❌"
                    print(f"   {i}. {active} {req.get('origin', 'גברעם')} → {req['destination']}")
                    print(f"      ID: {req.get('id')}")
                    print(f"      Date: {req.get('travel_date')}")
                    print(f"      Time: {req['departure_time']}")
                    print(f"      Flexibility: {req.get('flexibility', 'N/A')}")
    
    print(f"\n{'='*80}")
    print(f"📊 Summary:")
    print(f"   Total users: {user_count}")
    print(f"   Total driver rides: {driver_count}")
    print(f"   Total hitchhiker requests: {hitchhiker_count}")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    asyncio.run(main())

