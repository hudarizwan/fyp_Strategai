import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import Dashboard from './pages/Dashboard';
import Results from './pages/Results';
import Analytics from './pages/Analytics';
import Strategy from './pages/Strategy';
import Visualization from './pages/Visualization';
import Reports from './pages/Reports';
import Marketing from '@/pages/Marketing';
import MarketingHistory from '@/pages/MarketingHistory';
import Landing from './pages/Landing';
import Login from './pages/Login';
import Signup from './pages/Signup';
import ForgotPassword from './pages/ForgotPassword';
import AuthCallback from './pages/AuthCallback';
import ProtectedShell from './components/ProtectedShell';
import { GuestOnly, RequireAuth } from './components/AuthRouteGuards';
import { useAuth } from '@/context/AuthContext';

function HomeRoute() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center px-4">
        <div className="glass-strong max-w-md rounded-3xl px-8 py-10 text-center">
          <Loader2 className="mx-auto h-10 w-10 animate-spin text-cyan-300" />
          <p className="mt-5 text-lg font-semibold text-white">Loading StrategAI...</p>
          <p className="mt-2 text-sm text-gray-400">
            Preparing your personalized workspace and session state.
          </p>
        </div>
      </div>
    );
  }

  if (!user) {
    return <Landing />;
  }

  return (
    <ProtectedShell>
      <Dashboard />
    </ProtectedShell>
  );
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/auth/callback" element={<AuthCallback />} />

        <Route element={<GuestOnly />}>
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />
        </Route>

        <Route path="/" element={<HomeRoute />} />

        <Route element={<RequireAuth />}>
          <Route element={<ProtectedShell />}>
            <Route path="/results" element={<Results />} />
            <Route path="/analytics" element={<Analytics />} />
            <Route path="/strategy" element={<Strategy />} />
            <Route path="/visualization" element={<Visualization />} />
            <Route path="/reports" element={<Reports />} />
            <Route path="/marketing" element={<Marketing />} />
            <Route path="/marketing/history" element={<MarketingHistory />} />
          </Route>
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
