'use client';

import React, { Suspense, useEffect, useState } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import {
  ShoppingBag,
  Plus,
  Search,
  Trash2,
  Sparkles,
  ArrowRight,
  MapPin,
  CheckCircle2,
  AlertCircle,
  X,
  Loader2,
  Layers,
} from 'lucide-react';
import { AppShell } from '@/components/AppShell';
import { Badge } from '@/components/Badge';
import { api } from '@/lib/api-client';
import { useAuth } from '@/lib/auth';
import { BuyerRequirement, MaterialTypeInfo } from '@/types';
import { formatDate, formatNumber } from '@/lib/utils';

export default function BuyerRequirementsPage() {
  return (
    <Suspense fallback={<div style={{ padding: '2rem', textAlign: 'center' }}>Loading Buyer Requirements...</div>}>
      <BuyerRequirementsContent />
    </Suspense>
  );
}

function BuyerRequirementsContent() {
  const { user } = useAuth();
  const searchParams = useSearchParams();

  const [requirements, setRequirements] = useState<BuyerRequirement[]>([]);
  const [types, setTypes] = useState<MaterialTypeInfo[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');

  // Modal State
  const [modalOpen, setModalOpen] = useState(false);
  const [materialType, setMaterialType] = useState('ti-6al-4v-swarf');
  const [targetQuantity, setTargetQuantity] = useState<number>(25);
  const [unit, setUnit] = useState('tonne');
  const [maxPrice, setMaxPrice] = useState<number>(475);
  const [country, setCountry] = useState('CH');
  const [notes, setNotes] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [reqsRes, typesRes] = await Promise.all([
        api.exchange.listRequirements({ page_size: 50 }),
        api.materials.getTypes().catch(() => ({ data: [] })),
      ]);
      setRequirements(reqsRes.data || []);
      setTypes(typesRes.data || []);
    } catch (err) {
      console.warn('Failed to load buyer requirements:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleCreateRequirement = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    if (!targetQuantity || targetQuantity <= 0) {
      setError('Target quantity must be greater than zero.');
      return;
    }

    setIsSubmitting(true);
    try {
      const res = await api.exchange.createRequirement({
        material_type: materialType,
        target_quantity: targetQuantity,
        unit,
        max_price_per_unit: maxPrice || undefined,
        delivery_location_country: country,
        notes: notes || undefined,
      });

      setSuccess('Buyer feedstock requirement recorded successfully!');
      await loadData();

      setTimeout(() => {
        setModalOpen(false);
        setSuccess(null);
      }, 1000);
    } catch (err: any) {
      setError(err?.message || 'Failed to record buyer requirement.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteRequirement = async (id: string) => {
    if (!confirm('Are you sure you want to deactivate this requirement?')) return;
    try {
      await api.exchange.deleteRequirement(id);
      await loadData();
    } catch (err: any) {
      alert(err?.message || 'Failed to delete buyer requirement.');
    }
  };

  const filteredRequirements = requirements.filter((req) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      (req.material_type ?? '').toLowerCase().includes(q) ||
      req.requirement_id.toLowerCase().includes(q) ||
      (req.delivery_location_country && req.delivery_location_country.toLowerCase().includes(q))
    );
  });

  return (
    <AppShell>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
        {/* Header */}
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
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
              <span className="label-compact" style={{ color: 'var(--accent-teal)' }}>
                Feedstock Procurement Demand
              </span>
              <span style={{ color: 'var(--text-muted)' }}>·</span>
              <span className="label-compact" style={{ color: 'var(--text-muted)' }}>
                Bilateral &amp; Cluster Matching
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
              Buyer Requirements Console
            </h1>
            <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
              Manage material feedstock specifications, target volumes, and budget ceilings for <strong>{user?.org_name || 'Your Organization'}</strong>.
            </p>
          </div>

          <button
            onClick={() => setModalOpen(true)}
            className="clay-btn clay-btn-primary"
            style={{ gap: '0.5rem' }}
          >
            <Plus size={16} />
            <span>Record Requirement</span>
          </button>
        </div>

        {/* Filter and Search Bar */}
        <div
          className="clay-card"
          style={{
            padding: '0.875rem 1rem',
            backgroundColor: '#ffffff',
            display: 'flex',
            flexWrap: 'wrap',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '1rem',
          }}
        >
          <div style={{ position: 'relative', minWidth: '260px', flex: 1 }}>
            <Search
              size={16}
              style={{
                position: 'absolute',
                left: '0.75rem',
                top: '50%',
                transform: 'translateY(-50%)',
                color: 'var(--text-muted)',
              }}
            />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search material type or country..."
              className="clay-input"
              style={{ paddingLeft: '2.25rem' }}
            />
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span className="label-compact" style={{ color: 'var(--text-muted)' }}>
              Total Demands:
            </span>
            <span className="tnum" style={{ fontWeight: 700, fontSize: '0.875rem' }}>
              {requirements.length}
            </span>
          </div>
        </div>

        {/* Table Container */}
        <div className="strata-table-container">
          <table className="strata-table">
            <thead>
              <tr>
                <th>Required Material Type</th>
                <th>Target Demand</th>
                <th>Max Budget</th>
                <th>Delivery Country</th>
                <th>Status</th>
                <th>Created</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan={7} style={{ textAlign: 'center', padding: '2.5rem' }}>
                    <Loader2 size={24} className="animate-spin" style={{ margin: '0 auto' }} />
                  </td>
                </tr>
              ) : filteredRequirements.length === 0 ? (
                <tr>
                  <td
                    colSpan={7}
                    style={{
                      textAlign: 'center',
                      padding: '3rem 1rem',
                      color: 'var(--text-muted)',
                    }}
                  >
                    <ShoppingBag size={32} style={{ margin: '0 auto 0.5rem auto', opacity: 0.4 }} />
                    <div style={{ fontWeight: 600 }}>No buyer requirements registered</div>
                    <div style={{ fontSize: '0.75rem', marginTop: '0.25rem' }}>
                      Publish material specifications to enable algorithmic and ProofPath matching across active lots.
                    </div>
                  </td>
                </tr>
              ) : (
                filteredRequirements.map((req) => (
                  <tr key={req.requirement_id}>
                    <td>
                      <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                        {req.material_type}
                      </div>
                      <div
                        style={{
                          fontSize: '0.6875rem',
                          fontFamily: 'monospace',
                          color: 'var(--text-muted)',
                        }}
                      >
                        {req.requirement_id.slice(0, 16)}...
                      </div>
                    </td>

                    <td className="tnum">
                      <strong>{formatNumber(req.target_quantity)}</strong> {req.unit}
                    </td>

                    <td className="tnum">
                      {req.max_price_per_unit ? (
                        <span>${req.max_price_per_unit}/{req.unit}</span>
                      ) : (
                        <span style={{ color: 'var(--text-muted)' }}>Market Index</span>
                      )}
                    </td>

                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', fontSize: '0.75rem' }}>
                        <MapPin size={12} color="var(--text-muted)" />
                        <span>{req.delivery_location_country || 'CH'}</span>
                      </div>
                    </td>

                    <td>
                      <Badge variant="success" dot>
                        {req.status}
                      </Badge>
                    </td>

                    <td className="tnum" style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      {formatDate(req.created_at)}
                    </td>

                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <Link
                          href={`/matching?requirement_id=${req.requirement_id}`}
                          className="clay-btn clay-btn-primary"
                          style={{
                            padding: '0.25rem 0.625rem',
                            fontSize: '0.6875rem',
                            textDecoration: 'none',
                            gap: '0.25rem',
                          }}
                        >
                          <Sparkles size={12} />
                          <span>Match Candidates</span>
                        </Link>

                        <button
                          onClick={() => handleDeleteRequirement(req.requirement_id)}
                          className="clay-btn-ghost"
                          style={{
                            padding: '0.25rem',
                            color: 'var(--status-error)',
                            borderRadius: '4px',
                          }}
                          title="Archive Requirement"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* MODAL: RECORD REQUIREMENT */}
        {modalOpen && (
          <div
            style={{
              position: 'fixed',
              inset: 0,
              zIndex: 50,
              backgroundColor: 'rgba(18, 52, 32, 0.4)',
              backdropFilter: 'blur(3px)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              padding: '1rem',
            }}
          >
            <div
              className="clay-card"
              style={{
                width: '100%',
                maxWidth: '520px',
                backgroundColor: '#ffffff',
                padding: '2rem',
                position: 'relative',
              }}
            >
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  paddingBottom: '1rem',
                  borderBottom: '1px solid var(--border-subtle)',
                  marginBottom: '1.25rem',
                }}
              >
                <div>
                  <span className="label-compact" style={{ color: 'var(--accent-teal)' }}>
                    Procurement Intent
                  </span>
                  <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--primary)' }}>
                    Record Buyer Requirement
                  </h2>
                </div>
                <button
                  onClick={() => setModalOpen(false)}
                  className="clay-btn-ghost"
                  style={{ padding: '4px' }}
                >
                  <X size={18} />
                </button>
              </div>

              {error && (
                <div
                  style={{
                    padding: '0.75rem',
                    borderRadius: '6px',
                    backgroundColor: 'var(--status-error-bg)',
                    color: 'var(--status-error)',
                    fontSize: '0.8125rem',
                    marginBottom: '1rem',
                  }}
                >
                  {error}
                </div>
              )}

              {success && (
                <div
                  style={{
                    padding: '0.75rem',
                    borderRadius: '6px',
                    backgroundColor: 'var(--status-success-bg)',
                    color: 'var(--status-success)',
                    fontSize: '0.8125rem',
                    marginBottom: '1rem',
                  }}
                >
                  {success}
                </div>
              )}

              <form onSubmit={handleCreateRequirement} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <div>
                  <label className="label-compact" style={{ display: 'block', marginBottom: '0.375rem' }}>
                    Required Material Specification <span style={{ color: 'var(--status-error)' }}>*</span>
                  </label>
                  <select
                    value={materialType}
                    onChange={(e) => setMaterialType(e.target.value)}
                    className="clay-select"
                    required
                  >
                    {types.map((t) => (
                      <option key={t.type_id} value={t.type_id}>
                        {t.name} ({t.category})
                      </option>
                    ))}
                    {types.length === 0 && (
                      <>
                        <option value="ti-6al-4v-swarf">Titanium Ti-6Al-4V Secondary Swarf</option>
                        <option value="al-6061-offcuts">Aluminum 6061 Clean Offcuts</option>
                        <option value="cu-millberry">Copper Millberry Wire Scrap</option>
                      </>
                    )}
                  </select>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '0.75rem' }}>
                  <div>
                    <label className="label-compact" style={{ display: 'block', marginBottom: '0.375rem' }}>
                      Target Quantity <span style={{ color: 'var(--status-error)' }}>*</span>
                    </label>
                    <input
                      type="number"
                      step="0.1"
                      required
                      value={targetQuantity}
                      onChange={(e) => setTargetQuantity(parseFloat(e.target.value) || 0)}
                      placeholder="25"
                      className="clay-input"
                    />
                  </div>
                  <div>
                    <label className="label-compact" style={{ display: 'block', marginBottom: '0.375rem' }}>
                      Unit <span style={{ color: 'var(--status-error)' }}>*</span>
                    </label>
                    <select
                      value={unit}
                      onChange={(e) => setUnit(e.target.value)}
                      className="clay-select"
                    >
                      <option value="tonne">tonne</option>
                      <option value="kg">kg</option>
                      <option value="litre">litre</option>
                      <option value="m3">m3</option>
                    </select>
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                  <div>
                    <label className="label-compact" style={{ display: 'block', marginBottom: '0.375rem' }}>
                      Max Budget ($/unit)
                    </label>
                    <input
                      type="number"
                      step="0.01"
                      value={maxPrice}
                      onChange={(e) => setMaxPrice(parseFloat(e.target.value) || 0)}
                      placeholder="475"
                      className="clay-input"
                    />
                  </div>
                  <div>
                    <label className="label-compact" style={{ display: 'block', marginBottom: '0.375rem' }}>
                      Delivery Country
                    </label>
                    <input
                      type="text"
                      maxLength={2}
                      value={country}
                      onChange={(e) => setCountry(e.target.value.toUpperCase())}
                      placeholder="CH"
                      className="clay-input"
                    />
                  </div>
                </div>

                <div>
                  <label className="label-compact" style={{ display: 'block', marginBottom: '0.375rem' }}>
                    Specification Notes &amp; Acceptance Thresholds
                  </label>
                  <textarea
                    rows={3}
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    placeholder="Specify maximum iron/silicon impurities, acceptable moisture limits, or required ISO certifications..."
                    className="clay-input"
                    style={{ resize: 'vertical' }}
                  />
                </div>

                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'flex-end',
                    gap: '0.75rem',
                    paddingTop: '0.75rem',
                    borderTop: '1px solid var(--border-subtle)',
                  }}
                >
                  <button
                    type="button"
                    onClick={() => setModalOpen(false)}
                    className="clay-btn clay-btn-ghost"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={isSubmitting}
                    className="clay-btn clay-btn-primary"
                  >
                    {isSubmitting ? (
                      <>
                        <Loader2 size={16} className="animate-spin" />
                        <span>Recording...</span>
                      </>
                    ) : (
                      <span>Save Requirement</span>
                    )}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
