'use client';

import React, { Suspense, useEffect, useState } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import {
  FileText,
  Plus,
  Loader2,
  X,
  AlertCircle,
  ShieldCheck,
  Check,
  Ban,
  Clock,
} from 'lucide-react';
import { AppShell } from '@/components/AppShell';
import { Badge } from '@/components/Badge';
import { api, RFQ, Offer, MarketplaceListing } from '@/lib/api/client';
import { useAuth } from '@/lib/auth';
import { ApiErrorBoundary } from '@/components/ApiErrorBoundary';

function formatQuantity(val: number | string | undefined | null): string {
  if (val === undefined || val === null || val === '') return '0';
  const num = typeof val === 'number' ? val : parseFloat(val);
  if (isNaN(num)) return '0';
  return new Intl.NumberFormat('en-IN').format(num);
}

function formatPrice(val: number | string | undefined | null, currency: string = 'INR'): string {
  if (val === undefined || val === null || val === '') return 'Price upon request';
  const num = typeof val === 'number' ? val : parseFloat(val);
  if (isNaN(num)) return 'Price upon request';
  const sym = currency === 'USD' ? '$' : '₹';
  return `${sym}${new Intl.NumberFormat('en-IN').format(num)}`;
}

export default function RFQsPage() {
  return (
    <ApiErrorBoundary>
      <Suspense fallback={<div style={{ padding: '2rem', textAlign: 'center', color: '#6B7280' }}>Loading RFQs Workspace...</div>}>
        <RFQsContent />
      </Suspense>
    </ApiErrorBoundary>
  );
}

