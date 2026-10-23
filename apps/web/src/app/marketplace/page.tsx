'use client';

import React, { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import {
  Search,
  Layers,
  RefreshCw,
  Filter,
  ArrowRight,
  ChevronRight,
  X,
  Loader2,
  ShieldCheck,
  AlertCircle,
  Package,
} from 'lucide-react';
import { api } from '@/lib/api-client';
import { ExchangeListing } from '@/types';
import { formatNumber, formatDate } from '@/lib/utils';

const CATEGORIES = [
  { value: '', label: 'All Categories' },
  { value: 'metallics', label: 'Metallics' },
  { value: 'polymers', label: 'Polymers' },
  { value: 'chemicals', label: 'Chemicals' },
  { value: 'biomass', label: 'Biomass' },
  { value: 'minerals', label: 'Minerals' },
  { value: 'packaging', label: 'Packaging' },
  { value: 'textiles', label: 'Textiles' },
];

export default function MarketplacePage() {
  const [listings, setListings] = useState<ExchangeListing[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('');
  const [selectedListing, setSelectedListing] = useState<ExchangeListing | null>(null);

  const load = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await api.exchange.listListings({
        view: 'exchange',
        category: category || undefined,
        page_size: 50,
      });
      setListings(res.data || []);
      setTotal(res.pagination?.total || 0);
    } catch (e: any) {
      setError(e?.message || 'Failed to load marketplace listings.');
    } finally {
      setIsLoading(false);
    }
  }, [category]);

  useEffect(() => {
    load();
  }, [load]);

  const filtered = listings.filter((l) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      (l.material_type || '').toLowerCase().includes(q) ||
      (l.status || '').toLowerCase().includes(q)
    );
  });

  return (
    <div style={{ minHeight: '100vh', backgroundColor: 'var(--bg-canvas)', display: 'flex', flexDirection: 'column' }}>
      {/* Nav */}
      <header style={{ position: 'sticky', top: 0, zIndex: 40, backgroundColor: 'rgba(246,251,244,0.92)', backdropFilter: 'blur(10px)', borderBottom: '1px solid var(--border-subtle)' }}>
        <div style={{ maxWidth: '1280px', margin: '0 auto', padding: '0 1.5rem', height: '56px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Link href="/" style={{ display: 'flex', alignItems: 'center', gap: '0.625rem', textDecoration: 'none' }}>
            <div style={{ width: '28px', height: '28px', borderRadius: '6px', backgroundColor: 'var(--primary)', color: '#ffffff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: '0.875rem' }}>S</div>
            <span style={{ fontSize: '1rem', fontWeight: 700, letterSpacing: '0.05em', color: 'var(--text-primary)' }}>STRATA</span>
          </Link>
          <nav style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
            <Link href="/" style={{ padding: '0.375rem 0.75rem', fontSize: '0.8125rem', fontWeight: 500, color: 'var(--text-secondary)', textDecoration: 'none' }}>Home</Link>
            <Link href="/login" style={{ padding: '0.375rem 0.75rem', fontSize: '0.8125rem', fontWeight: 500, color: 'var(--text-secondary)', textDecoration: 'none' }}>Sign In</Link>
            <Link href="/register" className="clay-btn clay-btn-primary" style={{ padding: '0.4rem 0.875rem', fontSize: '0.8125rem' }}>Register</Link>
          </nav>
        </div>
      </header>

      <div style={{ maxWidth: '1280px', margin: '0 auto', padding: '2rem 1.5rem', flex: 1, width: '100%' }}>
        {/* Page Header */}
        <div style={{ marginBottom: '1.5rem' }}>
          <span className="label-compact" style={{ color: 'var(--accent-teal)' }}>Circular Exchange</span>
          <h1 className="font-serif" style={{ fontSize: '1.875rem', fontWeight: 500, color: 'var(--primary)', marginTop: '0.25rem', letterSpacing: '-0.015em' }}>
            Industrial Materials Marketplace
          </h1>
          <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
            Browse verified secondary material lots available for bilateral negotiation.
            {total > 0 && <span className="tnum" style={{ fontWeight: 600, color: 'var(--text-primary)', marginLeft: '0.375rem' }}>{formatNumber(total)} listings</span>}
          </p>
        </div>

        {/* Filters bar */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem', marginBottom: '1.5rem', alignItems: 'center' }}>
          <div style={{ position: 'relative', flex: '1 1 260px' }}>
            <Search size={15} style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search material type…"
              className="clay-input"
              style={{ paddingLeft: '2.25rem', paddingRight: search ? '2rem' : undefined }}
            />
            {search && (
              <button onClick={() => setSearch('')} style={{ position: 'absolute', right: '0.625rem', top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}>
                <X size={14} />
              </button>
            )}
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Filter size={14} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />
            <select value={category} onChange={(e) => setCategory(e.target.value)} className="clay-select" style={{ width: 'auto', minWidth: '160px' }}>
              {CATEGORIES.map((c) => (
                <option key={c.value} value={c.value}>{c.label}</option>
              ))}
            </select>
          </div>

          <button onClick={load} className="clay-btn clay-btn-secondary" style={{ flexShrink: 0 }}>
            <RefreshCw size={14} />
            Refresh
          </button>
        </div>

        {/* Error */}
        {error && (
          <div style={{ padding: '0.75rem 1rem', borderRadius: '8px', backgroundColor: 'var(--status-error-bg)', border: '1px solid rgba(166,58,53,0.25)', color: 'var(--status-error)', fontSize: '0.8125rem', display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}

        <div style={{ display: 'grid', gridTemplateColumns: selectedListing ? '1fr 380px' : '1fr', gap: '1.5rem', alignItems: 'start' }}>
          {/* Listings grid */}
          <div>
            {isLoading ? (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '4rem', color: 'var(--text-muted)', gap: '0.625rem' }}>
                <Loader2 size={20} className="animate-spin" />
                <span style={{ fontSize: '0.875rem' }}>Loading listings…</span>
              </div>
            ) : filtered.length === 0 ? (
              <div className="clay-card" style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)', backgroundColor: '#ffffff' }}>
                <Package size={32} style={{ margin: '0 auto 0.75rem', opacity: 0.4 }} />
                <p style={{ fontSize: '0.875rem', marginBottom: '0.5rem' }}>No listings match your filters.</p>
                <p style={{ fontSize: '0.8125rem' }}>
                  <Link href="/register?intent=sell" style={{ color: 'var(--primary-container)', fontWeight: 600 }}>
                    List your first byproduct →
                  </Link>
                </p>
              </div>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: '1rem' }}>
                {filtered.map((listing) => (
                  <div
                    key={listing.listing_id}
                    onClick={() => setSelectedListing(selectedListing?.listing_id === listing.listing_id ? null : listing)}
                    className={`clay-card-interactive ${selectedListing?.listing_id === listing.listing_id ? 'clay-card-selected' : ''}`}
                    style={{ padding: '1.125rem', backgroundColor: '#ffffff' }}
                  >
                    <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '0.5rem', marginBottom: '0.75rem' }}>
                      <div>
                        <div style={{ fontWeight: 600, fontSize: '0.875rem', color: 'var(--text-primary)', marginBottom: '0.25rem' }}>
                          {listing.material_type || 'Industrial Material'}
                        </div>
                        <span className={`strata-badge ${listing.status === 'active' ? 'strata-badge-success' : 'strata-badge-neutral'}`}>
                          {listing.status || 'active'}
                        </span>
                      </div>
                      {listing.asking_price_per_unit != null && (
                        <div style={{ textAlign: 'right', flexShrink: 0 }}>
                          <div className="tnum" style={{ fontSize: '1.125rem', fontWeight: 700, color: 'var(--primary)' }}>
                            ${listing.asking_price_per_unit}
                          </div>
                          <div style={{ fontSize: '0.6875rem', color: 'var(--text-muted)' }}>/{listing.unit}</div>
                        </div>
                      )}
                    </div>

                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem 1rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      <span className="tnum"><strong style={{ color: 'var(--text-primary)' }}>{formatNumber(listing.quantity)}</strong> {listing.unit}</span>
                      {listing.currency && <span>{listing.currency}</span>}
                    </div>

                    <div style={{ marginTop: '0.875rem', paddingTop: '0.75rem', borderTop: '1px solid var(--border-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <span style={{ fontSize: '0.6875rem', color: 'var(--text-muted)' }}>
                        Available {formatDate(listing.created_at)}
                      </span>
                      <ChevronRight size={14} color="var(--primary-container)" />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Detail panel */}
          {selectedListing && (
            <div className="clay-card" style={{ padding: '1.5rem', backgroundColor: '#ffffff', position: 'sticky', top: '72px' }}>
              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '1.25rem' }}>
                <div>
                  <span className="label-compact" style={{ color: 'var(--accent-teal)' }}>Listing Details</span>
                  <h2 style={{ fontSize: '1.125rem', fontWeight: 700, color: 'var(--text-primary)', marginTop: '0.25rem' }}>
                    {selectedListing.material_type || 'Industrial Material'}
                  </h2>
                </div>
                <button onClick={() => setSelectedListing(null)} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}>
                  <X size={18} />
                </button>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.875rem' }}>
                {[
                  { label: 'Status', value: selectedListing.status },
                  { label: 'Quantity', value: `${formatNumber(selectedListing.quantity)} ${selectedListing.unit}` },
                  { label: 'Asking Price', value: selectedListing.asking_price_per_unit != null ? `$${selectedListing.asking_price_per_unit} / ${selectedListing.unit}` : 'Not specified' },
                  { label: 'Currency', value: selectedListing.currency || 'USD' },
                  { label: 'Listed', value: formatDate(selectedListing.created_at) },
                  { label: 'Listing ID', value: selectedListing.listing_id.slice(0, 16) + '…', mono: true },
                ].map((row) => (
                  <div key={row.label} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '0.5rem' }}>
                    <span className="label-compact" style={{ flexShrink: 0 }}>{row.label}</span>
                    <span style={{ fontSize: '0.8125rem', color: 'var(--text-primary)', fontFamily: row.mono ? 'monospace' : undefined, textAlign: 'right', wordBreak: 'break-all' }}>
                      {row.value}
                    </span>
                  </div>
                ))}
              </div>

              <div style={{ marginTop: '1.25rem', paddingTop: '1rem', borderTop: '1px solid var(--border-subtle)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem', marginBottom: '0.75rem', color: 'var(--text-muted)', fontSize: '0.75rem' }}>
                  <ShieldCheck size={14} />
                  <span>Sign in to submit an RFQ or post a buyer requirement</span>
                </div>
                <div style={{ display: 'flex', gap: '0.625rem', flexDirection: 'column' }}>
                  <Link href="/register?intent=buy" className="clay-btn clay-btn-primary" style={{ width: '100%', justifyContent: 'center' }}>
                    Register to Request Quote
                    <ArrowRight size={14} />
                  </Link>
                  <Link href="/login" className="clay-btn clay-btn-secondary" style={{ width: '100%', justifyContent: 'center' }}>
                    Sign In
                  </Link>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Footer */}
      <footer style={{ borderTop: '1px solid var(--border-subtle)', backgroundColor: '#ffffff', marginTop: 'auto' }}>
        <div style={{ maxWidth: '1280px', margin: '0 auto', padding: '1rem 1.5rem', display: 'flex', justifyContent: 'space-between', fontSize: '0.6875rem', color: 'var(--text-muted)', flexWrap: 'wrap', gap: '0.5rem' }}>
          <span><strong>STRATA</strong> · Industrial Circularity Operating System</span>
          <Link href="/" style={{ color: 'inherit', textDecoration: 'none' }}>← Back to Home</Link>
        </div>
      </footer>
    </div>
  );
}
