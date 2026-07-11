import { AnalyticsRecommendation, MarketingStrategyBase, RetailItem, ScraperResponse, WholesaleItem } from '../types';

type AnyRecord = Record<string, any>;

export interface HistogramBin {
  label: string;
  min: number;
  max: number;
  count: number;
}

export interface PriceStats {
  count: number;
  min: number;
  max: number;
  mean: number;
  median: number;
  q1: number;
  q3: number;
  stdDev: number;
  coefficientOfVariation: number;
  range: number;
  histogram: HistogramBin[];
}

export interface LeaderboardEntry {
  name: string;
  count: number;
  averagePrice: number;
  minPrice: number;
  maxPrice: number;
  averageMoq: number;
  platforms: string[];
  origins: string[];
  sampleUrl?: string;
}

export interface EvidenceCard {
  section: string;
  recommendation: string;
  evidence: string[];
}

export interface PricingModeCard {
  key: 'competitive' | 'balanced' | 'premium';
  label: string;
  price: number;
  marginPercent: number;
  fitScore: number;
  confidenceLabel: 'High' | 'Medium' | 'Low';
  evidence: string[];
  reason: string;
  selected: boolean;
}

export interface ClusterCard {
  clusterKey: string;
  clusterDbId?: string | null;
  status: string;
  confidenceScore: number;
  confidenceReason: string;
  canonicalTitle: string;
  averagePrice: number;
  platformCount: number;
  vendorCount: number;
  selectedPolicy: string;
  insightSummary: string;
}

export interface AnalyticsDashboardModel {
  productName: string;
  category: string;
  marketOverview: {
    wholesale: PriceStats;
    retail: PriceStats;
    observedMarketSpread: number;
    recommendedBuy: number;
    recommendedSell: number;
    comparisonData: Array<{ name: string; wholesale: number; retail: number; recommended: number }>;
    wholesaleHistogram: HistogramBin[];
    retailHistogram: HistogramBin[];
    takeaway: string;
    varianceLabel: string;
    stabilityLabel: string;
  };
  supplierIntelligence: {
    leaders: LeaderboardEntry[];
    lowest: LeaderboardEntry | null;
    median: LeaderboardEntry | null;
    highest: LeaderboardEntry | null;
    mostCompetitive: LeaderboardEntry | null;
    supplierCount: number;
  };
  retailMarket: {
    leaders: LeaderboardEntry[];
    lowest: LeaderboardEntry | null;
    median: LeaderboardEntry | null;
    highest: LeaderboardEntry | null;
    mostCompetitive: LeaderboardEntry | null;
    sellerCount: number;
    platformSplit: Array<{ name: string; count: number }>;
    topListings: RetailItem[];
  };
  marketOpportunity: {
    cards: Array<{ label: string; value: number; note: string }>;
    radar: Array<{ metric: string; value: number }>;
    confidenceLabel: string;
    competitionLabel: string;
    coverageScore: number;
    priceStabilityScore: number;
    demandScore: number;
    riskScore: number;
  };
  pricingIntelligence: {
    backendPolicy: string;
    selectedPosture: PricingModeCard['key'];
    selectedModeLabel: string;
    selectedModeReason: string;
    selectionReason: string[];
    clampReasons: string[];
    confidenceReason: string;
    confidenceLabel: string;
    confidenceScore: number;
    grossMargin: number;
    grossProfit: number;
    observedSpread: number;
    pricingModes: PricingModeCard[];
    backendEvidence: EvidenceCard[];
    pricingSummary: Array<{ label: string; value: string; tone?: 'positive' | 'warning' | 'danger' | 'accent' | 'default' }>;
  };
  evidenceExplorer: { cards: EvidenceCard[] };
  clusterVisualization: { clusters: ClusterCard[]; clusterCount: number };
  competitiveLandscape: {
    supplierPoints: Array<{ name: string; x: number; y: number; group: 'supplier' | 'seller' }>;
    sellerPoints: Array<{ name: string; x: number; y: number; group: 'supplier' | 'seller' }>;
    platformSplit: Array<{ name: string; count: number }>;
  };
  recommendationSummary: {
    overallRecommendation: string;
    overallRecommendationTone: 'positive' | 'warning' | 'danger' | 'default';
    recommendationSentence: string;
    recommendedBuy: number;
    recommendedSell: number;
    expectedGrossProfit: number;
    confidenceScore: number;
    opportunityScore: number;
    riskScore: number;
    pricingStrategy: string;
    marketingReadiness: string;
    supplierRecommendation: string;
    topRisk: string;
    bestNextAction: string;
    approvalReadiness: string;
    scoreBreakdown: Array<{ label: string; value: string; tone?: 'positive' | 'warning' | 'danger' | 'accent' | 'default' }>;
  };
}

