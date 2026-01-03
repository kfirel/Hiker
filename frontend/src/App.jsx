import { Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout/Layout';
import DashboardPage from './pages/DashboardPage';
import UsersPage from './pages/UsersPage';
import RidesPage from './pages/RidesPage';
import ErrorsPage from './pages/ErrorsPage';
import SandboxPage from './pages/SandboxPage';
import LoginPage from './pages/LoginPage';
import TokenCheck from './components/TokenCheck';

function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/" element={
        <TokenCheck>
          <Layout />
        </TokenCheck>
      }>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="users" element={<UsersPage />} />
        <Route path="rides" element={<RidesPage />} />
        <Route path="errors" element={<ErrorsPage />} />
        <Route path="sandbox" element={<SandboxPage />} />
      </Route>
    </Routes>
  );
}

export default App;

