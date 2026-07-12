import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Loader2, Sparkles } from 'lucide-react';
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
    <div className="flex min-h-screen items-center justify-center bg-[radial-gradient(circle_at_top_left,_rgba(14,165,233,0.18),_transparent_30%),linear-gradient(180deg,#f8fbff_0%,#edf4ff_100%)] px-4 text-slate-900">
      <div className="rounded-[2rem] border border-slate-200 bg-white px-8 py-10 text-center shadow-[0_30px_90px_rgba(15,23,42,0.1)]">
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-sky-50 text-sky-700">
          <Sparkles className="h-6 w-6" />
        </div>
        <Loader2 className="mx-auto mt-6 h-10 w-10 animate-spin text-sky-600" />
        <h1 className="mt-6 text-2xl font-semibold tracking-tight text-slate-950">
          Completing your secure sign-in
        </h1>
        <p className="mt-3 text-sm leading-7 text-slate-600">
          StrategAI is loading your session and will take you to the dashboard shortly.
        </p>
      </div>
    </div>
  );
}

export default AuthCallback;

