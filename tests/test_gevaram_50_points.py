#!/usr/bin/env python3
"""
תרחישי בדיקה מקיפים מגברעם - 5 מסלולים x 50 נקודות = 250 בדיקות!
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
    
    if normalized in db:
        return db[normalized]
    
    for prefix in ['קיבוץ ', 'מושב ', 'כפר ']:
        if normalized.startswith(prefix):
            name_without = normalized[len(prefix):].strip()
            if name_without in db:
                return db[name_without]
    
    try:
        time.sleep(0.5)  # Rate limiting
        params = {'q': f"{address}, Israel", 'format': 'json', 'limit': 1}
        headers = {'User-Agent': NOMINATIM_USER_AGENT}
        response = requests.get(NOMINATIM_API_URL + "/search", params=params, headers=headers, timeout=API_TIMEOUT)
        response.raise_for_status()
        results = response.json()
        
        if results:
            return (float(results[0]['lat']), float(results[0]['lon']))
    except:
        pass
    
    return None

def batch_geocode_points(point_names):
    """
    Pre-geocode all points at once (simulating production behavior)
    Most points are in local GeoJSON so this is VERY fast!
    """
    geocoded = {}
    from_local = 0
    from_api = 0
    failed = 0
    
    db = load_settlements()
    
    for point in point_names:
        normalized = point.strip().lower()
        
        # Try local DB first (FAST!)
        coords = None
        if normalized in db:
            coords = db[normalized]
            from_local += 1
        else:
            # Try without prefix
            for prefix in ['קיבוץ ', 'מושב ', 'כפר ']:
                if normalized.startswith(prefix):
                    name_without = normalized[len(prefix):].strip()
                    if name_without in db:
                        coords = db[name_without]
                        from_local += 1
                        break
        
        # Fallback to API only if needed (SLOW!)
        if not coords:
            coords = geocode_address(point)
            if coords:
                from_api += 1
            else:
                failed += 1
        
        if coords:
            geocoded[point] = coords
    
    return geocoded, from_local, from_api, failed

def calculate_dynamic_threshold(distance_from_origin_km):
    """
    Calculate dynamic threshold based on distance from origin
    Closer to origin = smaller threshold (more strict)
    Farther from origin = larger threshold (more lenient)
    """
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
        
        print(f"  ✅ {distance_km:.1f} ק\"מ | {len(coordinates)} נקודות")
        print(f"  ℹ️  הסף יחושב דינמית לכל נקודה לפי מרחקה מהמוצא")
        
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

async def create_scenario_map(scenario_num, destination, test_points, output_file):
    origin = "גברעם"
    
    print(f"\n{'='*80}")
    print(f"  תרחיש {scenario_num}: גברעם → {destination}")
    print(f"  🎯 בודק {len(test_points)} נקודות")
    print(f"{'='*80}")
    
    # ⏱️ שלב 1: חישוב מסלול (פעם אחת!)
    route_start = time.time()
    route_data = await get_route_data(origin, destination)
    route_time = time.time() - route_start
    
    if not route_data:
        print("❌ לא הצלחתי לקבל נתוני מסלול")
        return None
    
    # ⏱️ שלב 2: Batch geocoding (מהיר מאוד!)
    print(f"\n⚡ Pre-geocoding {len(test_points)} נקודות...")
    geocode_start = time.time()
    geocoded_points, from_local, from_api, failed_geocode = batch_geocode_points(test_points)
    geocode_time = time.time() - geocode_start
    print(f"   ✅ {from_local} מקומי (GeoJSON), {from_api} API, {failed_geocode} נכשל | {geocode_time:.1f}s")
    
    # ⏱️ שלב 3: חישוב מרחקים (מהיר מאוד - חישוב מקומי!)
    print(f"\n⚡ מחשב מרחקים...")
    calc_start = time.time()
    
    mid_idx = len(route_data['coordinates']) // 2
    center = route_data['coordinates'][mid_idx]
    
    m = folium.Map(location=center, zoom_start=9, tiles='OpenStreetMap')
    
    route_line = [(lat, lon) for lat, lon in route_data['coordinates']]
    folium.PolyLine(
        route_line,
        color='#0066CC',
        weight=5,
        opacity=0.8,
        popup=f"מסלול: גברעם → {destination}<br>מרחק: {route_data['distance_km']:.1f} ק\"מ"
    ).add_to(m)
    
    folium.Marker(
        route_data['origin_coords'],
        popup=f"<b>🏠 מוצא: גברעם</b>",
        tooltip="גברעם",
        icon=folium.Icon(color='darkgreen', icon='home', prefix='fa')
    ).add_to(m)
    
    folium.Marker(
        route_data['dest_coords'],
        popup=f"<b>🎯 יעד: {destination}</b>",
        tooltip=destination,
        icon=folium.Icon(color='darkred', icon='flag-checkered', prefix='fa')
    ).add_to(m)
    
    print(f"\n🎒 בודק {len(test_points)} נקודות:")
    print(f"{'#':<4} {'נקודה':<25} {'מרחק':>10} {'סף':>8} {'סטטוס':>6}")
    print("-" * 65)
    
    on_route = 0
    too_far = 0
    failed = 0
    
    for i, point_name in enumerate(test_points, 1):
        point_coords = geocoded_points.get(point_name)
        
        if not point_coords:
            print(f"{i:3}. {point_name:<22} {'---':>10} {'---':>8} {'❌':>6}")
            failed += 1
            continue
        
        # 🆕 Calculate distance from origin to this point
        distance_from_origin = geopy_distance(route_data['origin_coords'], point_coords).kilometers
        
        # 🆕 Calculate dynamic threshold based on distance from origin
        dynamic_threshold = calculate_dynamic_threshold(distance_from_origin)
        
        min_distance, closest_point = calculate_min_distance_to_route(
            route_data['coordinates'],
            point_coords
        )
        
        is_on_route = min_distance <= dynamic_threshold
        
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
        
        print(f"{i:3}. {point_name:<22} {min_distance:>7.1f} ק\"מ {dynamic_threshold:>6.1f} {status:>6}")
        
        folium.Marker(
            point_coords,
            popup=f"<b>{point_name}</b><br>" +
                  f"מרחק ממסלול: {min_distance:.1f} ק\"מ<br>" +
                  f"מרחק ממוצא: {distance_from_origin:.1f} ק\"מ<br>" +
                  f"סף דינמי: {dynamic_threshold:.1f} ק\"מ",
            tooltip=f"{point_name}",
            icon=folium.Icon(color=color, icon=icon, prefix='fa')
        ).add_to(m)
    
    calc_time = time.time() - calc_start
    
    total = on_route + too_far
    success_rate = (on_route / total * 100) if total > 0 else 0
    
    print("-" * 65)
    print(f"📊 {on_route} ✅ | {too_far} ❌ | {failed} כשלון | {success_rate:.0f}%")
    print(f"\n⏱️  ביצועים:")
    print(f"   🛣️  חישוב מסלול: {route_time:.2f}s (OSRM API)")
    print(f"   📍 Geocoding: {geocode_time:.2f}s ({from_local} מקומי, {from_api} API)")
    print(f"   🧮 חישוב מרחקים: {calc_time:.2f}s (חישוב מקומי טהור!)")
    print(f"   ⚡ סה\"כ: {route_time + geocode_time + calc_time:.2f}s")
    
    legend_html = f"""
    <div style="position: fixed; bottom: 30px; right: 30px; width: 340px;
                background-color: white; border:3px solid #0066CC; z-index:9999; 
                font-size:14px; padding: 15px; border-radius: 8px;
                box-shadow: 3px 3px 10px rgba(0,0,0,0.4);">
        <h3 style="margin-top:0; color:#0066CC;">
            תרחיש {scenario_num}: גברעם → {destination}
        </h3>
        <b>📏 מסלול:</b> {route_data['distance_km']:.1f} ק"מ<br>
        <b>🎯 סף דינמי:</b> {ROUTE_PROXIMITY_MIN_THRESHOLD_KM:.1f}-{ROUTE_PROXIMITY_MAX_THRESHOLD_KM:.1f} ק"מ<br>
        <small style="color: #666;">קרוב למוצא = סף קטן, רחוק מהמוצא = סף גדול</small>
        <hr>
        <h4 style="color: #2ECC71;">✅ על הדרך: {on_route}</h4>
        <h4 style="color: #E67E22;">❌ רחוק: {too_far}</h4>
        <h4 style="color: #3498DB;">🎯 הצלחה: {success_rate:.0f}%</h4>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))
    
    plugins.Fullscreen().add_to(m)
    
    output_path = os.path.join(project_root, 'tests', 'outputs', output_file)
    m.save(output_path)
    print(f"\n✅ מפה: {output_path}")
    
    return {
        'file': output_file,
        'on_route': on_route,
        'too_far': too_far,
        'failed': failed,
        'success_rate': success_rate,
        'distance': route_data['distance_km']
    }

