#!/usr/bin/env python3
"""
🗺️ מערכת בדיקות מסלולים אינטראקטיבית
שימוש:
    python test_route.py                           # מצב אינטראקטיבי
    python test_route.py --origin גברעם --dest "תל אביב" --points "אשדוד,אשקלון,ראשון לציון"
    python test_route.py --dest "באר שבע" --points "זיקים,שדרות,נתיבות"
"""

import asyncio
import json
import os
import sys
import argparse
import importlib.util
from datetime import datetime
from geopy.distance import distance as geopy_distance
import folium
from folium import plugins

# Setup paths
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    ROUTE_PROXIMITY_MIN_THRESHOLD_KM,
    ROUTE_PROXIMITY_MAX_THRESHOLD_KM,
    ROUTE_PROXIMITY_SCALE_FACTOR
)

# Load route_service directly
route_service_path = os.path.join(os.path.dirname(__file__), 'services', 'route_service.py')
spec = importlib.util.spec_from_file_location("route_service", route_service_path)
route_service = importlib.util.module_from_spec(spec)
spec.loader.exec_module(route_service)

geocode_address = route_service.geocode_address
calculate_dynamic_threshold = route_service.calculate_dynamic_threshold
calculate_distance_between_points = route_service.calculate_distance_between_points

OSRM_API_URL = "http://router.project-osrm.org"
API_TIMEOUT = 10

def print_header(text):
    """Print a nice header"""
    print("\n" + "="*80)
    print(f"  {text}")
    print("="*80)

def print_section(text):
    """Print a section separator"""
    print(f"\n🔹 {text}")
    print("-"*60)

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
    """Get route from OSRM"""
    import requests
    
    print(f"  Calculating route: {origin} -> {destination}")
    
    origin_coords = geocode_address(origin)
    dest_coords = geocode_address(destination)
    
    if not origin_coords or not dest_coords:
        print(f"  ERROR: Geocoding failed")
        return None
    
    try:
        url = f"{OSRM_API_URL}/route/v1/driving/{origin_coords[1]},{origin_coords[0]};{dest_coords[1]},{dest_coords[0]}"
        params = {'overview': 'full', 'geometries': 'geojson'}
        
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: requests.get(url, params=params, timeout=API_TIMEOUT))
        response.raise_for_status()
        
        data = response.json()
        
        if data.get('code') != 'Ok' or not data.get('routes'):
            print(f"  ERROR: OSRM failed")
            return None
        
        route = data['routes'][0]
        geometry = route['geometry']
        coordinates = parse_osrm_geometry(geometry)
        
        if not coordinates:
            print(f"  ERROR: No coordinates")
            return None
        
        distance_km = calculate_route_length(coordinates)
        
        print(f"  ✅ {distance_km:.1f} km | {len(coordinates)} points")
        
        return {
            "coordinates": coordinates,
            "distance_km": distance_km,
            "origin_coords": origin_coords,
            "dest_coords": dest_coords
        }
    except Exception as e:
        print(f"  ERROR: {str(e)[:100]}")
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

