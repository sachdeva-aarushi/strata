'use client';

import React, { Suspense, useEffect, useState } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import {
  Sparkles,
  ShieldCheck,
  ShieldAlert,
  ShieldX,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Truck,
  ArrowRight,
  Layers,
  MapPin,
  RefreshCw,
  Loader2,
  ExternalLink,
  ChevronRight,
  ShoppingBag,
} from 'lucide-react';
import { AppShell } from '@/components/AppShell';
import { Badge } from '@/components/Badge';
import { api } from '@/lib/api-client';
import { useAuth } from '@/lib/auth';
import {
  BuyerRequirement,
  BuyerRequirementMatchesResponse,
  MatchCandidate,
} from '@/types';
import { formatDate, formatNumber } from '@/lib/utils';

export default function MatchingPage() {
  return (
    <Suspense fallback={<div style={{ padding: '2rem', textAlign: 'center' }}>Loading ProofPath Matching Engine...</div>}>
      <MatchingContent />
    </Suspense>
  );
}

function MatchingContent() {
  const { user } = useAuth();
  const searchParams = useSearchParams();

  const [requirements, setRequirements] = useState<BuyerRequirement[]>([]);
  const [selectedReqId, setSelectedReqId] = useState<string>('');
  const [matchesResponse, setMatchesResponse] = useState<BuyerRequirementMatchesResponse | null>(null);
  const [isLoadingReqs, setIsLoadingReqs] = useState(true);
  const [isMatching, setIsMatching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'all' | 'eligible' | 'conditional' | 'ineligible'>('all');

  // Load requirements on mount
  useEffect(() => {
    async function loadReqs() {
      setIsLoadingReqs(true);
      try {
        const res = await api.exchange.listRequirements({ page_size: 50 });
        const list = res.data || [];
        setRequirements(list);

        const urlReqId = searchParams?.get('requirement_id');
        if (urlReqId && list.some((r) => r.requirement_id === urlReqId)) {
          setSelectedReqId(urlReqId);
        } else if (list.length > 0) {
          setSelectedReqId(list[0].requirement_id);
        }
      } catch (err) {
        console.warn('Failed to load buyer requirements for matching:', err);
      } finally {
        setIsLoadingReqs(false);
      }
    }
    loadReqs();
  }, [searchParams]);

  // Load matches when selectedReqId changes
  useEffect(() => {
    if (!selectedReqId) return;

    async function loadMatches() {
      setIsMatching(true);
      setError(null);
      try {
        const res = await api.exchange.getRequirementMatches(selectedReqId);
        setMatchesResponse(res.data);
      } catch (err: any) {
        setError(err?.message || 'Failed to execute ProofPath matching on backend.');
        setMatchesResponse(null);
      } finally {
        setIsMatching(false);
      }
    }
    loadMatches();
  }, [selectedReqId]);

  const selectedRequirement = requirements.find((r) => r.requirement_id === selectedReqId);

  const candidates = matchesResponse?.matches || [];

  const filteredCandidates = candidates.filter((c) => {
    if (activeTab === 'eligible') return c.eligibility === 'eligible';
    if (activeTab === 'conditional') return c.eligibility === 'conditional';
    if (activeTab === 'ineligible') return c.eligibility === 'ineligible';
    return true;
  });

  return (
    <AppShell>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
        {/* Header */}
        <div
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '1rem',
          }}
        >
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
              <span className="label-compact" style={{ color: 'var(--accent-teal)' }}>
                Authoritative ProofPath Matching
              </span>
              <span style={{ color: 'var(--text-muted)' }}>·</span>
              <span className="label-compact" style={{ color: 'var(--text-muted)' }}>
                Deterministic Hard Gate Enforcement
              </span>
            </div>
            <h1
              className="font-serif"
              style={{
                fontSize: '1.75rem',
                fontWeight: 500,
                color: 'var(--primary)',
                letterSpacing: '-0.015em',
              }}
            >
              Candidate Compatibility &amp; Matching
            </h1>
            <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
              Evaluates registered lots against buyer specifications. Candidates are categorized into
              Eligible, Conditional, and Ineligible with full metallurgical explanations.
            </p>
          </div>

          <Link href="/requirements" className="clay-btn clay-btn-secondary" style={{ gap: '0.5rem' }}>
            <ShoppingBag size={16} />
            <span>Manage Requirements</span>
          </Link>
        </div>

        {/* Requirement Selector & Summary Card */}
        <div
          className="clay-card"
          style={{
            padding: '1.25rem',
            backgroundColor: '#ffffff',
            display: 'flex',
            flexDirection: 'column',
            gap: '1rem',
          }}
        >
          <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '1rem' }}>
            <div style={{ flex: 1, minWidth: '280px' }}>
              <label className="label-compact" style={{ display: 'block', marginBottom: '0.375rem' }}>
                Select Active Buyer Requirement
              </label>
              <select
                value={selectedReqId}
                onChange={(e) => setSelectedReqId(e.target.value)}
                className="clay-select"
                disabled={isLoadingReqs || requirements.length === 0}
              >
                {requirements.map((r) => (
                  <option key={r.requirement_id} value={r.requirement_id}>
                    {r.material_type} — {r.target_quantity} {r.unit} (${r.max_price_per_unit || 'Mkt'}/{r.unit}) [{r.requirement_id.slice(0, 8)}...]
                  </option>
                ))}
                {requirements.length === 0 && (
                  <option value="">No buyer requirements found. Post one first.</option>
                )}
              </select>
            </div>

            {selectedRequirement && (
              <div
                style={{
                  display: 'flex',
                  flexWrap: 'wrap',
                  gap: '0.75rem',
                  padding: '0.625rem 1rem',
                  backgroundColor: 'var(--bg-subtle)',
                  borderRadius: '8px',
                  border: '1px solid var(--border-subtle)',
                  alignItems: 'center',
                }}
              >
                <div>
                  <span className="label-compact">Demand Volume</span>
                  <div className="tnum" style={{ fontSize: '0.875rem', fontWeight: 700 }}>
                    {formatNumber(selectedRequirement.target_quantity)} {selectedRequirement.unit}
                  </div>
                </div>
                <div style={{ width: '1px', height: '24px', backgroundColor: 'var(--border-subtle)' }} />
                <div>
                  <span className="label-compact">Max Budget</span>
                  <div className="tnum" style={{ fontSize: '0.875rem', fontWeight: 700 }}>
                    {selectedRequirement.max_price_per_unit ? `$${selectedRequirement.max_price_per_unit}/${selectedRequirement.unit}` : 'Market Price'}
                  </div>
                </div>
                <div style={{ width: '1px', height: '24px', backgroundColor: 'var(--border-subtle)' }} />
                <div>
                  <span className="label-compact">Destination</span>
                  <div style={{ fontSize: '0.875rem', fontWeight: 600 }}>
                    {selectedRequirement.delivery_location_country || 'Switzerland (CH)'}
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* KPI Tiers Summary */}
          {matchesResponse && (
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
                gap: '0.75rem',
                paddingTop: '0.75rem',
                borderTop: '1px solid var(--border-subtle)',
              }}
            >
              <div
                style={{
                  padding: '0.625rem 0.875rem',
                  borderRadius: '6px',
                  backgroundColor: 'var(--bg-subtle)',
                }}
              >
                <span className="label-compact">Total Evaluated</span>
                <div className="tnum" style={{ fontSize: '1.25rem', fontWeight: 700 }}>
                  {matchesResponse.total_candidates_evaluated}
                </div>
              </div>

              <div
                style={{
                  padding: '0.625rem 0.875rem',
                  borderRadius: '6px',
                  backgroundColor: 'var(--status-success-bg)',
                  border: '1px solid rgba(40, 99, 67, 0.2)',
                }}
              >
                <span className="label-compact" style={{ color: 'var(--status-success)' }}>
                  Eligible (Fully Supported)
                </span>
                <div className="tnum" style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--status-success)' }}>
                  {matchesResponse.eligible_count}
                </div>
              </div>

              <div
                style={{
                  padding: '0.625rem 0.875rem',
                  borderRadius: '6px',
                  backgroundColor: 'var(--status-warning-bg)',
                  border: '1px solid rgba(184, 115, 51, 0.2)',
                }}
              >
                <span className="label-compact" style={{ color: 'var(--status-warning)' }}>
                  Conditional (Gaps/Testing)
                </span>
                <div className="tnum" style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--status-warning)' }}>
                  {matchesResponse.conditional_count}
                </div>
              </div>

              <div
                style={{
                  padding: '0.625rem 0.875rem',
                  borderRadius: '6px',
                  backgroundColor: 'var(--status-error-bg)',
                  border: '1px solid rgba(166, 58, 53, 0.2)',
                }}
              >
                <span className="label-compact" style={{ color: 'var(--status-error)' }}>
                  Ineligible (Hard Gate Fail)
                </span>
                <div className="tnum" style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--status-error)' }}>
                  {matchesResponse.ineligible_count}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Tab Filters */}
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          <button
            onClick={() => setActiveTab('all')}
            className={`clay-btn ${activeTab === 'all' ? 'clay-btn-primary' : 'clay-btn-secondary'}`}
          >
            <span>All Candidates ({candidates.length})</span>
          </button>
          <button
            onClick={() => setActiveTab('eligible')}
            className={`clay-btn ${activeTab === 'eligible' ? 'clay-btn-primary' : 'clay-btn-secondary'}`}
          >
            <span>Eligible ({matchesResponse?.eligible_count || 0})</span>
          </button>
          <button
            onClick={() => setActiveTab('conditional')}
            className={`clay-btn ${activeTab === 'conditional' ? 'clay-btn-primary' : 'clay-btn-secondary'}`}
          >
            <span>Conditional ({matchesResponse?.conditional_count || 0})</span>
          </button>
          <button
            onClick={() => setActiveTab('ineligible')}
            className={`clay-btn ${activeTab === 'ineligible' ? 'clay-btn-primary' : 'clay-btn-secondary'}`}
          >
            <span>Ineligible ({matchesResponse?.ineligible_count || 0})</span>
          </button>
        </div>

        {/* Candidate Feed */}
        {isMatching ? (
          <div style={{ padding: '4rem', textAlign: 'center' }}>
            <Loader2 size={28} className="animate-spin" style={{ margin: '0 auto 0.75rem auto' }} />
            <div style={{ fontWeight: 600 }}>Executing ProofPath Qualification Matcher...</div>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
              Testing chemical assays, physical constraints, and transport feasibility against platform invariants.
            </p>
          </div>
        ) : error ? (
          <div
            className="clay-card"
            style={{
              padding: '2rem',
              backgroundColor: 'var(--status-error-bg)',
              color: 'var(--status-error)',
              border: '1px solid rgba(166, 58, 53, 0.25)',
              textAlign: 'center',
            }}
          >
            <AlertTriangle size={28} style={{ margin: '0 auto 0.5rem auto' }} />
            <div style={{ fontWeight: 600 }}>Matching Query Error</div>
            <p style={{ fontSize: '0.8125rem', marginTop: '0.25rem' }}>{error}</p>
          </div>
        ) : filteredCandidates.length === 0 ? (
          <div
            className="clay-card"
            style={{
              padding: '3rem',
              backgroundColor: '#ffffff',
              textAlign: 'center',
              color: 'var(--text-muted)',
            }}
          >
            <Sparkles size={32} style={{ margin: '0 auto 0.5rem auto', opacity: 0.4 }} />
            <div style={{ fontWeight: 600 }}>No candidates match current filter</div>
            <p style={{ fontSize: '0.75rem', marginTop: '0.25rem' }}>
              Try selecting another requirement or broadening acceptable parameters.
            </p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {filteredCandidates.map((candidate, idx) => {
              const isEligible = candidate.eligibility === 'eligible';
              const isConditional = candidate.eligibility === 'conditional';
              const isIneligible = candidate.eligibility === 'ineligible';

              return (
                <div
                  key={idx}
                  className="clay-card"
                  style={{
                    padding: '1.25rem',
                    backgroundColor: '#ffffff',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '1rem',
                    borderLeft: isEligible
                      ? '4px solid var(--status-success)'
                      : isConditional
                      ? '4px solid var(--status-warning)'
                      : '4px solid var(--status-error)',
                  }}
                >
                  {/* Top Candidate Bar */}
                  <div
                    style={{
                      display: 'flex',
                      flexWrap: 'wrap',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      gap: '0.75rem',
                      paddingBottom: '0.75rem',
                      borderBottom: '1px solid var(--border-subtle)',
                    }}
                  >
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <h3 style={{ fontSize: '1.0625rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                          {candidate.listing.material_type || 'Industrial Scrap Lot'}
                        </h3>
                        <span
                          style={{
                            fontSize: '0.6875rem',
                            fontFamily: 'monospace',
                            color: 'var(--text-muted)',
                          }}
                        >
                          Listing: {candidate.listing.listing_id.slice(0, 8)}...
                        </span>
                      </div>
                      <div
                        style={{
                          fontSize: '0.75rem',
                          color: 'var(--text-secondary)',
                          marginTop: '0.15rem',
                        }}
                      >
                        Available: <strong>{formatNumber(candidate.listing.quantity)}</strong> {candidate.listing.unit} · Asking: ${candidate.listing.asking_price_per_unit || 'Negotiable'}/{candidate.listing.unit}
                      </div>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
                      {/* Compatibility Score */}
                      <div
                        style={{
                          padding: '0.25rem 0.625rem',
                          borderRadius: '6px',
                          backgroundColor: isEligible
                            ? 'var(--status-success-bg)'
                            : isConditional
                            ? 'var(--status-warning-bg)'
                            : 'var(--status-error-bg)',
                          color: isEligible
                            ? 'var(--status-success)'
                            : isConditional
                            ? 'var(--status-warning)'
                            : 'var(--status-error)',
                          fontWeight: 700,
                          fontSize: '0.8125rem',
                        }}
                        className="tnum"
                      >
                        {candidate.match_score.toFixed(1)}% Match
                      </div>

                      {/* Eligibility Badge */}
                      {isEligible && (
                        <Badge variant="success" dot>
                          Eligible
                        </Badge>
                      )}
                      {isConditional && (
                        <Badge variant="warning" dot>
                          Conditional
                        </Badge>
                      )}
                      {isIneligible && (
                        <Badge variant="error" dot>
                          Ineligible
                        </Badge>
                      )}
                    </div>
                  </div>

                  {/* Reasons & Incompatibilities Grid */}
                  <div
                    style={{
                      display: 'grid',
                      gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
                      gap: '1rem',
                      alignItems: 'start',
                    }}
                  >
                    {/* Compatibility Reasons */}
                    <div>
                      <span className="label-compact" style={{ display: 'block', marginBottom: '0.375rem' }}>
                        Compatibility Attributes
                      </span>
                      {candidate.compatibility_reasons.length === 0 ? (
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                          No positive compatibility attributes recorded.
                        </div>
                      ) : (
                        <ul style={{ paddingLeft: '1.25rem', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                          {candidate.compatibility_reasons.map((r, i) => (
                            <li key={i} style={{ marginBottom: '0.2rem' }}>
                              {r}
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>

                    {/* Hard Gate Incompatibilities (if any) */}
                    {candidate.incompatibilities.length > 0 && (
                      <div
                        style={{
                          padding: '0.75rem',
                          borderRadius: '6px',
                          backgroundColor: 'var(--status-error-bg)',
                          border: '1px solid rgba(166, 58, 53, 0.2)',
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', marginBottom: '0.25rem' }}>
                          <XCircle size={14} color="var(--status-error)" />
                          <span className="label-compact" style={{ color: 'var(--status-error)', fontWeight: 700 }}>
                            Violated Hard Gates ({candidate.incompatibilities.length})
                          </span>
                        </div>
                        <ul style={{ paddingLeft: '1.25rem', fontSize: '0.75rem', color: 'var(--status-error)' }}>
                          {candidate.incompatibilities.map((inc, i) => (
                            <li key={i} style={{ marginBottom: '0.2rem' }}>
                              {inc}
                            </li>
                          ))}
                        </ul>
                        <div style={{ fontSize: '0.6875rem', color: 'var(--text-muted)', marginTop: '0.375rem' }}>
                          * Inviolable platform policy: Hard gates cannot be overridden by user preference.
                        </div>
                      </div>
                    )}

                    {/* Missing Information (if any) */}
                    {candidate.missing_information.length > 0 && (
                      <div
                        style={{
                          padding: '0.75rem',
                          borderRadius: '6px',
                          backgroundColor: 'var(--status-warning-bg)',
                          border: '1px solid rgba(184, 115, 51, 0.2)',
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', marginBottom: '0.25rem' }}>
                          <AlertTriangle size={14} color="var(--status-warning)" />
                          <span className="label-compact" style={{ color: 'var(--status-warning)', fontWeight: 700 }}>
                            Missing Specifications ({candidate.missing_information.length})
                          </span>
                        </div>
                        <ul style={{ paddingLeft: '1.25rem', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                          {candidate.missing_information.map((m, i) => (
                            <li key={i} style={{ marginBottom: '0.2rem' }}>
                              {m}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>

                  {/* Freight / Logistics & Action Footer */}
                  <div
                    style={{
                      display: 'flex',
                      flexWrap: 'wrap',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      gap: '0.75rem',
                      paddingTop: '0.75rem',
                      borderTop: '1px solid var(--border-subtle)',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem' }}>
                        <Truck size={14} color="var(--primary-container)" />
                        <span>Distance: <strong>{candidate.distance_km ? `${candidate.distance_km} km` : 'Regional Transit'}</strong></span>
                      </div>
                      {candidate.logistics_summary && (
                        <span>· Freight: {candidate.logistics_summary.recommended_mode || 'Multimodal Rail'}</span>
                      )}
                    </div>

                    <div>
                      {isIneligible ? (
                        <button
                          disabled
                          className="clay-btn-ghost"
                          style={{
                            padding: '0.375rem 0.75rem',
                            fontSize: '0.75rem',
                            opacity: 0.5,
                            cursor: 'not-allowed',
                          }}
                        >
                          Blocked by Hard Gate
                        </button>
                      ) : (
                        <Link
                          href={`/rfqs?action=new&listing_id=${candidate.listing.listing_id}&requirement_id=${selectedReqId}`}
                          className="clay-btn clay-btn-primary"
                          style={{
                            padding: '0.375rem 0.75rem',
                            fontSize: '0.75rem',
                            textDecoration: 'none',
                            gap: '0.375rem',
                          }}
                        >
                          <span>Initiate RFQ Deal</span>
                          <ArrowRight size={14} />
                        </Link>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </AppShell>
  );
}
