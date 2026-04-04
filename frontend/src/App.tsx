import { Routes, Route } from 'react-router-dom';
import Navbar from './components/Navbar';
import ProtectedRoute from './components/ProtectedRoute';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import UploadPage from './pages/UploadPage';
import ResultPage from './pages/ResultPage';
import HistoryPage from './pages/HistoryPage';
import CallbackPage from './pages/CallbackPage';
import TwoFactorPage from './pages/TwoFactorPage';
import ApiKeyPage from './pages/ApiKeyPage';

export default function App() {
  return (
    <>
      <Navbar />
      <main style={{ padding: '1.5rem', maxWidth: '960px', margin: '0 auto' }}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/callback" element={<CallbackPage />} />
          <Route element={<ProtectedRoute />}>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/upload" element={<UploadPage />} />
            <Route path="/result/:materialId" element={<ResultPage />} />
            <Route path="/history" element={<HistoryPage />} />
            <Route path="/settings/2fa" element={<TwoFactorPage />} />
            <Route path="/settings/api-key" element={<ApiKeyPage />} />
          </Route>
        </Routes>
      </main>
    </>
  );
}