const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value));
const toNumber = (value: unknown, fallback = 0): number => {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : fallback;
};
const round = (value: number, digits = 2): number => {
  const factor = 10 ** digits;
  return Math.round(value * factor) / factor;
};
const safeString = (value: unknown, fallback = 'Unknown'): string =>
  typeof value === 'string' && value.trim() ? value.trim() : fallback;
const titleCase = (value: string): string =>
  value.replace(/[_-]+/g, ' ').replace(/\s+/g, ' ').trim().replace(/\b\w/g, (match) => match.toUpperCase());
const fmt = (value: number): string => `${Math.round(value).toLocaleString()} PKR`;
const label = (value: number): 'High' | 'Medium' | 'Low' => (value >= 70 ? 'High' : value >= 45 ? 'Medium' : 'Low');

const getMedian = (values: number[]): number => {
  const sorted = values.filter((value) => Number.isFinite(value) && value > 0).sort((a, b) => a - b);
  if (!sorted.length) return 0;
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 0 ? round((sorted[mid - 1] + sorted[mid]) / 2, 2) : round(sorted[mid], 2);
};

const getQuantile = (values: number[], quantile: number): number => {
  const sorted = values.filter((value) => Number.isFinite(value) && value > 0).sort((a, b) => a - b);
  if (!sorted.length) return 0;
  const position = (sorted.length - 1) * quantile;
  const lower = Math.floor(position);
  const upper = Math.ceil(position);
  if (lower === upper) return round(sorted[lower], 2);
  const weight = position - lower;
  return round(sorted[lower] * (1 - weight) + sorted[upper] * weight, 2);
};

const getStdDev = (values: number[]): number => {
  const cleaned = values.filter((value) => Number.isFinite(value) && value > 0);
  if (cleaned.length < 2) return 0;
  const mean = cleaned.reduce((sum, value) => sum + value, 0) / cleaned.length;
  const variance = cleaned.reduce((sum, value) => sum + (value - mean) ** 2, 0) / cleaned.length;
  return round(Math.sqrt(variance), 2);
};

const buildHistogram = (values: number[], bucketCount = 6): HistogramBin[] => {
  const cleaned = values.filter((value) => Number.isFinite(value) && value > 0);
  if (!cleaned.length) return [];
  const min = Math.min(...cleaned);
  const max = Math.max(...cleaned);
  if (min === max) return [{ label: fmt(min), min, max, count: cleaned.length }];
  const step = (max - min) / bucketCount;
  const bins: HistogramBin[] = Array.from({ length: bucketCount }, (_, index) => {
    const start = min + index * step;
    const end = index === bucketCount - 1 ? max : min + (index + 1) * step;
    return { label: `${Math.round(start).toLocaleString()}-${Math.round(end).toLocaleString()}`, min: round(start, 2), max: round(end, 2), count: 0 };
  });
  cleaned.forEach((value) => {
    const index = Math.min(Math.floor(((value - min) / (max - min)) * bucketCount), bucketCount - 1);
    bins[index].count += 1;
  });
  return bins;
};

const buildStats = (values: number[]): PriceStats => {
  const cleaned = values.filter((value) => Number.isFinite(value) && value > 0);
  if (!cleaned.length) {
    return { count: 0, min: 0, max: 0, mean: 0, median: 0, q1: 0, q3: 0, stdDev: 0, coefficientOfVariation: 0, range: 0, histogram: [] };
  }
  const min = Math.min(...cleaned);
  const max = Math.max(...cleaned);
  const mean = round(cleaned.reduce((sum, value) => sum + value, 0) / cleaned.length, 2);
  const stdDev = getStdDev(cleaned);
  return {
    count: cleaned.length,
    min: round(min, 2),
    max: round(max, 2),
    mean,
    median: getMedian(cleaned),
    q1: getQuantile(cleaned, 0.25),
    q3: getQuantile(cleaned, 0.75),
    stdDev,
    coefficientOfVariation: mean > 0 ? round(stdDev / mean, 4) : 0,
    range: round(max - min, 2),
    histogram: buildHistogram(cleaned),
  };
};

const buildLeaderboard = <T extends { count: number; averagePrice: number }>(entries: T[]): T[] =>
  [...entries].sort((a, b) => (a.averagePrice !== b.averagePrice ? a.averagePrice - b.averagePrice : b.count - a.count));
