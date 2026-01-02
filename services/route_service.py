"""
Route calculation service using OSRM API
Handles route calculation, geocoding, and distance calculations with dynamic thresholds
"""

import logging
import asyncio
import json
import os
from typing import Optional, Dict, List, Tuple
from functools import lru_cache
import requests
from geopy.distance import distance as geopy_distance

from config import (
    OSRM_API_URL,
    NOMINATIM_API_URL,
    NOMINATIM_USER_AGENT,
    GOOGLE_MAPS_API_KEY,
    ROUTE_PROXIMITY_MIN_THRESHOLD_KM,
    ROUTE_PROXIMITY_MAX_THRESHOLD_KM,
    ROUTE_PROXIMITY_SCALE_FACTOR,
    ROUTE_CALC_MAX_RETRIES,
    ROUTE_CALC_RETRY_DELAY,
    API_TIMEOUT_SECONDS
)

logger = logging.getLogger(__name__)

# Global task tracker to prevent race conditions
_active_route_tasks = {}  # {ride_id: task}

# Load Israeli settlements database from GeoJSON
_SETTLEMENTS_DB = None

def _load_settlements_database():
    """
    Load settlements from city.geojson file
    Returns a dictionary mapping settlement names (Hebrew and English) to coordinates
    """
    global _SETTLEMENTS_DB
    
    if _SETTLEMENTS_DB is not None:
        return _SETTLEMENTS_DB
    
    _SETTLEMENTS_DB = {}
    
    try:
        # Get path to city.geojson (in data directory)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        geojson_path = os.path.join(project_root, 'data', 'city.geojson')
        
        if not os.path.exists(geojson_path):
            logger.warning(f"⚠️ city.geojson not found at {geojson_path}")
            return _SETTLEMENTS_DB
        
        with open(geojson_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Parse GeoJSON features
        for feature in data.get('features', []):
            props = feature.get('properties', {})
            geom = feature.get('geometry', {})
            coords = geom.get('coordinates', [])
            
            if len(coords) != 2:
                continue
            
            # GeoJSON format is [longitude, latitude]
            lon, lat = coords
            coordinates = (lat, lon)  # We use (lat, lon) format
            
            # Get settlement names
            hebrew_name = props.get('MGLSDE_LOC', '').strip()
            english_name = props.get('MGLSDE_L_4', '').strip()
            
            # Add to database with multiple lookup keys
            if hebrew_name:
                # Original name
                _SETTLEMENTS_DB[hebrew_name.lower()] = coordinates
                
                # Without prefixes
                for prefix in ['קיבוץ ', 'מושב ', 'כפר ', 'נוה ']:
                    if hebrew_name.startswith(prefix):
                        name_without_prefix = hebrew_name[len(prefix):].strip()
                        _SETTLEMENTS_DB[name_without_prefix.lower()] = coordinates
            
            if english_name:
                _SETTLEMENTS_DB[english_name.lower()] = coordinates
        
        logger.info(f"✅ Loaded {len(_SETTLEMENTS_DB)} settlement names from GeoJSON")
        
    except Exception as e:
        logger.error(f"❌ Error loading settlements database: {e}")
    
    return _SETTLEMENTS_DB


def calculate_dynamic_threshold(distance_from_origin_km: float) -> float:
    """
    Calculate dynamic threshold based on distance from origin
    
    Formula: min(MIN + distance_from_origin/SCALE_FACTOR, MAX)
    
    Logic: Closer to origin = smaller threshold (more strict)
           Farther from origin = larger threshold (more lenient)
    
    Args:
        distance_from_origin_km: Distance from origin point to test point in kilometers
        
    Returns:
        Threshold in kilometers (between MIN and MAX)
    
    Examples (with MIN=0.5, MAX=5.0, SCALE=10.0):
        0 km from origin → 0.5 km threshold (minimum)
        5 km from origin → 1.0 km threshold
        25 km from origin → 3.0 km threshold
        45 km from origin → 5.0 km threshold (maximum)
        80 km from origin → 5.0 km threshold (maximum, capped)
    """
    threshold = ROUTE_PROXIMITY_MIN_THRESHOLD_KM + (distance_from_origin_km / ROUTE_PROXIMITY_SCALE_FACTOR)
    return min(threshold, ROUTE_PROXIMITY_MAX_THRESHOLD_KM)


def _geocode_with_google(address: str) -> Optional[Tuple[float, float]]:
    """
    Geocode using Google Maps API (most accurate for Israel)
    
    Args:
        address: Address string
        
    Returns:
        (latitude, longitude) or None if failed
    """
    if not GOOGLE_MAPS_API_KEY:
        return None
        
    try:
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            'address': f"{address}, Israel",
            'key': GOOGLE_MAPS_API_KEY,
            'region': 'il',  # Bias results to Israel
            'language': 'iw'  # Hebrew
        }
        
        response = requests.get(url, params=params, timeout=API_TIMEOUT_SECONDS)
        response.raise_for_status()
        
        data = response.json()
        
        if data['status'] == 'OK' and data['results']:
            location = data['results'][0]['geometry']['location']
            coords = (location['lat'], location['lng'])
            logger.info(f"✅ Geocoded '{address}' from Google Maps → ({coords[0]:.4f}, {coords[1]:.4f})")
            return coords
        else:
            logger.warning(f"⚠️ Google geocoding failed for '{address}': {data.get('status')}")
            return None
            
    except Exception as e:
        logger.warning(f"⚠️ Google geocoding error for '{address}': {e}")
        return None


