import { useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { CheckCircle2, Eye, EyeOff, Mail, Sparkles, UserRound } from 'lucide-react';
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

function Signup() {
  const { signUpWithEmail } = useAuth();
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [acceptedTerms, setAcceptedTerms] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(null);

    if (password !== confirmPassword) {
      setLoading(false);
      setError('Passwords do not match.');
      return;
    }

    if (!acceptedTerms) {
      setLoading(false);
      setError('Please accept the terms to create your account.');
      return;
    }

    try {
      const result = await signUpWithEmail(fullName, email, password);
      setSuccess(result.message);
      window.localStorage.setItem('strategai.signup.name', fullName.trim());
    } catch (submitError) {
      setError(formatAuthError(submitError));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative min-h-screen overflow-hidden bg-[radial-gradient(circle_at_top_left,_rgba(59,130,246,0.14),_transparent_28%),radial-gradient(circle_at_top_right,_rgba(14,165,233,0.12),_transparent_24%),linear-gradient(180deg,#07111f_0%,#050b14_100%)] px-4 py-10 text-slate-100">
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <motion.div animate={{ x: [0, 26, 0], y: [0, -14, 0] }} transition={{ duration: 15, repeat: Infinity, ease: 'easeInOut' }} className="absolute left-[-6rem] top-16 h-72 w-72 rounded-full bg-cyan-500/10 blur-3xl" />
        <motion.div animate={{ x: [0, -22, 0], y: [0, 18, 0] }} transition={{ duration: 17, repeat: Infinity, ease: 'easeInOut' }} className="absolute right-[-5rem] top-28 h-80 w-80 rounded-full bg-indigo-500/10 blur-3xl" />
      </div>

      <motion.div variants={containerVariants} initial="hidden" animate="visible" className="relative mx-auto grid min-h-[calc(100vh-5rem)] w-full max-w-6xl items-stretch gap-6 lg:grid-cols-[0.98fr_1.02fr]">
        <motion.aside variants={panelVariants} className="flex h-full flex-col rounded-[2rem] border border-white/10 bg-white/[0.045] p-8 shadow-[0_30px_90px_rgba(2,6,23,0.35)] backdrop-blur-2xl">
          <div className="inline-flex items-center gap-2 rounded-full border border-cyan-400/15 bg-cyan-400/10 px-4 py-2 text-sm font-semibold text-cyan-200">
            <Sparkles className="h-4 w-4" />
            Create your account
          </div>
          <h1 className="mt-6 text-4xl font-semibold tracking-tight text-white md:text-5xl">
            Start your StrategAI evaluation journey
          </h1>
          <p className="mt-4 max-w-xl text-base leading-8 text-slate-300">
            Sign up once, then move directly into the dashboard, pricing analytics, strategy, and reports.
          </p>

          <div className="mt-10 flex-1 space-y-4">
            {[
              'Email/password sign up for your StrategAI account',
              'Supabase Auth keeps your session and tokens refreshed',
              'Your existing dashboard remains unchanged after login',
            ].map((item) => (
              <div key={item} className="flex items-start gap-3 rounded-2xl border border-white/10 bg-slate-950/40 p-4 transition hover:border-cyan-400/15 hover:bg-white/[0.06]">
                <div className="mt-0.5 flex h-8 w-8 items-center justify-center rounded-full bg-cyan-400/10 text-cyan-200">
                  <CheckCircle2 className="h-4 w-4" />
                </div>
                <p className="text-sm leading-7 text-slate-300">{item}</p>
              </div>
            ))}
          </div>
        </motion.aside>

        <motion.section variants={panelVariants} className="flex h-full items-stretch">
          <form onSubmit={handleSubmit} className="flex w-full flex-col rounded-[2rem] border border-white/10 bg-white/[0.055] p-8 shadow-[0_30px_90px_rgba(2,6,23,0.38)] backdrop-blur-2xl">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.28em] text-cyan-300">Signup</p>
              <h2 className="mt-3 text-3xl font-semibold tracking-tight text-white">Create your StrategAI account</h2>
              <p className="mt-3 text-sm leading-7 text-slate-400">Use your name, email, and password to create your account.</p>
            </div>

            <div className="mt-8 space-y-5">
              <label className="block">
                <span className="mb-2 block text-sm font-medium text-slate-300">Full Name</span>
                <div className="relative">
                  <UserRound className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
                  <Input type="text" value={fullName} onChange={(event) => setFullName(event.target.value)} placeholder="Your full name" className="pl-10 text-slate-100 placeholder:text-slate-500" required />
                </div>
              </label>

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
                  <Eye className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
                  <Input type={showPassword ? 'text' : 'password'} value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Create a password" className="pl-10 pr-12 text-slate-100 placeholder:text-slate-500" required />
                  <button type="button" onClick={() => setShowPassword((current) => !current)} className="absolute inset-y-0 right-0 flex items-center px-3 text-slate-500 transition hover:text-slate-200" aria-label={showPassword ? 'Hide password' : 'Show password'}>
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </label>

              <label className="block">
                <span className="mb-2 block text-sm font-medium text-slate-300">Confirm Password</span>
                <div className="relative">
                  <Eye className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
                  <Input type={showConfirmPassword ? 'text' : 'password'} value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} placeholder="Confirm your password" className="pl-10 pr-12 text-slate-100 placeholder:text-slate-500" required />
                  <button type="button" onClick={() => setShowConfirmPassword((current) => !current)} className="absolute inset-y-0 right-0 flex items-center px-3 text-slate-500 transition hover:text-slate-200" aria-label={showConfirmPassword ? 'Hide confirm password' : 'Show confirm password'}>
                    {showConfirmPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </label>

              <label className="flex items-start gap-2 text-sm text-slate-400">
                <input type="checkbox" checked={acceptedTerms} onChange={(event) => setAcceptedTerms(event.target.checked)} className="mt-1 h-4 w-4 rounded border-slate-600 bg-transparent text-cyan-500 focus:ring-cyan-500" />
                <span>I agree to the terms and understand this account is for StrategAI access.</span>
              </label>
            </div>

            <div className="mt-4 min-h-14">
              {error && <div className="rounded-2xl border border-red-400/20 bg-red-500/10 px-4 py-3 text-sm text-red-200">{error}</div>}
              {success && <div className="rounded-2xl border border-emerald-400/20 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-200">{success}</div>}
            </div>

            <div className="mt-6 flex flex-col gap-3">
              <Button type="submit" size="lg" className="w-full justify-center">
                {loading ? 'Creating account...' : 'Create Account'}
              </Button>
            </div>

            <p className="mt-auto pt-6 text-center text-sm text-slate-400">
              Already have an account?{' '}
              <Link to="/login" className="font-semibold text-cyan-300 hover:text-cyan-200">Sign in</Link>
            </p>
          </form>
        </motion.section>
      </motion.div>
    </div>
  );
}

export default Signup;
