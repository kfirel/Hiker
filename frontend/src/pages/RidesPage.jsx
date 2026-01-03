import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ridesAPI } from '../api/client';
import RideMapModal from '../components/Rides/RideMapModal';

function RidesPage() {
  const [destination, setDestination] = useState('');
  const [selectedRide, setSelectedRide] = useState(null);
  
  // Fetch rides
  const { data, isLoading, refetch } = useQuery({
    queryKey: ['rides', { destination }],
    queryFn: () => ridesAPI.getActive({ destination }).then(res => res.data),
    refetchInterval: 30000,
  });

  const handleExportDrivers = async () => {
    try {
      const response = await ridesAPI.exportCSV('driver');
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'drivers_export.csv');
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (error) {
      alert('שגיאה בייצוא הנתונים');
    }
  };

  const handleExportHitchhikers = async () => {
    try {
      const response = await ridesAPI.exportCSV('hitchhiker');
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'hitchhikers_export.csv');
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (error) {
      alert('שגיאה בייצוא הנתונים');
    }
  };

  const handleCalculateRoutes = async () => {
    if (!confirm('האם לחשב מסלולים לכל הנסיעות? זה עלול לקחת זמן...')) {
      return;
    }
    
    try {
      const response = await ridesAPI.calculateRoutes();
      const result = response.data;
      alert(`✅ הופעלו ${result.calculations_started} חישובי מסלול!\n\nהמסלולים יחושבו ברקע. רענן את הדף בעוד דקה כדי לראות את המפות.`);
      // Refetch data after a delay
      setTimeout(() => refetch(), 60000); // 60 seconds
    } catch (error) {
      alert('שגיאה בהפעלת חישוב המסלולים: ' + (error.response?.data?.detail || error.message));
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-gray-600">טוען נסיעות...</p>
        </div>
      </div>
    );
  }

  const drivers = data?.drivers || [];
  const hitchhikers = data?.hitchhikers || [];
  const matchingParams = data?.matching_params || null;

  return (
    <div className="space-y-6">
      {/* Header with Search */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between gap-4 flex-wrap mb-4">
          <h3 className="text-xl font-bold text-gray-900">🚗 כל הנסיעות הפעילות</h3>
          <div className="flex items-center gap-3">
            <button
              onClick={handleCalculateRoutes}
              className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors text-sm font-medium whitespace-nowrap"
              title="חשב מסלולים לנסיעות ללא נתוני מסלול"
            >
              🗺️ חשב מסלולים
            </button>
            <div className="flex-1 min-w-[200px] max-w-md">
              <input
                type="text"
                placeholder="סינון לפי יעד..."
                value={destination}
                onChange={(e) => setDestination(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"
              />
            </div>
          </div>
        </div>

        <div className="flex items-center gap-4 text-sm text-gray-600">
          <span className="bg-blue-50 px-3 py-1 rounded">
            🚗 {drivers.length} נהגים
          </span>
          <span className="bg-green-50 px-3 py-1 rounded">
            🎒 {hitchhikers.length} טרמפיסטים
          </span>
        </div>
      </div>

      {/* Drivers Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="bg-blue-50 px-6 py-3 border-b flex items-center justify-between">
          <h4 className="font-semibold text-blue-900">🚗 נהגים פעילים</h4>
          <button
            onClick={handleExportDrivers}
            className="text-sm px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
          >
            📊 ייצוא
          </button>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="text-right py-3 px-4 font-semibold text-gray-700">שם</th>
                <th className="text-right py-3 px-4 font-semibold text-gray-700">טלפון</th>
                <th className="text-right py-3 px-4 font-semibold text-gray-700">מ</th>
                <th className="text-right py-3 px-4 font-semibold text-gray-700">אל</th>
                <th className="text-right py-3 px-4 font-semibold text-gray-700">ימים/תאריך</th>
                <th className="text-right py-3 px-4 font-semibold text-gray-700">יציאה</th>
                <th className="text-right py-3 px-4 font-semibold text-gray-700">חזרה</th>
                <th className="text-right py-3 px-4 font-semibold text-gray-700">הערות</th>
                <th className="text-right py-3 px-4 font-semibold text-gray-700">נוצר</th>
              </tr>
            </thead>
            <tbody>
              {drivers.map((ride) => (
                <tr 
                  key={ride.id} 
                  className="border-t hover:bg-blue-50 cursor-pointer transition-colors"
                  onClick={() => setSelectedRide(ride)}
                >
                  <td className="py-3 px-4 font-medium">{ride.name || '-'}</td>
                  <td className="py-3 px-4 font-mono text-sm">{ride.phone_number}</td>
                  <td className="py-3 px-4">{ride.origin}</td>
                  <td className="py-3 px-4 font-medium">{ride.destination}</td>
                  <td className="py-3 px-4 text-sm">
                    {ride.days?.length > 0 ? (
                      <div className="flex flex-wrap gap-1">
                        {ride.days.map(day => (
                          <span key={day} className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs">
                            {day.slice(0, 3)}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <span className="text-gray-600">{ride.travel_date || '-'}</span>
                    )}
                  </td>
                  <td className="py-3 px-4">{ride.departure_time || '-'}</td>
                  <td className="py-3 px-4">{ride.return_time || '-'}</td>
                  <td className="py-3 px-4 text-sm text-gray-600 max-w-[200px] truncate">
                    {ride.notes || '-'}
                  </td>
                  <td className="py-3 px-4 text-sm text-gray-600">
                    {ride.created_at ? new Date(ride.created_at).toLocaleDateString('he-IL') : '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          
          {drivers.length === 0 && (
            <div className="text-center py-12 text-gray-500">
              {destination ? 'לא נמצאו נהגים תואמים' : 'אין נהגים פעילים'}
            </div>
          )}
        </div>
      </div>

      {/* Hitchhikers Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="bg-green-50 px-6 py-3 border-b flex items-center justify-between">
          <h4 className="font-semibold text-green-900">🎒 טרמפיסטים פעילים</h4>
          <button
            onClick={handleExportHitchhikers}
            className="text-sm px-3 py-1 bg-green-600 text-white rounded hover:bg-green-700 transition-colors"
          >
            📊 ייצוא
          </button>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="text-right py-3 px-4 font-semibold text-gray-700">שם</th>
                <th className="text-right py-3 px-4 font-semibold text-gray-700">טלפון</th>
                <th className="text-right py-3 px-4 font-semibold text-gray-700">מ</th>
                <th className="text-right py-3 px-4 font-semibold text-gray-700">אל</th>
                <th className="text-right py-3 px-4 font-semibold text-gray-700">תאריך</th>
                <th className="text-right py-3 px-4 font-semibold text-gray-700">שעה</th>
                <th className="text-right py-3 px-4 font-semibold text-gray-700">גמישות</th>
                <th className="text-right py-3 px-4 font-semibold text-gray-700">הערות</th>
                <th className="text-right py-3 px-4 font-semibold text-gray-700">נוצר</th>
              </tr>
            </thead>
            <tbody>
              {hitchhikers.map((ride) => (
                <tr 
                  key={ride.id} 
                  className="border-t hover:bg-green-50 cursor-pointer transition-colors"
                  onClick={() => setSelectedRide(ride)}
                >
                  <td className="py-3 px-4 font-medium">{ride.name || '-'}</td>
                  <td className="py-3 px-4 font-mono text-sm">{ride.phone_number}</td>
                  <td className="py-3 px-4">{ride.origin}</td>
                  <td className="py-3 px-4 font-medium">{ride.destination}</td>
                  <td className="py-3 px-4 text-sm">
                    {ride.travel_date ? new Date(ride.travel_date).toLocaleDateString('he-IL') : '-'}
                  </td>
                  <td className="py-3 px-4">{ride.departure_time || '-'}</td>
                  <td className="py-3 px-4">
                    <span className={`px-2 py-1 rounded text-xs font-semibold ${
                      ride.flexibility === 'flexible' 
                        ? 'bg-green-100 text-green-700' 
                        : 'bg-orange-100 text-orange-700'
                    }`}>
                      {ride.flexibility === 'flexible' ? 'גמיש' : 'מדויק'}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-sm text-gray-600 max-w-[200px] truncate">
                    {ride.notes || '-'}
                  </td>
                  <td className="py-3 px-4 text-sm text-gray-600">
                    {ride.created_at ? new Date(ride.created_at).toLocaleDateString('he-IL') : '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          
          {hitchhikers.length === 0 && (
            <div className="text-center py-12 text-gray-500">
              {destination ? 'לא נמצאו טרמפיסטים תואמים' : 'אין טרמפיסטים פעילים'}
            </div>
          )}
        </div>
      </div>

      {/* Ride Map Modal */}
      {selectedRide && (
        <RideMapModal
          ride={selectedRide}
          matchingParams={matchingParams}
          onClose={() => setSelectedRide(null)}
        />
      )}
    </div>
  );
}

export default RidesPage;

