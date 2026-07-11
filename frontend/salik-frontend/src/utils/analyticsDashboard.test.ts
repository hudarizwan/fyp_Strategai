import assert from 'node:assert/strict';
import { buildAnalyticsDashboardModel } from './analyticsDashboard';
import type { AnalyticsRecommendation, ScraperResponse } from '../types';

const scraperResult: ScraperResponse = {
  product_name: 'Test Product',
  links_used: {},
  wholesale: {
    made_in_china: [
      {
        platform: 'made_in_china',
        supplier: 'Alpha Supply',
        moq: 10,
        unit_price: 100,
        unit_price_pkr: 100,
        currency: 'PKR',
        lead_time: '7 days',
        origin: 'Shenzhen',
        moq_listing: 10,
        attributes_listing: {},
      },
      {
        platform: 'made_in_china',
        supplier: 'Alpha Supply',
        moq: 12,
        unit_price: 110,
        unit_price_pkr: 110,
        currency: 'PKR',
        lead_time: '8 days',
        origin: 'Shenzhen',
        moq_listing: 12,
        attributes_listing: {},
      },
      {
        platform: 'made_in_china',
        supplier: 'Beta Source',
        moq: 20,
        unit_price: 140,
        unit_price_pkr: 140,
        currency: 'PKR',
        lead_time: '10 days',
        origin: 'Guangdong',
        moq_listing: 20,
        attributes_listing: {},
      },
    ],
  },
  retail: [
    {
      seller: 'Seller One',
      platform: 'daraz',
      list_price: 180,
      promo: '10% off',
      url: 'https://example.com/1',
      title: 'Test Product 1',
    },
    {
      seller: 'Seller One',
      platform: 'daraz',
      list_price: 210,
      promo: '',
      url: 'https://example.com/2',
      title: 'Test Product 2',
    },
    {
      seller: 'Seller Two',
      platform: 'daraz',
      list_price: 240,
      promo: '',
      url: 'https://example.com/3',
      title: 'Test Product 3',
    },
  ],
};

const analyticsRecommendation: Partial<AnalyticsRecommendation> = {
  product: 'Test Product',
  category: 'gaming_accessories',
  recommended_buy_price_pkr: 102,
  recommended_sell_price_pkr: 205,
  expected_profit_margin: 100.98,
  confidence_score: 0.82,
  confidence_reason: 'high confidence - both markets present with stable pricing',
  wholesale_vendors_count: 2,
  retail_sellers_count: 2,
  low_sample_warning: true,
  low_sample_reason: 'wholesale vendors below threshold (2/3); retail listings below threshold (2/5)',
  sample_thresholds: { wholesale_vendors: 3, retail_listings: 5 },
  reasoning_bullets: ['Competition is moderate', 'Demand is high'],
  gross_profit_pkr: 103,
  gross_margin_percent: 100.98,
  profitability_confidence: 0.79,
  confidence_band: 'balanced',
  observed_market_spread_pkr: 140,
  recommendation_status: 'generated',
  strategy_summary: 'hybrid_ml_sanity for cluster cluster-1',
  sourcing_recommendation: 'Prefer the lowest-cost supplier',
  marketing_recommendation: 'Use balanced launch scope',
  market_intelligence: {
    opportunity_score: 72,
    competition_score: 54,
    supplier_quality_score: 61,
    market_saturation_score: 38,
    data_quality_score: 48,
    risk_score: 33,
    confidence_band: 'balanced',
  },
  evidence_ledger: [
    {
      section: 'pricing',
      recommendation: 'Use a gross profit target around PKR 103.',
      evidence: ['recommended_buy_price_pkr=102', 'recommended_sell_price_pkr=205'],
    },
    {
      section: 'supplier',
      recommendation: 'Supplier quality is 61/100.',
      evidence: ['wholesale_vendors_count=2'],
    },
  ],
  analysis_details: {
    primary_cluster: {
      cluster_key: 'cluster-1',
      cluster_db_id: 'cluster-db-1',
      analytics_result_id: 'analytics-1',
      status: 'completed',
      metrics: {
        canonical_title: 'Test Product',
        avg_price_pkr: 190,
        platform_count: 2,
        vendor_count: 2,
      },
      pricing: {
        recommended_buy: 102,
        recommended_sell: 205,
        policy: 'hybrid_ml_sanity',
        sanity_adjustments: {
          clamp_reason: ['retail_anchor_clamp'],
        },
      },
      confidence_score: 0.82,
      confidence_reason: 'high confidence - both markets present with stable pricing',
      insight_summary: 'Cluster summary',
    },
    cluster_count: 1,
    clusters: [
      {
        cluster_key: 'cluster-1',
        cluster_db_id: 'cluster-db-1',
        analytics_result_id: 'analytics-1',
        status: 'completed',
        confidence_score: 0.82,
        confidence_reason: 'high confidence - both markets present with stable pricing',
        pricing: {
          recommended_buy: 102,
          recommended_sell: 205,
          policy: 'hybrid_ml_sanity',
        },
        metrics: {
          canonical_title: 'Test Product',
          avg_price_pkr: 190,
          platform_count: 2,
          vendor_count: 2,
        },
        insight_summary: 'Cluster summary',
      },
    ],
    commercial_intelligence: {
      market_intelligence: {
        opportunity_score: 72,
        competition_score: 54,
        supplier_quality_score: 61,
        market_saturation_score: 38,
        data_quality_score: 48,
        risk_score: 33,
        confidence_band: 'balanced',
      },
    },
  },
};

const model = buildAnalyticsDashboardModel(scraperResult, analyticsRecommendation as AnalyticsRecommendation, null);

assert.equal(model.marketOverview.wholesale.min, 100);
assert.equal(model.marketOverview.wholesale.max, 140);
assert.equal(model.marketOverview.retail.min, 180);
assert.equal(model.marketOverview.retail.max, 240);
assert.equal(model.supplierIntelligence.lowest?.name, 'Alpha Supply');
assert.equal(model.retailMarket.lowest?.name, 'Seller One');
assert.equal(model.marketOpportunity.cards[0].value, 72);
assert.equal(model.evidenceExplorer.cards.length, 2);
assert.equal(model.clusterVisualization.clusters[0].clusterKey, 'cluster-1');
assert.equal(model.pricingIntelligence.backendPolicy, 'hybrid_ml_sanity');
assert.equal(model.pricingIntelligence.selectedPosture, 'premium');
assert.equal(model.recommendationSummary.recommendedSell, 205);
