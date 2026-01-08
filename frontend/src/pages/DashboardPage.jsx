import { useQuery } from '@tanstack/react-query';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import StatsCard from '../components/Dashboard/StatsCard';
import { statsAPI } from '../api/client';

function DashboardPage() {
  // Fetch overview stats
  const { data: overview, isLoading: overviewLoading } = useQuery({
    queryKey: ['stats', 'overview'],
    queryFn: () => statsAPI.getOverview().then(res => res.data),
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  // Fetch trends
  const { data: trends, isLoading: trendsLoading } = useQuery({
    queryKey: ['stats', 'trends'],
    queryFn: () => statsAPI.getTrends(30).then(res => res.data),
    refetchInterval: 60000, // Refresh every minute
  });

  if (overviewLoading || trendsLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-gray-600">טוען נתונים...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatsCard
          title="משתמשים פעילים"
          value={overview?.active_users_30d || 0}
          subtitle={`סה"כ: ${overview?.total_users || 0}`}
          icon="👥"
          color="primary"
        />
        <StatsCard
          title="נסיעות פעילות"
          value={(overview?.active_driver_rides || 0) + (overview?.active_hitchhiker_requests || 0)}
          subtitle={`נהגים: ${overview?.active_driver_rides || 0} | טרמפיסטים: ${overview?.active_hitchhiker_requests || 0}`}
          icon="🚗"
          color="success"
        />
        <StatsCard
          title="משתמשים חדשים"
          value={overview?.new_users_7d || 0}
          subtitle="ב-7 ימים אחרונים"
          icon="✨"
          color="warning"
        />
        <StatsCard
          title="שגיאות"
          value={0}
          subtitle="היום"
          icon="⚠️"
          color="danger"
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* New Users Chart */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4">משתמשים חדשים (30 ימים)</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={trends?.new_users_by_day || []}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis 
                dataKey="date" 
                tick={{ fontSize: 12 }}
                tickFormatter={(value) => {
                  const date = new Date(value);
                  return `${date.getDate()}/${date.getMonth() + 1}`;
                }}
              />
              <YAxis />
              <Tooltip 
                labelFormatter={(value) => new Date(value).toLocaleDateString('he-IL')}
              />
              <Line 
                type="monotone" 
                dataKey="count" 
                stroke="#3B82F6" 
                strokeWidth={2}
                name="משתמשים"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* New Rides Chart */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4">נסיעות חדשות (30 ימים)</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={trends?.new_rides_by_day || []}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis 
                dataKey="date" 
                tick={{ fontSize: 12 }}
                tickFormatter={(value) => {
                  const date = new Date(value);
                  return `${date.getDate()}/${date.getMonth() + 1}`;
                }}
              />
              <YAxis />
              <Tooltip 
                labelFormatter={(value) => new Date(value).toLocaleDateString('he-IL')}
              />
              <Bar 
                dataKey="count" 
                fill="#10B981"
                name="נסיעות"
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Popular Destinations */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4">יעדים פופולריים</h3>
        <div className="overflow-x-auto">
          <table className="min-w-full">
            <thead>
              <tr className="border-b">
                <th className="text-right py-3 px-4 font-semibold text-gray-700">#</th>
                <th className="text-right py-3 px-4 font-semibold text-gray-700">יעד</th>
                <th className="text-right py-3 px-4 font-semibold text-gray-700">מספר נסיעות</th>
                <th className="text-right py-3 px-4 font-semibold text-gray-700">אחוז</th>
              </tr>
            </thead>
            <tbody>
              {(trends?.popular_destinations || []).map((dest, index) => {
                const total = trends.popular_destinations.reduce((sum, d) => sum + d.count, 0);
                const percentage = ((dest.count / total) * 100).toFixed(1);
                return (
                  <tr key={index} className="border-b hover:bg-gray-50">
                    <td className="py-3 px-4 text-gray-600">{index + 1}</td>
                    <td className="py-3 px-4 font-medium">{dest.destination}</td>
                    <td className="py-3 px-4">{dest.count}</td>
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-2">
                        <div className="flex-1 bg-gray-200 rounded-full h-2">
                          <div 
                            className="bg-primary h-2 rounded-full" 
                            style={{ width: `${percentage}%` }}
                          ></div>
                        </div>
                        <span className="text-sm text-gray-600 min-w-[3rem]">{percentage}%</span>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {(!trends?.popular_destinations || trends.popular_destinations.length === 0) && (
            <div className="text-center py-8 text-gray-500">
              אין נתונים להצגה
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default DashboardPage;