def _geocode_with_nominatim(address: str) -> Optional[Tuple[float, float]]:
    """
    Geocode using Nominatim (OpenStreetMap) - free but less accurate
    
    Args:
        address: Address string
        
    Returns:
        (latitude, longitude) or None if failed
    """
    try:
        params = {
            'q': f"{address}, Israel",
            'format': 'json',
            'limit': 1,
            'countrycodes': 'il',  # Limit to Israel
            'addressdetails': 1
        }
        headers = {
            'User-Agent': NOMINATIM_USER_AGENT
        }
        
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
        
        logger.info(f"✅ Geocoded '{address}' from Nominatim → ({lat:.4f}, {lon:.4f})")
        return (lat, lon)
        
    except Exception as e:
        logger.warning(f"⚠️ Nominatim geocoding error for '{address}': {e}")
        return None


@lru_cache(maxsize=200)
def geocode_address(address: str) -> Optional[Tuple[float, float]]:
    """
    Convert address to coordinates using multiple geocoding services
    
    Strategy:
    1. Try local Israeli settlements database (city.geojson) - fastest and most accurate
    2. Try Google Maps API (if API key is configured)
    3. Fallback to Nominatim (free but less accurate)
    
    Args:
        address: Address string (e.g., "גברעם", "אשקלון", "קיבוץ ניר עם")
        
    Returns:
        (latitude, longitude) or None if all services failed
    """
    try:
        # Try local database first (fast and accurate for Israeli settlements)
        settlements_db = _load_settlements_database()
        normalized = address.strip().lower()
        
        if normalized in settlements_db:
            coords = settlements_db[normalized]
            logger.info(f"✅ Geocoded '{address}' from local DB → ({coords[0]:.4f}, {coords[1]:.4f})")
            return coords
        
        # Try without common prefixes
        for prefix in ['קיבוץ ', 'מושב ', 'כפר ', 'נוה ', 'מעלה ', 'גבעת ']:
            if normalized.startswith(prefix):
                name_without_prefix = normalized[len(prefix):].strip()
                if name_without_prefix in settlements_db:
                    coords = settlements_db[name_without_prefix]
                    logger.info(f"✅ Geocoded '{address}' from local DB → ({coords[0]:.4f}, {coords[1]:.4f})")
                    return coords
        
        # Try Google Maps if API key is configured
        if GOOGLE_MAPS_API_KEY:
            coords = _geocode_with_google(address)
            if coords:
                return coords
            logger.info(f"🔄 Google failed for '{address}', trying Nominatim...")
        
        # Fallback to Nominatim
        coords = _geocode_with_nominatim(address)
        if coords:
            return coords
        
        logger.error(f"❌ All geocoding services failed for '{address}'")
        return None
        
    except Exception as e:
        logger.error(f"❌ Geocoding error for '{address}': {e}")
        return None


