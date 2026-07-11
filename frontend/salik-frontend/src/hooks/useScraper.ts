import { useMutation } from '@tanstack/react-query';
import { scraperService } from '../services/api';
import { ScraperResponse } from '../types';

export const useScraper = () => {
  return useMutation<ScraperResponse, Error, { productName: string; category: string }>({
    mutationFn: ({ productName, category }) => scraperService.startScraping(productName, category),
  });
};

