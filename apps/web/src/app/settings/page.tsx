'use client';

import React, { useEffect, useState } from 'react';
import {
  Settings,
  Building2,
  Factory,
  ShieldCheck,
  Activity,
  CheckCircle2,
  RefreshCw,
  User,
  Sliders,
  Check,
} from 'lucide-react';
import { AppShell } from '@/components/AppShell';
import { Badge } from '@/components/Badge';
import { useAuth } from '@/lib/auth';
import { api } from '@/lib/api-client';
import { UserRole } from '@/types';

export default function SettingsPage() {
  const { user, switchRole } = useAuth();
  const [healthStatus, setHealthStatus] = useState<string>('Checking...');
  const [healthLatency, setHealthLatency] = useState<number | null>(null);
  const [isPinging, setIsPinging] = useState(false);

  const pingHealth = async () => {
    setIsPinging(true);
    const start = Date.now();
    try {
      const res = await api.health.check();
      const elapsed = Date.now() - start;
      setHealthLatency(elapsed);
      setHealthStatus(res.data?.status === 'ok' ? 'Nominal (Healthy)' : 'Degraded');
    } catch {
      setHealthStatus('Unreachable (Offline)');
      setHealthLatency(null);
    } finally {
      setIsPinging(false);
    }
  };

  useEffect(() => {
    pingHealth();
  }, []);

  const roles: { id: UserRole; title: string; desc: string }[] = [
    {
      id: 'facility_operator',
      title: 'Facility Operator',
      desc: 'Focused on material lot creation, physical measurements, and ProofPath qualification.',
    },
    {
      id: 'buyer',
      title: 'Industrial Buyer',
      desc: 'Focused on feedstock requirements, circular exchange listings, and RFQ negotiations.',
    },
    {
      id: 'seller',
      title: 'Material Supplier / Seller',
      desc: 'Focused on inventory lots publishing, bilateral offer terms, and dispatch receipts.',
    },
    {
      id: 'admin',
      title: 'Cluster Administrator',
      desc: 'Full administrative access across all tenant nodes, cluster indicators, and settings.',
    },
  ];

  return (
    <AppShell>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', maxWidth: '1000px' }}>
        {/* Header */}
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
            <span className="label-compact" style={{ color: 'var(--accent-teal)' }}>
              Tenant Configuration &amp; Governance
            </span>
            <span style={{ color: 'var(--text-muted)' }}>·</span>
            <span className="label-compact" style={{ color: 'var(--text-muted)' }}>
              Hardware Sovereign Anchor
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
            Workspace &amp; Node Settings
          </h1>
          <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
            Manage active tenant scope, facility sites, and operational persona.
          </p>
        </div>

        {/* Section 1: Active Persona Switcher */}
        <section
          className="clay-card"
          style={{ padding: '1.5rem', backgroundColor: '#ffffff', display: 'flex', flexDirection: 'column', gap: '1rem' }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div>
              <span className="label-compact">Access &amp; Role Gate</span>
              <h2 style={{ fontSize: '1.125rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                Active Operational Role
              </h2>
            </div>
            <Badge variant="teal" dot>
              {user?.role?.replace('_', ' ')}
            </Badge>
          </div>

          <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
            Switch between industrial roles to test role-aware navigation and permissions supported by
            the existing authentication and organization model.
          </p>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
              gap: '0.75rem',
            }}
          >
            {roles.map((r) => {
              const isSelected = user?.role === r.id;
              return (
                <div
                  key={r.id}
                  onClick={() => switchRole(r.id)}
                  className={`clay-card-interactive ${isSelected ? 'clay-card-selected' : ''}`}
                  style={{
                    padding: '1rem',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                  }}
                >
                  <div>
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        marginBottom: '0.375rem',
                      }}
                    >
                      <span style={{ fontWeight: 600, fontSize: '0.875rem' }}>{r.title}</span>
                      {isSelected && <Check size={16} color="var(--primary-container)" />}
                    </div>
                    <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', lineHeight: 1.4 }}>
                      {r.desc}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        {/* Section 2: Organization & Facility Profile */}
        <section
          className="clay-card"
          style={{ padding: '1.5rem', backgroundColor: '#ffffff', display: 'flex', flexDirection: 'column', gap: '1.25rem' }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div>
              <span className="label-compact">Tenant Identity</span>
              <h2 style={{ fontSize: '1.125rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                Organization &amp; Facility Profile
              </h2>
            </div>
            <span className="label-compact" style={{ color: 'var(--status-success)' }}>
              Verified Entity
            </span>
          </div>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
              gap: '1rem',
            }}
          >
            <div
              style={{
                padding: '0.875rem',
                backgroundColor: 'var(--bg-subtle)',
                borderRadius: '8px',
                border: '1px solid var(--border-subtle)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
                <Building2 size={16} color="var(--primary-container)" />
                <span className="label-compact">Organization Legal Name</span>
              </div>
              <div style={{ fontWeight: 600, fontSize: '0.875rem' }}>
                Nordic Smelting &amp; Secondary Alloy AG
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                Org ID: {user?.org_id}
              </div>
            </div>

            <div
              style={{
                padding: '0.875rem',
                backgroundColor: 'var(--bg-subtle)',
                borderRadius: '8px',
                border: '1px solid var(--border-subtle)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
                <Factory size={16} color="var(--primary-container)" />
                <span className="label-compact">Active Production Site</span>
              </div>
              <div style={{ fontWeight: 600, fontSize: '0.875rem' }}>
                {user?.facility_name || 'Central Rail Smelter & Foundry #4'}
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                Facility ID: {user?.facility_id}
              </div>
            </div>
          </div>
        </section>

        {/* Section 3: Backend API Integration & Diagnostics */}
        <section
          className="clay-card"
          style={{ padding: '1.5rem', backgroundColor: '#ffffff', display: 'flex', flexDirection: 'column', gap: '1rem' }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div>
              <span className="label-compact">Connectivity Diagnostics</span>
              <h2 style={{ fontSize: '1.125rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                STRATA Core Telemetry API
              </h2>
            </div>
            <button
              onClick={pingHealth}
              disabled={isPinging}
              className="clay-btn clay-btn-secondary"
              style={{ padding: '0.375rem 0.625rem', fontSize: '0.75rem' }}
            >
              <RefreshCw size={12} className={isPinging ? 'animate-spin' : ''} />
              <span>Ping Health</span>
            </button>
          </div>

          <div
            style={{
              padding: '0.875rem',
              borderRadius: '8px',
              backgroundColor: 'var(--bg-subtle)',
              border: '1px solid var(--border-subtle)',
              display: 'flex',
              flexDirection: 'column',
              gap: '0.5rem',
              fontSize: '0.8125rem',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-muted)' }}>Configured API Base URL:</span>
              <span style={{ fontFamily: 'monospace', fontWeight: 600 }}>
                {process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-muted)' }}>Status Handshake:</span>
              <span style={{ fontWeight: 600 }}>{healthStatus}</span>
            </div>
            {healthLatency !== null && (
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Round-Trip Latency:</span>
                <span className="tnum" style={{ fontWeight: 600 }}>
                  {healthLatency} ms
                </span>
              </div>
            )}
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-muted)' }}>Tenant Isolation Header:</span>
              <span style={{ fontFamily: 'monospace' }}>X-Org-Id: {user?.org_id}</span>
            </div>
          </div>
        </section>
      </div>
    </AppShell>
  );
}
