import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ridesAPI } from '../api/client';

function RidesPage() {
  const [activeTab, setActiveTab] = useState('driver');
  const [destination, setDestination] = useState('');
  
  // Fetch rides
  const { data, isLoading, refetch } = useQuery({
    queryKey: ['rides', { destination }],
    queryFn: () => ridesAPI.getActive({ destination }).then(res => res.data),
    refetchInterval: 30000,
  });

  const handleExport = async () => {
    try {
      const response = await ridesAPI.exportCSV(activeTab === 'driver' ? 'driver' : 'hitchhiker');
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${activeTab}_rides_export.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (error) {
      alert('שגיאה בייצוא הנתונים');
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
  const currentData = activeTab === 'driver' ? drivers : hitchhikers;

  return (
    <div className="space-y-6">
      {/* Header with Tabs */}
      <div className="bg-white rounded-lg shadow">
        <div className="border-b border-gray-200">
          <div className="flex gap-1 p-1">
            <button
              onClick={() => setActiveTab('driver')}
              className={`flex-1 px-4 py-3 rounded-lg font-medium transition-colors ${
                activeTab === 'driver'
                  ? 'bg-primary text-white'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              🚗 נהגים ({drivers.length})
            </button>
            <button
              onClick={() => setActiveTab('hitchhiker')}
              className={`flex-1 px-4 py-3 rounded-lg font-medium transition-colors ${
                activeTab === 'hitchhiker'
                  ? 'bg-primary text-white'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              🎒 טרמפיסטים ({hitchhikers.length})
            </button>
          </div>
        </div>
        
        <div className="p-6">
          <div className="flex items-center justify-between gap-4 flex-wrap">
            <div className="flex-1 min-w-[200px]">
              <input
                type="text"
                placeholder="סינון לפי יעד..."
                value={destination}
                onChange={(e) => setDestination(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"
              />
            </div>
            
            <button
              onClick={handleExport}
              className="px-4 py-2 bg-success text-white rounded-lg hover:bg-green-600 transition-colors"
            >
              📊 ייצוא CSV
            </button>
          </div>
        </div>
      </div>

      {/* Rides Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="text-right py-3 px-4 font-semibold text-gray-700">שם</th>
                <th className="text-right py-3 px-4 font-semibold text-gray-700">טלפון</th>
                <th className="text-right py-3 px-4 font-semibold text-gray-700">מ</th>
                <th className="text-right py-3 px-4 font-semibold text-gray-700">אל</th>
                {activeTab === 'driver' ? (
                  <>
                    <th className="text-right py-3 px-4 font-semibold text-gray-700">ימים</th>
                    <th className="text-right py-3 px-4 font-semibold text-gray-700">יציאה</th>
                    <th className="text-right py-3 px-4 font-semibold text-gray-700">חזרה</th>
                  </>
                ) : (
                  <>
                    <th className="text-right py-3 px-4 font-semibold text-gray-700">תאריך</th>
                    <th className="text-right py-3 px-4 font-semibold text-gray-700">שעה</th>
                    <th className="text-right py-3 px-4 font-semibold text-gray-700">גמישות</th>
                  </>
                )}
                <th className="text-right py-3 px-4 font-semibold text-gray-700">הערות</th>
                <th className="text-right py-3 px-4 font-semibold text-gray-700">נוצר</th>
              </tr>
            </thead>
            <tbody>
              {currentData.map((ride) => (
                <tr key={ride.id} className="border-t hover:bg-gray-50">
                  <td className="py-3 px-4 font-medium">{ride.name || '-'}</td>
                  <td className="py-3 px-4 font-mono text-sm">{ride.phone_number}</td>
                  <td className="py-3 px-4">{ride.origin}</td>
                  <td className="py-3 px-4 font-medium">{ride.destination}</td>
                  {activeTab === 'driver' ? (
                    <>
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
                          <span className="text-gray-500">{ride.travel_date || '-'}</span>
                        )}
                      </td>
                      <td className="py-3 px-4">{ride.departure_time || '-'}</td>
                      <td className="py-3 px-4">{ride.return_time || '-'}</td>
                    </>
                  ) : (
                    <>
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
                    </>
                  )}
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
          
          {currentData.length === 0 && (
            <div className="text-center py-12 text-gray-500">
              {destination ? 'לא נמצאו נסיעות תואמות' : `אין ${activeTab === 'driver' ? 'נהגים' : 'טרמפיסטים'} פעילים`}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default RidesPage;

