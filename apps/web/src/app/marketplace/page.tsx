'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import {
  Search,
  RefreshCw,
  Filter,
  ArrowRight,
  ChevronRight,
  X,
  ShieldCheck,
  AlertCircle,
  Package,
} from 'lucide-react';
import { useListings } from '@/hooks/useListings';
import { MarketplaceListing } from '@/lib/api/client';
import { ApiErrorBoundary } from '@/components/ApiErrorBoundary';

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

function formatQuantity(val: number | string | undefined | null): string {
  if (val === undefined || val === null || val === '') return '0';
  const num = typeof val === 'number' ? val : parseFloat(val);
  if (isNaN(num)) return '0';
  return new Intl.NumberFormat('en-IN').format(num);
}

function formatPrice(val: number | string | undefined | null, currency: string = 'INR'): string {
  if (val === undefined || val === null || val === '') return 'Price upon request';
  const num = typeof val === 'number' ? val : parseFloat(val);
  if (isNaN(num)) return 'Price upon request';
  const sym = currency === 'USD' ? '$' : '₹';
  return `${sym}${new Intl.NumberFormat('en-IN').format(num)}`;
}

export default function MarketplacePage() {
  return (
    <ApiErrorBoundary>
      <MarketplaceContent />
    </ApiErrorBoundary>
  );
}

