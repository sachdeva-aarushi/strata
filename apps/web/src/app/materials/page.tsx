'use client';

import React, { Suspense, useEffect, useState } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import {
  Layers,
  Plus,
  Search,
  Filter,
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  X,
  Loader2,
  ExternalLink,
  ChevronRight,
  Sparkles,
} from 'lucide-react';
import { AppShell } from '@/components/AppShell';
import { Badge } from '@/components/Badge';
import { api } from '@/lib/api-client';
import { useAuth } from '@/lib/auth';
import {
  MaterialLot,
  MaterialLotCreate,
  MaterialLotStatus,
  MaterialTypeInfo,
} from '@/types';
import { formatDate, formatNumber } from '@/lib/utils';

export default function MaterialsPage() {
  return (
    <Suspense fallback={<div style={{ padding: '2rem', textAlign: 'center' }}>Loading Materials Registry...</div>}>
      <MaterialsContent />
    </Suspense>
  );
}

function MaterialsContent() {

  const { user } = useAuth();
  const searchParams = useSearchParams();

  const [lots, setLots] = useState<MaterialLot[]>([]);
  const [types, setTypes] = useState<MaterialTypeInfo[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedLot, setSelectedLot] = useState<MaterialLot | null>(null);

  // Filters
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [typeFilter, setTypeFilter] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Register Lot Modal
  const [modalOpen, setModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [formSuccess, setFormSuccess] = useState<string | null>(null);

  // Form State
  const [materialType, setMaterialType] = useState('ti-6al-4v-swarf');
  const [quantity, setQuantity] = useState<number>(12.5);
  const [unit, setUnit] = useState('tonne');
  const [availFrom, setAvailFrom] = useState(new Date().toISOString().split('T')[0]);
  const [availTo, setAvailTo] = useState(
    new Date(Date.now() + 30 * 24 * 3600 * 1000).toISOString().split('T')[0]
  );
  const [composition, setComposition] = useState('Ti 90%, Al 6%, V 4%');
  const [physicalForm, setPhysicalForm] = useState('swarf_shavings');
  const [moisturePct, setMoisturePct] = useState<number>(0.8);

  // Open modal if URL has ?action=new
  useEffect(() => {
    if (searchParams?.get('action') === 'new') {
      setModalOpen(true);
    }
  }, [searchParams]);

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [lotsRes, typesRes] = await Promise.all([
        api.materials.listLots({
          status: statusFilter || undefined,
          material_type: typeFilter || undefined,
        }),
        api.materials.getTypes(),
      ]);

      setLots(lotsRes.data || []);
      setTypes(typesRes.data || []);
      if (lotsRes.data && lotsRes.data.length > 0 && !selectedLot) {
        setSelectedLot(lotsRes.data[0]);
      }
    } catch (err) {
      console.warn('Failed to load materials registry data:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [statusFilter, typeFilter]);

  const handleRegisterLot = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    setFormSuccess(null);

    if (!quantity || quantity <= 0) {
      setFormError('Quantity must be greater than zero.');
      return;
    }

    setIsSubmitting(true);
    try {
      const payload: MaterialLotCreate = {
        material_type: materialType,
        quantity,
        unit,
        facility_id: user?.facility_id || '00000000-0000-0000-0000-000000000010',
        availability_from: availFrom,
        availability_to: availTo || null,
        declared_attributes: {
          composition,
          physical_form: physicalForm,
          moisture_pct: moisturePct,
        },
        status: 'available',
      };

      const res = await api.materials.createLot(payload);
      setFormSuccess(`Material lot ${res.data.lot_id} successfully registered!`);

      // Refresh table
      await loadData();
      setSelectedLot(res.data);

      setTimeout(() => {
        setModalOpen(false);
        setFormSuccess(null);
      }, 1200);
    } catch (err: any) {
      setFormError(err?.message || 'Failed to register material lot with backend.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const filteredLots = lots.filter((lot) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      lot.material_type.toLowerCase().includes(q) ||
      lot.lot_id.toLowerCase().includes(q) ||
      lot.status.toLowerCase().includes(q)
    );
  });

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
      default:
        return <Badge variant="neutral">{status.replace('_', ' ')}</Badge>;
    }
  };

  return (
    <AppShell>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
        {/* Header Bar */}
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
                Physical Feedstock Registry
              </span>
              <span style={{ color: 'var(--text-muted)' }}>·</span>
              <span className="label-compact" style={{ color: 'var(--text-muted)' }}>
                EU 1013/2006 &amp; VVEA Compliant
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
              Industrial Material Registry
            </h1>
            <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
              Canonical lots registered at facility <strong>{user?.facility_name}</strong>.
            </p>
          </div>

          <button
            onClick={() => setModalOpen(true)}
            className="clay-btn clay-btn-primary"
            style={{ gap: '0.5rem' }}
          >
            <Plus size={16} />
            <span>Register Material Lot</span>
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
            gap: '0.75rem',
            justifyContent: 'space-between',
          }}
        >
          {/* Search box */}
          <div style={{ position: 'relative', minWidth: '240px', flex: 1 }}>
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
              placeholder="Search lot UUID or taxonomy type..."
              className="clay-input"
              style={{ paddingLeft: '2.25rem' }}
            />
          </div>

          {/* Type filter */}
          <div style={{ width: '220px' }}>
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="clay-select"
            >
              <option value="">All Taxonomy Types</option>
              {types.map((t) => (
                <option key={t.type_id} value={t.type_id}>
                  {t.name} ({t.category})
                </option>
              ))}
            </select>
          </div>

          {/* Status filter */}
          <div style={{ width: '180px' }}>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="clay-select"
            >
              <option value="">All Statuses</option>
              <option value="available">Available</option>
              <option value="draft">Draft</option>
              <option value="under_qualification">Under Qualification</option>
              <option value="listed">Listed on Exchange</option>
              <option value="matched">Matched</option>
            </select>
          </div>
        </div>

        {/* Main Content Layout: Table + Detail Inspector */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: selectedLot ? '1fr 340px' : '1fr',
            gap: '1.25rem',
            alignItems: 'start',
          }}
        >
          {/* Table Container */}
          <div className="strata-table-container">
            <table className="strata-table">
              <thead>
                <tr>
                  <th>Material Stream</th>
                  <th>Quantity</th>
                  <th>Status</th>
                  <th>Availability</th>
                  <th>Facility Node</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {isLoading ? (
                  <tr>
                    <td colSpan={6} style={{ textAlign: 'center', padding: '2rem' }}>
                      <Loader2 size={20} className="animate-spin" style={{ margin: '0 auto' }} />
                    </td>
                  </tr>
                ) : filteredLots.length === 0 ? (
                  <tr>
                    <td
                      colSpan={6}
                      style={{
                        textAlign: 'center',
                        padding: '3rem 1rem',
                        color: 'var(--text-muted)',
                      }}
                    >
                      <Layers size={32} style={{ margin: '0 auto 0.5rem auto', opacity: 0.5 }} />
                      <div style={{ fontWeight: 600 }}>No material lots found</div>
                      <div style={{ fontSize: '0.75rem', marginTop: '0.25rem' }}>
                        Register your first material lot to start tracking mass-balance circularity.
                      </div>
                    </td>
                  </tr>
                ) : (
                  filteredLots.map((lot) => {
                    const isSelected = selectedLot?.lot_id === lot.lot_id;
                    return (
                      <tr
                        key={lot.lot_id}
                        onClick={() => setSelectedLot(lot)}
                        style={{
                          backgroundColor: isSelected ? 'var(--bg-subtle)' : undefined,
                          cursor: 'pointer',
                        }}
                      >
                        <td>
                          <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                            {lot.material_type}
                          </div>
                          <div
                            style={{
                              fontSize: '0.6875rem',
                              fontFamily: 'monospace',
                              color: 'var(--text-muted)',
                            }}
                          >
                            {lot.lot_id.slice(0, 16)}...
                          </div>
                        </td>

                        <td className="tnum">
                          <strong>{formatNumber(lot.quantity)}</strong> {lot.unit}
                        </td>

                        <td>{getStatusBadge(lot.status)}</td>

                        <td>
                          <div className="tnum" style={{ fontSize: '0.75rem' }}>
                            {formatDate(lot.availability_from)}
                          </div>
                          {lot.availability_to && (
                            <div
                              className="tnum"
                              style={{ fontSize: '0.6875rem', color: 'var(--text-muted)' }}
                            >
                              until {formatDate(lot.availability_to)}
                            </div>
                          )}
                        </td>

                        <td>
                          <span
                            className="label-compact"
                            style={{
                              padding: '0.15rem 0.4rem',
                              backgroundColor: 'var(--bg-subtle)',
                              borderRadius: '4px',
                            }}
                          >
                            Site #4
                          </span>
                        </td>

                        <td>
                          <Link
                            href={`/proofpath?lot_id=${lot.lot_id}`}
                            className="clay-btn clay-btn-secondary"
                            style={{
                              padding: '0.25rem 0.5rem',
                              fontSize: '0.6875rem',
                              textDecoration: 'none',
                              gap: '0.25rem',
                            }}
                            onClick={(e) => e.stopPropagation()}
                          >
                            <ShieldCheck size={12} color="var(--primary-container)" />
                            <span>Qualify</span>
                          </Link>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>

          {/* Right side Inspector Drawer */}
          {selectedLot && (
            <div
              className="clay-card"
              style={{
                padding: '1.25rem',
                backgroundColor: '#ffffff',
                display: 'flex',
                flexDirection: 'column',
                gap: '1rem',
              }}
            >
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  paddingBottom: '0.75rem',
                  borderBottom: '1px solid var(--border-subtle)',
                }}
              >
                <div>
                  <span className="label-compact">Lot Dossier</span>
                  <h3 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                    {selectedLot.material_type}
                  </h3>
                </div>
                <button
                  onClick={() => setSelectedLot(null)}
                  className="clay-btn-ghost"
                  style={{ padding: '4px' }}
                >
                  <X size={16} />
                </button>
              </div>

              {/* Status and UUID */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span className="label-compact">Current State</span>
                {getStatusBadge(selectedLot.status)}
              </div>

              <div>
                <span className="label-compact" style={{ display: 'block', marginBottom: '0.25rem' }}>
                  Canonical Lot UUID
                </span>
                <span
                  style={{
                    fontFamily: 'monospace',
                    fontSize: '0.75rem',
                    color: 'var(--text-secondary)',
                    wordBreak: 'break-all',
                    backgroundColor: 'var(--bg-subtle)',
                    padding: '0.375rem 0.5rem',
                    borderRadius: '4px',
                    display: 'block',
                  }}
                >
                  {selectedLot.lot_id}
                </span>
              </div>

              {/* Quantities */}
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: '1fr 1fr',
                  gap: '0.5rem',
                  padding: '0.75rem',
                  borderRadius: '6px',
                  backgroundColor: 'var(--bg-subtle)',
                }}
              >
                <div>
                  <span className="label-compact">Net Quantity</span>
                  <div className="tnum" style={{ fontSize: '1.125rem', fontWeight: 700 }}>
                    {formatNumber(selectedLot.quantity)} {selectedLot.unit}
                  </div>
                </div>
                <div>
                  <span className="label-compact">Provenance</span>
                  <div style={{ fontSize: '0.8125rem', fontWeight: 600, textTransform: 'capitalize' }}>
                    {selectedLot.provenance_label?.replace('_', ' ') || 'User Supplied'}
                  </div>
                </div>
              </div>

              {/* Declared Attributes */}
              <div>
                <span className="label-compact" style={{ display: 'block', marginBottom: '0.5rem' }}>
                  Declared Attributes
                </span>
                <div
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '0.375rem',
                    fontSize: '0.75rem',
                  }}
                >
                  {Object.entries(selectedLot.declared_attributes || {}).map(([k, v]) => (
                    <div
                      key={k}
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        padding: '0.25rem 0',
                        borderBottom: '1px dotted var(--border-subtle)',
                      }}
                    >
                      <span style={{ color: 'var(--text-muted)', textTransform: 'capitalize' }}>
                        {k.replace('_', ' ')}:
                      </span>
                      <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                        {String(v)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Action buttons */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginTop: '0.5rem' }}>
                <Link
                  href={`/proofpath?lot_id=${selectedLot.lot_id}`}
                  className="clay-btn clay-btn-primary"
                  style={{ width: '100%', fontSize: '0.8125rem' }}
                >
                  <ShieldCheck size={16} />
                  <span>Run Qualification Assessment</span>
                </Link>

                <Link
                  href={`/exchange?action=create_listing&lot_id=${selectedLot.lot_id}`}
                  className="clay-btn clay-btn-secondary"
                  style={{ width: '100%', fontSize: '0.8125rem' }}
                >
                  <span>Publish to Circular Exchange</span>
                </Link>
              </div>
            </div>
          )}
        </div>

        {/* REGISTER MATERIAL LOT MODAL DIALOG */}
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
                maxWidth: '560px',
                backgroundColor: '#ffffff',
                padding: '2rem',
                maxHeight: '90vh',
                overflowY: 'auto',
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
                    Statutory Entry
                  </span>
                  <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--primary)' }}>
                    Register Material Lot
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

              {formError && (
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
                  <span>{formError}</span>
                </div>
              )}

              {formSuccess && (
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
                  <span>{formSuccess}</span>
                </div>
              )}

              <form onSubmit={handleRegisterLot} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <div>
                  <label className="label-compact" style={{ display: 'block', marginBottom: '0.375rem' }}>
                    Taxonomy Material Type <span style={{ color: 'var(--status-error)' }}>*</span>
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
                      Measured Quantity <span style={{ color: 'var(--status-error)' }}>*</span>
                    </label>
                    <input
                      type="number"
                      step="0.01"
                      required
                      value={quantity}
                      onChange={(e) => setQuantity(parseFloat(e.target.value) || 0)}
                      placeholder="12.5"
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
                      <option value="unit">unit</option>
                    </select>
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                  <div>
                    <label className="label-compact" style={{ display: 'block', marginBottom: '0.375rem' }}>
                      Available From <span style={{ color: 'var(--status-error)' }}>*</span>
                    </label>
                    <input
                      type="date"
                      required
                      value={availFrom}
                      onChange={(e) => setAvailFrom(e.target.value)}
                      className="clay-input"
                    />
                  </div>
                  <div>
                    <label className="label-compact" style={{ display: 'block', marginBottom: '0.375rem' }}>
                      Available Until
                    </label>
                    <input
                      type="date"
                      value={availTo}
                      onChange={(e) => setAvailTo(e.target.value)}
                      className="clay-input"
                    />
                  </div>
                </div>

                <div>
                  <label className="label-compact" style={{ display: 'block', marginBottom: '0.375rem' }}>
                    Chemical Composition Assay
                  </label>
                  <input
                    type="text"
                    value={composition}
                    onChange={(e) => setComposition(e.target.value)}
                    placeholder="Ti 90%, Al 6%, V 4%"
                    className="clay-input"
                  />
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                  <div>
                    <label className="label-compact" style={{ display: 'block', marginBottom: '0.375rem' }}>
                      Physical Form
                    </label>
                    <input
                      type="text"
                      value={physicalForm}
                      onChange={(e) => setPhysicalForm(e.target.value)}
                      placeholder="swarf_shavings"
                      className="clay-input"
                    />
                  </div>
                  <div>
                    <label className="label-compact" style={{ display: 'block', marginBottom: '0.375rem' }}>
                      Moisture (%)
                    </label>
                    <input
                      type="number"
                      step="0.1"
                      value={moisturePct}
                      onChange={(e) => setMoisturePct(parseFloat(e.target.value) || 0)}
                      placeholder="0.8"
                      className="clay-input"
                    />
                  </div>
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
                    style={{ minWidth: '140px' }}
                  >
                    {isSubmitting ? (
                      <>
                        <Loader2 size={16} className="animate-spin" />
                        <span>Registering...</span>
                      </>
                    ) : (
                      <>
                        <Plus size={16} />
                        <span>Register Lot</span>
                      </>
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
