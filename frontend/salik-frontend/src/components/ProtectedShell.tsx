import { Outlet, useNavigate } from 'react-router-dom';
import type { ReactNode } from 'react';
import Navbar from './Navbar';
import Footer from './Footer';
import { useAuth } from '@/context/AuthContext';

export default function ProtectedShell({ children }: { children?: ReactNode }) {
  const { signOut, profile } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await signOut();
    navigate('/login', { replace: true });
  };

  return (
    <div className="min-h-screen flex flex-col bg-transparent">
      <Navbar userName={profile?.name} userEmail={profile?.email} onLogout={handleLogout} />
      <main className="flex-1">
        {children ?? <Outlet />}
      </main>
      <Footer />
    </div>
  );
}

