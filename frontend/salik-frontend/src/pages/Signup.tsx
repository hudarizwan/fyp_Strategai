import { useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, CheckCircle2, Eye, EyeOff, Mail, Sparkles, UserRound } from 'lucide-react';
import Button from '@/components/ui/Button';
import Input from '@/components/ui/Input';
import { useAuth } from '@/context/AuthContext';
import { formatAuthError } from '@/lib/auth';

function Signup() {
  const { signInWithGoogle, signUpWithEmail } = useAuth();
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
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(59,130,246,0.18),_transparent_30%),linear-gradient(180deg,#f8fbff_0%,#edf4ff_100%)] px-4 py-10 text-slate-900">
      <div className="mx-auto grid min-h-[calc(100vh-5rem)] w-full max-w-6xl items-stretch gap-6 lg:grid-cols-[0.95fr_1fr]">
        <aside className="rounded-[2rem] border border-slate-200 bg-white p-8 shadow-[0_30px_90px_rgba(15,23,42,0.08)]">
          <div className="inline-flex items-center gap-2 rounded-full bg-sky-50 px-4 py-2 text-sm font-semibold text-sky-700">
            <Sparkles className="h-4 w-4" />
            Create your account
          </div>
          <h1 className="mt-6 text-4xl font-semibold tracking-tight text-slate-950">
            Start your StrategAI evaluation journey
          </h1>
          <p className="mt-4 max-w-xl text-base leading-8 text-slate-600">
            Sign up once, then move directly into the dashboard, pricing analytics, marketing strategy, and reports.
          </p>

          <div className="mt-10 space-y-4">
            {[
              'Sign up with email/password or continue with Google',
              'Supabase Auth keeps your session and tokens refreshed',
              'Your existing dashboard remains unchanged after login',
            ].map((item) => (
              <div key={item} className="flex items-start gap-3 rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <div className="mt-0.5 flex h-8 w-8 items-center justify-center rounded-full bg-sky-100 text-sky-700">
                  <CheckCircle2 className="h-4 w-4" />
                </div>
                <p className="text-sm leading-7 text-slate-600">{item}</p>
              </div>
            ))}
          </div>
        </aside>

        <section className="flex items-center">
          <form
            onSubmit={handleSubmit}
            className="w-full rounded-[2rem] border border-slate-200 bg-white p-8 shadow-[0_30px_90px_rgba(15,23,42,0.1)]"
          >
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.28em] text-sky-700">Signup</p>
              <h2 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">
                Create your StrategAI account
              </h2>
              <p className="mt-3 text-sm leading-7 text-slate-600">
                Use your name, email, and password, or connect through Google OAuth.
              </p>
            </div>

            <div className="mt-8 space-y-5">
              <label className="block">
                <span className="mb-2 block text-sm font-medium text-slate-700">Full Name</span>
                <div className="relative">
                  <UserRound className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                  <Input
                    type="text"
                    value={fullName}
                    onChange={(event) => setFullName(event.target.value)}
                    placeholder="Your full name"
                    className="pl-10 text-slate-900 placeholder:text-slate-400"
                    required
                  />
                </div>
              </label>

              <label className="block">
                <span className="mb-2 block text-sm font-medium text-slate-700">Email</span>
                <div className="relative">
                  <Mail className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                  <Input
                    type="email"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    placeholder="you@example.com"
                    className="pl-10 text-slate-900 placeholder:text-slate-400"
                    required
                  />
                </div>
              </label>

              <label className="block">
                <span className="mb-2 block text-sm font-medium text-slate-700">Password</span>
                <div className="relative">
                  <Eye className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                  <Input
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    placeholder="Create a password"
                    className="pl-10 pr-12 text-slate-900 placeholder:text-slate-400"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((current) => !current)}
                    className="absolute inset-y-0 right-0 flex items-center px-3 text-slate-400 transition hover:text-slate-700"
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </label>

              <label className="block">
                <span className="mb-2 block text-sm font-medium text-slate-700">Confirm Password</span>
                <div className="relative">
                  <Eye className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                  <Input
                    type={showConfirmPassword ? 'text' : 'password'}
                    value={confirmPassword}
                    onChange={(event) => setConfirmPassword(event.target.value)}
                    placeholder="Confirm your password"
                    className="pl-10 pr-12 text-slate-900 placeholder:text-slate-400"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword((current) => !current)}
                    className="absolute inset-y-0 right-0 flex items-center px-3 text-slate-400 transition hover:text-slate-700"
                    aria-label={showConfirmPassword ? 'Hide confirm password' : 'Show confirm password'}
                  >
                    {showConfirmPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </label>

              <label className="flex items-start gap-2 text-sm text-slate-600">
                <input
                  type="checkbox"
                  checked={acceptedTerms}
                  onChange={(event) => setAcceptedTerms(event.target.checked)}
                  className="mt-1 h-4 w-4 rounded border-slate-300 text-sky-600 focus:ring-sky-500"
                />
                <span>I agree to the terms and understand this account is for StrategAI access.</span>
              </label>
            </div>

            {error && (
              <div className="mt-5 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                {error}
              </div>
            )}

            {success && (
              <div className="mt-5 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
                {success}
              </div>
            )}

            <div className="mt-8 flex flex-col gap-3">
              <Button type="submit" size="lg" className="w-full justify-center bg-slate-900 text-white">
                {loading ? 'Creating account...' : 'Create Account'}
              </Button>
              <button
                type="button"
                onClick={() => {
                  setError(null);
                  void signInWithGoogle();
                }}
                className="inline-flex items-center justify-center gap-2 rounded-full border border-slate-200 bg-white px-6 py-3 text-sm font-semibold text-slate-700 shadow-sm transition hover:-translate-y-0.5 hover:border-sky-200 hover:text-slate-900"
              >
                Continue with Google
                <ArrowRight className="h-4 w-4" />
              </button>
            </div>

            <p className="mt-6 text-center text-sm text-slate-600">
              Already have an account?{' '}
              <Link to="/login" className="font-semibold text-sky-700 hover:text-sky-800">
                Sign in
              </Link>
            </p>
          </form>
        </section>
      </div>
    </div>
  );
}

export default Signup;