const buildSupplierLeaderboard = (items: WholesaleItem[]): LeaderboardEntry[] => {
  const groups = new Map<string, { name: string; count: number; totalPrice: number; lowest: number; highest: number; totalMoq: number; platforms: Set<string>; origins: Set<string>; sampleUrl?: string }>();
  items.forEach((item) => {
    const name = safeString(item.supplier || item.origin || item.platform);
    const current = groups.get(name) || { name, count: 0, totalPrice: 0, lowest: Number.POSITIVE_INFINITY, highest: 0, totalMoq: 0, platforms: new Set<string>(), origins: new Set<string>(), sampleUrl: undefined };
    const price = toNumber(item.unit_price_pkr ?? item.unit_price);
    current.count += 1;
    current.totalPrice += price;
    current.lowest = Math.min(current.lowest, price);
    current.highest = Math.max(current.highest, price);
    current.totalMoq += toNumber(item.moq);
    current.platforms.add(safeString(item.platform, 'wholesale'));
    current.origins.add(safeString(item.origin, 'Unknown'));
    current.sampleUrl = current.sampleUrl || item.source_url;
    groups.set(name, current);
  });
  return buildLeaderboard(Array.from(groups.values()).map((entry) => ({
    name: entry.name,
    count: entry.count,
    averagePrice: round(entry.totalPrice / entry.count, 2),
    minPrice: round(entry.lowest, 2),
    maxPrice: round(entry.highest, 2),
    averageMoq: round(entry.totalMoq / entry.count, 2),
    platforms: Array.from(entry.platforms),
    origins: Array.from(entry.origins),
    sampleUrl: entry.sampleUrl,
  })));
};

const buildRetailLeaderboard = (items: RetailItem[]): LeaderboardEntry[] => {
  const groups = new Map<string, { name: string; count: number; totalPrice: number; lowest: number; highest: number; platforms: Set<string>; titles: string[]; sampleUrl?: string }>();
  items.forEach((item) => {
    const name = safeString(item.seller || item.platform);
    const current = groups.get(name) || { name, count: 0, totalPrice: 0, lowest: Number.POSITIVE_INFINITY, highest: 0, platforms: new Set<string>(), titles: [], sampleUrl: undefined };
    const price = toNumber(item.list_price);
    current.count += 1;
    current.totalPrice += price;
    current.lowest = Math.min(current.lowest, price);
    current.highest = Math.max(current.highest, price);
    current.platforms.add(safeString(item.platform, 'retail'));
    current.titles.push(item.title);
    current.sampleUrl = current.sampleUrl || item.url;
    groups.set(name, current);
  });
  return buildLeaderboard(Array.from(groups.values()).map((entry) => ({
    name: entry.name,
    count: entry.count,
    averagePrice: round(entry.totalPrice / entry.count, 2),
    minPrice: round(entry.lowest, 2),
    maxPrice: round(entry.highest, 2),
    averageMoq: 0,
    platforms: Array.from(entry.platforms),
    origins: entry.titles,
    sampleUrl: entry.sampleUrl,
  })));
};

const buildPlatformSplit = (wholesaleItems: WholesaleItem[], retailItems: RetailItem[]) => {
  const groups = new Map<string, number>();
  wholesaleItems.forEach((item) => {
    const platform = safeString(item.platform, 'wholesale');
    groups.set(platform, (groups.get(platform) || 0) + 1);
  });
  retailItems.forEach((item) => {
    const platform = safeString(item.platform, 'retail');
    groups.set(platform, (groups.get(platform) || 0) + 1);
  });
  return Array.from(groups.entries()).map(([name, count]) => ({ name, count }));
};

const buildCompetitivePoints = (entries: LeaderboardEntry[], group: 'supplier' | 'seller') => entries.map((entry) => ({ name: entry.name, x: entry.count, y: entry.averagePrice, group }));

const normalizeScore = (value: unknown, fallback = 0): number => clamp(toNumber(value, fallback), 0, 100);

const deriveCoverageScore = (wholesaleCount: number, retailCount: number, thresholds?: { wholesale_vendors?: number; retail_listings?: number }): number => {
  const wholesaleThreshold = thresholds?.wholesale_vendors ?? 3;
  const retailThreshold = thresholds?.retail_listings ?? 5;
  const coverage = ((wholesaleThreshold > 0 ? wholesaleCount / wholesaleThreshold : 0) + (retailThreshold > 0 ? retailCount / retailThreshold : 0)) / 2;
  return clamp(round(coverage * 100, 2), 0, 100);
};