def calculate_distance_between_points(
    point1: Tuple[float, float],
    point2: Tuple[float, float]
) -> float:
    """
    Calculate Haversine distance between two geographic points
    
    Args:
        point1: (lat, lon) of first point
        point2: (lat, lon) of second point
        
    Returns:
        Distance in kilometers
    """
    return geopy_distance(point1, point2).kilometers


def calculate_min_distance_to_route(
    route_coords: List[Tuple[float, float]], 
    location_coords: Tuple[float, float]
) -> float:
    """
    Calculate minimum Haversine distance from location to any point on route
    
    Args:
        route_coords: List of (lat, lon) tuples representing the route
        location_coords: (lat, lon) of the location to check
        
    Returns:
        Minimum distance in kilometers
    """
    if not route_coords:
        return float('inf')
    
    min_dist = float('inf')
    
    for route_point in route_coords:
        dist = geopy_distance(location_coords, route_point).kilometers
        min_dist = min(min_dist, dist)
    
    return min_dist


def _parse_osrm_geometry(geometry: Dict, target_resolution_km: float = 1.0) -> List[Tuple[float, float]]:
    """
    Parse OSRM geometry and sample points at ~1km intervals
    
    Args:
        geometry: OSRM geometry object (polyline or coordinates)
        target_resolution_km: Target distance between points
        
    Returns:
        List of (lat, lon) tuples
    """
    coordinates = []
    
    if 'coordinates' in geometry:
        # GeoJSON format: [lon, lat]
        raw_coords = geometry['coordinates']
        
        # Sample points at approximately target_resolution_km intervals
        if not raw_coords:
            return []
        
        # Always include first point
        coordinates.append((raw_coords[0][1], raw_coords[0][0]))  # Convert to (lat, lon)
        
        last_included = (raw_coords[0][1], raw_coords[0][0])
        
        for coord in raw_coords[1:]:
            current = (coord[1], coord[0])  # Convert to (lat, lon)
            dist = geopy_distance(last_included, current).kilometers
            
            if dist >= target_resolution_km:
                coordinates.append(current)
                last_included = current
        
        # Always include last point if not already included
        if coordinates[-1] != (raw_coords[-1][1], raw_coords[-1][0]):
            coordinates.append((raw_coords[-1][1], raw_coords[-1][0]))
    
    return coordinates


def _calculate_route_length(coordinates: List[Tuple[float, float]]) -> float:
    """
    Calculate total route length from coordinates
    
    Args:
        coordinates: List of (lat, lon) tuples
        
    Returns:
        Total distance in kilometers
    """
    if len(coordinates) < 2:
        return 0.0
    
    total = 0.0
    for i in range(len(coordinates) - 1):
        total += geopy_distance(coordinates[i], coordinates[i + 1]).kilometers
    
    return total


