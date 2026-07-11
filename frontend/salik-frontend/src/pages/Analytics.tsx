import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { TrendingUp, TrendingDown, DollarSign, Package, BarChart3, ExternalLink, ArrowRight } from 'lucide-react';
import { motion } from 'framer-motion';
import { ScraperResponse, AnalyticsRecommendation, MarketingStrategyBase } from '@/types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import PriceHistorySparkline from '@/components/PriceHistorySparkline';
import { marketingService } from '@/services/api';
import { normalizeScraperResult } from '@/utils/normalizeScraperResult';
import { buildAnalyticsDashboardModel } from '@/utils/analyticsDashboard';
import {
  BarChart,
  Bar,
  CartesianGrid,
  Legend,
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from 'recharts';

const pageVariants = {
  hidden: { opacity: 0, y: 12 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { staggerChildren: 0.08, delayChildren: 0.08 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 12 },
  visible: { opacity: 1, y: 0 },
};

const formatCurrency = (value: number) => `${Math.round(value).toLocaleString()} PKR`;

function MoneyTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{ value?: number | string; name?: string }>;
  label?: string;
}) {
  if (!active || !payload?.length) return null;

  return (
    <div className="rounded-2xl border border-white/10 bg-slate-950/95 px-4 py-3 shadow-[0_20px_60px_rgba(2,6,23,0.35)] backdrop-blur-xl">
      {label && <p className="mb-2 text-xs font-medium uppercase tracking-[0.18em] text-gray-400">{label}</p>}
      <div className="space-y-1">
        {payload.map((entry, index) => (
          <p key={`${entry.name ?? 'value'}-${index}`} className="text-sm text-white">
            <span className="text-gray-400">{entry.name ?? 'Value'}:</span>{' '}
            {typeof entry.value === 'number' ? formatCurrency(entry.value) : entry.value}
          </p>
        ))}
      </div>
    </div>
  );
}


function SummaryPill({ label, value, tone = 'default' }: { label: string; value: string; tone?: 'default' | 'positive' | 'warning' | 'danger' | 'accent' }) {
  const toneClasses = {
    default: 'border-white/10 bg-white/5 text-white',
    positive: 'border-emerald-500/20 bg-emerald-500/10 text-emerald-200',
    warning: 'border-amber-500/20 bg-amber-500/10 text-amber-100',
    danger: 'border-rose-500/20 bg-rose-500/10 text-rose-100',
    accent: 'border-cyan-500/20 bg-cyan-500/10 text-cyan-100',
  } as const;
  return (
    <div className={`rounded-2xl border px-4 py-3 ${toneClasses[tone]}`}>
      <p className="text-[11px] uppercase tracking-[0.22em] text-white/60">{label}</p>
      <p className="mt-1 text-sm font-semibold">{value}</p>
    </div>
  );
}

