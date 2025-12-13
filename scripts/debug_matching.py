#!/usr/bin/env python3
"""
Debug script to check why matching didn't work
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from bson import ObjectId
from src.database.mongodb_client import MongoDBClient
from src.config import Config

# Connect to MongoDB
db = MongoDBClient(Config.MONGODB_URI, Config.MONGODB_DB_NAME)

print("=" * 80)
print("🔍 בדיקת התאמות")
print("=" * 80)

# Get hitchhiker ride request
hitchhiker_phone = "972547482730"
hitchhiker = db.get_collection("users").find_one({"phone_number": hitchhiker_phone})
if hitchhiker:
    print(f"\n✅ טרמפיסט נמצא: {hitchhiker.get('full_name') or hitchhiker.get('whatsapp_name')}")
    ride_request = db.get_collection("ride_requests").find_one(
        {"requester_id": hitchhiker['_id']},
        sort=[("created_at", -1)]
    )
    if ride_request:
        print(f"📋 בקשה: {ride_request.get('destination')}")
        print(f"⏰ זמן: {ride_request.get('start_time_range')} - {ride_request.get('end_time_range')}")
        print(f"📅 נוצר: {ride_request.get('created_at')}")
    else:
        print("❌ לא נמצאה בקשה")
else:
    print(f"❌ טרמפיסט לא נמצא: {hitchhiker_phone}")

# Get driver routine
driver_phone = "972524297932"
driver = db.get_collection("users").find_one({"phone_number": driver_phone})
if driver:
    print(f"\n✅ נהג נמצא: {driver.get('full_name') or driver.get('whatsapp_name')}")
    routines = list(db.get_collection("routines").find({"user_id": driver['_id'], "is_active": True}))
    print(f"🔄 שגרות פעילות: {len(routines)}")
    for routine in routines:
        print(f"  - יעד: {routine.get('destination')}")
        print(f"    ימים: {routine.get('days')}")
        print(f"    זמן יציאה: {routine.get('departure_time_start')} - {routine.get('departure_time_end')}")
        print(f"    זמן חזרה: {routine.get('return_time_start')} - {routine.get('return_time_end')}")
        print(f"    נוצר: {routine.get('created_at')}")
else:
    print(f"❌ נהג לא נמצא: {driver_phone}")

# Check for matches
if hitchhiker and driver and ride_request:
    print(f"\n🔍 בודק התאמות...")
    matches = list(db.get_collection("matches").find({
        "ride_request_id": ride_request['_id'],
        "driver_id": driver['_id']
    }))
    print(f"📊 נמצאו {len(matches)} התאמות")
    for match in matches:
        print(f"  - סטטוס: {match.get('status')}")
        print(f"    נוצר: {match.get('matched_at')}")

print("\n" + "=" * 80)










