#!/usr/bin/env python3
"""
Simple standalone test for GeoJSON geocoding - no dependencies
"""

import json

# Test addresses
TEST_ADDRESSES = [
    "גברעם",
    "קיבוץ ניר עם",
    "ניר עם",
    "קיבוץ זיקים",
    "קיבוץ בארי",
    "קיבוץ רעים",
    "שדרות",
    "אשקלון",
    "באר שבע",
    "ירושלים",
    "תל אביב",
]

def load_settlements():
    """Load settlements from GeoJSON"""
    db = {}
    
    # Get path to city.geojson in data directory
    import os
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    geojson_path = os.path.join(project_root, 'data', 'city.geojson')
    
    with open(geojson_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    for feature in data.get('features', []):
        props = feature.get('properties', {})
        geom = feature.get('geometry', {})
        coords = geom.get('coordinates', [])
        
        if len(coords) != 2:
            continue
        
        # GeoJSON is [lon, lat], we need [lat, lon]
        lon, lat = coords
        
        hebrew_name = props.get('MGLSDE_LOC', '').strip()
        english_name = props.get('MGLSDE_L_4', '').strip()
        
        if hebrew_name:
            db[hebrew_name.lower()] = (lat, lon)
            
            # Without prefixes
            for prefix in ['קיבוץ ', 'מושב ', 'כפר ']:
                if hebrew_name.startswith(prefix):
                    name_without_prefix = hebrew_name[len(prefix):].strip()
                    db[name_without_prefix.lower()] = (lat, lon)
        
        if english_name:
            db[english_name.lower()] = (lat, lon)
    
    return db

def main():
    print("\n" + "="*80)
    print("  🗺️  בדיקת GeoJSON - קואורדינטות ישובים בישראל")
    print("="*80)
    
    db = load_settlements()
    print(f"\n✅ נטענו {len(db)} ישובים מהמסד נתונים")
    
    print(f"\n{'כתובת':<25} {'קואורדינטות (lat, lon)':<35} {'סטטוס'}")
    print("-" * 80)
    
    success_count = 0
    
    for address in TEST_ADDRESSES:
        normalized = address.strip().lower()
        
        if normalized in db:
            coords = db[normalized]
            print(f"{address:<25} ({coords[0]:.6f}, {coords[1]:.6f})     ✅")
            success_count += 1
        else:
            # Try without prefix
            found = False
            for prefix in ['קיבוץ ', 'מושב ', 'כפר ']:
                if normalized.startswith(prefix):
                    name_without = normalized[len(prefix):].strip()
                    if name_without in db:
                        coords = db[name_without]
                        print(f"{address:<25} ({coords[0]:.6f}, {coords[1]:.6f})     ✅")
                        success_count += 1
                        found = True
                        break
            
            if not found:
                print(f"{address:<25} {'---':<35}  ❌")
    
    print("-" * 80)
    print(f"\n📊 סיכום: {success_count}/{len(TEST_ADDRESSES)} נמצאו ({success_count/len(TEST_ADDRESSES)*100:.0f}%)")
    
    # Special check for Gevaram
    print("\n" + "="*80)
    print("  🎯 בדיקה מיוחדת: גברעם")
    print("="*80)
    
    gevaram_key = "גברעם"
    if gevaram_key in db:
        coords = db[gevaram_key]
        print(f"\n✅ גברעם נמצא במסד הנתונים!")
        print(f"   📍 Latitude:  {coords[0]:.6f}°N")
        print(f"   📍 Longitude: {coords[1]:.6f}°E")
        print(f"   🏘️  סוג: קיבוץ בעוטף עזה")
        
        # Compare with old coordinates
        old_coords = (31.4603, 34.4697)
        from math import radians, sin, cos, sqrt, atan2
        
        # Haversine distance
        R = 6371  # Earth radius in km
        lat1, lon1 = radians(old_coords[0]), radians(old_coords[1])
        lat2, lon2 = radians(coords[0]), radians(coords[1])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        distance = R * c
        
        print(f"\n   📏 הבדל מהקואורדינטות הישנות: {distance:.2f} ק\"מ")
        if distance > 1:
            print(f"   ⚠️  שימו לב: זה הבדל משמעותי! ה-GeoJSON יותר מדויק.")
    else:
        print(f"\n❌ גברעם לא נמצא!")
    
    print("\n" + "="*80)
    print("💡 יתרונות מסד הנתונים המקומי:")
    print("   ✅ מהירות - ללא צורך ב-API חיצוני")
    print("   ✅ דיוק - נתונים רשמיים")
    print("   ✅ אמינות - עובד גם ללא אינטרנט")
    print("   ✅ כיסוי מלא - כל הישובים בישראל")
    print("   ✅ חינמי - ללא עלויות")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()