async def get_route_data(origin: str, destination: str) -> Optional[Dict]:
    """
    Get complete route data: coordinates, distance, and dynamic threshold
    
    Args:
        origin: Origin address
        destination: Destination address
        
    Returns:
        {
            "coordinates": [(lat, lon), ...],
            "distance_km": float,
            "threshold_km": float
        }
        or None if failed
    """
    try:
        # 1. Geocode addresses
        origin_coords = geocode_address(origin)
        dest_coords = geocode_address(destination)
        
        if not origin_coords or not dest_coords:
            logger.error(f"❌ Failed to geocode: {origin} → {destination}")
            return None
        
        # 2. Query OSRM for route
        # Format: /route/v1/driving/{lon},{lat};{lon},{lat}
        url = f"{OSRM_API_URL}/route/v1/driving/{origin_coords[1]},{origin_coords[0]};{dest_coords[1]},{dest_coords[0]}"
        params = {
            'overview': 'full',
            'geometries': 'geojson'
        }
        
        logger.info(f"🔍 Querying OSRM: {origin} → {destination}")
        
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: requests.get(url, params=params, timeout=API_TIMEOUT_SECONDS)
        )
        response.raise_for_status()
        
        data = response.json()
        
        if data.get('code') != 'Ok' or not data.get('routes'):
            logger.error(f"❌ OSRM returned no route: {data.get('code')}")
            return None
        
        route = data['routes'][0]
        geometry = route['geometry']
        
        # 3. Parse coordinates (~1km resolution)
        coordinates = _parse_osrm_geometry(geometry, target_resolution_km=1.0)
        
        if not coordinates:
            logger.error(f"❌ Failed to parse route geometry")
            return None
        
        # 4. Calculate total distance
        distance_km = _calculate_route_length(coordinates)
        
        # 5. Note: Threshold is now calculated dynamically per test point based on distance from origin
        # We keep threshold_km for backward compatibility but it's not used in matching
        threshold_km = None  # Deprecated: calculated dynamically now
        
        logger.info(f"✅ Route calculated: {distance_km:.1f}km, {len(coordinates)} points")
        
        return {
            "coordinates": coordinates,
            "distance_km": distance_km,
            "threshold_km": threshold_km  # Deprecated field, kept for compatibility
        }
        
    except Exception as e:
        logger.error(f"❌ Error calculating route {origin} → {destination}: {e}")
        return None


async def calculate_and_save_route_background(
    phone_number: str,
    ride_id: str,
    origin: str,
    destination: str,
    max_retries: int = None
):
    """
    Calculate route in background with retry logic (fire-and-forget)
    
    This function runs asynchronously without blocking user response.
    It will retry on failure and gracefully handle cancellation.
    
    Args:
        phone_number: User's phone number
        ride_id: Ride ID
        origin: Origin address
        destination: Destination address
        max_retries: Maximum number of retry attempts (defaults to config)
    """
    if max_retries is None:
        max_retries = ROUTE_CALC_MAX_RETRIES
    
    # Cancel old task if exists (user updated quickly)
    if ride_id in _active_route_tasks:
        old_task = _active_route_tasks[ride_id]
        if not old_task.done():
            old_task.cancel()
            logger.info(f"🚫 Cancelled old route calculation for {ride_id}")
    
    # Register current task
    task = asyncio.current_task()
    _active_route_tasks[ride_id] = task
    
    try:
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"🔄 Background route calc (attempt {attempt}/{max_retries}): {origin} → {destination}")
                
                # Calculate route
                route_data = await get_route_data(origin, destination)
                
                if not route_data:
                    raise Exception("Failed to get route data")
                
                # Save to DB
                from database import update_ride_route_data
                success = await update_ride_route_data(
                    phone_number,
                    ride_id,
                    route_data
                )
                
                if success:
                    logger.info(f"✅ Route saved in background for {ride_id}: {route_data['distance_km']:.1f}km")
                    return  # Success!
                else:
                    raise Exception("Failed to save route to DB")
                    
            except asyncio.CancelledError:
                logger.info(f"🚫 Route calculation cancelled for {ride_id}")
                raise  # Don't retry if cancelled
                
            except Exception as e:
                logger.warning(f"⚠️ Background route calc failed (attempt {attempt}/{max_retries}): {e}")
                
                if attempt < max_retries:
                    await asyncio.sleep(ROUTE_CALC_RETRY_DELAY)
                else:
                    logger.error(f"❌ All retry attempts failed for {ride_id}. Will use lazy loading.")
    
    finally:
        # Cleanup
        _active_route_tasks.pop(ride_id, None)

