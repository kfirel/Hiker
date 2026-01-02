import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { logsAPI } from '../api/client';

function ErrorsPage() {
  const [activeTab, setActiveTab] = useState('errors');
  const [severity, setSeverity] = useState('');
  const [limit, setLimit] = useState(100);
  
  // Fetch logs based on active tab
  const { data, isLoading, refetch } = useQuery({
    queryKey: ['logs', activeTab, { severity, limit }],
    queryFn: () => {
      if (activeTab === 'errors') {
        return logsAPI.getErrors({ severity, limit }).then(res => res.data);
      } else {
        return logsAPI.getActivity({ limit }).then(res => res.data);
      }
    },
    refetchInterval: 30000,
  });

  const getSeverityColor = (sev) => {
    switch (sev) {
      case 'error':
        return 'bg-red-100 text-red-700 border-red-200';
      case 'warning':
        return 'bg-yellow-100 text-yellow-700 border-yellow-200';
      case 'info':
        return 'bg-blue-100 text-blue-700 border-blue-200';
      default:
        return 'bg-gray-100 text-gray-700 border-gray-200';
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-gray-600">טוען לוגים...</p>
        </div>
      </div>
    );
  }

  const logs = data?.logs || [];

  return (
    <div className="space-y-6">
      {/* Header with Tabs */}
      <div className="bg-white rounded-lg shadow">
        <div className="border-b border-gray-200">
          <div className="flex gap-1 p-1">
            <button
              onClick={() => setActiveTab('errors')}
              className={`flex-1 px-4 py-3 rounded-lg font-medium transition-colors ${
                activeTab === 'errors'
                  ? 'bg-primary text-white'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              ⚠️ שגיאות ({logs.length})
            </button>
            <button
              onClick={() => setActiveTab('activity')}
              className={`flex-1 px-4 py-3 rounded-lg font-medium transition-colors ${
                activeTab === 'activity'
                  ? 'bg-primary text-white'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              📝 לוג פעילות ({logs.length})
            </button>
          </div>
        </div>
        
        <div className="p-6">
          <div className="flex items-center justify-between gap-4 flex-wrap">
            {activeTab === 'errors' && (
              <div className="flex gap-2">
                <select
                  value={severity}
                  onChange={(e) => setSeverity(e.target.value)}
                  className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary"
                >
                  <option value="">כל הרמות</option>
                  <option value="error">שגיאות</option>
                  <option value="warning">אזהרות</option>
                  <option value="info">מידע</option>
                </select>
              </div>
            )}
            
            <div className="flex-1"></div>
            
            <select
              value={limit}
              onChange={(e) => setLimit(Number(e.target.value))}
              className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary"
            >
              <option value={50}>50 אחרונים</option>
              <option value={100}>100 אחרונים</option>
              <option value={200}>200 אחרונים</option>
            </select>
            
            <button
              onClick={() => refetch()}
              className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-blue-600 transition-colors"
            >
              🔄 רענן
            </button>
          </div>
        </div>
      </div>

      {/* Logs Display */}
      <div className="space-y-3">
        {logs.map((log) => (
          <div
            key={log.id}
            className="bg-white rounded-lg shadow p-4 hover:shadow-md transition-shadow"
          >
            <div className="flex items-start gap-4">
              {activeTab === 'errors' && (
                <span className={`px-3 py-1 rounded-full text-xs font-semibold border ${getSeverityColor(log.severity)}`}>
                  {log.severity}
                </span>
              )}
              
              <div className="flex-1">
                <div className="flex items-start justify-between gap-4 mb-2">
                  <p className="font-medium text-gray-900">{log.message || log.description}</p>
                  <span className="text-sm text-gray-500 whitespace-nowrap">
                    {log.timestamp ? new Date(log.timestamp).toLocaleString('he-IL') : '-'}
                  </span>
                </div>
                
                {log.user_phone && (
                  <p className="text-sm text-gray-600 mb-2">
                    <span className="font-semibold">משתמש:</span> {log.user_phone}
                  </p>
                )}
                
                {log.activity_type && (
                  <p className="text-sm text-gray-600 mb-2">
                    <span className="font-semibold">סוג:</span> {log.activity_type}
                  </p>
                )}
                
                {log.context && Object.keys(log.context).length > 0 && (
                  <details className="text-sm text-gray-600 mt-2">
                    <summary className="cursor-pointer hover:text-primary">הצג פרטים נוספים</summary>
                    <pre className="mt-2 p-3 bg-gray-50 rounded-lg overflow-x-auto text-xs">
                      {JSON.stringify(log.context, null, 2)}
                    </pre>
                  </details>
                )}
                
                {log.stack_trace && (
                  <details className="text-sm text-gray-600 mt-2">
                    <summary className="cursor-pointer hover:text-primary">הצג Stack Trace</summary>
                    <pre className="mt-2 p-3 bg-gray-50 rounded-lg overflow-x-auto text-xs font-mono">
                      {log.stack_trace}
                    </pre>
                  </details>
                )}
                
                {log.metadata && Object.keys(log.metadata).length > 0 && (
                  <details className="text-sm text-gray-600 mt-2">
                    <summary className="cursor-pointer hover:text-primary">הצג מטא-דאטה</summary>
                    <pre className="mt-2 p-3 bg-gray-50 rounded-lg overflow-x-auto text-xs">
                      {JSON.stringify(log.metadata, null, 2)}
                    </pre>
                  </details>
                )}
              </div>
            </div>
          </div>
        ))}
        
        {logs.length === 0 && (
          <div className="bg-white rounded-lg shadow p-12 text-center text-gray-500">
            {activeTab === 'errors' ? '🎉 אין שגיאות!' : 'אין לוגי פעילות'}
          </div>
        )}
      </div>
    </div>
  );
}

export default ErrorsPage;

