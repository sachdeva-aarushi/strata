'use client';

import { useState, useEffect, useCallback } from 'react';
import { api, RFQ, Offer } from '../lib/api/client';

export function useRFQ(rfqId?: string) {
  const [data, setData] = useState<RFQ | null>(null);
  const [offers, setOffers] = useState<Offer[]>([]);
  const [history, setHistory] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(Boolean(rfqId));
  const [error, setError] = useState<Error | null>(null);

  const fetchRFQ = useCallback(async () => {
    if (!rfqId) {
      setData(null);
      setOffers([]);
      setHistory([]);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const [rfqRes, offersRes, historyRes] = await Promise.allSettled([
        api.exchange.getRFQ(rfqId),
        api.exchange.listRFQOffers(rfqId),
        api.exchange.getRFQHistory(rfqId),
      ]);

      if (rfqRes.status === 'fulfilled') {
        setData(rfqRes.value);
      } else {
        throw rfqRes.reason;
      }

      if (offersRes.status === 'fulfilled') {
        setOffers(offersRes.value || []);
      } else {
        setOffers([]);
      }

      if (historyRes.status === 'fulfilled') {
        setHistory(historyRes.value || []);
      } else {
        setHistory([]);
      }
    } catch (err: any) {
      setError(err instanceof Error ? err : new Error(String(err)));
    } finally {
      setIsLoading(false);
    }
  }, [rfqId]);

  useEffect(() => {
    fetchRFQ();
  }, [fetchRFQ]);

  const approve = useCallback(async () => {
    if (!rfqId) throw new Error('Cannot approve: No RFQ ID provided');
    setIsLoading(true);
    try {
      const updated = await api.exchange.approveRFQ(rfqId);
      setData(updated);
      await fetchRFQ();
      return updated;
    } catch (err: any) {
      const errorObj = err instanceof Error ? err : new Error(String(err));
      setError(errorObj);
      throw errorObj;
    } finally {
      setIsLoading(false);
    }
  }, [rfqId, fetchRFQ]);

  const accept = useCallback(async (offerId: string) => {
    setIsLoading(true);
    try {
      const accepted = await api.exchange.acceptOffer(offerId);
      await fetchRFQ();
      return accepted;
    } catch (err: any) {
      const errorObj = err instanceof Error ? err : new Error(String(err));
      setError(errorObj);
      throw errorObj;
    } finally {
      setIsLoading(false);
    }
  }, [fetchRFQ]);

  return {
    data,
    offers,
    history,
    isLoading,
    error,
    refetch: fetchRFQ,
    approve,
    accept,
  };
}
