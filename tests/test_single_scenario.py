#!/usr/bin/env python3
"""
ריצה מהירה של תרחיש בודד
"""

import asyncio
import json
import os
import sys
import time
import requests
from geopy.distance import distance as geopy_distance
import folium
from folium import plugins

# Setup paths
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

# Import configuration
from config import (
    ROUTE_PROXIMITY_MIN_THRESHOLD_KM,
    ROUTE_PROXIMITY_MAX_THRESHOLD_KM,
    ROUTE_PROXIMITY_SCALE_FACTOR
)

# Configuration
OSRM_API_URL = "http://router.project-osrm.org"
NOMINATIM_API_URL = "https://nominatim.openstreetmap.org"
NOMINATIM_USER_AGENT = "HikerApp/1.0"
API_TIMEOUT = 10

# Load settlements database
SETTLEMENTS_DB = None

def load_settlements():
    """Load Israeli settlements from GeoJSON"""
    global SETTLEMENTS_DB
    if SETTLEMENTS_DB is not None:
        return SETTLEMENTS_DB
    
    SETTLEMENTS_DB = {}
    geojson_path = os.path.join(project_root, 'data', 'city.geojson')
    
    try:
        with open(geojson_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for feature in data.get('features', []):
            props = feature.get('properties', {})
            geom = feature.get('geometry', {})
            coords = geom.get('coordinates', [])
            
            if len(coords) != 2:
                continue
            
            lon, lat = coords
            coordinates = (lat, lon)
            
            hebrew_name = props.get('MGLSDE_LOC', '').strip()
            english_name = props.get('MGLSDE_L_4', '').strip()
            
            if hebrew_name:
                SETTLEMENTS_DB[hebrew_name.lower()] = coordinates
                for prefix in ['קיבוץ ', 'מושב ', 'כפר ', 'נוה ']:
                    if hebrew_name.startswith(prefix):
                        name_without = hebrew_name[len(prefix):].strip()
                        SETTLEMENTS_DB[name_without.lower()] = coordinates
            
            if english_name:
                SETTLEMENTS_DB[english_name.lower()] = coordinates
        
        print(f"✅ נטענו {len(SETTLEMENTS_DB)} שמות ישובים")
    except Exception as e:
        print(f"❌ שגיאה בטעינת GeoJSON: {e}")
    
    return SETTLEMENTS_DB

def geocode_address(address):
    """Geocode address using local DB first, then Nominatim"""
    db = load_settlements()
    normalized = address.strip().lower()
    
    if normalized in db:
        return db[normalized]
    
    for prefix in ['קיבוץ ', 'מושב ', 'כפר ']:
        if normalized.startswith(prefix):
            name_without = normalized[len(prefix):].strip()
            if name_without in db:
                return db[name_without]
    
    # Fallback to Nominatim (causes delays!)
    try:
        time.sleep(0.5)  # Rate limiting - THIS CAUSES DELAY!
        params = {'q': f"{address}, Israel", 'format': 'json', 'limit': 1}
        headers = {'User-Agent': NOMINATIM_USER_AGENT}
        response = requests.get(NOMINATIM_API_URL + "/search", params=params, headers=headers, timeout=API_TIMEOUT)
        response.raise_for_status()
        results = response.json()
        if results:
            return (float(results[0]['lat']), float(results[0]['lon']))
    except Exception as e:
        print(f"⚠️ שגיאה geocoding {address}: {e}")
    
    return None

def calculate_dynamic_threshold(distance_from_origin_km):
    """Calculate dynamic threshold based on distance from origin"""
    threshold = ROUTE_PROXIMITY_MIN_THRESHOLD_KM + (distance_from_origin_km / ROUTE_PROXIMITY_SCALE_FACTOR)
    return min(threshold, ROUTE_PROXIMITY_MAX_THRESHOLD_KM)

def calculate_route_length(coordinates):
    if len(coordinates) < 2:
        return 0.0
    total = 0.0
    for i in range(len(coordinates) - 1):
        total += geopy_distance(coordinates[i], coordinates[i + 1]).kilometers
    return total

def parse_osrm_geometry(geometry):
    coordinates = []
    if 'coordinates' in geometry:
        raw_coords = geometry['coordinates']
        if not raw_coords:
            return []
        
        coordinates.append((raw_coords[0][1], raw_coords[0][0]))
        last_included = (raw_coords[0][1], raw_coords[0][0])
        
        for coord in raw_coords[1:]:
            current = (coord[1], coord[0])
            dist = geopy_distance(last_included, current).kilometers
            if dist >= 1.0:
                coordinates.append(current)
                last_included = current
        
        if coordinates[-1] != (raw_coords[-1][1], raw_coords[-1][0]):
            coordinates.append((raw_coords[-1][1], raw_coords[-1][0]))
    
    return coordinates

async def get_route_data(origin, destination):
    try:
        print(f"  🔍 מחשב קואורדינטות...")
        origin_coords = geocode_address(origin)
        dest_coords = geocode_address(destination)
        
        if not origin_coords or not dest_coords:
            print(f"  ❌ לא הצלחתי למצוא קואורדינטות")
            return None
        
        print(f"  🛣️  מבקש מסלול מ-OSRM...")
        url = f"{OSRM_API_URL}/route/v1/driving/{origin_coords[1]},{origin_coords[0]};{dest_coords[1]},{dest_coords[0]}"
        params = {'overview': 'full', 'geometries': 'geojson'}
        
        response = requests.get(url, params=params, timeout=API_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        
        if data.get('code') != 'Ok' or not data.get('routes'):
            print(f"  ❌ OSRM החזיר שגיאה")
            return None
        
        route = data['routes'][0]
        geometry = route['geometry']
        
        print(f"  ⚙️  מעבד גיאומטריה...")
        coordinates = parse_osrm_geometry(geometry)
        
        if not coordinates:
            print(f"  ❌ אין קואורדינטות")
            return None
        
        distance_km = calculate_route_length(coordinates)
        
        print(f"  ✅ {distance_km:.1f} ק\"מ | {len(coordinates)} נקודות")
        
        return {
            "coordinates": coordinates,
            "distance_km": distance_km,
            "origin_coords": origin_coords,
            "dest_coords": dest_coords
        }
    except Exception as e:
        print(f"  ❌ שגיאה: {str(e)[:100]}")
        return None

def calculate_min_distance_to_route(route_coords, location_coords):
    if not route_coords:
        return float('inf'), None
    
    min_dist = float('inf')
    closest_point = None
    
    for route_point in route_coords:
        dist = geopy_distance(location_coords, route_point).kilometers
        if dist < min_dist:
            min_dist = dist
            closest_point = route_point
    
    return min_dist, closest_point

async def run_beer_sheva_scenario():
    origin = "גברעם"
    destination = "באר שבע"
    
    test_points = [
        "נתיבות", "שדרות", "אופקים", "באר שבע", "רהט", "לקיה",
        "תל שבע", "גילת", "קרית גת", "דימונה", "ערד",
        "קיבוץ רעים", "קיבוץ ניר עם", "קיבוץ זיקים", "קיבוץ בארי",
        "קיבוץ כיסופים", "קיבוץ נחל עוז", "קיבוץ כרם שלום",
        "מושב זמרת", "מושב ישע", "מושב אוהד", "מושב תלמי אליהו",
        "מושב תקומה", "מושב שובל", "מושב ניר עקיבא", "מושב חוות שקמים",
        "מבטחים", "עזר", "גבים", "מעון", "להב", "להבים",
        "דביר", "מיתר", "שובה", "פרי גן", "יד בנימין",
        "שדה דוד", "בית קמה", "תושיה", "מגן", "כפר סילבר",
        "חלץ", "נירים", "עין הבשור", "יכיני", "נחל עוז",
        "סופה", "גרופית", "פטיש", "שדה ניצן"
    ]
    
    print("\n" + "="*80)
    print(f"  🗺️  תרחיש: גברעם → באר שבע")
    print(f"  🎯 בודק {len(test_points)} נקודות")
    print("="*80 + "\n")
    
    start_time = time.time()
    
    load_settlements()
    
    print("⏱️  שלב 1: חישוב מסלול...")
    route_start = time.time()
    route_data = await get_route_data(origin, destination)
    route_time = time.time() - route_start
    print(f"   ⏱️  לקח {route_time:.1f} שניות\n")
    
    if not route_data:
        print("❌ נכשל בחישוב מסלול")
        return
    
    print("⏱️  שלב 2: בדיקת נקודות...")
    points_start = time.time()
    
    print(f"{'#':<4} {'נקודה':<25} {'מרחק':>10} {'סף':>8} {'סטטוס':>6}")
    print("-" * 65)
    
    on_route = 0
    too_far = 0
    failed = 0
    
    for i, point_name in enumerate(test_points, 1):
        point_coords = geocode_address(point_name)
        
        if not point_coords:
            print(f"{i:3}. {point_name:<22} {'---':>10} {'---':>8} {'❌':>6}")
            failed += 1
            continue
        
        distance_from_origin = geopy_distance(route_data['origin_coords'], point_coords).kilometers
        dynamic_threshold = calculate_dynamic_threshold(distance_from_origin)
        
        min_distance, closest_point = calculate_min_distance_to_route(
            route_data['coordinates'],
            point_coords
        )
        
        is_on_route = min_distance <= dynamic_threshold
        
        if is_on_route:
            status = "✅"
            on_route += 1
        else:
            status = "❌"
            too_far += 1
        
        print(f"{i:3}. {point_name:<22} {min_distance:>7.1f} ק\"מ {dynamic_threshold:>6.1f} {status:>6}")
    
    points_time = time.time() - points_start
    total_time = time.time() - start_time
    
    print("-" * 65)
    print(f"📊 {on_route} ✅ | {too_far} ❌ | {failed} כשלון")
    print(f"\n⏱️  זמנים:")
    print(f"   חישוב מסלול: {route_time:.1f} שניות")
    print(f"   בדיקת {len(test_points)} נקודות: {points_time:.1f} שניות")
    print(f"   סה\"כ: {total_time:.1f} שניות")
    print(f"\n💡 זיקים: במרחק ~14 ק\"מ מגברעם → סף 1.4 ק\"מ → {'✅ על הדרך' if 'קיבוץ זיקים' in [test_points[i] for i, s in enumerate([status]) if s == '✅'] else '❌ לא על הדרך'}")

if __name__ == "__main__":
    asyncio.run(run_beer_sheva_scenario())

