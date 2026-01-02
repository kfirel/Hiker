import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { usersAPI } from '../api/client';

function UsersPage() {
  const [search, setSearch] = useState('');
  const [sortBy, setSortBy] = useState('last_seen');
  const [order, setOrder] = useState('desc');
  
  // Fetch users
  const { data, isLoading, refetch } = useQuery({
    queryKey: ['users', { search, sortBy, order }],
    queryFn: () => usersAPI.list({ search, sort_by: sortBy, order, limit: 100 }).then(res => res.data),
    refetchInterval: 30000,
  });

  const handleExport = async () => {
    try {
      const response = await usersAPI.exportCSV();
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'users_export.csv');
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
          <p className="text-gray-600">טוען משתמשים...</p>
        </div>
      </div>
    );
  }

  const users = data?.users || [];

  return (
    <div className="space-y-6">
      {/* Header with Search and Export */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div className="flex-1 min-w-[200px]">
            <input
              type="text"
              placeholder="חיפוש לפי טלפון או שם..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"
            />
          </div>
          
          <div className="flex gap-2">
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary"
            >
              <option value="last_seen">לפי תאריך אחרון</option>
              <option value="created_at">לפי תאריך הצטרפות</option>
              <option value="name">לפי שם</option>
            </select>
            
            <button
              onClick={() => setOrder(order === 'asc' ? 'desc' : 'asc')}
              className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              {order === 'asc' ? '↑' : '↓'}
            </button>
            
            <button
              onClick={handleExport}
              className="px-4 py-2 bg-success text-white rounded-lg hover:bg-green-600 transition-colors"
            >
              📊 ייצוא CSV
            </button>
          </div>
        </div>
        
        <div className="mt-4 text-sm text-gray-600">
          סה"כ {data?.total || 0} משתמשים | מציג {users.length}
        </div>
      </div>

      {/* Users Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="text-right py-3 px-4 font-semibold text-gray-700">טלפון</th>
                <th className="text-right py-3 px-4 font-semibold text-gray-700">שם</th>
                <th className="text-right py-3 px-4 font-semibold text-gray-700">נסיעות נהג</th>
                <th className="text-right py-3 px-4 font-semibold text-gray-700">בקשות טרמפ</th>
                <th className="text-right py-3 px-4 font-semibold text-gray-700">הודעות</th>
                <th className="text-right py-3 px-4 font-semibold text-gray-700">נראה לאחרונה</th>
                <th className="text-right py-3 px-4 font-semibold text-gray-700">הצטרף</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.phone_number} className="border-t hover:bg-gray-50">
                  <td className="py-3 px-4 font-mono text-sm">{user.phone_number}</td>
                  <td className="py-3 px-4 font-medium">{user.name || '-'}</td>
                  <td className="py-3 px-4">
                    <span className={`px-2 py-1 rounded-full text-xs font-semibold ${
                      user.active_driver_rides > 0 ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-600'
                    }`}>
                      {user.active_driver_rides}
                    </span>
                  </td>
                  <td className="py-3 px-4">
                    <span className={`px-2 py-1 rounded-full text-xs font-semibold ${
                      user.active_hitchhiker_requests > 0 ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'
                    }`}>
                      {user.active_hitchhiker_requests}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-gray-600">{user.message_count}</td>
                  <td className="py-3 px-4 text-sm text-gray-600">
                    {user.last_seen ? new Date(user.last_seen).toLocaleDateString('he-IL') : '-'}
                  </td>
                  <td className="py-3 px-4 text-sm text-gray-600">
                    {user.created_at ? new Date(user.created_at).toLocaleDateString('he-IL') : '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          
          {users.length === 0 && (
            <div className="text-center py-12 text-gray-500">
              {search ? 'לא נמצאו משתמשים תואמים' : 'אין משתמשים במערכת'}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default UsersPage;