export default function Analytics() {
  const navigate = useNavigate();
  const [data, setData] = useState<ScraperResponse | null>(null);
  const [analyticsRecommendation, setAnalyticsRecommendation] = useState<AnalyticsRecommendation | null>(null);
  const [latestStrategy, setLatestStrategy] = useState<MarketingStrategyBase | null>(null);

  useEffect(() => {
    const storedData = sessionStorage.getItem('scraperResult');
    const storedAnalytics = sessionStorage.getItem('analyticsRecommendation');
    if (!storedData) {
      return;
    }

    try {
      const parsed = normalizeScraperResult(JSON.parse(storedData));
      setData(parsed);
      setAnalyticsRecommendation(storedAnalytics ? JSON.parse(storedAnalytics) : null);
    } catch (error) {
      console.error('Failed to parse analytics data:', error);
    }
  }, []);

  useEffect(() => {
    const lookup = async () => {
      if (!analyticsRecommendation) return;
      try {
        const strategy = analyticsRecommendation.analytics_result_id
          ? await marketingService.getLatestByAnalytics(analyticsRecommendation.analytics_result_id)
          : analyticsRecommendation.pipeline_run_id
            ? await marketingService.getLatestByPipeline(analyticsRecommendation.pipeline_run_id)
            : null;
        setLatestStrategy(strategy);
      } catch {
        setLatestStrategy(null);
      }
    };
    void lookup();
  }, [analyticsRecommendation]);

  if (!data) {
    return (
      <div className="container mx-auto min-h-[calc(100vh-8rem)] px-4 py-8">
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-gray-400">No analytics data available. Please search for a product first.</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const dashboard = buildAnalyticsDashboardModel(data, analyticsRecommendation, latestStrategy);
  const hasMarketing = Boolean(latestStrategy);

  const leaderBars = dashboard.supplierIntelligence.leaders.slice(0, 8).map((item) => ({
    name: item.name,
    price: item.averagePrice,
    count: item.count,
  }));

  const sellerBars = dashboard.retailMarket.leaders.slice(0, 8).map((item) => ({
    name: item.name,
    price: item.averagePrice,
    count: item.count,
  }));

  const marketRadar = dashboard.marketOpportunity.radar;

  const axisTick = { fill: '#94a3b8', fontSize: 12 };
  const gridStroke = 'rgba(148, 163, 184, 0.14)';

  return (
    <motion.div className="container mx-auto space-y-8 px-4 py-8" initial="hidden" animate="visible" variants={pageVariants}>
      <motion.div className="rounded-3xl border border-white/10 bg-gradient-to-br from-slate-950 via-slate-900 to-cyan-950/60 p-6 shadow-[0_24px_120px_rgba(2,6,23,0.45)]" variants={itemVariants}>
        <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-3xl">
            <p className="text-xs uppercase tracking-[0.3em] text-cyan-300/80">Analytics Dashboard</p>
            <h1 className="mt-2 text-4xl font-black tracking-tight text-white md:text-5xl">{dashboard.productName}</h1>
            <p className="mt-3 text-base text-slate-300">
              Business intelligence for {dashboard.category}. Every chart is derived from observed wholesale and retail market evidence, then translated into pricing, opportunity, and execution guidance.
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Button variant="outline" onClick={() => navigate('/results')}>
              Back to Results
            </Button>
            <Button onClick={() => navigate('/marketing')}>
              Marketing View
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </div>
        </div>
      </motion.div>

      <motion.div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-6" variants={pageVariants}>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Recommended Buy</CardTitle>
            <DollarSign className="h-4 w-4 text-cyan-300" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-cyan-300">{formatCurrency(dashboard.recommendationSummary.recommendedBuy)}</div>
            <p className="mt-1 text-xs text-gray-400">Selected sourcing target</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Recommended Sell</CardTitle>
            {dashboard.recommendationSummary.recommendedSell > dashboard.recommendationSummary.recommendedBuy ? (
              <TrendingUp className="h-4 w-4 text-emerald-300" />
            ) : (
              <TrendingDown className="h-4 w-4 text-rose-300" />
            )}
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-emerald-300">{formatCurrency(dashboard.recommendationSummary.recommendedSell)}</div>
            <p className="mt-1 text-xs text-gray-400">Selected selling target</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Expected Gross Profit</CardTitle>
            <DollarSign className="h-4 w-4 text-emerald-300" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatCurrency(dashboard.recommendationSummary.expectedGrossProfit)}</div>
            <p className="mt-1 text-xs text-gray-400">Observed market spread after recommendation</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Confidence</CardTitle>
            <BarChart3 className="h-4 w-4 text-indigo-300" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-white">{dashboard.recommendationSummary.confidenceScore.toFixed(0)}%</div>
            <p className="mt-1 text-xs text-gray-400">{dashboard.pricingIntelligence.confidenceReason}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Market Opportunity</CardTitle>
            <TrendingUp className="h-4 w-4 text-cyan-300" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-white">{dashboard.recommendationSummary.opportunityScore.toFixed(0)}/100</div>
            <p className="mt-1 text-xs text-gray-400">Backend opportunity score</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Approval Readiness</CardTitle>
            <Package className="h-4 w-4 text-cyan-300" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{dashboard.recommendationSummary.approvalReadiness}</div>
            <p className="mt-1 text-xs text-gray-400">{hasMarketing ? `Marketing ready: ${dashboard.recommendationSummary.marketingReadiness}` : 'Marketing strategy not generated yet'}</p>
          </CardContent>
        </Card>
      </motion.div>
      <motion.div className="grid grid-cols-1 gap-6 lg:grid-cols-2" variants={pageVariants}>
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Market Overview</CardTitle>
            <p className="text-sm text-gray-400">Wholesale and retail distributions derived from actual observed listings.</p>
          </CardHeader>
          <CardContent className="grid grid-cols-1 gap-6 xl:grid-cols-2">
            <div>
              <p className="mb-3 text-sm font-medium text-white">Wholesale Price Distribution</p>
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={dashboard.marketOverview.wholesaleHistogram}>
                  <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} vertical={false} />
                  <XAxis dataKey="label" tick={axisTick} axisLine={false} tickLine={false} />
                  <YAxis tick={axisTick} axisLine={false} tickLine={false} allowDecimals={false} />
                  <Tooltip content={<MoneyTooltip />} />
                  <Bar dataKey="count" fill="#22d3ee" radius={[8, 8, 0, 0]} name="Listings" />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div>
              <p className="mb-3 text-sm font-medium text-white">Retail Price Distribution</p>
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={dashboard.marketOverview.retailHistogram}>
                  <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} vertical={false} />
                  <XAxis dataKey="label" tick={axisTick} axisLine={false} tickLine={false} />
                  <YAxis tick={axisTick} axisLine={false} tickLine={false} allowDecimals={false} />
                  <Tooltip content={<MoneyTooltip />} />
                  <Bar dataKey="count" fill="#818cf8" radius={[8, 8, 0, 0]} name="Listings" />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="grid grid-cols-1 gap-3 md:grid-cols-3 xl:col-span-2">
              <SummaryPill label="Observed market spread" value={formatCurrency(dashboard.marketOverview.observedMarketSpread)} tone="accent" />
              <SummaryPill label="Variance" value={dashboard.marketOverview.varianceLabel} tone={dashboard.marketOverview.varianceLabel === 'Low variance' ? 'positive' : dashboard.marketOverview.varianceLabel === 'High variance' ? 'warning' : 'default'} />
              <SummaryPill label="Stability" value={dashboard.marketOverview.stabilityLabel} tone={dashboard.marketOverview.stabilityLabel === 'Stable' ? 'positive' : dashboard.marketOverview.stabilityLabel === 'Volatile' ? 'warning' : 'default'} />
            </div>
            <div className="xl:col-span-2 rounded-2xl border border-white/10 bg-white/[0.03] p-4 text-sm text-gray-300">
              <p className="font-medium text-white">Why it matters</p>
              <p className="mt-2">{dashboard.marketOverview.takeaway}</p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Supplier Intelligence</CardTitle>
            <p className="text-sm text-gray-400">Leaderboards and price dispersion from wholesale listings only.</p>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <SummaryPill label="Lowest supplier" value={dashboard.supplierIntelligence.lowest?.name || 'n/a'} tone="positive" />
              <SummaryPill label="Median supplier" value={dashboard.supplierIntelligence.median?.name || 'n/a'} />
              <SummaryPill label="Highest supplier" value={dashboard.supplierIntelligence.highest?.name || 'n/a'} tone="warning" />
              <SummaryPill label="Most competitive" value={dashboard.supplierIntelligence.mostCompetitive?.name || 'n/a'} tone="accent" />
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-3">
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={leaderBars}>
                  <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} vertical={false} />
                  <XAxis dataKey="name" tick={axisTick} axisLine={false} tickLine={false} interval={0} />
                  <YAxis tick={axisTick} axisLine={false} tickLine={false} />
                  <Tooltip content={<MoneyTooltip />} />
                  <Legend />
                  <Bar dataKey="price" fill="#22d3ee" name="Avg price" radius={[8, 8, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Retail Market Intelligence</CardTitle>
            <p className="text-sm text-gray-400">Daraz seller concentration and observed retail pricing behavior.</p>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <SummaryPill label="Lowest seller" value={dashboard.retailMarket.lowest?.name || 'n/a'} tone="positive" />
              <SummaryPill label="Median seller" value={dashboard.retailMarket.median?.name || 'n/a'} />
              <SummaryPill label="Highest seller" value={dashboard.retailMarket.highest?.name || 'n/a'} tone="warning" />
              <SummaryPill label="Most competitive" value={dashboard.retailMarket.mostCompetitive?.name || 'n/a'} tone="accent" />
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-3">
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={sellerBars}>
                  <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} vertical={false} />
                  <XAxis dataKey="name" tick={axisTick} axisLine={false} tickLine={false} interval={0} />
                  <YAxis tick={axisTick} axisLine={false} tickLine={false} />
                  <Tooltip content={<MoneyTooltip />} />
                  <Legend />
                  <Bar dataKey="price" fill="#818cf8" name="Avg price" radius={[8, 8, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-3 text-sm text-gray-300">
              <p className="mb-2 font-medium text-white">Top retail listings</p>
              <div className="space-y-2">
                {dashboard.retailMarket.topListings.map((item, index) => (
                  <div key={`${item.url}-${index}`} className="flex items-center justify-between gap-3 rounded-xl border border-white/5 bg-black/20 px-3 py-2">
                    <div>
                      <p className="text-sm font-medium text-white">{item.title}</p>
                      <p className="text-xs text-gray-400">{item.seller} · {item.platform}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-semibold text-cyan-300">{formatCurrency(item.list_price)}</p>
                      {item.promo && <p className="text-[11px] text-emerald-200">{item.promo}</p>}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {analyticsRecommendation?.category && (
        <motion.div variants={itemVariants}>
          <PriceHistorySparkline productName={data.product_name} category={analyticsRecommendation.category} />
        </motion.div>
      )}

      <motion.div className="grid grid-cols-1 gap-6 lg:grid-cols-2" variants={pageVariants}>
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Market Opportunity</CardTitle>
            <p className="text-sm text-gray-400">Backend opportunity, competition, and coverage metrics with a price-stability overlay.</p>
          </CardHeader>
          <CardContent className="grid grid-cols-1 gap-6 xl:grid-cols-[1.15fr_0.85fr]">
            <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-3">
              <ResponsiveContainer width="100%" height={320}>
                <RadarChart data={marketRadar}>
                  <PolarGrid stroke={gridStroke} />
                  <PolarAngleAxis dataKey="metric" tick={{ fill: '#e5e7eb', fontSize: 12 }} />
                  <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fill: '#94a3b8', fontSize: 11 }} />
                  <Radar dataKey="value" stroke="#22d3ee" fill="#22d3ee" fillOpacity={0.24} name="Score" />
                  <Tooltip content={<MoneyTooltip />} />
                </RadarChart>
              </ResponsiveContainer>
            </div>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              {dashboard.marketOpportunity.cards.map((card) => (
                <div key={card.label} className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
                  <p className="text-xs uppercase tracking-[0.24em] text-gray-400">{card.label}</p>
                  <p className="mt-2 text-2xl font-semibold text-white">{card.value.toFixed(0)}/100</p>
                  <p className="mt-1 text-sm text-gray-400">{card.note}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Pricing Intelligence</CardTitle>
            <p className="text-sm text-gray-400">Selected posture, alternative price postures, and the evidence used to support the recommendation.</p>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
              {dashboard.pricingIntelligence.pricingModes.map((mode) => (
                <div
                  key={mode.key}
                  className={`rounded-2xl border p-4 ${mode.selected ? 'border-cyan-400/40 bg-cyan-500/10' : 'border-white/10 bg-white/[0.03]'}`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-xs uppercase tracking-[0.24em] text-gray-400">{mode.label}</p>
                      <p className="mt-1 text-2xl font-semibold text-white">{formatCurrency(mode.price)}</p>
                    </div>
                    <span className={`rounded-full border px-2 py-1 text-[11px] uppercase tracking-[0.2em] ${mode.selected ? 'border-cyan-400/40 bg-cyan-500/10 text-cyan-100' : 'border-white/10 bg-white/5 text-gray-300'}`}>
                      {mode.confidenceLabel}
                    </span>
                  </div>
                  <p className="mt-2 text-sm text-gray-300">Fit score: {mode.fitScore.toFixed(0)}/100</p>
                  <p className="mt-1 text-sm text-gray-400">{mode.reason}</p>
                  <p className="mt-3 text-sm font-medium text-white">Margin: {mode.marginPercent.toFixed(1)}%</p>
                  <ul className="mt-2 space-y-1 text-xs text-gray-400">
                    {mode.evidence.map((item) => (
                      <li key={item}>• {item}</li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
              {dashboard.pricingIntelligence.pricingSummary.map((item) => (
                <SummaryPill key={item.label} label={item.label} value={item.value} tone={item.tone} />
              ))}
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4 text-sm text-gray-300">
              <p className="font-medium text-white">Why this posture won</p>
              <ul className="mt-2 space-y-1">
                {dashboard.pricingIntelligence.selectionReason.map((reason) => (
                  <li key={reason}>• {reason}</li>
                ))}
              </ul>
              {dashboard.pricingIntelligence.clampReasons.length > 0 && (
                <p className="mt-3 text-xs text-amber-200">Sanity checks applied: {dashboard.pricingIntelligence.clampReasons.join(', ')}</p>
              )}
            </div>
          </CardContent>
        </Card>
      </motion.div>

      <motion.div className="grid grid-cols-1 gap-6 lg:grid-cols-2" variants={pageVariants}>
        <Card>
          <CardHeader>
            <CardTitle>Evidence Explorer</CardTitle>
            <p className="text-sm text-gray-400">Human-readable evidence cards instead of raw JSON.</p>
          </CardHeader>
          <CardContent className="space-y-3">
            {dashboard.evidenceExplorer.cards.length > 0 ? (
              dashboard.evidenceExplorer.cards.map((card) => (
                <div key={card.section} className="rounded-2xl border border-white/10 bg-white/[0.03] p-4 text-sm text-gray-300">
                  <p className="text-xs uppercase tracking-[0.24em] text-cyan-300/80">{card.section}</p>
                  <p className="mt-2 font-medium text-white">{card.recommendation}</p>
                  <ul className="mt-2 space-y-1 text-xs text-gray-400">
                    {card.evidence.map((item) => (
                      <li key={item}>• {item}</li>
                    ))}
                  </ul>
                </div>
              ))
            ) : (
              <p className="text-sm text-gray-400">No evidence ledger is available for this analysis.</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Cluster Visualization</CardTitle>
            <p className="text-sm text-gray-400">NLP clustering output that explains why listings were grouped together.</p>
          </CardHeader>
          <CardContent className="space-y-3">
            {dashboard.clusterVisualization.clusters.length > 0 ? (
              dashboard.clusterVisualization.clusters.map((cluster) => (
                <div key={cluster.clusterKey} className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-white">{cluster.canonicalTitle}</p>
                      <p className="text-xs text-gray-400">{cluster.clusterKey} · {cluster.status}</p>
                    </div>
                    <span className="rounded-full border border-cyan-400/30 bg-cyan-500/10 px-2 py-1 text-[11px] text-cyan-100">
                      {cluster.confidenceScore.toFixed(0)}% similarity confidence
                    </span>
                  </div>
                  <div className="mt-3 grid grid-cols-2 gap-3 text-sm text-gray-300">
                    <SummaryPill label="Average price" value={formatCurrency(cluster.averagePrice)} tone="accent" />
                    <SummaryPill label="Platform count" value={`${cluster.platformCount}`} />
                    <SummaryPill label="Vendor count" value={`${cluster.vendorCount}`} />
                    <SummaryPill label="Policy" value={cluster.selectedPolicy} tone="positive" />
                  </div>
                  <p className="mt-3 text-sm text-gray-400">{cluster.insightSummary}</p>
                </div>
              ))
            ) : (
              <p className="text-sm text-gray-400">No clusters available for this product yet.</p>
            )}
          </CardContent>
        </Card>
      </motion.div>

      <motion.div className="grid grid-cols-1 gap-6 xl:grid-cols-[1.1fr_0.9fr]" variants={pageVariants}>
        <Card>
          <CardHeader>
            <CardTitle>Competitive Landscape</CardTitle>
            <p className="text-sm text-gray-400">Observed market coverage and supplier/seller price positioning.</p>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-3">
              <ResponsiveContainer width="100%" height={320}>
                <ScatterChart>
                  <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} />
                  <XAxis type="number" dataKey="x" name="Count" tick={axisTick} axisLine={false} tickLine={false} />
                  <YAxis type="number" dataKey="y" name="Average Price" tick={axisTick} axisLine={false} tickLine={false} />
                  <ZAxis type="number" range={[60, 220]} />
                  <Tooltip content={<MoneyTooltip />} />
                  <Legend />
                  <Scatter data={dashboard.competitiveLandscape.supplierPoints} fill="#22d3ee" name="Suppliers" />
                  <Scatter data={dashboard.competitiveLandscape.sellerPoints} fill="#818cf8" name="Sellers" />
                </ScatterChart>
              </ResponsiveContainer>
            </div>
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              {dashboard.competitiveLandscape.platformSplit.map((item) => (
                <div key={item.name} className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
                  <p className="text-xs uppercase tracking-[0.24em] text-gray-400">Platform Split</p>
                  <p className="mt-2 text-lg font-semibold text-white">{item.name}</p>
                  <p className="text-sm text-cyan-200">{item.count} records</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Market Overview Summary</CardTitle>
            <p className="text-sm text-gray-400">The quick business view for a decision maker.</p>
          </CardHeader>
          <CardContent className="space-y-3">
            {dashboard.recommendationSummary.scoreBreakdown.map((item) => (
              <SummaryPill key={item.label} label={item.label} value={item.value} tone={item.tone} />
            ))}
            <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4 text-sm text-gray-300">
              <p className="font-medium text-white">Executive recommendation</p>
              <p className="mt-2">{dashboard.recommendationSummary.recommendationSentence}</p>
              <div className="mt-4 grid grid-cols-1 gap-3">
                <SummaryPill label="Supplier recommendation" value={dashboard.recommendationSummary.supplierRecommendation} tone="positive" />
                <SummaryPill label="Top risk" value={dashboard.recommendationSummary.topRisk} tone="warning" />
                <SummaryPill label="Best next action" value={dashboard.recommendationSummary.bestNextAction} tone="accent" />
              </div>
            </div>
            {hasMarketing && latestStrategy?.id && (
              <Button onClick={() => navigate(`/marketing?strategyId=${latestStrategy.id}`)}>
                View Marketing Strategy
                <ExternalLink className="ml-2 h-4 w-4" />
              </Button>
            )}
          </CardContent>
        </Card>
      </motion.div>
    </motion.div>
  );
}
