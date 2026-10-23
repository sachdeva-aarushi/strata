export type UserRole =
  | 'facility_operator'
  | 'buyer'
  | 'seller'
  | 'admin'
  | 'municipal_authority';

export interface AuthUser {
  user_id: string;
  org_id: string;
  org_name?: string;
  role: UserRole;
  cluster_ids?: string[];
  email?: string;
  name?: string;
  facility_id?: string;
  facility_name?: string;
}

export type OrgType =
  | 'manufacturer'
  | 'processor'
  | 'aggregator'
  | 'logistics'
  | 'cluster'
  | 'municipality';

export interface OrganizationRef {
  org_id: string;
  name: string;
  org_type: OrgType;
  jurisdiction_country?: string;
  domain?: string;
  contact_name?: string;
  contact_title?: string;
}

export interface FacilityRef {
  facility_id: string;
  org_id: string;
  name: string;
  location_country: string;
  location_postal_code?: string;
  cluster_id?: string;
  city_id?: string;
  zone_id?: string;
  processing_capacity_tpa?: number;
  facility_type?: 'generator' | 'receiver' | 'aggregator';
}

export type MaterialLotStatus =
  | 'draft'
  | 'available'
  | 'under_qualification'
  | 'listed'
  | 'matched'
  | 'rfq_in_progress'
  | 'order_confirmed'
  | 'dispatched'
  | 'received'
  | 'outcome_recorded'
  | 'withdrawn';

export interface MaterialTypeInfo {
  type_id: string;
  name: string;
  category: string;
  standard_units: string[];
  is_hazardous: boolean;
  description: string;
}

export interface MaterialLot {
  lot_id: string;
  org_id: string;
  facility_id: string;
  material_type: string;
  quantity: number;
  unit: string;
  status: MaterialLotStatus;
  availability_from: string;
  availability_to?: string | null;
  declared_attributes: Record<string, any>;
  provenance_label: string;
  evidence_ids?: string[];
  created_at: string;
  updated_at: string;
}

export interface MaterialLotCreate {
  material_type: string;
  quantity: number;
  unit: string;
  facility_id: string;
  availability_from: string;
  availability_to?: string | null;
  declared_attributes?: Record<string, any>;
  status?: MaterialLotStatus;
  provenance_label?: string;
  evidence_ids?: string[];
}

export type QualificationOutcome = 'supported' | 'conditional' | 'unsupported';

export interface HardGateResult {
  gate_id: string;
  gate_name: string;
  outcome: string;
  material_value?: any;
  required_value?: any;
  evidence_ref_id?: string | null;
  blocking?: boolean;
}

export interface MissingFact {
  fact_id: string;
  description: string;
  acquisition_method?: string;
  is_critical?: boolean;
}

export interface HardIncompatibility {
  rule_id: string;
  parameter: string;
  required_threshold: string | number;
  actual_value: string | number;
  reason: string;
}

export interface EvidenceRecord {
  evidence_id: string;
  lot_id?: string;
  org_id: string;
  claim_type: string;
  provenance: string;
  verification_status: string;
  data_payload: Record<string, any>;
  retrieved_at: string;
}

export interface QualificationAssessment {
  assessment_id: string;
  lot_id: string;
  candidate_route_id?: string;
  route_id?: string;
  status?: QualificationOutcome;
  outcome?: QualificationOutcome;
  hard_gate_results?: HardGateResult[];
  hard_incompatibilities?: HardIncompatibility[];
  blocking_conditions?: string[];
  missing_facts?: MissingFact[];
  recommendations?: string[];
  rationale?: string;
  next_action?: string;
  evidence_refs?: string[];
  supporting_evidence_ids?: string[];
  rule_version?: string;
  created_at?: string;
  assessed_at?: string;
}

export interface Investigation {
  investigation_id: string;
  lot_id: string;
  org_id: string;
  status: 'pending' | 'completed' | 'failed';
  qualification_outcome?: QualificationOutcome;
  candidate_route_ids?: string[];
  assessments?: QualificationAssessment[];
  hard_incompatibilities?: HardIncompatibility[];
  recommendations?: string[];
  notes?: string;
  created_at: string;
  completed_at?: string;
}

export interface ExchangeListing {
  id?: string;
  listing_id: string;
  lot_id?: string;
  material_lot_id?: string;
  org_id: string;
  facility_id: string;
  material_type?: string;
  category?: string;
  quantity?: number;
  available_quantity?: number;
  unit: string;
  asking_price_per_unit?: number | null;
  currency?: string;
  visibility: 'public' | 'cluster_only' | 'verified_only';
  status: 'active' | 'paused' | 'matched' | 'withdrawn' | 'draft';
  created_at: string;
  lot?: MaterialLot;
  location?: string;
  notes?: string;
}

export interface BuyerRequirement {
  id?: string;
  requirement_id: string;
  org_id: string;
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
  delivery_location?: string;
  location?: string;
  status: 'active' | 'fulfilled' | 'cancelled';
  notes?: string;
  created_at: string;
}

export interface MatchCandidate {
  listing: ExchangeListing;
  match_score: number;
  eligibility: 'eligible' | 'conditional' | 'ineligible';
  compatibility_reasons: string[];
  incompatibilities: string[];
  missing_information: string[];
  distance_km?: number | null;
  logistics_summary?: Record<string, any> | null;
  qualification_details?: Record<string, any> | null;
}

export interface BuyerRequirementMatchesResponse {
  requirement_id: string;
  total_candidates_evaluated: number;
  eligible_count: number;
  conditional_count: number;
  ineligible_count: number;
  matches: MatchCandidate[];
}

export interface Offer {
  id: string;
  rfq_id: string;
  listing_id: string;
  seller_organization_id: string;
  seller_facility_id: string;
  offered_quantity: number;
  unit: string;
  price_per_unit: number;
  currency: string;
  status: 'draft' | 'pending_review' | 'under_review' | 'accepted' | 'rejected' | 'withdrawn' | 'expired';
  terms?: string | null;
  valid_until?: string | null;
  created_by: string;
  reviewed_by?: string | null;
  reviewed_at?: string | null;
  created_at: string;
  updated_at?: string | null;
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

export interface RFQ {
  rfq_id: string;
  listing_id: string;
  buyer_org_id: string;
  seller_org_id: string;
  requested_quantity: number;
  target_price_per_unit?: number;
  currency?: string;
  unit?: string;
  status: 'draft' | 'submitted' | 'approved' | 'accepted' | 'rejected' | 'cancelled';
  notes?: string;
  created_at: string;
}

export interface PaginationInfo {
  total: number;
  page: number;
  page_size: number;
  has_next: boolean;
}

export interface ResponseEnvelope<T> {
  data: T;
  meta: {
    request_id: string;
    timestamp: string;
  };
}

export interface PaginatedResponseEnvelope<T> {
  data: T[];
  pagination: PaginationInfo;
  meta: {
    request_id: string;
    timestamp: string;
  };
}

export interface ErrorEnvelope {
  error: {
    code: string;
    message: string;
    details?: Record<string, any>;
  };
}
