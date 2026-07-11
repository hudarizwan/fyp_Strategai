import { AlertTriangle, ArrowDownRight, BarChart3, DollarSign, Package, Target, TrendingDown, TrendingUp } from 'lucide-react';
import { ComparisonData } from '@/types';
import { Card, CardContent, CardHeader, CardTitle } from './ui/Card';
import Badge from './ui/Badge';

interface ComparisonSummaryProps {
  data: ComparisonData;
}

export default function ComparisonSummary({ data }: ComparisonSummaryProps) {
  const usingAnalytics = Boolean(data.analyticsRecommendation);
  const confidencePercent = data.confidenceScore > 0 ? `${(data.confidenceScore * 100).toFixed(0)}%` : '0%';
  const confidenceTone = data.confidenceScore >= 0.78 ? 'success' : data.confidenceScore >= 0.62 ? 'warning' : 'danger';
  const marginPercent = data.recommendedProfitMargin.toFixed(1);
  const pricingDelta = Math.max(0, data.recommendedSellPrice - data.recommendedBuyPrice);
  const approvalThreshold = data.analyticsRecommendation?.mcb_decision?.confidence_threshold ?? 0.7;
  const approvalThresholdSource = data.analyticsRecommendation?.mcb_decision?.threshold_source_tier ?? 'hardcoded 0.70';

  return (
    <Card className="border border-cyan-400/15 bg-gradient-to-br from-cyan-500/10 via-white/[0.04] to-indigo-500/10">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Target className="h-5 w-5 text-cyan-300" />
          Pricing Recommendation
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <div className="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/[0.04] p-4">
            <div className="rounded-xl bg-cyan-500/10 p-2">
              <Package className="h-5 w-5 text-cyan-300" />
            </div>
            <div>
              <p className="text-xs text-gray-400">Recommended Buy</p>
              <p className="text-lg font-bold">{data.recommendedBuyPrice.toLocaleString()} PKR</p>
              {usingAnalytics && <p className="text-xs text-gray-400">Model-led sourcing target</p>}
            </div>
          </div>

          <div className="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/[0.04] p-4">
            <div className="rounded-xl bg-indigo-500/10 p-2">
              <TrendingUp className="h-5 w-5 text-indigo-300" />
            </div>
            <div>
              <p className="text-xs text-gray-400">Recommended Sell</p>
              <p className="text-lg font-bold">{data.recommendedSellPrice.toLocaleString()} PKR</p>
              {usingAnalytics && <p className="text-xs text-gray-400">Model-led sales target</p>}
            </div>
          </div>

          <div className="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/[0.04] p-4">
            <div className={`rounded-xl p-2 ${data.recommendedSellPrice > data.recommendedBuyPrice ? 'bg-emerald-500/10' : 'bg-red-500/10'}`}>
              {data.recommendedSellPrice > data.recommendedBuyPrice ? (
                <TrendingUp className="h-5 w-5 text-emerald-300" />
              ) : (
                <TrendingDown className="h-5 w-5 text-red-300" />
              )}
            </div>
            <div>
              <p className="text-xs text-gray-400">Expected Margin</p>
              <p className={`text-lg font-bold ${data.recommendedSellPrice > data.recommendedBuyPrice ? 'text-emerald-300' : 'text-red-300'}`}>
                {marginPercent}%
              </p>
              <p className="text-xs text-gray-400">Confidence {confidencePercent}</p>
              <div className="mt-3 flex flex-wrap gap-2">
                <Badge variant="outline">MCB threshold {(approvalThreshold * 100).toFixed(0)}%</Badge>
                <Badge variant="secondary">{approvalThresholdSource}</Badge>
              </div>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
          <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
            <div className="mb-2 flex items-center justify-between gap-2">
              <span className="text-xs uppercase tracking-[0.18em] text-gray-400">Confidence</span>
              <Badge variant={confidenceTone === 'success' ? 'success' : confidenceTone === 'warning' ? 'warning' : 'destructive'}>
                {confidenceTone === 'success' ? 'High' : confidenceTone === 'warning' ? 'Moderate' : 'Low'}
              </Badge>
            </div>
            <p className="text-lg font-bold">{confidencePercent}</p>
            <p className="mt-1 text-xs text-gray-400">{data.confidenceReason || 'No confidence note available.'}</p>
          </div>

          <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
            <div className="mb-2 flex items-center justify-between gap-2">
              <span className="text-xs uppercase tracking-[0.18em] text-gray-400">Observed Spread</span>
              <ArrowDownRight className="h-4 w-4 text-cyan-300" />
            </div>
            <p className="text-lg font-bold">{data.observedMarketSpread.toLocaleString()} PKR</p>
            <p className="mt-1 text-xs text-gray-400">Raw retail max minus wholesale min.</p>
          </div>

          <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
            <div className="mb-2 flex items-center justify-between gap-2">
              <span className="text-xs uppercase tracking-[0.18em] text-gray-400">Sample Quality</span>
              {data.lowSampleWarning ? (
                <AlertTriangle className="h-4 w-4 text-amber-300" />
              ) : (
                <BarChart3 className="h-4 w-4 text-emerald-300" />
              )}
            </div>
            <p className="text-lg font-bold">{data.lowSampleWarning ? 'Low confidence' : 'Healthy sample'}</p>
            <p className="mt-1 text-xs text-gray-400">
              {data.lowSampleWarning
                ? data.lowSampleReason || 'Based on deduped supplier/listing counts.'
                : 'Wholesale and retail coverage is sufficient for a steadier recommendation.'}
            </p>
            <p className="mt-2 text-[11px] leading-5 text-gray-500">
              Low-sample checks use deduped supplier and listing counts, while the trend card shows raw run history.
            </p>
          </div>

          <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
            <div className="mb-2 flex items-center justify-between gap-2">
              <span className="text-xs uppercase tracking-[0.18em] text-gray-400">Net Delta</span>
              <DollarSign className="h-4 w-4 text-indigo-300" />
            </div>
            <p className="text-lg font-bold">{pricingDelta.toLocaleString()} PKR</p>
            <p className="mt-1 text-xs text-gray-400">Recommended sell minus recommended buy.</p>
          </div>
        </div>

        {data.reasoningBullets.length > 0 && (
          <div className="rounded-2xl border border-cyan-400/20 bg-white/[0.04] p-4">
            <h4 className="mb-3 flex items-center gap-2 font-semibold text-cyan-200">
              <Target className="h-4 w-4" />
              Recommendation reasoning
            </h4>
            <ul className="space-y-2">
              {data.reasoningBullets.map((item, index) => (
                <li key={`${item}-${index}`} className="flex items-start gap-2 text-sm text-gray-300">
                  <span className="mt-1 inline-block h-1.5 w-1.5 rounded-full bg-cyan-300" />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
            <h4 className="mb-3 flex items-center gap-2 font-semibold">
              <Package className="h-4 w-4 text-cyan-300" />
              Recommended Supplier
            </h4>
            {data.recommendedSupplier ? (
              <div className="space-y-2">
                <div className="flex items-center justify-between gap-3">
                  <span className="text-sm text-gray-400">Supplier:</span>
                  <span className="font-medium">{data.recommendedSupplier.supplier}</span>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <span className="text-sm text-gray-400">Platform:</span>
                  <Badge variant="outline">{data.recommendedSupplier.platform}</Badge>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <span className="text-sm text-gray-400">MOQ:</span>
                  <span className="font-medium">{data.recommendedSupplier.moq.toLocaleString()} pcs</span>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <span className="text-sm text-gray-400">Unit Price:</span>
                  <span className="font-medium">{data.recommendedSupplier.unit_price_pkr.toLocaleString()} PKR</span>
                </div>
              </div>
            ) : (
              <p className="text-sm text-gray-400">No supplier recommendation available.</p>
            )}
          </div>

          <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
            <h4 className="mb-3 flex items-center gap-2 font-semibold">
              <TrendingUp className="h-4 w-4 text-indigo-300" />
              Recommended Retail Platform
            </h4>
            {data.recommendedRetailPlatform ? (
              <div className="space-y-2">
                <div className="flex items-center justify-between gap-3">
                  <span className="text-sm text-gray-400">Platform:</span>
                  <Badge variant="outline">{data.recommendedRetailPlatform.platform}</Badge>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <span className="text-sm text-gray-400">Seller:</span>
                  <span className="font-medium">{data.recommendedRetailPlatform.seller}</span>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <span className="text-sm text-gray-400">List Price:</span>
                  <span className="font-medium">{data.recommendedRetailPlatform.list_price.toLocaleString()} PKR</span>
                </div>
              </div>
            ) : (
              <p className="text-sm text-gray-400">No retail recommendation available.</p>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
