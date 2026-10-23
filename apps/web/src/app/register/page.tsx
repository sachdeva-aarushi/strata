'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import {
  Building2,
  Mail,
  User,
  Lock,
  ArrowRight,
  ArrowLeft,
  CheckCircle2,
  AlertCircle,
  Loader2,
  ShoppingCart,
  Layers,
  RefreshCw,
  Check,
} from 'lucide-react';
import { useAuth } from '@/lib/auth';
import { UserRole } from '@/types';

type Intent = 'buy' | 'sell' | 'both';

const INTENT_OPTIONS: { id: Intent; label: string; description: string; role: UserRole; icon: React.ReactNode }[] = [
  {
    id: 'buy',
    label: 'Buy Materials',
    description: 'Source qualified secondary materials. Browse listings, submit RFQs, and manage buyer requirements.',
    role: 'buyer',
    icon: <ShoppingCart size={22} />,
  },
  {
    id: 'sell',
    label: 'Sell Byproducts',
    description: 'List industrial byproducts for circular reuse. Register lots, run ProofPath qualification, and publish listings.',
    role: 'seller',
    icon: <Layers size={22} />,
  },
  {
    id: 'both',
    label: 'Buy & Sell',
    description: 'Operate as both a materials buyer and a byproduct generator. Start as a facility operator.',
    role: 'facility_operator',
    icon: <RefreshCw size={22} />,
  },
];

export default function RegisterPage() {
  return (
    <React.Suspense
      fallback={
        <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: 'var(--bg-canvas)' }}>
          <Loader2 size={24} className="animate-spin" />
        </div>
      }
    >
      <RegisterContent />
    </React.Suspense>
  );
}

function RegisterContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { register } = useAuth();

  // Two-step: step 1 = intent, step 2 = account details
  const [step, setStep] = useState<1 | 2>(1);
  const [intent, setIntent] = useState<Intent>('buy');

  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [orgName, setOrgName] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Pre-select intent from URL param ?intent=buy|sell
  useEffect(() => {
    const param = searchParams.get('intent');
    if (param === 'buy' || param === 'sell' || param === 'both') {
      setIntent(param);
    }
  }, [searchParams]);

  const selectedOption = INTENT_OPTIONS.find((o) => o.id === intent)!;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!name.trim()) { setError('Please enter your full name.'); return; }
    if (!email || !email.includes('@')) { setError('Please enter a valid work email.'); return; }
    if (!orgName.trim()) { setError('Please enter your organization name.'); return; }
    if (!password || password.length < 6) { setError('Password must be at least 6 characters.'); return; }
    if (password !== confirmPassword) { setError('Passwords do not match.'); return; }

    setIsLoading(true);
    try {
      await register(name, email, selectedOption.role);
      router.push('/onboarding');
    } catch (err: any) {
      setError(err?.message || 'Registration failed. Please check your inputs.');
      setIsLoading(false);
    }
  };

  return (
    <div style={{ minHeight: '100vh', backgroundColor: 'var(--bg-canvas)', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <header style={{ height: '56px', backgroundColor: '#ffffff', borderBottom: '1px solid var(--border-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 1.5rem' }}>
        <Link href="/" style={{ display: 'flex', alignItems: 'center', gap: '0.625rem', textDecoration: 'none' }}>
          <div style={{ width: '28px', height: '28px', borderRadius: '6px', backgroundColor: 'var(--primary)', color: '#ffffff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: '0.875rem' }}>S</div>
          <span style={{ fontSize: '1rem', fontWeight: 700, letterSpacing: '0.05em', color: 'var(--text-primary)' }}>STRATA</span>
        </Link>

        {/* Step indicator */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
          {[1, 2].map((s) => (
            <React.Fragment key={s}>
              {s > 1 && <div style={{ width: '24px', height: '1px', backgroundColor: 'var(--border-strong)' }} />}
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem' }}>
                <span style={{
                  width: '22px', height: '22px', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: '0.6875rem', fontWeight: 700,
                  backgroundColor: step === s ? 'var(--primary-container)' : step > s ? 'var(--status-success)' : 'var(--bg-subtle)',
                  color: step >= s ? '#ffffff' : 'var(--text-muted)',
                }}>
                  {step > s ? <Check size={12} /> : s}
                </span>
                <span style={{ fontSize: '0.75rem', fontWeight: 500, color: step === s ? 'var(--primary)' : 'var(--text-muted)', display: 'none' }}>
                  {s === 1 ? 'Your Goal' : 'Account'}
                </span>
              </div>
            </React.Fragment>
          ))}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Already registered?</span>
          <Link href="/login" className="clay-btn clay-btn-secondary" style={{ padding: '0.35rem 0.75rem', fontSize: '0.75rem' }}>Sign In</Link>
        </div>
      </header>

      <main style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', padding: '2rem 1.5rem' }}>
        <div style={{ maxWidth: '640px', width: '100%', margin: '0 auto' }}>

          {/* Step 1: Intent Selection */}
          {step === 1 && (
            <div>
              <div style={{ marginBottom: '2rem', textAlign: 'center' }}>
                <span className="label-compact" style={{ color: 'var(--accent-teal)' }}>Step 1 of 2</span>
                <h1 className="font-serif" style={{ fontSize: '1.875rem', fontWeight: 500, color: 'var(--primary)', marginTop: '0.375rem', letterSpacing: '-0.015em' }}>
                  What brings you to STRATA?
                </h1>
                <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginTop: '0.5rem' }}>
                  Your selection shapes your default dashboard and onboarding experience.
                </p>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.875rem', marginBottom: '1.5rem' }}>
                {INTENT_OPTIONS.map((opt) => {
                  const isSelected = intent === opt.id;
                  return (
                    <div
                      key={opt.id}
                      onClick={() => setIntent(opt.id)}
                      className={`clay-card-interactive ${isSelected ? 'clay-card-selected' : ''}`}
                      style={{ padding: '1.125rem 1.25rem', display: 'flex', alignItems: 'center', gap: '1rem' }}
                    >
                      <div style={{
                        width: '44px', height: '44px', borderRadius: '10px', flexShrink: 0,
                        backgroundColor: isSelected ? 'var(--primary-container)' : 'var(--bg-subtle)',
                        color: isSelected ? '#ffffff' : 'var(--text-primary)',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                      }}>
                        {opt.icon}
                      </div>
                      <div style={{ flex: 1 }}>
                        <div style={{ fontWeight: 600, fontSize: '0.9375rem', color: 'var(--text-primary)', marginBottom: '0.25rem' }}>{opt.label}</div>
                        <div style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', lineHeight: 1.4 }}>{opt.description}</div>
                      </div>
                      <div style={{
                        width: '20px', height: '20px', borderRadius: '50%', flexShrink: 0,
                        border: isSelected ? '6px solid var(--primary-container)' : '2px solid var(--border-strong)',
                        backgroundColor: '#ffffff',
                        transition: 'all 0.15s ease',
                      }} />
                    </div>
                  );
                })}
              </div>

              <button
                onClick={() => setStep(2)}
                className="clay-btn clay-btn-primary"
                style={{ width: '100%', padding: '0.6875rem', fontSize: '0.875rem' }}
              >
                <span>Continue as {selectedOption.label}</span>
                <ArrowRight size={16} />
              </button>

              <p style={{ textAlign: 'center', fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '1rem' }}>
                You can add additional roles after registration in Settings.
              </p>
            </div>
          )}

          {/* Step 2: Account Details */}
          {step === 2 && (
            <div>
              <div style={{ marginBottom: '1.75rem' }}>
                <button onClick={() => setStep(1)} style={{ background: 'none', border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.375rem', color: 'var(--text-muted)', fontSize: '0.8125rem', marginBottom: '1rem', padding: 0 }}>
                  <ArrowLeft size={14} />
                  Change goal
                </button>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                  <span className="label-compact" style={{ color: 'var(--accent-teal)' }}>Step 2 of 2</span>
                  <span className="strata-badge strata-badge-teal">{selectedOption.label}</span>
                </div>
                <h1 style={{ fontSize: '1.375rem', fontWeight: 700, color: 'var(--primary)', marginBottom: '0.25rem' }}>
                  Create your account
                </h1>
                <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
                  Your credentials to access STRATA. You'll configure your organization and facility in the next step.
                </p>
              </div>

              <div className="clay-card" style={{ padding: '1.75rem', backgroundColor: '#ffffff' }}>
                {error && (
                  <div style={{ padding: '0.75rem', borderRadius: '8px', backgroundColor: 'var(--status-error-bg)', border: '1px solid rgba(166,58,53,0.25)', color: 'var(--status-error)', fontSize: '0.8125rem', display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
                    <AlertCircle size={16} />
                    <span>{error}</span>
                  </div>
                )}

                <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                  {/* Name */}
                  <div>
                    <label htmlFor="name" className="label-compact" style={{ display: 'block', marginBottom: '0.375rem' }}>
                      Full Name <span style={{ color: 'var(--status-error)' }}>*</span>
                    </label>
                    <div style={{ position: 'relative' }}>
                      <User size={15} style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                      <input id="name" type="text" required value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Dr. Hélène Vance" className="clay-input" style={{ paddingLeft: '2.25rem' }} />
                    </div>
                  </div>

                  {/* Email */}
                  <div>
                    <label htmlFor="email" className="label-compact" style={{ display: 'block', marginBottom: '0.375rem' }}>
                      Work Email <span style={{ color: 'var(--status-error)' }}>*</span>
                    </label>
                    <div style={{ position: 'relative' }}>
                      <Mail size={15} style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                      <input id="email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@yourcompany.com" className="clay-input" style={{ paddingLeft: '2.25rem' }} />
                    </div>
                  </div>

                  {/* Org */}
                  <div>
                    <label htmlFor="orgName" className="label-compact" style={{ display: 'block', marginBottom: '0.375rem' }}>
                      Organization Name <span style={{ color: 'var(--status-error)' }}>*</span>
                    </label>
                    <div style={{ position: 'relative' }}>
                      <Building2 size={15} style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                      <input id="orgName" type="text" required value={orgName} onChange={(e) => setOrgName(e.target.value)} placeholder="Nordic Smelting AG" className="clay-input" style={{ paddingLeft: '2.25rem' }} />
                    </div>
                  </div>

                  {/* Password */}
                  <div>
                    <label htmlFor="password" className="label-compact" style={{ display: 'block', marginBottom: '0.375rem' }}>
                      Password <span style={{ color: 'var(--status-error)' }}>*</span>
                    </label>
                    <div style={{ position: 'relative' }}>
                      <Lock size={15} style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                      <input id="password" type="password" required value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Min. 6 characters" className="clay-input" style={{ paddingLeft: '2.25rem' }} />
                    </div>
                  </div>

                  {/* Confirm Password */}
                  <div>
                    <label htmlFor="confirmPassword" className="label-compact" style={{ display: 'block', marginBottom: '0.375rem' }}>
                      Confirm Password <span style={{ color: 'var(--status-error)' }}>*</span>
                    </label>
                    <div style={{ position: 'relative' }}>
                      <Lock size={15} style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                      <input id="confirmPassword" type="password" required value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} placeholder="Re-enter password" className="clay-input" style={{ paddingLeft: '2.25rem' }} />
                    </div>
                  </div>

                  <button type="submit" disabled={isLoading} className="clay-btn clay-btn-primary" style={{ width: '100%', padding: '0.6875rem', fontSize: '0.875rem', marginTop: '0.5rem' }}>
                    {isLoading ? (
                      <><Loader2 size={16} className="animate-spin" /><span>Creating Account…</span></>
                    ) : (
                      <><span>Create Account & Continue</span><ArrowRight size={16} /></>
                    )}
                  </button>
                </form>
              </div>

              <p style={{ textAlign: 'center', fontSize: '0.6875rem', color: 'var(--text-muted)', marginTop: '1rem', lineHeight: 1.5 }}>
                By registering you agree to STRATA's data custody framework.<br />
                Organization and facility details collected in the next onboarding step.
              </p>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
