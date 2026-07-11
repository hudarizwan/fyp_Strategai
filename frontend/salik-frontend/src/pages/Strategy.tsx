import { useEffect, useState } from 'react';
import { Target, TrendingUp, DollarSign, Package, CheckCircle2 } from 'lucide-react';
import { motion } from 'framer-motion';
import { ScraperResponse } from '@/types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { calculateComparison } from '@/utils/comparison';
import Badge from '@/components/ui/Badge';
import { normalizeScraperResult } from '@/utils/normalizeScraperResult';

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

export default function Strategy() {
  const [data, setData] = useState<ScraperResponse | null>(null);
  const [comparisonData, setComparisonData] = useState<any>(null);
  const [analyticsRecommendation, setAnalyticsRecommendation] = useState<any>(null);

  useEffect(() => {
    const storedData = sessionStorage.getItem('scraperResult');
    const storedAnalytics = sessionStorage.getItem('analyticsRecommendation');
    if (storedData) {
      try {
        const parsed = normalizeScraperResult(JSON.parse(storedData));
        setData(parsed);
        const analytics = storedAnalytics ? JSON.parse(storedAnalytics) : null;
        setAnalyticsRecommendation(analytics);
        const comparison = calculateComparison(
          parsed.wholesale.made_in_china || [],
          parsed.retail || [],
          analytics
        );
        setComparisonData(comparison);
      } catch (err) {
        console.error('Failed to parse data:', err);
      }
    }
  }, []);

  if (!data) {
    return (
      <div className="container mx-auto min-h-[calc(100vh-8rem)] px-4 py-8">
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-gray-400">
              No strategy data available. Please search for a product first.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const wholesaleItems = data.wholesale.made_in_china || [];
  const retailItems = data.retail || [];
  const observedMarketSpread = comparisonData?.observedMarketSpread ?? comparisonData?.estimatedProfit ?? 0;
  const recommendationConfidence = analyticsRecommendation?.confidence_score ?? comparisonData?.confidenceScore ?? 0;
  const recommendationMargin = analyticsRecommendation?.expected_profit_margin ?? comparisonData?.recommendedProfitMargin ?? 0;
  const resolvedApprovalThreshold = analyticsRecommendation?.mcb_decision?.confidence_threshold ?? 0.7;
  const approvalThresholdSource = analyticsRecommendation?.mcb_decision?.threshold_source_tier ?? 'hardcoded 0.70';
  const recommendationLooksStrong = Boolean(analyticsRecommendation) && recommendationConfidence >= resolvedApprovalThreshold && !analyticsRecommendation?.low_sample_warning && recommendationMargin > 0;

  const strategies = [
    {
      title: 'Optimal Purchase Strategy',
      icon: Package,
      items: comparisonData?.recommendedSupplier
        ? [
            {
              label: 'Recommended Supplier',
              value: comparisonData.recommendedSupplier.supplier,
              status: 'success',
            },
            {
              label: 'Minimum Order Quantity',
              value: `${comparisonData.recommendedSupplier.moq.toLocaleString()} units`,
              status: 'info',
            },
            {
              label: 'Unit Cost',
              value: `${comparisonData.recommendedSupplier.unit_price_pkr.toLocaleString()} PKR`,
              status: 'info',
            },
            {
              label: 'Lead Time',
              value: comparisonData.recommendedSupplier.lead_time || 'N/A',
              status: 'info',
            },
          ]
        : [],
    },
    {
      title: 'Sales Strategy',
      icon: TrendingUp,
      items: comparisonData?.recommendedRetailPlatform
        ? [
            {
              label: 'Target Platform',
              value: comparisonData.recommendedRetailPlatform.platform,
              status: 'success',
            },
            {
              label: 'Competitive Price Range',
              value: `${Math.min(...retailItems.map((r) => r.list_price)).toLocaleString()} - ${Math.max(...retailItems.map((r) => r.list_price)).toLocaleString()} PKR`,
              status: 'info',
            },
            {
              label: 'Recommended Selling Price',
              value: analyticsRecommendation?.recommended_sell_price_pkr
                ? `${analyticsRecommendation.recommended_sell_price_pkr.toLocaleString()} PKR`
                : comparisonData.recommendedRetailPlatform.list_price
                ? `${(comparisonData.recommendedRetailPlatform.list_price * 0.95).toLocaleString()} PKR`
                : 'N/A',
              status: 'success',
            },
            {
              label: 'Profit Margin',
              value: analyticsRecommendation?.expected_profit_margin
                ? `${analyticsRecommendation.expected_profit_margin.toFixed(1)}%`
                : observedMarketSpread > 0
                ? `${((observedMarketSpread / comparisonData.bestWholesalePrice) * 100).toFixed(1)}%`
                : '0%',
              status: observedMarketSpread > 0 ? 'success' : 'warning',
            },
          ]
        : [],
    },
    {
      title: 'Market Insights',
      icon: Target,
      items: [
        {
          label: 'Total Suppliers Found',
          value: wholesaleItems.length.toString(),
          status: 'info',
        },
        {
          label: 'Total Retail Competitors',
          value: retailItems.length.toString(),
          status: 'info',
        },
        {
          label: 'Market Opportunity',
          value: recommendationLooksStrong
            ? 'Model-backed opportunity - confidence and margin are aligned'
            : analyticsRecommendation
            ? 'Caution - model confidence or margin is limited'
            : observedMarketSpread > 0
            ? 'Positive spread - room for a pricing strategy'
            : 'Tight spread - consider sourcing improvements',
          status: recommendationLooksStrong ? 'success' : 'warning',
        },
      ],
    },
  ];

  const recommendations = [
    {
      type: 'success',
      icon: CheckCircle2,
      title: 'Recommended Actions',
      items: recommendationLooksStrong
        ? [
            'Purchase from recommended supplier at optimal MOQ',
            `Target selling price: ${comparisonData.recommendedRetailPlatform?.list_price ? (comparisonData.recommendedRetailPlatform.list_price * 0.95).toLocaleString() : 'N/A'} PKR`,
            'Focus on the recommended retail platform for maximum visibility',
            'Consider bulk purchasing to reduce unit costs further',
          ]
        : analyticsRecommendation
        ? [
            'The model is not confident enough to recommend an aggressive launch yet',
            'Review the confidence notes before placing an order',
            'Consider smaller test quantities or a second data pass',
            'Compare against alternative suppliers or product variants',
          ]
        : observedMarketSpread > 0
        ? [
            'Purchase from recommended supplier at optimal MOQ',
            `Target selling price: ${comparisonData.recommendedRetailPlatform?.list_price ? (comparisonData.recommendedRetailPlatform.list_price * 0.95).toLocaleString() : 'N/A'} PKR`,
            'Focus on the recommended retail platform for maximum visibility',
            'Consider bulk purchasing to reduce unit costs further',
          ]
        : [
            'This product may not support a strong opportunity at current market rates',
            'Consider negotiating better wholesale prices',
            'Explore alternative suppliers or products',
            'Review market demand before investing',
          ],
    },
  ];

  return (
    <motion.div
      className="container mx-auto space-y-8 px-4 py-8"
      initial="hidden"
      animate="visible"
      variants={pageVariants}
    >
      <motion.div className="mb-6" variants={itemVariants}>
        <h1 className="mb-2 text-3xl font-bold text-white">Sales Strategy</h1>
        <p className="text-gray-400">
          AI-powered recommendations for {data.product_name}
        </p>
      </motion.div>

      <motion.div className="grid grid-cols-1 gap-6 md:grid-cols-3" variants={pageVariants}>
        {strategies.map((strategy, index) => {
          const Icon = strategy.icon;
          return (
            <Card key={index}>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <Icon className="h-5 w-5 text-cyan-300" />
                  <CardTitle className="text-lg">{strategy.title}</CardTitle>
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                {strategy.items.length > 0 ? (
                  strategy.items.map((item, itemIndex) => (
                    <div
                      key={itemIndex}
                      className="flex items-start justify-between gap-3 rounded-xl border border-white/10 bg-white/[0.03] p-3"
                    >
                      <span className="text-sm text-gray-400">{item.label}:</span>
                      <div className="text-right">
                        <span className="text-sm font-medium">{item.value}</span>
                        {item.status === 'success' && (
                          <Badge variant="emerald" className="ml-2">
                            Recommended
                          </Badge>
                        )}
                        {item.label === 'Market Opportunity' && (
                          <div className="mt-2 flex justify-end">
                            <Badge variant="outline">
                              MCB threshold {(resolvedApprovalThreshold * 100).toFixed(0)}% - {approvalThresholdSource}
                            </Badge>
                          </div>
                        )}
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="text-sm text-gray-400">No data available</p>
                )}
              </CardContent>
            </Card>
          );
        })}
      </motion.div>

      {recommendations.map((rec, index) => {
        const Icon = rec.icon;
        return (
          <Card key={index} className="border border-cyan-400/15">
            <CardHeader>
              <div className="flex items-center gap-2">
                <Icon
                  className={`h-5 w-5 ${
                    rec.type === 'success' ? 'text-emerald-300' : 'text-amber-300'
                  }`}
                />
                <CardTitle>{rec.title}</CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2">
                {rec.items.map((item, itemIndex) => (
                  <li key={itemIndex} className="flex items-start gap-2">
                    <CheckCircle2 className="mt-0.5 h-4 w-4 flex-shrink-0 text-cyan-300" />
                    <span className="text-sm text-gray-300">{item}</span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        );
      })}

      {comparisonData && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <DollarSign className="h-5 w-5 text-cyan-300" />
              Observed Market Range
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
              <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
                <p className="mb-1 text-sm text-gray-400">Best Wholesale Price</p>
                <p className="text-2xl font-bold">
                  {comparisonData.bestWholesalePrice.toLocaleString()} PKR
                </p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
                <p className="mb-1 text-sm text-gray-400">Best Retail Price</p>
                <p className="text-2xl font-bold">
                  {comparisonData.bestRetailPrice.toLocaleString()} PKR
                </p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
                <p className="mb-1 text-sm text-gray-400">Observed Market Spread</p>
                <p
                  className={`text-2xl font-bold ${
                    observedMarketSpread > 0 ? 'text-emerald-300' : 'text-red-300'
                  }`}
                >
                  {observedMarketSpread.toLocaleString()} PKR
                </p>
                <p className="mt-1 text-xs text-gray-400">Raw retail max minus wholesale min.</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </motion.div>
  );
}






