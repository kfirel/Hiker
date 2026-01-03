import { useEffect } from 'react';

function RideMapModal({ ride, onClose }) {
  useEffect(() => {
    const handleEsc = (e) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleEsc);
    return () => window.removeEventListener('keydown', handleEsc);
  }, [onClose]);

  // For now, showing a placeholder - we'll integrate with actual map data
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
          {hasRouteData ? (
            <div className="bg-gray-100 rounded-lg p-8 text-center">
              <div className="text-6xl mb-4">🗺️</div>
              <h3 className="text-xl font-semibold mb-2">תצוגת מפה מתקדמת</h3>
              <p className="text-gray-600 mb-4">
                הנסיעה כוללת נתוני מסלול מפורטים
              </p>
              <div className="bg-white rounded p-4 text-right space-y-2 text-sm">
                <p><span className="font-semibold">מספר נקודות במסלול:</span> {ride.route_coordinates?.length || 0}</p>
                <p><span className="font-semibold">מרחק כולל:</span> {ride.route_distance_km?.toFixed(1) || 0} ק"מ</p>
                <p><span className="font-semibold">רדיוס התאמה:</span> {ride.route_threshold_km?.toFixed(1) || 0} ק"מ</p>
              </div>
              <p className="text-xs text-gray-500 mt-4">
                💡 בגרסה הבאה תוצג מפה אינטראקטיבית עם המסלול המדויק ואזור ההתאמה
              </p>
            </div>
          ) : (
            <div className="bg-gray-100 rounded-lg p-8 text-center">
              <div className="text-6xl mb-4">📍</div>
              <h3 className="text-xl font-semibold mb-2">פתח ב-Google Maps</h3>
              <p className="text-gray-600 mb-4">
                הנסיעה טרם נותחה - אפשר לפתוח ב-Google Maps
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

