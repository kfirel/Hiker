import { useState, useRef, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';

const SANDBOX_API = {
  sendMessage: (data) => axios.post('/a/sandbox/send', data, {
    headers: { 'X-Admin-Token': localStorage.getItem('admin_token') },
    timeout: 60000  // 60 seconds timeout (1 minute)
  }),
  getUsers: (env) => axios.get(`/a/sandbox/users?environment=${env}`, {
    headers: { 'X-Admin-Token': localStorage.getItem('admin_token') }
  }),
  getAllRides: (env) => axios.get(`/a/sandbox/all-rides?environment=${env}`, {
    headers: { 'X-Admin-Token': localStorage.getItem('admin_token') }
  }),
  reset: (env) => axios.delete(`/a/sandbox/reset?environment=${env}`, {
    headers: { 'X-Admin-Token': localStorage.getItem('admin_token') }
  })
};

// Test phone numbers
const TEST_USERS = [
  { phone: '972500000001', name: 'User 1', color: 'blue' },
  { phone: '972500000002', name: 'User 2', color: 'green' },
  { phone: '972500000003', name: 'User 3', color: 'purple' },
  { phone: '972500000004', name: 'User 4', color: 'orange' },
];

// Quick messages templates
const QUICK_MESSAGES = [
  { 
    label: '🚗 נהג → תל אביב מחר 10:00',
    text: 'אני נוסע לתל אביב מחר בשעה 10'
  },
  { 
    label: '🚗 נהג → ירושלים מחר 8:00',
    text: 'אני נוסע לירושלים מחר בשעה 8'
  },
  { 
    label: '🚗 נהג → חיפה היום 14:00',
    text: 'אני נוסע לחיפה היום בשעה 14'
  },
  { 
    label: '🚗 נהג קבוע → ת״א א׳-ה׳',
    text: 'אני נוסע לתל אביב בימים א-ה בשעה 8'
  },
  { 
    label: '🎒 טרמפיסט → תל אביב מחר 10:00',
    text: 'מחפש טרמפ לתל אביב מחר בשעה 10'
  },
  { 
    label: '🎒 טרמפיסט → ירושלים מחר 8:00',
    text: 'מחפש טרמפ לירושלים מחר בשעה 8'
  },
  { 
    label: '🎒 טרמפיסט → חיפה היום',
    text: 'צריך טרמפ לחיפה היום'
  },
  { 
    label: '📋 צפה ברשימה',
    text: '?'
  },
  { 
    label: '🗑️ מחק הכל',
    text: 'מחק הכל'
  },
  { 
    label: '❓ עזרה',
    text: 'עזרה'
  },
];

function ChatPanel({ user, environment }) {
  const [message, setMessage] = useState('');
  const [chatHistory, setChatHistory] = useState([]);
  const [showQuickMessages, setShowQuickMessages] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const messagesEndRef = useRef(null);
  const queryClient = useQueryClient();

  // Helper function to clean metadata from messages
  const cleanMetadata = (content) => {
    // Remove [CONFLICT:...] metadata that's meant for AI only
    if (typeof content === 'string') {
      return content.replace(/\s*\[CONFLICT:[^\]]+\]\s*$/, '');
    }
    return content;
  };

  // Sync chatHistory with user.chat_history from server
  // But skip if we're currently sending (to avoid overwriting optimistic updates)
  useEffect(() => {
    if (user.chat_history && Array.isArray(user.chat_history) && !isSending) {
      const serverHistory = user.chat_history.map(msg => ({
        role: msg.role || (msg.content.startsWith('👤') ? 'user' : 'assistant'),
        content: cleanMetadata(msg.content), // Clean metadata before displaying
        timestamp: msg.timestamp
      }));
      
      console.log(`🔄 [${user.phone}] Syncing chat history: ${user.chat_history.length} messages, message_count: ${user.message_count}`);
      setChatHistory(serverHistory);
    } else {
      console.log(`⏸️ [${user.phone}] Skipping sync: isSending=${isSending}, has_history=${!!user.chat_history}`);
    }
  }, [user.message_count, user.phone, isSending]); // Re-sync when message count changes

  const sendMutation = useMutation({
    mutationFn: (msg) => SANDBOX_API.sendMessage({
      phone_number: user.phone,
      message: msg,
      environment
    }),
    onMutate: (sentMessage) => {
      // Mark as sending to prevent useEffect from overwriting
      setIsSending(true);
      // Add user message immediately (optimistic update)
      setChatHistory(prev => [
        ...prev,
        { role: 'user', content: sentMessage, timestamp: new Date().toISOString() },
        { role: 'assistant', content: '⏳ מעבד...', timestamp: new Date().toISOString(), isLoading: true }
      ]);
      setMessage('');
    },
    onSuccess: (response, sentMessage) => {
      // Replace loading message with actual response
      setChatHistory(prev => {
        const withoutLoading = prev.filter(msg => !msg.isLoading);
        return [
          ...withoutLoading,
          { role: 'assistant', content: response.data.response || 'טעינה...', timestamp: new Date().toISOString() }
        ];
      });
      queryClient.invalidateQueries(['sandboxUsers', environment]);
      // Allow useEffect to sync again after a short delay
      setTimeout(() => setIsSending(false), 500);
    },
    onError: (error, sentMessage) => {
      // Remove loading message on error
      setChatHistory(prev => {
        const withoutLoading = prev.filter(msg => !msg.isLoading);
        // Add error message
        return [
          ...withoutLoading,
          { 
            role: 'assistant', 
            content: error.code === 'ECONNABORTED' 
              ? '⏳ השרת עמוס כרגע. נסה שוב בעוד כמה שניות 🔄' 
              : '❌ שגיאה: ' + error.message,
            timestamp: new Date().toISOString() 
          }
        ];
      });
      // Allow useEffect to sync again
      setIsSending(false);
    },
    retry: false  // Don't retry on failure
  });

  const handleSend = (e) => {
    e.preventDefault();
    if (!message.trim()) return;
    sendMutation.mutate(message);
  };

  const handleQuickMessage = (text) => {
    setShowQuickMessages(false);
    // Send immediately
    sendMutation.mutate(text);
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory]);

  const colorClasses = {
    blue: 'bg-blue-500',
    green: 'bg-green-500',
    purple: 'bg-purple-500',
    orange: 'bg-orange-500'
  };

  return (
    <div className="flex flex-col h-full bg-white rounded-lg shadow border-2 border-gray-200">
      {/* Header */}
      <div className={`${colorClasses[user.color]} text-white p-3 rounded-t-lg`}>
        <div className="font-semibold">{user.name}</div>
        <div className="text-xs opacity-90">{user.phone}</div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-2" style={{ minHeight: '200px', maxHeight: '300px' }}>
        {chatHistory.map((msg, idx) => (
          <div
            key={idx}
            className={`p-2 rounded-lg text-sm ${
              msg.role === 'user'
                ? 'bg-blue-50 border-r-4 border-blue-500 text-right'
                : 'bg-green-50 border-r-4 border-green-500 text-right'
            }`}
          >
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs font-semibold">
                {msg.role === 'user' ? '👤 אני' : '🤖 בוט'}
              </span>
              <span className="text-xs text-gray-500">
                {new Date(msg.timestamp).toLocaleTimeString('he-IL')}
              </span>
            </div>
            <p className="whitespace-pre-wrap">{msg.content}</p>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSend} className="p-3 border-t bg-gray-50 rounded-b-lg">
        {/* Quick Messages Dropdown */}
        {showQuickMessages && (
          <div className="mb-2 p-2 bg-white border rounded-lg shadow-lg max-h-64 overflow-y-auto">
            <div className="text-xs font-semibold text-gray-600 mb-2 px-2">הודעות מהירות:</div>
            {QUICK_MESSAGES.map((msg, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => handleQuickMessage(msg.text)}
                className="w-full text-right px-3 py-2 text-sm hover:bg-blue-50 rounded transition-colors flex items-center gap-2"
              >
                <span>{msg.label}</span>
              </button>
            ))}
          </div>
        )}
        
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => setShowQuickMessages(!showQuickMessages)}
            className="px-3 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors text-sm font-medium"
            title="הודעות מהירות"
          >
            📝 מהיר
          </button>
          <input
            type="text"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="הקלד הודעה..."
            className="flex-1 px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
            disabled={sendMutation.isPending}
          />
          <button
            type="submit"
            disabled={sendMutation.isPending || !message.trim()}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors text-sm font-medium"
          >
            {sendMutation.isPending ? '...' : 'שלח'}
          </button>
        </div>
      </form>
    </div>
  );
}

