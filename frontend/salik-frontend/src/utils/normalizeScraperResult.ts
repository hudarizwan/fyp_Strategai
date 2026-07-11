import { ScraperResponse, WholesaleItem } from '@/types';

const WHOLESALE_KEYS = ['made_in_china', 'made-in-china', 'made_in_china_search'];

function normalizeWholesaleItem(item: any): WholesaleItem {
  return {
    platform: item?.platform || 'made_in_china',
    supplier: item?.supplier || 'Unknown Supplier',
    moq: Number(item?.moq ?? 1),
    unit_price: Number(item?.unit_price ?? 0),
    unit_price_pkr: Number(item?.unit_price_pkr ?? 0),
    currency: item?.currency || 'USD',
    lead_time: item?.lead_time || '',
    origin: item?.origin || '',
    moq_listing: Number(item?.moq_listing ?? item?.moq ?? 1),
    attributes_listing: item?.attributes_listing || {},
    source_url: item?.source_url || item?.url || '',
  };
}

export function normalizeScraperResult(input: any): ScraperResponse {
  const wholesaleSource = input?.wholesale || {};
  const wholesaleItems =
    wholesaleSource?.made_in_china ||
    wholesaleSource?.['made-in-china'] ||
    [];

  const linksUsed = input?.links_used || {};
  const micLink =
    linksUsed?.made_in_china_search ||
    linksUsed?.made_in_china ||
    linksUsed?.['made-in-china'] ||
    '';

  return {
    product_name: input?.product_name || input?.product || '',
    links_used: {
      ...linksUsed,
      made_in_china_search: micLink,
    },
    wholesale: {
      made_in_china: Array.isArray(wholesaleItems)
        ? wholesaleItems.map(normalizeWholesaleItem)
        : [],
    },
    retail: Array.isArray(input?.retail) ? input.retail : [],
  };
}

export function getMicSearchLink(data: ScraperResponse | null): string {
  if (!data) {
    return '';
  }
  for (const key of WHOLESALE_KEYS) {
    const value = data.links_used?.[key];
    if (value) {
      return value;
    }
  }
  return '';
}