async def test_route(origin, destination, test_points, show_map=True, output_file=None):
    """Test a route with multiple points"""
    
    print_header(f"Testing Route: {origin} -> {destination}")
    print(f"  Testing {len(test_points)} points")
    
    # Get route
    route_data = await get_route_data(origin, destination)
    if not route_data:
        print("ERROR: Failed to get route")
        return None
    
    # Geocode test points
    print_section("Geocoding Points")
    geocoded_points = {}
    for point in test_points:
        coords = geocode_address(point)
        if coords:
            geocoded_points[point] = coords
            print(f"  ✅ {point}")
        else:
            print(f"  ❌ {point} - Not found")
    
    # Check each point
    print_section("Testing Points")
    results = []
    
    print(f"{'Point':<25} {'Dist Origin':>12} {'Dist Route':>12} {'Threshold':>10} {'Result':>10}")
    print("-" * 80)
    
    on_route_count = 0
    off_route_count = 0
    
    for point_name, point_coords in geocoded_points.items():
        # Distance from origin
        dist_from_origin = calculate_distance_between_points(route_data['origin_coords'], point_coords)
        
        # Dynamic threshold
        threshold = calculate_dynamic_threshold(dist_from_origin)
        
        # Distance to route
        min_distance, closest_point = calculate_min_distance_to_route(route_data['coordinates'], point_coords)
        
        # Check if on route
        is_on_route = min_distance <= threshold
        
        if is_on_route:
            status = "✅ ON"
            on_route_count += 1
        else:
            status = "❌ OFF"
            off_route_count += 1
        
        print(f"{point_name:<25} {dist_from_origin:>10.1f} km {min_distance:>10.1f} km {threshold:>8.1f} km {status:>10}")
        
        results.append({
            'name': point_name,
            'coords': point_coords,
            'distance_from_origin': dist_from_origin,
            'distance_to_route': min_distance,
            'threshold': threshold,
            'is_on_route': is_on_route
        })
    
    # Summary
    print("-" * 80)
    total = on_route_count + off_route_count
    success_rate = (on_route_count / total * 100) if total > 0 else 0
    print(f"Summary: {on_route_count} ON route | {off_route_count} OFF route | {success_rate:.0f}% success")
    
    # Create map if requested
    if show_map:
        print_section("Creating Map")
        map_file = await create_map(origin, destination, route_data, results, output_file)
        if map_file:
            print(f"  ✅ Map saved: {map_file}")
            
            # Try to open the map
            import subprocess
            try:
                subprocess.run(['open', map_file], check=False)
                print(f"  🌐 Opening map in browser...")
            except:
                print(f"  💡 Open manually: {map_file}")
    
    return {
        'origin': origin,
        'destination': destination,
        'route_distance': route_data['distance_km'],
        'on_route': on_route_count,
        'off_route': off_route_count,
        'success_rate': success_rate,
        'results': results
    }

