#!/usr/bin/env python3
"""
תרחישי בדיקה מקיפים מגברעם - 5 מסלולים x 15 נקודות בדיקה
עם מפות אינטראקטיביות מפורטות
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
    
    # Try local DB
    if normalized in db:
        coords = db[normalized]
        print(f"  ✓ '{address}' מ-DB → ({coords[0]:.4f}, {coords[1]:.4f})")
        return coords
    
    # Try without prefix
    for prefix in ['קיבוץ ', 'מושב ', 'כפר ']:
        if normalized.startswith(prefix):
            name_without = normalized[len(prefix):].strip()
            if name_without in db:
                coords = db[name_without]
                print(f"  ✓ '{address}' מ-DB → ({coords[0]:.4f}, {coords[1]:.4f})")
                return coords
    
    # Fallback to Nominatim
    try:
        time.sleep(1)  # Rate limiting
        params = {'q': f"{address}, Israel", 'format': 'json', 'limit': 1}
        headers = {'User-Agent': NOMINATIM_USER_AGENT}
        response = requests.get(NOMINATIM_API_URL + "/search", params=params, headers=headers, timeout=API_TIMEOUT)
        response.raise_for_status()
        results = response.json()
        
        if results:
            coords = (float(results[0]['lat']), float(results[0]['lon']))
            print(f"  ✓ '{address}' מ-Nominatim → ({coords[0]:.4f}, {coords[1]:.4f})")
            return coords
    except Exception as e:
        print(f"  ✗ '{address}' - שגיאה: {str(e)[:50]}")
    
    return None

def calculate_dynamic_threshold(route_distance_km):
    """Calculate dynamic proximity threshold"""
    threshold = ROUTE_PROXIMITY_MIN_THRESHOLD_KM + (route_distance_km / ROUTE_PROXIMITY_SCALE_FACTOR)
    return max(ROUTE_PROXIMITY_MIN_THRESHOLD_KM, min(threshold, ROUTE_PROXIMITY_MAX_THRESHOLD_KM))

def calculate_route_length(coordinates):
    """Calculate total route length"""
    if len(coordinates) < 2:
        return 0.0
    total = 0.0
    for i in range(len(coordinates) - 1):
        total += geopy_distance(coordinates[i], coordinates[i + 1]).kilometers
    return total

def parse_osrm_geometry(geometry):
    """Parse OSRM geometry to coordinates"""
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
            if dist >= 1.0:  # 1km resolution
                coordinates.append(current)
                last_included = current
        
        if coordinates[-1] != (raw_coords[-1][1], raw_coords[-1][0]):
            coordinates.append((raw_coords[-1][1], raw_coords[-1][0]))
    
    return coordinates

async def get_route_data(origin, destination):
    """Get route from OSRM"""
    print(f"\n🗺️  מחשב מסלול: {origin} → {destination}")
    
    origin_coords = geocode_address(origin)
    dest_coords = geocode_address(destination)
    
    if not origin_coords or not dest_coords:
        print(f"  ❌ Geocoding נכשל")
        return None
    
    try:
        url = f"{OSRM_API_URL}/route/v1/driving/{origin_coords[1]},{origin_coords[0]};{dest_coords[1]},{dest_coords[0]}"
        params = {'overview': 'full', 'geometries': 'geojson'}
        
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: requests.get(url, params=params, timeout=API_TIMEOUT))
        response.raise_for_status()
        
        data = response.json()
        
        if data.get('code') != 'Ok' or not data.get('routes'):
            print(f"  ❌ OSRM נכשל")
            return None
        
        route = data['routes'][0]
        geometry = route['geometry']
        coordinates = parse_osrm_geometry(geometry)
        
        if not coordinates:
            print(f"  ❌ אין קואורדינטות")
            return None
        
        distance_km = calculate_route_length(coordinates)
        threshold_km = calculate_dynamic_threshold(distance_km)
        
        print(f"  ✅ {distance_km:.1f} ק\"מ | סף: {threshold_km:.1f} ק\"מ | {len(coordinates)} נקודות")
        
        return {
            "coordinates": coordinates,
            "distance_km": distance_km,
            "threshold_km": threshold_km,
            "origin_coords": origin_coords,
            "dest_coords": dest_coords
        }
    except Exception as e:
        print(f"  ❌ שגיאה: {str(e)[:100]}")
        return None

def calculate_min_distance_to_route(route_coords, location_coords):
    """Calculate minimum distance from point to route"""
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

async def create_scenario_map(scenario_num, destination, test_points, output_file):
    """Create interactive map for scenario"""
    
    origin = "גברעם"
    
    print(f"\n{'='*80}")
    print(f"  תרחיש {scenario_num}: גברעם → {destination}")
    print(f"{'='*80}")
    
    route_data = await get_route_data(origin, destination)
    
    if not route_data:
        print("❌ לא הצלחתי לקבל נתוני מסלול")
        return None
    
    # Create map centered on route
    mid_idx = len(route_data['coordinates']) // 2
    center = route_data['coordinates'][mid_idx]
    
    m = folium.Map(location=center, zoom_start=9, tiles='OpenStreetMap')
    
    # Add route line
    route_line = [(lat, lon) for lat, lon in route_data['coordinates']]
    folium.PolyLine(
        route_line,
        color='#0066CC',
        weight=5,
        opacity=0.8,
        popup=f"מסלול: גברעם → {destination}<br>מרחק: {route_data['distance_km']:.1f} ק\"מ<br>סף: {route_data['threshold_km']:.1f} ק\"מ"
    ).add_to(m)
    
    # Add origin marker
    folium.Marker(
        route_data['origin_coords'],
        popup=f"<b>🏠 מוצא: גברעם</b>",
        tooltip="גברעם",
        icon=folium.Icon(color='darkgreen', icon='home', prefix='fa')
    ).add_to(m)
    
    # Add destination marker
    folium.Marker(
        route_data['dest_coords'],
        popup=f"<b>🎯 יעד: {destination}</b>",
        tooltip=destination,
        icon=folium.Icon(color='darkred', icon='flag-checkered', prefix='fa')
    ).add_to(m)
    
    # Test hitchhiker points
    print(f"\n🎒 בודק 15 נקודות טרמפיסטים:")
    print(f"{'#':<4} {'נקודה':<25} {'מרחק':>10} {'סטטוס':>10} {'% מסף':>10}")
    print("-" * 70)
    
    on_route = 0
    too_far = 0
    failed = 0
    
    for i, point_name in enumerate(test_points, 1):
        point_coords = geocode_address(point_name)
        
        if not point_coords:
            print(f"{i:3}. {point_name:<22} {'---':>10} {'❌':>10} {'':>10}")
            failed += 1
            continue
        
        min_distance, closest_point = calculate_min_distance_to_route(
            route_data['coordinates'],
            point_coords
        )
        
        is_on_route = min_distance <= route_data['threshold_km']
        
        if is_on_route:
            color = 'lightgreen'
            icon = 'check-circle'
            status = "✅"
            on_route += 1
        else:
            color = 'orange'
            icon = 'times-circle'
            status = "❌"
            too_far += 1
        
        percentage = (min_distance / route_data['threshold_km'] * 100)
        
        print(f"{i:3}. {point_name:<22} {min_distance:>7.1f} ק\"מ {status:>10} {percentage:>7.0f}%")
        
        # Add marker to map
        folium.Marker(
            point_coords,
            popup=f"""
                <div style='width: 200px'>
                    <h4>{point_name}</h4>
                    <b>מרחק מהמסלול:</b> {min_distance:.1f} ק"מ<br>
                    <b>סף:</b> {route_data['threshold_km']:.1f} ק"מ<br>
                    <b>אחוז:</b> {percentage:.0f}%<br>
                    <b>סטטוס:</b> {'✅ על הדרך' if is_on_route else '❌ רחוק מדי'}
                </div>
            """,
            tooltip=f"{point_name} ({min_distance:.1f} ק\"מ)",
            icon=folium.Icon(color=color, icon=icon, prefix='fa')
        ).add_to(m)
        
        # Draw line to closest point
        if closest_point:
            folium.PolyLine(
                [point_coords, closest_point],
                color='green' if is_on_route else 'red',
                weight=2,
                opacity=0.5,
                dash_array='5, 5'
            ).add_to(m)
            
            folium.CircleMarker(
                closest_point,
                radius=3,
                color='blue',
                fill=True,
                fillColor='blue',
                fillOpacity=0.6
            ).add_to(m)
    
    # Statistics
    total = on_route + too_far
    success_rate = (on_route / total * 100) if total > 0 else 0
    
    print("-" * 70)
    print(f"📊 {on_route} על הדרך | {too_far} רחוק | {failed} כשלון | {success_rate:.0f}% הצלחה")
    
    # Add legend
    legend_html = f"""
    <div style="position: fixed; 
                bottom: 30px; right: 30px; width: 350px;
                background-color: white; border:3px solid #0066CC; z-index:9999; 
                font-size:14px; padding: 15px; border-radius: 8px;
                box-shadow: 3px 3px 10px rgba(0,0,0,0.4);">
        <h3 style="margin-top:0; color:#0066CC; border-bottom: 2px solid #0066CC; padding-bottom: 8px;">
            תרחיש {scenario_num}: גברעם → {destination}
        </h3>
        
        <div style="margin: 10px 0;">
            <b>📏 מרחק מסלול:</b> {route_data['distance_km']:.1f} ק"מ<br>
            <b>🎯 סף דינמי:</b> {route_data['threshold_km']:.1f} ק"מ<br>
            <b>📊 נקודות במסלול:</b> {len(route_data['coordinates'])}
        </div>
        
        <hr style="border: 1px solid #eee;">
        
        <div style="margin: 10px 0;">
            <h4 style="margin: 5px 0; color: #2ECC71;">✅ על הדרך: {on_route}</h4>
            <h4 style="margin: 5px 0; color: #E67E22;">❌ רחוק מדי: {too_far}</h4>
            {f'<h4 style="margin: 5px 0; color: #95A5A6;">⚠️  כשלון: {failed}</h4>' if failed > 0 else ''}
            <h4 style="margin: 5px 0; color: #3498DB;">🎯 הצלחה: {success_rate:.0f}%</h4>
        </div>
        
        <hr style="border: 1px solid #eee;">
        
        <div style="font-size: 12px; color: #7F8C8D; margin-top: 10px;">
            <i>קווים ירוקים = על הדרך<br>
            קווים אדומים = רחוק מדי<br>
            נקודות כחולות = נקודה קרובה ביותר</i>
        </div>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))
    
    # Add fullscreen button
    plugins.Fullscreen().add_to(m)
    
    # Save map
    output_path = os.path.join(project_root, 'tests', 'outputs', output_file)
    m.save(output_path)
    print(f"\n✅ מפה נשמרה: {output_path}")
    
    return {
        'file': output_file,
        'on_route': on_route,
        'too_far': too_far,
        'failed': failed,
        'success_rate': success_rate,
        'distance': route_data['distance_km'],
        'threshold': route_data['threshold_km']
    }

