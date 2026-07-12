import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';

function AuthLoadingScreen({ message }: { message: string }) {
  return (
    <div className="flex min-h-[70vh] items-center justify-center px-4 py-20">
      <div className="glass-strong max-w-md rounded-3xl px-8 py-10 text-center">
        <Loader2 className="mx-auto h-10 w-10 animate-spin text-cyan-300" />
        <p className="mt-5 text-lg font-semibold text-white">{message}</p>
        <p className="mt-2 text-sm text-gray-400">
          StrategAI is checking your session and preparing your workspace.
        </p>
      </div>
    </div>
  );
}

export function RequireAuth() {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return <AuthLoadingScreen message="Loading your StrategAI workspace..." />;
  }

  if (!user) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  return <Outlet />;
}

export function GuestOnly() {
  const { user, loading } = useAuth();

  if (loading) {
    return <AuthLoadingScreen message="Preparing your login experience..." />;
  }

  if (user) {
    return <Navigate to="/" replace />;
  }

  return <Outlet />;
}

export function AuthBootstrap() {
  const { loading } = useAuth();

  if (loading) {
    return <AuthLoadingScreen message="Syncing your StrategAI session..." />;
  }

  return null;
}

