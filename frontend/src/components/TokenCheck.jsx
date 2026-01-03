import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

function TokenCheck({ children }) {
  const [hasToken, setHasToken] = useState(false);
  const [checking, setChecking] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const token = localStorage.getItem('admin_token');
    if (!token) {
      navigate('/login');
    } else {
      setHasToken(true);
    }
    setChecking(false);
  }, [navigate]);

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
    return null; // Will redirect to login
  }

  return children;
}

export default TokenCheck;

