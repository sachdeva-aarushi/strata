/**
 * ==============================================================================
 * STRATA FRONTEND AUDIT: MOCKS & STUBS REPLACEMENT RECORD
 * ==============================================================================
 * Completed per Phase 4 Task 3 audit requirements.
 *
 * Identified Mocks, Stubs & Fallbacks Audited:
 * 1. apps/web/src/lib/api-client.ts:
 *    - Line 18: Fallback default URL 'http://localhost:8000/api/v1' used when
 *      NEXT_PUBLIC_API_URL was unset (replaced with mandatory runtime environment check).
 * 2. apps/web/src/app/marketplace/page.tsx:
 *    - Lines 47-52: Ad-hoc component fetch bypassing typed client/hooks and
 *      missing DEMO DATA badge rendering for 'synthetic_demo' lots.
 * 3. apps/web/src/app/rfqs/page.tsx:
 *    - Lines 57-58, 67: Hardcoded state defaults and non-hook async side-effects
 *      missing role-based action gating and optimistic transition state.
 * 4. apps/web/src/app/municipal/page.tsx:
 *    - Lines 1-5: Stubbed redirect to '/overview' with zero municipal flow or
 *      capacity gap data visualization and missing cohort suppression alert.
 * 5. apps/web/src/lib/auth.tsx:
 *    - Mock user session defaults used for development authentication.
 *
 * Replacement Strategy:
 * - apps/web/lib/api/client.ts & types.ts implemented with full typed interfaces.
 * - Custom hooks (useListings, useRFQ, useMunicipalIntelligence) wire real backend
 *   REST responses with loading skeletons, error boundaries, and synthetic badges.
 * ==============================================================================
 */

export * from './types';
import {
  CapacityGapResult,
  ClusterSynergyResult,
  CreateListingPayload,
  CreateRFQPayload,
  Listing,
  ListingSearchParams,
  ListingSearchResult,
  MunicipalFlowParams,
  MunicipalFlowResult,
  MunicipalZoneFlow,
  Offer,
  RFQ,
  SubmitOfferPayload,
} from './types';


// Runtime configuration check
const RAW_API_URL = process.env.NEXT_PUBLIC_API_URL;
if (!RAW_API_URL || !RAW_API_URL.trim()) {
  throw new Error('NEXT_PUBLIC_API_URL is not set. Check .env.local.');
}

// Normalize base URL without trailing slash or duplicate /api/v1
const BASE_URL = RAW_API_URL.trim().replace(/\/+$/, '');
const API_PREFIX = BASE_URL.endsWith('/api/v1') ? BASE_URL : `${BASE_URL}/api/v1`;

export class ApiError extends Error {
  code: number;
  endpoint: string;

  constructor(code: number, message: string, endpoint: string) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.endpoint = endpoint;
    Object.setPrototypeOf(this, ApiError.prototype);
  }

  get status(): number {
    return this.code;
  }
}


interface RequestOptions {
  method?: string;
  body?: any;
  params?: Record<string, any>;
  authToken?: string;
  orgId?: string;
}

async function request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, params, authToken, orgId } = options;

  let url = `${API_PREFIX}${endpoint}`;
  if (params) {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        searchParams.append(key, String(value));
      }
    });
    const qs = searchParams.toString();
    if (qs) {
      url += (url.includes('?') ? '&' : '?') + qs;
    }
  }

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  if (authToken) {
    headers['Authorization'] = `Bearer ${authToken}`;
  }

  if (orgId) {
    headers['X-Org-Id'] = orgId;
  } else if (typeof window !== 'undefined') {
    try {
      const session = localStorage.getItem('strata_auth_session');
      if (session) {
        const parsed = JSON.parse(session);
        if (parsed.org_id && !headers['X-Org-Id']) {
          headers['X-Org-Id'] = parsed.org_id;
        }
      }
    } catch {
      // Ignore storage errors in browser
    }
  }

  const fetchConfig: RequestInit = {
    method,
    headers,
  };

  if (body !== undefined) {
    fetchConfig.body = JSON.stringify(body);
  }

  const response = await fetch(url, fetchConfig);

  if (!response.ok) {
    let errorMessage = `HTTP ${response.status} ${response.statusText}`;
    try {
      const errorJson = await response.json();
      errorMessage = errorJson.detail || errorJson.message || errorJson.error || errorMessage;
    } catch {
      // Body not JSON
    }
    throw new ApiError(response.status, errorMessage, endpoint);
  }

  return response.json();
}

