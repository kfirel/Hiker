import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { matchesAPI } from '../api/client';

function MatchesPage() {
  const [destination, setDestination] = useState('');
  const [matchType, setMatchType] = useState('');
  const [limit, setLimit] = useState(100);

  const { data, isLoading } = useQuery({
    queryKey: ['matches', { destination, matchType, limit }],
    queryFn: () =>
      matchesAPI
        .list({
          destination: destination || undefined,
          match_type: matchType || undefined,
          limit,
        })
        .then((res) => res.data),
    refetchInterval: 30000,
  });

  const matches = data?.matches || [];

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-gray-600">טוען התאמות...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-lg shadow p-4 sm:p-6">
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex-1 min-w-0">
            <input
              type="text"
              placeholder="סינון לפי יעד..."
              value={destination}
              onChange={(e) => setDestination(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"
            />
          </div>
          <select
            value={matchType}
            onChange={(e) => setMatchType(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary"
          >
            <option value="">כל הסוגים</option>
            <option value="driver">נהג</option>
            <option value="hitchhiker">טרמפיסט</option>
          </select>
          <select
            value={limit}
            onChange={(e) => setLimit(Number(e.target.value))}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary"
          >
            <option value={50}>50</option>
            <option value={100}>100</option>
            <option value={200}>200</option>
          </select>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="text-right py-3 px-4 font-semibold text-gray-700">זמן</th>
                <th className="text-right py-3 px-4 font-semibold text-gray-700">סוג</th>
                <th className="text-right py-3 px-4 font-semibold text-gray-700">משתמש</th>
                <th className="text-right py-3 px-4 font-semibold text-gray-700">הותאם עם</th>
                <th className="text-right py-3 px-4 font-semibold text-gray-700">מוצא → יעד</th>
                <th className="text-right py-3 px-4 font-semibold text-gray-700">תאריך/שעה</th>
                <th className="text-right py-3 px-4 font-semibold text-gray-700">מרחק/סף</th>
              </tr>
            </thead>
            <tbody>
              {matches.map((match) => {
                const detail = match.match_details || {};
                const distance = detail.distance ? `${detail.distance.toFixed(1)} ק"מ` : '-';
                const threshold = detail.threshold ? `${detail.threshold.toFixed(1)} ק"מ` : '-';
                return (
                  <tr key={match.id} className="border-t hover:bg-gray-50">
                    <td className="py-3 px-4 text-sm text-gray-600">
                      {match.timestamp ? new Date(match.timestamp).toLocaleString('he-IL') : '-'}
                    </td>
                    <td className="py-3 px-4">
                      <span className="px-2 py-1 rounded-full text-xs font-semibold bg-blue-100 text-blue-700">
                        {match.match_type === 'driver' ? 'נהג' : 'טרמפיסט'}
                      </span>
                      {match.match_kind === 'on_route' && (
                        <span className="ml-2 text-xs text-green-700">על הדרך</span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-sm">
                      <div>{match.matcher_name || '-'}</div>
                      <div className="font-mono text-xs text-gray-500">{match.matcher_phone}</div>
                    </td>
                    <td className="py-3 px-4 text-sm">
                      <div>{match.matched_name || '-'}</div>
                      <div className="font-mono text-xs text-gray-500">{match.matched_phone}</div>
                    </td>
                    <td className="py-3 px-4 text-sm">
                      {match.origin || '-'} → {match.destination || '-'}
                    </td>
                    <td className="py-3 px-4 text-sm text-gray-600">
                      {match.travel_date || '-'} {match.departure_time || ''}
                    </td>
                    <td className="py-3 px-4 text-sm text-gray-600">
                      {distance} / {threshold}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {matches.length === 0 && (
          <div className="text-center py-12 text-gray-500">אין התאמות להצגה</div>
        )}
      </div>
    </div>
  );
}

export default MatchesPage;