function MarketplaceContent() {
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('');
  const [selectedListing, setSelectedListing] = useState<MarketplaceListing | null>(null);

  const { data: listings, isLoading, error, refetch } = useListings({
    view: 'all',
    category: category || undefined,
  });

  const filtered = (listings || []).filter((l) => {
    if (!search) return true;
    const q = search.toLowerCase();
    const mat = (l.material_type || l.lot?.material_type || '').toLowerCase();
    const stat = (l.status || '').toLowerCase();
    return mat.includes(q) || stat.includes(q);
  });

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#F8F9FA', display: 'flex', flexDirection: 'column' }}>
      {/* Nav */}
      <header style={{ position: 'sticky', top: 0, zIndex: 40, backgroundColor: 'rgba(255,255,255,0.95)', backdropFilter: 'blur(8px)', borderBottom: '1px solid #E5E7EB' }}>
        <div style={{ maxWidth: '1280px', margin: '0 auto', padding: '0 1.5rem', height: '56px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Link href="/" style={{ display: 'flex', alignItems: 'center', gap: '0.625rem', textDecoration: 'none' }}>
            <div style={{ width: '28px', height: '28px', borderRadius: '6px', backgroundColor: '#0F4C81', color: '#ffffff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: '0.875rem' }}>S</div>
            <span style={{ fontSize: '1rem', fontWeight: 700, letterSpacing: '0.05em', color: '#1A1A1A' }}>STRATA</span>
          </Link>
          <nav style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Link href="/" style={{ padding: '0.375rem 0.75rem', fontSize: '0.8125rem', fontWeight: 500, color: '#4B5563', textDecoration: 'none' }}>Home</Link>
            <Link href="/municipal" style={{ padding: '0.375rem 0.75rem', fontSize: '0.8125rem', fontWeight: 500, color: '#4B5563', textDecoration: 'none' }}>Municipal</Link>
            <Link href="/rfqs" style={{ padding: '0.375rem 0.75rem', fontSize: '0.8125rem', fontWeight: 500, color: '#4B5563', textDecoration: 'none' }}>RFQs</Link>
            <Link href="/login" style={{ padding: '0.375rem 0.75rem', fontSize: '0.8125rem', fontWeight: 500, color: '#4B5563', textDecoration: 'none' }}>Sign In</Link>
            <Link href="/register" style={{ backgroundColor: '#0F4C81', color: '#FFFFFF', padding: '0.4rem 0.875rem', borderRadius: '6px', fontSize: '0.8125rem', fontWeight: 500, textDecoration: 'none' }}>Register</Link>
          </nav>
        </div>
      </header>

      <div style={{ maxWidth: '1280px', margin: '0 auto', padding: '2rem 1.5rem', flex: 1, width: '100%' }}>
        {/* Page Header */}
        <div style={{ marginBottom: '1.5rem' }}>
          <span style={{ fontSize: '0.75rem', fontWeight: 600, color: '#0F4C81', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Circular Exchange</span>
          <h1 style={{ fontSize: '1.875rem', fontWeight: 600, color: '#1A1A1A', marginTop: '0.25rem', letterSpacing: '-0.015em' }}>
            Industrial Materials Marketplace
          </h1>
          <p style={{ fontSize: '0.875rem', color: '#4B5563', marginTop: '0.25rem' }}>
            Browse verified secondary material lots available for bilateral industrial negotiation.
            {filtered.length > 0 && <span style={{ fontWeight: 600, color: '#1A1A1A', marginLeft: '0.375rem' }}>({filtered.length} active listings)</span>}
          </p>
        </div>

        {/* Filters bar */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem', marginBottom: '1.5rem', alignItems: 'center' }}>
          <div style={{ position: 'relative', flex: '1 1 260px' }}>
            <Search size={15} style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', color: '#9CA3AF' }} />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search material type or cluster..."
              style={{
                width: '100%',
                padding: '0.5rem 2rem 0.5rem 2.25rem',
                borderRadius: '6px',
                border: '1px solid #D1D5DB',
                fontSize: '0.875rem',
                backgroundColor: '#FFFFFF',
              }}
            />
            {search && (
              <button
                onClick={() => setSearch('')}
                style={{ position: 'absolute', right: '0.625rem', top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', color: '#9CA3AF', cursor: 'pointer' }}
              >
                <X size={14} />
              </button>
            )}
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Filter size={14} style={{ color: '#6B7280', flexShrink: 0 }} />
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              style={{
                padding: '0.5rem 1rem',
                borderRadius: '6px',
                border: '1px solid #D1D5DB',
                fontSize: '0.875rem',
                backgroundColor: '#FFFFFF',
                minWidth: '160px',
              }}
            >
              {CATEGORIES.map((c) => (
                <option key={c.value} value={c.value}>{c.label}</option>
              ))}
            </select>
          </div>

          <button
            onClick={() => refetch()}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.375rem',
              backgroundColor: '#FFFFFF',
              color: '#374151',
              border: '1px solid #D1D5DB',
              borderRadius: '6px',
              padding: '0.5rem 0.875rem',
              fontSize: '0.875rem',
              cursor: 'pointer',
              flexShrink: 0,
            }}
          >
            <RefreshCw size={14} />
            Refresh
          </button>
        </div>

        {/* Error Notification */}
        {error && (
          <div style={{ padding: '0.75rem 1rem', borderRadius: '8px', backgroundColor: '#FEF2F2', border: '1px solid #FCA5A5', color: '#B91C1C', fontSize: '0.8125rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.5rem', marginBottom: '1.25rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <AlertCircle size={16} />
              <span>{error.message || 'Failed to communicate with marketplace API.'}</span>
            </div>
            <button
              onClick={() => refetch()}
              style={{ backgroundColor: '#B91C1C', color: '#FFFFFF', border: 'none', borderRadius: '4px', padding: '0.25rem 0.625rem', fontSize: '0.75rem', cursor: 'pointer' }}
            >
              Retry
            </button>
          </div>
        )}

        <div style={{ display: 'grid', gridTemplateColumns: selectedListing ? '1fr 380px' : '1fr', gap: '1.5rem', alignItems: 'start' }}>
          {/* Listings grid */}
          <div>
            {isLoading ? (
              /* Content-shaped CSS Skeleton */
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '1rem' }}>
                {[1, 2, 3, 4, 5, 6].map((i) => (
                  <div
                    key={i}
                    style={{
                      height: '180px',
                      backgroundColor: '#FFFFFF',
                      borderRadius: '8px',
                      border: '1px solid #E5E7EB',
                      padding: '1.125rem',
                      display: 'flex',
                      flexDirection: 'column',
                      justifyContent: 'space-between',
                      boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
                    }}
                  >
                    <div>
                      <div style={{ width: '60%', height: '18px', backgroundColor: '#E5E7EB', borderRadius: '4px', marginBottom: '0.75rem', animation: 'pulse 1.5s infinite ease-in-out' }} />
                      <div style={{ width: '35%', height: '14px', backgroundColor: '#F3F4F6', borderRadius: '4px', animation: 'pulse 1.5s infinite ease-in-out' }} />
                    </div>
                    <div>
                      <div style={{ width: '45%', height: '22px', backgroundColor: '#E5E7EB', borderRadius: '4px', marginBottom: '0.5rem', animation: 'pulse 1.5s infinite ease-in-out' }} />
                      <div style={{ width: '80%', height: '12px', backgroundColor: '#F3F4F6', borderRadius: '4px', animation: 'pulse 1.5s infinite ease-in-out' }} />
                    </div>
                  </div>
                ))}
              </div>
            ) : filtered.length === 0 ? (
              <div style={{ padding: '3.5rem 2rem', textAlign: 'center', color: '#6B7280', backgroundColor: '#FFFFFF', borderRadius: '8px', border: '1px solid #E5E7EB' }}>
                <Package size={36} style={{ margin: '0 auto 0.75rem', opacity: 0.4 }} />
                <h3 style={{ fontSize: '1rem', fontWeight: 600, color: '#1A1A1A', marginBottom: '0.25rem' }}>No Listings Found</h3>
                <p style={{ fontSize: '0.875rem', marginBottom: '1rem' }}>No industrial material lots match the selected filters or search terms.</p>
                <button
                  onClick={() => { setSearch(''); setCategory(''); refetch(); }}
                  style={{ backgroundColor: '#0F4C81', color: '#FFFFFF', border: 'none', borderRadius: '6px', padding: '0.5rem 1rem', fontSize: '0.875rem', cursor: 'pointer' }}
                >
                  Reset Filters
                </button>
              </div>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '1rem' }}>
                {filtered.map((listing) => {
                  const isDemoData =
                    listing.provenance_label === 'synthetic_demo' ||
                    listing.lot?.provenance_label === 'synthetic_demo' ||
                    (listing as any).lot_id?.includes('lot-') ||
                    listing.listing_id.startsWith('demo-');

                  const isSelected = selectedListing?.listing_id === listing.listing_id;
                  const displayMaterial = listing.material_type || listing.lot?.material_type || 'Industrial Material';
                  const displayUnit = listing.unit || listing.lot?.unit || 'MT';
                  const quantityVal = listing.quantity ?? listing.lot?.available_quantity ?? 0;

                  return (
                    <div
                      key={listing.listing_id}
                      onClick={() => setSelectedListing(isSelected ? null : listing)}
                      style={{
                        padding: '1.25rem',
                        backgroundColor: '#FFFFFF',
                        borderRadius: '8px',
                        border: isSelected ? '2px solid #0F4C81' : '1px solid #E5E7EB',
                        cursor: 'pointer',
                        transition: 'all 0.15s ease',
                        boxShadow: isSelected ? '0 4px 6px -1px rgba(15, 76, 129, 0.1)' : '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
                        position: 'relative',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '0.5rem', marginBottom: '0.75rem' }}>
                        <div>
                          <div style={{ fontWeight: 600, fontSize: '0.9375rem', color: '#1A1A1A', marginBottom: '0.375rem' }}>
                            {displayMaterial}
                          </div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                            <span
                              style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                padding: '0.125rem 0.5rem',
                                borderRadius: '9999px',
                                fontSize: '0.75rem',
                                fontWeight: 500,
                                backgroundColor: listing.status === 'active' ? '#ECFDF5' : '#F3F4F6',
                                color: listing.status === 'active' ? '#065F46' : '#4B5563',
                                border: listing.status === 'active' ? '1px solid #A7F3D0' : '1px solid #E5E7EB',
                              }}
                            >
                              {listing.status || 'active'}
                            </span>

                            {/* Required Non-Dismissible Amber DEMO DATA Badge */}
                            {isDemoData && (
                              <span
                                style={{
                                  backgroundColor: '#FEF3C7',
                                  color: '#92400E',
                                  fontSize: '10px',
                                  textTransform: 'uppercase',
                                  borderRadius: '4px',
                                  padding: '4px',
                                  fontWeight: 700,
                                  letterSpacing: '0.05em',
                                  display: 'inline-block',
                                }}
                              >
                                DEMO DATA
                              </span>
                            )}
                          </div>
                        </div>

                        <div style={{ textAlign: 'right', flexShrink: 0 }}>
                          <div style={{ fontSize: '1.125rem', fontWeight: 700, color: '#0F4C81' }}>
                            {formatPrice(listing.asking_price_per_unit, listing.currency)}
                          </div>
                          <div style={{ fontSize: '0.6875rem', color: '#6B7280' }}>per {displayUnit}</div>
                        </div>
                      </div>

                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem 1rem', fontSize: '0.8125rem', color: '#4B5563', marginBottom: '0.75rem' }}>
                        <span>
                          Available: <strong style={{ color: '#1A1A1A' }}>{formatQuantity(quantityVal)}</strong> {displayUnit}
                        </span>
                        {listing.facility_name && (
                          <span style={{ color: '#6B7280' }}>📍 {listing.facility_name}</span>
                        )}
                      </div>

                      <div style={{ paddingTop: '0.75rem', borderTop: '1px solid #F3F4F6', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <span style={{ fontSize: '0.75rem', color: '#9CA3AF' }}>
                          Lot ID: {(listing.lot_id || listing.lot?.lot_id || 'N/A').slice(0, 8)}…
                        </span>
                        <ChevronRight size={16} color="#0F4C81" />
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Detail panel */}
          {selectedListing && (
            <div
              style={{
                backgroundColor: '#FFFFFF',
                borderRadius: '8px',
                border: '1px solid #E5E7EB',
                padding: '1.5rem',
                position: 'sticky',
                top: '72px',
                boxShadow: '0 4px 6px -1px rgba(0,0,0,0.05)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '1.25rem' }}>
                <div>
                  <span style={{ fontSize: '0.75rem', fontWeight: 600, color: '#0F4C81', textTransform: 'uppercase' }}>Listing Details</span>
                  <h2 style={{ fontSize: '1.125rem', fontWeight: 700, color: '#1A1A1A', marginTop: '0.25rem' }}>
                    {selectedListing.material_type || selectedListing.lot?.material_type || 'Industrial Material'}
                  </h2>
                </div>
                <button
                  onClick={() => setSelectedListing(null)}
                  style={{ background: 'none', border: 'none', color: '#6B7280', cursor: 'pointer', padding: '0.25rem' }}
                >
                  <X size={18} />
                </button>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', fontSize: '0.875rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #F3F4F6', paddingBottom: '0.5rem' }}>
                  <span style={{ color: '#6B7280' }}>Status</span>
                  <span style={{ fontWeight: 600, color: '#065F46' }}>{selectedListing.status}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #F3F4F6', paddingBottom: '0.5rem' }}>
                  <span style={{ color: '#6B7280' }}>Available Quantity</span>
                  <span style={{ fontWeight: 600, color: '#1A1A1A' }}>
                    {formatQuantity(selectedListing.quantity ?? selectedListing.lot?.available_quantity)} {selectedListing.unit || selectedListing.lot?.unit}
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #F3F4F6', paddingBottom: '0.5rem' }}>
                  <span style={{ color: '#6B7280' }}>Asking Price</span>
                  <span style={{ fontWeight: 700, color: '#0F4C81' }}>
                    {formatPrice(selectedListing.asking_price_per_unit, selectedListing.currency)} / {selectedListing.unit || selectedListing.lot?.unit}
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #F3F4F6', paddingBottom: '0.5rem' }}>
                  <span style={{ color: '#6B7280' }}>Listing ID</span>
                  <span style={{ fontFamily: 'monospace', fontSize: '0.75rem', color: '#374151' }}>{selectedListing.listing_id}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #F3F4F6', paddingBottom: '0.5rem' }}>
                  <span style={{ color: '#6B7280' }}>Lot ID</span>
                  <span style={{ fontFamily: 'monospace', fontSize: '0.75rem', color: '#374151' }}>{selectedListing.lot_id}</span>
                </div>
                {selectedListing.facility_name && (
                  <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #F3F4F6', paddingBottom: '0.5rem' }}>
                    <span style={{ color: '#6B7280' }}>Facility</span>
                    <span style={{ color: '#1A1A1A' }}>{selectedListing.facility_name}</span>
                  </div>
                )}
                {selectedListing.cluster_name && (
                  <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #F3F4F6', paddingBottom: '0.5rem' }}>
                    <span style={{ color: '#6B7280' }}>Industrial Cluster</span>
                    <span style={{ color: '#1A1A1A' }}>{selectedListing.cluster_name}</span>
                  </div>
                )}
              </div>

              <div style={{ marginTop: '1.25rem', paddingTop: '1rem', borderTop: '1px solid #E5E7EB' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem', marginBottom: '0.75rem', color: '#6B7280', fontSize: '0.75rem' }}>
                  <ShieldCheck size={14} color="#0F4C81" />
                  <span>Verified physical inspection and mass balance certified</span>
                </div>
                <div style={{ display: 'flex', gap: '0.625rem', flexDirection: 'column' }}>
                  <Link
                    href={`/rfqs?listing_id=${selectedListing.listing_id}`}
                    style={{
                      backgroundColor: '#0F4C81',
                      color: '#FFFFFF',
                      borderRadius: '6px',
                      padding: '0.625rem 1rem',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '0.5rem',
                      textDecoration: 'none',
                      fontSize: '0.875rem',
                      fontWeight: 600,
                    }}
                  >
                    Initiate RFQ for this Lot
                    <ArrowRight size={14} />
                  </Link>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Footer */}
      <footer style={{ borderTop: '1px solid #E5E7EB', backgroundColor: '#FFFFFF', marginTop: 'auto' }}>
        <div style={{ maxWidth: '1280px', margin: '0 auto', padding: '1rem 1.5rem', display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: '#6B7280', flexWrap: 'wrap', gap: '0.5rem' }}>
          <span><strong>STRATA</strong> · Industrial Circularity Operating System</span>
          <Link href="/" style={{ color: 'inherit', textDecoration: 'none' }}>← Back to Home</Link>
        </div>
      </footer>
    </div>
  );
}