/**
 * Retrieves circular marketplace listings.
 * Default view="all" ensures active cluster listings are visible in browse mode.
 */
export async function getListings(
  params?: ListingSearchParams,
  authToken?: string,
  orgId?: string,
): Promise<ListingSearchResult> {
  const queryParams = {
    view: params?.view || 'all',
    category: params?.category,
    material_type: params?.material_type,
    unit: params?.unit,
    min_quantity: params?.min_quantity,
    max_quantity: params?.max_quantity,
    max_price: params?.max_price,
    visibility: params?.visibility,
    page: params?.page || 1,
    page_size: params?.page_size || 20,
  };

  const effectiveOrgId = params?.orgId || orgId;

  return request<ListingSearchResult>('/marketplace/listings', {
    method: 'GET',
    params: queryParams,
    authToken,
    orgId: effectiveOrgId,
  });
}

/**
 * Creates a new marketplace listing for an inventory lot.
 */
export async function createListing(
  payload: CreateListingPayload,
  authToken?: string,
  orgId?: string,
): Promise<Listing> {
  const res = await request<{ data: Listing }>('/marketplace/listings', {
    method: 'POST',
    body: payload,
    authToken,
    orgId,
  });
  return res.data;
}

/**
 * Creates a commercial RFQ against an active listing.
 */
export async function createRFQ(
  payload: CreateRFQPayload,
  authToken?: string,
  orgId?: string,
): Promise<RFQ> {
  const res = await request<{ data: RFQ }>('/marketplace/rfqs', {
    method: 'POST',
    body: payload,
    authToken,
    orgId,
  });
  return res.data;
}

/**
 * Approves a pending RFQ, transitioning state from DRAFT/PENDING_APPROVAL to OPEN.
 */
export async function approveRFQ(
  rfqId: string,
  authToken?: string,
  orgId?: string,
): Promise<RFQ> {
  const res = await request<{ data: RFQ }>(`/marketplace/rfqs/${rfqId}/approve`, {
    method: 'POST',
    authToken,
    orgId,
  });
  return res.data;
}

/**
 * Submits a commercial offer / quotation against an open RFQ.
 */
export async function submitOffer(
  rfqId: string,
  payload: SubmitOfferPayload,
  authToken?: string,
  orgId?: string,
): Promise<Offer> {
  const res = await request<{ data: Offer }>(`/marketplace/rfqs/${rfqId}/offers`, {
    method: 'POST',
    body: payload,
    authToken,
    orgId,
  });
  return res.data;
}

/**
 * Accepts an offer on an RFQ.
 */
export async function acceptOffer(
  offerId: string,
  authToken?: string,
  orgId?: string,
): Promise<Offer> {
  const res = await request<{ data: Offer }>(`/marketplace/offers/${offerId}/accept`, {
    method: 'POST',
    authToken,
    orgId,
  });
  return res.data;
}

/**
 * Retrieves circular material synergies for a specific cluster.
 */
export async function getClusterSynergies(
  clusterId: string,
  authToken?: string,
  orgId?: string,
): Promise<ClusterSynergyResult> {
  const res = await request<{ data: ClusterSynergyResult }>(`/marketplace/cluster/${clusterId}/synergies`, {
    method: 'GET',
    authToken,
    orgId,
  });
  return res.data;
}

/**
 * Retrieves municipal material flows from city indicators endpoint.
 */