async def main():
    print("\n" + "🗺️ "*40)
    print("  תרחישי בדיקה מקיפים מגברעם")
    print("  5 מסלולים × 15 נקודות = 75 בדיקות!")
    print("🗺️ "*40)
    
    scenarios = [
        {
            "num": 1,
            "destination": "תל אביב",
            "test_points": [
                "אשדוד", "אשקלון", "ראשון לציון", "חולון", "בת ים",
                "רמלה", "לוד", "רחובות", "נס ציונה", "יבנה",
                "גדרה", "קרית גת", "קרית מלאכי", "גן יבנה", "מזכרת בתיה"
            ],
            "output": "gevaram_1_tel_aviv.html"
        },
        {
            "num": 2,
            "destination": "ירושלים",
            "test_points": [
                "קרית גת", "בית שמש", "לכיש", "קרית מלאכי", "אשדוד",
                "אשקלון", "באר טוביה", "גדרה", "יבנה", "נתיבות",
                "לטרון", "שער הגיא", "צור הדסה", "מבשרת ציון", "מוצא"
            ],
            "output": "gevaram_2_jerusalem.html"
        },
        {
            "num": 3,
            "destination": "באר שבע",
            "test_points": [
                "נתיבות", "שדרות", "אופקים", "קיבוץ רעים", "קיבוץ ניר עם",
                "קיבוץ זיקים", "קיבוץ בארי", "קיבוץ כיסופים", "להבים", "דביר",
                "מיתר", "רהט", "לקיה", "תל שבע", "גילת"
            ],
            "output": "gevaram_3_beer_sheva.html"
        },
        {
            "num": 4,
            "destination": "חיפה",
            "test_points": [
                "אשדוד", "אשקלון", "רחובות", "נס ציונה", "רמלה",
                "לוד", "ראשון לציון", "תל אביב", "הרצליה", "נתניה",
                "חדרה", "קיסריה", "זכרון יעקב", "עתלית", "טירת כרמל"
            ],
            "output": "gevaram_4_haifa.html"
        },
        {
            "num": 5,
            "destination": "נתניה",
            "test_points": [
                "אשדוד", "אשקלון", "יבנה", "גן יבנה", "קרית מלאכי",
                "גדרה", "נס ציונה", "רחובות", "רמלה", "לוד",
                "ראשון לציון", "תל אביב", "פתח תקווה", "כפר סבא", "רעננה"
            ],
            "output": "gevaram_5_netanya.html"
        }
    ]
    
    results = []
    total_on_route = 0
    total_tested = 0
    
    for scenario in scenarios:
        try:
            result = await create_scenario_map(
                scenario["num"],
                scenario["destination"],
                scenario["test_points"],
                scenario["output"]
            )
            
            if result:
                results.append(result)
                total_on_route += result['on_route']
                total_tested += (result['on_route'] + result['too_far'])
            
            # Small delay between scenarios
            await asyncio.sleep(2)
            
        except Exception as e:
            print(f"❌ שגיאה בתרחיש {scenario['num']}: {e}")
    
    # Final summary
    print("\n" + "="*80)
    print("  📊 סיכום כללי")
    print("="*80)
    
    for i, result in enumerate(results, 1):
        print(f"\nתרחיש {i}:")
        print(f"  📁 {result['file']}")
        print(f"  📏 {result['distance']:.1f} ק\"מ | סף: {result['threshold']:.1f} ק\"מ")
        print(f"  ✅ {result['on_route']} על הדרך | ❌ {result['too_far']} רחוק")
        print(f"  🎯 {result['success_rate']:.0f}% הצלחה")
    
    overall = (total_on_route / total_tested * 100) if total_tested > 0 else 0
    
    print("\n" + "-"*80)
    print(f"📊 סה\"כ: {total_tested} נקודות | {total_on_route} על הדרך | {overall:.1f}% הצלחה")
    print("-"*80)
    print(f"\n✅ נוצרו {len(results)} מפות HTML!")
    print(f"📂 המפות נמצאות ב: tests/outputs/")
    print("="*80 + "\n")

if __name__ == "__main__":
    asyncio.run(main())

