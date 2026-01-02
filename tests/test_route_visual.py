#!/usr/bin/env python3
"""
Visual test for route service - creates an interactive HTML map
Shows the route, test points, and distances
"""

import asyncio
import requests
from functools import lru_cache
from geopy.distance import distance as geopy_distance
import folium
from folium import plugins

# Mock config values
OSRM_API_URL = "http://router.project-osrm.org"
NOMINATIM_API_URL = "https://nominatim.openstreetmap.org"
NOMINATIM_USER_AGENT = "HikerApp/1.0"
ROUTE_PROXIMITY_MIN_THRESHOLD_KM = 2.5
ROUTE_PROXIMITY_MAX_THRESHOLD_KM = 10.0
ROUTE_PROXIMITY_SCALE_FACTOR = 10.0
API_TIMEOUT_SECONDS = 10

# Copy functions from route_service

def calculate_dynamic_threshold(route_distance_km):
    threshold = ROUTE_PROXIMITY_MIN_THRESHOLD_KM + (route_distance_km / ROUTE_PROXIMITY_SCALE_FACTOR)
    return max(ROUTE_PROXIMITY_MIN_THRESHOLD_KM, min(threshold, ROUTE_PROXIMITY_MAX_THRESHOLD_KM))

@lru_cache(maxsize=200)
def geocode_address(address):
    try:
        params = {
            'q': f"{address}, Israel",
            'format': 'json',
            'limit': 1
        }
        headers = {'User-Agent': NOMINATIM_USER_AGENT}
        
        response = requests.get(
            NOMINATIM_API_URL + "/search",
            params=params,
            headers=headers,
            timeout=API_TIMEOUT_SECONDS
        )
        response.raise_for_status()
        
        results = response.json()
        if not results:
            return None
        
        lat = float(results[0]['lat'])
        lon = float(results[0]['lon'])
        return (lat, lon)
        
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
        params = {
            'overview': 'full',
            'geometries': 'geojson'
        }
        
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: requests.get(url, params=params, timeout=API_TIMEOUT_SECONDS)
        )
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

