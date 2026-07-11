import axios from 'axios';
import {
  AnalyticsFeedbackRequest,
  AnalyticsFeedbackResponse,
  AnalyticsRecommendation,
  MarketingStrategyRecord,
  MarketingStrategySummary,
  PriceHistoryResponse,
  ReportPayload,
  ScraperResponse,
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || (import.meta.env.DEV ? 'http://127.0.0.1:8001' : '');

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const analyticsService = {
  submitFeedback: async (payload: AnalyticsFeedbackRequest): Promise<AnalyticsFeedbackResponse> => {
    const response = await api.post<AnalyticsFeedbackResponse>('/analytics/feedback', payload);
    return response.data;
  },

  getPriceHistory: async (
    productName: string,
    category: string,
    limit = 12
  ): Promise<PriceHistoryResponse> => {
    const response = await api.get<PriceHistoryResponse>('/analytics/price-history', {
      params: {
        product_name: productName,
        category,
        limit,
      },
    });
    return response.data;
  },
};

export const scraperService = {
  startScraping: async (productName: string, category: string): Promise<ScraperResponse> => {
    const response = await api.post<ScraperResponse>('/scraper/start', {
      product_name: productName,
      category: category,
    });
    return response.data;
  },

  analyzeProduct: async (productName: string, category: string): Promise<AnalyticsRecommendation> => {
    const response = await api.post<AnalyticsRecommendation>('/analytics/analyze', {
      product_name: productName,
      category: category,
    });
    return response.data;
  },
};

export const marketingService = {
  generate: async (payload: MarketingGeneratePayload): Promise<MarketingStrategyRecord> => {
    const response = await api.post<MarketingStrategyRecord>('/marketing/generate', payload);
    return response.data;
  },

  regenerate: async (payload: MarketingGeneratePayload): Promise<MarketingStrategyRecord> => {
    const response = await api.post<MarketingStrategyRecord>('/marketing/regenerate', payload);
    return response.data;
  },

  getHistory: async (limit = 20): Promise<{ strategies: MarketingStrategySummary[]; count: number }> => {
    const response = await api.get<{ strategies: MarketingStrategySummary[]; count: number }>(`/marketing/history?limit=${limit}`);
    return response.data;
  },

  getHistoryByAnalytics: async (analyticsResultId: string, limit = 20): Promise<{ strategies: MarketingStrategySummary[]; count: number }> => {
    const response = await api.get<{ strategies: MarketingStrategySummary[]; count: number }>(`/marketing/history/${analyticsResultId}?limit=${limit}`);
    return response.data;
  },

  getHistoryByPipeline: async (pipelineRunId: string, limit = 20): Promise<{ strategies: MarketingStrategySummary[]; count: number }> => {
    const response = await api.get<{ strategies: MarketingStrategySummary[]; count: number }>(`/marketing/history-pipeline/${pipelineRunId}?limit=${limit}`);
    return response.data;
  },

  getLatestByAnalytics: async (analyticsResultId: string): Promise<MarketingStrategyRecord> => {
    const response = await api.get<MarketingStrategyRecord>(`/marketing/by-analytics/${analyticsResultId}`);
    return response.data;
  },

  getLatestByPipeline: async (pipelineRunId: string): Promise<MarketingStrategyRecord> => {
    const response = await api.get<MarketingStrategyRecord>(`/marketing/by-pipeline/${pipelineRunId}`);
    return response.data;
  },

  getById: async (id: string): Promise<MarketingStrategyRecord> => {
    const response = await api.get<MarketingStrategyRecord>(`/marketing/${id}`);
    return response.data;
  },
};

export const reportService = {
  downloadPdf: async (payload: ReportPayload): Promise<Blob> => {
    const response = await api.post<Blob>('/reports/pdf', payload, {
      responseType: 'blob',
    });
    return response.data;
  },
};

type MarketingGeneratePayload = {
  product_name: string;
  category: string;
  analytics_result: Record<string, any>;
  scraper_result: Record<string, any>;
  pipeline_run_id?: string;
  analytics_result_id?: string;
  product_cluster_id?: string;
  parent_strategy_id?: string;
  generation_type?: 'initial' | 'regenerate';
};