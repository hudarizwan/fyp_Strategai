import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Loader2, Sparkles } from 'lucide-react';
import { motion } from 'framer-motion';
import { useAuth } from '@/context/AuthContext';

function AuthCallback() {
  const { user, loading } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!loading && user) {
      navigate('/', { replace: true });
    }
  }, [loading, navigate, user]);

  return (
    <div className="flex min-h-screen items-center justify-center overflow-hidden bg-[radial-gradient(circle_at_top_left,_rgba(14,165,233,0.16),_transparent_28%),radial-gradient(circle_at_top_right,_rgba(99,102,241,0.12),_transparent_24%),linear-gradient(180deg,#07111f_0%,#050b14_100%)] px-4 text-slate-100">
      <motion.div animate={{ x: [0, 24, 0], y: [0, -14, 0] }} transition={{ duration: 14, repeat: Infinity, ease: 'easeInOut' }} className="pointer-events-none absolute left-[-6rem] top-20 h-72 w-72 rounded-full bg-cyan-500/10 blur-3xl" />
      <motion.div animate={{ x: [0, -20, 0], y: [0, 16, 0] }} transition={{ duration: 16, repeat: Infinity, ease: 'easeInOut' }} className="pointer-events-none absolute right-[-5rem] bottom-10 h-80 w-80 rounded-full bg-indigo-500/10 blur-3xl" />

      <motion.div initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} className="relative rounded-[2rem] border border-white/10 bg-white/[0.05] px-8 py-10 text-center shadow-[0_30px_90px_rgba(2,6,23,0.35)] backdrop-blur-2xl">
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl border border-cyan-400/15 bg-cyan-400/10 text-cyan-200">
          <Sparkles className="h-6 w-6" />
        </div>
        <Loader2 className="mx-auto mt-6 h-10 w-10 animate-spin text-cyan-300" />
        <h1 className="mt-6 text-2xl font-semibold tracking-tight text-white">Completing your secure sign-in</h1>
        <p className="mt-3 text-sm leading-7 text-slate-400">StrategAI is loading your session and will take you to the dashboard shortly.</p>
      </motion.div>
    </div>
  );
}

export default AuthCallback;
