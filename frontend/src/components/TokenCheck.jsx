import { useEffect, useState } from 'react';

function TokenCheck({ children }) {
  const [hasToken, setHasToken] = useState(false);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('admin_token');
    setHasToken(!!token);
    setChecking(false);
  }, []);

  if (checking) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-gray-600">טוען...</p>
        </div>
      </div>
    );
  }

  if (!hasToken) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-50" dir="rtl">
        <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-8">
          <div className="text-center mb-6">
            <div className="text-6xl mb-4">🔐</div>
            <h1 className="text-2xl font-bold text-gray-900 mb-2">דרוש אימות</h1>
            <p className="text-gray-600">נדרש token למערכת ניהול</p>
          </div>

          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
            <p className="text-sm text-gray-700 mb-3 font-semibold">
              הוראות התחברות:
            </p>
            <ol className="text-sm text-gray-600 space-y-2 list-decimal list-inside">
              <li>פתח Console (לחץ F12)</li>
              <li>הדבק את הקוד הבא:</li>
            </ol>
          </div>

          <div className="bg-gray-900 rounded-lg p-4 mb-4">
            <code className="text-green-400 text-sm font-mono break-all">
              localStorage.setItem('admin_token', 'hiker-admin-2026');
            </code>
          </div>

          <button
            onClick={() => window.location.reload()}
            className="w-full bg-primary text-white py-3 px-4 rounded-lg hover:bg-blue-600 transition-colors font-medium"
          >
            🔄 רענן את הדף אחרי הגדרת Token
          </button>

          <div className="mt-6 text-center">
            <p className="text-xs text-gray-500">
              💡 הtoken שומר במחשב שלך ונשאר פעיל
            </p>
          </div>
        </div>
      </div>
    );
  }

  return children;
}

export default TokenCheck;