function SandboxPage() {
  // Test users always use 'test' environment (test_ collections)
  const environment = 'test';
  const [showAllRides, setShowAllRides] = useState(false);
  const queryClient = useQueryClient();

  // Fetch sandbox users
  const { data: usersData } = useQuery({
    queryKey: ['sandboxUsers', environment],
    queryFn: () => SANDBOX_API.getUsers(environment).then(res => res.data),
    refetchInterval: 10000, // Refresh every 10 seconds
  });

  // Fetch all rides (on demand)
  const { data: allRidesData, refetch: refetchRides } = useQuery({
    queryKey: ['sandboxAllRides', environment],
    queryFn: () => SANDBOX_API.getAllRides(environment).then(res => res.data),
    enabled: showAllRides, // Only fetch when modal is shown
  });

  const resetMutation = useMutation({
    mutationFn: () => SANDBOX_API.reset(environment),
    onSuccess: () => {
      queryClient.invalidateQueries(['sandboxUsers']);
      alert('✅ ה-Sandbox אופס!');
    },
    onError: () => {
      alert('❌ שגיאה באיפוס');
    }
  });

  const handleReset = () => {
    if (window.confirm('האם אתה בטוח שברצונך לאפס את כל נתוני הטסט?')) {
      resetMutation.mutate();
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">🧪 Sandbox</h1>
            <p className="text-gray-600 mt-1">סביבת בדיקות עם 4 משתמשי טסט</p>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-2">
                <button
                  onClick={() => {
                    setShowAllRides(true);
                    refetchRides();
                  }}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
                >
                  📊 הצג כל הנסיעות
                </button>
                <button
                  onClick={handleReset}
                  disabled={resetMutation.isPending}
                  className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:bg-gray-300 transition-colors text-sm font-medium"
                >
                  🗑️ אפס הכל
                </button>
              </div>
        </div>

      </div>

      {/* Chat Panels */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {TEST_USERS.map((staticUser) => {
          // Find matching user data from server (includes chat_history)
          const serverUser = usersData?.users?.find(u => u.phone_number === staticUser.phone);
          
          // Merge static info (name, color) with server data (chat_history)
          const mergedUser = {
            ...staticUser,
            chat_history: serverUser?.chat_history || [],
            message_count: serverUser?.message_count || 0
          };
          
          return <ChatPanel key={staticUser.phone} user={mergedUser} environment={environment} />;
        })}
      </div>

      {/* All Rides Modal */}
      {showAllRides && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" onClick={() => setShowAllRides(false)}>
          <div className="bg-white rounded-lg shadow-xl p-6 max-w-4xl w-full max-h-[80vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold text-gray-900">📊 כל הנסיעות והבקשות</h2>
              <button
                onClick={() => setShowAllRides(false)}
                className="text-gray-500 hover:text-gray-700 text-2xl"
              >
                ×
              </button>
            </div>

            {allRidesData ? (
              <div className="space-y-6">
                {/* Summary */}
                <div className="bg-blue-50 rounded-lg p-4">
                  <div className="text-sm text-gray-600">סה"כ:</div>
                  <div className="flex gap-6 mt-2">
                    <div className="font-semibold">🚗 {allRidesData.driver_count} נהגים</div>
                    <div className="font-semibold">🎒 {allRidesData.hitchhiker_count} טרמפיסטים</div>
                  </div>
                </div>

                {/* Drivers */}
                {allRidesData.drivers && allRidesData.drivers.length > 0 && (
                  <div>
                    <h3 className="text-lg font-semibold mb-2 text-gray-900">🚗 נהגים</h3>
                    <div className="space-y-2">
                      {allRidesData.drivers.map((driver, idx) => (
                        <div key={idx} className="bg-green-50 border-r-4 border-green-500 rounded-lg p-3">
                          <div className="flex justify-between items-start">
                            <div>
                              <div className="font-semibold">{driver.name} ({driver.phone})</div>
                              <div className="text-sm">📍 {driver.origin || 'גברעם'} → {driver.destination}</div>
                              <div className="text-sm">🕐 {driver.date} בשעה {driver.time}</div>
                              {driver.days && <div className="text-sm">📅 {driver.days}</div>}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Hitchhikers */}
                {allRidesData.hitchhikers && allRidesData.hitchhikers.length > 0 && (
                  <div>
                    <h3 className="text-lg font-semibold mb-2 text-gray-900">🎒 טרמפיסטים</h3>
                    <div className="space-y-2">
                      {allRidesData.hitchhikers.map((hitchhiker, idx) => (
                        <div key={idx} className="bg-blue-50 border-r-4 border-blue-500 rounded-lg p-3">
                          <div className="flex justify-between items-start">
                            <div>
                              <div className="font-semibold">{hitchhiker.name} ({hitchhiker.phone})</div>
                              <div className="text-sm">📍 {hitchhiker.origin || 'גברעם'} → {hitchhiker.destination}</div>
                              <div className="text-sm">🕐 {hitchhiker.date} בשעה {hitchhiker.time}</div>
                              {hitchhiker.flexibility && (
                                <div className="text-sm">
                                  ⏱️ גמישות: {
                                    hitchhiker.flexibility === 'exact' 
                                      ? 'מדויק' 
                                      : hitchhiker.flexibility === 'flexible' 
                                      ? 'גמיש' 
                                      : 'גמיש מאוד'
                                  }
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {allRidesData.driver_count === 0 && allRidesData.hitchhiker_count === 0 && (
                  <div className="text-center text-gray-500 py-8">
                    אין נסיעות או בקשות בסביבת הטסט
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center text-gray-500 py-8">טוען...</div>
            )}
          </div>
        </div>
      )}

    </div>
  );
}

export default SandboxPage;

