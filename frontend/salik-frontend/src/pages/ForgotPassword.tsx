import { useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, Mail, Sparkles } from 'lucide-react';
import Button from '@/components/ui/Button';
import Input from '@/components/ui/Input';
import { useAuth } from '@/context/AuthContext';
import { formatAuthError } from '@/lib/auth';

function ForgotPassword() {
  const { sendPasswordResetEmail } = useAuth();
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const result = await sendPasswordResetEmail(email);
      setSuccess(result.message);
    } catch (submitError) {
      setError(formatAuthError(submitError));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(14,165,233,0.18),_transparent_30%),linear-gradient(180deg,#f8fbff_0%,#edf4ff_100%)] px-4 py-10 text-slate-900">
      <div className="mx-auto grid min-h-[calc(100vh-5rem)] w-full max-w-4xl items-center">
        <form
          onSubmit={handleSubmit}
          className="rounded-[2rem] border border-slate-200 bg-white p-8 shadow-[0_30px_90px_rgba(15,23,42,0.1)]"
        >
          <div className="inline-flex items-center gap-2 rounded-full bg-sky-50 px-4 py-2 text-sm font-semibold text-sky-700">
            <Sparkles className="h-4 w-4" />
            Password recovery
          </div>
          <h1 className="mt-6 text-4xl font-semibold tracking-tight text-slate-950">
            Reset your StrategAI password
          </h1>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-600">
            Enter the email address linked to your account. Supabase will send a secure password reset link.
          </p>

          <div className="mt-8 max-w-xl">
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

          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <Button type="submit" size="lg" className="justify-center bg-slate-900 text-white sm:w-auto">
              {loading ? 'Sending reset link...' : 'Send Reset Link'}
            </Button>
            <Link
              to="/login"
              className="inline-flex items-center justify-center gap-2 rounded-full border border-slate-200 bg-white px-6 py-3 text-sm font-semibold text-slate-700 shadow-sm transition hover:-translate-y-0.5 hover:border-sky-200 hover:text-slate-900"
            >
              Back to login
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </form>
      </div>
    </div>
  );
}

export default ForgotPassword;



