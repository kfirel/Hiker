#!/usr/bin/env python3
"""
Test scenarios from Gevaram (גברעם) - 5 routes with 15 test points each
Uses local settlement database for accurate geocoding of small kibbutzim
"""

import asyncio
import requests
from functools import lru_cache
from geopy.distance import distance as geopy_distance
import folium
from folium import plugins
import time

# Config
OSRM_API_URL = "http://router.project-osrm.org"
NOMINATIM_API_URL = "https://nominatim.openstreetmap.org"
NOMINATIM_USER_AGENT = "HikerApp/1.0"
ROUTE_PROXIMITY_MIN_THRESHOLD_KM = 2.5
ROUTE_PROXIMITY_MAX_THRESHOLD_KM = 10.0
ROUTE_PROXIMITY_SCALE_FACTOR = 10.0
API_TIMEOUT_SECONDS = 10

# Local database of known settlements in the area (lat, lon)
KNOWN_SETTLEMENTS = {
    # Kibbutzim near Gaza envelope
    "גברעם": (31.4603, 34.4697),
    "gevaram": (31.4603, 34.4697),
    "ניר-עם": (31.4167, 34.4500),
    "ניר עם": (31.4167, 34.4500),
    "קיבוץ ניר-עם": (31.4167, 34.4500),
    "קיבוץ ניר עם": (31.4167, 34.4500),
    "זיקים": (31.5833, 34.4833),
    "קיבוץ זיקים": (31.5833, 34.4833),
    "כרם שלום": (31.2333, 34.4167),
    "קיבוץ כרם שלום": (31.2333, 34.4167),
    "נחל עוז": (31.4167, 34.4667),
    "קיבוץ נחל עוז": (31.4167, 34.4667),
    "כיסופים": (31.3833, 34.4333),
    "קיבוץ כיסופים": (31.3833, 34.4333),
    "עין השלושה": (31.2167, 34.3500),
    "קיבוץ עין השלושה": (31.2167, 34.3500),
    "רעים": (31.4833, 34.4833),
    "קיבוץ רעים": (31.4833, 34.4833),
    "יד מרדכי": (31.5667, 34.5000),
    "קיבוץ יד מרדכי": (31.5667, 34.5000),
    "מפלסים": (31.4167, 34.4833),
    "קיבוץ מפלסים": (31.4167, 34.4833),
    "בארי": (31.3333, 34.4500),
    "קיבוץ בארי": (31.3333, 34.4500),
    "ניר יצחק": (31.3167, 34.4167),
    "קיבוץ ניר יצחק": (31.3167, 34.4167),
    
    # Major cities (as fallback)
    "שדרות": (31.5244, 34.5964),
    "אשקלון": (31.6688, 34.5742),
    "אשדוד": (31.8044, 34.6553),
    "באר שבע": (31.2518, 34.7913),
    "beer sheva": (31.2518, 34.7913),
    "נתיבות": (31.4170, 34.5961),
    "אופקים": (31.3140, 34.6181),
    "קרית גת": (31.6100, 34.7642),
    "קרית מלאכי": (31.7331, 34.7481),
}

def calculate_dynamic_threshold(route_distance_km):
    threshold = ROUTE_PROXIMITY_MIN_THRESHOLD_KM + (route_distance_km / ROUTE_PROXIMITY_SCALE_FACTOR)
    return max(ROUTE_PROXIMITY_MIN_THRESHOLD_KM, min(threshold, ROUTE_PROXIMITY_MAX_THRESHOLD_KM))