const derivePriceStabilityScore = (wholesaleStats: PriceStats, retailStats: PriceStats): number => {
  const wholesale = wholesaleStats.count > 0 ? 1 - Math.min(wholesaleStats.coefficientOfVariation, 1) : 0;
  const retail = retailStats.count > 0 ? 1 - Math.min(retailStats.coefficientOfVariation, 1) : 0;
  return clamp(round(((wholesale + retail) / 2) * 100, 2), 0, 100);
};

const derivePricingPosture = (analyticsRecommendation: AnalyticsRecommendation | null, wholesaleStats: PriceStats, retailStats: PriceStats): PricingModeCard['key'] => {
  const recommendedSell = analyticsRecommendation?.recommended_sell_price_pkr ?? retailStats.max;
  const lowerBound = wholesaleStats.min > 0 ? wholesaleStats.min : analyticsRecommendation?.recommended_buy_price_pkr ?? 0;
  const upperBound = retailStats.max > 0 ? retailStats.max : Math.max(recommendedSell, lowerBound * 1.1);
  const span = Math.max(1, upperBound - lowerBound);
  const position = clamp((recommendedSell - lowerBound) / span, 0, 1);
  if (position < 0.33) return 'competitive';
  if (position < 0.66) return 'balanced';
  return 'premium';
};

const buildSelectionReason = (analyticsRecommendation: AnalyticsRecommendation | null, selectedPosture: PricingModeCard['key'], marketIntelligence: AnyRecord, wholesaleStats: PriceStats, retailStats: PriceStats): string[] => {
  const reasons: string[] = [];
  const backendReasons = analyticsRecommendation?.reasoning_bullets || [];
  const confidenceReason = analyticsRecommendation?.confidence_reason;
  const lowSampleReason = analyticsRecommendation?.low_sample_warning ? analyticsRecommendation.low_sample_reason : '';
  const sell = analyticsRecommendation?.recommended_sell_price_pkr ?? retailStats.max;
  const span = retailStats.max > wholesaleStats.min ? retailStats.max - wholesaleStats.min : 0;
  const position = span > 0 ? clamp((sell - wholesaleStats.min) / span, 0, 1) : 0.5;
  reasons.push(`Selected posture: ${titleCase(selectedPosture)} sits at ${(position * 100).toFixed(0)}% of the observed market range.`);
  if (confidenceReason) reasons.push(confidenceReason);
  reasons.push(...backendReasons.slice(0, 3));
  if (lowSampleReason) reasons.push(`Low-sample guardrail: ${lowSampleReason}`);
  if (marketIntelligence.confidence_band) reasons.push(`Confidence band: ${safeString(marketIntelligence.confidence_band, 'balanced')}`);
  return Array.from(new Set(reasons));
};

