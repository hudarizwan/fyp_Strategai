import { useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Eye, EyeOff, LockKeyhole, Mail, Sparkles } from 'lucide-react';
import { motion } from 'framer-motion';
import Button from '@/components/ui/Button';
import Input from '@/components/ui/Input';
import { useAuth } from '@/context/AuthContext';
import { formatAuthError } from '@/lib/auth';

const containerVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.08, delayChildren: 0.08 } },
};

const panelVariants = {
  hidden: { opacity: 0, y: 18 },
  visible: { opacity: 1, y: 0 },
};

function Login() {
  const { signInWithEmail } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(true);
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setLoading(true);
    setError(null);

    try {
      await signInWithEmail(email, password);
      window.localStorage.setItem('strategai.rememberMe', String(rememberMe));
      navigate('/', { replace: true });
    } catch (submitError) {
      setError(formatAuthError(submitError));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative min-h-screen overflow-hidden bg-[radial-gradient(circle_at_top_left,_rgba(14,165,233,0.16),_transparent_28%),radial-gradient(circle_at_top_right,_rgba(99,102,241,0.12),_transparent_24%),linear-gradient(180deg,#07111f_0%,#050b14_100%)] px-4 py-10 text-slate-100">
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <motion.div animate={{ x: [0, 30, 0], y: [0, -16, 0] }} transition={{ duration: 14, repeat: Infinity, ease: 'easeInOut' }} className="absolute left-[-6rem] top-16 h-72 w-72 rounded-full bg-cyan-500/10 blur-3xl" />
        <motion.div animate={{ x: [0, -24, 0], y: [0, 18, 0] }} transition={{ duration: 16, repeat: Infinity, ease: 'easeInOut' }} className="absolute right-[-5rem] top-28 h-80 w-80 rounded-full bg-indigo-500/10 blur-3xl" />
      </div>

      <motion.div variants={containerVariants} initial="hidden" animate="visible" className="relative mx-auto grid min-h-[calc(100vh-5rem)] w-full max-w-6xl items-stretch gap-6 lg:grid-cols-[1.04fr_0.96fr]">
        <motion.aside variants={panelVariants} className="flex h-full flex-col rounded-[2rem] border border-white/10 bg-white/[0.045] p-8 shadow-[0_30px_90px_rgba(2,6,23,0.35)] backdrop-blur-2xl">
          <div className="inline-flex items-center gap-2 rounded-full border border-cyan-400/15 bg-cyan-400/10 px-4 py-2 text-sm font-semibold text-cyan-200">
            <Sparkles className="h-4 w-4" />
            Welcome back
          </div>
          <h1 className="mt-6 max-w-xl text-4xl font-semibold tracking-tight text-white md:text-5xl">
            Sign in to continue your StrategAI workspace
          </h1>
          <p className="mt-4 max-w-xl text-base leading-8 text-slate-300">
            Access your dashboard, results, analytics, and strategy pages from one secure Supabase session.
          </p>

          <div className="mt-10 flex-1 space-y-4">
            {[
              'Persistent sessions with automatic token refresh',
              'Protected access to the existing StrategAI dashboard',
              'Smooth handoff between landing page and workspace',
            ].map((item) => (
              <div key={item} className="flex items-start gap-3 rounded-2xl border border-white/10 bg-slate-950/40 p-4 transition hover:border-cyan-400/15 hover:bg-white/[0.06]">
                <div className="mt-0.5 flex h-8 w-8 items-center justify-center rounded-full bg-cyan-400/10 text-cyan-200">
                  <LockKeyhole className="h-4 w-4" />
                </div>
                <p className="text-sm leading-7 text-slate-300">{item}</p>
              </div>
            ))}
          </div>
        </motion.aside>

        <motion.section variants={panelVariants} className="flex h-full items-stretch">
          <form onSubmit={handleSubmit} className="flex w-full flex-col rounded-[2rem] border border-white/10 bg-white/[0.055] p-8 shadow-[0_30px_90px_rgba(2,6,23,0.38)] backdrop-blur-2xl">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.28em] text-cyan-300">Login</p>
              <h2 className="mt-3 text-3xl font-semibold tracking-tight text-white">Sign in to StrategAI</h2>
              <p className="mt-3 text-sm leading-7 text-slate-400">Use your email to access the full app.</p>
            </div>

            <div className="mt-8 space-y-5">
              <label className="block">
                <span className="mb-2 block text-sm font-medium text-slate-300">Email</span>
                <div className="relative">
                  <Mail className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
                  <Input type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@example.com" className="pl-10 text-slate-100 placeholder:text-slate-500" required />
                </div>
              </label>

              <label className="block">
                <span className="mb-2 block text-sm font-medium text-slate-300">Password</span>
                <div className="relative">
                  <LockKeyhole className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
                  <Input type={showPassword ? 'text' : 'password'} value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Enter your password" className="pl-10 pr-12 text-slate-100 placeholder:text-slate-500" required />
                  <button type="button" onClick={() => setShowPassword((current) => !current)} className="absolute inset-y-0 right-0 flex items-center px-3 text-slate-500 transition hover:text-slate-200" aria-label={showPassword ? 'Hide password' : 'Show password'}>
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </label>

              <div className="flex items-center justify-between gap-4">
                <label className="flex items-center gap-2 text-sm text-slate-400">
                  <input type="checkbox" checked={rememberMe} onChange={(event) => setRememberMe(event.target.checked)} className="h-4 w-4 rounded border-slate-600 bg-transparent text-cyan-500 focus:ring-cyan-500" />
                  Remember me
                </label>
                <Link to="/forgot-password" className="text-sm font-medium text-cyan-300 hover:text-cyan-200">Forgot password?</Link>
              </div>
            </div>

            <div className="mt-4 min-h-14">
              {error && <div className="rounded-2xl border border-red-400/20 bg-red-500/10 px-4 py-3 text-sm text-red-200">{error}</div>}
            </div>

            <div className="mt-6 flex flex-col gap-3">
              <Button type="submit" size="lg" className="w-full justify-center">
                {loading ? 'Signing in...' : 'Login'}
              </Button>
            </div>

            <p className="mt-auto pt-6 text-center text-sm text-slate-400">
              Don&apos;t have an account?{' '}
              <Link to="/signup" className="font-semibold text-cyan-300 hover:text-cyan-200">Sign up</Link>
            </p>
          </form>
        </motion.section>
      </motion.div>
    </div>
  );
}

export default Login;