async def create_map(origin, destination, route_data, results, output_file=None):
    """Create an interactive map"""
    
    # Default output file
    if not output_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"route_test_{timestamp}.html"
    
    # Ensure outputs directory exists
    output_dir = os.path.join(os.path.dirname(__file__), 'tests', 'outputs')
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, output_file)
    
    # Create map centered on route
    mid_idx = len(route_data['coordinates']) // 2
    center = route_data['coordinates'][mid_idx]
    m = folium.Map(location=center, zoom_start=10, tiles='OpenStreetMap')
    
    # Draw route
    route_line = [(lat, lon) for lat, lon in route_data['coordinates']]
    folium.PolyLine(
        route_line,
        color='#0066CC',
        weight=5,
        opacity=0.8,
        popup=f"מסלול: {origin} → {destination}<br>מרחק: {route_data['distance_km']:.1f} ק\"מ"
    ).add_to(m)
    
    # Origin marker
    folium.Marker(
        route_data['origin_coords'],
        popup=f"<b>🏠 מוצא: {origin}</b>",
        tooltip=origin,
        icon=folium.Icon(color='darkgreen', icon='home', prefix='fa')
    ).add_to(m)
    
    # Destination marker
    folium.Marker(
        route_data['dest_coords'],
        popup=f"<b>🎯 יעד: {destination}</b>",
        tooltip=destination,
        icon=folium.Icon(color='darkred', icon='flag-checkered', prefix='fa')
    ).add_to(m)
    
    # Test points
    for result in results:
        if result['is_on_route']:
            color = 'lightgreen'
            icon = 'check-circle'
        else:
            color = 'orange'
            icon = 'times-circle'
        
        popup_text = f"""
        <b>{result['name']}</b><br>
        מרחק ממוצא: {result['distance_from_origin']:.1f} ק"מ<br>
        מרחק ממסלול: {result['distance_to_route']:.1f} ק"מ<br>
        סף דינמי: {result['threshold']:.1f} ק"מ<br>
        {'✅ על הדרך' if result['is_on_route'] else '❌ מחוץ לדרך'}
        """
        
        folium.Marker(
            result['coords'],
            popup=popup_text,
            tooltip=result['name'],
            icon=folium.Icon(color=color, icon=icon, prefix='fa')
        ).add_to(m)
    
    # Legend
    on_route_count = sum(1 for r in results if r['is_on_route'])
    off_route_count = len(results) - on_route_count
    success_rate = (on_route_count / len(results) * 100) if results else 0
    
    legend_html = f"""
    <div style="position: fixed; bottom: 30px; right: 30px; width: 340px;
                background-color: white; border:3px solid #0066CC; z-index:9999; 
                font-size:14px; padding: 15px; border-radius: 8px;
                box-shadow: 3px 3px 10px rgba(0,0,0,0.4);">
        <h3 style="margin-top:0; color:#0066CC;">
            {origin} → {destination}
        </h3>
        <b>📏 מסלול:</b> {route_data['distance_km']:.1f} ק"מ<br>
        <b>🎯 סף דינמי:</b> {ROUTE_PROXIMITY_MIN_THRESHOLD_KM:.1f}-{ROUTE_PROXIMITY_MAX_THRESHOLD_KM:.1f} ק"מ<br>
        <small style="color: #666;">קרוב למוצא = סף קטן, רחוק = סף גדול</small>
        <hr>
        <h4 style="color: #2ECC71;">✅ על הדרך: {on_route_count}</h4>
        <h4 style="color: #E67E22;">❌ רחוק: {off_route_count}</h4>
        <h4 style="color: #3498DB;">🎯 הצלחה: {success_rate:.0f}%</h4>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))
    
    # Add fullscreen button
    plugins.Fullscreen().add_to(m)
    
    # Save map
    m.save(output_path)
    
    return output_path

async def interactive_mode():
    """Interactive CLI mode"""
    print_header("Route Testing System")
    
    print("\nWelcome! Let's test a route")
    print("(You can type in Hebrew)")
    
    # Get origin
    origin = input("\nOrigin (default: Gvar'am): ").strip()
    if not origin:
        origin = "גברעם"
        print(f"  Using default: גברעם")
    
    # Get destination
    destination = input("Destination (e.g., Tel Aviv, Beer Sheva): ").strip()
    if not destination:
        print("ERROR: Must enter a destination!")
        return
    
    # Get test points
    print("\nTest points (separate with commas):")
    print("  Example: Ashdod,Ashkelon,Rishon LeZion,Zikim")
    points_input = input("  Points: ").strip()
    
    if not points_input:
        print("ERROR: Must enter at least one point!")
        return
    
    test_points = [p.strip() for p in points_input.split(',') if p.strip()]
    
    # Show map?
    show_map_input = input("\nShow map? (y/n, default: y): ").strip().lower()
    show_map = show_map_input != 'n'
    
    # Run test
    print()
    result = await test_route(origin, destination, test_points, show_map=show_map)
    
    if result:
        print_header("Test completed successfully!")

async def main():
    parser = argparse.ArgumentParser(
        description='🗺️ מערכת בדיקות מסלולים',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
דוגמאות שימוש:
  python test_route.py
      → מצב אינטראקטיבי
  
  python test_route.py --dest "תל אביב" --points "אשדוד,אשקלון,ראשון לציון"
      → בדיקה מהירה (מוצא: גברעם)
  
  python test_route.py --origin "ירושלים" --dest "חיפה" --points "תל אביב,נתניה" --no-map
      → ללא מפה
        """
    )
    
    parser.add_argument('--origin', '-o', default='גברעם', help='נקודת מוצא (ברירת מחדל: גברעם)')
    parser.add_argument('--dest', '-d', help='יעד')
    parser.add_argument('--points', '-p', help='נקודות לבדיקה (מופרדות בפסיקים)')
    parser.add_argument('--no-map', action='store_true', help='לא להציג מפה')
    parser.add_argument('--output', '-f', help='שם קובץ פלט למפה')
    
    args = parser.parse_args()
    
    # If no arguments provided, run interactive mode
    if not args.dest and not args.points:
        await interactive_mode()
    else:
        # Command line mode
        if not args.dest:
            print("❌ שגיאה: חייב להזין יעד (--dest)")
            parser.print_help()
            return
        
        if not args.points:
            print("❌ שגיאה: חייב להזין נקודות (--points)")
            parser.print_help()
            return
        
        test_points = [p.strip() for p in args.points.split(',') if p.strip()]
        show_map = not args.no_map
        
        result = await test_route(
            args.origin, 
            args.dest, 
            test_points, 
            show_map=show_map,
            output_file=args.output
        )
        
        if result:
            print_header("✅ הבדיקה הושלמה בהצלחה!")

if __name__ == "__main__":
    asyncio.run(main())