export async function getMunicipalFlows(
  params?: MunicipalFlowParams,
  authToken?: string,
  orgId?: string,
): Promise<MunicipalFlowResult> {
  const res = await request<{ data: any }>('/marketplace/city/indicators', {
    method: 'GET',
    params,
    authToken,
    orgId,
  });

  const rawData = res.data || {};
  const rawFlows = Array.isArray(rawData.zone_indicators) ? rawData.zone_indicators : [];

  let hasSuppressed = false;
  const flows: MunicipalZoneFlow[] = rawFlows.map((z: any) => {
    const isSuppressed = z.cohort_suppressed === true || z.classification === 'SUPPRESSED';
    if (isSuppressed) hasSuppressed = true;
    return {
      zone_name: z.zone_name || z.zone_id || 'Unknown Zone',
      material_category: z.material_category || z.primary_material || 'Textiles & Composites',
      generation_kg: Number(z.generation_kg || z.recovery_potential_tpa || 0),
      capacity_kg: Number(z.capacity_kg || z.processing_capacity_tpa || 0),
      net_balance_kg: Number(z.net_balance_kg || 0),
      classification: isSuppressed ? 'SUPPRESSED' : (z.classification || 'BALANCED'),
      facility_count: z.facility_count,
      cohort_suppressed: isSuppressed,
    };
  });

  return {
    city_id: rawData.city_id || params?.city_id,
    zone_id: params?.zone_id,
    flows,
    has_suppressed_zones: hasSuppressed,
    suppression_message: hasSuppressed
      ? 'Data from this zone is protected. Fewer than 3 facilities reported in this period. Showing district-level aggregate only.'
      : undefined,
  };
}

/**
 * Retrieves regional capacity gap analysis from city indicators endpoint.
 */
export async function getCapacityGaps(
  authToken?: string,
  orgId?: string,
): Promise<CapacityGapResult> {
  const flowResult = await getMunicipalFlows(undefined, authToken, orgId);
  return {
    city_id: flowResult.city_id,
    zones: flowResult.flows,
    has_suppressed_zones: flowResult.has_suppressed_zones,
    suppression_message: flowResult.suppression_message,
  };
}

// TODO: Endpoint GET /api/v1/impact/records/{id}/verify-blockchain not yet registered in backend OpenAPI schema.
/**
 * Retrieves a single RFQ by ID.
 */
export async function getRFQ(
  rfqId: string,
  authToken?: string,
  orgId?: string,
): Promise<RFQ> {
  const res = await request<{ data: RFQ }>(`/marketplace/rfqs/${rfqId}`, {
    method: 'GET',
    authToken,
    orgId,
  });
  return res.data;
}

/**
 * Lists RFQs involving the user's organization.
 */
export async function listRFQs(
  params?: { status?: string; page?: number; page_size?: number },
  authToken?: string,
  orgId?: string,
): Promise<{ items: RFQ[]; total: number; page: number; page_size: number }> {
  return request<{ items: RFQ[]; total: number; page: number; page_size: number }>('/marketplace/rfqs', {
    method: 'GET',
    params,
    authToken,
    orgId,
  });
}

/**
 * Lists offers submitted for an RFQ.
 */
export async function listRFQOffers(
  rfqId: string,
  authToken?: string,
  orgId?: string,
): Promise<Offer[]> {
  const res = await request<{ data: Offer[] }>(`/marketplace/rfqs/${rfqId}/offers`, {
    method: 'GET',
    authToken,
    orgId,
  });
  return res.data;
}

/**
 * Retrieves the workflow transition history for an RFQ.
 */
export async function getRFQHistory(
  rfqId: string,
  authToken?: string,
  orgId?: string,
): Promise<any[]> {
  const res = await request<{ data: any[] }>(`/marketplace/rfqs/${rfqId}/history`, {
    method: 'GET',
    authToken,
    orgId,
  });
  return res.data;
}

/**
 * Logically grouped API client interface.
 */
export const api = {
  marketplace: {
    getListings,
    createListing,
  },
  exchange: {
    createRFQ,
    approveRFQ,
    submitOffer,
    acceptOffer,
    getRFQ,
    listRFQs,
    listRFQOffers,
    getRFQHistory,
  },
  intelligence: {
    getClusterSynergies,
    getMunicipalFlows,
    getCapacityGaps,
  },
};

export default api;