@lru_cache(maxsize=500)
def geocode_address(address):
    try:
        # Normalize address for lookup
        normalized = address.strip().lower()
        
        # Check local database first (for small settlements)
        if normalized in KNOWN_SETTLEMENTS:
            coords = KNOWN_SETTLEMENTS[normalized]
            print(f"  ✅ '{address}' from local DB → ({coords[0]:.4f}, {coords[1]:.4f})")
            return coords
        
        # Try without "קיבוץ" prefix
        if normalized.startswith("קיבוץ "):
            name_without_prefix = normalized.replace("קיבוץ ", "")
            if name_without_prefix in KNOWN_SETTLEMENTS:
                coords = KNOWN_SETTLEMENTS[name_without_prefix]
                print(f"  ✅ '{address}' from local DB → ({coords[0]:.4f}, {coords[1]:.4f})")
                return coords
        
        # Try without "מושב" prefix
        if normalized.startswith("מושב "):
            name_without_prefix = normalized.replace("מושב ", "")
            if name_without_prefix in KNOWN_SETTLEMENTS:
                coords = KNOWN_SETTLEMENTS[name_without_prefix]
                print(f"  ✅ '{address}' from local DB → ({coords[0]:.4f}, {coords[1]:.4f})")
                return coords
        
        # Add small delay to avoid rate limiting
        time.sleep(0.5)
        
        # Fallback to Nominatim
        params = {'q': f"{address}, Israel", 'format': 'json', 'limit': 1}
        headers = {'User-Agent': NOMINATIM_USER_AGENT}
        response = requests.get(NOMINATIM_API_URL + "/search", params=params, headers=headers, timeout=API_TIMEOUT_SECONDS)
        response.raise_for_status()
        results = response.json()
        if not results:
            print(f"  ⚠️  No results for '{address}'")
            return None
        
        coords = (float(results[0]['lat']), float(results[0]['lon']))
        print(f"  ✅ '{address}' from Nominatim → ({coords[0]:.4f}, {coords[1]:.4f})")
        return coords
        
    except Exception as e:
        print(f"  ⚠️  Geocoding error for '{address}': {str(e)[:50]}")
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

def _calculate_route_length(coordinates):
    if len(coordinates) < 2:
        return 0.0
    total = 0.0
    for i in range(len(coordinates) - 1):
        total += geopy_distance(coordinates[i], coordinates[i + 1]).kilometers
    return total

def _parse_osrm_geometry(geometry, target_resolution_km=1.0):
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
            if dist >= target_resolution_km:
                coordinates.append(current)
                last_included = current
        if coordinates[-1] != (raw_coords[-1][1], raw_coords[-1][0]):
            coordinates.append((raw_coords[-1][1], raw_coords[-1][0]))
    return coordinates

async def get_route_data(origin, destination):
    try:
        print(f"\n🗺️  מחשב מסלול: {origin} → {destination}")
        origin_coords = geocode_address(origin)
        dest_coords = geocode_address(destination)
        
        if not origin_coords or not dest_coords:
            print(f"  ❌ Geocoding failed")
            return None
            
        url = f"{OSRM_API_URL}/route/v1/driving/{origin_coords[1]},{origin_coords[0]};{dest_coords[1]},{dest_coords[0]}"
        params = {'overview': 'full', 'geometries': 'geojson'}
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: requests.get(url, params=params, timeout=API_TIMEOUT_SECONDS))
        response.raise_for_status()
        data = response.json()
        
        if data.get('code') != 'Ok' or not data.get('routes'):
            print(f"  ❌ OSRM route error")
            return None
            
        route = data['routes'][0]
        geometry = route['geometry']
        coordinates = _parse_osrm_geometry(geometry, target_resolution_km=1.0)
        
        if not coordinates:
            print(f"  ❌ No coordinates")
            return None
            
        distance_km = _calculate_route_length(coordinates)
        threshold_km = calculate_dynamic_threshold(distance_km)
        
        print(f"  ✅ מסלול: {distance_km:.1f} ק\"מ | סף: {threshold_km:.1f} ק\"מ | נקודות: {len(coordinates)}")
        
        return {
            "coordinates": coordinates,
            "distance_km": distance_km,
            "threshold_km": threshold_km,
            "origin_coords": origin_coords,
            "dest_coords": dest_coords
        }
    except Exception as e:
        print(f"  ❌ Route error: {str(e)[:100]}")
        return None