async def main():
    print("\n" + "🗺️ "*40)
    print("  תרחישי בדיקה מקיפים מגברעם")
    print("  5 מסלולים × 50 נקודות = 250 בדיקות!")
    print("🗺️ "*40)
    
    load_settlements()  # Pre-load
    
    scenarios = [
        {
            "num": 1,
            "destination": "תל אביב",
            "test_points": [
                # ערים מרכזיות
                "אשדוד", "אשקלון", "ראשון לציון", "חולון", "בת ים", "תל אביב",
                "רמלה", "לוד", "רחובות", "נס ציונה", "יבנה", "גדרה",
                "קרית גת", "קרית מלאכי", "גן יבנה", "מזכרת בתיה",
                # קיבוצים ומושבים באזור
                "קיבוץ רעים", "קיבוץ ניר עם", "קיבוץ זיקים", "קיבוץ בארי",
                "קיבוץ נחל עוז", "קיבוץ כיסופים", "מושב שובה", "מושב זמרת",
                "מושב בני דרום", "מושב תלמי יוסף", "כפר עזה", "מושב עמיעוז",
                # ישובים נוספים
                "שדרות", "נתיבות", "אופקים", "שדה צבי", "ישע", "מבטחים",
                "עזר", "גבים", "אבשלום", "ניצן", "נווה מבטח", "ספיר",
                "מחנה טלי", "באר גנים", "בני נצרים", "ניר ישראל",
                "שלווה", "תקומה"
            ],
            "output": "gevaram_50_tel_aviv.html"
        },
        {
            "num": 2,
            "destination": "ירושלים",
            "test_points": [
                # ערים מרכזיות
                "קרית גת", "בית שמש", "קרית מלאכי", "אשדוד", "אשקלון",
                "באר טוביה", "גדרה", "יבנה", "נתיבות", "לטרון",
                "צור הדסה", "מבשרת ציון", "מוצא", "ירושלים",
                # קיבוצים ומושבים
                "מושב לכיש", "מושב עמציה", "מושב עגור", "מושב נחלה",
                "מושב בית גוברין", "מושב צפרירים", "מושב זכריה", "מושב נחושה",
                "קיבוץ רעים", "קיבוץ ניר עם", "מושב תלמי יוסף",
                # ערים נוספות
                "שדרות", "אופקים", "גן יבנה", "געתון", "כרמי יוסף",
                "בית נחמיה", "שדה משה", "נועם", "גיאה", "קדמה",
                "חוסן", "מסילת ציון", "צלפון", "אורה", "נוב",
                "שורש", "תרום", "כפר אוריה", "רגבה", "זנוח",
                "עין ראפה", "מתתיהו", "מודיעין", "חשמונאים"
            ],
            "output": "gevaram_50_jerusalem.html"
        },
        {
            "num": 3,
            "destination": "באר שבע",
            "test_points": [
                # ערים
                "נתיבות", "שדרות", "אופקים", "באר שבע", "רהט", "לקיה",
                "תל שבע", "גילת", "קרית גת", "דימונה", "ערד",
                # קיבוצים ומושבים באזור
                "קיבוץ רעים", "קיבוץ ניר עם", "קיבוץ זיקים", "קיבוץ בארי",
                "קיבוץ כיסופים", "קיבוץ נחל עוז", "קיבוץ כרם שלום",
                "מושב זמרת", "מושב ישע", "מושב אוהד", "מושב תלמי אליהו",
                "מושב תקומה", "מושב שובל", "מושב ניר עקיבא", "מושב חוות שקמים",
                # ישובים נוספים
                "מבטחים", "עזר", "גבים", "מעון", "להב", "להבים",
                "דביר", "מיתר", "שובה", "פרי גן", "יד בנימין",
                "שדה דוד", "בית קמה", "תושיה", "מגן", "כפר סילבר",
                "חלץ", "נירים", "עין הבשור", "יכיני", "נחל עוז",
                "סופה", "גרופית", "פטיש", "שדה ניצן"
            ],
            "output": "gevaram_50_beer_sheva.html"
        },
        {
            "num": 4,
            "destination": "חיפה",
            "test_points": [
                # ערים מרכזיות בדרך
                "אשדוד", "אשקלון", "רחובות", "נס ציונה", "רמלה", "לוד",
                "ראשון לציון", "תל אביב", "הרצליה", "נתניה", "חדרה",
                "קיסריה", "זכרון יעקב", "עתלית", "טירת כרמל", "חיפה",
                # ישובים לאורך הדרך
                "יבנה", "גדרה", "גן יבנה", "קרית מלאכי", "בת ים",
                "חולון", "פתח תקווה", "רעננה", "כפר סבא", "רמת השרון",
                "כפר יונה", "עמק חפר", "בנימינה", "פרדס חנה", "מגדים",
                "ג'סר א-זרקא", "אור עקיבא", "בנימינה-גבעת עדה",
                # קיבוצים ומושבים
                "מושב בן עמי", "מושב גבעת חיים", "מושב עין שמר", "קיבוץ מענית",
                "קיבוץ שדות ים", "מושב בית חנניה", "מושב חגור", "מושב שדה יצחק",
                "קיבוץ גבעת חיים איחוד", "מושב צור משה", "קיבוץ אילון",
                "מושב חרוצים", "מושב עין ורד"
            ],
            "output": "gevaram_50_haifa.html"
        },
        {
            "num": 5,
            "destination": "נתניה",
            "test_points": [
                # ערים בדרך
                "אשדוד", "אשקלון", "יבנה", "גן יבנה", "קרית מלאכי",
                "גדרה", "נס ציונה", "רחובות", "רמלה", "לוד",
                "ראשון לציון", "תל אביב", "פתח תקווה", "כפר סבא",
                "רעננה", "הרצליה", "נתניה",
                # ישובים נוספים
                "בת ים", "חולון", "רמת השרון", "הוד השרון", "צורן קדימה",
                "מזכרת בתיה", "באר יעקב", "גני תקווה", "קרית אונו", "אור יהודה",
                "יהוד מונוסון", "אזור", "בני עי\"ש", "גבעת שמואל",
                # מושבים וקיבוצים
                "מושב בן עמי", "מושב גבעת חיים", "קיבוץ מענית", "מושב חגור",
                "מושב עין שמר", "קיבוץ שדות ים", "מושב בית יהושע",
                "מושב נורדיה", "מושב בצרה", "מושב עין ורד", "קיבוץ יקום",
                "מושב חרוצים", "קיבוץ גבעת חיים איחוד", "מושב צור משה",
                "מושב בית חנניה", "קיבוץ אילון", "מושב שדה יצחק"
            ],
            "output": "gevaram_50_netanya.html"
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
            
            await asyncio.sleep(3)  # Delay between scenarios
            
        except Exception as e:
            print(f"❌ שגיאה בתרחיש {scenario['num']}: {e}")
    
    print("\n" + "="*80)
    print("  📊 סיכום כללי")
    print("="*80)
    
    for i, result in enumerate(results, 1):
        print(f"\nתרחיש {i}: {result['file']}")
        print(f"  📏 {result['distance']:.1f} ק\"מ | סף דינמי: {ROUTE_PROXIMITY_MIN_THRESHOLD_KM:.1f}-{ROUTE_PROXIMITY_MAX_THRESHOLD_KM:.1f} ק\"מ")
        print(f"  ✅ {result['on_route']} על הדרך | ❌ {result['too_far']} רחוק")
        print(f"  🎯 {result['success_rate']:.0f}% הצלחה")
    
    overall = (total_on_route / total_tested * 100) if total_tested > 0 else 0
    
    print("\n" + "-"*80)
    print(f"📊 סה\"כ: {total_tested} נקודות | {total_on_route} על הדרך | {overall:.1f}% הצלחה")
    print("-"*80)
    print(f"\n✅ נוצרו {len(results)} מפות HTML!")
    print(f"📂 tests/outputs/gevaram_50_*.html")
    print("="*80 + "\n")

if __name__ == "__main__":
    asyncio.run(main())

