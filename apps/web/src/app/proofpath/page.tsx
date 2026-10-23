'use client';

import React, { Suspense, useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import {
  ShieldCheck,
  ShieldAlert,
  ShieldX,
  Play,
  RotateCcw,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  FileText,
  Search,
  Loader2,
  Layers,
  ChevronRight,
  Info,
} from 'lucide-react';
import { AppShell } from '@/components/AppShell';
import { Badge } from '@/components/Badge';
import { api } from '@/lib/api-client';
import { useAuth } from '@/lib/auth';
import {
  Investigation,
  MaterialLot,
  QualificationAssessment,
  QualificationOutcome,
} from '@/types';
import { formatDate, formatNumber } from '@/lib/utils';

export default function ProofPathPage() {
  return (
    <Suspense fallback={<div style={{ padding: '2rem', textAlign: 'center' }}>Loading ProofPath Engine...</div>}>
      <ProofPathContent />
    </Suspense>
  );
}

function ProofPathContent() {

  const { user } = useAuth();
  const searchParams = useSearchParams();

  const [lots, setLots] = useState<MaterialLot[]>([]);
  const [selectedLotId, setSelectedLotId] = useState<string>('');
  const [assessments, setAssessments] = useState<QualificationAssessment[]>([]);
  const [currentInvestigation, setCurrentInvestigation] = useState<Investigation | null>(null);

  const [runDiscovery, setRunDiscovery] = useState(false);
  const [notes, setNotes] = useState('');
  const [isQualifying, setIsQualifying] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load lots on mount
  useEffect(() => {
    async function initLots() {
      try {
        const res = await api.materials.listLots({ page_size: 50 });
        const lotsList = res.data || [];
        setLots(lotsList);

        const urlLotId = searchParams?.get('lot_id');
        if (urlLotId && lotsList.some((l) => l.lot_id === urlLotId)) {
          setSelectedLotId(urlLotId);
        } else if (lotsList.length > 0) {
          setSelectedLotId(lotsList[0].lot_id);
        }
      } catch (err) {
        console.warn('Failed to load lots for ProofPath:', err);
      }
    }
    initLots();
  }, [searchParams]);

  // Load previous assessments when selectedLotId changes
  useEffect(() => {
    if (!selectedLotId) return;

    async function loadAssessments() {
      setLoadingHistory(true);
      setError(null);
      try {
        const res = await api.qualification.getLotAssessments(selectedLotId);
        setAssessments(res.data || []);
      } catch (err) {
        // No previous assessments is acceptable
        setAssessments([]);
      } finally {
        setLoadingHistory(false);
      }
    }

    loadAssessments();
  }, [selectedLotId]);

  const handleRunAssessment = async () => {
    if (!selectedLotId) {
      setError('Please select a material lot to evaluate.');
      return;
    }

    setIsQualifying(true);
    setError(null);
    try {
      const res = await api.qualification.assessLot(selectedLotId, {
        notes: notes || undefined,
        run_discovery: runDiscovery,
      });

      setCurrentInvestigation(res.data);

      // Refresh assessment history
      const historyRes = await api.qualification.getLotAssessments(selectedLotId);
      setAssessments(historyRes.data || []);
    } catch (err: any) {
      setError(err?.message || 'ProofPath assessment evaluation failed.');
    } finally {
      setIsQualifying(false);
    }
  };

  const selectedLot = lots.find((l) => l.lot_id === selectedLotId);

  const getOutcomeBanner = (outcome: QualificationOutcome) => {
    switch (outcome) {
      case 'supported':
        return (
          <div
            style={{
              padding: '1rem',
              borderRadius: '8px',
              backgroundColor: 'var(--status-success-bg)',
              border: '1.5px solid var(--status-success)',
              display: 'flex',
              alignItems: 'center',
              gap: '0.75rem',
            }}
          >
            <CheckCircle2 size={24} color="var(--status-success)" />
            <div>
              <div style={{ fontWeight: 700, fontSize: '0.9375rem', color: 'var(--status-success)' }}>
                OUTCOME: SUPPORTED (QUALIFIED FOR RECOVERY)
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                All technical specifications and regulatory constraints satisfied. DPP chain verification passed.
              </div>
            </div>
          </div>
        );
      case 'conditional':
        return (
          <div
            style={{
              padding: '1rem',
              borderRadius: '8px',
              backgroundColor: 'var(--status-warning-bg)',
              border: '1.5px solid var(--status-warning)',
              display: 'flex',
              alignItems: 'center',
              gap: '0.75rem',
            }}
          >
            <AlertTriangle size={24} color="var(--status-warning)" />
            <div>
              <div style={{ fontWeight: 700, fontSize: '0.9375rem', color: 'var(--status-warning)' }}>
                OUTCOME: CONDITIONAL (ADDITIONAL EVIDENCE REQUIRED)
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                Material meets baseline criteria but requires documented assay certificate or pre-treatment step.
              </div>
            </div>
          </div>
        );
      case 'unsupported':
      default:
        return (
          <div
            style={{
              padding: '1rem',
              borderRadius: '8px',
              backgroundColor: 'var(--status-error-bg)',
              border: '1.5px solid var(--status-error)',
              display: 'flex',
              alignItems: 'center',
              gap: '0.75rem',
            }}
          >
            <XCircle size={24} color="var(--status-error)" />
            <div>
              <div style={{ fontWeight: 700, fontSize: '0.9375rem', color: 'var(--status-error)' }}>
                OUTCOME: UNSUPPORTED (HARD INCOMPATIBILITY DETECTED)
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                Deterministic hard constraint violation. Under strict platform policy, this cannot be overridden.
              </div>
            </div>
          </div>
        );
    }
  };

  return (
    <AppShell>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
        {/* Header */}
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
            <span className="label-compact" style={{ color: 'var(--accent-teal)' }}>
              ProofPath Audit Engine
            </span>
            <span style={{ color: 'var(--text-muted)' }}>·</span>
            <span className="label-compact" style={{ color: 'var(--text-muted)' }}>
              Deterministic Rule Invariants Active
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
            Material Recovery Qualification
          </h1>
          <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
            Evaluates candidate recovery routes deterministically against strict metallurgical,
            hazardous waste, and transport rules. Hard incompatibilities cannot be bypassed.
          </p>
        </div>

        {/* Console layout */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
            gap: '1.5rem',
            alignItems: 'start',
          }}
        >
          {/* Left: Lot Selection & Evaluation Config */}
          <div
            className="clay-card"
            style={{ padding: '1.5rem', backgroundColor: '#ffffff', display: 'flex', flexDirection: 'column', gap: '1.25rem' }}
          >
            <div>
              <label className="label-compact" style={{ display: 'block', marginBottom: '0.375rem' }}>
                Select Material Lot for Assessment <span style={{ color: 'var(--status-error)' }}>*</span>
              </label>
              <select
                value={selectedLotId}
                onChange={(e) => setSelectedLotId(e.target.value)}
                className="clay-select"
              >
                {lots.map((lot) => (
                  <option key={lot.lot_id} value={lot.lot_id}>
                    {lot.material_type} — {lot.quantity} {lot.unit} ({lot.lot_id.slice(0, 8)}...)
                  </option>
                ))}
                {lots.length === 0 && (
                  <option value="">No material lots available in facility</option>
                )}
              </select>
            </div>

            {selectedLot && (
              <div
                style={{
                  padding: '0.75rem',
                  borderRadius: '6px',
                  backgroundColor: 'var(--bg-subtle)',
                  border: '1px solid var(--border-subtle)',
                  fontSize: '0.75rem',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '0.375rem',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Material Class:</span>
                  <span style={{ fontWeight: 600 }}>{selectedLot.material_type}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Inventory Volume:</span>
                  <span className="tnum" style={{ fontWeight: 600 }}>
                    {formatNumber(selectedLot.quantity)} {selectedLot.unit}
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Current Status:</span>
                  <span style={{ textTransform: 'capitalize', fontWeight: 600 }}>
                    {selectedLot.status.replace('_', ' ')}
                  </span>
                </div>
              </div>
            )}

            <div>
              <label className="label-compact" style={{ display: 'block', marginBottom: '0.375rem' }}>
                Assessment Notes &amp; Custody Remarks
              </label>
              <textarea
                rows={3}
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Include batch processing notes, pre-treatment steps, or customer specifications..."
                className="clay-input"
                style={{ resize: 'vertical' }}
              />
            </div>

            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                padding: '0.75rem',
                borderRadius: '6px',
                backgroundColor: 'var(--bg-subtle)',
                border: '1px solid var(--border-subtle)',
              }}
            >
              <input
                type="checkbox"
                id="discovery-toggle"
                checked={runDiscovery}
                onChange={(e) => setRunDiscovery(e.target.checked)}
                style={{ accentColor: 'var(--primary-container)' }}
              />
              <label htmlFor="discovery-toggle" style={{ fontSize: '0.75rem', cursor: 'pointer' }}>
                <strong>Enable External Discovery:</strong> Search verified receiver capability
                evidence before deterministic evaluation.
              </label>
            </div>

            {error && (
              <div
                style={{
                  padding: '0.75rem',
                  borderRadius: '6px',
                  backgroundColor: 'var(--status-error-bg)',
                  border: '1px solid rgba(166, 58, 53, 0.25)',
                  color: 'var(--status-error)',
                  fontSize: '0.8125rem',
                }}
              >
                {error}
              </div>
            )}

            <button
              type="button"
              disabled={isQualifying || !selectedLotId}
              onClick={handleRunAssessment}
              className="clay-btn clay-btn-primary"
              style={{ padding: '0.75rem' }}
            >
              {isQualifying ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  <span>Evaluating Rules Deterministically...</span>
                </>
              ) : (
                <>
                  <Play size={16} />
                  <span>Run Qualification Assessment</span>
                </>
              )}
            </button>
          </div>

          {/* Right: Assessment Outcome Dossier */}
          <div
            className="clay-card"
            style={{ padding: '1.5rem', backgroundColor: '#ffffff', display: 'flex', flexDirection: 'column', gap: '1.25rem' }}
          >
            <div>
              <span className="label-compact">Deterministic Audit Result</span>
              <h3 style={{ fontSize: '1.125rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                Structured Qualification Dossier
              </h3>
            </div>

            {currentInvestigation || assessments.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                {(() => {
                  const activeAssessment = currentInvestigation?.assessments?.[0] || assessments[0];
                  const outcome =
                    currentInvestigation?.qualification_outcome ||
                    activeAssessment?.status ||
                    activeAssessment?.outcome ||
                    'unsupported';
                  const hardGates =
                    activeAssessment?.hard_gate_results?.filter((g) => g.outcome === 'fail') || [];
                  const blockingConditions =
                    activeAssessment?.blocking_conditions ||
                    currentInvestigation?.hard_incompatibilities?.map((h) => `${h.parameter}: ${h.reason}`) ||
                    [];
                  const missingFacts = activeAssessment?.missing_facts || [];
                  const evidenceRefs =
                    activeAssessment?.evidence_refs ||
                    activeAssessment?.supporting_evidence_ids ||
                    [];
                  const nextAction =
                    activeAssessment?.next_action ||
                    (currentInvestigation?.recommendations?.[0]) ||
                    'No action required';
                  const rationale = activeAssessment?.rationale;

                  return (
                    <>
                      {getOutcomeBanner(outcome)}

                      {/* Route & Evaluation Meta */}
                      <div
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          padding: '0.625rem 0.875rem',
                          backgroundColor: 'var(--bg-subtle)',
                          borderRadius: '6px',
                          fontSize: '0.75rem',
                        }}
                      >
                        <span style={{ color: 'var(--text-secondary)' }}>
                          Candidate Route: <strong>{activeAssessment?.candidate_route_id || 'Standard Pyrometallurgical Smelting'}</strong>
                        </span>
                        <span className="label-compact" style={{ color: 'var(--text-muted)' }}>
                          Engine v{activeAssessment?.rule_version || '1.0.0'}
                        </span>
                      </div>

                      {/* Hard Incompatibilities & Violated Gates */}
                      {(hardGates.length > 0 || blockingConditions.length > 0) && (
                        <div
                          style={{
                            padding: '1rem',
                            borderRadius: '8px',
                            backgroundColor: 'var(--status-error-bg)',
                            border: '1px solid rgba(166, 58, 53, 0.25)',
                          }}
                        >
                          <div
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              gap: '0.375rem',
                              marginBottom: '0.5rem',
                            }}
                          >
                            <XCircle size={16} color="var(--status-error)" />
                            <span
                              className="label-compact"
                              style={{ color: 'var(--status-error)', fontWeight: 700 }}
                            >
                              Violated Hard Gates &amp; Incompatibilities ({hardGates.length || blockingConditions.length})
                            </span>
                          </div>

                          {hardGates.map((gate, idx) => (
                            <div
                              key={idx}
                              style={{
                                fontSize: '0.75rem',
                                padding: '0.5rem 0.75rem',
                                backgroundColor: '#ffffff',
                                borderRadius: '6px',
                                border: '1px solid rgba(166, 58, 53, 0.2)',
                                marginBottom: '0.375rem',
                              }}
                            >
                              <div style={{ fontWeight: 600, color: 'var(--status-error)' }}>
                                Gate [{gate.gate_id}]: {gate.gate_name}
                              </div>
                              <div className="tnum" style={{ fontSize: '0.6875rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
                                Required: {String(gate.required_value ?? 'compliant')} | Measured: {String(gate.material_value ?? 'fail')}
                              </div>
                            </div>
                          ))}

                          {hardGates.length === 0 && blockingConditions.map((cond, idx) => (
                            <div
                              key={idx}
                              style={{
                                fontSize: '0.75rem',
                                padding: '0.5rem 0.75rem',
                                backgroundColor: '#ffffff',
                                borderRadius: '6px',
                                border: '1px solid rgba(166, 58, 53, 0.2)',
                                marginBottom: '0.375rem',
                                color: 'var(--status-error)',
                                fontWeight: 500,
                              }}
                            >
                              {cond}
                            </div>
                          ))}
                        </div>
                      )}

                      {/* Missing Information / Missing Facts */}
                      {missingFacts.length > 0 && (
                        <div
                          style={{
                            padding: '1rem',
                            borderRadius: '8px',
                            backgroundColor: 'var(--status-warning-bg)',
                            border: '1px solid rgba(184, 115, 51, 0.25)',
                          }}
                        >
                          <div
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              gap: '0.375rem',
                              marginBottom: '0.5rem',
                            }}
                          >
                            <AlertTriangle size={16} color="var(--status-warning)" />
                            <span
                              className="label-compact"
                              style={{ color: 'var(--status-warning)', fontWeight: 700 }}
                            >
                              Missing Information &amp; Specification Gaps ({missingFacts.length})
                            </span>
                          </div>

                          {missingFacts.map((fact, idx) => (
                            <div
                              key={idx}
                              style={{
                                fontSize: '0.75rem',
                                padding: '0.5rem 0.75rem',
                                backgroundColor: '#ffffff',
                                borderRadius: '6px',
                                border: '1px solid rgba(184, 115, 51, 0.2)',
                                marginBottom: '0.375rem',
                                display: 'flex',
                                justifyContent: 'space-between',
                                alignItems: 'center',
                              }}
                            >
                              <div>
                                <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                                  {fact.description}
                                </div>
                                <div style={{ fontSize: '0.6875rem', color: 'var(--text-muted)' }}>
                                  Acquisition method: {fact.acquisition_method || 'document'}
                                </div>
                              </div>
                              {fact.is_critical && (
                                <span
                                  className="label-compact"
                                  style={{
                                    fontSize: '0.625rem',
                                    color: 'var(--status-warning)',
                                    backgroundColor: 'var(--status-warning-bg)',
                                    padding: '2px 6px',
                                    borderRadius: '4px',
                                  }}
                                >
                                  Critical
                                </span>
                              )}
                            </div>
                          ))}
                        </div>
                      )}

                      {/* Supporting Evidence References */}
                      <div
                        style={{
                          padding: '1rem',
                          borderRadius: '8px',
                          backgroundColor: 'var(--bg-subtle)',
                          border: '1px solid var(--border-subtle)',
                        }}
                      >
                        <div
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.375rem',
                            marginBottom: '0.5rem',
                          }}
                        >
                          <FileText size={16} color="var(--primary-container)" />
                          <span className="label-compact" style={{ fontWeight: 700 }}>
                            Supporting Evidence &amp; Audit Records ({evidenceRefs.length})
                          </span>
                        </div>

                        {evidenceRefs.length === 0 ? (
                          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                            No external evidence references attached to this qualification run.
                          </div>
                        ) : (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.375rem' }}>
                            {evidenceRefs.map((ref, idx) => (
                              <div
                                key={idx}
                                style={{
                                  padding: '0.5rem 0.75rem',
                                  backgroundColor: '#ffffff',
                                  borderRadius: '6px',
                                  border: '1px solid var(--border-subtle)',
                                  fontSize: '0.75rem',
                                  display: 'flex',
                                  alignItems: 'center',
                                  justifyContent: 'space-between',
                                }}
                              >
                                <span style={{ fontFamily: 'monospace', color: 'var(--text-primary)' }}>
                                  REF: {ref}
                                </span>
                                <Badge variant="teal">Verified</Badge>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>

                      {/* Engine Rationale & Next Recommendations */}
                      <div
                        style={{
                          padding: '1rem',
                          borderRadius: '8px',
                          backgroundColor: 'var(--bg-subtle)',
                          border: '1px solid var(--border-subtle)',
                        }}
                      >
                        <span className="label-compact" style={{ display: 'block', marginBottom: '0.375rem' }}>
                          Authoritative Determination &amp; Next Action
                        </span>
                        {rationale && (
                          <p style={{ fontSize: '0.8125rem', color: 'var(--text-primary)', marginBottom: '0.5rem' }}>
                            {rationale}
                          </p>
                        )}
                        <div
                          style={{
                            fontSize: '0.75rem',
                            padding: '0.5rem 0.75rem',
                            backgroundColor: '#ffffff',
                            borderRadius: '6px',
                            border: '1px solid var(--border-subtle)',
                            color: 'var(--primary-container)',
                            fontWeight: 600,
                          }}
                        >
                          Action: {nextAction}
                        </div>
                      </div>
                    </>
                  );
                })()}
              </div>
            ) : (
              <div
                style={{
                  padding: '3rem 1rem',
                  textAlign: 'center',
                  color: 'var(--text-muted)',
                }}
              >
                <ShieldCheck size={36} style={{ margin: '0 auto 0.75rem auto', opacity: 0.4 }} />
                <div style={{ fontWeight: 600, fontSize: '0.875rem' }}>No Assessment Run Yet</div>
                <p style={{ fontSize: '0.75rem', marginTop: '0.25rem', maxWidth: '320px', margin: '0.25rem auto' }}>
                  Click &quot;Run Qualification Assessment&quot; to test this material lot against
                  authoritative circularity routes.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </AppShell>
  );
}
