import { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// Fix for default marker icons in Leaflet with Vite
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

// Calculate dynamic threshold based on distance from origin
function calculateDynamicThreshold(distanceFromOriginKm, minThreshold, maxThreshold, scaleFactor) {
  return Math.min(minThreshold + distanceFromOriginKm / scaleFactor, maxThreshold);
}

// Calculate distance between two points using Haversine formula
function calculateDistance(lat1, lon1, lat2, lon2) {
  const R = 6371; // Earth's radius in km
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLon = (lon2 - lon1) * Math.PI / 180;
  const a = 
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
    Math.sin(dLon / 2) * Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

// Create dynamic buffer around route
function createDynamicBuffer(coords, minThreshold, maxThreshold, scaleFactor) {
  if (coords.length < 2) return [];
  
  const bufferLeft = [];
  const bufferRight = [];
  
  for (let i = 0; i < coords.length; i++) {
    const [lat, lon] = coords[i];
    
    // Calculate distance from origin along route
    let distFromOrigin = 0;
    for (let j = 1; j <= i; j++) {
      distFromOrigin += calculateDistance(
        coords[j-1][0], coords[j-1][1],
        coords[j][0], coords[j][1]
      );
    }
    
    // Get dynamic threshold for this point
    const thresholdKm = calculateDynamicThreshold(distFromOrigin, minThreshold, maxThreshold, scaleFactor);
    
    // Calculate bearing (direction) of the route at this point
    let bearing = 0;
    
    if (i === 0 && coords.length > 1) {
      // First point - use direction to next point
      bearing = calculateBearing(lat, lon, coords[1][0], coords[1][1]);
    } else if (i === coords.length - 1) {
      // Last point - use direction from previous point
      bearing = calculateBearing(coords[i-1][0], coords[i-1][1], lat, lon);
    } else {
      // Middle points - average of incoming and outgoing directions
      const bearingIn = calculateBearing(coords[i-1][0], coords[i-1][1], lat, lon);
      const bearingOut = calculateBearing(lat, lon, coords[i+1][0], coords[i+1][1]);
      bearing = (bearingIn + bearingOut) / 2;
    }
    
    // Calculate offset distance in degrees (more accurate for latitude)
    const latOffsetDegrees = thresholdKm / 111.0; // 1 degree latitude ≈ 111 km
    const lonOffsetDegrees = thresholdKm / (111.0 * Math.cos(lat * Math.PI / 180)); // Adjust for latitude
    
    // Calculate perpendicular bearings (left and right)
    const leftBearing = bearing - Math.PI / 2;
    const rightBearing = bearing + Math.PI / 2;
    
    // Calculate offset points
    const leftLat = lat + latOffsetDegrees * Math.sin(leftBearing);
    const leftLon = lon + lonOffsetDegrees * Math.cos(leftBearing);
    bufferLeft.push([leftLat, leftLon]);
    
    const rightLat = lat + latOffsetDegrees * Math.sin(rightBearing);
    const rightLon = lon + lonOffsetDegrees * Math.cos(rightBearing);
    bufferRight.push([rightLat, rightLon]);
  }
  
  // Combine left and right to create closed polygon
  return [...bufferLeft, ...bufferRight.reverse()];
}

// Calculate bearing between two points
function calculateBearing(lat1, lon1, lat2, lon2) {
  const dLon = (lon2 - lon1) * Math.PI / 180;
  const lat1Rad = lat1 * Math.PI / 180;
  const lat2Rad = lat2 * Math.PI / 180;
  
  const y = Math.sin(dLon) * Math.cos(lat2Rad);
  const x = Math.cos(lat1Rad) * Math.sin(lat2Rad) -
            Math.sin(lat1Rad) * Math.cos(lat2Rad) * Math.cos(dLon);
  
  return Math.atan2(y, x);
}

function RideMapModal({ ride, matchingParams, onClose }) {
  const mapRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const [mapError, setMapError] = useState(false);

  // Default values if params not provided (fallback)
  const minThreshold = matchingParams?.min_threshold_km || 0.5;
  const maxThreshold = matchingParams?.max_threshold_km || 10.0;
  const scaleFactor = matchingParams?.scale_factor || 5.0;

  // Debug: Log ride data
  useEffect(() => {
    console.log('🗺️ RideMapModal - ride data:', ride);
    console.log('📍 route_coordinates:', ride.route_coordinates);
    console.log('🎯 matching params:', matchingParams);
  }, [ride, matchingParams]);

  useEffect(() => {
    const handleEsc = (e) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleEsc);
    return () => window.removeEventListener('keydown', handleEsc);
  }, [onClose]);

  // Initialize map
  useEffect(() => {
    if (!mapRef.current || mapInstanceRef.current) return;
    
    const hasRouteData = ride.route_coordinates && ride.route_coordinates.length > 0;
    console.log('🔍 hasRouteData:', hasRouteData, 'length:', ride.route_coordinates?.length);
    if (!hasRouteData) {
      setMapError(true);
      return;
    }

    try {
      // Parse coordinates (they come as flat array: [lat1, lon1, lat2, lon2, ...])
      const coords = [];
      for (let i = 0; i < ride.route_coordinates.length; i += 2) {
        const lat = ride.route_coordinates[i];
        const lon = ride.route_coordinates[i + 1];
        if (lat && lon) {
          coords.push([lat, lon]);
        }
      }

      if (coords.length === 0) {
        setMapError(true);
        return;
      }

      // Create map
      const map = L.map(mapRef.current, {
        scrollWheelZoom: false,
      });
      mapInstanceRef.current = map;

      // Add tile layer
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
        maxZoom: 19,
      }).addTo(map);

      // Add route line
      const routeLine = L.polyline(coords, {
        color: '#3B82F6',
        weight: 4,
        opacity: 0.8,
      }).addTo(map);

      // Add start marker
      const startIcon = L.divIcon({
        className: 'custom-div-icon',
        html: "<div style='background-color:#22C55E;width:30px;height:30px;border-radius:50%;display:flex;align-items:center;justify-content:center;color:white;font-weight:bold;border:3px solid white;box-shadow:0 2px 8px rgba(0,0,0,0.3);'>🚗</div>",
        iconSize: [30, 30],
        iconAnchor: [15, 15],
      });
      L.marker(coords[0], { icon: startIcon })
        .bindPopup(`<b>נקודת התחלה</b><br>${ride.origin || 'לא ידוע'}`)
        .addTo(map);

      // Add end marker
      const endIcon = L.divIcon({
        className: 'custom-div-icon',
        html: "<div style='background-color:#EF4444;width:30px;height:30px;border-radius:50%;display:flex;align-items:center;justify-content:center;color:white;font-weight:bold;border:3px solid white;box-shadow:0 2px 8px rgba(0,0,0,0.3);'>📍</div>",
        iconSize: [30, 30],
        iconAnchor: [15, 15],
      });
      L.marker(coords[coords.length - 1], { icon: endIcon })
        .bindPopup(`<b>יעד</b><br>${ride.destination || 'לא ידוע'}`)
        .addTo(map);

      // Add dynamic matching zone as circles along route
      // Calculate accumulated distance for each point
      const distances = [0];
      for (let i = 1; i < coords.length; i++) {
        const dist = distances[i-1] + calculateDistance(
          coords[i-1][0], coords[i-1][1],
          coords[i][0], coords[i][1]
        );
        distances.push(dist);
      }
      
      // Draw circles at regular intervals
      const stepKm = 0.5; // Draw circle every 0.5 km
      const drawnCircles = [];
      
      for (let targetDist = 0; targetDist <= distances[distances.length - 1]; targetDist += stepKm) {
        // Find the segment containing this distance
        let segmentIdx = 0;
        for (let i = 1; i < distances.length; i++) {
          if (distances[i] >= targetDist) {
            segmentIdx = i;
            break;
          }
        }
        
        if (segmentIdx === 0) segmentIdx = 1;
        
        // Interpolate position
        const segStart = distances[segmentIdx - 1];
        const segEnd = distances[segmentIdx];
        const ratio = (targetDist - segStart) / (segEnd - segStart);
        
        const lat = coords[segmentIdx - 1][0] + ratio * (coords[segmentIdx][0] - coords[segmentIdx - 1][0]);
        const lon = coords[segmentIdx - 1][1] + ratio * (coords[segmentIdx][1] - coords[segmentIdx - 1][1]);
        
        // Calculate dynamic threshold at this distance
        const thresholdKm = calculateDynamicThreshold(targetDist, minThreshold, maxThreshold, scaleFactor);
        
        // Draw circle
        L.circle([lat, lon], {
          radius: thresholdKm * 1000, // Convert to meters
          color: '#34D399',
          fillColor: '#34D399',
          fillOpacity: 0.04,  // Very transparent
          weight: 0,
          opacity: 0,
        }).addTo(map);
      }
      
      if (true) {
        // Add legend
        const legend = L.control({ position: 'bottomright' });
        legend.onAdd = function() {
          const div = L.DomUtil.create('div', 'info legend');
          div.style.background = 'white';
          div.style.padding = '10px';
          div.style.borderRadius = '8px';
          div.style.boxShadow = '0 2px 8px rgba(0,0,0,0.15)';
          div.innerHTML = `
            <div style="font-size:12px;font-weight:bold;margin-bottom:5px;color:#10B981;">🎯 אזור התאמה דינמי</div>
            <div style="font-size:11px;color:#666;line-height:1.4;">
              <div>התחלה: ${minThreshold.toFixed(1)} ק"מ</div>
              <div>סוף: עד ${maxThreshold.toFixed(1)} ק"מ</div>
              <div style="margin-top:4px;padding-top:4px;border-top:1px solid #e5e7eb;">
                <span style="color:#059669;">▬▬▬</span> אזור פיקאפ
              </div>
            </div>
          `;
          return div;
        };
        legend.addTo(map);
      }

      // Fit bounds to show entire route
      map.fitBounds(routeLine.getBounds(), { padding: [50, 50] });

    } catch (error) {
      console.error('Error creating map:', error);
      setMapError(true);
    }

    // Cleanup
    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, [ride]);

  const hasRouteData = ride.route_coordinates && ride.route_coordinates.length > 0;
  const mapUrl = hasRouteData 
    ? `https://www.google.com/maps/dir/${ride.origin}/${ride.destination}`
    : `https://www.google.com/maps/search/${ride.destination}`;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div 
        className="bg-white rounded-lg shadow-xl max-w-5xl w-full max-h-[90vh] overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="bg-primary text-white p-6 flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold">🗺️ מסלול נסיעה</h2>
            <p className="text-blue-100 mt-1">{ride.origin} ← {ride.destination}</p>
          </div>
          <button
            onClick={onClose}
            className="text-white hover:bg-blue-600 rounded-full p-2 transition-colors"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Ride Info */}
        <div className="p-6 bg-gray-50 border-b">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <p className="text-sm text-gray-600 mb-1">נהג/טרמפיסט</p>
              <p className="font-semibold">{ride.name || 'לא ידוע'}</p>
            </div>
            <div>
              <p className="text-sm text-gray-600 mb-1">טלפון</p>
              <p className="font-mono text-sm">{ride.phone_number}</p>
            </div>
            <div>
              <p className="text-sm text-gray-600 mb-1">שעת יציאה</p>
              <p className="font-semibold">{ride.departure_time || '-'}</p>
            </div>
            <div>
              <p className="text-sm text-gray-600 mb-1">תאריך</p>
              <p className="font-semibold text-sm">
                {ride.travel_date ? new Date(ride.travel_date).toLocaleDateString('he-IL') : 
                 ride.days?.length > 0 ? ride.days.join(', ') : '-'}
              </p>
            </div>
          </div>

          {ride.route_distance_km && (
            <div className="mt-4 flex items-center gap-4 text-sm">
              <span className="bg-blue-100 text-blue-800 px-3 py-1 rounded-full">
                📏 מרחק: {ride.route_distance_km.toFixed(1)} ק"מ
              </span>
              {ride.route_threshold_km && (
                <span className="bg-green-100 text-green-800 px-3 py-1 rounded-full">
                  🎯 טווח התאמה: {ride.route_threshold_km.toFixed(1)} ק"מ
                </span>
              )}
            </div>
          )}
        </div>

        {/* Map */}
        <div className="p-6">
          {hasRouteData && !mapError ? (
            <div>
              {/* Map Container */}
              <div 
                ref={mapRef} 
                className="w-full h-[500px] rounded-lg shadow-lg border-2 border-gray-200"
                style={{ minHeight: '500px' }}
              />
              
              {/* Map Info */}
              <div className="mt-4 grid grid-cols-3 gap-4 text-center">
                <div className="bg-blue-50 p-3 rounded-lg">
                  <p className="text-xs text-gray-600 mb-1">נקודות במסלול</p>
                  <p className="text-lg font-bold text-blue-700">
                    {Math.floor(ride.route_coordinates?.length / 2) || 0}
                  </p>
                </div>
                <div className="bg-green-50 p-3 rounded-lg">
                  <p className="text-xs text-gray-600 mb-1">מרחק כולל</p>
                  <p className="text-lg font-bold text-green-700">
                    {ride.route_distance_km?.toFixed(1) || 0} ק"מ
                  </p>
                </div>
                <div className="bg-purple-50 p-3 rounded-lg">
                  <p className="text-xs text-gray-600 mb-1">אזור התאמה</p>
                  <p className="text-lg font-bold text-purple-700">
                    ±{ride.route_threshold_km?.toFixed(1) || 0} ק"מ
                  </p>
                </div>
              </div>

              {/* Legend */}
              <div className="mt-4 flex items-center justify-center gap-6 text-sm flex-wrap">
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 bg-green-500 rounded-full border-2 border-white shadow"></div>
                  <span>נקודת התחלה (🚗)</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 bg-blue-500 rounded"></div>
                  <span>מסלול הנסיעה</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 bg-green-500 opacity-30 rounded"></div>
                  <span>אזור פיקאפ 🎯</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 bg-red-500 rounded-full border-2 border-white shadow"></div>
                  <span>יעד (📍)</span>
                </div>
              </div>

              {/* Google Maps Link */}
              <div className="mt-4 text-center">
                <a
                  href={mapUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-block text-blue-600 hover:text-blue-800 underline text-sm"
                >
                  🗺️ פתח ב-Google Maps
                </a>
              </div>
            </div>
          ) : (
            <div className="bg-gray-100 rounded-lg p-8 text-center">
              <div className="text-6xl mb-4">📍</div>
              <h3 className="text-xl font-semibold mb-2">
                {mapError ? 'שגיאה בטעינת המפה' : 'פתח ב-Google Maps'}
              </h3>
              <p className="text-gray-600 mb-4">
                {mapError 
                  ? 'לא ניתן להציג את המפה - הקואורדינטות אינן תקינות'
                  : 'הנסיעה טרם נותחה - אפשר לפתוח ב-Google Maps'
                }
              </p>
              <a
                href={mapUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-block bg-primary text-white px-6 py-3 rounded-lg hover:bg-blue-600 transition-colors font-medium"
              >
                🗺️ פתח ב-Google Maps
              </a>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="bg-gray-50 px-6 py-4 flex justify-end gap-3 border-t">
          <button
            onClick={onClose}
            className="px-6 py-2 bg-gray-200 text-gray-800 rounded-lg hover:bg-gray-300 transition-colors font-medium"
          >
            סגור
          </button>
        </div>
      </div>
    </div>
  );
}

export default RideMapModal;

