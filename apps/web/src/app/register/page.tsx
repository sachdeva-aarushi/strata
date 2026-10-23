'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  Building2,
  Mail,
  User,
  Lock,
  ArrowRight,
  CheckCircle2,
  AlertCircle,
  Loader2,
  ShieldAlert,
} from 'lucide-react';
import { useAuth } from '@/lib/auth';
import { UserRole } from '@/types';

export default function RegisterPage() {
  const router = useRouter();
  const { register } = useAuth();

  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [orgName, setOrgName] = useState('');
  const [role, setRole] = useState<UserRole>('facility_operator');

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!name.trim()) {
      setError('Please provide your operational contact name.');
      return;
    }
    if (!email || !email.includes('@')) {
      setError('Please provide a valid work or enterprise email.');
      return;
    }
    if (!orgName.trim()) {
      setError('Please specify your incorporated organization name.');
      return;
    }
    if (!password || password.length < 6) {
      setError('Credential secret must be at least 6 characters.');
      return;
    }

    setIsLoading(true);
    try {
      await register(name, email, role);
      // Proceed directly to the Onboarding wizard to configure entity & facility
      router.push('/onboarding');
    } catch (err: any) {
      setError(err?.message || 'Registration failed. Please check inputs.');
      setIsLoading(false);
    }
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        backgroundColor: 'var(--bg-canvas)',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        padding: '1.5rem',
      }}
    >
      <header
        style={{
          maxWidth: '1280px',
          width: '100%',
          margin: '0 auto',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          paddingBottom: '1.5rem',
        }}
      >
        <Link
          href="/login"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.625rem',
            textDecoration: 'none',
            color: 'inherit',
          }}
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
          <span
            style={{
              fontSize: '1.125rem',
              fontWeight: 700,
              letterSpacing: '0.04em',
              color: 'var(--text-primary)',
            }}
          >
            STRATA
          </span>
        </Link>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <span className="label-compact">Already registered?</span>
          <Link href="/login" className="clay-btn clay-btn-secondary" style={{ padding: '0.375rem 0.75rem' }}>
            Sign In
          </Link>
        </div>
      </header>

      <main
        style={{
          maxWidth: '520px',
          width: '100%',
          margin: 'auto',
          padding: '1rem 0',
        }}
      >
        <div className="clay-card" style={{ padding: '2.25rem', backgroundColor: '#ffffff' }}>
          <div style={{ marginBottom: '1.5rem' }}>
            <span className="label-compact" style={{ color: 'var(--accent-teal)' }}>
              Step 0 · Account Provisioning
            </span>
            <h1
              style={{
                fontSize: '1.375rem',
                fontWeight: 700,
                color: 'var(--primary)',
                marginTop: '0.25rem',
                marginBottom: '0.25rem',
              }}
            >
              Register Enterprise Account
            </h1>
            <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
              Create your administrative credentials to begin circularity onboarding.
            </p>
          </div>

          {error && (
            <div
              style={{
                padding: '0.75rem',
                borderRadius: '8px',
                backgroundColor: 'var(--status-error-bg)',
                border: '1px solid rgba(166, 58, 53, 0.25)',
                color: 'var(--status-error)',
                fontSize: '0.8125rem',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                marginBottom: '1rem',
              }}
            >
              <AlertCircle size={16} />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div>
              <label
                htmlFor="name"
                className="label-compact"
                style={{ display: 'block', marginBottom: '0.375rem' }}
              >
                Contact Full Name <span style={{ color: 'var(--status-error)' }}>*</span>
              </label>
              <div style={{ position: 'relative' }}>
                <span
                  style={{
                    position: 'absolute',
                    left: '0.75rem',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    color: 'var(--text-muted)',
                  }}
                >
                  <User size={16} />
                </span>
                <input
                  id="name"
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Dr. Hélène Vance"
                  className="clay-input"
                  style={{ paddingLeft: '2.25rem' }}
                />
              </div>
            </div>

            <div>
              <label
                htmlFor="email"
                className="label-compact"
                style={{ display: 'block', marginBottom: '0.375rem' }}
              >
                Work Email Address <span style={{ color: 'var(--status-error)' }}>*</span>
              </label>
              <div style={{ position: 'relative' }}>
                <span
                  style={{
                    position: 'absolute',
                    left: '0.75rem',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    color: 'var(--text-muted)',
                  }}
                >
                  <Mail size={16} />
                </span>
                <input
                  id="email"
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="helene.vance@nordicsmelting.ch"
                  className="clay-input"
                  style={{ paddingLeft: '2.25rem' }}
                />
              </div>
            </div>

            <div>
              <label
                htmlFor="orgName"
                className="label-compact"
                style={{ display: 'block', marginBottom: '0.375rem' }}
              >
                Legal Organization Name <span style={{ color: 'var(--status-error)' }}>*</span>
              </label>
              <div style={{ position: 'relative' }}>
                <span
                  style={{
                    position: 'absolute',
                    left: '0.75rem',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    color: 'var(--text-muted)',
                  }}
                >
                  <Building2 size={16} />
                </span>
                <input
                  id="orgName"
                  type="text"
                  required
                  value={orgName}
                  onChange={(e) => setOrgName(e.target.value)}
                  placeholder="Nordic Smelting & Secondary Alloy AG"
                  className="clay-input"
                  style={{ paddingLeft: '2.25rem' }}
                />
              </div>
            </div>

            <div>
              <label
                htmlFor="role"
                className="label-compact"
                style={{ display: 'block', marginBottom: '0.375rem' }}
              >
                Primary Enterprise Role
              </label>
              <select
                id="role"
                value={role}
                onChange={(e) => setRole(e.target.value as UserRole)}
                className="clay-select"
              >
                <option value="facility_operator">Facility Operator (Production / Smelter)</option>
                <option value="buyer">Industrial Buyer (Feedstock Procurement)</option>
                <option value="seller">Material Supplier / Recovery Partner</option>
                <option value="admin">Cluster / Entity Administrator</option>
              </select>
            </div>

            <div>
              <label
                htmlFor="password"
                className="label-compact"
                style={{ display: 'block', marginBottom: '0.375rem' }}
              >
                Credential Secret <span style={{ color: 'var(--status-error)' }}>*</span>
              </label>
              <div style={{ position: 'relative' }}>
                <span
                  style={{
                    position: 'absolute',
                    left: '0.75rem',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    color: 'var(--text-muted)',
                  }}
                >
                  <Lock size={16} />
                </span>
                <input
                  id="password"
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="clay-input"
                  style={{ paddingLeft: '2.25rem' }}
                />
              </div>
              <p style={{ fontSize: '0.6875rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                Must be at least 6 characters. Stored securely with PBKDF2 hashing.
              </p>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="clay-btn clay-btn-primary"
              style={{
                width: '100%',
                padding: '0.6875rem',
                fontSize: '0.875rem',
                marginTop: '0.5rem',
              }}
            >
              {isLoading ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  <span>Provisioning Account...</span>
                </>
              ) : (
                <>
                  <span>Continue to Onboarding</span>
                  <ArrowRight size={16} />
                </>
              )}
            </button>
          </form>
        </div>
      </main>

      <footer
        style={{
          maxWidth: '1280px',
          width: '100%',
          margin: '0 auto',
          textAlign: 'center',
          fontSize: '0.6875rem',
          color: 'var(--text-muted)',
        }}
      >
        STRATA Circularity Intelligence © 2026 · Sovereign Enterprise Telemetry
      </footer>
    </div>
  );
}
