#!/usr/bin/env python3
"""
Multiple test scenarios for route visualization
Creates several maps demonstrating different cases
"""

import asyncio
import requests
from functools import lru_cache
from geopy.distance import distance as geopy_distance
import folium
from folium import plugins

# Config
OSRM_API_URL = "http://router.project-osrm.org"
NOMINATIM_API_URL = "https://nominatim.openstreetmap.org"
NOMINATIM_USER_AGENT = "HikerApp/1.0"
ROUTE_PROXIMITY_MIN_THRESHOLD_KM = 2.5
ROUTE_PROXIMITY_MAX_THRESHOLD_KM = 10.0
ROUTE_PROXIMITY_SCALE_FACTOR = 10.0
API_TIMEOUT_SECONDS = 10

# Copy functions
def calculate_dynamic_threshold(route_distance_km):
    threshold = ROUTE_PROXIMITY_MIN_THRESHOLD_KM + (route_distance_km / ROUTE_PROXIMITY_SCALE_FACTOR)
    return max(ROUTE_PROXIMITY_MIN_THRESHOLD_KM, min(threshold, ROUTE_PROXIMITY_MAX_THRESHOLD_KM))

@lru_cache(maxsize=200)
def geocode_address(address):
    try:
        params = {'q': f"{address}, Israel", 'format': 'json', 'limit': 1}
        headers = {'User-Agent': NOMINATIM_USER_AGENT}
        response = requests.get(NOMINATIM_API_URL + "/search", params=params, headers=headers, timeout=API_TIMEOUT_SECONDS)
        response.raise_for_status()
        results = response.json()
        if not results:
            return None
        return (float(results[0]['lat']), float(results[0]['lon']))
    except Exception as e:
        print(f"❌ Geocoding error for '{address}': {e}")
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
        origin_coords = geocode_address(origin)
        dest_coords = geocode_address(destination)
        if not origin_coords or not dest_coords:
            return None
        url = f"{OSRM_API_URL}/route/v1/driving/{origin_coords[1]},{origin_coords[0]};{dest_coords[1]},{dest_coords[0]}"
        params = {'overview': 'full', 'geometries': 'geojson'}
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: requests.get(url, params=params, timeout=API_TIMEOUT_SECONDS))
        response.raise_for_status()
        data = response.json()
        if data.get('code') != 'Ok' or not data.get('routes'):
            return None
        route = data['routes'][0]
        geometry = route['geometry']
        coordinates = _parse_osrm_geometry(geometry, target_resolution_km=1.0)
        if not coordinates:
            return None
        distance_km = _calculate_route_length(coordinates)
        threshold_km = calculate_dynamic_threshold(distance_km)
        return {
            "coordinates": coordinates,
            "distance_km": distance_km,
            "threshold_km": threshold_km,
            "origin_coords": origin_coords,
            "dest_coords": dest_coords
        }
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

