import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { usersAPI } from '../../api/client';

function UserDetailsModal({ user, onClose }) {
  const [activeTab, setActiveTab] = useState('history');

  // Fetch user chat history
  const { data: historyData, isLoading } = useQuery({
    queryKey: ['userHistory', user.phone_number],
    queryFn: () => usersAPI.getHistory(user.phone_number, 100).then(res => res.data),
    enabled: !!user,
  });

  useEffect(() => {
    // Close modal on ESC key
    const handleEsc = (e) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleEsc);
    return () => window.removeEventListener('keydown', handleEsc);
  }, [onClose]);

  const chatHistory = historyData?.chat_history || [];

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div 
        className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="bg-primary text-white p-6 flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold">{user.name || 'משתמש'}</h2>
            <p className="text-blue-100 font-mono text-sm mt-1">{user.phone_number}</p>
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

        {/* Tabs */}
        <div className="border-b border-gray-200 px-6">
          <div className="flex gap-4">
            <button
              onClick={() => setActiveTab('history')}
              className={`py-3 px-4 border-b-2 font-medium transition-colors ${
                activeTab === 'history'
                  ? 'border-primary text-primary'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              💬 היסטוריית צ'אט ({historyData?.total_messages || 0})
            </button>
            <button
              onClick={() => setActiveTab('info')}
              className={`py-3 px-4 border-b-2 font-medium transition-colors ${
                activeTab === 'info'
                  ? 'border-primary text-primary'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              ℹ️ פרטים
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[calc(90vh-200px)]">
          {activeTab === 'history' && (
            <div className="space-y-3">
              {isLoading && (
                <div className="text-center py-12">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
                  <p className="text-gray-600">טוען היסטוריה...</p>
                </div>
              )}

              {!isLoading && chatHistory.length === 0 && (
                <div className="text-center py-12 text-gray-500">
                  אין היסטוריית צ'אט
                </div>
              )}

              {!isLoading && chatHistory.map((message, index) => (
                <div
                  key={index}
                  className={`p-4 rounded-lg ${
                    message.role === 'user'
                      ? 'bg-blue-50 border-r-4 border-blue-500'
                      : 'bg-green-50 border-r-4 border-green-500'
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-semibold text-sm">
                      {message.role === 'user' ? '👤 משתמש' : '🤖 מערכת'}
                    </span>
                    <span className="text-xs text-gray-500">
                      {message.timestamp ? new Date(message.timestamp).toLocaleString('he-IL') : ''}
                    </span>
                  </div>
                  <p className="text-gray-800 whitespace-pre-wrap">{message.content}</p>
                </div>
              ))}
            </div>
          )}

          {activeTab === 'info' && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-gray-50 p-4 rounded-lg">
                  <p className="text-sm text-gray-600 mb-1">טלפון</p>
                  <p className="font-mono font-semibold">{user.phone_number}</p>
                </div>
                <div className="bg-gray-50 p-4 rounded-lg">
                  <p className="text-sm text-gray-600 mb-1">שם</p>
                  <p className="font-semibold">{user.name || '-'}</p>
                </div>
                <div className="bg-gray-50 p-4 rounded-lg">
                  <p className="text-sm text-gray-600 mb-1">נסיעות נהג</p>
                  <p className="font-semibold text-blue-600">{user.active_driver_rides || 0}</p>
                </div>
                <div className="bg-gray-50 p-4 rounded-lg">
                  <p className="text-sm text-gray-600 mb-1">בקשות טרמפ</p>
                  <p className="font-semibold text-green-600">{user.active_hitchhiker_requests || 0}</p>
                </div>
                <div className="bg-gray-50 p-4 rounded-lg">
                  <p className="text-sm text-gray-600 mb-1">הודעות</p>
                  <p className="font-semibold">{user.message_count || 0}</p>
                </div>
                <div className="bg-gray-50 p-4 rounded-lg">
                  <p className="text-sm text-gray-600 mb-1">נראה לאחרונה</p>
                  <p className="font-semibold text-sm">
                    {user.last_seen ? new Date(user.last_seen).toLocaleString('he-IL') : '-'}
                  </p>
                </div>
                <div className="bg-gray-50 p-4 rounded-lg col-span-2">
                  <p className="text-sm text-gray-600 mb-1">הצטרף</p>
                  <p className="font-semibold text-sm">
                    {user.created_at ? new Date(user.created_at).toLocaleString('he-IL') : '-'}
                  </p>
                </div>
              </div>
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

export default UserDetailsModal;