const buildPricingModes = (analyticsRecommendation: AnalyticsRecommendation | null, wholesaleStats: PriceStats, retailStats: PriceStats, marketIntelligence: AnyRecord, selectedPosture: PricingModeCard['key']): PricingModeCard[] => {
  const recommendedBuy = analyticsRecommendation?.recommended_buy_price_pkr ?? wholesaleStats.min;
  const recommendedSell = analyticsRecommendation?.recommended_sell_price_pkr ?? retailStats.max;
  const wholesaleFloor = wholesaleStats.min > 0 ? wholesaleStats.min : recommendedBuy;
  const retailMedian = retailStats.median > 0 ? retailStats.median : recommendedSell;
  const retailMax = retailStats.max > 0 ? retailStats.max : recommendedSell;
  const confidenceScore = normalizeScore((analyticsRecommendation?.confidence_score ?? 0) * 100);
  const opportunityScore = normalizeScore(marketIntelligence.opportunity_score ?? 0);
  const competitionScore = normalizeScore(marketIntelligence.competition_score ?? 0);
  const supplierQualityScore = normalizeScore(marketIntelligence.supplier_quality_score ?? 0);
  const demandScore = normalizeScore(marketIntelligence.demand_score ?? 0);
  const coverageScore = deriveCoverageScore(analyticsRecommendation?.wholesale_vendors_count ?? 0, analyticsRecommendation?.retail_sellers_count ?? 0, analyticsRecommendation?.sample_thresholds);
  const stabilityScore = derivePriceStabilityScore(wholesaleStats, retailStats);
  const competitivePrice = clamp(Math.max(wholesaleFloor * 1.05, recommendedBuy * 1.03), wholesaleFloor, retailStats.count > 0 ? Math.max(wholesaleFloor, retailMedian * 0.92) : recommendedSell * 0.95);
  const balancedPrice = clamp(recommendedSell, Math.max(competitivePrice, recommendedBuy * 1.05), Math.max(recommendedSell, retailMax));
  const premiumPrice = clamp(Math.max(recommendedSell * 1.08, retailMedian * 1.05), balancedPrice, Math.max(retailMax * 0.98, balancedPrice));
  const competitiveFit = clamp(competitionScore * 0.45 + (100 - stabilityScore) * 0.2 + (analyticsRecommendation?.low_sample_warning ? 12 : 0) + (100 - confidenceScore) * 0.15, 0, 100);
  const balancedFit = clamp(confidenceScore * 0.3 + opportunityScore * 0.25 + stabilityScore * 0.25 + coverageScore * 0.2, 0, 100);
  const premiumFit = clamp(supplierQualityScore * 0.35 + demandScore * 0.25 + confidenceScore * 0.2 + (100 - competitionScore) * 0.2, 0, 100);
  const modes: Array<Omit<PricingModeCard, 'selected'>> = [
    { key: 'competitive', label: 'Competitive', price: round(competitivePrice, 2), marginPercent: recommendedBuy > 0 ? round(((competitivePrice - recommendedBuy) / recommendedBuy) * 100, 2) : 0, fitScore: round(competitiveFit, 2), confidenceLabel: label(competitiveFit), evidence: [`Wholesale floor: ${fmt(wholesaleFloor)}`, `Retail pressure: ${fmt(retailStats.min)}`, `Competition score: ${competitionScore.toFixed(0)}/100`], reason: 'Favors conversion when the market is crowded or the sample is thin.' },
    { key: 'balanced', label: 'Balanced', price: round(balancedPrice, 2), marginPercent: recommendedBuy > 0 ? round(((balancedPrice - recommendedBuy) / recommendedBuy) * 100, 2) : 0, fitScore: round(balancedFit, 2), confidenceLabel: label(balancedFit), evidence: [`Model recommendation: ${fmt(recommendedSell)}`, `Opportunity score: ${opportunityScore.toFixed(0)}/100`, `Price stability: ${stabilityScore.toFixed(0)}/100`], reason: 'Centres the recommendation around the strongest market evidence.' },
    { key: 'premium', label: 'Premium', price: round(premiumPrice, 2), marginPercent: recommendedBuy > 0 ? round(((premiumPrice - recommendedBuy) / recommendedBuy) * 100, 2) : 0, fitScore: round(premiumFit, 2), confidenceLabel: label(premiumFit), evidence: [`Retail median: ${fmt(retailMedian)}`, `Retail ceiling: ${fmt(retailMax)}`, `Supplier quality: ${supplierQualityScore.toFixed(0)}/100`], reason: 'Works only when quality, demand, and margin support a stronger positioning.' },
  ];
  return modes.map((mode) => ({ ...mode, selected: mode.key === selectedPosture }));
};

const buildEvidenceExplorer = (analyticsRecommendation: AnalyticsRecommendation | null): EvidenceCard[] =>
  (analyticsRecommendation?.evidence_ledger || []).map((entry: AnyRecord) => ({
    section: safeString(entry.section, 'evidence'),
    recommendation: safeString(entry.recommendation, 'Evidence unavailable'),
    evidence: Array.isArray(entry.evidence) ? entry.evidence.map((value) => safeString(value, 'n/a')) : [],
  }));

const buildClusterVisualization = (analysisDetails: AnyRecord | undefined, pricingModes: PricingModeCard[]): ClusterCard[] => {
  const clusters = Array.isArray(analysisDetails?.clusters) ? analysisDetails.clusters : [];
  return clusters.map((cluster: AnyRecord) => {
    const pricing = cluster.pricing || {};
    const metrics = cluster.metrics || {};
    const posture = pricingModes.find((mode) => mode.selected) || pricingModes[1] || pricingModes[0];
    return {
      clusterKey: safeString(cluster.cluster_key, 'cluster'),
      clusterDbId: cluster.cluster_db_id ?? null,
      status: safeString(cluster.status, 'unknown'),
      confidenceScore: normalizeScore((cluster.confidence_score ?? 0) * 100),
      confidenceReason: safeString(cluster.confidence_reason, ''),
      canonicalTitle: safeString(metrics.canonical_title, safeString(cluster.insight_summary, 'Cluster summary')),
      averagePrice: round(toNumber(metrics.avg_price_pkr, 0), 2),
      platformCount: toNumber(metrics.platform_count, 0),
      vendorCount: toNumber(metrics.vendor_count, 0),
      selectedPolicy: safeString(pricing.policy, posture?.label ?? 'Balanced'),
      insightSummary: safeString(cluster.insight_summary, 'No cluster insight available'),
    };
  });
};
const wholesaleLeaderboardCount = (items: WholesaleItem[]): number => new Set(items.map((item) => safeString(item.supplier || item.origin || item.platform))).size;
const retailLeaderboardCount = (items: RetailItem[]): number => new Set(items.map((item) => safeString(item.seller || item.platform))).size;

