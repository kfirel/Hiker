import { NavLink } from 'react-router-dom';

const menuItems = [
  { path: '/dashboard', label: 'דשבורד', icon: '📊' },
  { path: '/users', label: 'משתמשים', icon: '👥' },
  { path: '/rides', label: 'נסיעות', icon: '🚗' },
  { path: '/errors', label: 'שגיאות ולוגים', icon: '⚠️' },
];

function Sidebar() {
  return (
    <aside className="w-64 bg-white border-l border-gray-200 flex flex-col">
      <div className="p-6 border-b border-gray-200">
        <h1 className="text-2xl font-bold text-primary">🚗 גברעם</h1>
        <p className="text-sm text-gray-600 mt-1">ממשק ניהול</p>
      </div>
      
      <nav className="flex-1 p-4">
        <ul className="space-y-2">
          {menuItems.map((item) => (
            <li key={item.path}>
              <NavLink
                to={item.path}
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
  );
}

export default Sidebar;

