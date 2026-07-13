import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ArrowRight,
  BadgeCheck,
  BarChart3,
  Brain,
  ChevronRight,
  FileText,
  Gauge,
  Megaphone,
  Search,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  Workflow,
  LineChart,
} from 'lucide-react';

const features = [
  { icon: Search, title: 'Market Scraping', description: 'Collects wholesale and retail evidence from the supported sources.' },
  { icon: Brain, title: 'Product Clustering', description: 'Normalizes listing noise into cleaner product groups for analysis.' },
  { icon: BarChart3, title: 'Pricing Intelligence', description: 'Highlights recommended buy and sell prices with explainable confidence.' },
  { icon: Megaphone, title: 'Marketing Intelligence', description: 'Shapes launch strategy from live market conditions and risk signals.' },
  { icon: ShieldCheck, title: 'Decision Support', description: 'Combines pricing, opportunity, and governance into one view.' },
  { icon: FileText, title: 'PDF Reporting', description: 'Exports concise reports for presentation, review, and evaluation.' },
];

const workflow = [
  'Made-in-China',
  'Daraz',
  'Scraper',
  'NLP',
  'Analytics',
  'Marketing',
  'Decision',
  'Report',
];

const previewSlides = [
  {
    title: 'Dashboard snapshot',
    eyebrow: 'Overview',
    description: 'A clean executive view of pricing, opportunity, and confidence before drilling into details.',
    accent: 'from-cyan-400/20 via-sky-500/10 to-indigo-500/20',
    frame: (
      <div className="grid gap-3 sm:grid-cols-2">
        {[
          ['Recommended Buy', 'PKR 2,106', 'Model-led sourcing target'],
          ['Recommended Sell', 'PKR 2,541', 'Model-led sales target'],
          ['Confidence', '42%', 'Explainable and traceable'],
          ['Opportunity Score', '35/100', 'Competitive but viable'],
        ].map(([label, value, hint]) => (
          <div key={label} className="rounded-2xl border border-white/10 bg-slate-950/55 p-4 backdrop-blur-xl">
            <div className="text-xs font-medium uppercase tracking-[0.22em] text-slate-500">{label}</div>
            <div className="mt-2 text-2xl font-semibold text-white">{value}</div>
            <div className="mt-1 text-sm text-slate-400">{hint}</div>
          </div>
        ))}
      </div>
    ),
  },
  {
    title: 'Results and pricing',
    eyebrow: 'Pricing',
    description: 'The recommendation layer shows the selected buy/sell posture alongside observed market spread.',
    accent: 'from-indigo-400/20 via-violet-500/10 to-cyan-500/20',
    frame: (
      <div className="space-y-3">
        <div className="rounded-2xl border border-cyan-400/20 bg-cyan-500/10 p-4">
          <div className="flex items-center justify-between text-sm text-cyan-100">
            <span>Selected Posture</span>
            <span className="rounded-full border border-cyan-400/30 px-2 py-1 text-[11px] uppercase tracking-[0.2em]">Competitive</span>
          </div>
          <div className="mt-3 grid grid-cols-2 gap-3 text-white">
            <div>
              <div className="text-xs uppercase tracking-[0.2em] text-cyan-100/70">Buy</div>
              <div className="text-2xl font-semibold">PKR 2,106</div>
            </div>
            <div>
              <div className="text-xs uppercase tracking-[0.2em] text-cyan-100/70">Sell</div>
              <div className="text-2xl font-semibold">PKR 2,541</div>
            </div>
          </div>
        </div>
        <div className="grid grid-cols-3 gap-3">
          {[
            ['Observed Spread', 'PKR 2,643'],
            ['Gross Profit', 'PKR 435'],
            ['Risk', 'Low confidence'],
          ].map(([label, value]) => (
            <div key={label} className="rounded-2xl border border-white/10 bg-white/[0.05] p-4 text-left">
              <div className="text-[11px] uppercase tracking-[0.2em] text-slate-500">{label}</div>
              <div className="mt-2 text-sm font-semibold text-white">{value}</div>
            </div>
          ))}
        </div>
      </div>
    ),
  },
  {
    title: 'Marketing strategy',
    eyebrow: 'Go-to-market',
    description: 'Strategy output is aligned with the data quality and the selected pricing posture.',
    accent: 'from-sky-500/20 via-cyan-500/10 to-blue-500/20',
    frame: (
      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {['STP', 'SWOT', 'PESTEL', '4Ps'].map((item) => (
            <div key={item} className="rounded-2xl border border-white/10 bg-slate-950/55 p-4 text-center text-sm font-semibold text-white backdrop-blur-xl">
              {item}
            </div>
          ))}
        </div>
        <div className="rounded-2xl border border-white/10 bg-white/[0.05] p-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm font-semibold text-white">Budget allocation</div>
              <div className="text-xs text-slate-400">Channel mix tuned to confidence and competition</div>
            </div>
            <Sparkles className="h-5 w-5 text-cyan-300" />
          </div>
          <div className="mt-4 h-3 overflow-hidden rounded-full bg-white/5">
            <div className="h-full w-[38%] bg-gradient-to-r from-cyan-400 to-indigo-400" />
          </div>
          <div className="mt-3 flex items-center justify-between text-xs text-slate-400">
            <span>Search</span>
            <span>Social</span>
            <span>Content</span>
            <span>Influencers</span>
          </div>
        </div>
      </div>
    ),
  },
  {
    title: 'Analytics and reports',
    eyebrow: 'BI layer',
    description: 'The analytics page turns evidence into charts, with PDF export for evaluation and presentation.',
    accent: 'from-blue-500/20 via-slate-500/10 to-cyan-500/20',
    frame: (
      <div className="grid gap-3 md:grid-cols-[1.15fr_0.85fr]">
        <div className="rounded-2xl border border-white/10 bg-slate-950/55 p-4 backdrop-blur-xl">
          <div className="flex items-center justify-between">
            <div className="text-sm font-semibold text-white">Market Opportunity</div>
            <LineChart className="h-5 w-5 text-cyan-300" />
          </div>
          <div className="mt-4 grid grid-cols-5 items-end gap-2">
            {[18, 32, 28, 46, 38].map((height, index) => (
              <div key={index} className="rounded-t-2xl bg-gradient-to-t from-cyan-400 to-indigo-400" style={{ height: `${height * 2}px` }} />
            ))}
          </div>
        </div>
        <div className="space-y-3">
          <div className="rounded-2xl border border-white/10 bg-white/[0.05] p-4 text-white">
            <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Report</div>
            <div className="mt-2 text-lg font-semibold">Download PDF</div>
            <div className="mt-1 text-sm text-slate-400">Detailed analytics report for review</div>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/[0.05] p-4 text-white">
            <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Summary</div>
            <div className="mt-2 text-lg font-semibold">Explainable AI</div>
            <div className="mt-1 text-sm text-slate-400">No hidden assumptions, only market evidence</div>
          </div>
        </div>
      </div>
    ),
  },
];

