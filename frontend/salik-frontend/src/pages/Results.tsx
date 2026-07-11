import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Package, ShoppingBag, Sparkles } from 'lucide-react';
import { motion } from 'framer-motion';
import { marketingService, scraperService } from '@/services/api';
import { MarketingStrategySummary, ScraperResponse } from '@/types';
import WholesaleCard from '@/components/WholesaleCard';
import RetailCard from '@/components/RetailCard';
import ComparisonSummary from '@/components/ComparisonSummary';
import PriceHistorySparkline from '@/components/PriceHistorySparkline';
import OutcomeCapturePanel from '@/components/OutcomeCapturePanel';
import LoaderSkeleton from '@/components/LoaderSkeleton';
import ErrorAlert from '@/components/ErrorAlert';
import Button from '@/components/ui/Button';
import { calculateComparison } from '@/utils/comparison';
import { getMicSearchLink, normalizeScraperResult } from '@/utils/normalizeScraperResult';

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

export default function Results() {
  const navigate = useNavigate();
  const [data, setData] = useState<ScraperResponse | null>(null);
  const [analyticsRecommendation, setAnalyticsRecommendation] = useState<any>(null);
  const [analyticsLoading, setAnalyticsLoading] = useState(false);
  const [analyticsError, setAnalyticsError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [marketingLoading, setMarketingLoading] = useState(false);
  const [marketingLookupLoading, setMarketingLookupLoading] = useState(false);
  const [marketingError, setMarketingError] = useState<string | null>(null);
  const [latestStrategy, setLatestStrategy] = useState<MarketingStrategySummary | null>(null);
  const autoMarketingStartedRef = useRef(false);

  useEffect(() => {
    const storedData = sessionStorage.getItem('scraperResult');
    const storedAnalytics = sessionStorage.getItem('analyticsRecommendation');
    const storedStrategy = sessionStorage.getItem('marketingStrategy');
    if (storedData) {
      try {
        const parsed = normalizeScraperResult(JSON.parse(storedData));
        setData(parsed);
        setAnalyticsRecommendation(storedAnalytics ? JSON.parse(storedAnalytics) : null);
        setLatestStrategy(storedStrategy ? JSON.parse(storedStrategy) : null);
      } catch {
        setError('Failed to parse stored data');
      }
    } else {
      setError('No results found. Please search for a product first.');
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    const runAnalytics = async () => {
      if (!data || analyticsRecommendation || analyticsLoading) return;

      const storedContext = sessionStorage.getItem('searchContext');
      if (!storedContext) return;

      try {
        const { productName, category } = JSON.parse(storedContext) as {
          productName?: string;
          category?: string;
        };

        if (!productName || !category) return;

        setAnalyticsLoading(true);
        setAnalyticsError(null);
        const analytics = await scraperService.analyzeProduct(productName, category);
        sessionStorage.setItem('analyticsRecommendation', JSON.stringify(analytics));
        setAnalyticsRecommendation(analytics);
      } catch (err) {
        setAnalyticsError(
          err instanceof Error ? err.message : 'Analytics is taking longer than expected.'
        );
      } finally {
        setAnalyticsLoading(false);
      }
    };

    void runAnalytics();
  }, [analyticsLoading, analyticsRecommendation, data]);

  useEffect(() => {
    const syncLatestStrategy = async () => {
      if (!analyticsRecommendation || !data) {
        return;
      }

      const scraperResult = JSON.parse(sessionStorage.getItem('scraperResult') || '{}');
      const basePayload = {
        product_name: data.product_name,
        category: analyticsRecommendation.category || '',
        analytics_result: analyticsRecommendation,
        scraper_result: scraperResult,
        pipeline_run_id: analyticsRecommendation.pipeline_run_id,
        analytics_result_id: analyticsRecommendation.analytics_result_id,
        product_cluster_id: analyticsRecommendation.product_cluster_id,
        generation_type: 'initial' as const,
      };

      setMarketingLookupLoading(true);
      try {
        let strategy: MarketingStrategySummary | null = null;

        if (analyticsRecommendation.marketing_strategy_id) {
          try {
            strategy = await marketingService.getById(
              analyticsRecommendation.marketing_strategy_id
            );
          } catch {
            strategy = null;
          }
        }

        if (!strategy && analyticsRecommendation.analytics_result_id) {
          try {
            strategy = await marketingService.getLatestByAnalytics(
              analyticsRecommendation.analytics_result_id
            );
          } catch {
            strategy = null;
          }
        }

        if (!strategy && analyticsRecommendation.pipeline_run_id) {
          try {
            strategy = await marketingService.getLatestByPipeline(
              analyticsRecommendation.pipeline_run_id
            );
          } catch {
            strategy = null;
          }
        }

        if (strategy) {
          setLatestStrategy(strategy);
          sessionStorage.setItem('marketingStrategy', JSON.stringify(strategy));
          return;
        }

        setLatestStrategy(null);

        if (!autoMarketingStartedRef.current) {
          autoMarketingStartedRef.current = true;
          setMarketingLoading(true);
          setMarketingError(null);
          const generatedStrategy = await marketingService.generate(basePayload);
          sessionStorage.setItem('marketingStrategy', JSON.stringify(generatedStrategy));
          setLatestStrategy(generatedStrategy);
        }
      } catch (err) {
        setMarketingError(
          err instanceof Error ? err.message : 'Failed to generate marketing strategy'
        );
      } finally {
        setMarketingLookupLoading(false);
        setMarketingLoading(false);
      }
    };

    void syncLatestStrategy();
  }, [analyticsRecommendation, data]);

  const ensureAnalyticsReady = async () => {
    if (analyticsRecommendation) {
      return analyticsRecommendation;
    }

    const storedContext = sessionStorage.getItem('searchContext');
    const parsedContext = storedContext
      ? (JSON.parse(storedContext) as { productName?: string; category?: string })
      : {};
    const productName = parsedContext.productName || data?.product_name;
    const category = parsedContext.category || '';

    if (!productName) {
      throw new Error('Product search details are incomplete. Please search again.');
    }

    setAnalyticsLoading(true);
    setAnalyticsError(null);
    try {
      const analytics = await scraperService.analyzeProduct(productName, category);
      sessionStorage.setItem('analyticsRecommendation', JSON.stringify(analytics));
      setAnalyticsRecommendation(analytics);
      return analytics;
    } catch (err) {
      const message =
        err instanceof Error ? err.message : 'Analytics could not be prepared for marketing.';
      setAnalyticsError(message);
      throw new Error(message);
    } finally {
      setAnalyticsLoading(false);
    }
  };

  const runMarketingGeneration = async (regenerate: boolean) => {
    if (!data) return;
    setMarketingLoading(true);
    setMarketingError(null);
    try {
      const analyticsResult = await ensureAnalyticsReady();
      const scraperResult = JSON.parse(sessionStorage.getItem('scraperResult') || '{}');
      const payload = {
        product_name: data.product_name,
        category: analyticsResult.category || '',
        analytics_result: analyticsResult,
        scraper_result: scraperResult,
        pipeline_run_id: analyticsResult.pipeline_run_id,
        analytics_result_id: analyticsResult.analytics_result_id,
        product_cluster_id: analyticsResult.product_cluster_id,
        parent_strategy_id: regenerate ? latestStrategy?.id : undefined,
        generation_type: (regenerate ? 'regenerate' : 'initial') as 'initial' | 'regenerate',
      };
      const strategy = regenerate
        ? await marketingService.regenerate(payload)
        : await marketingService.generate(payload);
      sessionStorage.setItem('marketingStrategy', JSON.stringify(strategy));
      setLatestStrategy(strategy);
      navigate(`/marketing?strategyId=${strategy.id}`);
    } catch (err) {
      setMarketingError(
        err instanceof Error ? err.message : 'Failed to generate marketing strategy'
      );
    } finally {
      setMarketingLoading(false);
    }
  };

  const handleViewMarketing = async () => {
    if (!latestStrategy) return;
    try {
      const strategy = await marketingService.getById(latestStrategy.id);
      sessionStorage.setItem('marketingStrategy', JSON.stringify(strategy));
      navigate(`/marketing?strategyId=${strategy.id}`);
    } catch (err) {
      setMarketingError(
        err instanceof Error ? err.message : 'Failed to load marketing strategy'
      );
    }
  };

  if (loading) {
    return (
      <div className="container mx-auto min-h-[calc(100vh-8rem)] px-4 py-8">
        <LoaderSkeleton />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="container mx-auto min-h-[calc(100vh-8rem)] px-4 py-8">
        <ErrorAlert message={error || 'No data available'} />
        <Button onClick={() => navigate('/')} className="mt-4">
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Dashboard
        </Button>
      </div>
    );
  }

  const comparisonData = calculateComparison(
    data.wholesale.made_in_china || [],
    data.retail || [],
    analyticsRecommendation
  );

  const wholesaleItems = data.wholesale.made_in_china || [];
  const retailItems = data.retail || [];

  const historyTarget = analyticsRecommendation?.analytics_result_id
    ? `/marketing/history?analyticsResultId=${analyticsRecommendation.analytics_result_id}`
    : analyticsRecommendation?.pipeline_run_id
      ? `/marketing/history?pipelineRunId=${analyticsRecommendation.pipeline_run_id}`
      : latestStrategy?.analytics_result_id
        ? `/marketing/history?analyticsResultId=${latestStrategy.analytics_result_id}`
        : latestStrategy?.pipeline_run_id
          ? `/marketing/history?pipelineRunId=${latestStrategy.pipeline_run_id}`
          : '/marketing/history';

  return (
    <motion.div
      className="container mx-auto space-y-8 px-4 py-8"
      initial="hidden"
      animate="visible"
      variants={pageVariants}
    >
      <motion.div className="mb-6 flex items-center justify-between" variants={itemVariants}>
        <div>
          <h1 className="mb-2 text-3xl font-bold text-white">Product Analysis Results</h1>
          <p className="text-gray-400">{data.product_name}</p>
        </div>
        <Button variant="outline" onClick={() => navigate('/')}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Dashboard
        </Button>
      </motion.div>

      {analyticsRecommendation && comparisonData && (
        <div className="space-y-4">
          <ComparisonSummary data={comparisonData} />
          {analyticsRecommendation.category && (
            <PriceHistorySparkline
              productName={data.product_name}
              category={analyticsRecommendation.category}
            />
          )}
        </div>
      )}

      {analyticsRecommendation && (
        <OutcomeCapturePanel
          key={analyticsRecommendation.analytics_result_id || analyticsRecommendation.pipeline_run_id || data.product_name}
          analyticsRecommendation={analyticsRecommendation}
          productName={data.product_name}
          category={analyticsRecommendation.category || ''}
        />
      )}

      <motion.div
        className="rounded-2xl border border-white/10 bg-white/[0.04] py-6 text-center shadow-[0_16px_40px_rgba(2,6,23,0.16)] backdrop-blur-xl"
        variants={itemVariants}
      >
        <p className="text-sm text-gray-300">
          {latestStrategy
            ? 'A saved marketing strategy already exists for this analysis.'
            : analyticsRecommendation
              ? marketingLoading
                ? 'Analytics is complete. Marketing strategy is generating in the background.'
                : 'Analytics complete - generate a full go-to-market strategy.'
              : 'Scraping is complete. Marketing actions unlock as soon as analytics finishes.'}
        </p>

        {marketingLookupLoading && (
          <p className="mt-2 text-xs text-gray-500">
            Checking for saved marketing strategy...
          </p>
        )}

        {!analyticsRecommendation && (
          <div className="mt-2">
            <p className="text-xs text-gray-500">
              {analyticsLoading
                ? 'Running analytics in the background...'
                : analyticsError || 'Waiting for analytics before generation can start.'}
            </p>
            {analyticsLoading && (
              <div className="mt-3 flex items-center justify-center gap-2 text-sm text-cyan-300">
                <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-cyan-300 border-t-transparent" />
                Preparing pricing and decision intelligence
              </div>
            )}
          </div>
        )}

        {analyticsRecommendation && marketingLoading && !latestStrategy && (
          <div className="mt-2">
            <p className="text-xs text-gray-500">
              Marketing generation started automatically after analytics.
            </p>
            <div className="mt-3 flex items-center justify-center gap-2 text-sm text-emerald-300">
              <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-emerald-300 border-t-transparent" />
              Building your marketing strategy
            </div>
          </div>
        )}

        {latestStrategy && (
          <div className="mt-2 text-center text-sm text-gray-400">
            <p>
              Version {latestStrategy.version_number || 1} ·{' '}
              {new Date(latestStrategy.created_at).toLocaleString('en-PK')}
            </p>
          </div>
        )}

        {(analyticsError || marketingError) && (
          <div className="mt-4 space-y-3 px-4">
            {analyticsError && (
              <ErrorAlert message={analyticsError} onClose={() => setAnalyticsError(null)} />
            )}
            {marketingError && (
              <ErrorAlert message={marketingError} onClose={() => setMarketingError(null)} />
            )}
          </div>
        )}

        <div className="mt-5 flex flex-wrap justify-center gap-3">
          <Button onClick={handleViewMarketing} disabled={!latestStrategy || marketingLoading}>
            View Marketing Strategy
          </Button>
          <Button
            onClick={() => void runMarketingGeneration(Boolean(latestStrategy))}
            disabled={marketingLoading || marketingLookupLoading}
            variant={latestStrategy ? 'outline' : 'default'}
          >
            {marketingLoading ? (
              <>
                <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                {latestStrategy ? 'Regenerating...' : 'Generating strategy...'}
              </>
            ) : (
              <>
                <Sparkles className="h-4 w-4" />
                {latestStrategy ? 'Regenerate Strategy' : 'Generate Marketing Strategy'}
              </>
            )}
          </Button>
          <Button
            variant="outline"
            disabled={
              !latestStrategy &&
              !analyticsRecommendation?.analytics_result_id &&
              !analyticsRecommendation?.pipeline_run_id
            }
            onClick={() => navigate(historyTarget)}
          >
            View Strategy History
          </Button>
        </div>
      </motion.div>

      {wholesaleItems.length > 0 && (
        <motion.section variants={itemVariants}>
          <div className="mb-6 flex items-center gap-2">
            <Package className="h-6 w-6 text-cyan-300" />
            <h2 className="text-2xl font-semibold text-white">Wholesale Suppliers</h2>
            <span className="text-sm text-gray-400">({wholesaleItems.length} found)</span>
          </div>
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
            {wholesaleItems.map((item, index) => (
              <WholesaleCard
                key={index}
                item={item}
                linkUrl={item.source_url || getMicSearchLink(data)}
              />
            ))}
          </div>
        </motion.section>
      )}

      {retailItems.length > 0 && (
        <motion.section variants={itemVariants}>
          <div className="mb-6 flex items-center gap-2">
            <ShoppingBag className="h-6 w-6 text-indigo-300" />
            <h2 className="text-2xl font-semibold text-white">Retail Market</h2>
            <span className="text-sm text-gray-400">({retailItems.length} found)</span>
          </div>
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
            {retailItems.map((item, index) => (
              <RetailCard key={index} item={item} />
            ))}
          </div>
        </motion.section>
      )}

      {wholesaleItems.length === 0 && retailItems.length === 0 && (
        <motion.div className="py-12 text-center" variants={itemVariants}>
          <p className="text-gray-400">No data found for this product.</p>
        </motion.div>
      )}
    </motion.div>
  );
}
