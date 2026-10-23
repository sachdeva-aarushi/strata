'use client';

import React, { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import {
  ShoppingCart,
  Search,
  Plus,
  ArrowRight,
  Loader2,
  AlertCircle,
  RefreshCw,
  ShieldCheck,
  FileText,
  Package,
  CheckCircle2,
  Clock,
  XCircle,
} from 'lucide-react';
import { AppShell } from '@/components/AppShell';
import { Badge } from '@/components/Badge';
import { MetricCard } from '@/components/MetricCard';
import { api } from '@/lib/api-client';
import { useAuth } from '@/lib/auth';
import { BuyerRequirement, ExchangeListing, RFQ } from '@/types';
import { formatNumber, formatDate, formatCurrency } from '@/lib/utils';

export default function BuyerDashboardPage() {
  const { user } = useAuth();

  const [requirements, setRequirements] = useState<BuyerRequirement[]>([]);
  const [listings, setListings] = useState<ExchangeListing[]>([]);
  const [rfqs, setRfqs] = useState<RFQ[]>([]);

  const [loadingReqs, setLoadingReqs] = useState(true);
  const [loadingListings, setLoadingListings] = useState(true);
  const [loadingRfqs, setLoadingRfqs] = useState(true);

  const [reqError, setReqError] = useState<string | null>(null);
  const [listingsError, setListingsError] = useState<string | null>(null);
  const [rfqsError, setRfqsError] = useState<string | null>(null);

  const loadAll = useCallback(async () => {
    // Buyer requirements
    setLoadingReqs(true);
    api.exchange.listRequirements({ page_size: 20 })
      .then((r) => setRequirements(r.data || []))
      .catch((e) => setReqError(e?.message || 'Failed to load requirements.'))
      .finally(() => setLoadingReqs(false));

    // Available marketplace listings (from other orgs)
    setLoadingListings(true);
    api.exchange.listListings({ view: 'exchange', page_size: 8 })
      .then((r) => setListings(r.data || []))
      .catch((e) => setListingsError(e?.message || 'Failed to load listings.'))
      .finally(() => setLoadingListings(false));

    // RFQs as buyer
    setLoadingRfqs(true);
    api.exchange.listRFQs({ as_buyer: true, page_size: 10 })
      .then((r) => setRfqs(r.data || []))
      .catch((e) => setRfqsError(e?.message || 'Failed to load RFQs.'))
      .finally(() => setLoadingRfqs(false));
  }, []);

  useEffect(() => { loadAll(); }, [loadAll]);

  const pendingRfqs = rfqs.filter((r) => ['draft', 'submitted', 'under_review'].includes(r.status));
  const acceptedRfqs = rfqs.filter((r) => r.status === 'accepted' || r.status === 'approved');

  const getRfqBadge = (status: string) => {
    if (['accepted', 'approved'].includes(status)) return <Badge variant="success" dot>{status}</Badge>;
    if (status === 'submitted' || status === 'under_review') return <Badge variant="warning" dot>{status.replace('_', ' ')}</Badge>;
    if (status === 'cancelled' || status === 'rejected') return <Badge variant="error">{status}</Badge>;
    return <Badge variant="neutral">{status}</Badge>;
  };

  return (
    <AppShell>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
        {/* Header */}
        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'flex-start', justifyContent: 'space-between', gap: '1rem' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
              <ShoppingCart size={16} color="var(--accent-teal)" />
              <span className="label-compact" style={{ color: 'var(--accent-teal)' }}>Buyer Workspace</span>
            </div>
            <h1 className="font-serif" style={{ fontSize: '1.75rem', fontWeight: 500, color: 'var(--primary)', letterSpacing: '-0.015em' }}>
              Buyer Dashboard
            </h1>
            <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
              {user?.name || 'Buyer'} · {user?.facility_name || 'Your Facility'}
            </p>
          </div>
          <div style={{ display: 'flex', gap: '0.625rem' }}>
            <Link href="/requirements" className="clay-btn clay-btn-secondary">
              <Plus size={15} />
              New Requirement
            </Link>
            <Link href="/marketplace" className="clay-btn clay-btn-primary">
              <Search size={15} />
              Browse Materials
            </Link>
          </div>
        </div>

        {/* KPIs */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
          <MetricCard
            label="Active Requirements"
            value={requirements.length}
            subtext="Posted buyer demands"
            icon={<Package size={18} />}
          />
          <MetricCard
            label="Available Listings"
            value={listings.length}
            subtext="On circular exchange"
            icon={<RefreshCw size={18} />}
          />
          <MetricCard
            label="Pending RFQs"
            value={pendingRfqs.length}
            subtext="Awaiting seller response"
            icon={<Clock size={18} />}
          />
          <MetricCard
            label="Accepted Deals"
            value={acceptedRfqs.length}
            subtext="Confirmed orders"
            deltaType="positive"
            icon={<CheckCircle2 size={18} />}
          />
        </div>

        {/* Two-column layout: Requirements + Marketplace browse */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '1.5rem' }}>
          {/* My Requirements */}
          <div className="clay-card" style={{ padding: '1.25rem', backgroundColor: '#ffffff' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingBottom: '0.75rem', borderBottom: '1px solid var(--border-subtle)', marginBottom: '1rem' }}>
              <div>
                <span className="label-compact">Feedstock Demands</span>
                <h3 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)' }}>My Buyer Requirements</h3>
              </div>
              <Link href="/requirements" style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--primary-container)', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                Manage <ArrowRight size={13} />
              </Link>
            </div>

            {loadingReqs ? (
              <div style={{ display: 'flex', justifyContent: 'center', padding: '1.5rem', color: 'var(--text-muted)' }}>
                <Loader2 size={18} className="animate-spin" />
              </div>
            ) : reqError ? (
              <div style={{ padding: '0.75rem', borderRadius: '8px', backgroundColor: 'var(--status-error-bg)', color: 'var(--status-error)', fontSize: '0.8125rem', display: 'flex', gap: '0.5rem' }}>
                <AlertCircle size={15} />{reqError}
              </div>
            ) : requirements.length === 0 ? (
              <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                <Package size={28} style={{ margin: '0 auto 0.5rem', opacity: 0.4 }} />
                <p style={{ fontSize: '0.8125rem', marginBottom: '0.75rem' }}>No buyer requirements posted yet.</p>
                <Link href="/requirements" className="clay-btn clay-btn-secondary" style={{ display: 'inline-flex' }}>
                  Post a Requirement
                </Link>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.625rem' }}>
                {requirements.slice(0, 6).map((req) => (
                  <div key={req.requirement_id} style={{ padding: '0.75rem', borderRadius: '8px', backgroundColor: 'var(--bg-subtle)', border: '1px solid var(--border-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.75rem' }}>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontWeight: 600, fontSize: '0.8125rem', color: 'var(--text-primary)', marginBottom: '0.2rem' }}>
                        {req.material_type || req.material_category || 'Material Requirement'}
                      </div>
                      <div style={{ fontSize: '0.6875rem', color: 'var(--text-muted)', display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                        <span className="tnum">{formatNumber(req.min_quantity)} {req.unit}</span>
                        {req.target_price_per_unit && <span>≤${req.target_price_per_unit}/{req.unit}</span>}
                        {req.location && <span>📍{req.location}</span>}
                      </div>
                    </div>
                    <Link href={`/matching?req=${req.requirement_id}`} className="clay-btn clay-btn-secondary" style={{ fontSize: '0.6875rem', padding: '0.3rem 0.625rem', flexShrink: 0 }}>
                      <ShieldCheck size={12} />
                      Match
                    </Link>
                  </div>
                ))}
                {requirements.length > 6 && (
                  <Link href="/requirements" style={{ textAlign: 'center', fontSize: '0.75rem', color: 'var(--primary-container)', fontWeight: 600, textDecoration: 'none', padding: '0.5rem' }}>
                    +{requirements.length - 6} more →
                  </Link>
                )}
              </div>
            )}
          </div>

          {/* Browse Marketplace */}
          <div className="clay-card" style={{ padding: '1.25rem', backgroundColor: '#ffffff' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingBottom: '0.75rem', borderBottom: '1px solid var(--border-subtle)', marginBottom: '1rem' }}>
              <div>
                <span className="label-compact">Available Now</span>
                <h3 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)' }}>Marketplace Listings</h3>
              </div>
              <Link href="/exchange" style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--primary-container)', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                Exchange Board <ArrowRight size={13} />
              </Link>
            </div>

            {loadingListings ? (
              <div style={{ display: 'flex', justifyContent: 'center', padding: '1.5rem', color: 'var(--text-muted)' }}>
                <Loader2 size={18} className="animate-spin" />
              </div>
            ) : listingsError ? (
              <div style={{ padding: '0.75rem', borderRadius: '8px', backgroundColor: 'var(--status-error-bg)', color: 'var(--status-error)', fontSize: '0.8125rem', display: 'flex', gap: '0.5rem' }}>
                <AlertCircle size={15} />{listingsError}
              </div>
            ) : listings.length === 0 ? (
              <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                <RefreshCw size={28} style={{ margin: '0 auto 0.5rem', opacity: 0.4 }} />
                <p style={{ fontSize: '0.8125rem' }}>No listings currently available.</p>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.625rem' }}>
                {listings.map((listing) => (
                  <div key={listing.listing_id} style={{ padding: '0.75rem', borderRadius: '8px', backgroundColor: 'var(--bg-subtle)', border: '1px solid var(--border-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.75rem' }}>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontWeight: 600, fontSize: '0.8125rem', color: 'var(--text-primary)', marginBottom: '0.2rem' }}>
                        {listing.material_type || 'Industrial Material'}
                      </div>
                      <div style={{ fontSize: '0.6875rem', color: 'var(--text-muted)', display: 'flex', gap: '0.5rem' }}>
                        <span className="tnum">{formatNumber(listing.quantity)} {listing.unit}</span>
                        {listing.asking_price_per_unit != null && (
                          <span className="tnum">${listing.asking_price_per_unit}/{listing.unit}</span>
                        )}
                      </div>
                    </div>
                    <Link href="/rfqs" className="clay-btn clay-btn-secondary" style={{ fontSize: '0.6875rem', padding: '0.3rem 0.625rem', flexShrink: 0 }}>
                      <FileText size={12} />
                      RFQ
                    </Link>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* RFQ Status Panel */}
        <div className="clay-card" style={{ padding: '1.25rem', backgroundColor: '#ffffff' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingBottom: '0.75rem', borderBottom: '1px solid var(--border-subtle)', marginBottom: '1rem' }}>
            <div>
              <span className="label-compact">Negotiation Tracker</span>
              <h3 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)' }}>My RFQs & Offers</h3>
            </div>
            <Link href="/rfqs" style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--primary-container)', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
              Full Workspace <ArrowRight size={13} />
            </Link>
          </div>

          {loadingRfqs ? (
            <div style={{ display: 'flex', justifyContent: 'center', padding: '1.5rem', color: 'var(--text-muted)' }}>
              <Loader2 size={18} className="animate-spin" />
            </div>
          ) : rfqsError ? (
            <div style={{ padding: '0.75rem', borderRadius: '8px', backgroundColor: 'var(--status-error-bg)', color: 'var(--status-error)', fontSize: '0.8125rem', display: 'flex', gap: '0.5rem' }}>
              <AlertCircle size={15} />{rfqsError}
            </div>
          ) : rfqs.length === 0 ? (
            <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}>
              <FileText size={28} style={{ margin: '0 auto 0.5rem', opacity: 0.4 }} />
              <p style={{ fontSize: '0.8125rem', marginBottom: '0.75rem' }}>No RFQs submitted yet. Browse the marketplace to initiate a deal.</p>
              <Link href="/exchange" className="clay-btn clay-btn-secondary" style={{ display: 'inline-flex' }}>Browse Exchange</Link>
            </div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '0.75rem' }}>
              {rfqs.slice(0, 6).map((rfq) => (
                <div key={rfq.rfq_id} style={{ padding: '0.875rem 1rem', borderRadius: '8px', backgroundColor: 'var(--bg-subtle)', border: '1px solid var(--border-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
                      <span style={{ fontFamily: 'monospace', fontSize: '0.75rem', fontWeight: 600 }}>RFQ-{rfq.rfq_id.slice(0, 8)}</span>
                      {getRfqBadge(rfq.status)}
                    </div>
                    <div className="tnum" style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                      {formatNumber(rfq.requested_quantity)} MT
                      {rfq.target_price_per_unit && ` · Target $${rfq.target_price_per_unit}/MT`}
                    </div>
                  </div>
                  <Link href={`/rfqs?rfq_id=${rfq.rfq_id}`} className="clay-btn clay-btn-ghost" style={{ fontSize: '0.6875rem', padding: '0.3rem 0.625rem' }}>
                    View
                  </Link>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Quick links */}
        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
          <Link href="/matching" className="clay-btn clay-btn-secondary">
            <ShieldCheck size={15} />
            ProofPath Matching
          </Link>
          <Link href="/proofpath" className="clay-btn clay-btn-secondary">
            <ShieldCheck size={15} />
            Qualification Status
          </Link>
          <Link href="/requirements" className="clay-btn clay-btn-secondary">
            <Plus size={15} />
            Post New Requirement
          </Link>
        </div>
      </div>
    </AppShell>
  );
}