async def create_gevaram_scenario_map(scenario_num, destination, test_destinations, output_file):
    """Create a map for a Gevaram scenario"""
    
    origin = "גברעם"
    
    print(f"\n{'='*70}")
    print(f"  תרחיש {scenario_num}: גברעם → {destination}")
    print(f"{'='*70}")
    
    route_data = await get_route_data(origin, destination)
    
    if not route_data:
        print("❌ Failed to get route data")
        return None
    
    # Create map
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
    
    # Add origin and destination
    folium.Marker(
        route_data['origin_coords'],
        popup=f"<b>🏠 מוצא</b><br>גברעם",
        tooltip="גברעם (מוצא)",
        icon=folium.Icon(color='darkgreen', icon='home', prefix='fa')
    ).add_to(m)
    
    folium.Marker(
        route_data['dest_coords'],
        popup=f"<b>🎯 יעד</b><br>{destination}",
        tooltip=f"{destination} (יעד)",
        icon=folium.Icon(color='darkred', icon='flag-checkered', prefix='fa')
    ).add_to(m)
    
    # Test hitchhiker destinations
    print(f"\n🎒 בודק 15 נקודות טרמפיסטים:")
    print(f"{'נקודה':<25} {'מרחק':>10} {'סטטוס':>15} {'% מסף':>10}")
    print("-" * 70)
    
    on_route_count = 0
    too_far_count = 0
    failed_count = 0
    
    for i, dest_name in enumerate(test_destinations, 1):
        dest_coords = geocode_address(dest_name)
        if not dest_coords:
            print(f"{i:2}. {dest_name:<22} {'---':>10} {'❌ Failed':>15} {'':>10}")
            failed_count += 1
            continue
        
        min_distance, closest_point = calculate_min_distance_to_route(
            route_data['coordinates'],
            dest_coords
        )
        
        is_on_route = min_distance <= route_data['threshold_km']
        
        if is_on_route:
            color = 'lightgreen'
            icon = 'check-circle'
            status = "✅"
            on_route_count += 1
        else:
            color = 'orange'
            icon = 'times-circle'
            status = "❌"
            too_far_count += 1
        
        percentage = (min_distance / route_data['threshold_km'] * 100)
        
        print(f"{i:2}. {dest_name:<22} {min_distance:>7.1f} ק\"מ {status:>15} {percentage:>7.0f}%")
        
        # Add marker
        folium.Marker(
            dest_coords,
            popup=f"""
                <div style='width: 200px'>
                    <h4>{dest_name}</h4>
                    <b>מרחק מהמסלול:</b> {min_distance:.1f} ק"מ<br>
                    <b>סף:</b> {route_data['threshold_km']:.1f} ק"מ<br>
                    <b>אחוז מהסף:</b> {percentage:.0f}%<br>
                    <b>סטטוס:</b> {'✅ על הדרך' if is_on_route else '❌ רחוק מדי'}
                </div>
            """,
            tooltip=f"{dest_name} ({min_distance:.1f} ק\"מ)",
            icon=folium.Icon(color=color, icon=icon, prefix='fa')
        ).add_to(m)
        
        # Draw line to closest point
        if closest_point:
            folium.PolyLine(
                [dest_coords, closest_point],
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
    total_tested = on_route_count + too_far_count
    success_rate = (on_route_count / total_tested * 100) if total_tested > 0 else 0
    
    print("-" * 70)
    print(f"📊 סיכום: {on_route_count} על הדרך | {too_far_count} רחוק | {failed_count} כשלון")
    print(f"🎯 שיעור הצלחה: {success_rate:.0f}%")
    
    # Add comprehensive legend
    legend_html = f"""
    <div style="position: fixed; 
                bottom: 30px; right: 30px; width: 340px;
                background-color: white; border:3px solid #0066CC; z-index:9999; 
                font-size:13px; padding: 15px; border-radius: 8px;
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
            <h4 style="margin: 5px 0; color: #2ECC71;">✅ על הדרך: {on_route_count}</h4>
            <h4 style="margin: 5px 0; color: #E67E22;">❌ רחוק מדי: {too_far_count}</h4>
            {f'<h4 style="margin: 5px 0; color: #95A5A6;">⚠️  כשלון: {failed_count}</h4>' if failed_count > 0 else ''}
        </div>
        
        <hr style="border: 1px solid #eee;">
        
        <div style="font-size: 11px; color: #7F8C8D; margin-top: 10px;">
            <b>🎯 שיעור הצלחה:</b> {success_rate:.0f}%<br>
            <i>קווים ירוקים = על הדרך<br>
            קווים אדומים = רחוק מדי<br>
            נקודות כחולות = הנקודה הקרובה ביותר</i>
        </div>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))
    
    plugins.Fullscreen().add_to(m)
    
    m.save(output_file)
    print(f"\n✅ מפה נשמרה ב: {output_file}")
    
    return {
        'file': output_file,
        'on_route': on_route_count,
        'too_far': too_far_count,
        'failed': failed_count,
        'success_rate': success_rate,
        'route_distance': route_data['distance_km'],
        'threshold': route_data['threshold_km']
    }

async def main():
    print("\n" + "🗺️ "*35)
    print("  תרחישי בדיקה מגברעם - 5 מסלולים x 15 נקודות")
    print("  🏡 משתמש במאגר מקומי לזיהוי קיבוצים ומושבים קטנים")
    print("🗺️ "*35)
    
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
                "נתיבות", "שדרות", "אופקים", "להבים", "דביר",
                "מיתר", "רהט", "לקיה", "תל שבע", "ערד",
                "אשקלון", "קרית גת", "קרית מלאכי", "נתיב העשרה", "גילת"
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
            "destination": "באר שבע",  # Changed from Eilat due to timeout issues
            "test_points": [
                "שדרות", "נתיבות", "אופקים", "קיבוץ רעים", "קיבוץ ניר עם",
                "קיבוץ זיקים", "קיבוץ בארי", "קיבוץ כיסופים", "ערד", "דימונה",
                "ירוחם", "מצפה רמון", "אשקלון", "קרית גת", "רהט"
            ],
            "output": "gevaram_5_beer_sheva_kibbutzim.html"
        }
    ]
    
    results = []
    total_on_route = 0
    total_tested = 0
    
    for scenario in scenarios:
        try:
            print(f"\n{'='*70}")
            print(f"מעבד תרחיש {scenario['num']}/5...")
            print(f"{'='*70}")
            
            result = await create_gevaram_scenario_map(
                scenario["num"],
                scenario["destination"],
                scenario["test_points"],
                scenario["output"]
            )
            
            if result:
                results.append(result)
                total_on_route += result['on_route']
                total_tested += (result['on_route'] + result['too_far'])
            
            # Delay between scenarios to avoid rate limiting
            await asyncio.sleep(3)
            
        except Exception as e:
            print(f"❌ שגיאה בתרחיש {scenario['num']}: {e}")
    
    # Final summary
    print("\n" + "="*70)
    print("  📊 סיכום כללי - כל התרחישים")
    print("="*70)
    
    for i, result in enumerate(results, 1):
        print(f"\nתרחיש {i}:")
        print(f"  📁 {result['file']}")
        print(f"  📏 מרחק: {result['route_distance']:.1f} ק\"מ | סף: {result['threshold']:.1f} ק\"מ")
        print(f"  ✅ על הדרך: {result['on_route']} | ❌ רחוק: {result['too_far']}")
        print(f"  🎯 הצלחה: {result['success_rate']:.0f}%")
    
    overall_success = (total_on_route / total_tested * 100) if total_tested > 0 else 0
    
    print("\n" + "-"*70)
    print(f"📊 סה\"כ נקודות נבדקו: {total_tested}")
    print(f"✅ סה\"כ על הדרך: {total_on_route}")
    print(f"🎯 שיעור הצלחה כולל: {overall_success:.1f}%")
    print("-"*70)
    
    print(f"\n✅ נוצרו {len(results)} מפות אינטראקטיביות!")
    print("📂 פתח את הקבצים בדפדפן לראות את התוצאות המלאות")
    print("="*70)

if __name__ == "__main__":
    asyncio.run(main())

