import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ridesAPI } from '../api/client';
import RideMapModal from '../components/Rides/RideMapModal';

function RidesPage() {
  const [destination, setDestination] = useState('');
  const [selectedRide, setSelectedRide] = useState(null);
  const [editingRide, setEditingRide] = useState(null);
  const [editingType, setEditingType] = useState(null);
  const [editForm, setEditForm] = useState({});
  const [isSaving, setIsSaving] = useState(false);
  
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

  const openEditModal = (ride, type) => {
    setEditingRide(ride);
    setEditingType(type);
    setEditForm({
      origin: ride.origin || '',
      destination: ride.destination || '',
      travel_date: ride.travel_date || '',
      departure_time: ride.departure_time || '',
      return_time: ride.return_time || '',
      days_text: Array.isArray(ride.days) ? ride.days.join(', ') : '',
      notes: ride.notes || '',
      flexibility: ride.flexibility || 'flexible',
    });
  };

  const closeEditModal = () => {
    setEditingRide(null);
    setEditingType(null);
    setEditForm({});
  };

  const handleEditSave = async () => {
    if (!editingRide || !editingType) {
      return;
    }

    const updates = {};
    const originalDays = Array.isArray(editingRide.days) ? editingRide.days.join(', ') : '';

    if (editForm.origin !== (editingRide.origin || '')) {
      updates.origin = editForm.origin;
    }
    if (editForm.destination !== (editingRide.destination || '')) {
      updates.destination = editForm.destination;
    }
    if (editForm.travel_date !== (editingRide.travel_date || '')) {
      updates.travel_date = editForm.travel_date || null;
    }
    if (editForm.departure_time !== (editingRide.departure_time || '')) {
      updates.departure_time = editForm.departure_time || null;
    }
    if (editForm.return_time !== (editingRide.return_time || '')) {
      updates.return_time = editForm.return_time || null;
    }
    if (editForm.notes !== (editingRide.notes || '')) {
      updates.notes = editForm.notes || null;
    }

    if (editingType === 'driver') {
      if (editForm.days_text !== originalDays) {
        const days = editForm.days_text
          .split(',')
          .map((day) => day.trim())
          .filter(Boolean);
        updates.days = days.length > 0 ? days : null;
      }
    } else {
      if (editForm.flexibility !== (editingRide.flexibility || 'flexible')) {
        updates.flexibility = editForm.flexibility;
      }
    }

    if (Object.keys(updates).length === 0) {
      closeEditModal();
      return;
    }

    setIsSaving(true);
    try {
      await ridesAPI.update(editingRide.phone_number, editingRide.id, editingType, updates);
      await refetch();
      closeEditModal();
      alert('הנסיעה עודכנה בהצלחה');
    } catch (error) {
      alert('שגיאה בעדכון הנסיעה: ' + (error.response?.data?.detail || error.message));
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header with Search */}
      <div className="bg-white rounded-lg shadow p-4 sm:p-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-4">
          <h3 className="text-xl font-bold text-gray-900">🚗 כל הנסיעות הפעילות</h3>
          <div className="flex flex-col sm:flex-row items-stretch gap-3 w-full sm:w-auto">
            <button
              onClick={handleCalculateRoutes}
              className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors text-sm font-medium whitespace-nowrap w-full sm:w-auto"
              title="חשב מסלולים לנסיעות ללא נתוני מסלול"
            >
              🗺️ חשב מסלולים
            </button>
            <div className="flex-1 min-w-0 sm:min-w-[200px] sm:max-w-md">
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

        <div className="flex flex-wrap items-center gap-2 text-sm text-gray-600">
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
                <th className="text-right py-3 px-4 font-semibold text-gray-700">פעולות</th>
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
                  <td className="py-3 px-4" onClick={(e) => e.stopPropagation()}>
                    <button
                      onClick={() => openEditModal(ride, 'driver')}
                      className="text-blue-600 hover:text-blue-800 hover:bg-blue-50 p-2 rounded transition-colors"
                      title="עריכת נסיעה"
                    >
                      ✏️
                    </button>
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
                <th className="text-right py-3 px-4 font-semibold text-gray-700">פעולות</th>
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
                      ride.flexibility === 'exact'
                        ? 'bg-orange-100 text-orange-700'
                        : ride.flexibility === 'flexible'
                        ? 'bg-green-100 text-green-700'
                        : 'bg-blue-100 text-blue-700'
                    }`}>
                      {ride.flexibility === 'exact' 
                        ? 'מדויק' 
                        : ride.flexibility === 'flexible' 
                        ? 'גמיש' 
                        : 'גמיש מאוד'}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-sm text-gray-600 max-w-[200px] truncate">
                    {ride.notes || '-'}
                  </td>
                  <td className="py-3 px-4 text-sm text-gray-600">
                    {ride.created_at ? new Date(ride.created_at).toLocaleDateString('he-IL') : '-'}
                  </td>
                  <td className="py-3 px-4" onClick={(e) => e.stopPropagation()}>
                    <button
                      onClick={() => openEditModal(ride, 'hitchhiker')}
                      className="text-blue-600 hover:text-blue-800 hover:bg-blue-50 p-2 rounded transition-colors"
                      title="עריכת נסיעה"
                    >
                      ✏️
                    </button>
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

      {editingRide && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" onClick={closeEditModal}>
          <div
            className="bg-white rounded-lg shadow-xl w-full max-w-lg max-h-[90vh] overflow-y-auto p-6"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">עריכת נסיעה</h3>
              <button
                type="button"
                onClick={closeEditModal}
                className="text-gray-500 hover:text-gray-700 text-xl"
              >
                ×
              </button>
            </div>

            <div className="space-y-3">
              <label className="block text-sm text-gray-700">
                מוצא
                <input
                  type="text"
                  value={editForm.origin || ''}
                  onChange={(e) => setEditForm({ ...editForm, origin: e.target.value })}
                  className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-lg"
                />
              </label>

              <label className="block text-sm text-gray-700">
                יעד
                <input
                  type="text"
                  value={editForm.destination || ''}
                  onChange={(e) => setEditForm({ ...editForm, destination: e.target.value })}
                  className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-lg"
                />
              </label>

              {editingType === 'driver' && (
                <label className="block text-sm text-gray-700">
                  ימים (מופרד בפסיקים)
                  <input
                    type="text"
                    value={editForm.days_text || ''}
                    onChange={(e) => setEditForm({ ...editForm, days_text: e.target.value })}
                    className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-lg"
                    placeholder="Sunday, Monday"
                  />
                </label>
              )}

              <label className="block text-sm text-gray-700">
                תאריך
                <input
                  type="date"
                  value={editForm.travel_date || ''}
                  onChange={(e) => setEditForm({ ...editForm, travel_date: e.target.value })}
                  className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-lg"
                />
              </label>

              <label className="block text-sm text-gray-700">
                שעה
                <input
                  type="time"
                  value={editForm.departure_time || ''}
                  onChange={(e) => setEditForm({ ...editForm, departure_time: e.target.value })}
                  className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-lg"
                />
              </label>

              {editingType === 'driver' && (
                <label className="block text-sm text-gray-700">
                  שעת חזרה
                  <input
                    type="time"
                    value={editForm.return_time || ''}
                    onChange={(e) => setEditForm({ ...editForm, return_time: e.target.value })}
                    className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-lg"
                  />
                </label>
              )}

              {editingType === 'hitchhiker' && (
                <label className="block text-sm text-gray-700">
                  גמישות
                  <select
                    value={editForm.flexibility || 'flexible'}
                    onChange={(e) => setEditForm({ ...editForm, flexibility: e.target.value })}
                    className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-lg"
                  >
                    <option value="strict">מדויק</option>
                    <option value="flexible">גמיש</option>
                    <option value="very_flexible">גמיש מאוד</option>
                  </select>
                </label>
              )}

              <label className="block text-sm text-gray-700">
                הערות
                <textarea
                  value={editForm.notes || ''}
                  onChange={(e) => setEditForm({ ...editForm, notes: e.target.value })}
                  className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-lg"
                  rows={3}
                />
              </label>
            </div>

            <div className="mt-6 flex flex-col sm:flex-row gap-3">
              <button
                type="button"
                onClick={handleEditSave}
                disabled={isSaving}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300"
              >
                {isSaving ? 'שומר...' : 'שמור'}
              </button>
              <button
                type="button"
                onClick={closeEditModal}
                className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                ביטול
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default RidesPage;

