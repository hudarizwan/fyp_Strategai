import { WholesaleItem, RetailItem, ComparisonData, AnalyticsRecommendation, PriceRange } from '../types';

const EMPTY_RANGE: PriceRange = { min: 0, max: 0 };

const getPriceRange = (values: number[]): PriceRange => {
  if (values.length === 0) {
    return EMPTY_RANGE;
  }
  return {
    min: Math.min(...values),
    max: Math.max(...values),
  };
};

const buildReasoningBullets = (analyticsRecommendation?: AnalyticsRecommendation | null): string[] => {
  if (!analyticsRecommendation) {
    return [];
  }

  const mcbReasoningTrail = Array.isArray(analyticsRecommendation.mcb_decision?.reasoning_trail)
    ? analyticsRecommendation.mcb_decision.reasoning_trail
    : [];

  const bullets = [
    ...(analyticsRecommendation.reasoning_bullets || []),
    ...mcbReasoningTrail,
    ...(analyticsRecommendation.low_sample_warning && analyticsRecommendation.low_sample_reason
      ? [`Low confidence - based on limited data: ${analyticsRecommendation.low_sample_reason}`]
      : []),
  ];

  if (bullets.length > 0) {
    return Array.from(new Set(bullets));
  }

  if (analyticsRecommendation.confidence_reason) {
    return [analyticsRecommendation.confidence_reason];
  }

  return [];
};

export const calculateComparison = (
  wholesale: WholesaleItem[],
  retail: RetailItem[],
  analyticsRecommendation?: AnalyticsRecommendation | null
): ComparisonData => {
  const wholesalePrices = wholesale.map((item) => item.unit_price_pkr).filter((price) => price > 0);
  const retailPrices = retail.map((item) => item.list_price).filter((price) => price > 0);

  const wholesaleRange = getPriceRange(wholesalePrices);
  const retailRange = getPriceRange(retailPrices);
  const wholesaleSampleCount = analyticsRecommendation?.wholesale_vendors_count ?? wholesale.length;
  const retailSampleCount = analyticsRecommendation?.retail_sellers_count ?? retail.length;
  const sampleThresholds = analyticsRecommendation?.sample_thresholds ?? { wholesale_vendors: 3, retail_listings: 5 };
  const lowSampleWarning =
    analyticsRecommendation?.low_sample_warning ??
    (wholesaleSampleCount < (sampleThresholds.wholesale_vendors ?? 3) ||
      retailSampleCount < (sampleThresholds.retail_listings ?? 5));
  const lowSampleReason =
    analyticsRecommendation?.low_sample_reason ||
    (lowSampleWarning
      ? `wholesale vendors below threshold (${wholesaleSampleCount}/${sampleThresholds.wholesale_vendors ?? 3}); retail listings below threshold (${retailSampleCount}/${sampleThresholds.retail_listings ?? 5})`
      : '');

  if (wholesale.length === 0 || retail.length === 0) {
    return {
      bestRetailPrice: 0,
      bestWholesalePrice: 0,
      estimatedProfit: 0,
      observedMarketSpread: 0,
      observedWholesaleRange: wholesaleRange,
      observedRetailRange: retailRange,
      recommendedBuyPrice: analyticsRecommendation?.recommended_buy_price_pkr || 0,
      recommendedSellPrice: analyticsRecommendation?.recommended_sell_price_pkr || 0,
      recommendedProfitMargin: analyticsRecommendation?.expected_profit_margin || 0,
      confidenceScore: analyticsRecommendation?.confidence_score || 0,
      confidenceReason: analyticsRecommendation?.confidence_reason || '',
      lowSampleWarning,
      lowSampleReason,
      reasoningBullets: buildReasoningBullets(analyticsRecommendation),
      recommendedSupplier: null,
      recommendedRetailPlatform: null,
      analyticsRecommendation: analyticsRecommendation ?? null,
    };
  }

  const bestWholesale = wholesale.reduce((best, current) => {
    return current.unit_price_pkr < best.unit_price_pkr ? current : best;
  }, wholesale[0]);

  const bestRetail = retail.reduce((best, current) => {
    return current.list_price > best.list_price ? current : best;
  }, retail[0]);

  const observedMarketSpread = Math.max(0, bestRetail.list_price - bestWholesale.unit_price_pkr);
  const recommendedBuyPrice = analyticsRecommendation?.recommended_buy_price_pkr ?? bestWholesale.unit_price_pkr;
  const recommendedSellPrice = analyticsRecommendation?.recommended_sell_price_pkr ?? bestRetail.list_price;
  const recommendedProfitMargin =
    analyticsRecommendation?.expected_profit_margin ??
    (recommendedBuyPrice > 0 ? ((Math.max(0, recommendedSellPrice - recommendedBuyPrice) / recommendedBuyPrice) * 100) : 0);
  const confidenceScore = analyticsRecommendation?.confidence_score ?? 0;
  const confidenceReason = analyticsRecommendation?.confidence_reason ?? '';

  return {
    bestRetailPrice: bestRetail.list_price,
    bestWholesalePrice: bestWholesale.unit_price_pkr,
    estimatedProfit: observedMarketSpread,
    observedMarketSpread,
    observedWholesaleRange: wholesaleRange,
    observedRetailRange: retailRange,
    recommendedBuyPrice,
    recommendedSellPrice,
    recommendedProfitMargin,
    confidenceScore,
    confidenceReason,
    lowSampleWarning,
    lowSampleReason,
    reasoningBullets: buildReasoningBullets(analyticsRecommendation),
    recommendedSupplier: bestWholesale,
    recommendedRetailPlatform: bestRetail,
    analyticsRecommendation: analyticsRecommendation ?? null,
  };
};