function Landing() {
  const [activeSlide, setActiveSlide] = useState(0);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setActiveSlide((current) => (current + 1) % previewSlides.length);
    }, 4200);
    return () => window.clearInterval(timer);
  }, []);

  const currentSlide = previewSlides[activeSlide];

  const metrics = useMemo(
    () => [
      ['Wholesale', 'Made-in-China'],
      ['Retail', 'Daraz'],
      ['Analysis', 'Explainable'],
      ['Reports', 'PDF export'],
    ],
    []
  );

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(56,189,248,0.18),_transparent_25%),radial-gradient(circle_at_top_right,_rgba(99,102,241,0.14),_transparent_22%),linear-gradient(180deg,#040816_0%,#07111f_50%,#050b14_100%)] text-slate-100">
      <header className="sticky top-0 z-40 border-b border-white/10 bg-slate-950/75 backdrop-blur-2xl">
        <div className="mx-auto flex w-full max-w-7xl items-center justify-between px-6 py-4 lg:px-8">
          <Link to="/" className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-white/10 bg-white/8 text-cyan-300 shadow-[0_18px_50px_rgba(34,211,238,0.12)] backdrop-blur-xl">
              <Brain className="h-6 w-6" />
            </div>
            <div>
              <div className="text-lg font-semibold tracking-tight text-white">StrategAI</div>
              <div className="text-xs text-slate-400">E-commerce decision intelligence</div>
            </div>
          </Link>

          <nav className="hidden items-center gap-6 text-sm font-medium text-slate-400 md:flex">
            <a href="#features" className="transition-colors hover:text-white">Features</a>
            <a href="#workflow" className="transition-colors hover:text-white">Workflow</a>
            <a href="#preview" className="transition-colors hover:text-white">Preview</a>
            <a href="#footer" className="transition-colors hover:text-white">Contact</a>
          </nav>

          <div className="flex items-center gap-3">
            <Link to="/login" className="hidden rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm font-medium text-slate-200 shadow-sm transition hover:-translate-y-0.5 hover:border-white/20 hover:bg-white/10 md:inline-flex">Sign in</Link>
            <Link to="/signup" className="rounded-full bg-white px-4 py-2 text-sm font-semibold text-slate-950 shadow-[0_18px_40px_rgba(255,255,255,0.08)] transition hover:-translate-y-0.5 hover:bg-slate-100">Get Started</Link>
          </div>
        </div>
      </header>

      <main className="mx-auto flex w-full max-w-7xl flex-col gap-24 px-6 py-14 lg:px-8">
        <section className="grid items-center gap-12 lg:grid-cols-[1.02fr_0.98fr]">
          <motion.div initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.55 }} className="max-w-2xl">
            <div className="inline-flex items-center gap-2 rounded-full border border-cyan-400/20 bg-cyan-400/10 px-4 py-2 text-sm font-medium text-cyan-200 shadow-sm">
              <Sparkles className="h-4 w-4" />
              Premium product intelligence for faster business decisions
            </div>

            <h1 className="mt-6 text-5xl font-semibold tracking-tight text-white md:text-7xl">
              StrategAI helps you pick, price, and present products with confidence.
            </h1>

            <p className="mt-6 max-w-xl text-lg leading-8 text-slate-300 md:text-xl">
              Compare wholesale and retail markets, shape pricing, and turn real market evidence into launch-ready strategy for Pakistani e-commerce.
            </p>

            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <Link to="/signup" className="inline-flex items-center justify-center gap-2 rounded-full bg-white px-6 py-3 text-sm font-semibold text-slate-950 shadow-[0_20px_45px_rgba(255,255,255,0.08)] transition hover:-translate-y-0.5 hover:bg-slate-100">
                Start Using StrategAI
                <ArrowRight className="h-4 w-4" />
              </Link>
              <a href="#preview" className="inline-flex items-center justify-center gap-2 rounded-full border border-white/10 bg-white/5 px-6 py-3 text-sm font-semibold text-slate-200 shadow-sm transition hover:-translate-y-0.5 hover:border-white/20 hover:bg-white/10">
                View Preview
              </a>
            </div>

            <div className="mt-10 grid grid-cols-2 gap-4 sm:grid-cols-4">
              {metrics.map(([label, value]) => (
                <div key={label} className="rounded-2xl border border-white/10 bg-white/5 p-4 shadow-sm backdrop-blur-xl">
                  <div className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">{label}</div>
                  <div className="mt-2 text-sm font-medium text-white">{value}</div>
                </div>
              ))}
            </div>
          </motion.div>

          <motion.div initial={{ opacity: 0, y: 30, scale: 0.98 }} animate={{ opacity: 1, y: 0, scale: 1 }} transition={{ duration: 0.65, delay: 0.08 }} className="relative">
            <div className="absolute -inset-6 rounded-[2rem] bg-gradient-to-br from-cyan-400/18 via-transparent to-indigo-500/20 blur-3xl" />
            <div className="relative overflow-hidden rounded-[2rem] border border-white/10 bg-white/[0.05] p-6 shadow-[0_30px_90px_rgba(2,6,23,0.45)] backdrop-blur-2xl">
              <div className="mb-5 flex items-start justify-between gap-4">
                <div>
                  <div className="text-sm font-medium text-slate-400">Business intelligence snapshot</div>
                  <div className="text-2xl font-semibold tracking-tight text-white">StrategAI Product Preview</div>
                </div>
                <div className="rounded-full bg-cyan-400/10 px-3 py-1 text-xs font-semibold text-cyan-200">Live analysis</div>
              </div>

              <div className={`rounded-[1.75rem] border border-white/10 bg-gradient-to-br ${currentSlide.accent} p-4 shadow-[0_24px_80px_rgba(2,6,23,0.35)]`}>
                <div className="mb-4 flex items-center justify-between">
                  <div>
                    <p className="text-xs uppercase tracking-[0.28em] text-slate-300/80">{currentSlide.eyebrow}</p>
                    <h2 className="mt-2 text-2xl font-semibold text-white">{currentSlide.title}</h2>
                  </div>
                  <div className="flex gap-1">
                    {previewSlides.map((slide, index) => (
                      <button key={slide.title} type="button" onClick={() => setActiveSlide(index)} className={`h-2 rounded-full transition-all ${index === activeSlide ? 'w-8 bg-cyan-300' : 'w-2 bg-white/35'}`} aria-label={`Show ${slide.title}`} />
                    ))}
                  </div>
                </div>

                <AnimatePresence mode="wait">
                  <motion.div
                    key={currentSlide.title}
                    initial={{ opacity: 0, y: 16, scale: 0.985 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: -12, scale: 0.985 }}
                    transition={{ duration: 0.35 }}
                    className="rounded-[1.4rem] border border-white/10 bg-slate-950/50 p-4 backdrop-blur-2xl"
                  >
                    {currentSlide.frame}
                  </motion.div>
                </AnimatePresence>

                <div className="mt-4 flex items-center justify-between text-xs text-slate-300/80">
                  <span>{currentSlide.description}</span>
                  <span className="inline-flex items-center gap-1"><ChevronRight className="h-3.5 w-3.5" /> Auto-rotating preview</span>
                </div>
              </div>
            </div>
          </motion.div>
        </section>

        <section id="features" className="space-y-8">
          <div className="max-w-2xl">
            <div className="text-sm font-semibold uppercase tracking-[0.28em] text-cyan-300">Features</div>
            <h2 className="mt-3 text-3xl font-semibold tracking-tight text-white md:text-4xl">A polished workspace for pricing, marketing, and decision support</h2>
            <p className="mt-4 text-base leading-7 text-slate-400">The platform turns market evidence into business actions without changing the core workflow or analytics logic.</p>
          </div>

          <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
            {features.map((feature) => {
              const Icon = feature.icon;
              return (
                <motion.div key={feature.title} whileHover={{ y: -6 }} className="rounded-3xl border border-white/10 bg-white/[0.05] p-6 shadow-sm">
                  <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-cyan-400/10 text-cyan-200">
                    <Icon className="h-6 w-6" />
                  </div>
                  <h3 className="mt-5 text-xl font-semibold text-white">{feature.title}</h3>
                  <p className="mt-3 text-sm leading-7 text-slate-400">{feature.description}</p>
                </motion.div>
              );
            })}
          </div>
        </section>

        <section id="workflow" className="rounded-[2rem] border border-white/10 bg-white/[0.04] p-8 shadow-sm lg:p-10 backdrop-blur-2xl">
          <div className="max-w-2xl">
            <div className="text-sm font-semibold uppercase tracking-[0.28em] text-cyan-300">How It Works</div>
            <h2 className="mt-3 text-3xl font-semibold tracking-tight text-white md:text-4xl">A clear flow from market data to final recommendation</h2>
          </div>

          <div className="mt-10 grid gap-4 lg:grid-cols-[repeat(8,minmax(0,1fr))] lg:items-center">
            {workflow.map((step, index) => (
              <div key={step} className="flex items-center gap-4 lg:flex-col lg:gap-3">
                <div className="flex flex-1 items-center justify-center rounded-2xl border border-white/10 bg-slate-950/45 px-3 py-4 text-sm font-semibold text-slate-200 shadow-sm">
                  {step}
                </div>
                {index < workflow.length - 1 && (
                  <div className="flex items-center justify-center text-cyan-300 lg:w-full">
                    <ArrowRight className="h-4 w-4 lg:hidden" />
                    <div className="hidden h-px w-full bg-gradient-to-r from-cyan-300/10 via-cyan-300/90 to-indigo-300/10 lg:block" />
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>

        <section className="grid gap-5 lg:grid-cols-3">
          {[
            { title: 'Decision clarity', icon: BadgeCheck, description: 'Keeps reasoning and confidence visible instead of hiding behind a model.' },
            { title: 'Launch readiness', icon: TrendingUp, description: 'Turns market spread into actionable go-to-market advice for sellers.' },
            { title: 'Business fit', icon: Gauge, description: 'Highlights whether the product is worth attention before time and capital are spent.' },
          ].map((benefit) => {
            const Icon = benefit.icon;
            return (
              <div key={benefit.title} className="rounded-3xl border border-white/10 bg-white/[0.05] p-6 shadow-sm">
                <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-cyan-400 to-indigo-500 text-white">
                  <Icon className="h-5 w-5" />
                </div>
                <h3 className="mt-5 text-xl font-semibold text-white">{benefit.title}</h3>
                <p className="mt-3 text-sm leading-7 text-slate-400">{benefit.description}</p>
              </div>
            );
          })}
        </section>

        <section id="preview" className="space-y-8">
          <div className="max-w-2xl">
            <div className="text-sm font-semibold uppercase tracking-[0.28em] text-cyan-300">Preview</div>
            <h2 className="mt-3 text-3xl font-semibold tracking-tight text-white md:text-4xl">Real StrategAI views, styled as a premium product showcase</h2>
          </div>

          <div className="grid gap-5 lg:grid-cols-2">
            {previewSlides.slice(0, 2).map((shot) => (
              <div key={shot.title} className="overflow-hidden rounded-[2rem] border border-white/10 bg-white/[0.05] shadow-sm">
                <div className={`h-full bg-gradient-to-br ${shot.accent} p-6`}>
                  <div className="rounded-[1.5rem] border border-white/10 bg-slate-950/55 p-5 backdrop-blur-xl">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="text-xs uppercase tracking-[0.28em] text-slate-300/80">{shot.eyebrow}</div>
                        <h3 className="mt-2 text-2xl font-semibold text-white">{shot.title}</h3>
                      </div>
                      <div className="rounded-full bg-cyan-400/10 px-3 py-1 text-xs font-semibold text-cyan-200">StrategAI</div>
                    </div>
                    <div className="mt-4 text-sm leading-7 text-slate-300">{shot.description}</div>
                    <div className="mt-5 rounded-2xl border border-white/10 bg-white/[0.04] p-4">
                      {shot.frame}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-[2rem] border border-white/10 bg-gradient-to-br from-slate-950 to-slate-900 px-8 py-10 text-white shadow-[0_30px_90px_rgba(2,6,23,0.45)] lg:px-12">
          <div className="grid gap-8 lg:grid-cols-[1fr_auto] lg:items-center">
            <div>
              <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm font-medium text-slate-200">
                <Workflow className="h-4 w-4" />
                Ready to discover profitable products?
              </div>
              <h2 className="mt-5 text-3xl font-semibold tracking-tight md:text-4xl">Turn market data into a confident product decision.</h2>
              <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-300 md:text-base">
                StrategAI keeps the pricing, marketing, and decision flow aligned so you can present a complete AI business story during your evaluation.
              </p>
            </div>
            <div className="flex flex-col gap-3 sm:flex-row lg:flex-col">
              <Link to="/signup" className="inline-flex items-center justify-center gap-2 rounded-full bg-white px-6 py-3 text-sm font-semibold text-slate-950 transition hover:-translate-y-0.5 hover:bg-slate-100">
                Start Using StrategAI
                <ArrowRight className="h-4 w-4" />
              </Link>
              <Link to="/login" className="inline-flex items-center justify-center gap-2 rounded-full border border-white/10 bg-white/5 px-6 py-3 text-sm font-semibold text-white transition hover:-translate-y-0.5 hover:bg-white/10">
                Sign in
              </Link>
            </div>
          </div>
        </section>
      </main>

      <footer id="footer" className="border-t border-white/10 bg-slate-950/80 backdrop-blur-2xl">
        <div className="mx-auto grid w-full max-w-7xl gap-8 px-6 py-10 text-sm text-slate-400 lg:grid-cols-3 lg:px-8">
          <div>
            <div className="text-base font-semibold text-white">StrategAI</div>
            <p className="mt-3 max-w-sm leading-7">An explainable AI e-commerce platform for wholesale, retail, pricing, and marketing intelligence.</p>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <a href="#features" className="transition hover:text-white">Features</a>
            <a href="#workflow" className="transition hover:text-white">Workflow</a>
            <a href="#preview" className="transition hover:text-white">Preview</a>
            <a href="https://github.com/hudarizwan/fyp_Strategai" target="_blank" rel="noreferrer" className="transition hover:text-white">GitHub</a>
          </div>
          <div className="rounded-3xl border border-white/10 bg-white/[0.04] p-5">
            <div className="text-base font-semibold text-white">Contact</div>
            <p className="mt-3 leading-7">For evaluation, demos, and documentation, connect this landing page to your project report and presentation materials.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default Landing;