function RFQsContent() {
  const { user } = useAuth();
  const searchParams = useSearchParams();

  const [rfqs, setRfqs] = useState<RFQ[]>([]);
  const [listings, setListings] = useState<MarketplaceListing[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedRfq, setSelectedRfq] = useState<RFQ | null>(null);

  // Inspector Drawer data
  const [offers, setOffers] = useState<Offer[]>([]);
  const [historyEvents, setHistoryEvents] = useState<any[]>([]);
  const [loadingDetails, setLoadingDetails] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);

  // New RFQ Modal
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedListingId, setSelectedListingId] = useState('');
  const [quantity, setQuantity] = useState<number>(100);
  const [targetPrice, setTargetPrice] = useState<number>(500);
  const [notes, setNotes] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Submit Offer Modal
  const [offerModalOpen, setOfferModalOpen] = useState(false);
  const [offeredQty, setOfferedQty] = useState<number>(100);
  const [offerPrice, setOfferPrice] = useState<number>(480);
  const [offerTerms, setOfferTerms] = useState('FOB origin facility siding; 30-day payment term');
  const [offerNotes, setOfferNotes] = useState('');
  const [isSubmittingOffer, setIsSubmittingOffer] = useState(false);
  const [offerError, setOfferError] = useState<string | null>(null);

  const isFacilityManager = user?.role === 'facility_manager' || user?.role === 'admin';
  const roleTooltip = !isFacilityManager
    ? 'Action requires facility_manager or admin role permissions'
    : undefined;

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
      const [rfqRes, listingsRes] = await Promise.allSettled([
        api.exchange.listRFQs(),
        api.marketplace.getListings({ view: 'all' }),
      ]);

      const rfqList = rfqRes.status === 'fulfilled' ? rfqRes.value.items || [] : [];
      setRfqs(rfqList);

      const listingList = listingsRes.status === 'fulfilled' ? listingsRes.value.items || [] : [];
      setListings(listingList);

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
        const [offersRes, historyRes] = await Promise.allSettled([
          api.exchange.listRFQOffers(selectedRfq!.rfq_id),
          api.exchange.getRFQHistory(selectedRfq!.rfq_id),
        ]);
        setOffers(offersRes.status === 'fulfilled' ? offersRes.value || [] : []);
        setHistoryEvents(historyRes.status === 'fulfilled' ? historyRes.value || [] : []);
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
      setFormError('Please choose a valid exchange listing.');
      return;
    }

    setIsSubmitting(true);
    setFormError(null);
    try {
      const created = await api.exchange.createRFQ({
        listing_id: selectedListingId,
        requested_quantity: quantity,
        target_price_per_unit: targetPrice || undefined,
        notes: notes || undefined,
      });

      await loadData();
      setSelectedRfq(created);
      setModalOpen(false);
    } catch (err: any) {
      setFormError(err?.message || 'Failed to initiate RFQ.');
    } finally {
      setIsSubmitting(false);
    }
  };

  // RFQ State Transitions
  const handleApproveRFQ = async () => {
    if (!selectedRfq) return;
    setActionLoading(true);
    try {
      const approved = await api.exchange.approveRFQ(selectedRfq.rfq_id);
      setSelectedRfq(approved);
      await loadData();
    } catch (err: any) {
      alert(err?.message || 'Failed to approve RFQ');
    } finally {
      setActionLoading(false);
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
        unit: selectedRfq.unit || 'MT',
        price_per_unit: offerPrice,
        currency: 'INR',
        terms: offerTerms,
        notes: offerNotes || undefined,
      });

      const updatedOffers = await api.exchange.listRFQOffers(selectedRfq.rfq_id);
      setOffers(updatedOffers || []);
      setOfferModalOpen(false);
    } catch (err: any) {
      setOfferError(err?.message || 'Failed to submit commercial offer.');
    } finally {
      setIsSubmittingOffer(false);
    }
  };

  // Accept Offer
  const handleAcceptOffer = async (offerId: string) => {
    if (!confirm('Accepting this commercial offer executes a legally binding bilateral agreement and will reject all other offers. Proceed?')) {
      return;
    }
    setActionLoading(true);
    try {
      await api.exchange.acceptOffer(offerId);
      // Refresh offers and RFQ
      if (selectedRfq) {
        const [updatedRfq, updatedOffers] = await Promise.all([
          api.exchange.getRFQ(selectedRfq.rfq_id),
          api.exchange.listRFQOffers(selectedRfq.rfq_id),
        ]);
        setSelectedRfq(updatedRfq);
        setOffers(updatedOffers);
      }
      await loadData();
    } catch (err: any) {
      alert(err?.message || 'Failed to accept offer');
    } finally {
      setActionLoading(false);
    }
  };

  const getStatusBadge = (status: string) => {
    const s = (status || '').toUpperCase();
    switch (s) {
      case 'OPEN':
        return <Badge variant="success" dot>OPEN</Badge>;
      case 'PENDING_APPROVAL':
      case 'SUBMITTED':
        return <Badge variant="warning" dot>PENDING_APPROVAL</Badge>;
      case 'ACCEPTED':
        return <Badge variant="teal" dot>ACCEPTED</Badge>;
      case 'OFFERS_RECEIVED':
        return <Badge variant="warning" dot>OFFERS_RECEIVED</Badge>;
      case 'CANCELLED':
      case 'REJECTED':
        return <Badge variant="error">CANCELLED</Badge>;
      default:
        return <Badge variant="neutral">{s || 'DRAFT'}</Badge>;
    }
  };

  return (
    <AppShell>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
        {/* Header */}
        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: '1rem' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
              <span className="label-compact" style={{ color: '#0F4C81' }}>Bilateral Negotiation Workspace</span>
              <span style={{ color: '#9CA3AF' }}>·</span>
              <span className="label-compact" style={{ color: '#6B7280' }}>Human In-the-Loop Approval Gates</span>
            </div>
            <h1 style={{ fontSize: '1.75rem', fontWeight: 600, color: '#1A1A1A', letterSpacing: '-0.015em' }}>
              Requests for Quotation (RFQs) &amp; Offers
            </h1>
            <p style={{ fontSize: '0.875rem', color: '#4B5563' }}>
              Negotiate price per unit, tonnage allotments, delivery terms, and review binding commercial offers.
            </p>
          </div>

          <button
            onClick={() => setModalOpen(true)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              backgroundColor: '#0F4C81',
              color: '#FFFFFF',
              border: 'none',
              borderRadius: '6px',
              padding: '0.5rem 1rem',
              fontSize: '0.875rem',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            <Plus size={16} />
            <span>Initiate RFQ</span>
          </button>
        </div>

        {/* Layout: RFQ Table + Detail Inspector */}
        <div style={{ display: 'grid', gridTemplateColumns: selectedRfq ? '1fr 400px' : '1fr', gap: '1.25rem', alignItems: 'start' }}>
          {/* Main Table */}
          <div className="strata-table-container" style={{ backgroundColor: '#FFFFFF', borderRadius: '8px', border: '1px solid #E5E7EB', overflowX: 'auto' }}>
            <table className="strata-table" style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid #E5E7EB', backgroundColor: '#F9FAFB', textAlign: 'left' }}>
                  <th style={{ padding: '0.75rem 1rem' }}>RFQ Identifier</th>
                  <th style={{ padding: '0.75rem 1rem' }}>Target Listing</th>
                  <th style={{ padding: '0.75rem 1rem' }}>Volume</th>
                  <th style={{ padding: '0.75rem 1rem' }}>Target Price</th>
                  <th style={{ padding: '0.75rem 1rem' }}>Status</th>
                  <th style={{ padding: '0.75rem 1rem' }}>Created</th>
                </tr>
              </thead>
              <tbody>
                {isLoading ? (
                  <tr>
                    <td colSpan={6} style={{ textAlign: 'center', padding: '3rem' }}>
                      <Loader2 size={24} className="animate-spin" style={{ margin: '0 auto', color: '#0F4C81' }} />
                    </td>
                  </tr>
                ) : rfqs.length === 0 ? (
                  <tr>
                    <td colSpan={6} style={{ textAlign: 'center', padding: '3.5rem 1rem', color: '#6B7280' }}>
                      <FileText size={36} style={{ margin: '0 auto 0.5rem auto', opacity: 0.4 }} />
                      <div style={{ fontWeight: 600, color: '#1A1A1A' }}>No RFQs Found</div>
                      <div style={{ fontSize: '0.8125rem', marginTop: '0.25rem' }}>
                        Browse the Circular Marketplace to initiate requests for quotation on active listings.
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
                          backgroundColor: isSelected ? '#EFF6FF' : 'transparent',
                          cursor: 'pointer',
                          borderBottom: '1px solid #F3F4F6',
                        }}
                      >
                        <td style={{ padding: '0.75rem 1rem', fontFamily: 'monospace', fontWeight: 600 }}>
                          RFQ-{rfq.rfq_id.slice(0, 8)}
                        </td>
                        <td style={{ padding: '0.75rem 1rem', color: '#4B5563' }}>
                          {rfq.listing_id ? `Lot ${rfq.listing_id.slice(0, 8)}...` : 'Direct Inquiry'}
                        </td>
                        <td style={{ padding: '0.75rem 1rem' }}>
                          <strong>{formatQuantity(rfq.requested_quantity)}</strong> {rfq.unit || 'MT'}
                        </td>
                        <td style={{ padding: '0.75rem 1rem' }}>
                          {formatPrice(rfq.target_price_per_unit, 'INR')}
                        </td>
                        <td style={{ padding: '0.75rem 1rem' }}>{getStatusBadge(rfq.status)}</td>
                        <td style={{ padding: '0.75rem 1rem', fontSize: '0.75rem', color: '#6B7280' }}>
                          {rfq.created_at ? new Date(rfq.created_at).toLocaleDateString('en-IN') : 'Recent'}
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
              style={{
                padding: '1.25rem',
                backgroundColor: '#FFFFFF',
                borderRadius: '8px',
                border: '1px solid #E5E7EB',
                display: 'flex',
                flexDirection: 'column',
                gap: '1.25rem',
                boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingBottom: '0.75rem', borderBottom: '1px solid #E5E7EB' }}>
                <div>
                  <span style={{ fontSize: '0.75rem', fontWeight: 600, color: '#0F4C81', textTransform: 'uppercase' }}>Negotiation Dossier</span>
                  <h3 style={{ fontSize: '1.125rem', fontWeight: 700, color: '#1A1A1A' }}>
                    RFQ-{selectedRfq.rfq_id.slice(0, 10)}
                  </h3>
                </div>
                <button
                  onClick={() => setSelectedRfq(null)}
                  style={{ background: 'none', border: 'none', color: '#6B7280', cursor: 'pointer', padding: '4px' }}
                >
                  <X size={18} />
                </button>
              </div>

              {/* Status & Volume Summary */}
              <div style={{ padding: '0.875rem', borderRadius: '6px', backgroundColor: '#F8F9FA', border: '1px solid #E5E7EB', display: 'flex', flexDirection: 'column', gap: '0.5rem', fontSize: '0.8125rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ color: '#6B7280' }}>Status:</span>
                  {getStatusBadge(selectedRfq.status)}
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#6B7280' }}>Buyer Organization:</span>
                  <span style={{ fontWeight: 600, color: '#1A1A1A' }}>{selectedRfq.buyer_org_name || selectedRfq.buyer_org_id || 'Procuring Partner'}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#6B7280' }}>Seller Organization:</span>
                  <span style={{ fontWeight: 600, color: '#1A1A1A' }}>{selectedRfq.seller_org_name || selectedRfq.seller_org_id || 'Generating Facility'}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#6B7280' }}>Requested Quantity:</span>
                  <span style={{ fontWeight: 600, color: '#1A1A1A' }}>
                    {formatQuantity(selectedRfq.requested_quantity)} {selectedRfq.unit || 'MT'}
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#6B7280' }}>Target Price:</span>
                  <span style={{ fontWeight: 700, color: '#0F4C81' }}>
                    {formatPrice(selectedRfq.target_price_per_unit, 'INR')} / {selectedRfq.unit || 'MT'}
                  </span>
                </div>
                {selectedRfq.notes && (
                  <div style={{ marginTop: '0.25rem', borderTop: '1px solid #E5E7EB', paddingTop: '0.375rem' }}>
                    <span style={{ color: '#6B7280' }}>Specs: </span>
                    <span style={{ color: '#374151' }}>{selectedRfq.notes}</span>
                  </div>
                )}
              </div>

              {/* RFQ Workflow Approval Button */}
              {['DRAFT', 'PENDING_APPROVAL', 'SUBMITTED'].includes(selectedRfq.status?.toUpperCase()) && (
                <div>
                  <button
                    onClick={handleApproveRFQ}
                    disabled={!isFacilityManager || actionLoading}
                    title={roleTooltip}
                    style={{
                      width: '100%',
                      backgroundColor: isFacilityManager ? '#0F4C81' : '#9CA3AF',
                      color: '#FFFFFF',
                      border: 'none',
                      borderRadius: '6px',
                      padding: '0.625rem',
                      fontSize: '0.875rem',
                      fontWeight: 600,
                      cursor: isFacilityManager && !actionLoading ? 'pointer' : 'not-allowed',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '0.5rem',
                    }}
                  >
                    {actionLoading ? <Loader2 size={16} className="animate-spin" /> : <ShieldCheck size={16} />}
                    <span>{actionLoading ? 'Approving RFQ...' : 'Approve RFQ (Gate)'}</span>
                  </button>
                  {!isFacilityManager && (
                    <div style={{ fontSize: '0.6875rem', color: '#B45309', marginTop: '0.25rem', textAlign: 'center' }}>
                      ⚠️ Approval gate requires facility_manager role.
                    </div>
                  )}
                </div>
              )}

              {/* Offers Section */}
              <div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.625rem' }}>
                  <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#374151', textTransform: 'uppercase' }}>
                    Commercial Offers ({offers.length})
                  </span>
                  <button
                    onClick={() => setOfferModalOpen(true)}
                    style={{
                      backgroundColor: '#FFFFFF',
                      border: '1px solid #D1D5DB',
                      borderRadius: '4px',
                      padding: '0.25rem 0.5rem',
                      fontSize: '0.75rem',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.25rem',
                    }}
                  >
                    <Plus size={12} />
                    <span>Submit Offer</span>
                  </button>
                </div>

                {loadingDetails ? (
                  <div style={{ padding: '1rem', textAlign: 'center' }}>
                    <Loader2 size={18} className="animate-spin" style={{ margin: '0 auto', color: '#0F4C81' }} />
                  </div>
                ) : offers.length === 0 ? (
                  <div style={{ padding: '1.25rem', textAlign: 'center', color: '#6B7280', backgroundColor: '#F9FAFB', borderRadius: '6px', fontSize: '0.8125rem' }}>
                    No offers received yet. Click &quot;Submit Offer&quot; to propose quotation terms.
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.625rem' }}>
                    {offers.map((offer) => {
                      const isOfferPending = ['PENDING', 'SUBMITTED', 'DRAFT', 'UNDER_REVIEW'].includes(offer.status?.toUpperCase());
                      return (
                        <div
                          key={offer.offer_id}
                          style={{
                            padding: '0.75rem',
                            borderRadius: '6px',
                            border: '1px solid #E5E7EB',
                            backgroundColor: '#FFFFFF',
                            fontSize: '0.8125rem',
                            display: 'flex',
                            flexDirection: 'column',
                            gap: '0.375rem',
                          }}
                        >
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <span style={{ fontWeight: 700, fontSize: '0.9375rem', color: '#0F4C81' }}>
                              {formatPrice(offer.price_per_unit, offer.currency || 'INR')} / {offer.unit}
                            </span>
                            <span
                              style={{
                                padding: '0.125rem 0.375rem',
                                borderRadius: '4px',
                                fontSize: '0.6875rem',
                                fontWeight: 600,
                                backgroundColor: offer.status === 'ACCEPTED' ? '#ECFDF5' : offer.status === 'REJECTED' ? '#FEF2F2' : '#EFF6FF',
                                color: offer.status === 'ACCEPTED' ? '#065F46' : offer.status === 'REJECTED' ? '#B91C1C' : '#1E40AF',
                              }}
                            >
                              {offer.status || 'PENDING'}
                            </span>
                          </div>

                          <div style={{ color: '#4B5563' }}>
                            Offered Volume: <strong>{formatQuantity(offer.offered_quantity)}</strong> {offer.unit}
                          </div>

                          <div style={{ fontSize: '0.6875rem', color: '#6B7280', fontFamily: 'monospace' }}>
                            Offer ID: {offer.offer_id.slice(0, 12)}…
                          </div>

                          {offer.terms && (
                            <div style={{ color: '#6B7280', fontSize: '0.75rem' }}>
                              Terms: {offer.terms}
                            </div>
                          )}

                          {/* Accept Offer Button with Role Check & Confirmation */}
                          {isOfferPending && selectedRfq.status?.toUpperCase() !== 'ACCEPTED' && (
                            <div style={{ marginTop: '0.5rem', paddingTop: '0.5rem', borderTop: '1px solid #F3F4F6' }}>
                              <button
                                onClick={() => handleAcceptOffer(offer.offer_id)}
                                disabled={!isFacilityManager || actionLoading}
                                title={roleTooltip}
                                style={{
                                  width: '100%',
                                  backgroundColor: isFacilityManager ? '#059669' : '#9CA3AF',
                                  color: '#FFFFFF',
                                  border: 'none',
                                  borderRadius: '4px',
                                  padding: '0.375rem 0.625rem',
                                  fontSize: '0.75rem',
                                  fontWeight: 600,
                                  cursor: isFacilityManager && !actionLoading ? 'pointer' : 'not-allowed',
                                  display: 'flex',
                                  alignItems: 'center',
                                  justifyContent: 'center',
                                  gap: '0.375rem',
                                }}
                              >
                                <Check size={14} />
                                <span>Accept Offer (Execute Deal)</span>
                              </button>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
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
              backgroundColor: 'rgba(0, 0, 0, 0.4)',
              backdropFilter: 'blur(3px)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              padding: '1rem',
            }}
          >
            <div
              style={{
                width: '100%',
                maxWidth: '520px',
                backgroundColor: '#FFFFFF',
                borderRadius: '8px',
                padding: '1.75rem',
                position: 'relative',
                boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingBottom: '0.875rem', borderBottom: '1px solid #E5E7EB', marginBottom: '1.25rem' }}>
                <div>
                  <span style={{ fontSize: '0.75rem', fontWeight: 600, color: '#0F4C81', textTransform: 'uppercase' }}>Commercial Inquiry</span>
                  <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#1A1A1A', marginTop: '0.125rem' }}>Initiate Request for Quotation</h2>
                </div>
                <button onClick={() => setModalOpen(false)} style={{ background: 'none', border: 'none', color: '#6B7280', cursor: 'pointer' }}>
                  <X size={18} />
                </button>
              </div>

              {formError && (
                <div style={{ padding: '0.625rem 0.875rem', borderRadius: '6px', backgroundColor: '#FEF2F2', color: '#B91C1C', fontSize: '0.8125rem', marginBottom: '1rem' }}>
                  {formError}
                </div>
              )}

              <form onSubmit={handleCreateRFQ} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.8125rem', fontWeight: 600, color: '#374151', marginBottom: '0.375rem' }}>
                    Target Marketplace Listing <span style={{ color: '#DC2626' }}>*</span>
                  </label>
                  <select
                    value={selectedListingId}
                    onChange={(e) => setSelectedListingId(e.target.value)}
                    style={{ width: '100%', padding: '0.5rem', borderRadius: '6px', border: '1px solid #D1D5DB', fontSize: '0.875rem' }}
                    required
                  >
                    <option value="">Select an active listing...</option>
                    {listings.map((l) => (
                      <option key={l.listing_id} value={l.listing_id}>
                        {l.material_type || l.lot?.material_type || 'Material'} — {formatQuantity(l.quantity)} {l.unit} ({l.listing_id.slice(0, 8)}...)
                      </option>
                    ))}
                  </select>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.8125rem', fontWeight: 600, color: '#374151', marginBottom: '0.375rem' }}>
                      Requested Quantity (MT) <span style={{ color: '#DC2626' }}>*</span>
                    </label>
                    <input
                      type="number"
                      step="0.1"
                      required
                      value={quantity}
                      onChange={(e) => setQuantity(parseFloat(e.target.value) || 0)}
                      style={{ width: '100%', padding: '0.5rem', borderRadius: '6px', border: '1px solid #D1D5DB', fontSize: '0.875rem' }}
                    />
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.8125rem', fontWeight: 600, color: '#374151', marginBottom: '0.375rem' }}>
                      Target Price / MT (₹)
                    </label>
                    <input
                      type="number"
                      step="0.01"
                      value={targetPrice}
                      onChange={(e) => setTargetPrice(parseFloat(e.target.value) || 0)}
                      style={{ width: '100%', padding: '0.5rem', borderRadius: '6px', border: '1px solid #D1D5DB', fontSize: '0.875rem' }}
                    />
                  </div>
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.8125rem', fontWeight: 600, color: '#374151', marginBottom: '0.375rem' }}>
                    Commercial Logistics &amp; Specifications
                  </label>
                  <textarea
                    rows={3}
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    placeholder="Specify delivery timeline, quality grading, and multimodal freight requirements..."
                    style={{ width: '100%', padding: '0.5rem', borderRadius: '6px', border: '1px solid #D1D5DB', fontSize: '0.875rem', resize: 'vertical' }}
                  />
                </div>

                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '0.75rem', paddingTop: '0.875rem', borderTop: '1px solid #E5E7EB' }}>
                  <button
                    type="button"
                    onClick={() => setModalOpen(false)}
                    style={{ backgroundColor: '#FFFFFF', border: '1px solid #D1D5DB', borderRadius: '6px', padding: '0.5rem 1rem', fontSize: '0.875rem', cursor: 'pointer' }}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={isSubmitting || !selectedListingId}
                    style={{ backgroundColor: '#0F4C81', color: '#FFFFFF', border: 'none', borderRadius: '6px', padding: '0.5rem 1rem', fontSize: '0.875rem', fontWeight: 600, cursor: isSubmitting ? 'not-allowed' : 'pointer' }}
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
              backgroundColor: 'rgba(0, 0, 0, 0.4)',
              backdropFilter: 'blur(3px)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              padding: '1rem',
            }}
          >
            <div
              style={{
                width: '100%',
                maxWidth: '500px',
                backgroundColor: '#FFFFFF',
                borderRadius: '8px',
                padding: '1.75rem',
                position: 'relative',
                boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingBottom: '0.875rem', borderBottom: '1px solid #E5E7EB', marginBottom: '1.25rem' }}>
                <div>
                  <span style={{ fontSize: '0.75rem', fontWeight: 600, color: '#0F4C81', textTransform: 'uppercase' }}>Quotation Submission</span>
                  <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#1A1A1A', marginTop: '0.125rem' }}>Submit Commercial Offer</h2>
                </div>
                <button onClick={() => setOfferModalOpen(false)} style={{ background: 'none', border: 'none', color: '#6B7280', cursor: 'pointer' }}>
                  <X size={18} />
                </button>
              </div>

              {offerError && (
                <div style={{ padding: '0.625rem 0.875rem', borderRadius: '6px', backgroundColor: '#FEF2F2', color: '#B91C1C', fontSize: '0.8125rem', marginBottom: '1rem' }}>
                  {offerError}
                </div>
              )}

              <form onSubmit={handleSubmitOffer} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.8125rem', fontWeight: 600, color: '#374151', marginBottom: '0.375rem' }}>
                      Offered Quantity ({selectedRfq?.unit || 'MT'}) <span style={{ color: '#DC2626' }}>*</span>
                    </label>
                    <input
                      type="number"
                      step="0.1"
                      required
                      value={offeredQty}
                      onChange={(e) => setOfferedQty(parseFloat(e.target.value) || 0)}
                      style={{ width: '100%', padding: '0.5rem', borderRadius: '6px', border: '1px solid #D1D5DB', fontSize: '0.875rem' }}
                    />
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.8125rem', fontWeight: 600, color: '#374151', marginBottom: '0.375rem' }}>
                      Price Per Unit (₹) <span style={{ color: '#DC2626' }}>*</span>
                    </label>
                    <input
                      type="number"
                      step="0.01"
                      required
                      value={offerPrice}
                      onChange={(e) => setOfferPrice(parseFloat(e.target.value) || 0)}
                      style={{ width: '100%', padding: '0.5rem', borderRadius: '6px', border: '1px solid #D1D5DB', fontSize: '0.875rem' }}
                    />
                  </div>
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.8125rem', fontWeight: 600, color: '#374151', marginBottom: '0.375rem' }}>
                    Commercial &amp; Freight Terms
                  </label>
                  <input
                    type="text"
                    value={offerTerms}
                    onChange={(e) => setOfferTerms(e.target.value)}
                    style={{ width: '100%', padding: '0.5rem', borderRadius: '6px', border: '1px solid #D1D5DB', fontSize: '0.875rem' }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.8125rem', fontWeight: 600, color: '#374151', marginBottom: '0.375rem' }}>
                    Seller Remarks
                  </label>
                  <textarea
                    rows={2}
                    value={offerNotes}
                    onChange={(e) => setOfferNotes(e.target.value)}
                    placeholder="Dispatched from Surat cluster siding, loading within 48h..."
                    style={{ width: '100%', padding: '0.5rem', borderRadius: '6px', border: '1px solid #D1D5DB', fontSize: '0.875rem', resize: 'vertical' }}
                  />
                </div>

                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '0.75rem', paddingTop: '0.875rem', borderTop: '1px solid #E5E7EB' }}>
                  <button
                    type="button"
                    onClick={() => setOfferModalOpen(false)}
                    style={{ backgroundColor: '#FFFFFF', border: '1px solid #D1D5DB', borderRadius: '6px', padding: '0.5rem 1rem', fontSize: '0.875rem', cursor: 'pointer' }}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={isSubmittingOffer}
                    style={{ backgroundColor: '#0F4C81', color: '#FFFFFF', border: 'none', borderRadius: '6px', padding: '0.5rem 1rem', fontSize: '0.875rem', fontWeight: 600, cursor: isSubmittingOffer ? 'not-allowed' : 'pointer' }}
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
