'use client';

import { useState, useEffect, useCallback } from 'react';
import { api, MunicipalFlowResult, MunicipalFlowParams } from '../lib/api/client';

export function useMunicipalIntelligence(params?: MunicipalFlowParams) {
  const [data, setData] = useState<MunicipalFlowResult | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchFlows = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await api.intelligence.getMunicipalFlows(params);
      setData(result);
    } catch (err: any) {
      setError(err instanceof Error ? err : new Error(String(err)));
    } finally {
      setIsLoading(false);
    }
  }, [params?.city_id, params?.zone_id, params?.material_category, params?.start_date, params?.end_date]);

  useEffect(() => {
    fetchFlows();
  }, [fetchFlows]);

  return {
    data,
    isLoading,
    error,
    refetch: fetchFlows,
  };
}