async def create_scenario_map(scenario_name, driver_origin, driver_dest, test_destinations, output_file):
    """Create a map for a specific scenario"""
    
    print(f"\n{'='*60}")
    print(f"  {scenario_name}")
    print(f"{'='*60}")
    print(f"📍 Driver route: {driver_origin} → {driver_dest}")
    
    route_data = await get_route_data(driver_origin, driver_dest)
    
    if not route_data:
        print("❌ Failed to get route data")
        return None
    
    print(f"✅ Route: {route_data['distance_km']:.1f} km")
    print(f"✅ Threshold: {route_data['threshold_km']:.1f} km")
    
    # Create map
    mid_idx = len(route_data['coordinates']) // 2
    center = route_data['coordinates'][mid_idx]
    
    m = folium.Map(location=center, zoom_start=10, tiles='OpenStreetMap')
    
    # Add route line
    route_line = [(lat, lon) for lat, lon in route_data['coordinates']]
    folium.PolyLine(
        route_line,
        color='blue',
        weight=4,
        opacity=0.7,
        popup=f"מסלול: {driver_origin} → {driver_dest}<br>מרחק: {route_data['distance_km']:.1f} ק\"מ<br>סף: {route_data['threshold_km']:.1f} ק\"מ"
    ).add_to(m)
    
    # Add origin and destination
    folium.Marker(
        route_data['origin_coords'],
        popup=f"<b>מוצא</b><br>{driver_origin}",
        tooltip=driver_origin,
        icon=folium.Icon(color='green', icon='play', prefix='fa')
    ).add_to(m)
    
    folium.Marker(
        route_data['dest_coords'],
        popup=f"<b>יעד</b><br>{driver_dest}",
        tooltip=driver_dest,
        icon=folium.Icon(color='red', icon='stop', prefix='fa')
    ).add_to(m)
    
    # Test hitchhiker destinations
    print(f"\n🎒 Testing hitchhiker destinations:")
    
    on_route_count = 0
    too_far_count = 0
    
    for dest_name in test_destinations:
        dest_coords = geocode_address(dest_name)
        if not dest_coords:
            print(f"  ⚠️  Failed to geocode: {dest_name}")
            continue
        
        min_distance, closest_point = calculate_min_distance_to_route(
            route_data['coordinates'],
            dest_coords
        )
        
        is_on_route = min_distance <= route_data['threshold_km']
        
        if is_on_route:
            color = 'lightgreen'
            icon = 'check'
            status = "✅ על הדרך"
            on_route_count += 1
        else:
            color = 'orange'
            icon = 'times'
            status = "❌ רחוק מדי"
            too_far_count += 1
        
        percentage = (min_distance / route_data['threshold_km'] * 100)
        print(f"  {status} - {dest_name}: {min_distance:.1f} ק\"מ ({percentage:.0f}% מהסף)")
        
        # Add marker
        folium.Marker(
            dest_coords,
            popup=f"""
                <b>{dest_name}</b><br>
                מרחק מהמסלול: {min_distance:.1f} ק"מ<br>
                סף: {route_data['threshold_km']:.1f} ק"מ<br>
                {percentage:.0f}% מהסף<br>
                <b>{status}</b>
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
                opacity=0.6,
                dash_array='5, 5',
                popup=f"מרחק: {min_distance:.1f} ק\"מ"
            ).add_to(m)
            
            folium.CircleMarker(
                closest_point,
                radius=4,
                color='blue',
                fill=True,
                fillColor='blue',
                fillOpacity=0.7
            ).add_to(m)
    
    # Add legend
    legend_html = f"""
    <div style="position: fixed; 
                bottom: 50px; right: 50px; width: 320px;
                background-color: white; border:2px solid grey; z-index:9999; 
                font-size:14px; padding: 10px; border-radius: 5px;
                box-shadow: 2px 2px 6px rgba(0,0,0,0.3);">
        <h4 style="margin-top:0; color:#2874A6;">{scenario_name}</h4>
        <p><i class="fa fa-road" style="color:blue"></i> {driver_origin} → {driver_dest}</p>
        <p><b>מרחק מסלול:</b> {route_data['distance_km']:.1f} ק"מ</p>
        <p><b>סף דינמי:</b> {route_data['threshold_km']:.1f} ק"מ</p>
        <hr>
        <p><i class="fa fa-check" style="color:lightgreen"></i> על הדרך: {on_route_count}</p>
        <p><i class="fa fa-times" style="color:orange"></i> רחוק מדי: {too_far_count}</p>
        <p style="font-size:12px; color:gray; margin-top:10px;">
            קווים ירוקים = על הדרך<br>
            קווים אדומים = רחוק מדי
        </p>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))
    
    plugins.Fullscreen().add_to(m)
    
    m.save(output_file)
    print(f"\n✅ Map saved to: {output_file}")
    print(f"   📊 Summary: {on_route_count} על הדרך, {too_far_count} רחוק מדי")
    
    return output_file

async def main():
    print("\n" + "🗺️ "*30)
    print("  MULTIPLE TEST SCENARIOS - VISUAL MAPS")
    print("🗺️ "*30)
    
    scenarios = [
        {
            "name": "תרחיש 1: מסלול ארוך (תל אביב → חיפה)",
            "origin": "תל אביב",
            "destination": "חיפה",
            "test_points": ["נתניה", "חדרה", "קיסריה", "רעננה", "פתח תקווה", "הרצליה"],
            "output": "scenario_1_long_route.html"
        },
        {
            "name": "תרחיש 2: מסלול בינוני (תל אביב → ירושלים)",
            "origin": "תל אביב",
            "destination": "ירושלים",
            "test_points": ["רמלה", "לוד", "מודיעין", "בית שמש", "ראשון לציון", "חולון"],
            "output": "scenario_2_medium_route.html"
        },
        {
            "name": "תרחיש 3: מסלול קצר (תל אביב → רחובות)",
            "origin": "תל אביב",
            "destination": "רחובות",
            "test_points": ["חולון", "בת ים", "ראשון לציון", "נס ציונה", "רמת גן"],
            "output": "scenario_3_short_route.html"
        },
        {
            "name": "תרחיש 4: מסלול ארוך מאוד (תל אביב → אילת)",
            "origin": "תל אביב",
            "destination": "אילת",
            "test_points": ["באר שבע", "ירוחם", "מצפה רמון", "אשדוד", "קרית גת"],
            "output": "scenario_4_very_long_route.html"
        },
    ]
    
    results = []
    
    for scenario in scenarios:
        try:
            output_file = await create_scenario_map(
                scenario["name"],
                scenario["origin"],
                scenario["destination"],
                scenario["test_points"],
                scenario["output"]
            )
            if output_file:
                results.append(output_file)
            
            # Small delay to avoid overwhelming the API
            await asyncio.sleep(2)
            
        except Exception as e:
            print(f"❌ Error in scenario '{scenario['name']}': {e}")
    
    print("\n" + "="*60)
    print("  SUMMARY")
    print("="*60)
    print(f"\n✅ Created {len(results)} maps:")
    for i, file in enumerate(results, 1):
        print(f"   {i}. {file}")
    
    print("\n📂 Open these files in your browser to compare scenarios!")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())

