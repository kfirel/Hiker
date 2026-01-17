import { NavLink } from 'react-router-dom';

const menuItems = [
  { path: '/dashboard', label: 'דשבורד', icon: '📊' },
  { path: '/users', label: 'משתמשים', icon: '👥' },
  { path: '/rides', label: 'נסיעות', icon: '🚗' },
  { path: '/matches', label: 'התאמות', icon: '🎯' },
  { path: '/errors', label: 'שגיאות ולוגים', icon: '⚠️' },
  { path: '/sandbox', label: 'Sandbox', icon: '🧪' },
];

function Sidebar({ isOpen, onClose }) {
  return (
    <>
      <div
        className={`fixed inset-0 bg-black/40 z-40 sm:hidden ${isOpen ? 'block' : 'hidden'}`}
        onClick={onClose}
        aria-hidden={!isOpen}
      />
      <aside
        className={`fixed right-0 top-0 z-50 h-full w-72 bg-white border-l border-gray-200 flex flex-col transform transition-transform sm:static sm:z-auto sm:translate-x-0 sm:w-64 ${
          isOpen ? 'translate-x-0' : 'translate-x-full'
        }`}
      >
        <div className="p-6 border-b border-gray-200 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-primary">🚗 גברעם</h1>
            <p className="text-sm text-gray-600 mt-1">ממשק ניהול</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="sm:hidden inline-flex items-center justify-center p-2 rounded-md border border-gray-200 text-gray-600 hover:bg-gray-50"
            aria-label="סגור תפריט"
          >
            ✕
          </button>
        </div>
        
        <nav className="flex-1 p-4">
          <ul className="space-y-2">
            {menuItems.map((item) => (
              <li key={item.path}>
                <NavLink
                  to={item.path}
                  onClick={onClose}
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                      isActive
                        ? 'bg-primary text-white'
                        : 'text-gray-700 hover:bg-gray-100'
                    }`
                  }
                >
                  <span className="text-xl">{item.icon}</span>
                  <span className="font-medium">{item.label}</span>
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>
        
        <div className="p-4 border-t border-gray-200">
          <p className="text-xs text-gray-500 text-center">
            פותח על ידי כפיר אלגבסי 👨‍💻
          </p>
        </div>
      </aside>
    </>
  );
}

export default Sidebar;

