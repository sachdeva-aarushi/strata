/**
 * ==============================================================================
 * STRATA FRONTEND DATA CONTRACTS & TYPE DEFINITIONS
 * ==============================================================================
 * Derived from inspected PRD schemas, SQLAlchemy models, and Alembic migrations.
 * Exact field names enforced:
 *   - org_id (not organization_id) on organizations
 *   - lot_id (not id) on material_lots
 *   - requested_quantity (not target_quantity) on marketplace_rfqs
 *   - provenance_label (not data_provenance) on material_lots
 * ==============================================================================
 */

export type ListingVisibility = 'private' | 'cluster_only' | 'public';
export type ListingStatus = 'draft' | 'active' | 'paused' | 'sold_out' | 'withdrawn';

export type RFQStatus = 'draft' | 'pending_approval' | 'open' | 'closed' | 'cancelled' | 'submitted' | 'accepted' | 'rejected';
export type OfferStatus = 'submitted' | 'under_review' | 'revised' | 'accepted' | 'rejected' | 'withdrawn' | 'pending';

export type ZoneClassification = 'DEFICIT_HOTSPOT' | 'BALANCED' | 'SURPLUS_CAPACITY' | 'SUPPRESSED';

export interface Listing {
  id?: string;
  listing_id: string;
  material_lot_id?: string;
  lot_id?: string;
  organization_id?: string;
  org_id?: string;
  facility_id?: string;
  facility_name?: string;
  cluster_id?: string;
  cluster_name?: string;
  visibility?: ListingVisibility;
  asking_price_per_unit?: number;
  currency?: string;
  available_quantity?: number;
  quantity?: number;
  unit?: string;
  status: ListingStatus | string;
  material_type?: string;
  material_category?: string | null;
  material_properties?: Record<string, any>;
  location?: string;
  availability_from?: string;
  availability_to?: string;
  lot_quantity?: number;
  provenance_label?: string;
  data_provenance?: string;
  lot?: any;
  created_at?: string;
  updated_at?: string;
}

export type MarketplaceListing = Listing;

export interface ListingSearchParams {
  view?: 'all' | 'exchange' | 'own';
  category?: string;
  material_type?: string;
  unit?: string;
  min_quantity?: number;
  max_quantity?: number;
  max_price?: number;
  visibility?: ListingVisibility;
  page?: number;
  page_size?: number;
  orgId?: string;
}

export interface ListingSearchResult {
  data?: Listing[];
  items?: Listing[];
  pagination?: {
    total: number;
    page: number;
    page_size: number;
    has_next: boolean;
  };
  total?: number;
  page?: number;
  page_size?: number;
  meta?: {
    request_id?: string;
    timestamp?: string;
  };
}

export interface CreateListingPayload {
  material_lot_id: string;
  facility_id: string;
  visibility: ListingVisibility;
  asking_price_per_unit: number;
  currency?: string;
  available_quantity: number;
  unit: string;
}

export interface RFQ {
  id?: string;
  rfq_id: string;
  listing_id: string;
  buyer_requirement_id?: string | null;
  buyer_organization_id?: string;
  buyer_org_id?: string;
  buyer_facility_id?: string;
  seller_organization_id?: string;
  seller_org_id?: string;
  seller_facility_id?: string;
  requested_quantity: number;
  unit?: string;
  target_price_per_unit?: number | null;
  currency?: string;
  status: RFQStatus | string;
  notes?: string | null;
  created_by?: string;
  approved_by?: string | null;
  approved_at?: string | null;
  buyer_org_name?: string;
  seller_org_name?: string;
  created_at?: string;
  updated_at?: string;
}

export interface CreateRFQPayload {
  listing_id: string;
  requested_quantity: number;
  unit?: string;
  target_price_per_unit?: number;
  currency?: string;
  notes?: string;
  buyer_requirement_id?: string;
  buyer_facility_id?: string;
}

export interface Offer {
  id?: string;
  offer_id: string;
  rfq_id: string;
  listing_id?: string;
  seller_organization_id?: string;
  seller_org_id?: string;
  seller_facility_id?: string;
  offered_quantity: number;
  unit: string;
  price_per_unit: number;
  currency?: string;
  status: OfferStatus | string;
  terms?: string | null;
  valid_until?: string | null;
  created_by?: string;
  reviewed_by?: string | null;
  reviewed_at?: string | null;
  created_at?: string;
  updated_at?: string;
}

export interface SubmitOfferPayload {
  offered_quantity: number;
  unit: string;
  price_per_unit: number;
  currency?: string;
  terms?: string;
  valid_until?: string;
  notes?: string;
}

export interface WorkflowEvent {
  id: string;
  entity_type: string;
  entity_id: string;
  event_type: string;
  from_state?: string | null;
  to_state: string;
  actor_id: string;
  actor_role: string;
  actor_org_id: string;
  notes?: string | null;
  metadata?: Record<string, any>;
  created_at: string;
}

export interface ClusterSynergyResult {
  cluster_id: string;
  synergies: Array<{
    source_facility_id: string;
    target_facility_id: string;
    material_type: string;
    annual_tonnage: number;
    distance_km: number;
    status: string;
  }>;
}

export interface MunicipalFlowParams {
  city_id?: string;
  zone_id?: string;
  material_category?: string;
  start_date?: string;
  end_date?: string;
  period_start?: string;
  period_end?: string;
}

export interface MunicipalZoneFlow {
  zone_name: string;
  material_category: string;
  generation_kg: number;
  capacity_kg: number;
  net_balance_kg: number;
  classification: ZoneClassification | string;
  facility_count?: number;
  cohort_suppressed?: boolean;
}

export interface MunicipalFlowResult {
  city_id?: string;
  zone_id?: string;
  flows: MunicipalZoneFlow[];
  has_suppressed_zones: boolean;
  suppression_message?: string;
}

export interface CapacityGapResult {
  city_id?: string;
  zones: MunicipalZoneFlow[];
  has_suppressed_zones: boolean;
  suppression_message?: string;
}

export interface BlockchainVerification {
  record_id: string;
  is_verified: boolean;
  blockchain_tx_hash: string;
  block_number: number;
  anchored_at?: string;
  chain_id?: number;
}
