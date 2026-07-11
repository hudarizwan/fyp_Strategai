import { useEffect, useState } from 'react';
import { Download, FileText, Calendar, Package, DollarSign, TrendingUp, AlertTriangle } from 'lucide-react';
import { motion } from 'framer-motion';
import { ScraperResponse, ReportPayload, PriceHistoryResponse } from '@/types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { calculateComparison } from '@/utils/comparison';
import { analyticsService, reportService } from '@/services/api';
import Button from '@/components/ui/Button';
import ErrorAlert from '@/components/ErrorAlert';
import { normalizeScraperResult } from '@/utils/normalizeScraperResult';
import PriceHistorySparkline from '@/components/PriceHistorySparkline';

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

const formatCurrency = (value?: number | null) => Number(value || 0).toLocaleString();

const formatDateTime = (value: string) =>
  `${new Intl.DateTimeFormat('en-US', {
    timeZone: 'UTC',
    month: 'short',
    day: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: true,
  })
    .format(new Date(value))
    .replace(',', '')} UTC`;

const slugify = (value: string) =>
  value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '') || 'report';

export default function Reports() {
  const [data, setData] = useState<ScraperResponse | null>(null);
  const [comparisonData, setComparisonData] = useState<any>(null);
  const [analyticsRecommendation, setAnalyticsRecommendation] = useState<any>(null);
  const [priceHistory, setPriceHistory] = useState<PriceHistoryResponse | null>(null);
  const [generatedAt] = useState(() => new Date().toISOString());
  const [downloadLoading, setDownloadLoading] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);

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
        setDownloadError('Failed to load report data from the current session.');
      }
    }
  }, []);

  const wholesaleItems = data?.wholesale.made_in_china || [];
  const retailItems = data?.retail || [];
  const resolvedAnalyticsRecommendation = analyticsRecommendation || comparisonData?.analyticsRecommendation || null;

  useEffect(() => {
    const loadPriceHistory = async () => {
      if (!resolvedAnalyticsRecommendation?.category || !data) {
        setPriceHistory(null);
        return;
      }

      try {
        const history = await analyticsService.getPriceHistory(
          data.product_name,
          resolvedAnalyticsRecommendation.category,
          12
        );
        setPriceHistory(history);
      } catch (err) {
        console.error('Failed to load price history:', err);
        setPriceHistory(null);
      }
    };

    void loadPriceHistory();
  }, [resolvedAnalyticsRecommendation, data]);

  const reportPayload: ReportPayload | null = data
    ? {
        report_title: 'Product Report',
        generated_at: generatedAt,
        product_name: data.product_name,
        summary: {
          total_suppliers: wholesaleItems.length,
          total_retailers: retailItems.length,
          recommended_buy_price: comparisonData?.recommendedBuyPrice || 0,
          recommended_sell_price: comparisonData?.recommendedSellPrice || 0,
          expected_profit_margin: comparisonData?.recommendedProfitMargin || 0,
          confidence_score: comparisonData?.confidenceScore || 0,
          low_sample_warning: comparisonData?.lowSampleWarning || false,
          low_sample_reason: comparisonData?.lowSampleReason || '',
          observed_wholesale_min: comparisonData?.observedWholesaleRange.min || 0,
          observed_wholesale_max: comparisonData?.observedWholesaleRange.max || 0,
          observed_retail_min: comparisonData?.observedRetailRange.min || 0,
          observed_retail_max: comparisonData?.observedRetailRange.max || 0,
          observed_market_spread: comparisonData?.observedMarketSpread || 0,
          best_wholesale_price: comparisonData?.bestWholesalePrice || 0,
          best_retail_price: comparisonData?.bestRetailPrice || 0,
          estimated_profit: comparisonData?.estimatedProfit || 0,
        },
        analytics_recommendation: resolvedAnalyticsRecommendation,
        price_history: priceHistory?.points || [],
        wholesale: wholesaleItems,
        retail: retailItems,
        recommendations: {
          supplier: comparisonData?.recommendedSupplier || null,
          retail_platform: comparisonData?.recommendedRetailPlatform || null,
        },
      }
    : null;

  const handleDownloadReport = async () => {
    if (!reportPayload) return;

    setDownloadLoading(true);
    setDownloadError(null);
    try {
      const blob = await reportService.downloadPdf(reportPayload);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `strategai-report-${slugify(data?.product_name || 'report')}-${Date.now()}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setDownloadError(err instanceof Error ? err.message : 'Failed to download the PDF report.');
    } finally {
      setDownloadLoading(false);
    }
  };

  if (!data) {
    return (
      <div className="container mx-auto min-h-[calc(100vh-8rem)] px-4 py-8">
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-gray-400">
              No report data available. Please search for a product first.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <motion.div
      className="container mx-auto space-y-8 px-4 py-8"
      initial="hidden"
      animate="visible"
      variants={pageVariants}
    >
      <motion.div className="mb-6 flex items-center justify-between" variants={itemVariants}>
        <div>
          <h1 className="mb-2 text-3xl font-bold text-white">Product Report</h1>
          <p className="text-gray-400">Comprehensive analysis for {data.product_name}</p>
        </div>
        <Button onClick={handleDownloadReport} disabled={downloadLoading}>
          {downloadLoading ? (
            <>
              <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
              Generating PDF...
            </>
          ) : (
            <>
              <Download className="mr-2 h-4 w-4" />
              Download PDF
            </>
          )}
        </Button>
      </motion.div>

      {downloadError && (
        <motion.div variants={itemVariants}>
          <ErrorAlert message={downloadError} onClose={() => setDownloadError(null)} />
        </motion.div>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-cyan-300" />
            Executive Summary
          </CardTitle>
        </CardHeader>
        <CardContent>
          {comparisonData?.lowSampleWarning && (
            <div className="mb-4 rounded-2xl border border-amber-400/20 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
              <div className="flex items-start gap-2">
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-300" />
                <div>
                  <p className="font-semibold">Low confidence - based on limited data</p>
                  <p className="text-amber-100/80">
                    {comparisonData.lowSampleReason || 'The recommendation is based on a sparse market sample.'}
                  </p>
                </div>
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
              <div className="mb-2 flex items-center gap-2">
                <Package className="h-4 w-4 text-cyan-300" />
                <span className="text-sm text-gray-400">Total Suppliers</span>
              </div>
              <p className="text-2xl font-bold">{wholesaleItems.length}</p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
              <div className="mb-2 flex items-center gap-2">
                <FileText className="h-4 w-4 text-indigo-300" />
                <span className="text-sm text-gray-400">Retail Listings</span>
              </div>
              <p className="text-2xl font-bold">{retailItems.length}</p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
              <div className="mb-2 flex items-center gap-2">
                <DollarSign className="h-4 w-4 text-cyan-300" />
                <span className="text-sm text-gray-400">Recommended Buy</span>
              </div>
              <p className="text-2xl font-bold">{formatCurrency(comparisonData?.recommendedBuyPrice)} PKR</p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
              <div className="mb-2 flex items-center gap-2">
                <TrendingUp className="h-4 w-4 text-emerald-300" />
                <span className="text-sm text-gray-400">Recommended Sell</span>
              </div>
              <p
                className={`text-2xl font-bold ${
                  (comparisonData?.recommendedSellPrice || 0) > (comparisonData?.recommendedBuyPrice || 0)
                    ? 'text-emerald-300'
                    : 'text-red-300'
                }`}
              >
                {formatCurrency(comparisonData?.recommendedSellPrice)} PKR
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Wholesale Suppliers Analysis</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {wholesaleItems.map((item, index) => (
              <div
                key={index}
                className="rounded-2xl border border-white/10 bg-white/[0.03] p-4 transition-colors hover:bg-white/[0.05]"
              >
                <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
                  <div>
                    <p className="text-sm text-gray-400">Supplier</p>
                    <p className="font-semibold">{item.supplier}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-400">Platform</p>
                    <p className="font-semibold">{item.platform}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-400">Unit Price</p>
                    <p className="font-semibold">{item.unit_price_pkr.toLocaleString()} PKR</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-400">MOQ</p>
                    <p className="font-semibold">{item.moq.toLocaleString()} units</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Retail Market Analysis</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {retailItems.map((item, index) => (
              <div
                key={index}
                className="rounded-2xl border border-white/10 bg-white/[0.03] p-4 transition-colors hover:bg-white/[0.05]"
              >
                <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
                  <div>
                    <p className="text-sm text-gray-400">Platform</p>
                    <p className="font-semibold">{item.platform}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-400">Seller</p>
                    <p className="font-semibold">{item.seller}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-400">List Price</p>
                    <p className="font-semibold">{item.list_price.toLocaleString()} PKR</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-400">Product Title</p>
                    <p className="line-clamp-2 font-semibold">{item.title}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {comparisonData && (
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Recommendations</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
            {comparisonData.recommendedSupplier && (
              <div className="rounded-2xl border border-cyan-400/15 bg-cyan-500/10 p-4">
                <h4 className="mb-2 font-semibold">Recommended Supplier</h4>
                <p className="mb-1 text-sm text-gray-300">
                  <strong>Supplier:</strong> {comparisonData.recommendedSupplier.supplier}
                </p>
                <p className="mb-1 text-sm text-gray-300">
                  <strong>Platform:</strong> {comparisonData.recommendedSupplier.platform}
                </p>
                <p className="mb-1 text-sm text-gray-300">
                  <strong>Unit Price:</strong>{' '}
                  {comparisonData.recommendedSupplier.unit_price_pkr.toLocaleString()} PKR
                </p>
                <p className="text-sm text-gray-300">
                  <strong>MOQ:</strong> {comparisonData.recommendedSupplier.moq.toLocaleString()}{' '}
                  units
                </p>
              </div>
            )}

            {comparisonData.recommendedRetailPlatform && (
              <div className="rounded-2xl border border-indigo-400/15 bg-indigo-500/10 p-4">
                <h4 className="mb-2 font-semibold">Recommended Retail Platform</h4>
                <p className="mb-1 text-sm text-gray-300">
                  <strong>Platform:</strong> {comparisonData.recommendedRetailPlatform.platform}
                </p>
                <p className="mb-1 text-sm text-gray-300">
                  <strong>Seller:</strong> {comparisonData.recommendedRetailPlatform.seller}
                </p>
                <p className="text-sm text-gray-300">
                  <strong>List Price:</strong>{' '}
                  {comparisonData.recommendedRetailPlatform.list_price.toLocaleString()} PKR
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        {priceHistory && resolvedAnalyticsRecommendation?.category && (
          <PriceHistorySparkline
            productName={data.product_name}
            category={resolvedAnalyticsRecommendation.category}
            historyData={priceHistory}
          />
        )}
      </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Calendar className="h-5 w-5 text-cyan-300" />
            Report Information
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2 text-sm">
            <p>
              <strong>Generated:</strong> {formatDateTime(generatedAt)}
            </p>
            <p>
              <strong>Product:</strong> {data.product_name}
            </p>
            <p>
              <strong>Data Sources:</strong> Made-in-China, Daraz, Mega.pk, Homeshopping.pk,
              Telemart.pk
            </p>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}
