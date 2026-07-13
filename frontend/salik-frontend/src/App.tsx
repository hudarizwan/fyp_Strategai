import { BrowserRouter, Navigate, Route, Routes, useLocation } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import { AnimatePresence, motion } from 'framer-motion';
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

const pageTransition = {
  initial: { opacity: 0, y: 12, filter: 'blur(8px)' },
  animate: { opacity: 1, y: 0, filter: 'blur(0px)' },
  exit: { opacity: 0, y: -8, filter: 'blur(6px)' },
  transition: { duration: 0.28, ease: [0.4, 0, 0.2, 1] as const },
};

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
    <motion.div {...pageTransition} className="min-h-screen">
      <ProtectedShell>
        <Dashboard />
      </ProtectedShell>
    </motion.div>
  );
}

function AppRoutes() {
  const location = useLocation();

  return (
    <AnimatePresence mode="wait">
      <motion.div key={location.pathname} {...pageTransition} className="min-h-screen">
        <Routes location={location}>
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
      </motion.div>
    </AnimatePresence>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AppRoutes />
    </BrowserRouter>
  );
}

export default App;
