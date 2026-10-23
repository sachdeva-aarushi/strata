import {
  BuyerRequirement,
  BuyerRequirementMatchesResponse,
  EvidenceRecord,
  ExchangeListing,
  Investigation,
  MaterialLot,
  MaterialLotCreate,
  MaterialTypeInfo,
  Offer,
  PaginatedResponseEnvelope,
  QualificationAssessment,
  ResponseEnvelope,
  RFQ,
  WorkflowEvent,
} from '@/types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export class ApiError extends Error {
  code: string;
  status: number;
  details?: Record<string, any>;

  constructor(message: string, status: number, code = 'API_ERROR', details?: Record<string, any>) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

function getStoredHeaders(): Record<string, string> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  if (typeof window !== 'undefined') {
    try {
      const session = localStorage.getItem('strata_auth_session');
      if (session) {
        const user = JSON.parse(session);
        if (user.user_id) headers['X-User-Id'] = user.user_id;
        if (user.org_id) headers['X-Org-Id'] = user.org_id;
        if (user.role) headers['X-Role'] = user.role;
      }
    } catch {
      // ignore parsing error
    }
  }

  return headers;
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE}${path}`;
  const defaultHeaders = getStoredHeaders();

  const config: RequestInit = {
    ...options,
    headers: {
      ...defaultHeaders,
      ...(options.headers || {}),
    },
  };

  try {
    const res = await fetch(url, config);
    const contentType = res.headers.get('content-type');
    const isJson = contentType && contentType.includes('application/json');

    if (!res.ok) {
      let errorMessage = `HTTP error ${res.status}: ${res.statusText}`;
      let errorCode = 'HTTP_ERROR';
      let errorDetails: Record<string, any> | undefined;

      if (isJson) {
        const errorBody = await res.json().catch(() => null);
        if (errorBody?.error) {
          errorMessage = errorBody.error.message || errorMessage;
          errorCode = errorBody.error.code || errorCode;
          errorDetails = errorBody.error.details;
        } else if (errorBody?.detail) {
          errorMessage = typeof errorBody.detail === 'string' ? errorBody.detail : JSON.stringify(errorBody.detail);
        }
      }

      throw new ApiError(errorMessage, res.status, errorCode, errorDetails);
    }

    if (isJson) {
      return (await res.json()) as T;
    }
    return {} as T;
  } catch (err: any) {
    if (err instanceof ApiError) {
      throw err;
    }
    throw new ApiError(
      err?.message || 'Failed to connect to STRATA API service.',
      0,
      'NETWORK_ERROR'
    );
  }
}

export const api = {
  // Health
  health: {
    check: () => request<ResponseEnvelope<{ status: string; timestamp: string }>>('/health'),
  },

  // Materials Registry
  materials: {
    getTypes: () => request<ResponseEnvelope<MaterialTypeInfo[]>>('/materials/types'),

    listLots: (params?: {
      status?: string;
      material_type?: string;
      facility_id?: string;
      page?: number;
      page_size?: number;
    }) => {
      const q = new URLSearchParams();
      if (params?.status) q.set('status', params.status);
      if (params?.material_type) q.set('material_type', params.material_type);
      if (params?.facility_id) q.set('facility_id', params.facility_id);
      if (params?.page) q.set('page', params.page.toString());
      if (params?.page_size) q.set('page_size', params.page_size.toString());
      const queryStr = q.toString() ? `?${q.toString()}` : '';
      return request<PaginatedResponseEnvelope<MaterialLot>>(`/materials/lots${queryStr}`);
    },

    getLot: (lot_id: string) =>
      request<ResponseEnvelope<MaterialLot>>(`/materials/lots/${lot_id}`),

    createLot: (data: MaterialLotCreate) =>
      request<ResponseEnvelope<MaterialLot>>('/materials/lots', {
        method: 'POST',
        body: JSON.stringify(data),
      }),

    updateLot: (lot_id: string, data: Partial<MaterialLotCreate>) =>
      request<ResponseEnvelope<MaterialLot>>(`/materials/lots/${lot_id}`, {
        method: 'PATCH',
        body: JSON.stringify(data),
      }),

    getLotEvidence: (lot_id: string) =>
      request<ResponseEnvelope<EvidenceRecord[]>>(`/materials/lots/${lot_id}/evidence`),

    createLotEvidence: (
      lot_id: string,
      data: {
        claim_type: string;
        provenance: string;
        data_payload: Record<string, any>;
        verification_status?: string;
      }
    ) =>
      request<ResponseEnvelope<EvidenceRecord>>(`/materials/lots/${lot_id}/evidence`, {
        method: 'POST',
        body: JSON.stringify(data),
      }),

    attachEvidence: (lot_id: string, evidence_ids: string[]) =>
      request<ResponseEnvelope<MaterialLot>>(`/materials/lots/${lot_id}/evidence/attach`, {
        method: 'POST',
        body: JSON.stringify({ evidence_ids }),
      }),
  },

  // ProofPath Qualification
  qualification: {
    createInvestigation: (data: {
      lot_id: string;
      candidate_route_ids?: string[];
      notes?: string;
      run_discovery?: boolean;
    }) =>
      request<ResponseEnvelope<Investigation>>('/investigations', {
        method: 'POST',
        body: JSON.stringify(data),
      }),

    getInvestigation: (investigation_id: string) =>
      request<ResponseEnvelope<Investigation>>(`/investigations/${investigation_id}`),

    assessLot: (
      lot_id: string,
      data?: {
        candidate_route_ids?: string[];
        notes?: string;
        run_discovery?: boolean;
      }
    ) =>
      request<ResponseEnvelope<Investigation>>(`/lots/${lot_id}/qualification/assess`, {
        method: 'POST',
        body: JSON.stringify(data || {}),
      }),

    getLotAssessments: (lot_id: string) =>
      request<ResponseEnvelope<QualificationAssessment[]>>(
        `/lots/${lot_id}/qualification/assessments`
      ),
  },

  // Circular Exchange & Marketplace
  exchange: {
    listListings: (params?: {
      view?: 'exchange' | 'own';
      category?: string;
      material_type?: string;
      page?: number;
      page_size?: number;
    }) => {
      const q = new URLSearchParams();
      if (params?.view) q.set('view', params.view);
      if (params?.category) q.set('category', params.category);
      if (params?.material_type) q.set('material_type', params.material_type);
      if (params?.page) q.set('page', params.page.toString());
      if (params?.page_size) q.set('page_size', params.page_size.toString());
      const queryStr = q.toString() ? `?${q.toString()}` : '';
      return request<PaginatedResponseEnvelope<ExchangeListing>>(`/exchange/listings${queryStr}`);
    },

    getListing: (listing_id: string) =>
      request<ResponseEnvelope<ExchangeListing>>(`/exchange/listings/${listing_id}`),

    createListing: (data: {
      lot_id?: string;
      material_lot_id?: string;
      facility_id?: string;
      quantity?: number;
      available_quantity?: number;
      unit: string;
      asking_price_per_unit?: number;
      currency?: string;
      visibility?: string;
      status?: string;
    }) => {
      const payload = {
        material_lot_id: data.material_lot_id || data.lot_id,
        facility_id: data.facility_id || '00000000-0000-0000-0000-000000000010',
        available_quantity: data.available_quantity ?? data.quantity ?? 1.0,
        unit: data.unit,
        asking_price_per_unit: data.asking_price_per_unit ?? 0.0,
        currency: data.currency || 'USD',
        visibility: data.visibility || 'public',
        status: data.status || 'active',
      };
      return request<ResponseEnvelope<ExchangeListing>>('/exchange/listings', {
        method: 'POST',
        body: JSON.stringify(payload),
      });
    },

    updateListingStatus: (listing_id: string, status: string, notes?: string) =>
      request<ResponseEnvelope<ExchangeListing>>(`/exchange/listings/${listing_id}/status`, {
        method: 'POST',
        body: JSON.stringify({ status, notes }),
      }),

    getListingHistory: (listing_id: string) =>
      request<ResponseEnvelope<WorkflowEvent[]>>(`/exchange/listings/${listing_id}/history`),

    // Buyer Requirements
    listRequirements: (params?: { page?: number; page_size?: number }) => {
      const q = new URLSearchParams();
      if (params?.page) q.set('page', params.page.toString());
      if (params?.page_size) q.set('page_size', params.page_size.toString());
      const queryStr = q.toString() ? `?${q.toString()}` : '';
      return request<PaginatedResponseEnvelope<BuyerRequirement>>(
        `/exchange/buyer-requirements${queryStr}`
      );
    },

    getRequirement: (requirement_id: string) =>
      request<ResponseEnvelope<BuyerRequirement>>(
        `/exchange/buyer-requirements/${requirement_id}`
      ),

    createRequirement: (data: {
      facility_id?: string;
      material_type?: string;
      material_category?: string;
      category?: string;
      target_quantity?: number;
      min_quantity?: number;
      max_quantity?: number;
      unit: string;
      max_price_per_unit?: number;
      target_price_per_unit?: number;
      delivery_location_country?: string;
      location?: string;
      notes?: string;
    }) => {
      const validCategories = ['biomass', 'chemicals', 'metallics', 'minerals', 'packaging', 'polymers', 'textiles'];
      let category = (data.material_category || data.category || '').toLowerCase();
      if (!validCategories.includes(category)) {
        const mat = (data.material_type || '').toLowerCase();
        if (mat.includes('aluminum') || mat.includes('copper') || mat.includes('ti') || mat.includes('steel') || mat.includes('metal')) {
          category = 'metallics';
        } else if (mat.includes('polymer') || mat.includes('pp') || mat.includes('hdpe') || mat.includes('plastic')) {
          category = 'polymers';
        } else if (mat.includes('chemical') || mat.includes('solvent') || mat.includes('glycol') || mat.includes('ipa')) {
          category = 'chemicals';
        } else if (mat.includes('wood') || mat.includes('biomass')) {
          category = 'biomass';
        } else if (mat.includes('cardboard') || mat.includes('packaging')) {
          category = 'packaging';
        } else if (mat.includes('textile') || mat.includes('cotton')) {
          category = 'textiles';
        } else if (mat.includes('sand') || mat.includes('mineral') || mat.includes('slag')) {
          category = 'minerals';
        } else {
          category = 'metallics';
        }
      }

      const payload = {
        facility_id: data.facility_id || '00000000-0000-0000-0000-000000000010',
        material_category: category,
        min_quantity: data.min_quantity ?? data.target_quantity ?? 1.0,
        max_quantity: data.max_quantity ?? data.target_quantity ?? undefined,
        unit: data.unit,
        target_price_per_unit: data.target_price_per_unit ?? data.max_price_per_unit ?? undefined,
        location: data.location || data.delivery_location_country || 'CH',
        visibility: 'public',
        required_properties: {
          material_type: data.material_type,
        },
      };
      return request<ResponseEnvelope<BuyerRequirement>>('/exchange/buyer-requirements', {
        method: 'POST',
        body: JSON.stringify(payload),
      });
    },

    deleteRequirement: (requirement_id: string) =>
      request<ResponseEnvelope<{ deleted: boolean; requirement_id: string }>>(
        `/exchange/buyer-requirements/${requirement_id}`,
        { method: 'DELETE' }
      ),

    // Matching
    getRequirementMatches: (requirement_id: string) =>
      request<ResponseEnvelope<BuyerRequirementMatchesResponse>>(
        `/exchange/buyer-requirements/${requirement_id}/matches`
      ),

    // RFQs
    listRFQs: (params?: { as_buyer?: boolean; page?: number; page_size?: number }) => {
      const q = new URLSearchParams();
      if (params?.as_buyer !== undefined) q.set('as_buyer', params.as_buyer.toString());
      if (params?.page) q.set('page', params.page.toString());
      if (params?.page_size) q.set('page_size', params.page_size.toString());
      const queryStr = q.toString() ? `?${q.toString()}` : '';
      return request<PaginatedResponseEnvelope<RFQ>>(`/exchange/rfqs${queryStr}`);
    },

    getRFQ: (rfq_id: string) =>
      request<ResponseEnvelope<RFQ>>(`/exchange/rfqs/${rfq_id}`),

    createRFQ: (data: {
      listing_id: string;
      buyer_facility_id?: string;
      buyer_requirement_id?: string;
      requested_quantity: number;
      unit?: string;
      target_price_per_unit?: number;
      currency?: string;
      notes?: string;
      submit_for_approval?: boolean;
    }) =>
      request<ResponseEnvelope<RFQ>>('/exchange/rfqs', {
        method: 'POST',
        body: JSON.stringify({
          buyer_facility_id: data.buyer_facility_id || '00000000-0000-0000-0000-000000000010',
          unit: data.unit || 'tonne',
          ...data,
        }),
      }),

    submitRFQ: (rfq_id: string, notes?: string) =>
      request<ResponseEnvelope<RFQ>>(`/exchange/rfqs/${rfq_id}/submit`, {
        method: 'POST',
        body: JSON.stringify({ notes }),
      }),

    approveRFQ: (rfq_id: string, notes?: string) =>
      request<ResponseEnvelope<RFQ>>(`/exchange/rfqs/${rfq_id}/approve`, {
        method: 'POST',
        body: JSON.stringify({ notes }),
      }),

    cancelRFQ: (rfq_id: string, notes?: string) =>
      request<ResponseEnvelope<RFQ>>(`/exchange/rfqs/${rfq_id}/cancel`, {
        method: 'POST',
        body: JSON.stringify({ notes }),
      }),

    getRFQHistory: (rfq_id: string) =>
      request<ResponseEnvelope<WorkflowEvent[]>>(`/exchange/rfqs/${rfq_id}/history`),

    // Offers
    listRFQOffers: (rfq_id: string) =>
      request<ResponseEnvelope<Offer[]>>(`/exchange/rfqs/${rfq_id}/offers`),

    submitOffer: (
      rfq_id: string,
      data: {
        offered_quantity: number;
        unit: string;
        price_per_unit: number;
        currency?: string;
        terms?: string;
        valid_until?: string;
        notes?: string;
      }
    ) =>
      request<ResponseEnvelope<Offer>>(`/exchange/rfqs/${rfq_id}/offers`, {
        method: 'POST',
        body: JSON.stringify(data),
      }),

    reviewOffer: (offer_id: string, notes?: string) =>
      request<ResponseEnvelope<Offer>>(`/exchange/offers/${offer_id}/review`, {
        method: 'POST',
        body: JSON.stringify({ notes }),
      }),

    acceptOffer: (offer_id: string, notes?: string) =>
      request<ResponseEnvelope<Offer>>(`/exchange/offers/${offer_id}/accept`, {
        method: 'POST',
        body: JSON.stringify({ notes }),
      }),

    rejectOffer: (offer_id: string, notes?: string) =>
      request<ResponseEnvelope<Offer>>(`/exchange/offers/${offer_id}/reject`, {
        method: 'POST',
        body: JSON.stringify({ notes }),
      }),

    withdrawOffer: (offer_id: string, notes?: string) =>
      request<ResponseEnvelope<Offer>>(`/exchange/offers/${offer_id}/withdraw`, {
        method: 'POST',
        body: JSON.stringify({ notes }),
      }),
  },
};
