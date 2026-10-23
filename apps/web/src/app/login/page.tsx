'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  ShieldCheck,
  Lock,
  Mail,
  ArrowRight,
  Eye,
  EyeOff,
  CheckCircle2,
  KeyRound,
  AlertCircle,
  Loader2,
} from 'lucide-react';
import { useAuth } from '@/lib/auth';
import { UserRole } from '@/types';

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();

  const [email, setEmail] = useState('operator@plant-line.com');
  const [password, setPassword] = useState('••••••••••••');
  const [role, setRole] = useState<UserRole>('facility_operator');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberTerminal, setRememberTerminal] = useState(true);

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!email || !email.includes('@')) {
      setError('Please provide a valid work or facility email.');
      return;
    }
    if (!password || password.length < 6) {
      setError('Credential secret must be at least 6 characters.');
      return;
    }

    setIsLoading(true);
    try {
      await login(email, role);
      setSuccess(true);
      setTimeout(() => {
        router.push('/overview');
      }, 700);
    } catch (err: any) {
      setError(err?.message || 'Authentication failed. Please verify credentials.');
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
      {/* Header bar */}
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
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
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
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.375rem' }}>
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
            <span
              className="label-compact"
              style={{ fontSize: '0.625rem', color: 'var(--text-muted)' }}
            >
              Circularity Engine
            </span>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.375rem',
              backgroundColor: 'var(--bg-subtle)',
              padding: '0.25rem 0.625rem',
              borderRadius: '6px',
              border: '1px solid var(--border-subtle)',
            }}
          >
            <span
              style={{
                width: '6px',
                height: '6px',
                borderRadius: '50%',
                backgroundColor: 'var(--status-success)',
              }}
            />
            <span className="label-compact" style={{ fontSize: '0.625rem' }}>
              Node 09 · Nominal
            </span>
          </div>
          <span
            className="label-compact"
            style={{
              padding: '0.25rem 0.5rem',
              backgroundColor: 'var(--bg-subtle)',
              border: '1px solid var(--border-subtle)',
              borderRadius: '6px',
              color: 'var(--text-secondary)',
            }}
          >
            ENTERPRISE ACCESS V2.4
          </span>
        </div>
      </header>

      {/* Main Dual-Column Content */}
      <main
        style={{
          maxWidth: '1280px',
          width: '100%',
          margin: 'auto',
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
          gap: '2.5rem',
          alignItems: 'center',
          padding: '1rem 0',
        }}
      >
        {/* Left Column: Industrial Assurance Digest */}
        <section
          className="clay-card"
          style={{
            padding: '2rem',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
            backgroundColor: 'var(--bg-subtle)',
            minHeight: '440px',
          }}
        >
          <div>
            <div
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.375rem',
                color: 'var(--accent-teal)',
                marginBottom: '1rem',
              }}
            >
              <ShieldCheck size={16} />
              <span className="label-compact" style={{ color: 'var(--accent-teal)' }}>
                Continuous Mass-Balance Traceability
              </span>
            </div>

            <h1
              className="font-serif"
              style={{
                fontSize: '2rem',
                fontWeight: 500,
                lineHeight: 1.25,
                color: 'var(--primary)',
                marginBottom: '1rem',
                letterSpacing: '-0.015em',
              }}
            >
              A clearer path from waste to value.
            </h1>

            <p
              style={{
                color: 'var(--text-secondary)',
                fontSize: '0.9375rem',
                lineHeight: 1.6,
                marginBottom: '1.75rem',
              }}
            >
              Industrial material intelligence, physical custody signatures, and deterministic
              qualification across verified closed-loop processing networks.
            </p>

            {/* Micro Metrics Panel */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(3, 1fr)',
                gap: '0.75rem',
              }}
            >
              <div
                className="clay-card"
                style={{ padding: '0.75rem', backgroundColor: '#ffffff' }}
              >
                <div className="label-compact" style={{ marginBottom: '0.25rem' }}>
                  Assayed Purity
                </div>
                <div
                  className="tnum"
                  style={{
                    fontSize: '1.25rem',
                    fontWeight: 700,
                    color: 'var(--primary)',
                  }}
                >
                  99.82%
                </div>
              </div>

              <div
                className="clay-card"
                style={{ padding: '0.75rem', backgroundColor: '#ffffff' }}
              >
                <div className="label-compact" style={{ marginBottom: '0.25rem' }}>
                  CO2 Offset
                </div>
                <div
                  className="tnum"
                  style={{
                    fontSize: '1.25rem',
                    fontWeight: 700,
                    color: 'var(--status-success)',
                  }}
                >
                  -4.18 t
                </div>
              </div>

              <div
                className="clay-card"
                style={{ padding: '0.75rem', backgroundColor: '#ffffff' }}
              >
                <div className="label-compact" style={{ marginBottom: '0.25rem' }}>
                  Chain State
                </div>
                <div
                  style={{
                    fontSize: '1rem',
                    fontWeight: 700,
                    color: 'var(--primary)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.25rem',
                    marginTop: '0.25rem',
                  }}
                >
                  <CheckCircle2 size={16} color="var(--status-success)" />
                  <span>Signed</span>
                </div>
              </div>
            </div>
          </div>

          <div
            style={{
              paddingTop: '1.5rem',
              borderTop: '1px solid var(--border-subtle)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              fontSize: '0.75rem',
              color: 'var(--text-muted)',
            }}
          >
            <span>Certified Audit Ledger</span>
            <span className="tnum">ISO/IEC 19770 · EU DPP Standard</span>
          </div>
        </section>

        {/* Right Column: Console Sign In Form */}
        <section
          className="clay-card"
          style={{
            padding: '2.25rem',
            maxWidth: '480px',
            width: '100%',
            margin: '0 auto',
            backgroundColor: '#ffffff',
          }}
        >
          <div style={{ marginBottom: '1.5rem' }}>
            <h2
              style={{
                fontSize: '1.25rem',
                fontWeight: 700,
                color: 'var(--primary)',
                marginBottom: '0.25rem',
              }}
            >
              Sign In to Facility Rail
            </h2>
            <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
              Enter your verified credentials or select an operational role.
            </p>
          </div>

          {/* SAML fast-lane button */}
          <button
            type="button"
            className="clay-btn clay-btn-secondary"
            style={{
              width: '100%',
              padding: '0.625rem',
              marginBottom: '1.25rem',
              fontSize: '0.8125rem',
              fontWeight: 500,
            }}
            onClick={() => {
              setEmail('sso.operator@enterprise-node.eu');
              setRole('facility_operator');
            }}
          >
            <KeyRound size={16} color="var(--primary-container)" />
            <span>Continue with Enterprise SAML / SSO</span>
          </button>

          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.75rem',
              marginBottom: '1.25rem',
            }}
          >
            <div style={{ flex: 1, height: '1px', backgroundColor: 'var(--border-subtle)' }} />
            <span className="label-compact" style={{ fontSize: '0.625rem' }}>
              or continue with industrial credentials
            </span>
            <div style={{ flex: 1, height: '1px', backgroundColor: 'var(--border-subtle)' }} />
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

          {success && (
            <div
              style={{
                padding: '0.75rem',
                borderRadius: '8px',
                backgroundColor: 'var(--status-success-bg)',
                border: '1px solid rgba(40, 99, 67, 0.25)',
                color: 'var(--status-success)',
                fontSize: '0.8125rem',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                marginBottom: '1rem',
              }}
            >
              <CheckCircle2 size={16} />
              <span>Handshake established. Loading workspace...</span>
            </div>
          )}

          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {/* Email field */}
            <div>
              <label
                htmlFor="email"
                className="label-compact"
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  marginBottom: '0.375rem',
                }}
              >
                <span>Work or Facility Email</span>
                <span style={{ textTransform: 'none', color: 'var(--text-muted)' }}>
                  Operator ID
                </span>
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
                  placeholder="operator@plant-line.com"
                  className="clay-input"
                  style={{ paddingLeft: '2.25rem' }}
                />
              </div>
            </div>

            {/* Password field */}
            <div>
              <label
                htmlFor="password"
                className="label-compact"
                style={{ display: 'block', marginBottom: '0.375rem' }}
              >
                Credential Secret
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
                  type={showPassword ? 'text' : 'password'}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="clay-input"
                  style={{ paddingLeft: '2.25rem', paddingRight: '2.25rem' }}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  style={{
                    position: 'absolute',
                    right: '0.75rem',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    background: 'none',
                    border: 'none',
                    color: 'var(--text-muted)',
                    cursor: 'pointer',
                  }}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            {/* Role selector */}
            <div>
              <label
                htmlFor="role"
                className="label-compact"
                style={{ display: 'block', marginBottom: '0.375rem' }}
              >
                Target Workspace Persona
              </label>
              <select
                id="role"
                value={role}
                onChange={(e) => setRole(e.target.value as UserRole)}
                className="clay-select"
              >
                <option value="facility_operator">Facility Operator (Materials &amp; ProofPath)</option>
                <option value="buyer">Industrial Buyer (Circular Exchange &amp; RFQs)</option>
                <option value="seller">Material Supplier / Seller</option>
                <option value="admin">Cluster Administrator</option>
              </select>
            </div>

            {/* Remember terminal row */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '0.25rem 0',
              }}
            >
              <label
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  fontSize: '0.75rem',
                  color: 'var(--text-secondary)',
                  cursor: 'pointer',
                }}
              >
                <input
                  type="checkbox"
                  checked={rememberTerminal}
                  onChange={(e) => setRememberTerminal(e.target.checked)}
                  style={{ accentColor: 'var(--primary-container)' }}
                />
                <span>Remember terminal (30 days)</span>
              </label>

              <a
                href="#forgot"
                style={{
                  fontSize: '0.75rem',
                  color: 'var(--primary-container)',
                  textDecoration: 'none',
                  fontWeight: 500,
                }}
              >
                Forgot secret?
              </a>
            </div>

            {/* Submit button */}
            <button
              type="submit"
              disabled={isLoading || success}
              className="clay-btn clay-btn-primary"
              style={{
                width: '100%',
                padding: '0.6875rem',
                fontSize: '0.875rem',
                marginTop: '0.25rem',
              }}
            >
              {isLoading ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  <span>Verifying Credentials...</span>
                </>
              ) : success ? (
                <>
                  <CheckCircle2 size={16} />
                  <span>Access Verified</span>
                </>
              ) : (
                <>
                  <span>Sign In to Facility Rail</span>
                  <ArrowRight size={16} />
                </>
              )}
            </button>
          </form>

          {/* Registration link */}
          <div
            style={{
              marginTop: '1.25rem',
              paddingTop: '1rem',
              borderTop: '1px solid var(--border-subtle)',
              textAlign: 'center',
              fontSize: '0.75rem',
              color: 'var(--text-muted)',
            }}
          >
            <span>Need enterprise or facility onboarding? </span>
            <Link
              href="/register"
              style={{
                color: 'var(--primary-container)',
                fontWeight: 600,
                textDecoration: 'none',
              }}
            >
              Register Organization
            </Link>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer
        style={{
          maxWidth: '1280px',
          width: '100%',
          margin: '0 auto',
          paddingTop: '1.5rem',
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          fontSize: '0.6875rem',
          color: 'var(--text-muted)',
          gap: '0.75rem',
        }}
      >
        <div>STRATA Industrial Systems SE · Telemetry Core v4.11-rc</div>
        <div style={{ display: 'flex', gap: '1rem' }}>
          <span>Data Custody Framework</span>
          <span>·</span>
          <span>Audit Ledger</span>
          <span>·</span>
          <span style={{ color: 'var(--status-success)' }}>Zero Packet Drop</span>
        </div>
      </footer>
    </div>
  );
}
