'use client';

import React, { Suspense, useEffect, useState } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import {
  FileText,
  Plus,
  CheckCircle2,
  Clock,
  Send,
  Check,
  XCircle,
  Loader2,
  Layers,
  ArrowRight,
  ExternalLink,
  DollarSign,
  History,
  X,
  AlertCircle,
  ShieldCheck,
  Tag,
} from 'lucide-react';
import { AppShell } from '@/components/AppShell';
import { Badge } from '@/components/Badge';
import { api } from '@/lib/api-client';
import { useAuth } from '@/lib/auth';
import { RFQ, ExchangeListing, Offer, WorkflowEvent } from '@/types';
import { formatDate, formatNumber } from '@/lib/utils';

export default function RFQsPage() {
  return (
    <Suspense fallback={<div style={{ padding: '2rem', textAlign: 'center' }}>Loading RFQs Workspace...</div>}>
      <RFQsContent />
    </Suspense>
  );
}

function RFQsContent() {
  const { user } = useAuth();
  const searchParams = useSearchParams();

  const [rfqs, setRfqs] = useState<RFQ[]>([]);
  const [listings, setListings] = useState<ExchangeListing[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedRfq, setSelectedRfq] = useState<RFQ | null>(null);

  // Inspector Drawer data
  const [offers, setOffers] = useState<Offer[]>([]);
  const [historyEvents, setHistoryEvents] = useState<WorkflowEvent[]>([]);
  const [loadingDetails, setLoadingDetails] = useState(false);

  // New RFQ Modal
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedListingId, setSelectedListingId] = useState('');
  const [quantity, setQuantity] = useState<number>(10);
  const [targetPrice, setTargetPrice] = useState<number>(440);
  const [notes, setNotes] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Submit Offer Modal
  const [offerModalOpen, setOfferModalOpen] = useState(false);
  const [offeredQty, setOfferedQty] = useState<number>(10);
  const [offerPrice, setOfferPrice] = useState<number>(435);
  const [offerTerms, setOfferTerms] = useState('FOB origin smelter siding; 30-day payment term');
  const [offerNotes, setOfferNotes] = useState('');
  const [isSubmittingOffer, setIsSubmittingOffer] = useState(false);
  const [offerError, setOfferError] = useState<string | null>(null);

  useEffect(() => {
    if (searchParams?.get('action') === 'new') {
      const urlListing = searchParams?.get('listing_id');
      if (urlListing) setSelectedListingId(urlListing);
      setModalOpen(true);
    }
  }, [searchParams]);

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [rfqRes, listingsRes] = await Promise.all([
        api.exchange.listRFQs(),
        api.exchange.listListings(),
      ]);
      const rfqList = rfqRes.data || [];
      setRfqs(rfqList);
      setListings(listingsRes.data || []);

      const urlRfqId = searchParams?.get('rfq_id');
      if (urlRfqId) {
        const found = rfqList.find((r) => r.rfq_id === urlRfqId);
        if (found) setSelectedRfq(found);
      } else if (rfqList.length > 0 && !selectedRfq) {
        setSelectedRfq(rfqList[0]);
      }
    } catch (err) {
      console.warn('Failed to load RFQs data:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // Load offers & history when selectedRfq changes
  useEffect(() => {
    if (!selectedRfq) {
      setOffers([]);
      setHistoryEvents([]);
      return;
    }

    async function loadRfqDetails() {
      setLoadingDetails(true);
      try {
        const [offersRes, historyRes] = await Promise.all([
          api.exchange.listRFQOffers(selectedRfq!.rfq_id).catch(() => ({ data: [] })),
          api.exchange.getRFQHistory(selectedRfq!.rfq_id).catch(() => ({ data: [] })),
        ]);
        setOffers(offersRes.data || []);
        setHistoryEvents(historyRes.data || []);
      } catch (err) {
        console.warn('Failed to load RFQ details:', err);
      } finally {
        setLoadingDetails(false);
      }
    }

    loadRfqDetails();
  }, [selectedRfq]);

  const handleCreateRFQ = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedListingId) {
      setError('Please choose a valid exchange listing.');
      return;
    }

    setIsSubmitting(true);
    setError(null);
    try {
      const res = await api.exchange.createRFQ({
        listing_id: selectedListingId,
        requested_quantity: quantity,
        target_price_per_unit: targetPrice || undefined,
        notes: notes || undefined,
      });

      await loadData();
      setSelectedRfq(res.data);
      setModalOpen(false);
    } catch (err: any) {
      setError(err?.message || 'Failed to initiate RFQ.');
    } finally {
      setIsSubmitting(false);
    }
  };

  // RFQ State Transitions
  const handleTransitionRFQ = async (action: 'submit' | 'approve' | 'cancel') => {
    if (!selectedRfq) return;
    try {
      let res;
      if (action === 'submit') {
        res = await api.exchange.submitRFQ(selectedRfq.rfq_id, 'Submitted for manager approval');
      } else if (action === 'approve') {
        res = await api.exchange.approveRFQ(selectedRfq.rfq_id, 'Approved commercial negotiation');
      } else {
        res = await api.exchange.cancelRFQ(selectedRfq.rfq_id, 'Withdrawn by caller');
      }
      setSelectedRfq(res.data);
      await loadData();
    } catch (err: any) {
      alert(err?.message || `Failed to ${action} RFQ`);
    }
  };

  // Submit Offer
  const handleSubmitOffer = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedRfq) return;

    setIsSubmittingOffer(true);
    setOfferError(null);
    try {
      await api.exchange.submitOffer(selectedRfq.rfq_id, {
        offered_quantity: offeredQty,
        unit: selectedRfq.unit || 'tonne',
        price_per_unit: offerPrice,
        currency: 'USD',
        terms: offerTerms,
        notes: offerNotes || undefined,
      });

      // Reload details
      const offersRes = await api.exchange.listRFQOffers(selectedRfq.rfq_id);
      setOffers(offersRes.data || []);
      setOfferModalOpen(false);
    } catch (err: any) {
      setOfferError(err?.message || 'Failed to submit commercial offer.');
    } finally {
      setIsSubmittingOffer(false);
    }
  };

  // Offer State Transitions
  const handleOfferAction = async (offerId: string, action: 'review' | 'accept' | 'reject' | 'withdraw') => {
    try {
      if (action === 'review') {
        await api.exchange.reviewOffer(offerId, 'Under active technical and commercial review');
      } else if (action === 'accept') {
        if (!confirm('Accepting this commercial offer executes a legally binding bilateral agreement. Proceed?')) return;
        await api.exchange.acceptOffer(offerId, 'Offer accepted. Bilateral deal finalized.');
      } else if (action === 'reject') {
        await api.exchange.rejectOffer(offerId, 'Offer terms rejected');
      } else {
        await api.exchange.withdrawOffer(offerId, 'Withdrawn by seller');
      }

      if (selectedRfq) {
        const offersRes = await api.exchange.listRFQOffers(selectedRfq.rfq_id);
        setOffers(offersRes.data || []);
        await loadData();
      }
    } catch (err: any) {
      alert(err?.message || `Failed to perform offer action: ${action}`);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'approved':
        return <Badge variant="success" dot>Approved</Badge>;
      case 'submitted':
        return <Badge variant="warning" dot>Pending Review</Badge>;
      case 'accepted':
        return <Badge variant="teal" dot>Accepted / Deal Final</Badge>;
      case 'under_review':
        return <Badge variant="warning" dot>Under Review</Badge>;
      case 'rejected':
      case 'cancelled':
        return <Badge variant="error">Terminated</Badge>;
      default:
        return <Badge variant="neutral">Draft</Badge>;
    }
  };

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
                Bilateral Negotiation Workspace
              </span>
              <span style={{ color: 'var(--text-muted)' }}>·</span>
              <span className="label-compact" style={{ color: 'var(--text-muted)' }}>
                Human In-the-Loop Approval Gates
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
              Requests for Quotation (RFQs) &amp; Offers
            </h1>
            <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
              Negotiate price per unit, tonnage allotments, delivery terms, and review binding commercial offers.
            </p>
          </div>

          <button
            onClick={() => setModalOpen(true)}
            className="clay-btn clay-btn-primary"
            style={{ gap: '0.5rem' }}
          >
            <Plus size={16} />
            <span>Initiate RFQ</span>
          </button>
        </div>

        {/* Layout: RFQ Table + Detail Inspector */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: selectedRfq ? '1fr 380px' : '1fr',
            gap: '1.25rem',
            alignItems: 'start',
          }}
        >
          {/* Main Table */}
          <div className="strata-table-container">
            <table className="strata-table">
              <thead>
                <tr>
                  <th>RFQ Identifier</th>
                  <th>Target Listing</th>
                  <th>Volume</th>
                  <th>Target Price</th>
                  <th>Status</th>
                  <th>Date Initiated</th>
                </tr>
              </thead>
              <tbody>
                {isLoading ? (
                  <tr>
                    <td colSpan={6} style={{ textAlign: 'center', padding: '2.5rem' }}>
                      <Loader2 size={24} className="animate-spin" style={{ margin: '0 auto' }} />
                    </td>
                  </tr>
                ) : rfqs.length === 0 ? (
                  <tr>
                    <td
                      colSpan={6}
                      style={{
                        textAlign: 'center',
                        padding: '3rem 1rem',
                        color: 'var(--text-muted)',
                      }}
                    >
                      <FileText size={32} style={{ margin: '0 auto 0.5rem auto', opacity: 0.4 }} />
                      <div style={{ fontWeight: 600 }}>No RFQs initiated yet</div>
                      <div style={{ fontSize: '0.75rem', marginTop: '0.25rem' }}>
                        Browse the Circular Exchange to initiate requests for quotation on active listings.
                      </div>
                    </td>
                  </tr>
                ) : (
                  rfqs.map((rfq) => {
                    const isSelected = selectedRfq?.rfq_id === rfq.rfq_id;
                    return (
                      <tr
                        key={rfq.rfq_id}
                        onClick={() => setSelectedRfq(rfq)}
                        style={{
                          backgroundColor: isSelected ? 'var(--bg-subtle)' : undefined,
                          cursor: 'pointer',
                        }}
                      >
                        <td>
                          <span
                            style={{
                              fontFamily: 'monospace',
                              fontSize: '0.75rem',
                              fontWeight: 600,
                              color: 'var(--text-primary)',
                            }}
                          >
                            RFQ-{rfq.rfq_id.slice(0, 10)}
                          </span>
                        </td>
                        <td>
                          <span style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
                            Listing: {rfq.listing_id.slice(0, 8)}...
                          </span>
                        </td>
                        <td className="tnum">
                          <strong>{formatNumber(rfq.requested_quantity)}</strong> {rfq.unit || 'MT'}
                        </td>
                        <td className="tnum">
                          {rfq.target_price_per_unit ? `$${rfq.target_price_per_unit}` : 'Market Index'}
                        </td>
                        <td>{getStatusBadge(rfq.status)}</td>
                        <td className="tnum" style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                          {formatDate(rfq.created_at)}
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>

          {/* Right Inspector Drawer: RFQ Detail & Commercial Offers */}
          {selectedRfq && (
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
                  <span className="label-compact">Negotiation Dossier</span>
                  <h3 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                    RFQ-{selectedRfq.rfq_id.slice(0, 10)}
                  </h3>
                </div>
                <button
                  onClick={() => setSelectedRfq(null)}
                  className="clay-btn-ghost"
                  style={{ padding: '4px' }}
                >
                  <X size={16} />
                </button>
              </div>

              {/* Status & Volume Summary */}
              <div
                style={{
                  padding: '0.75rem',
                  borderRadius: '6px',
                  backgroundColor: 'var(--bg-subtle)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '0.375rem',
                  fontSize: '0.75rem',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Workflow State:</span>
                  {getStatusBadge(selectedRfq.status)}
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Target Quantity:</span>
                  <span className="tnum" style={{ fontWeight: 600 }}>
                    {formatNumber(selectedRfq.requested_quantity)} {selectedRfq.unit || 'MT'}
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Target Price:</span>
                  <span className="tnum" style={{ fontWeight: 600 }}>
                    {selectedRfq.target_price_per_unit ? `$${selectedRfq.target_price_per_unit}/MT` : 'Market Index'}
                  </span>
                </div>
                {selectedRfq.notes && (
                  <div style={{ marginTop: '0.25rem', borderTop: '1px dotted var(--border-subtle)', paddingTop: '0.25rem' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Notes: </span>
                    <span style={{ color: 'var(--text-secondary)' }}>{selectedRfq.notes}</span>
                  </div>
                )}
              </div>

              {/* RFQ Workflow Transitions */}
              <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                {selectedRfq.status === 'draft' && (
                  <button
                    onClick={() => handleTransitionRFQ('submit')}
                    className="clay-btn clay-btn-primary"
                    style={{ flex: 1, fontSize: '0.75rem', padding: '0.375rem' }}
                  >
                    Submit for Approval
                  </button>
                )}
                {selectedRfq.status === 'submitted' && (
                  <button
                    onClick={() => handleTransitionRFQ('approve')}
                    className="clay-btn clay-btn-primary"
                    style={{ flex: 1, fontSize: '0.75rem', padding: '0.375rem' }}
                  >
                    Approve RFQ
                  </button>
                )}
                {selectedRfq.status !== 'cancelled' && selectedRfq.status !== 'accepted' && (
                  <button
                    onClick={() => handleTransitionRFQ('cancel')}
                    className="clay-btn clay-btn-ghost"
                    style={{ fontSize: '0.75rem', padding: '0.375rem', color: 'var(--status-error)' }}
                  >
                    Cancel RFQ
                  </button>
                )}
              </div>

              {/* Offers Section */}
              <div>
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    marginBottom: '0.5rem',
                  }}
                >
                  <span className="label-compact" style={{ fontWeight: 700 }}>
                    Commercial Offers / Quotes ({offers.length})
                  </span>
                  <button
                    onClick={() => setOfferModalOpen(true)}
                    className="clay-btn clay-btn-secondary"
                    style={{ fontSize: '0.6875rem', padding: '0.2rem 0.5rem', gap: '0.25rem' }}
                  >
                    <Plus size={12} />
                    <span>Submit Quote</span>
                  </button>
                </div>

                {loadingDetails ? (
                  <div style={{ padding: '1rem', textAlign: 'center' }}>
                    <Loader2 size={16} className="animate-spin" style={{ margin: '0 auto' }} />
                  </div>
                ) : offers.length === 0 ? (
                  <div
                    style={{
                      padding: '1.25rem',
                      textAlign: 'center',
                      color: 'var(--text-muted)',
                      backgroundColor: 'var(--bg-subtle)',
                      borderRadius: '6px',
                      fontSize: '0.75rem',
                    }}
                  >
                    No offers received yet. Click &quot;Submit Quote&quot; to propose commercial terms.
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.625rem' }}>
                    {offers.map((offer) => (
                      <div
                        key={offer.id}
                        style={{
                          padding: '0.75rem',
                          borderRadius: '6px',
                          border: '1px solid var(--border-subtle)',
                          backgroundColor: 'var(--bg-subtle)',
                          fontSize: '0.75rem',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '0.375rem',
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <span className="tnum" style={{ fontWeight: 700, fontSize: '0.875rem' }}>
                            ${offer.price_per_unit} / {offer.unit}
                          </span>
                          {getStatusBadge(offer.status)}
                        </div>

                        <div className="tnum" style={{ color: 'var(--text-secondary)' }}>
                          Offered Volume: <strong>{formatNumber(offer.offered_quantity)}</strong> {offer.unit}
                        </div>

                        {offer.terms && (
                          <div style={{ color: 'var(--text-muted)', fontSize: '0.6875rem' }}>
                            Terms: {offer.terms}
                          </div>
                        )}

                        {/* Offer Action Buttons */}
                        <div
                          style={{
                            display: 'flex',
                            gap: '0.375rem',
                            marginTop: '0.375rem',
                            paddingTop: '0.375rem',
                            borderTop: '1px dotted var(--border-subtle)',
                          }}
                        >
                          {offer.status === 'draft' || offer.status === 'pending_review' ? (
                            <button
                              onClick={() => handleOfferAction(offer.id, 'review')}
                              className="clay-btn clay-btn-secondary"
                              style={{ flex: 1, fontSize: '0.6875rem', padding: '0.25rem' }}
                            >
                              Review
                            </button>
                          ) : null}

                          {offer.status !== 'accepted' && offer.status !== 'rejected' && (
                            <button
                              onClick={() => handleOfferAction(offer.id, 'accept')}
                              className="clay-btn clay-btn-primary"
                              style={{ flex: 1, fontSize: '0.6875rem', padding: '0.25rem' }}
                            >
                              Accept (Deal)
                            </button>
                          )}

                          {offer.status !== 'rejected' && offer.status !== 'accepted' && (
                            <button
                              onClick={() => handleOfferAction(offer.id, 'reject')}
                              className="clay-btn-ghost"
                              style={{ fontSize: '0.6875rem', padding: '0.25rem', color: 'var(--status-error)' }}
                            >
                              Reject
                            </button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Workflow Audit Timeline */}
              {historyEvents.length > 0 && (
                <div>
                  <span className="label-compact" style={{ display: 'block', marginBottom: '0.5rem' }}>
                    Audit State Timeline ({historyEvents.length})
                  </span>
                  <div
                    style={{
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '0.375rem',
                      maxHeight: '160px',
                      overflowY: 'auto',
                    }}
                  >
                    {historyEvents.map((evt) => (
                      <div
                        key={evt.id}
                        style={{
                          padding: '0.375rem 0.5rem',
                          backgroundColor: 'var(--bg-subtle)',
                          borderRadius: '4px',
                          fontSize: '0.6875rem',
                          display: 'flex',
                          justifyContent: 'space-between',
                        }}
                      >
                        <span style={{ fontWeight: 600 }}>
                          {evt.from_state ? `${evt.from_state} → ` : ''}{evt.to_state}
                        </span>
                        <span className="tnum" style={{ color: 'var(--text-muted)' }}>
                          {formatDate(evt.created_at)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* MODAL: INITIATE RFQ */}
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
                    Commercial Negotiation
                  </span>
                  <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--primary)' }}>
                    Initiate Request for Quotation
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

              <form onSubmit={handleCreateRFQ} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <div>
                  <label className="label-compact" style={{ display: 'block', marginBottom: '0.375rem' }}>
                    Target Exchange Listing <span style={{ color: 'var(--status-error)' }}>*</span>
                  </label>
                  <select
                    value={selectedListingId}
                    onChange={(e) => setSelectedListingId(e.target.value)}
                    className="clay-select"
                    required
                  >
                    {listings.map((l) => (
                      <option key={l.listing_id} value={l.listing_id}>
                        {l.material_type || 'Industrial Scrap'} — {l.quantity} {l.unit} ({l.listing_id.slice(0, 8)}...)
                      </option>
                    ))}
                    {listings.length === 0 && (
                      <option value="">No active listings found</option>
                    )}
                  </select>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                  <div>
                    <label className="label-compact" style={{ display: 'block', marginBottom: '0.375rem' }}>
                      Requested Quantity (MT) <span style={{ color: 'var(--status-error)' }}>*</span>
                    </label>
                    <input
                      type="number"
                      step="0.1"
                      required
                      value={quantity}
                      onChange={(e) => setQuantity(parseFloat(e.target.value) || 0)}
                      className="clay-input"
                    />
                  </div>
                  <div>
                    <label className="label-compact" style={{ display: 'block', marginBottom: '0.375rem' }}>
                      Target Price / MT ($)
                    </label>
                    <input
                      type="number"
                      step="0.01"
                      value={targetPrice}
                      onChange={(e) => setTargetPrice(parseFloat(e.target.value) || 0)}
                      className="clay-input"
                    />
                  </div>
                </div>

                <div>
                  <label className="label-compact" style={{ display: 'block', marginBottom: '0.375rem' }}>
                    Commercial Specifications &amp; Delivery Logistics
                  </label>
                  <textarea
                    rows={3}
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    placeholder="Specify target delivery date, multimodal rail siding requirement, or packaging specifications..."
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
                    disabled={isSubmitting || !selectedListingId}
                    className="clay-btn clay-btn-primary"
                  >
                    {isSubmitting ? 'Submitting...' : 'Submit RFQ'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* MODAL: SUBMIT OFFER / QUOTE */}
        {offerModalOpen && (
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
                maxWidth: '500px',
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
                    Bilateral Quotation
                  </span>
                  <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--primary)' }}>
                    Submit Commercial Quote
                  </h2>
                </div>
                <button
                  onClick={() => setOfferModalOpen(false)}
                  className="clay-btn-ghost"
                  style={{ padding: '4px' }}
                >
                  <X size={18} />
                </button>
              </div>

              {offerError && (
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
                  {offerError}
                </div>
              )}

              <form onSubmit={handleSubmitOffer} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                  <div>
                    <label className="label-compact" style={{ display: 'block', marginBottom: '0.375rem' }}>
                      Offered Quantity <span style={{ color: 'var(--status-error)' }}>*</span>
                    </label>
                    <input
                      type="number"
                      step="0.1"
                      required
                      value={offeredQty}
                      onChange={(e) => setOfferedQty(parseFloat(e.target.value) || 0)}
                      className="clay-input"
                    />
                  </div>
                  <div>
                    <label className="label-compact" style={{ display: 'block', marginBottom: '0.375rem' }}>
                      Price Per Unit ($) <span style={{ color: 'var(--status-error)' }}>*</span>
                    </label>
                    <input
                      type="number"
                      step="0.01"
                      required
                      value={offerPrice}
                      onChange={(e) => setOfferPrice(parseFloat(e.target.value) || 0)}
                      className="clay-input"
                    />
                  </div>
                </div>

                <div>
                  <label className="label-compact" style={{ display: 'block', marginBottom: '0.375rem' }}>
                    Commercial &amp; Freight Terms
                  </label>
                  <input
                    type="text"
                    value={offerTerms}
                    onChange={(e) => setOfferTerms(e.target.value)}
                    placeholder="e.g. FOB Smelter Siding, 30 days net"
                    className="clay-input"
                  />
                </div>

                <div>
                  <label className="label-compact" style={{ display: 'block', marginBottom: '0.375rem' }}>
                    Seller Remarks
                  </label>
                  <textarea
                    rows={2}
                    value={offerNotes}
                    onChange={(e) => setOfferNotes(e.target.value)}
                    placeholder="Available for pickup within 5 business days..."
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
                    onClick={() => setOfferModalOpen(false)}
                    className="clay-btn clay-btn-ghost"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={isSubmittingOffer}
                    className="clay-btn clay-btn-primary"
                  >
                    {isSubmittingOffer ? 'Submitting Offer...' : 'Send Quote'}
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
