import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  ArrowRight,
  BadgeCheck,
  BarChart3,
  Brain,
  FileText,
  Gauge,
  Megaphone,
  Search,
  ShieldCheck,
  Sparkles,
  Target,
  TrendingUp,
  Workflow,
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';

const features = [
  {
    icon: Search,
    title: 'AI Product Scraping',
    description: 'Collects wholesale and retail market evidence from the supported sources.',
  },
  {
    icon: Brain,
    title: 'NLP Product Clustering',
    description: 'Normalizes listing noise into cleaner product groups for analysis.',
  },
  {
    icon: BarChart3,
    title: 'Pricing Intelligence',
    description: 'Highlights recommended buy and sell prices with explainable confidence.',
  },
  {
    icon: Megaphone,
    title: 'Marketing Intelligence',
    description: 'Shapes launch strategy from live market conditions and risk signals.',
  },
  {
    icon: ShieldCheck,
    title: 'Business Decision Support',
    description: 'Combines pricing, opportunity, and MCB governance into one view.',
  },
  {
    icon: FileText,
    title: 'PDF Reporting',
    description: 'Exports concise reports for presentation, review, and evaluation.',
  },
];

const workflow = [
  'Made-in-China',
  'Daraz',
  'Scraper',
  'NLP',
  'Analytics',
  'Marketing AI',
  'Decision Agent',
  'Reports',
];

const screenshots = [
  {
    title: 'Results',
    note: 'Recommended buy, sell, and observed market spread in one place.',
    accent: 'from-cyan-500/20 to-blue-500/10',
  },
  {
    title: 'Analytics',
    note: 'Price ranges, supplier intelligence, and explainable recommendations.',
    accent: 'from-blue-500/20 to-indigo-500/10',
  },
  {
    title: 'Marketing Strategy',
    note: 'Launch scope, channels, and decision rationale aligned to quality.',
    accent: 'from-indigo-500/20 to-sky-500/10',
  },
];

