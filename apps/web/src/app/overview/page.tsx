'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  Layers,
  ShieldCheck,
  RefreshCw,
  Plus,
  ArrowRight,
  TrendingUp,
  Activity,
  AlertCircle,
  ExternalLink,
  CheckCircle2,
  Cpu,
  FileText,
} from 'lucide-react';
import { AppShell } from '@/components/AppShell';
import { MetricCard } from '@/components/MetricCard';
import { Badge } from '@/components/Badge';
import { api } from '@/lib/api-client';
import { useAuth } from '@/lib/auth';
import { MaterialLot, ExchangeListing, RFQ } from '@/types';
import { formatDate, formatNumber } from '@/lib/utils';

export default function OverviewPage() {
  const { user } = useAuth();
  const [lots, setLots] = useState<MaterialLot[]>([]);
  const [listings, setListings] = useState<ExchangeListing[]>([]);
  const [rfqs, setRfqs] = useState<RFQ[]>([]);
  const [totalLotsCount, setTotalLotsCount] = useState<number>(0);
  const [totalListingsCount, setTotalListingsCount] = useState<number>(0);
  const [totalRfqsCount, setTotalRfqsCount] = useState<number>(0);
  const [qualifyingCount, setQualifyingCount] = useState<number>(0);
  const [availableCount, setAvailableCount] = useState<number>(0);
  const [apiHealth, setApiHealth] = useState<'healthy' | 'checking' | 'unreachable'>('checking');
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      setIsLoading(true);

      // Check API Health
      try {
        const healthRes = await api.health.check();
        if (healthRes.data?.status === 'ok') {
          setApiHealth('healthy');
        } else {
          setApiHealth('unreachable');
        }
      } catch {
        setApiHealth('unreachable');
      }

      // Fetch lots
      try {
        const lotsRes = await api.materials.listLots({ page_size: 50 });
        const lotsList = lotsRes.data || [];
        setLots(lotsList.slice(0, 5));
        setTotalLotsCount(lotsRes.pagination?.total || lotsList.length);
        const qualifying = lotsList.filter((l) => l.status === 'under_qualification').length;
        const avail = lotsList.filter((l) => l.status === 'available' || l.status === 'listed').length;
        setQualifyingCount(qualifying);
        setAvailableCount(avail);
      } catch (e) {
        console.warn('Failed to load material lots from backend:', e);
      }

      // Fetch listings
      try {
        const listingsRes = await api.exchange.listListings({ page_size: 5 });
        setListings(listingsRes.data || []);
        setTotalListingsCount(listingsRes.pagination?.total || 0);
      } catch (e) {
        console.warn('Failed to load exchange listings from backend:', e);
      }

      // Fetch RFQs
      try {
        const rfqsRes = await api.exchange.listRFQs({ page_size: 5 });
        setRfqs(rfqsRes.data || []);
        setTotalRfqsCount(rfqsRes.pagination?.total || 0);
      } catch (e) {
        console.warn('Failed to load RFQs from backend:', e);
      }

      setIsLoading(false);
    }

    loadData();
  }, []);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'available':
        return <Badge variant="success" dot>Available</Badge>;
      case 'under_qualification':
        return <Badge variant="warning" dot>Qualifying</Badge>;
      case 'listed':
        return <Badge variant="teal" dot>Listed</Badge>;
      case 'matched':
        return <Badge variant="teal" dot>Matched</Badge>;
      case 'submitted':
        return <Badge variant="warning" dot>Submitted</Badge>;
      case 'approved':
        return <Badge variant="success" dot>Approved</Badge>;
      case 'accepted':
        return <Badge variant="teal" dot>Accepted</Badge>;
      default:
        return <Badge variant="neutral">{status.replace('_', ' ')}</Badge>;
    }
  };

  return (
    <AppShell>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
        {/* Top Operational Status Header */}
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
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                marginBottom: '0.25rem',
              }}
            >
              <span className="label-compact" style={{ color: 'var(--accent-teal)' }}>
                Continuous Mass-Balance Telemetry
              </span>
              <span style={{ color: 'var(--text-muted)' }}>·</span>
              <span
                style={{
                  fontSize: '0.6875rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.25rem',
                  color:
                    apiHealth === 'healthy'
                      ? 'var(--status-success)'
                      : apiHealth === 'checking'
                      ? 'var(--status-warning)'
                      : 'var(--status-error)',
                }}
              >
                <span
                  style={{
                    width: '6px',
                    height: '6px',
                    borderRadius: '50%',
                    backgroundColor:
                      apiHealth === 'healthy'
                        ? 'var(--status-success)'
                        : apiHealth === 'checking'
                        ? 'var(--status-warning)'
                        : 'var(--status-error)',
                  }}
                />
                Backend API {apiHealth === 'healthy' ? 'Connected' : apiHealth}
              </span>
            </div>

            <h1
              className="font-serif"
              style={{
                fontSize: '1.75rem',
                fontWeight: 500,
                color: 'var(--primary)',
                letterSpacing: '-0.015em',
                lineHeight: 1.2,
              }}
            >
              Circularity Intelligence Overview
            </h1>
            <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
              Facility: <strong>{user?.facility_name || 'Central Rail Smelter & Foundry #4'}</strong> · 
              Active Role: <span style={{ textTransform: 'capitalize' }}>{user?.role?.replace('_', ' ') || 'Facility Operator'}</span>
            </p>
          </div>

          {/* Quick action buttons */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
            <Link href="/materials?action=new" className="clay-btn clay-btn-primary">
              <Plus size={16} />
              <span>Register Lot</span>
            </Link>
            <Link href="/proofpath" className="clay-btn clay-btn-secondary">
              <ShieldCheck size={16} />
              <span>Run ProofPath</span>
            </Link>
          </div>
        </div>

        {/* 4 Core KPIs: Lots, Qualification Status, Listings, Pending RFQs */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
            gap: '1rem',
          }}
        >
          <MetricCard
            label="Material Lots Registered"
            value={formatNumber(totalLotsCount)}
            unit="lots"
            subtext={`${availableCount} ready for circular use`}
            delta="+12% this month"
            deltaType="positive"
            icon={<Layers size={18} />}
          />

          <MetricCard
            label="ProofPath Qualification"
            value={formatNumber(availableCount)}
            unit="qualified"
            subtext={`${qualifyingCount} under evaluation`}
            delta="Zero hard overrides"
            deltaType="positive"
            icon={<ShieldCheck size={18} />}
          />

          <MetricCard
            label="Active Exchange Listings"
            value={formatNumber(totalListingsCount)}
            unit="active"
            subtext="Available on circular marketplace"
            delta="Live matching"
            deltaType="positive"
            icon={<RefreshCw size={18} />}
          />

          <MetricCard
            label="Pending RFQs & Negotiations"
            value={formatNumber(totalRfqsCount)}
            unit="active"
            subtext="Bilateral quotes under review"
            delta="Human approval gate"
            deltaType="neutral"
            icon={<FileText size={18} />}
          />
        </div>

        {/* Main 2-column operational section */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))',
            gap: '1.5rem',
          }}
        >
          {/* Left panel: Registered Material Lots Feed */}
          <div
            className="clay-card"
            style={{
              padding: '1.25rem',
              display: 'flex',
              flexDirection: 'column',
              backgroundColor: '#ffffff',
            }}
          >
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                paddingBottom: '0.75rem',
                borderBottom: '1px solid var(--border-subtle)',
                marginBottom: '1rem',
              }}
            >
              <div>
                <span className="label-compact">Feedstock Telemetry</span>
                <h3
                  style={{
                    fontSize: '1rem',
                    fontWeight: 600,
                    color: 'var(--text-primary)',
                  }}
                >
                  Recent Registered Material Lots
                </h3>
              </div>
              <Link
                href="/materials"
                style={{
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  color: 'var(--primary-container)',
                  textDecoration: 'none',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.25rem',
                }}
              >
                <span>View All</span>
                <ArrowRight size={14} />
              </Link>
            </div>

            {lots.length === 0 ? (
              <div
                style={{
                  padding: '2.5rem 1rem',
                  textAlign: 'center',
                  color: 'var(--text-muted)',
                }}
              >
                <Layers size={28} style={{ margin: '0 auto 0.5rem auto', opacity: 0.5 }} />
                <p style={{ fontSize: '0.8125rem' }}>No material lots registered in this facility yet.</p>
                <Link
                  href="/materials?action=new"
                  className="clay-btn clay-btn-secondary"
                  style={{ marginTop: '0.75rem', display: 'inline-flex' }}
                >
                  Register First Lot
                </Link>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.625rem' }}>
                {lots.map((lot) => (
                  <div
                    key={lot.lot_id}
                    style={{
                      padding: '0.75rem',
                      borderRadius: '8px',
                      backgroundColor: 'var(--bg-subtle)',
                      border: '1px solid var(--border-subtle)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      gap: '0.75rem',
                    }}
                  >
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '0.5rem',
                          marginBottom: '0.25rem',
                        }}
                      >
                        <span
                          style={{
                            fontWeight: 600,
                            fontSize: '0.8125rem',
                            color: 'var(--text-primary)',
                            whiteSpace: 'nowrap',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                          }}
                        >
                          {lot.material_type}
                        </span>
                        {getStatusBadge(lot.status)}
                      </div>
                      <div
                        style={{
                          fontSize: '0.6875rem',
                          color: 'var(--text-muted)',
                          display: 'flex',
                          gap: '0.75rem',
                        }}
                      >
                        <span className="tnum">
                          Qty: <strong>{formatNumber(lot.quantity)}</strong> {lot.unit}
                        </span>
                        <span>Avail: {formatDate(lot.availability_from)}</span>
                      </div>
                    </div>

                    <Link
                      href={`/proofpath?lot_id=${lot.lot_id}`}
                      className="clay-btn-ghost"
                      style={{
                        padding: '0.375rem 0.625rem',
                        fontSize: '0.6875rem',
                        borderRadius: '6px',
                        textDecoration: 'none',
                        color: 'var(--primary-container)',
                        fontWeight: 600,
                        backgroundColor: '#ffffff',
                        border: '1px solid var(--border-subtle)',
                      }}
                      title="Run qualification on lot"
                    >
                      Qualify
                    </Link>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Right panel: Circular Exchange Marketplace Snapshot */}
          <div
            className="clay-card"
            style={{
              padding: '1.25rem',
              display: 'flex',
              flexDirection: 'column',
              backgroundColor: '#ffffff',
            }}
          >
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                paddingBottom: '0.75rem',
                borderBottom: '1px solid var(--border-subtle)',
                marginBottom: '1rem',
              }}
            >
              <div>
                <span className="label-compact">Bilateral Trading</span>
                <h3
                  style={{
                    fontSize: '1rem',
                    fontWeight: 600,
                    color: 'var(--text-primary)',
                  }}
                >
                  Circular Exchange Active Streams
                </h3>
              </div>
              <Link
                href="/exchange"
                style={{
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  color: 'var(--primary-container)',
                  textDecoration: 'none',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.25rem',
                }}
              >
                <span>Exchange Board</span>
                <ArrowRight size={14} />
              </Link>
            </div>

            {listings.length === 0 ? (
              <div
                style={{
                  padding: '2.5rem 1rem',
                  textAlign: 'center',
                  color: 'var(--text-muted)',
                }}
              >
                <RefreshCw size={28} style={{ margin: '0 auto 0.5rem auto', opacity: 0.5 }} />
                <p style={{ fontSize: '0.8125rem' }}>No exchange listings currently live.</p>
                <Link
                  href="/exchange"
                  className="clay-btn clay-btn-secondary"
                  style={{ marginTop: '0.75rem', display: 'inline-flex' }}
                >
                  Browse Requirements
                </Link>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.625rem' }}>
                {listings.map((item) => (
                  <div
                    key={item.listing_id}
                    style={{
                      padding: '0.75rem',
                      borderRadius: '8px',
                      backgroundColor: 'var(--bg-subtle)',
                      border: '1px solid var(--border-subtle)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                    }}
                  >
                    <div>
                      <div
                        style={{
                          fontWeight: 600,
                          fontSize: '0.8125rem',
                          color: 'var(--text-primary)',
                        }}
                      >
                        {item.material_type || 'Industrial Scrap Lot'}
                      </div>
                      <div
                        style={{
                          fontSize: '0.6875rem',
                          color: 'var(--text-muted)',
                          display: 'flex',
                          gap: '0.75rem',
                          marginTop: '0.15rem',
                        }}
                      >
                        <span className="tnum">
                          {formatNumber(item.quantity)} {item.unit}
                        </span>
                        {item.asking_price_per_unit && (
                          <span className="tnum">
                            ${item.asking_price_per_unit}/{item.unit}
                          </span>
                        )}
                        <span style={{ textTransform: 'capitalize' }}>{item.status}</span>
                      </div>
                    </div>

                    <Link
                      href="/rfqs"
                      className="clay-btn-ghost"
                      style={{
                        padding: '0.375rem 0.625rem',
                        fontSize: '0.6875rem',
                        borderRadius: '6px',
                        textDecoration: 'none',
                        color: 'var(--primary-container)',
                        fontWeight: 600,
                        backgroundColor: '#ffffff',
                        border: '1px solid var(--border-subtle)',
                      }}
                    >
                      Negotiate
                    </Link>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Third Section: Pending Requests for Quotation (RFQs) */}
        <div
          className="clay-card"
          style={{
            padding: '1.25rem',
            display: 'flex',
            flexDirection: 'column',
            backgroundColor: '#ffffff',
          }}
        >
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              paddingBottom: '0.75rem',
              borderBottom: '1px solid var(--border-subtle)',
              marginBottom: '1rem',
            }}
          >
            <div>
              <span className="label-compact">Bilateral Deals in Flight</span>
              <h3 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                Pending Requests for Quotation (RFQs)
              </h3>
            </div>
            <Link
              href="/rfqs"
              style={{
                fontSize: '0.75rem',
                fontWeight: 600,
                color: 'var(--primary-container)',
                textDecoration: 'none',
                display: 'flex',
                alignItems: 'center',
                gap: '0.25rem',
              }}
            >
              <span>View All RFQs</span>
              <ArrowRight size={14} />
            </Link>
          </div>

          {rfqs.length === 0 ? (
            <div
              style={{
                padding: '2rem 1rem',
                textAlign: 'center',
                color: 'var(--text-muted)',
              }}
            >
              <FileText size={28} style={{ margin: '0 auto 0.5rem auto', opacity: 0.5 }} />
              <p style={{ fontSize: '0.8125rem' }}>No pending RFQs in this tenant workspace.</p>
            </div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '0.75rem' }}>
              {rfqs.map((rfq) => (
                <div
                  key={rfq.rfq_id}
                  style={{
                    padding: '0.75rem 1rem',
                    borderRadius: '8px',
                    backgroundColor: 'var(--bg-subtle)',
                    border: '1px solid var(--border-subtle)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                  }}
                >
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
                      <span style={{ fontFamily: 'monospace', fontSize: '0.75rem', fontWeight: 600 }}>
                        RFQ-{rfq.rfq_id.slice(0, 8)}
                      </span>
                      {getStatusBadge(rfq.status)}
                    </div>
                    <div className="tnum" style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                      Requested: <strong>{formatNumber(rfq.requested_quantity)}</strong> MT · Target: ${rfq.target_price_per_unit || 'Market'}/MT
                    </div>
                  </div>
                  <Link
                    href={`/rfqs?rfq_id=${rfq.rfq_id}`}
                    className="clay-btn-ghost"
                    style={{
                      padding: '0.375rem 0.625rem',
                      fontSize: '0.6875rem',
                      borderRadius: '6px',
                      textDecoration: 'none',
                      color: 'var(--primary-container)',
                      fontWeight: 600,
                      backgroundColor: '#ffffff',
                      border: '1px solid var(--border-subtle)',
                    }}
                  >
                    Inspect
                  </Link>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Geological / Industrial Assurance Footnote */}
        <div
          className="clay-card"
          style={{
            padding: '1rem 1.25rem',
            backgroundColor: 'var(--bg-subtle)',
            display: 'flex',
            flexWrap: 'wrap',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '1rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <Cpu size={20} color="var(--primary-container)" />
            <div>
              <div style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                Immutable Audit Trails Active
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                All lot registrations, qualification proofs, and exchange transactions generate
                verifiable SHA-256 state transitions.
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span
              className="label-compact"
              style={{
                padding: '0.2rem 0.5rem',
                backgroundColor: 'var(--accent-teal-subtle)',
                color: 'var(--primary-container)',
                borderRadius: '4px',
              }}
            >
              DPP 2026/02 Ready
            </span>
            <span
              className="label-compact"
              style={{
                padding: '0.2rem 0.5rem',
                backgroundColor: '#ffffff',
                border: '1px solid var(--border-subtle)',
                borderRadius: '4px',
              }}
            >
              EN 15804+A2
            </span>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
