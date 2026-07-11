export interface WholesaleItem {
  platform: string;
  supplier: string;
  moq: number;
  unit_price: number;
  unit_price_pkr: number;
  currency: string;
  lead_time: string;
  origin: string;
  moq_listing: number;
  attributes_listing: Record<string, any>;
  source_url?: string;
}

export interface RetailItem {
  seller: string;
  platform: string;
  list_price: number;
  promo: string;
  url: string;
  title: string;
}

export interface LinksUsed {
  [key: string]: string;
}

export interface ScraperResponse {
  product_name: string;
  links_used: LinksUsed;
  wholesale: {
    made_in_china: WholesaleItem[];
  };
  retail: RetailItem[];
}

export interface AnalyticsRecommendation {
  product: string;
  category: string;
  pipeline_run_id?: string | null;
  analytics_result_id?: string | null;
  product_cluster_id?: string | null;
  recommended_buy_price_pkr: number;
  recommended_sell_price_pkr: number;
  expected_profit_margin: number;
  confidence_score: number;
  confidence_reason: string;
  wholesale_vendors_count: number;
  retail_sellers_count: number;
  low_sample_warning?: boolean;
  low_sample_reason?: string;
  sample_thresholds?: {
    wholesale_vendors?: number;
    retail_listings?: number;
  };
  reasoning_bullets?: string[];
  gross_profit_pkr?: number;
  net_profit_pkr?: number;
  gross_margin_percent?: number;
  roi_percent?: number;
  break_even_sell_price_pkr?: number;
  profitability_confidence?: number;
  confidence_band?: string;
  observed_market_spread_pkr?: number;
  observed_market_spread?: number;
  price_spread_wholesale?: number;
  price_spread_retail?: number;
  recommendation_status?: string;
  strategy_summary?: string;
  sourcing_recommendation?: string;
  marketing_recommendation?: string;
  cost_breakdown?: Record<string, any>;
  cost_profile?: Record<string, any>;
  market_intelligence?: Record<string, any>;
  commercial_intelligence?: Record<string, any>;
  profitability_summary?: Record<string, any>;
  evidence_ledger?: Array<Record<string, any>>;
  analysis_details?: Record<string, any>;
  marketing_strategy_id?: string | null;
  marketing_analysis_status?: string | null;
  mcb_decision?: Record<string, any> | null;
}

export interface AnalyticsFeedbackRequest {
  pipeline_run_id?: string | null;
  analytics_result_id?: string | null;
  recommendation_id?: string | null;
  marketing_strategy_id?: string | null;
  submitted_by_user_id?: string | null;
  product_name: string;
  category?: string | null;
  feedback_type: 'acted_on_recommendation' | 'skipped' | 'follow_up';
  action_taken?: string | null;
  actual_buy_price_pkr?: number | null;
  actual_sell_price_pkr?: number | null;
  quantity?: number | null;
  notes?: string | null;
  source_page?: string | null;
}

export interface AnalyticsFeedbackResponse {
  id: string;
  pipeline_run_id?: string | null;
  analytics_result_id?: string | null;
  recommendation_id?: string | null;
  feedback_type: string;
  action_taken?: string | null;
  created_at?: string | null;
  status?: string;
}

export interface PriceHistoryPoint {
  pipeline_run_id?: string | null;
  captured_at?: string | null;
  wholesale_count: number;
  retail_count: number;
  wholesale_avg_price_pkr: number;
  wholesale_min_price_pkr: number;
  wholesale_max_price_pkr: number;
  retail_avg_price_pkr: number;
  retail_min_price_pkr: number;
  retail_max_price_pkr: number;
}

export interface PriceHistoryResponse {
  product_name: string;
  category: string;
  total_points: number;
  points: PriceHistoryPoint[];
}

export interface MarketingStrategyBase {
  id: string;
  product_name: string;
  category: string;
  analysis_status: string;
  confidence_score: number;
  created_at: string;
  version_number?: number;
  is_latest?: boolean;
  pipeline_run_id?: string | null;
  analytics_result_id?: string | null;
  product_cluster_id?: string | null;
  parent_strategy_id?: string | null;
  generation_type?: string;
  strategy_status?: string;
  strategy?: Record<string, any> | null;
}

export type MarketingStrategySummary = MarketingStrategyBase;
export type MarketingStrategyRecord = MarketingStrategyBase;

export interface PriceRange {
  min: number;
  max: number;
}

export interface ComparisonData {
  bestRetailPrice: number;
  bestWholesalePrice: number;
  /** Legacy compatibility alias for the observed market spread. */
  estimatedProfit: number;
  observedMarketSpread: number;
  observedWholesaleRange: PriceRange;
  observedRetailRange: PriceRange;
  recommendedBuyPrice: number;
  recommendedSellPrice: number;
  recommendedProfitMargin: number;
  confidenceScore: number;
  confidenceReason: string;
  lowSampleWarning: boolean;
  lowSampleReason: string;
  reasoningBullets: string[];
  recommendedSupplier: WholesaleItem | null;
  recommendedRetailPlatform: RetailItem | null;
  analyticsRecommendation?: AnalyticsRecommendation | null;
}

export interface ReportPayload {
  report_title: string;
  generated_at: string;
  product_name: string;
  category?: string;
  summary: {
    total_suppliers: number;
    total_retailers: number;
    recommended_buy_price: number;
    recommended_sell_price: number;
    expected_profit_margin: number;
    confidence_score: number;
    low_sample_warning: boolean;
    low_sample_reason: string;
    observed_wholesale_min: number;
    observed_wholesale_max: number;
    observed_retail_min: number;
    observed_retail_max: number;
    observed_market_spread: number;
    best_wholesale_price: number;
    best_retail_price: number;
    estimated_profit: number;
  };
  wholesale: WholesaleItem[];
  retail: RetailItem[];
  recommendations: {
    supplier: WholesaleItem | null;
    retail_platform: RetailItem | null;
  };
  analytics_recommendation?: AnalyticsRecommendation | null;
  price_history?: PriceHistoryPoint[];
}