function Landing() {
  const { signInWithGoogle } = useAuth();

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(14,165,233,0.16),_transparent_30%),radial-gradient(circle_at_top_right,_rgba(79,70,229,0.14),_transparent_28%),linear-gradient(180deg,#f8fbff_0%,#edf4ff_100%)] text-slate-900">
      <header className="sticky top-0 z-40 border-b border-slate-200/80 bg-white/80 backdrop-blur-xl">
        <div className="mx-auto flex w-full max-w-7xl items-center justify-between px-6 py-4 lg:px-8">
          <Link to="/" className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-sky-500 to-indigo-600 text-white shadow-lg shadow-sky-500/20">
              <Brain className="h-6 w-6" />
            </div>
            <div>
              <div className="text-lg font-semibold tracking-tight text-slate-900">StrategAI</div>
              <div className="text-xs text-slate-500">AI e-commerce intelligence</div>
            </div>
          </Link>

          <nav className="hidden items-center gap-6 text-sm font-medium text-slate-600 md:flex">
            <a href="#features" className="transition-colors hover:text-slate-900">Features</a>
            <a href="#workflow" className="transition-colors hover:text-slate-900">How It Works</a>
            <a href="#screenshots" className="transition-colors hover:text-slate-900">Screenshots</a>
            <a href="#footer" className="transition-colors hover:text-slate-900">Contact</a>
          </nav>

          <div className="flex items-center gap-3">
            <Link
              to="/login"
              className="hidden rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm transition hover:-translate-y-0.5 hover:border-sky-200 hover:text-slate-900 md:inline-flex"
            >
              Sign in
            </Link>
            <Link
              to="/signup"
              className="rounded-full bg-slate-900 px-4 py-2 text-sm font-medium text-white shadow-lg shadow-slate-900/15 transition hover:-translate-y-0.5 hover:bg-slate-800"
            >
              Get Started
            </Link>
          </div>
        </div>
      </header>

      <main className="mx-auto flex w-full max-w-7xl flex-col gap-24 px-6 py-14 lg:px-8">
        <section className="grid items-center gap-12 lg:grid-cols-[1.05fr_0.95fr]">
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.55 }}
            className="max-w-2xl"
          >
            <div className="inline-flex items-center gap-2 rounded-full border border-sky-200 bg-sky-50 px-4 py-2 text-sm font-medium text-sky-700 shadow-sm">
              <Sparkles className="h-4 w-4" />
              AI-powered product intelligence for smarter e-commerce decisions
            </div>

            <h1 className="mt-6 text-5xl font-semibold tracking-tight text-slate-950 md:text-7xl">
              Find profitable products with explainable AI business intelligence.
            </h1>

            <p className="mt-6 max-w-xl text-lg leading-8 text-slate-600 md:text-xl">
              StrategAI compares wholesale and retail markets, recommends pricing, and turns market evidence into launch-ready strategy for Pakistani e-commerce.
            </p>

            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <Link
                to="/signup"
                className="inline-flex items-center justify-center gap-2 rounded-full bg-slate-900 px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-slate-900/15 transition hover:-translate-y-0.5 hover:bg-slate-800"
              >
                Start Using StrategAI
                <ArrowRight className="h-4 w-4" />
              </Link>
              <button
                type="button"
                onClick={() => {
                  void signInWithGoogle();
                }}
                className="inline-flex items-center justify-center gap-2 rounded-full border border-slate-200 bg-white px-6 py-3 text-sm font-semibold text-slate-700 shadow-sm transition hover:-translate-y-0.5 hover:border-sky-200 hover:text-slate-900"
              >
                Continue with Google
              </button>
              <a
                href="#screenshots"
                className="inline-flex items-center justify-center gap-2 rounded-full border border-transparent px-6 py-3 text-sm font-semibold text-slate-600 transition hover:text-slate-900"
              >
                Watch Demo
              </a>
            </div>

            <div className="mt-10 grid grid-cols-2 gap-4 sm:grid-cols-4">
              {[
                ['Wholesale', 'Made-in-China'],
                ['Retail', 'Daraz'],
                ['Analytics', 'Explainable'],
                ['Reports', 'PDF export'],
              ].map(([label, value]) => (
                <div
                  key={label}
                  className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"
                >
                  <div className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">
                    {label}
                  </div>
                  <div className="mt-2 text-sm font-medium text-slate-900">{value}</div>
                </div>
              ))}
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 30, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{ duration: 0.65, delay: 0.08 }}
            className="relative"
          >
            <div className="absolute -inset-6 rounded-[2rem] bg-gradient-to-br from-sky-400/20 via-transparent to-indigo-500/20 blur-3xl" />
            <div className="relative overflow-hidden rounded-[2rem] border border-white/70 bg-white/85 p-6 shadow-[0_30px_90px_rgba(15,23,42,0.14)] backdrop-blur-xl">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-sm font-medium text-slate-500">Business intelligence snapshot</div>
                  <div className="text-2xl font-semibold tracking-tight text-slate-950">StrategAI Dashboard</div>
                </div>
                <div className="rounded-full bg-sky-50 px-3 py-1 text-xs font-semibold text-sky-700">
                  Live analysis
                </div>
              </div>

              <div className="mt-6 grid gap-4 sm:grid-cols-2">
                {[
                  { label: 'Recommended Buy', value: 'PKR 5,320', hint: 'Model-led sourcing target' },
                  { label: 'Recommended Sell', value: 'PKR 6,815', hint: 'Model-led sales target' },
                  { label: 'Confidence', value: 'High', hint: 'Explainable and traceable' },
                  { label: 'Opportunity Score', value: '87/100', hint: 'Competitive but viable' },
                ].map((item) => (
                  <div key={item.label} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                    <div className="text-sm font-medium text-slate-500">{item.label}</div>
                    <div className="mt-2 text-2xl font-semibold tracking-tight text-slate-950">{item.value}</div>
                    <div className="mt-1 text-sm text-slate-500">{item.hint}</div>
                  </div>
                ))}
              </div>

              <div className="mt-6 rounded-2xl border border-sky-100 bg-gradient-to-br from-sky-50 to-indigo-50 p-5">
                <div className="flex items-center justify-between">
                  <div className="text-sm font-semibold text-slate-700">Pricing intelligence</div>
                  <Target className="h-5 w-5 text-sky-600" />
                </div>
                <div className="mt-4 flex items-end gap-3">
                  {[22, 42, 30, 56, 44, 68, 84, 76].map((height, index) => (
                    <div
                      key={index}
                      className="flex-1 rounded-t-2xl bg-gradient-to-t from-sky-500 to-indigo-500"
                      style={{ height: `${height}px` }}
                    />
                  ))}
                </div>
                <div className="mt-4 flex items-center justify-between text-xs text-slate-500">
                  <span>Observed market range</span>
                  <span>Recommended price band</span>
                </div>
              </div>
            </div>
          </motion.div>
        </section>

        <section id="features" className="space-y-8">
          <div className="max-w-2xl">
            <div className="text-sm font-semibold uppercase tracking-[0.28em] text-sky-700">
              Features
            </div>
            <h2 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950 md:text-4xl">
              Everything StrategAI needs to support a business decision
            </h2>
            <p className="mt-4 text-base leading-7 text-slate-600">
              The platform transforms raw market evidence into pricing, marketing, and governance insight without changing the core dashboard workflow.
            </p>
          </div>

          <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
            {features.map((feature) => {
              const Icon = feature.icon;

              return (
                <div
                  key={feature.title}
                  className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm transition hover:-translate-y-1 hover:shadow-[0_20px_50px_rgba(15,23,42,0.09)]"
                >
                  <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-sky-50 text-sky-700">
                    <Icon className="h-6 w-6" />
                  </div>
                  <h3 className="mt-5 text-xl font-semibold text-slate-950">{feature.title}</h3>
                  <p className="mt-3 text-sm leading-7 text-slate-600">{feature.description}</p>
                </div>
              );
            })}
          </div>
        </section>

        <section id="workflow" className="rounded-[2rem] border border-slate-200 bg-white p-8 shadow-sm lg:p-10">
          <div className="max-w-2xl">
            <div className="text-sm font-semibold uppercase tracking-[0.28em] text-sky-700">
              How It Works
            </div>
            <h2 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950 md:text-4xl">
              A clear workflow from market scrape to final recommendation
            </h2>
          </div>

          <div className="mt-8 grid gap-4 lg:grid-cols-8">
            {workflow.map((step, index) => (
              <div key={step} className="flex flex-col items-center gap-3 text-center">
                <div className="flex h-16 w-full items-center justify-center rounded-2xl border border-slate-200 bg-slate-50 px-3 text-sm font-semibold text-slate-800">
                  {step}
                </div>
                {index < workflow.length - 1 && (
                  <ArrowRight className="hidden h-4 w-4 text-sky-500 lg:block" />
                )}
              </div>
            ))}
          </div>
        </section>

        <section className="grid gap-5 lg:grid-cols-3">
          {[
            {
              title: 'Why it matters',
              icon: Gauge,
              description: 'Shows whether the product is worth investing in before the user spends time or capital.',
            },
            {
              title: 'Decision clarity',
              icon: BadgeCheck,
              description: 'Every recommendation keeps its reasoning and confidence visible instead of hiding behind a model.',
            },
            {
              title: 'Launch readiness',
              icon: TrendingUp,
              description: 'Turns raw market spread into actionable go-to-market advice for Pakistani sellers.',
            },
          ].map((benefit) => {
            const Icon = benefit.icon;

            return (
              <div
                key={benefit.title}
                className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm"
              >
                <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-sky-500 to-indigo-600 text-white">
                  <Icon className="h-5 w-5" />
                </div>
                <h3 className="mt-5 text-xl font-semibold text-slate-950">{benefit.title}</h3>
                <p className="mt-3 text-sm leading-7 text-slate-600">{benefit.description}</p>
              </div>
            );
          })}
        </section>

        <section id="screenshots" className="space-y-8">
          <div className="max-w-2xl">
            <div className="text-sm font-semibold uppercase tracking-[0.28em] text-sky-700">
              Screenshots
            </div>
            <h2 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950 md:text-4xl">
              Real StrategAI views, presented as a clean product preview
            </h2>
          </div>

          <div className="grid gap-5 lg:grid-cols-3">
            {screenshots.map((shot) => (
              <div
                key={shot.title}
                className="overflow-hidden rounded-[2rem] border border-slate-200 bg-white shadow-sm"
              >
                <div className={`h-56 bg-gradient-to-br ${shot.accent} p-6`}>
                  <div className="flex h-full flex-col justify-between rounded-[1.5rem] border border-white/70 bg-white/70 p-4 backdrop-blur-xl">
                    <div className="flex items-center justify-between">
                      <div className="text-sm font-semibold text-slate-700">{shot.title}</div>
                      <div className="rounded-full bg-sky-100 px-2 py-1 text-[11px] font-semibold text-sky-700">
                        StrategAI
                      </div>
                    </div>
                    <div className="space-y-3">
                      <div className="grid grid-cols-3 gap-3">
                        <div className="rounded-2xl bg-slate-100 p-3">
                          <div className="text-[11px] text-slate-500">Metric</div>
                          <div className="mt-1 text-sm font-semibold text-slate-900">87/100</div>
                        </div>
                        <div className="rounded-2xl bg-slate-100 p-3">
                          <div className="text-[11px] text-slate-500">Risk</div>
                          <div className="mt-1 text-sm font-semibold text-slate-900">Medium</div>
                        </div>
                        <div className="rounded-2xl bg-slate-100 p-3">
                          <div className="text-[11px] text-slate-500">Mode</div>
                          <div className="mt-1 text-sm font-semibold text-slate-900">Balanced</div>
                        </div>
                      </div>
                      <div className="h-20 rounded-2xl bg-gradient-to-r from-sky-500/90 via-indigo-500/80 to-cyan-500/90 opacity-90" />
                    </div>
                  </div>
                </div>
                <div className="p-6">
                  <h3 className="text-xl font-semibold text-slate-950">{shot.title}</h3>
                  <p className="mt-2 text-sm leading-7 text-slate-600">{shot.note}</p>
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-[2rem] bg-slate-950 px-8 py-10 text-white shadow-[0_30px_90px_rgba(15,23,42,0.2)] lg:px-12">
          <div className="grid gap-8 lg:grid-cols-[1fr_auto] lg:items-center">
            <div>
              <div className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/5 px-4 py-2 text-sm font-medium text-slate-200">
                <Workflow className="h-4 w-4" />
                Ready to discover profitable products?
              </div>
              <h2 className="mt-5 text-3xl font-semibold tracking-tight md:text-4xl">
                Turn market data into a confident product decision.
              </h2>
              <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-300 md:text-base">
                StrategAI keeps the analytics, marketing, and decision flow aligned so you can present a complete AI business story during your evaluation.
              </p>
            </div>
            <div className="flex flex-col gap-3 sm:flex-row lg:flex-col">
              <Link
                to="/signup"
                className="inline-flex items-center justify-center gap-2 rounded-full bg-white px-6 py-3 text-sm font-semibold text-slate-900 transition hover:-translate-y-0.5 hover:bg-slate-100"
              >
                Start Using StrategAI
                <ArrowRight className="h-4 w-4" />
              </Link>
              <Link
                to="/login"
                className="inline-flex items-center justify-center gap-2 rounded-full border border-white/15 bg-white/5 px-6 py-3 text-sm font-semibold text-white transition hover:-translate-y-0.5 hover:bg-white/10"
              >
                Sign in
              </Link>
            </div>
          </div>
        </section>
      </main>

      <footer id="footer" className="border-t border-slate-200 bg-white/90">
        <div className="mx-auto grid w-full max-w-7xl gap-8 px-6 py-10 text-sm text-slate-600 lg:grid-cols-3 lg:px-8">
          <div>
            <div className="text-base font-semibold text-slate-950">StrategAI</div>
            <p className="mt-3 max-w-sm leading-7">
              An explainable AI e-commerce profit optimization platform for wholesale, retail, pricing, and marketing intelligence.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <a href="#features" className="transition hover:text-slate-900">Features</a>
            <a href="#workflow" className="transition hover:text-slate-900">How It Works</a>
            <a href="#screenshots" className="transition hover:text-slate-900">Screenshots</a>
            <a href="https://github.com/hudarizwan/fyp_Strategai" target="_blank" rel="noreferrer" className="transition hover:text-slate-900">GitHub</a>
          </div>
          <div className="rounded-3xl border border-slate-200 bg-slate-50 p-5">
            <div className="text-base font-semibold text-slate-950">Contact</div>
            <p className="mt-3 leading-7">
              For evaluation, demos, and documentation, connect this landing page to your project report and presentation materials.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default Landing;