type SummaryTone = 'positive' | 'warning' | 'danger' | 'accent' | 'default';

const buildSummaryFields = (fields: Array<[string, string, SummaryTone?]>) =>
  fields.map(([label, value, tone]) => ({ label, value, tone: tone ?? 'default' }));

const buildRecommendationSentence = (recommendedBuy: number, recommendedSell: number, confidence: number, posture: string, opportunity: number): string =>
  `Recommend buying near ${fmt(recommendedBuy)} and selling near ${fmt(recommendedSell)} using a ${posture.toLowerCase()} posture, backed by ${confidence.toFixed(0)}% confidence and ${opportunity.toFixed(0)}/100 opportunity.`;

export function buildAnalyticsDashboardModel(
  scraperResult: ScraperResponse,
  analyticsRecommendation: AnalyticsRecommendation | null,
  latestStrategy: MarketingStrategyBase | null,
): AnalyticsDashboardModel {
  const wholesaleItems = scraperResult.wholesale?.made_in_china || [];
  const retailItems = scraperResult.retail || [];
  const wholesaleStats = buildStats(wholesaleItems.map((item) => toNumber(item.unit_price_pkr ?? item.unit_price)).filter((value) => value > 0));
  const retailStats = buildStats(retailItems.map((item) => toNumber(item.list_price)).filter((value) => value > 0));
  const marketIntelligence = (analyticsRecommendation?.market_intelligence || {}) as AnyRecord;
  const primaryPricing = ((analyticsRecommendation?.analysis_details as AnyRecord | undefined)?.primary_cluster?.pricing || {}) as AnyRecord;
  const backendPolicy = safeString(primaryPricing.policy, analyticsRecommendation?.strategy_summary || 'hybrid_ml_sanity');
  const selectedPosture = derivePricingPosture(analyticsRecommendation, wholesaleStats, retailStats);
  const pricingModes = buildPricingModes(analyticsRecommendation, wholesaleStats, retailStats, marketIntelligence, selectedPosture);
  const supplierLeaderboard = buildSupplierLeaderboard(wholesaleItems);
  const retailLeaderboard = buildRetailLeaderboard(retailItems);
  const evidenceExplorer = buildEvidenceExplorer(analyticsRecommendation);
  const clusterVisualization = buildClusterVisualization(analyticsRecommendation?.analysis_details as AnyRecord | undefined, pricingModes);
  const wholesaleCount = analyticsRecommendation?.wholesale_vendors_count ?? wholesaleLeaderboardCount(wholesaleItems);
  const retailCount = analyticsRecommendation?.retail_sellers_count ?? retailLeaderboardCount(retailItems);
  const confidenceScore = normalizeScore((analyticsRecommendation?.confidence_score ?? 0) * 100);
  const opportunityScore = normalizeScore(marketIntelligence.opportunity_score ?? 0);
  const competitionScore = normalizeScore(marketIntelligence.competition_score ?? 0);
  const supplierQualityScore = normalizeScore(marketIntelligence.supplier_quality_score ?? 0);
  const demandScore = normalizeScore(marketIntelligence.demand_score ?? 0);
  const riskScore = normalizeScore(marketIntelligence.risk_score ?? 0);
  const coverageScore = deriveCoverageScore(wholesaleCount, retailCount, analyticsRecommendation?.sample_thresholds);
  const priceStabilityScore = derivePriceStabilityScore(wholesaleStats, retailStats);
  const selectedBuy = analyticsRecommendation?.recommended_buy_price_pkr ?? wholesaleStats.min;
  const selectedSell = analyticsRecommendation?.recommended_sell_price_pkr ?? retailStats.max;
  const observedSpread = analyticsRecommendation?.observed_market_spread_pkr ?? Math.max(0, retailStats.max - wholesaleStats.min);
  const grossProfit = analyticsRecommendation?.gross_profit_pkr ?? Math.max(0, selectedSell - selectedBuy);
  const grossMargin = analyticsRecommendation?.gross_margin_percent ?? (selectedBuy > 0 ? round(((selectedSell - selectedBuy) / selectedBuy) * 100, 2) : 0);
  const clampReasons = Array.isArray(primaryPricing.sanity_adjustments?.clamp_reason)
    ? primaryPricing.sanity_adjustments.clamp_reason.map((reason: unknown) => safeString(reason, 'clamp'))
    : [];
  const selectedMode = pricingModes.find((mode) => mode.selected) || pricingModes[1] || pricingModes[0];
  const selectionReason = buildSelectionReason(analyticsRecommendation, selectedPosture, marketIntelligence, wholesaleStats, retailStats);
  const marketingStatus = latestStrategy?.analysis_status ? titleCase(latestStrategy.analysis_status) : 'Not generated yet';
  const marketingReadiness = latestStrategy?.confidence_score != null ? `${round(latestStrategy.confidence_score * 100, 0)}%` : 'Pending';
  const approvalReadiness = safeString((analyticsRecommendation?.mcb_decision as AnyRecord | undefined)?.final_status, analyticsRecommendation?.confidence_score && analyticsRecommendation.confidence_score >= 0.7 ? 'REVIEW' : 'CAUTION');
  const topRisk = analyticsRecommendation?.low_sample_warning
    ? safeString(analyticsRecommendation.low_sample_reason, 'Limited market sample')
    : clampReasons[0] || (riskScore > 0 ? `${riskScore.toFixed(0)}/100 risk` : 'Moderate market risk');
  const supplierRecommendation = analyticsRecommendation?.sourcing_recommendation || supplierLeaderboard[0]?.name || 'Review supplier data';
  const bestNextAction = analyticsRecommendation?.marketing_recommendation || 'Review the market signal and prepare launch messaging.';
  const recommendationTone: 'positive' | 'warning' | 'danger' | 'default' = approvalReadiness === 'READY' ? 'positive' : approvalReadiness === 'DO_NOT_LAUNCH' ? 'danger' : approvalReadiness === 'CAUTION' ? 'warning' : 'default';
  const overallRecommendation = approvalReadiness;

  return {
    productName: scraperResult.product_name,
    category: analyticsRecommendation?.category || 'Uncategorized',
    marketOverview: {
      wholesale: wholesaleStats,
      retail: retailStats,
      observedMarketSpread: round(observedSpread, 2),
      recommendedBuy: round(selectedBuy, 2),
      recommendedSell: round(selectedSell, 2),
      comparisonData: [
        { name: 'Wholesale minimum', wholesale: wholesaleStats.min, retail: 0, recommended: round(selectedBuy, 2) },
        { name: 'Wholesale median', wholesale: wholesaleStats.median, retail: 0, recommended: round(selectedBuy, 2) },
        { name: 'Retail median', wholesale: 0, retail: retailStats.median, recommended: round(selectedSell, 2) },
        { name: 'Retail maximum', wholesale: 0, retail: retailStats.max, recommended: round(selectedSell, 2) },
      ],
      wholesaleHistogram: wholesaleStats.histogram,
      retailHistogram: retailStats.histogram,
      takeaway:
        wholesaleStats.count > 0 && retailStats.count > 0
          ? `The market is ${priceStabilityScore >= 70 ? 'fairly stable' : 'volatile'} with a ${observedSpread > 0 ? 'clear' : 'tight'} gap between wholesale and retail pricing.`
          : 'The market sample is incomplete, so the dashboard emphasizes observed evidence instead of inferred trend lines.',
      varianceLabel: priceStabilityScore >= 70 ? 'Low variance' : priceStabilityScore >= 45 ? 'Moderate variance' : 'High variance',
      stabilityLabel: priceStabilityScore >= 70 ? 'Stable' : priceStabilityScore >= 45 ? 'Watchful' : 'Volatile',
    },
    supplierIntelligence: {
      leaders: supplierLeaderboard,
      lowest: supplierLeaderboard[0] || null,
      median: supplierLeaderboard.length ? supplierLeaderboard[Math.floor((supplierLeaderboard.length - 1) / 2)] : null,
      highest: supplierLeaderboard.length ? supplierLeaderboard[supplierLeaderboard.length - 1] : null,
      mostCompetitive: supplierLeaderboard[0] || null,
      supplierCount: supplierLeaderboard.length,
    },
    retailMarket: {
      leaders: retailLeaderboard,
      lowest: retailLeaderboard[0] || null,
      median: retailLeaderboard.length ? retailLeaderboard[Math.floor((retailLeaderboard.length - 1) / 2)] : null,
      highest: retailLeaderboard.length ? retailLeaderboard[retailLeaderboard.length - 1] : null,
      mostCompetitive: retailLeaderboard[0] || null,
      sellerCount: retailLeaderboard.length,
      platformSplit: buildPlatformSplit(wholesaleItems, retailItems),
      topListings: [...retailItems].sort((a, b) => toNumber(b.list_price) - toNumber(a.list_price)).slice(0, 5),
    },
    marketOpportunity: {
      cards: [
        { label: 'Opportunity', value: opportunityScore, note: 'Backend opportunity score' },
        { label: 'Competition Pressure', value: competitionScore, note: 'Higher means stronger rivalry' },
        { label: 'Supplier Quality', value: supplierQualityScore, note: 'Backend supplier quality score' },
        { label: 'Demand', value: demandScore, note: 'Backend demand score' },
        { label: 'Coverage', value: coverageScore, note: 'Based on observed suppliers and listings' },
        { label: 'Price Stability', value: priceStabilityScore, note: 'Derived from observed volatility' },
      ],
      radar: [
        { metric: 'Opportunity', value: opportunityScore },
        { metric: 'Demand', value: demandScore },
        { metric: 'Supplier Quality', value: supplierQualityScore },
        { metric: 'Coverage', value: coverageScore },
        { metric: 'Confidence', value: confidenceScore },
        { metric: 'Price Stability', value: priceStabilityScore },
      ],
      confidenceLabel: label(confidenceScore),
      competitionLabel: competitionScore >= 70 ? 'High' : competitionScore >= 45 ? 'Medium' : 'Low',
      coverageScore,
      priceStabilityScore,
      demandScore,
      riskScore,
    },
    pricingIntelligence: {
      backendPolicy,
      selectedPosture,
      selectedModeLabel: selectedMode.label,
      selectedModeReason: selectedMode.reason,
      selectionReason,
      clampReasons,
      confidenceReason: analyticsRecommendation?.confidence_reason || 'No confidence reason provided.',
      confidenceLabel: label(confidenceScore),
      confidenceScore,
      grossMargin,
      grossProfit,
      observedSpread: round(observedSpread, 2),
      pricingModes,
      backendEvidence: evidenceExplorer,
      pricingSummary: buildSummaryFields([
        ['Backend policy', titleCase(backendPolicy), 'accent'],
        ['Selected posture', titleCase(selectedPosture), selectedMode.selected ? 'positive' : 'default'],
        ['Confidence', `${label(confidenceScore)} (${confidenceScore.toFixed(0)}%)`, confidenceScore >= 70 ? 'positive' : confidenceScore >= 45 ? 'warning' : 'danger'],
        ['Observed spread', fmt(round(observedSpread, 2)), 'default'],
        ['Gross profit', fmt(round(grossProfit, 2)), 'positive'],
        ['Gross margin', `${grossMargin.toFixed(1)}%`, 'positive'],
      ]),
    },
    evidenceExplorer: { cards: evidenceExplorer },
    clusterVisualization: { clusters: clusterVisualization, clusterCount: clusterVisualization.length },
    competitiveLandscape: {
      supplierPoints: buildCompetitivePoints(supplierLeaderboard, 'supplier'),
      sellerPoints: buildCompetitivePoints(retailLeaderboard, 'seller'),
      platformSplit: buildPlatformSplit(wholesaleItems, retailItems),
    },
    recommendationSummary: {
      overallRecommendation,
      overallRecommendationTone: recommendationTone,
      recommendationSentence: buildRecommendationSentence(round(selectedBuy, 2), round(selectedSell, 2), confidenceScore, titleCase(selectedPosture), opportunityScore),
      recommendedBuy: round(selectedBuy, 2),
      recommendedSell: round(selectedSell, 2),
      expectedGrossProfit: round(grossProfit, 2),
      confidenceScore,
      opportunityScore,
      riskScore,
      pricingStrategy: `${titleCase(selectedPosture)} / ${titleCase(backendPolicy)}`,
      marketingReadiness,
      supplierRecommendation,
      topRisk,
      bestNextAction,
      approvalReadiness,
      scoreBreakdown: buildSummaryFields([
        ['Opportunity', `${opportunityScore.toFixed(0)}/100`, 'positive'],
        ['Confidence', `${confidenceScore.toFixed(0)}/100`, confidenceScore >= 70 ? 'positive' : 'warning'],
        ['Supplier quality', `${supplierQualityScore.toFixed(0)}/100`, 'default'],
        ['Price stability', `${priceStabilityScore.toFixed(0)}/100`, 'default'],
        ['Marketing readiness', marketingStatus, latestStrategy ? 'positive' : 'warning'],
        ['Approval readiness', approvalReadiness, recommendationTone],
      ]),
    },
  };
}
