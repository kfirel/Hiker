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

function RideMapModal({ ride, onClose }) {
  const mapRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const [mapError, setMapError] = useState(false);

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
    if (!hasRouteData) return;

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

      // Add threshold buffer if available
      if (ride.route_threshold_km) {
        const thresholdMeters = ride.route_threshold_km * 1000;
        const buffer = L.polyline(coords, {
          color: '#10B981',
          weight: thresholdMeters / 50, // Scale weight based on threshold
          opacity: 0.15,
        }).addTo(map);
        
        // Add legend
        const legend = L.control({ position: 'bottomright' });
        legend.onAdd = function() {
          const div = L.DomUtil.create('div', 'info legend');
          div.style.background = 'white';
          div.style.padding = '10px';
          div.style.borderRadius = '8px';
          div.style.boxShadow = '0 2px 8px rgba(0,0,0,0.15)';
          div.innerHTML = `
            <div style="font-size:12px;font-weight:bold;margin-bottom:5px;">אזור התאמה</div>
            <div style="font-size:11px;color:#666;">±${ride.route_threshold_km.toFixed(1)} ק"מ מהמסלול</div>
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
              <div className="mt-4 flex items-center justify-center gap-6 text-sm">
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 bg-green-500 rounded-full border-2 border-white shadow"></div>
                  <span>נקודת התחלה (🚗)</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 bg-blue-500 rounded"></div>
                  <span>מסלול הנסיעה</span>
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

