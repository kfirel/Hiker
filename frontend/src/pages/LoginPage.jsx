import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

function LoginPage() {
  const [token, setToken] = useState('');
  const navigate = useNavigate();

  const handleLogin = (e) => {
    e.preventDefault();
    if (token.trim()) {
      localStorage.setItem('admin_token', token.trim());
      navigate('/dashboard');
      window.location.reload(); // Reload to apply token
    } else {
      alert('נא להזין Admin Token');
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-500 to-blue-700 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-2xl p-8 max-w-md w-full">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">🚗 גברעם</h1>
          <p className="text-gray-600">ממשק ניהול</p>
        </div>

        <form onSubmit={handleLogin} className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Admin Token
            </label>
            <input
              type="password"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              placeholder="הזן את ה-Admin Token שלך"
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              autoFocus
            />
          </div>

          <button
            type="submit"
            className="w-full bg-blue-600 text-white py-3 rounded-lg hover:bg-blue-700 transition-colors font-medium"
          >
            התחבר
          </button>
        </form>

        <div className="mt-6 p-4 bg-gray-50 rounded-lg">
          <p className="text-xs text-gray-600 text-center mb-2">💡 לפיתוח מקומי:</p>
          <code className="text-xs bg-gray-800 text-green-400 px-2 py-1 rounded block text-center">
            hiker-admin-2026
          </code>
        </div>

        <div className="mt-6 text-center text-xs text-gray-500">
          <p>או פתח Console (F12) והרץ:</p>
          <code className="text-xs bg-gray-100 px-2 py-1 rounded inline-block mt-2">
            localStorage.setItem('admin_token', 'your-token')
          </code>
        </div>
      </div>
    </div>
  );
}

export default LoginPage;



