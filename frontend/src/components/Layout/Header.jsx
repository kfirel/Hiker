import { useLocation } from 'react-router-dom';

const pageTitles = {
  '/dashboard': 'דשבורד',
  '/users': 'משתמשים',
  '/rides': 'נסיעות',
  '/errors': 'שגיאות ולוגים',
};

function Header({ onMenuClick }) {
  const location = useLocation();
  const title = pageTitles[location.pathname] || 'דשבורד';

  return (
    <header className="bg-white border-b border-gray-200 px-4 sm:px-6 py-4">
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={onMenuClick}
            className="sm:hidden inline-flex items-center justify-center p-2 rounded-md border border-gray-200 text-gray-600 hover:bg-gray-50"
            aria-label="פתח תפריט"
          >
            ☰
          </button>
          <h2 className="text-xl sm:text-2xl font-bold text-gray-900">{title}</h2>
        </div>
        <div className="hidden sm:flex items-center gap-4">
          <span className="text-sm text-gray-600">
            {new Date().toLocaleDateString('he-IL', {
              weekday: 'long',
              year: 'numeric',
              month: 'long',
              day: 'numeric',
            })}
          </span>
          <div className="w-10 h-10 rounded-full bg-primary flex items-center justify-center text-white font-bold">
            מ
          </div>
        </div>
      </div>
    </header>
  );
}

export default Header;



