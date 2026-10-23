'use client';

import React, { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import {
  Layers,
  Plus,
  ArrowRight,
  Loader2,
  AlertCircle,
  ShieldCheck,
  FileText,
  RefreshCw,
  Package,
  CheckCircle2,
  Clock,
  BarChart2,
  TrendingUp,
} from 'lucide-react';
import { AppShell } from '@/components/AppShell';
import { Badge } from '@/components/Badge';
import { MetricCard } from '@/components/MetricCard';
import { api } from '@/lib/api-client';
import { useAuth } from '@/lib/auth';
import { MaterialLot, ExchangeListing, RFQ } from '@/types';
import { formatNumber, formatDate } from '@/lib/utils';

export default function SellerDashboardPage() {
  const { user } = useAuth();

  const [lots, setLots] = useState<MaterialLot[]>([]);
  const [listings, setListings] = useState<ExchangeListing[]>([]);
  const [rfqs, setRfqs] = useState<RFQ[]>([]);

  const [loadingLots, setLoadingLots] = useState(true);
  const [loadingListings, setLoadingListings] = useState(true);
  const [loadingRfqs, setLoadingRfqs] = useState(true);

  const [lotsError, setLotsError] = useState<string | null>(null);
  const [listingsError, setListingsError] = useState<string | null>(null);
  const [rfqsError, setRfqsError] = useState<string | null>(null);

  const loadAll = useCallback(async () => {
    setLoadingLots(true);
    api.materials.listLots({ page_size: 30 })
      .then((r) => setLots(r.data || []))
      .catch((e) => setLotsError(e?.message || 'Failed to load material lots.'))
      .finally(() => setLoadingLots(false));

    setLoadingListings(true);
    api.exchange.listListings({ view: 'own', page_size: 20 })
      .then((r) => setListings(r.data || []))
      .catch((e) => setListingsError(e?.message || 'Failed to load listings.'))
      .finally(() => setLoadingListings(false));

    setLoadingRfqs(true);
    api.exchange.listRFQs({ as_buyer: false, page_size: 10 })
      .then((r) => setRfqs(r.data || []))
      .catch((e) => setRfqsError(e?.message || 'Failed to load RFQs.'))
      .finally(() => setLoadingRfqs(false));
  }, []);

  useEffect(() => { loadAll(); }, [loadAll]);

  const qualifiedLots = lots.filter((l) => l.status === 'available' || l.status === 'listed');
  const activeListings = listings.filter((l) => l.status === 'active');
  const pendingRfqs = rfqs.filter((r) => ['submitted', 'under_review'].includes(r.status));

  const getLotStatusBadge = (status: string) => {
    if (status === 'available') return <Badge variant="success" dot>Available</Badge>;
    if (status === 'listed') return <Badge variant="teal" dot>Listed</Badge>;
    if (status === 'under_qualification') return <Badge variant="warning" dot>Qualifying</Badge>;
    if (status === 'draft') return <Badge variant="neutral">Draft</Badge>;
    if (status === 'matched') return <Badge variant="teal" dot>Matched</Badge>;
    return <Badge variant="neutral">{status.replace(/_/g, ' ')}</Badge>;
  };

  return (
    <AppShell>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
        {/* Header */}
        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'flex-start', justifyContent: 'space-between', gap: '1rem' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
              <Layers size={16} color="var(--accent-teal)" />
              <span className="label-compact" style={{ color: 'var(--accent-teal)' }}>Seller Workspace</span>
            </div>
            <h1 className="font-serif" style={{ fontSize: '1.75rem', fontWeight: 500, color: 'var(--primary)', letterSpacing: '-0.015em' }}>
              Seller Dashboard
            </h1>
            <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
              {user?.name || 'Seller'} · {user?.facility_name || 'Your Facility'}
            </p>
          </div>
          <div style={{ display: 'flex', gap: '0.625rem' }}>
            <Link href="/proofpath" className="clay-btn clay-btn-secondary">
              <ShieldCheck size={15} />
              Run ProofPath
            </Link>
            <Link href="/materials?action=new" className="clay-btn clay-btn-primary">
              <Plus size={15} />
              Add Material Lot
            </Link>
          </div>
        </div>

        {/* KPIs */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
          <MetricCard
            label="Material Inventory"
            value={lots.length}
            unit="lots"
            subtext={`${qualifiedLots.length} ready for exchange`}
            icon={<Package size={18} />}
          />
          <MetricCard
            label="Active Listings"
            value={activeListings.length}
            subtext="Published on marketplace"
            deltaType="positive"
            icon={<RefreshCw size={18} />}
          />
          <MetricCard
            label="Incoming RFQs"
            value={rfqs.length}
            subtext={`${pendingRfqs.length} awaiting response`}
            icon={<FileText size={18} />}
          />
          <MetricCard
            label="Qualification Rate"
            value={lots.length > 0 ? `${Math.round((qualifiedLots.length / lots.length) * 100)}%` : '—'}
            subtext="Lots passing ProofPath"
            deltaType={qualifiedLots.length > 0 ? 'positive' : 'neutral'}
            icon={<ShieldCheck size={18} />}
          />
        </div>

        {/* Two-col: Inventory + Listings */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '1.5rem' }}>
          {/* Material Inventory */}
          <div className="clay-card" style={{ padding: '1.25rem', backgroundColor: '#ffffff' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingBottom: '0.75rem', borderBottom: '1px solid var(--border-subtle)', marginBottom: '1rem' }}>
              <div>
                <span className="label-compact">Byproduct Inventory</span>
                <h3 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)' }}>Material Lots</h3>
              </div>
              <Link href="/materials" style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--primary-container)', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                Registry <ArrowRight size={13} />
              </Link>
            </div>

            {loadingLots ? (
              <div style={{ display: 'flex', justifyContent: 'center', padding: '1.5rem', color: 'var(--text-muted)' }}>
                <Loader2 size={18} className="animate-spin" />
              </div>
            ) : lotsError ? (
              <div style={{ padding: '0.75rem', borderRadius: '8px', backgroundColor: 'var(--status-error-bg)', color: 'var(--status-error)', fontSize: '0.8125rem', display: 'flex', gap: '0.5rem' }}>
                <AlertCircle size={15} />{lotsError}
              </div>
            ) : lots.length === 0 ? (
              <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                <Package size={28} style={{ margin: '0 auto 0.5rem', opacity: 0.4 }} />
                <p style={{ fontSize: '0.8125rem', marginBottom: '0.75rem' }}>No material lots registered yet.</p>
                <Link href="/materials?action=new" className="clay-btn clay-btn-primary" style={{ display: 'inline-flex' }}>
                  Register First Lot
                </Link>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.625rem' }}>
                {lots.slice(0, 7).map((lot) => (
                  <div key={lot.lot_id} style={{ padding: '0.75rem', borderRadius: '8px', backgroundColor: 'var(--bg-subtle)', border: '1px solid var(--border-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.75rem' }}>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.2rem', flexWrap: 'wrap' }}>
                        <span style={{ fontWeight: 600, fontSize: '0.8125rem', color: 'var(--text-primary)' }}>
                          {lot.material_type}
                        </span>
                        {getLotStatusBadge(lot.status)}
                      </div>
                      <div style={{ fontSize: '0.6875rem', color: 'var(--text-muted)', display: 'flex', gap: '0.5rem' }}>
                        <span className="tnum">{formatNumber(lot.quantity)} {lot.unit}</span>
                        <span>· {formatDate(lot.availability_from)}</span>
                      </div>
                    </div>
                    <Link href={`/proofpath?lot_id=${lot.lot_id}`} className="clay-btn clay-btn-secondary" style={{ fontSize: '0.6875rem', padding: '0.3rem 0.625rem', flexShrink: 0 }}>
                      <ShieldCheck size={12} />
                      Qualify
                    </Link>
                  </div>
                ))}
                {lots.length > 7 && (
                  <Link href="/materials" style={{ textAlign: 'center', fontSize: '0.75rem', color: 'var(--primary-container)', fontWeight: 600, textDecoration: 'none', padding: '0.5rem' }}>
                    +{lots.length - 7} more →
                  </Link>
                )}
              </div>
            )}
          </div>

          {/* My Listings */}
          <div className="clay-card" style={{ padding: '1.25rem', backgroundColor: '#ffffff' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingBottom: '0.75rem', borderBottom: '1px solid var(--border-subtle)', marginBottom: '1rem' }}>
              <div>
                <span className="label-compact">Circular Exchange</span>
                <h3 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)' }}>My Published Listings</h3>
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
                <p style={{ fontSize: '0.8125rem', marginBottom: '0.5rem' }}>No listings published yet.</p>
                <p style={{ fontSize: '0.75rem', marginBottom: '0.875rem' }}>Qualify a material lot first, then publish it to the exchange.</p>
                <Link href="/exchange" className="clay-btn clay-btn-secondary" style={{ display: 'inline-flex' }}>
                  Create Listing
                </Link>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.625rem' }}>
                {listings.map((listing) => (
                  <div key={listing.listing_id} style={{ padding: '0.75rem', borderRadius: '8px', backgroundColor: 'var(--bg-subtle)', border: '1px solid var(--border-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.75rem' }}>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.2rem', flexWrap: 'wrap' }}>
                        <span style={{ fontWeight: 600, fontSize: '0.8125rem', color: 'var(--text-primary)' }}>
                          {listing.material_type || 'Material'}
                        </span>
                        <Badge variant={listing.status === 'active' ? 'success' : 'neutral'} dot>
                          {listing.status || 'active'}
                        </Badge>
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
                      RFQs
                    </Link>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Incoming RFQs from buyers */}
        <div className="clay-card" style={{ padding: '1.25rem', backgroundColor: '#ffffff' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingBottom: '0.75rem', borderBottom: '1px solid var(--border-subtle)', marginBottom: '1rem' }}>
            <div>
              <span className="label-compact">Buyer Interest</span>
              <h3 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)' }}>Incoming RFQs & Offers</h3>
            </div>
            <Link href="/rfqs" style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--primary-container)', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
              Negotiation Workspace <ArrowRight size={13} />
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
              <p style={{ fontSize: '0.8125rem' }}>No incoming RFQs yet. Publish listings to attract buyer interest.</p>
            </div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '0.75rem' }}>
              {rfqs.map((rfq) => {
                const isUrgent = ['submitted', 'under_review'].includes(rfq.status);
                return (
                  <div key={rfq.rfq_id} style={{ padding: '0.875rem 1rem', borderRadius: '8px', backgroundColor: isUrgent ? 'var(--status-warning-bg)' : 'var(--bg-subtle)', border: `1px solid ${isUrgent ? 'rgba(154,103,34,0.25)' : 'var(--border-subtle)'}`, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
                        <span style={{ fontFamily: 'monospace', fontSize: '0.75rem', fontWeight: 600 }}>RFQ-{rfq.rfq_id.slice(0, 8)}</span>
                        <Badge variant={isUrgent ? 'warning' : rfq.status === 'accepted' ? 'success' : 'neutral'} dot>
                          {rfq.status.replace(/_/g, ' ')}
                        </Badge>
                      </div>
                      <div className="tnum" style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                        {formatNumber(rfq.requested_quantity)} MT
                        {rfq.target_price_per_unit && ` · $${rfq.target_price_per_unit}/MT target`}
                      </div>
                    </div>
                    <Link href={`/rfqs?rfq_id=${rfq.rfq_id}`} className="clay-btn clay-btn-primary" style={{ fontSize: '0.6875rem', padding: '0.35rem 0.75rem' }}>
                      Respond
                    </Link>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Quick nav */}
        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
          <Link href="/materials" className="clay-btn clay-btn-secondary">
            <Layers size={15} />
            Material Registry
          </Link>
          <Link href="/proofpath" className="clay-btn clay-btn-secondary">
            <ShieldCheck size={15} />
            ProofPath Qualification
          </Link>
          <Link href="/exchange" className="clay-btn clay-btn-secondary">
            <RefreshCw size={15} />
            Circular Exchange
          </Link>
        </div>
      </div>
    </AppShell>
  );
}
