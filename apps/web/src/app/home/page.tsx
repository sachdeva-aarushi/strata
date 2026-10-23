'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  ArrowRight,
  ShieldCheck,
  Layers,
  RefreshCw,
  Search,
  ChevronRight,
  CircleDot,
  Truck,
  Factory,
  BarChart2,
  Loader2,
} from 'lucide-react';
import { api } from '@/lib/api-client';
import { ExchangeListing } from '@/types';
import { formatNumber } from '@/lib/utils';

export default function HomePage() {
  const [listings, setListings] = useState<ExchangeListing[]>([]);
  const [loadingListings, setLoadingListings] = useState(true);
  const [totalListings, setTotalListings] = useState(0);

  useEffect(() => {
    api.exchange
      .listListings({ page_size: 6, view: 'exchange' })
      .then((res) => {
        setListings(res.data || []);
        setTotalListings(res.pagination?.total || 0);
      })
      .catch(() => {})
      .finally(() => setLoadingListings(false));
  }, []);

  return (
    <div
      style={{
        minHeight: '100vh',
        backgroundColor: 'var(--bg-canvas)',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      {/* ─── Nav ──────────────────────────────────────────────────── */}
      <header
        style={{
          position: 'sticky',
          top: 0,
          zIndex: 40,
          backgroundColor: 'rgba(246,251,244,0.92)',
          backdropFilter: 'blur(10px)',
          borderBottom: '1px solid var(--border-subtle)',
        }}
      >
        <div
          style={{
            maxWidth: '1280px',
            margin: '0 auto',
            padding: '0 1.5rem',
            height: '56px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <Link
            href="/"
            style={{ display: 'flex', alignItems: 'center', gap: '0.625rem', textDecoration: 'none' }}
          >
            <div
              style={{
                width: '28px',
                height: '28px',
                borderRadius: '6px',
                backgroundColor: 'var(--primary)',
                color: '#ffffff',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontWeight: 700,
                fontSize: '0.875rem',
              }}
            >
              S
            </div>
            <span style={{ fontSize: '1rem', fontWeight: 700, letterSpacing: '0.05em', color: 'var(--text-primary)' }}>
              STRATA
            </span>
          </Link>

          <nav style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
            <Link href="/marketplace" style={{ padding: '0.375rem 0.75rem', fontSize: '0.8125rem', fontWeight: 500, color: 'var(--text-secondary)', textDecoration: 'none', borderRadius: '6px' }}>
              Marketplace
            </Link>
            <a href="#how-it-works" style={{ padding: '0.375rem 0.75rem', fontSize: '0.8125rem', fontWeight: 500, color: 'var(--text-secondary)', textDecoration: 'none', borderRadius: '6px' }}>
              How It Works
            </a>
            <Link href="/login" style={{ padding: '0.375rem 0.75rem', fontSize: '0.8125rem', fontWeight: 500, color: 'var(--text-secondary)', textDecoration: 'none', borderRadius: '6px' }}>
              Sign In
            </Link>
            <Link href="/register" className="clay-btn clay-btn-primary" style={{ padding: '0.4rem 0.875rem', fontSize: '0.8125rem' }}>
              Get Started
            </Link>
          </nav>
        </div>
      </header>

      {/* ─── Hero ─────────────────────────────────────────────────── */}
      <section
        style={{
          maxWidth: '1280px',
          margin: '0 auto',
          padding: '4rem 1.5rem 3rem',
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
          gap: '3rem',
          alignItems: 'center',
        }}
      >
        <div>
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.375rem',
              padding: '0.25rem 0.625rem',
              borderRadius: '4px',
              backgroundColor: 'var(--accent-teal-subtle)',
              color: 'var(--accent-teal)',
              fontSize: '0.6875rem',
              fontWeight: 600,
              textTransform: 'uppercase',
              letterSpacing: '0.06em',
              marginBottom: '1.25rem',
            }}
          >
            <CircleDot size={12} />
            Industrial Byproduct Exchange
          </div>

          <h1
            className="font-serif"
            style={{
              fontSize: 'clamp(2rem, 4vw, 2.75rem)',
              fontWeight: 500,
              lineHeight: 1.2,
              letterSpacing: '-0.02em',
              color: 'var(--primary)',
              marginBottom: '1rem',
            }}
          >
            Turn industrial<br />byproducts into<br />verified resources.
          </h1>

          <p
            style={{
              fontSize: '0.9375rem',
              lineHeight: 1.65,
              color: 'var(--text-secondary)',
              maxWidth: '440px',
              marginBottom: '2rem',
            }}
          >
            STRATA connects facilities that generate secondary materials with buyers that need them — with built-in qualification, chain-of-custody traceability, and bilateral deal workflows.
          </p>

          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem' }}>
            <Link href="/marketplace" className="clay-btn clay-btn-primary" style={{ padding: '0.625rem 1.25rem', fontSize: '0.875rem' }}>
              <Search size={16} />
              <span>Find Materials</span>
            </Link>
            <Link href="/register?intent=sell" className="clay-btn clay-btn-secondary" style={{ padding: '0.625rem 1.25rem', fontSize: '0.875rem' }}>
              <Layers size={16} />
              <span>List a Byproduct</span>
              <ArrowRight size={14} />
            </Link>
          </div>
        </div>

        {/* Hero stat grid */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.875rem' }}>
          {[
            { label: 'Material Categories', value: '7', sub: 'Metallics, Polymers, Chemicals...', icon: <Layers size={18} /> },
            { label: 'ProofPath Qualified', value: '100%', sub: 'Deterministic gate-pass engine', icon: <ShieldCheck size={18} /> },
            { label: 'Active Listings', value: totalListings > 0 ? formatNumber(totalListings) : '—', sub: 'Open on circular exchange', icon: <RefreshCw size={18} /> },
            { label: 'Chain of Custody', value: 'Verified', sub: 'SHA-256 state transitions', icon: <BarChart2 size={18} /> },
          ].map((s, i) => (
            <div key={i} className="clay-card" style={{ padding: '1.125rem', backgroundColor: '#ffffff' }}>
              <div style={{ color: 'var(--text-muted)', marginBottom: '0.625rem' }}>{s.icon}</div>
              <div className="tnum" style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--primary)', lineHeight: 1, marginBottom: '0.25rem' }}>{s.value}</div>
              <div className="label-compact" style={{ marginBottom: '0.25rem' }}>{s.label}</div>
              <div style={{ fontSize: '0.6875rem', color: 'var(--text-muted)' }}>{s.sub}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ─── How It Works ─────────────────────────────────────────── */}
      <section id="how-it-works" style={{ borderTop: '1px solid var(--border-subtle)', backgroundColor: '#ffffff' }}>
        <div style={{ maxWidth: '1280px', margin: '0 auto', padding: '3rem 1.5rem' }}>
          <div style={{ marginBottom: '2rem' }}>
            <span className="label-compact" style={{ color: 'var(--accent-teal)' }}>Platform Overview</span>
            <h2 className="font-serif" style={{ fontSize: '1.625rem', fontWeight: 500, color: 'var(--primary)', marginTop: '0.25rem' }}>
              How STRATA works
            </h2>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1.25rem' }}>
            {[
              { step: '01', icon: <Factory size={20} />, title: 'Register material lots', body: 'Generators record byproduct batches with declared attributes, quantities, and provenance labels.' },
              { step: '02', icon: <ShieldCheck size={20} />, title: 'ProofPath qualification', body: "STRATA's deterministic engine verifies each lot against buyer criteria — producing a gate-pass or gap analysis." },
              { step: '03', icon: <RefreshCw size={20} />, title: 'List on Circular Exchange', body: 'Qualified lots appear on the marketplace. Buyers browse, filter by category, and express interest.' },
              { step: '04', icon: <Truck size={20} />, title: 'Bilateral RFQ & deal close', body: 'Buyers submit RFQs, sellers respond with offers. Accepted deals generate verifiable custody transfers.' },
            ].map((s) => (
              <div key={s.step} className="clay-card" style={{ padding: '1.25rem', backgroundColor: 'var(--bg-subtle)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.875rem' }}>
                  <div style={{ width: '36px', height: '36px', borderRadius: '8px', backgroundColor: 'var(--primary-container)', color: '#ffffff', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                    {s.icon}
                  </div>
                  <span className="label-compact" style={{ fontSize: '0.625rem', color: 'var(--text-muted)' }}>Step {s.step}</span>
                </div>
                <h3 style={{ fontSize: '0.9375rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.375rem' }}>{s.title}</h3>
                <p style={{ fontSize: '0.8125rem', lineHeight: 1.55, color: 'var(--text-secondary)' }}>{s.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── Marketplace Preview ──────────────────────────────────── */}
      <section style={{ borderTop: '1px solid var(--border-subtle)' }}>
        <div style={{ maxWidth: '1280px', margin: '0 auto', padding: '3rem 1.5rem' }}>
          <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'baseline', justifyContent: 'space-between', gap: '1rem', marginBottom: '1.5rem' }}>
            <div>
              <span className="label-compact" style={{ color: 'var(--accent-teal)' }}>Live Exchange</span>
              <h2 className="font-serif" style={{ fontSize: '1.625rem', fontWeight: 500, color: 'var(--primary)', marginTop: '0.25rem' }}>
                Materials available now
              </h2>
            </div>
            <Link href="/marketplace" style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', fontSize: '0.8125rem', fontWeight: 600, color: 'var(--primary-container)', textDecoration: 'none' }}>
              Browse all <ChevronRight size={14} />
            </Link>
          </div>

          {loadingListings ? (
            <div style={{ display: 'flex', justifyContent: 'center', padding: '2.5rem', color: 'var(--text-muted)' }}>
              <Loader2 size={20} className="animate-spin" />
            </div>
          ) : listings.length === 0 ? (
            <div className="clay-card" style={{ padding: '2.5rem', textAlign: 'center', color: 'var(--text-muted)', backgroundColor: '#ffffff' }}>
              <RefreshCw size={28} style={{ margin: '0 auto 0.5rem', opacity: 0.4 }} />
              <p style={{ fontSize: '0.875rem' }}>
                No active listings at this time.{' '}
                <Link href="/register?intent=sell" style={{ color: 'var(--primary-container)', fontWeight: 600 }}>
                  List your first byproduct →
                </Link>
              </p>
            </div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '1rem' }}>
              {listings.map((listing) => (
                <div key={listing.listing_id} className="clay-card" style={{ padding: '1.125rem', backgroundColor: '#ffffff', display: 'flex', flexDirection: 'column', gap: '0.625rem' }}>
                  <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '0.5rem' }}>
                    <div>
                      <div style={{ fontWeight: 600, fontSize: '0.875rem', color: 'var(--text-primary)', marginBottom: '0.2rem' }}>
                        {listing.material_type || 'Industrial Material'}
                      </div>
                      <span className="strata-badge strata-badge-teal" style={{ fontSize: '0.625rem' }}>
                        {listing.status || 'active'}
                      </span>
                    </div>
                    {listing.asking_price_per_unit && (
                      <div style={{ textAlign: 'right', flexShrink: 0 }}>
                        <div className="tnum" style={{ fontSize: '1.0625rem', fontWeight: 700, color: 'var(--primary)' }}>
                          ${listing.asking_price_per_unit}
                        </div>
                        <div style={{ fontSize: '0.6875rem', color: 'var(--text-muted)' }}>per {listing.unit}</div>
                      </div>
                    )}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'flex', gap: '0.75rem' }}>
                    <span className="tnum">{formatNumber(listing.quantity)} {listing.unit}</span>
                  </div>
                  <Link href="/marketplace" style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', fontSize: '0.75rem', fontWeight: 600, color: 'var(--primary-container)', textDecoration: 'none', marginTop: '0.25rem' }}>
                    View details <ChevronRight size={12} />
                  </Link>
                </div>
              ))}
            </div>
          )}

          <div style={{ marginTop: '2rem', display: 'flex', gap: '0.75rem', justifyContent: 'center', flexWrap: 'wrap' }}>
            <Link href="/marketplace" className="clay-btn clay-btn-secondary" style={{ padding: '0.625rem 1.25rem', fontSize: '0.875rem' }}>
              <Search size={16} />
              Browse all materials
            </Link>
            <Link href="/register?intent=buy" className="clay-btn clay-btn-primary" style={{ padding: '0.625rem 1.25rem', fontSize: '0.875rem' }}>
              Register to post requirements
              <ArrowRight size={14} />
            </Link>
          </div>
        </div>
      </section>

      {/* ─── Footer ───────────────────────────────────────────────── */}
      <footer style={{ borderTop: '1px solid var(--border-subtle)', backgroundColor: '#ffffff', marginTop: 'auto' }}>
        <div style={{ maxWidth: '1280px', margin: '0 auto', padding: '1.25rem 1.5rem', display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: '0.75rem', fontSize: '0.6875rem', color: 'var(--text-muted)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ fontWeight: 700, letterSpacing: '0.04em', color: 'var(--text-secondary)' }}>STRATA</span>
            <span>· Industrial Circularity Operating System</span>
          </div>
          <div style={{ display: 'flex', gap: '1.25rem' }}>
            <Link href="/marketplace" style={{ color: 'inherit', textDecoration: 'none' }}>Marketplace</Link>
            <Link href="/login" style={{ color: 'inherit', textDecoration: 'none' }}>Sign In</Link>
            <Link href="/register" style={{ color: 'inherit', textDecoration: 'none' }}>Register</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