async def create_visual_map():
    """Create an interactive map showing routes and test points"""
    
    print("🗺️  Creating interactive map...")
    
    # Test scenario - using well-known cities for better geocoding
    driver_origin = "תל אביב"
    driver_dest = "חיפה"
    
    print(f"\n📍 Driver route: {driver_origin} → {driver_dest}")
    route_data = await get_route_data(driver_origin, driver_dest)
    
    if not route_data:
        print("❌ Failed to get route data")
        return
    
    print(f"✅ Route: {route_data['distance_km']:.1f} km")
    print(f"✅ Threshold: {route_data['threshold_km']:.1f} km")
    
    # Create map centered on route midpoint
    mid_idx = len(route_data['coordinates']) // 2
    center = route_data['coordinates'][mid_idx]
    
    m = folium.Map(
        location=center,
        zoom_start=10,
        tiles='OpenStreetMap'
    )
    
    # Add route line
    route_line = [(lat, lon) for lat, lon in route_data['coordinates']]
    folium.PolyLine(
        route_line,
        color='blue',
        weight=4,
        opacity=0.7,
        popup=f"מסלול: {driver_origin} → {driver_dest}<br>מרחק: {route_data['distance_km']:.1f} ק\"מ"
    ).add_to(m)
    
    # Add origin marker
    folium.Marker(
        route_data['origin_coords'],
        popup=f"<b>מוצא</b><br>{driver_origin}",
        tooltip=driver_origin,
        icon=folium.Icon(color='green', icon='play', prefix='fa')
    ).add_to(m)
    
    # Add destination marker
    folium.Marker(
        route_data['dest_coords'],
        popup=f"<b>יעד</b><br>{driver_dest}",
        tooltip=driver_dest,
        icon=folium.Icon(color='red', icon='stop', prefix='fa')
    ).add_to(m)
    
    # Test multiple hitchhiker destinations (relevant to Tel Aviv-Haifa route)
    test_destinations = [
        ("נתניה", "should be on route"),
        ("חדרה", "should be on route"),
        ("קיסריה", "should be close to route"),
        ("זכרון יעקב", "should be too far"),
        ("רעננה", "should be too far"),
    ]
    
    print(f"\n🎒 Testing hitchhiker destinations:")
    
    for dest_name, description in test_destinations:
        dest_coords = geocode_address(dest_name)
        if not dest_coords:
            print(f"  ❌ Failed to geocode: {dest_name}")
            continue
        
        # Calculate distance to route
        min_distance, closest_point = calculate_min_distance_to_route(
            route_data['coordinates'],
            dest_coords
        )
        
        is_on_route = min_distance <= route_data['threshold_km']
        
        # Determine marker color and icon
        if is_on_route:
            color = 'lightgreen'
            icon = 'check'
            status = "✅ על הדרך"
        else:
            color = 'orange'
            icon = 'times'
            status = "❌ רחוק מדי"
        
        print(f"  {status} - {dest_name}: {min_distance:.1f} ק\"מ מהמסלול")
        
        # Add hitchhiker marker
        folium.Marker(
            dest_coords,
            popup=f"""
                <b>{dest_name}</b><br>
                מרחק מהמסלול: {min_distance:.1f} ק"מ<br>
                סף: {route_data['threshold_km']:.1f} ק"מ<br>
                <b>{status}</b>
            """,
            tooltip=f"{dest_name} ({min_distance:.1f} ק\"מ)",
            icon=folium.Icon(color=color, icon=icon, prefix='fa')
        ).add_to(m)
        
        # Draw line to closest point on route
        if closest_point:
            folium.PolyLine(
                [dest_coords, closest_point],
                color='gray' if is_on_route else 'orange',
                weight=2,
                opacity=0.5,
                dash_array='5, 5',
                popup=f"מרחק: {min_distance:.1f} ק\"מ"
            ).add_to(m)
            
            # Add small marker at closest point
            folium.CircleMarker(
                closest_point,
                radius=4,
                color='blue',
                fill=True,
                fillColor='blue',
                fillOpacity=0.7,
                popup=f"הנקודה הקרובה ביותר ל-{dest_name}"
            ).add_to(m)
    
    # Add legend
    legend_html = f"""
    <div style="position: fixed; 
                bottom: 50px; right: 50px; width: 300px; height: auto;
                background-color: white; border:2px solid grey; z-index:9999; 
                font-size:14px; padding: 10px; border-radius: 5px;
                box-shadow: 2px 2px 6px rgba(0,0,0,0.3);">
        <h4 style="margin-top:0">מפת בדיקה - מערכת ניתוב</h4>
        <p><i class="fa fa-road" style="color:blue"></i> מסלול הנהג ({route_data['distance_km']:.1f} ק"מ)</p>
        <p><i class="fa fa-play" style="color:green"></i> מוצא: {driver_origin}</p>
        <p><i class="fa fa-stop" style="color:red"></i> יעד: {driver_dest}</p>
        <p><i class="fa fa-check" style="color:lightgreen"></i> טרמפיסטים על הדרך</p>
        <p><i class="fa fa-times" style="color:orange"></i> טרמפיסטים רחוקים מדי</p>
        <hr>
        <p><b>סף דינמי:</b> {route_data['threshold_km']:.1f} ק"מ</p>
        <p style="font-size:12px; color:gray;">קווים מקווקווים = מרחק מהמסלול</p>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))
    
    # Add fullscreen button
    plugins.Fullscreen().add_to(m)
    
    # Save map
    output_file = 'route_visualization.html'
    m.save(output_file)
    
    print(f"\n✅ Map saved to: {output_file}")
    print(f"📂 Open this file in your browser to see the interactive map!")
    
    return output_file

async def main():
    print("\n" + "🗺️ "*30)
    print("  VISUAL ROUTE TEST - INTERACTIVE MAP")
    print("🗺️ "*30)
    
    await create_visual_map()
    
    print("\n" + "="*60)
    print("✅ Done! Open 'route_visualization.html' in your browser")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())

