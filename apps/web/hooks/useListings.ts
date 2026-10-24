'use client';

import { useState, useEffect, useCallback } from 'react';
import { api, MarketplaceListing } from '../lib/api/client';

interface UseListingsParams {
  view?: 'all' | 'own';
  category?: string;
  status?: string;
  cluster_id?: string;
}

export function useListings(params: UseListingsParams = { view: 'all' }) {
  const [data, setData] = useState<MarketplaceListing[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchListings = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await api.marketplace.getListings(params);
      setData(response.items || []);
    } catch (err: any) {
      setError(err instanceof Error ? err : new Error(String(err)));
    } finally {
      setIsLoading(false);
    }
  }, [params.view, params.category, params.status, params.cluster_id]);

  useEffect(() => {
    fetchListings();
  }, [fetchListings]);

  return {
    data,
    isLoading,
    error,
    refetch: fetchListings,
  };
}
