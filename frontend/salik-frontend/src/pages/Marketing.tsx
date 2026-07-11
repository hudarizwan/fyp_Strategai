import { useEffect, useState, type ReactNode } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  History,
  CheckCircle,
  XCircle,
  ShieldCheck,
  ShieldAlert,
  Sparkles,
  Landmark,
  DollarSign,
  Users,
  Cpu,
  Leaf,
  Scale,
  Layers3,
} from 'lucide-react';
import { AnimatePresence, motion } from 'framer-motion';
import Button from '@/components/ui/Button';
import { marketingService } from '@/services/api';
import { MarketingStrategyRecord } from '@/types';

function StatusBadge({ status }: { status: string }) {
  if (status === 'ok') {
    return (
      <span className="inline-flex items-center gap-1 rounded-full border border-emerald-400/20 bg-emerald-500/10 px-2.5 py-1 text-xs font-medium text-emerald-300">
        <CheckCircle className="h-3 w-3" /> OK
      </span>
    );
  }
  if (status === 'needs_review') {
    return (
      <span className="inline-flex items-center gap-1 rounded-full border border-amber-400/20 bg-amber-500/10 px-2.5 py-1 text-xs font-medium text-amber-300">
        <AlertTriangle className="h-3 w-3" /> Needs Review
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 rounded-full border border-red-400/20 bg-red-500/10 px-2.5 py-1 text-xs font-medium text-red-300">
      <XCircle className="h-3 w-3" /> Invalid
    </span>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  const [open, setOpen] = useState(true);

  return (
    <motion.div
      className="overflow-hidden rounded-2xl border border-white/10 bg-white/[0.04] shadow-[0_16px_40px_rgba(2,6,23,0.16)] backdrop-blur-xl"
      layout
    >
      <button
        className="flex w-full items-center justify-between border-b border-white/5 px-4 py-4 text-left transition-colors hover:bg-white/5"
        onClick={() => setOpen((o) => !o)}
      >
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-xl border border-white/10 bg-white/5">
            <Layers3 className="h-4 w-4 text-cyan-300" />
          </div>
          <h2 className="text-lg font-semibold text-white">{title}</h2>
        </div>
        {open ? <ChevronUp className="h-4 w-4 text-gray-400" /> : <ChevronDown className="h-4 w-4 text-gray-400" />}
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.24, ease: 'easeInOut' }}
          >
            <div className="space-y-4 px-4 py-4">{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

function KVRow({ label, value }: { label: string; value?: string | number }) {
  if (value === undefined || value === null || value === '') return null;
  return (
    <div className="flex gap-2">
      <span className="min-w-[140px] text-sm text-gray-400">{label}:</span>
      <span className="text-sm text-white">{String(value)}</span>
    </div>
  );
}

function renderText(value: unknown): string {
  if (typeof value === 'string') return value;
  if (Array.isArray(value)) return value.map((item) => String(item)).join(' ');
  if (value && typeof value === 'object') {
    return Object.entries(value as Record<string, unknown>)
      .map(([key, entry]) => `${key.replace(/_/g, ' ')}: ${String(entry)}`)
      .join(' ');
  }
  return '-';
}

function renderList(value: unknown): string[] {
  if (Array.isArray(value)) return value.map((item) => String(item)).filter(Boolean);
  if (typeof value === 'string' && value.trim()) return [value.trim()];
  return [];
}

function InfoCard({
  title,
  children,
  accent = 'text-cyan-300',
}: {
  title: string;
  children: ReactNode;
  accent?: string;
}) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
      <h3 className={`mb-2 text-sm font-semibold ${accent}`}>{title}</h3>
      {children}
    </div>
  );
}

const swotStyles = {
  strengths: {
    card: 'border-emerald-400/20 bg-emerald-500/10 text-emerald-300',
    icon: ShieldCheck,
  },
  weaknesses: {
    card: 'border-red-400/20 bg-red-500/10 text-red-300',
    icon: ShieldAlert,
  },
  opportunities: {
    card: 'border-cyan-400/20 bg-cyan-500/10 text-cyan-300',
    icon: Sparkles,
  },
  threats: {
    card: 'border-amber-400/20 bg-amber-500/10 text-amber-300',
    icon: AlertTriangle,
  },
} as const;

const pestelMeta = {
  political: { icon: Landmark, accent: 'text-indigo-300' },
  economic: { icon: DollarSign, accent: 'text-cyan-300' },
  social: { icon: Users, accent: 'text-purple-300' },
  technological: { icon: Cpu, accent: 'text-cyan-300' },
  environmental: { icon: Leaf, accent: 'text-emerald-300' },
  legal: { icon: Scale, accent: 'text-amber-300' },
} as const;

export default function Marketing() {
  const navigate = useNavigate();
  const location = useLocation();
  const [strategy, setStrategy] = useState<MarketingStrategyRecord | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadStrategy = async () => {
      const params = new URLSearchParams(location.search);
      const strategyId = params.get('strategyId');
      const analyticsResultId = params.get('analyticsResultId');
      try {
        if (strategyId) {
          const fetched = await marketingService.getById(strategyId);
          sessionStorage.setItem('marketingStrategy', JSON.stringify(fetched));
          setStrategy(fetched);
          return;
        }
        if (analyticsResultId) {
          let fetched;
          try {
            fetched = await marketingService.getLatestByAnalytics(analyticsResultId);
          } catch {
            const storedAnalytics = sessionStorage.getItem('analyticsRecommendation');
            const analytics = storedAnalytics ? JSON.parse(storedAnalytics) : null;
            if (!analytics?.pipeline_run_id) {
              throw new Error('No saved marketing strategy found for this analytics result.');
            }
            fetched = await marketingService.getLatestByPipeline(analytics.pipeline_run_id);
          }
          sessionStorage.setItem('marketingStrategy', JSON.stringify(fetched));
          setStrategy(fetched);
          return;
        }
        const stored = sessionStorage.getItem('marketingStrategy');
        if (stored) {
          setStrategy(JSON.parse(stored));
          return;
        }
        setError('No strategy found. Please generate one from the Results page.');
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load marketing strategy');
      } finally {
        setLoading(false);
      }
    };

    void loadStrategy();
  }, [location.search]);

  if (loading) {
    return (
      <div className="container mx-auto min-h-[calc(100vh-8rem)] px-4 py-8">
        <p className="text-gray-400">Loading strategy...</p>
      </div>
    );
  }

  if (error || !strategy) {
    return (
      <div className="container mx-auto min-h-[calc(100vh-8rem)] px-4 py-8">
        <p className="text-gray-400">{error || 'No strategy found. Please generate one from the Results page.'}</p>
        <Button onClick={() => navigate('/results')} className="mt-4">
          <ArrowLeft className="mr-2 h-4 w-4" /> Back to Results
        </Button>
      </div>
    );
  }

  const strategyContent = (
    strategy.strategy && typeof strategy.strategy === 'object' ? strategy.strategy : strategy
  ) as Record<string, any>;

  const stp = strategyContent.stp || {};
  const swot = strategyContent.swot || {};
  const pestel = strategyContent.pestel || {};
  const ca = strategyContent.competitor_analysis || {};
  const mix = strategyContent.marketing_mix || {};
  const branding = strategyContent.branding || {};
  const channels: any[] = strategyContent.channels || [];
  const launch = strategyContent.launch_plan || {};
  const funnel = strategyContent.growth_funnel || {};
  const evidence: any[] = strategyContent.evidence_ledger || [];
  const validation = strategyContent.validation_report || {};
  const meta = strategyContent.strategy_meta || {};

  return (
    <motion.div
      className="relative mx-auto min-h-[calc(100vh-8rem)] space-y-6 px-4 py-8"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -left-24 top-16 h-72 w-72 rounded-full bg-cyan-500/10 blur-3xl" />
        <div className="absolute right-0 top-36 h-80 w-80 rounded-full bg-indigo-500/10 blur-3xl" />
      </div>

      <div className="relative z-10">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-white">Marketing Strategy</h1>
            <p className="mt-1 text-sm text-gray-400">
              {strategy.product_name} - {strategy.category}
            </p>
            <p className="mt-1 text-xs text-gray-500">
              Version {strategy.version_number || 1}
              {strategy.created_at ? ` - ${new Date(strategy.created_at).toLocaleString('en-PK')}` : ''}
            </p>
          </div>
          <div className="flex flex-wrap items-center justify-end gap-3">
            <StatusBadge status={strategy.analysis_status || 'ok'} />
            <span className="text-sm text-gray-400">
              Confidence:{' '}
              {strategy.confidence_score !== undefined && strategy.confidence_score !== null
                ? `${(strategy.confidence_score * 100).toFixed(0)}%`
                : 'N/A'}
            </span>
            {(strategy.analytics_result_id || strategy.pipeline_run_id) && (
              <Button
                variant="outline"
                onClick={() =>
                  navigate(
                    strategy.analytics_result_id
                      ? `/marketing/history?analyticsResultId=${strategy.analytics_result_id}`
                      : `/marketing/history?pipelineRunId=${strategy.pipeline_run_id}`
                  )
                }
              >
                <History className="mr-2 h-4 w-4" /> History
              </Button>
            )}
            <Button variant="outline" onClick={() => navigate('/results')}>
              <ArrowLeft className="mr-2 h-4 w-4" /> Back to Results
            </Button>
          </div>
        </div>

        <Section title="Strategy Lens">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <InfoCard title="Strategic Angle">
              <p className="text-sm leading-7 text-gray-300">{renderText(meta.strategy_angle)}</p>
            </InfoCard>
            <InfoCard title="Generation Mode" accent="text-purple-300">
              <p className="text-sm leading-7 text-gray-300">{renderText(meta.generation_mode)}</p>
            </InfoCard>
            <InfoCard title="Variation Type" accent="text-indigo-300">
              <p className="text-sm leading-7 text-gray-300">{renderText(meta.variation_type)}</p>
            </InfoCard>
          </div>
        </Section>

        <Section title="STP Analysis">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <InfoCard title="Segmentation">
              <p className="text-sm leading-7 text-gray-300">
                {renderText(stp.segmentation?.demographics || stp.segmentation)}
              </p>
              {stp.segmentation?.psychographics && (
                <p className="mt-2 text-xs leading-6 text-gray-400">
                  {renderText(stp.segmentation.psychographics)}
                </p>
              )}
            </InfoCard>
            <InfoCard title="Targeting" accent="text-indigo-300">
              <p className="text-sm leading-7 text-gray-300">
                {renderText(stp.targeting?.primary_segment || stp.targeting)}
              </p>
            </InfoCard>
            <InfoCard title="Positioning" accent="text-purple-300">
              <p className="text-sm leading-7 text-gray-300">
                {renderText(stp.positioning?.statement || stp.positioning)}
              </p>
            </InfoCard>
          </div>
        </Section>

        <Section title="SWOT Analysis">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            {[
              { key: 'strengths', items: renderList(swot.strengths) },
              { key: 'weaknesses', items: renderList(swot.weaknesses) },
              { key: 'opportunities', items: renderList(swot.opportunities) },
              { key: 'threats', items: renderList(swot.threats) },
            ].map(({ key, items }) => {
              const meta = swotStyles[key as keyof typeof swotStyles];
              const Icon = meta.icon;
              return (
                <div key={key} className={`rounded-2xl border p-4 ${meta.card}`}>
                  <div className="mb-3 flex items-center gap-2">
                    <div className="flex h-8 w-8 items-center justify-center rounded-xl border border-white/10 bg-white/10">
                      <Icon className="h-4 w-4" />
                    </div>
                    <h3 className="font-medium capitalize text-white/90">{key}</h3>
                  </div>
                  <ul className="list-disc list-inside space-y-1">
                    {items.length > 0 ? (
                      items.map((item, i) => (
                        <li key={i} className="text-sm leading-7 text-gray-300">
                          {item}
                        </li>
                      ))
                    ) : (
                      <li className="text-sm text-gray-500">No details available.</li>
                    )}
                  </ul>
                </div>
              );
            })}
          </div>
        </Section>

        <Section title="PESTEL Analysis">
          <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
            {[
              ['Political', pestel.political, 'political'],
              ['Economic', pestel.economic, 'economic'],
              ['Social', pestel.social, 'social'],
              ['Technological', pestel.technological, 'technological'],
              ['Environmental', pestel.environmental, 'environmental'],
              ['Legal', pestel.legal, 'legal'],
            ].map(([label, value, key]) => {
              const meta = pestelMeta[key as keyof typeof pestelMeta];
              const Icon = meta.icon;
              return (
                <InfoCard key={label} title={String(label)} accent={meta.accent}>
                  <div className="mb-2 flex items-center gap-2">
                    <div className="flex h-7 w-7 items-center justify-center rounded-lg border border-white/10 bg-white/10">
                      <Icon className="h-3.5 w-3.5 text-white" />
                    </div>
                    <span className="text-xs uppercase tracking-[0.16em] text-gray-500">Factor</span>
                  </div>
                  <p className="text-xs leading-6 text-gray-300">{renderText(value)}</p>
                </InfoCard>
              );
            })}
          </div>
        </Section>

        <Section title="Competitor Analysis">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <InfoCard title="Porter's Five Forces" accent="text-cyan-300">
              <div className="space-y-2 text-sm">
                {Object.entries(ca.five_forces || {}).map(([key, value]) => (
                  <div
                    key={key}
                    className="flex items-center justify-between border-b border-white/10 py-2"
                  >
                    <span className="text-sm capitalize text-gray-400">
                      {key.replace(/_/g, ' ')}
                    </span>
                    <span className="text-sm text-white">{String(value)}</span>
                  </div>
                ))}
              </div>
            </InfoCard>
            <InfoCard title="Key Competitors" accent="text-purple-300">
              <ul className="list-disc list-inside space-y-1">
                {renderList(ca.key_competitors).map((competitorName, i) => (
                  <li key={i} className="text-sm leading-7 text-gray-300">
                    {competitorName}
                  </li>
                ))}
              </ul>
              {ca.price_band && (
                <div className="mt-3 rounded-xl border border-white/10 bg-white/[0.03] p-3 text-sm">
                  <span className="text-gray-400">Price band: </span>
                  <span className="text-white">
                    {ca.price_band.min?.toLocaleString?.() ?? ca.price_band.min} -{' '}
                    {ca.price_band.max?.toLocaleString?.() ?? ca.price_band.max}{' '}
                    {ca.price_band.currency}
                  </span>
                </div>
              )}
            </InfoCard>
          </div>
        </Section>

        <Section title="Marketing Mix (4Ps)">
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <InfoCard title="Product" accent="text-purple-300">
              <p className="text-xs leading-6 text-gray-300">
                {renderText(mix.product?.description)}
              </p>
              {mix.product?.usp && (
                <p className="mt-2 text-xs leading-6 text-gray-400">
                  USP: {renderText(mix.product.usp)}
                </p>
              )}
            </InfoCard>
            <InfoCard title="Price" accent="text-indigo-300">
              <p className="text-xs leading-6 text-gray-300">
                {renderText(mix.price?.strategy)}
              </p>
              {mix.price?.recommended_sell_pkr && (
                <p className="mt-2 text-xs text-white">
                  Recommended sell: PKR {Number(mix.price.recommended_sell_pkr).toLocaleString('en-PK')}
                </p>
              )}
            </InfoCard>
            <InfoCard title="Place" accent="text-cyan-300">
              <p className="text-xs leading-6 text-gray-300">
                {renderList(mix.place?.channels).join(', ') || '-'}
              </p>
            </InfoCard>
            <InfoCard title="Promotion" accent="text-emerald-300">
              <ul className="list-disc list-inside space-y-1">
                {renderList(mix.promotion?.tactics).map((item, i) => (
                  <li key={i} className="text-xs leading-6 text-gray-300">
                    {item}
                  </li>
                ))}
              </ul>
            </InfoCard>
          </div>
        </Section>

        <Section title="Branding">
          <KVRow label="Value Proposition" value={renderText(branding.value_proposition)} />
          <KVRow label="Tone" value={renderText(branding.tone)} />
          <KVRow label="Tagline" value={renderText(branding.tagline)} />
        </Section>

        <Section title="Channel Plan">
          <div className="space-y-2">
            {channels.map((channel: any, i: number) => (
              <div
                key={i}
                className="flex items-start gap-3 rounded-2xl border border-white/10 bg-white/[0.03] p-4"
              >
                <span className="w-6 text-sm font-bold text-cyan-300">
                  {channel.priority || i + 1}
                </span>
                <div>
                  <p className="text-sm font-medium text-white">{channel.name}</p>
                  <p className="text-xs leading-6 text-gray-400">{renderText(channel.rationale)}</p>
                </div>
              </div>
            ))}
          </div>
        </Section>

        <Section title={`Growth Funnel (${funnel.model || 'AARRR'})`}>
          <div className="flex flex-wrap gap-2">
            {(funnel.stages || []).map((stage: any, i: number) => (
              <div
                key={i}
                className="min-w-[120px] flex-1 rounded-2xl border border-white/10 bg-white/[0.03] p-4 text-center"
              >
                <p className="text-sm font-medium text-cyan-300">{renderText(stage.stage)}</p>
                <p className="mt-1 text-xs text-gray-300">{renderText(stage.metric)}</p>
                {stage.target !== undefined && (
                  <p className="mt-1 text-xs text-white">Target: {stage.target}</p>
                )}
              </div>
            ))}
          </div>
        </Section>

        <Section title="Launch Plan">
          <div className="space-y-3">
            {(launch.phases || []).map((phase: any, i: number) => (
              <div key={i} className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
                <div className="mb-2 flex items-center gap-2">
                  <span className="text-sm font-medium text-purple-300">{renderText(phase.name)}</span>
                  {phase.duration && <span className="text-xs text-gray-500">- {phase.duration}</span>}
                </div>
                <ul className="list-disc list-inside space-y-1">
                  {renderList(phase.actions).map((action, j) => (
                    <li key={j} className="text-xs leading-6 text-gray-300">
                      {action}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
          {(launch.kpis || []).length > 0 && (
            <div className="mt-4">
              <h3 className="mb-2 text-sm font-medium text-white">KPIs</h3>
              <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
                {(launch.kpis || []).map((kpi: any, i: number) => (
                  <div key={i} className="rounded-xl border border-white/10 bg-white/[0.03] p-3 text-xs">
                    <span className="text-cyan-300">{renderText(kpi.metric)}: </span>
                    <span className="text-white">
                      {renderText(kpi.target)} ({renderText(kpi.period)})
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
          {launch.measurement_plan && (
            <div className="mt-4 rounded-2xl border border-white/10 bg-white/[0.03] p-3">
              <p className="mb-1 text-sm font-medium text-white">Measurement Plan</p>
              <p className="text-xs leading-6 text-gray-300">
                {renderList(launch.measurement_plan.tools).join(', ') || '-'}
              </p>
              {launch.measurement_plan.cadence && (
                <p className="mt-2 text-xs text-gray-400">
                  Cadence: {renderText(launch.measurement_plan.cadence)}
                </p>
              )}
            </div>
          )}
        </Section>

        <Section title="Content Strategy">
          <KVRow label="Formats" value={renderList(strategyContent.content_strategy?.formats).join(', ')} />
          <KVRow label="Frequency" value={renderText(strategyContent.content_strategy?.frequency)} />
        </Section>

        <Section title="Evidence Ledger">
          <div className="space-y-2">
            {evidence.map((entry: any, i: number) => (
              <div key={i} className="rounded-xl border border-white/10 bg-white/[0.03] p-3 text-xs">
                <p className="text-white">{renderText(entry.recommendation)}</p>
                <p className="mt-1 text-gray-400">Evidence: {renderList(entry.evidence).join(', ')}</p>
              </div>
            ))}
          </div>
        </Section>

        <Section title="Validation Report">
          <div className="mb-3 flex items-center gap-2">
            <StatusBadge status={validation.status || 'ok'} />
          </div>
          {(validation.flags || []).length > 0 && (
            <div>
              <p className="mb-1 text-sm font-medium text-amber-300">Flags:</p>
              <ul className="list-disc list-inside space-y-1">
                {renderList(validation.flags).map((flag, i) => (
                  <li key={i} className="text-sm leading-6 text-gray-300">
                    {flag}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </Section>
      </div>
    </motion.div>
  );
}
