'use client';

import React, { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import {
  ArrowLeft,
  ShieldCheck,
  ShieldAlert,
  ShieldX,
  Layers,
  FileCheck,
  RefreshCw,
  Plus,
  ArrowRight,
  Loader2,
  AlertCircle,
  CheckCircle2,
  Clock,
  ExternalLink,
  ChevronRight,
  X,
  FileText,
  Building2,
  Calendar,
} from 'lucide-react';
import { AppShell } from '@/components/AppShell';
import { Badge } from '@/components/Badge';
import { MetricCard } from '@/components/MetricCard';
import { api } from '@/lib/api-client';
import {
  EvidenceRecord,
  MaterialLot,
  QualificationAssessment,
} from '@/types';
import { formatDate, formatNumber } from '@/lib/utils';

export default function MaterialDetailPage() {
  const params = useParams();
  const router = useRouter();
  const lotId = params?.id as string;

  const [lot, setLot] = useState<MaterialLot | null>(null);
  const [assessments, setAssessments] = useState<QualificationAssessment[]>([]);
  const [evidenceList, setEvidenceList] = useState<EvidenceRecord[]>([]);

  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Evidence modal state
  const [showEvidenceModal, setShowEvidenceModal] = useState(false);
  const [claimType, setClaimType] = useState('chemical_assay');
  const [provenance, setProvenance] = useState('Lab ICP-OES Spectrometry Batch #914');
  const [testStandard, setTestStandard] = useState('ASTM E2371');
  const [certId, setCertId] = useState('CERT-CH-2026-');
  const [submittingEvidence, setSubmittingEvidence] = useState(false);
  const [evidenceSuccess, setEvidenceSuccess] = useState<string | null>(null);
  const [evidenceError, setEvidenceError] = useState<string | null>(null);

  // Assessment trigger state
  const [isAssessing, setIsAssessing] = useState(false);
  const [assessSuccess, setAssessSuccess] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    if (!lotId) return;
    setIsLoading(true);
    setError(null);

    try {
      const [lotRes, assessmentsRes, evidenceRes] = await Promise.all([
        api.materials.getLot(lotId),
        api.qualification.getLotAssessments(lotId).catch(() => ({ data: [] })),
        api.materials.getLotEvidence(lotId).catch(() => ({ data: [] })),
      ]);

      setLot(lotRes.data);
      setAssessments(assessmentsRes.data || []);
      setEvidenceList(evidenceRes.data || []);
    } catch (err: any) {
      setError(err?.message || 'Failed to load material lot details.');
    } finally {
      setIsLoading(false);
    }
  }, [lotId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleCreateEvidence = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!lot) return;
    setEvidenceError(null);
    setEvidenceSuccess(null);
    setSubmittingEvidence(true);

    try {
      await api.materials.createLotEvidence(lot.lot_id, {
        claim_type: claimType,
        provenance,
        verification_status: 'verified',
        data_payload: {
          standard: testStandard,
          certificate_id: certId,
          submitted_at: new Date().toISOString(),
        },
      });

      setEvidenceSuccess('Evidence record attached to lot audit chain.');
      const evRes = await api.materials.getLotEvidence(lot.lot_id);
      setEvidenceList(evRes.data || []);

      setTimeout(() => {
        setShowEvidenceModal(false);
        setEvidenceSuccess(null);
      }, 1200);
    } catch (err: any) {
      setEvidenceError(err?.message || 'Failed to attach evidence record.');
    } finally {
      setSubmittingEvidence(false);
    }
  };

  const handleRunAssessment = async () => {
    if (!lot) return;
    setIsAssessing(true);
    setAssessSuccess(null);
    try {
      await api.qualification.assessLot(lot.lot_id, {
        run_discovery: true,
        notes: 'Manual trigger from Material Detail dossier',
      });
      setAssessSuccess('ProofPath qualification assessment completed.');
      const res = await api.qualification.getLotAssessments(lot.lot_id);
      setAssessments(res.data || []);
    } catch (err: any) {
      setError(err?.message || 'ProofPath assessment failed.');
    } finally {
      setIsAssessing(false);
    }
  };

  const getStatusBadge = (status?: string) => {
    switch (status) {
      case 'available':
        return <Badge variant="success" dot>Available</Badge>;
      case 'listed':
        return <Badge variant="teal" dot>Listed on Exchange</Badge>;
      case 'under_qualification':
        return <Badge variant="warning" dot>Under Qualification</Badge>;
      case 'matched':
        return <Badge variant="teal" dot>Matched with Buyer</Badge>;
      case 'draft':
        return <Badge variant="neutral">Draft</Badge>;
      default:
        return <Badge variant="neutral">{(status || 'unknown').replace(/_/g, ' ')}</Badge>;
    }
  };

  const latestAssessment = assessments[0];

  return (
    <AppShell>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', maxWidth: '1200px' }}>
        {/* Navigation Breadcrumb */}
        <div>
          <Link
            href="/materials"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.375rem',
              fontSize: '0.8125rem',
              color: 'var(--text-muted)',
              textDecoration: 'none',
              marginBottom: '0.75rem',
            }}
          >
            <ArrowLeft size={14} />
            Back to Materials Registry
          </Link>
        </div>

        {/* Loading / Error States */}
        {isLoading ? (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '4rem', color: 'var(--text-muted)', gap: '0.75rem' }}>
            <Loader2 size={24} className="animate-spin" />
            <span>Loading material lot dossier…</span>
          </div>
        ) : error || !lot ? (
          <div className="clay-card" style={{ padding: '2rem', backgroundColor: '#ffffff', textAlign: 'center' }}>
            <AlertCircle size={32} color="var(--status-error)" style={{ margin: '0 auto 0.75rem' }} />
            <h2 style={{ fontSize: '1.125rem', fontWeight: 600, color: 'var(--primary)', marginBottom: '0.375rem' }}>
              Material Lot Unavailable
            </h2>
            <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', marginBottom: '1.25rem' }}>
              {error || `Lot ID "${lotId}" could not be retrieved from the tenant registry.`}
            </p>
            <Link href="/materials" className="clay-btn clay-btn-secondary">
              Return to Registry
            </Link>
          </div>
        ) : (
          <>
            {/* Header Hero Card */}
            <div className="clay-card" style={{ padding: '1.75rem', backgroundColor: '#ffffff' }}>
              <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'flex-start', justifyContent: 'space-between', gap: '1rem' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem', marginBottom: '0.5rem' }}>
                    <span className="label-compact" style={{ color: 'var(--accent-teal)' }}>
                      Secondary Material Lot
                    </span>
                    <span style={{ color: 'var(--text-muted)' }}>·</span>
                    <span className="tnum" style={{ fontFamily: 'monospace', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      {lot.lot_id}
                    </span>
                    {getStatusBadge(lot.status)}
                  </div>

                  <h1 className="font-serif" style={{ fontSize: '1.75rem', fontWeight: 500, color: 'var(--primary)', letterSpacing: '-0.015em' }}>
                    {lot.material_type.replace(/-/g, ' ').toUpperCase()}
                  </h1>

                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1.25rem', marginTop: '0.75rem', fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '0.375rem' }}>
                      <Building2 size={14} color="var(--text-muted)" />
                      Facility: <strong style={{ color: 'var(--text-primary)' }}>{lot.facility_id.slice(0, 13)}…</strong>
                    </span>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '0.375rem' }}>
                      <Calendar size={14} color="var(--text-muted)" />
                      Registered: {formatDate(lot.created_at)}
                    </span>
                    <span>
                      Provenance: <strong style={{ color: 'var(--text-primary)', textTransform: 'capitalize' }}>{lot.provenance_label?.replace(/_/g, ' ') || 'Manufacturer Offcut'}</strong>
                    </span>
                  </div>
                </div>

                {/* Primary Action Buttons */}
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.625rem' }}>
                  <button
                    onClick={handleRunAssessment}
                    disabled={isAssessing}
                    className="clay-btn clay-btn-secondary"
                  >
                    {isAssessing ? (
                      <><Loader2 size={14} className="animate-spin" /><span>Assessing…</span></>
                    ) : (
                      <><ShieldCheck size={14} /><span>Run ProofPath</span></>
                    )}
                  </button>

                  <button
                    onClick={() => setShowEvidenceModal(true)}
                    className="clay-btn clay-btn-secondary"
                  >
                    <Plus size={14} />
                    <span>Attach Evidence</span>
                  </button>

                  <Link
                    href={`/exchange?action=create_listing&lot_id=${lot.lot_id}`}
                    className="clay-btn clay-btn-primary"
                  >
                    <RefreshCw size={14} />
                    <span>List on Exchange</span>
                  </Link>
                </div>
              </div>

              {assessSuccess && (
                <div style={{ marginTop: '1rem', padding: '0.625rem 0.875rem', borderRadius: '6px', backgroundColor: 'var(--status-success-bg)', border: '1px solid rgba(40,99,67,0.25)', color: 'var(--status-success)', fontSize: '0.8125rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <CheckCircle2 size={15} />
                  <span>{assessSuccess}</span>
                </div>
              )}
            </div>

            {/* Quick Metrics */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
              <MetricCard
                label="Physical Volume"
                value={formatNumber(lot.quantity)}
                unit={lot.unit}
                subtext="Mass-balance verified"
                icon={<Layers size={18} />}
              />
              <MetricCard
                label="ProofPath Outcome"
                value={latestAssessment?.outcome || latestAssessment?.status || 'Pending'}
                subtext={latestAssessment ? `${latestAssessment.hard_gate_results?.length || 0} gates audited` : 'Ready for assessment'}
                deltaType={latestAssessment?.outcome === 'supported' ? 'positive' : latestAssessment?.outcome === 'conditional' ? 'neutral' : 'negative'}
                icon={<ShieldCheck size={18} />}
              />
              <MetricCard
                label="Attached Evidence"
                value={evidenceList.length}
                unit="claims"
                subtext="Audit-grade proofs"
                icon={<FileCheck size={18} />}
              />
              <MetricCard
                label="Availability Window"
                value={lot.availability_from ? formatDate(lot.availability_from) : 'Immediate'}
                subtext={lot.availability_to ? `Until ${formatDate(lot.availability_to)}` : 'Indefinite availability'}
                icon={<Clock size={18} />}
              />
            </div>

            {/* Grid: Properties & ProofPath Qualification */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '1.5rem' }}>
              {/* Properties Card */}
              <div className="clay-card" style={{ padding: '1.5rem', backgroundColor: '#ffffff' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingBottom: '0.75rem', borderBottom: '1px solid var(--border-subtle)', marginBottom: '1rem' }}>
                  <div>
                    <span className="label-compact">Chemical & Physical</span>
                    <h3 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)' }}>Declared Attributes</h3>
                  </div>
                  <span className="strata-badge strata-badge-neutral">Self-Declared</span>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                  {Object.entries(lot.declared_attributes || {}).map(([key, value]) => (
                    <div
                      key={key}
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'baseline',
                        padding: '0.5rem 0',
                        borderBottom: '1px dotted var(--border-subtle)',
                        fontSize: '0.8125rem',
                      }}
                    >
                      <span style={{ color: 'var(--text-muted)', textTransform: 'capitalize' }}>
                        {key.replace(/_/g, ' ')}
                      </span>
                      <strong style={{ color: 'var(--text-primary)', textAlign: 'right' }}>
                        {String(value)}
                      </strong>
                    </div>
                  ))}
                  {Object.keys(lot.declared_attributes || {}).length === 0 && (
                    <div style={{ color: 'var(--text-muted)', fontSize: '0.8125rem', padding: '1rem 0' }}>
                      No declared technical attributes provided.
                    </div>
                  )}
                </div>

                <div style={{ marginTop: '1.5rem', paddingTop: '1rem', borderTop: '1px solid var(--border-subtle)' }}>
                  <span className="label-compact" style={{ display: 'block', marginBottom: '0.5rem' }}>
                    Custody Metadata
                  </span>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                    <div>Organization ID: <span style={{ fontFamily: 'monospace' }}>{lot.org_id}</span></div>
                    <div>Facility ID: <span style={{ fontFamily: 'monospace' }}>{lot.facility_id}</span></div>
                    <div>Last Synchronized: {formatDate(lot.updated_at)}</div>
                  </div>
                </div>
              </div>

              {/* ProofPath Assessment Card */}
              <div className="clay-card" style={{ padding: '1.5rem', backgroundColor: '#ffffff' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingBottom: '0.75rem', borderBottom: '1px solid var(--border-subtle)', marginBottom: '1rem' }}>
                  <div>
                    <span className="label-compact" style={{ color: 'var(--accent-teal)' }}>ProofPath Engine</span>
                    <h3 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)' }}>Qualification Assessment</h3>
                  </div>
                  <Link href={`/proofpath?lot_id=${lot.lot_id}`} style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--primary-container)', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                    Full Audit <ArrowRight size={13} />
                  </Link>
                </div>

                {!latestAssessment ? (
                  <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                    <ShieldCheck size={32} style={{ margin: '0 auto 0.5rem', opacity: 0.4 }} />
                    <p style={{ fontSize: '0.8125rem', marginBottom: '0.75rem' }}>
                      This lot has not been audited through the ProofPath qualification engine yet.
                    </p>
                    <button onClick={handleRunAssessment} disabled={isAssessing} className="clay-btn clay-btn-primary" style={{ margin: '0 auto' }}>
                      {isAssessing ? <Loader2 size={14} className="animate-spin" /> : <ShieldCheck size={14} />}
                      <span>Run Qualification Assessment</span>
                    </button>
                  </div>
                ) : (
                  <div>
                    {/* Outcome Status Banner */}
                    <div style={{
                      padding: '0.875rem',
                      borderRadius: '8px',
                      backgroundColor: latestAssessment.outcome === 'supported' ? 'var(--status-success-bg)' : latestAssessment.outcome === 'conditional' ? 'var(--status-warning-bg)' : 'var(--status-error-bg)',
                      border: `1px solid ${latestAssessment.outcome === 'supported' ? 'rgba(40,99,67,0.25)' : latestAssessment.outcome === 'conditional' ? 'rgba(184,134,11,0.25)' : 'rgba(166,58,53,0.25)'}`,
                      marginBottom: '1rem',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.75rem',
                    }}>
                      {latestAssessment.outcome === 'supported' ? <CheckCircle2 size={20} color="var(--status-success)" /> : latestAssessment.outcome === 'conditional' ? <AlertCircle size={20} color="var(--status-warning)" /> : <ShieldX size={20} color="var(--status-error)" />}
                      <div>
                        <div style={{ fontWeight: 700, fontSize: '0.875rem', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                          Outcome: {latestAssessment.outcome || latestAssessment.status}
                        </div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                          Assessment ID: {latestAssessment.assessment_id?.slice(0, 16)}…
                        </div>
                      </div>
                    </div>

                    {/* Hard Gate Results Table */}
                    {latestAssessment.hard_gate_results && latestAssessment.hard_gate_results.length > 0 && (
                      <div>
                        <div className="label-compact" style={{ marginBottom: '0.5rem' }}>Hard Gate Audits</div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                          {latestAssessment.hard_gate_results.map((gate) => (
                            <div key={gate.gate_id} style={{ padding: '0.5rem 0.75rem', borderRadius: '6px', backgroundColor: 'var(--bg-subtle)', border: '1px solid var(--border-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.75rem' }}>
                              <div>
                                <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{gate.gate_name}</span>
                                {gate.required_value && <span style={{ color: 'var(--text-muted)', marginLeft: '0.5rem' }}>Req: {String(gate.required_value)}</span>}
                              </div>
                              <span className={`strata-badge ${gate.outcome === 'pass' ? 'strata-badge-success' : gate.outcome === 'fail' ? 'strata-badge-error' : 'strata-badge-warning'}`}>
                                {gate.outcome}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Missing facts if any */}
                    {latestAssessment.missing_facts && latestAssessment.missing_facts.length > 0 && (
                      <div style={{ marginTop: '1rem' }}>
                        <div className="label-compact" style={{ color: 'var(--status-warning)', marginBottom: '0.375rem' }}>Missing ProofPath Facts</div>
                        <ul style={{ margin: 0, paddingLeft: '1.25rem', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                          {latestAssessment.missing_facts.map((mf) => (
                            <li key={mf.fact_id} style={{ marginBottom: '0.25rem' }}>
                              <strong>{mf.description}</strong> — <em>{mf.acquisition_method || 'Laboratory test required'}</em>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* Evidence & Provenance Claim Dossier */}
            <div className="clay-card" style={{ padding: '1.5rem', backgroundColor: '#ffffff' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingBottom: '0.75rem', borderBottom: '1px solid var(--border-subtle)', marginBottom: '1rem' }}>
                <div>
                  <span className="label-compact" style={{ color: 'var(--accent-teal)' }}>Immutable Evidence Claims</span>
                  <h3 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)' }}>Attached Laboratory & Custody Records</h3>
                </div>
                <button
                  onClick={() => setShowEvidenceModal(true)}
                  className="clay-btn clay-btn-secondary"
                  style={{ fontSize: '0.75rem', padding: '0.35rem 0.75rem' }}
                >
                  <Plus size={13} />
                  <span>Attach Evidence</span>
                </button>
              </div>

              {evidenceList.length === 0 ? (
                <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                  <FileText size={28} style={{ margin: '0 auto 0.5rem', opacity: 0.4 }} />
                  <p style={{ fontSize: '0.8125rem', marginBottom: '0.75rem' }}>
                    No certified evidence claims attached to this lot yet.
                  </p>
                  <button onClick={() => setShowEvidenceModal(true)} className="clay-btn clay-btn-secondary" style={{ display: 'inline-flex' }}>
                    <Plus size={14} />
                    Attach Chemical Assay or Certificate
                  </button>
                </div>
              ) : (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '0.875rem' }}>
                  {evidenceList.map((ev) => (
                    <div key={ev.evidence_id} style={{ padding: '1rem', borderRadius: '8px', backgroundColor: 'var(--bg-subtle)', border: '1px solid var(--border-subtle)', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                        <div>
                          <div style={{ fontWeight: 600, fontSize: '0.8125rem', color: 'var(--text-primary)', textTransform: 'capitalize' }}>
                            {ev.claim_type.replace(/_/g, ' ')}
                          </div>
                          <div style={{ fontSize: '0.6875rem', color: 'var(--text-muted)' }}>
                            {formatDate(ev.retrieved_at)}
                          </div>
                        </div>
                        <span className={`strata-badge ${ev.verification_status === 'verified' ? 'strata-badge-success' : 'strata-badge-neutral'}`}>
                          {ev.verification_status}
                        </span>
                      </div>

                      <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                        <strong>Source:</strong> {ev.provenance}
                      </div>

                      {ev.data_payload && Object.keys(ev.data_payload).length > 0 && (
                        <div style={{ fontSize: '0.6875rem', color: 'var(--text-muted)', backgroundColor: '#ffffff', padding: '0.5rem', borderRadius: '4px', border: '1px solid var(--border-subtle)' }}>
                          {Object.entries(ev.data_payload).map(([k, v]) => (
                            <div key={k}>
                              <span style={{ textTransform: 'capitalize' }}>{k.replace(/_/g, ' ')}:</span> <strong>{String(v)}</strong>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        )}

        {/* ATTACH EVIDENCE MODAL */}
        {showEvidenceModal && (
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
            <div className="clay-card" style={{ width: '100%', maxWidth: '520px', backgroundColor: '#ffffff', padding: '1.75rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingBottom: '0.75rem', borderBottom: '1px solid var(--border-subtle)', marginBottom: '1.25rem' }}>
                <div>
                  <span className="label-compact" style={{ color: 'var(--accent-teal)' }}>Audit Evidence</span>
                  <h2 style={{ fontSize: '1.125rem', fontWeight: 700, color: 'var(--primary)' }}>Attach Evidence Record</h2>
                </div>
                <button onClick={() => setShowEvidenceModal(false)} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}>
                  <X size={18} />
                </button>
              </div>

              {evidenceError && (
                <div style={{ padding: '0.75rem', borderRadius: '8px', backgroundColor: 'var(--status-error-bg)', color: 'var(--status-error)', fontSize: '0.8125rem', display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
                  <AlertCircle size={15} />
                  <span>{evidenceError}</span>
                </div>
              )}

              {evidenceSuccess && (
                <div style={{ padding: '0.75rem', borderRadius: '8px', backgroundColor: 'var(--status-success-bg)', color: 'var(--status-success)', fontSize: '0.8125rem', display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
                  <CheckCircle2 size={15} />
                  <span>{evidenceSuccess}</span>
                </div>
              )}

              <form onSubmit={handleCreateEvidence} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <div>
                  <label className="label-compact" style={{ display: 'block', marginBottom: '0.375rem' }}>Claim Type</label>
                  <select value={claimType} onChange={(e) => setClaimType(e.target.value)} className="clay-select">
                    <option value="chemical_assay">Chemical Assay (ICP-OES / XRF)</option>
                    <option value="radiological_clearance">Radiological Clearance Certificate</option>
                    <option value="weighbridge_slip">Weighbridge &amp; Gross Mass Slip</option>
                    <option value="moisture_certificate">Moisture &amp; Volatiles Analysis</option>
                    <option value="basel_permit">Basel Convention Shipment Permit</option>
                  </select>
                </div>

                <div>
                  <label className="label-compact" style={{ display: 'block', marginBottom: '0.375rem' }}>Provenance / Laboratory Source</label>
                  <input
                    type="text"
                    required
                    value={provenance}
                    onChange={(e) => setProvenance(e.target.value)}
                    placeholder="e.g. SGS Metallurgical Testing Lab Basel"
                    className="clay-input"
                  />
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                  <div>
                    <label className="label-compact" style={{ display: 'block', marginBottom: '0.375rem' }}>Test Standard</label>
                    <input
                      type="text"
                      value={testStandard}
                      onChange={(e) => setTestStandard(e.target.value)}
                      placeholder="ASTM E2371 / ISO 17025"
                      className="clay-input"
                    />
                  </div>
                  <div>
                    <label className="label-compact" style={{ display: 'block', marginBottom: '0.375rem' }}>Certificate ID</label>
                    <input
                      type="text"
                      value={certId}
                      onChange={(e) => setCertId(e.target.value)}
                      placeholder="CERT-CH-2026-902"
                      className="clay-input"
                    />
                  </div>
                </div>

                <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end', marginTop: '0.75rem' }}>
                  <button type="button" onClick={() => setShowEvidenceModal(false)} className="clay-btn clay-btn-ghost">
                    Cancel
                  </button>
                  <button type="submit" disabled={submittingEvidence} className="clay-btn clay-btn-primary">
                    {submittingEvidence ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
                    <span>Attach to Audit Chain</span>
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
