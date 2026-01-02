import { Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout/Layout';
import DashboardPage from './pages/DashboardPage';
import UsersPage from './pages/UsersPage';
import RidesPage from './pages/RidesPage';
import ErrorsPage from './pages/ErrorsPage';

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="users" element={<UsersPage />} />
        <Route path="rides" element={<RidesPage />} />
        <Route path="errors" element={<ErrorsPage />} />
      </Route>
    </Routes>
  );
}

export default App;

