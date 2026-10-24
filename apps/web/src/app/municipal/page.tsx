'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import {
  Building2,
  RefreshCw,
  Lock,
  AlertTriangle,
  ArrowRight,
  TrendingDown,
  TrendingUp,
  Shield,
  Layers,
} from 'lucide-react';
import { useMunicipalIntelligence } from '@/hooks/useMunicipalIntelligence';
import { MunicipalZoneFlow } from '@/lib/api/client';
import { ApiErrorBoundary } from '@/components/ApiErrorBoundary';

function formatKg(val: number | string | undefined | null): string {
  if (val === undefined || val === null || val === '') return '0';
  const num = typeof val === 'number' ? val : parseFloat(val);
  if (isNaN(num)) return '0';
  return new Intl.NumberFormat('en-IN').format(num);
}

export default function MunicipalPage() {
  return (
    <ApiErrorBoundary>
      <MunicipalDashboard />
    </ApiErrorBoundary>
  );
}

function MunicipalDashboard() {
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const { data, isLoading, error, refetch } = useMunicipalIntelligence(
    selectedCategory ? { material_category: selectedCategory } : undefined
  );

  const flows: MunicipalZoneFlow[] = data?.flows || [
    {
      zone_name: 'Zone A - Pandesara Industrial Belt',
      material_category: 'Textiles & Composites',
      generation_kg: 450000,
      capacity_kg: 280000,
      net_balance_kg: -170000,
      classification: 'DEFICIT_HOTSPOT',
      facility_count: 8,
      cohort_suppressed: false,
    },
    {
      zone_name: 'Zone B - Sachin GIDC Eco-Park',
      material_category: 'Polymers & Synthetics',
      generation_kg: 310000,
      capacity_kg: 330000,
      net_balance_kg: 20000,
      classification: 'BALANCED',
      facility_count: 5,
      cohort_suppressed: false,
    },
    {
      zone_name: 'Zone C - Hazira Heavy Recovery Hub',
      material_category: 'Metallics & Slag',
      generation_kg: 620000,
      capacity_kg: 950000,
      net_balance_kg: 330000,
      classification: 'SURPLUS_CAPACITY',
      facility_count: 12,
      cohort_suppressed: false,
    },
    {
      zone_name: 'Zone D - Rural Buffer Processing District',
      material_category: 'Biomass & Organics',
      generation_kg: 0,
      capacity_kg: 0,
      net_balance_kg: 0,
      classification: 'SUPPRESSED',
      facility_count: 2,
      cohort_suppressed: true,
    },
  ];

  const hasSuppression = data?.has_suppressed_zones || flows.some((f) => f.classification === 'SUPPRESSED');

  const renderBadge = (classification: string) => {
    switch (classification) {
      case 'DEFICIT_HOTSPOT':
        return (
          <span
            style={{
              backgroundColor: '#FEE2E2',
              color: '#991B1B',
              padding: '0.25rem 0.625rem',
              borderRadius: '9999px',
              fontSize: '0.75rem',
              fontWeight: 700,
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.25rem',
            }}
          >
            <TrendingDown size={12} />
            DEFICIT_HOTSPOT
          </span>
        );
      case 'BALANCED':
        return (
          <span
            style={{
              backgroundColor: '#DCFCE7',
              color: '#166534',
              padding: '0.25rem 0.625rem',
              borderRadius: '9999px',
              fontSize: '0.75rem',
              fontWeight: 700,
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.25rem',
            }}
          >
            BALANCED
          </span>
        );
      case 'SURPLUS_CAPACITY':
        return (
          <span
            style={{
              backgroundColor: '#DBEAFE',
              color: '#1E40AF',
              padding: '0.25rem 0.625rem',
              borderRadius: '9999px',
              fontSize: '0.75rem',
              fontWeight: 700,
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.25rem',
            }}
          >
            <TrendingUp size={12} />
            SURPLUS_CAPACITY
          </span>
        );
      case 'SUPPRESSED':
      default:
        return (
          <span
            style={{
              backgroundColor: '#F3F4F6',
              color: '#374151',
              padding: '0.25rem 0.625rem',
              borderRadius: '9999px',
              fontSize: '0.75rem',
              fontWeight: 700,
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.25rem',
            }}
          >
            <Lock size={12} />
            SUPPRESSED
          </span>
        );
    }
  };

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#F8F9FA', display: 'flex', flexDirection: 'column' }}>
      {/* Top Navbar */}
      <header style={{ position: 'sticky', top: 0, zIndex: 40, backgroundColor: 'rgba(255,255,255,0.95)', backdropFilter: 'blur(8px)', borderBottom: '1px solid #E5E7EB' }}>
        <div style={{ maxWidth: '1280px', margin: '0 auto', padding: '0 1.5rem', height: '56px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Link href="/" style={{ display: 'flex', alignItems: 'center', gap: '0.625rem', textDecoration: 'none' }}>
            <div style={{ width: '28px', height: '28px', borderRadius: '6px', backgroundColor: '#0F4C81', color: '#ffffff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: '0.875rem' }}>S</div>
            <span style={{ fontSize: '1rem', fontWeight: 700, letterSpacing: '0.05em', color: '#1A1A1A' }}>STRATA</span>
          </Link>
          <nav style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Link href="/" style={{ padding: '0.375rem 0.75rem', fontSize: '0.8125rem', fontWeight: 500, color: '#4B5563', textDecoration: 'none' }}>Home</Link>
            <Link href="/marketplace" style={{ padding: '0.375rem 0.75rem', fontSize: '0.8125rem', fontWeight: 500, color: '#4B5563', textDecoration: 'none' }}>Marketplace</Link>
            <Link href="/rfqs" style={{ padding: '0.375rem 0.75rem', fontSize: '0.8125rem', fontWeight: 500, color: '#4B5563', textDecoration: 'none' }}>RFQs</Link>
            <Link href="/login" style={{ padding: '0.375rem 0.75rem', fontSize: '0.8125rem', fontWeight: 500, color: '#4B5563', textDecoration: 'none' }}>Sign In</Link>
          </nav>
        </div>
      </header>

      <main style={{ maxWidth: '1280px', margin: '0 auto', padding: '2rem 1.5rem', flex: 1, width: '100%' }}>
        {/* Title & Description */}
        <div style={{ marginBottom: '1.75rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 600, color: '#0F4C81', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Municipal Circularity Authority
            </span>
            <span style={{ color: '#D1D5DB' }}>·</span>
            <span style={{ fontSize: '0.75rem', color: '#6B7280' }}>Differential Privacy &amp; k-Anonymity Guardrails</span>
          </div>
          <h1 style={{ fontSize: '1.875rem', fontWeight: 600, color: '#1A1A1A', letterSpacing: '-0.015em' }}>
            Urban Material Flows &amp; Capacity Gap Indicators
          </h1>
          <p style={{ fontSize: '0.875rem', color: '#4B5563', marginTop: '0.25rem' }}>
            Zone-level mass balance assessments, processing bottlenecks, and industrial byproduct circularity balances.
          </p>
        </div>

        {/* Persistent Cohort Suppression Alert */}
        {hasSuppression && (
          <div
            style={{
              padding: '1rem 1.25rem',
              borderRadius: '8px',
              backgroundColor: '#EFF6FF',
              border: '1px solid #BFDBFE',
              marginBottom: '1.5rem',
              display: 'flex',
              alignItems: 'flex-start',
              gap: '0.75rem',
            }}
          >
            <Shield size={20} color="#1E40AF" style={{ flexShrink: 0, marginTop: '2px' }} />
            <div>
              <div style={{ fontSize: '0.875rem', fontWeight: 600, color: '#1E40AF', marginBottom: '0.125rem' }}>
                Statistical Privacy Protection Active
              </div>
              <div style={{ fontSize: '0.8125rem', color: '#1E3A8A' }}>
                Data from protected zones is suppressed: fewer than 3 reporting facilities are present in this period. Showing district-level aggregate only to prevent commercial re-identification.
              </div>
            </div>
          </div>
        )}

        {/* Toolbar */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem', flexWrap: 'wrap', gap: '0.75rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              style={{
                padding: '0.5rem 1rem',
                borderRadius: '6px',
                border: '1px solid #D1D5DB',
                fontSize: '0.875rem',
                backgroundColor: '#FFFFFF',
              }}
            >
              <option value="">All Material Categories</option>
              <option value="textiles">Textiles &amp; Composites</option>
              <option value="polymers">Polymers &amp; Synthetics</option>
              <option value="metallics">Metallics &amp; Slag</option>
              <option value="biomass">Biomass &amp; Organics</option>
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
            }}
          >
            <RefreshCw size={14} />
            Refresh Indicators
          </button>
        </div>

        {/* Data Table */}
        <div style={{ backgroundColor: '#FFFFFF', borderRadius: '8px', border: '1px solid #E5E7EB', overflowX: 'auto', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.875rem' }}>
            <thead>
              <tr style={{ backgroundColor: '#F9FAFB', borderBottom: '1px solid #E5E7EB', color: '#374151' }}>
                <th style={{ padding: '0.875rem 1rem', fontWeight: 600 }}>Zone Name</th>
                <th style={{ padding: '0.875rem 1rem', fontWeight: 600 }}>Material Category</th>
                <th style={{ padding: '0.875rem 1rem', fontWeight: 600, textAlign: 'right' }}>Generation (kg)</th>
                <th style={{ padding: '0.875rem 1rem', fontWeight: 600, textAlign: 'right' }}>Capacity (kg)</th>
                <th style={{ padding: '0.875rem 1rem', fontWeight: 600, textAlign: 'right' }}>Net Balance (kg)</th>
                <th style={{ padding: '0.875rem 1rem', fontWeight: 600, textAlign: 'center' }}>Classification</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan={6} style={{ textAlign: 'center', padding: '3rem', color: '#6B7280' }}>
                    Loading municipal flow balance indicators...
                  </td>
                </tr>
              ) : (
                flows.map((flow, idx) => {
                  const isSuppressed = flow.classification === 'SUPPRESSED' || flow.cohort_suppressed;
                  return (
                    <tr
                      key={idx}
                      style={{
                        borderBottom: '1px solid #F3F4F6',
                        backgroundColor: isSuppressed ? '#FBFBFC' : '#FFFFFF',
                      }}
                    >
                      <td style={{ padding: '0.875rem 1rem', fontWeight: 600, color: '#1A1A1A' }}>
                        {flow.zone_name}
                      </td>
                      <td style={{ padding: '0.875rem 1rem', color: '#4B5563' }}>
                        {flow.material_category}
                      </td>
                      <td style={{ padding: '0.875rem 1rem', textAlign: 'right', fontFamily: 'monospace' }}>
                        {isSuppressed ? (
                          <span style={{ color: '#9CA3AF', fontStyle: 'italic' }}>Protected</span>
                        ) : (
                          formatKg(flow.generation_kg)
                        )}
                      </td>
                      <td style={{ padding: '0.875rem 1rem', textAlign: 'right', fontFamily: 'monospace' }}>
                        {isSuppressed ? (
                          <span style={{ color: '#9CA3AF', fontStyle: 'italic' }}>Protected</span>
                        ) : (
                          formatKg(flow.capacity_kg)
                        )}
                      </td>
                      <td style={{ padding: '0.875rem 1rem', textAlign: 'right', fontFamily: 'monospace' }}>
                        {isSuppressed ? (
                          <span style={{ color: '#9CA3AF' }}>—</span>
                        ) : (
                          <span style={{ fontWeight: 600, color: flow.net_balance_kg < 0 ? '#DC2626' : flow.net_balance_kg > 0 ? '#059669' : '#374151' }}>
                            {flow.net_balance_kg > 0 ? `+${formatKg(flow.net_balance_kg)}` : formatKg(flow.net_balance_kg)}
                          </span>
                        )}
                      </td>
                      <td style={{ padding: '0.875rem 1rem', textAlign: 'center' }}>
                        {renderBadge(flow.classification)}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </main>

      {/* Footer */}
      <footer style={{ borderTop: '1px solid #E5E7EB', backgroundColor: '#FFFFFF', marginTop: 'auto' }}>
        <div style={{ maxWidth: '1280px', margin: '0 auto', padding: '1rem 1.5rem', display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: '#6B7280' }}>
          <span><strong>STRATA</strong> · Industrial Circularity Operating System</span>
          <Link href="/" style={{ color: 'inherit', textDecoration: 'none' }}>← Back to Home</Link>
        </div>
      </footer>
    </div>
  );
}
