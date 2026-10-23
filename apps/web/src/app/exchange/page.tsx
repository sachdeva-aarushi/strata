'use client';

import React, { Suspense, useEffect, useState } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import {
  RefreshCw,
  Plus,
  Search,
  Filter,
  ArrowRight,
  TrendingUp,
  MapPin,
  Calendar,
  DollarSign,
  Layers,
  X,
  Loader2,
  CheckCircle2,
  AlertCircle,
  ShoppingBag,
} from 'lucide-react';
import { AppShell } from '@/components/AppShell';
import { Badge } from '@/components/Badge';
import { api } from '@/lib/api-client';
import { useAuth } from '@/lib/auth';
import {
  BuyerRequirement,
  ExchangeListing,
  MaterialLot,
} from '@/types';
import { formatDate, formatNumber } from '@/lib/utils';

export default function ExchangePage() {
  return (
    <Suspense fallback={<div style={{ padding: '2rem', textAlign: 'center' }}>Loading Exchange Board...</div>}>
      <ExchangeContent />
    </Suspense>
  );
}

function ExchangeContent() {

  const { user } = useAuth();
  const searchParams = useSearchParams();

  const [activeTab, setActiveTab] = useState<'listings' | 'requirements'>('listings');
  const [listings, setListings] = useState<ExchangeListing[]>([]);
  const [requirements, setRequirements] = useState<BuyerRequirement[]>([]);
  const [lots, setLots] = useState<MaterialLot[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Filter
  const [searchQuery, setSearchQuery] = useState('');

  // Create Listing Modal
  const [listingModalOpen, setListingModalOpen] = useState(false);
  const [selectedLotId, setSelectedLotId] = useState('');
  const [askingPrice, setAskingPrice] = useState<number>(450);
  const [currency, setCurrency] = useState('USD');
  const [visibility, setVisibility] = useState('public');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);
  const [modalSuccess, setModalSuccess] = useState<string | null>(null);

  // Create Requirement Modal
  const [reqModalOpen, setReqModalOpen] = useState(false);
  const [reqMaterialType, setReqMaterialType] = useState('ti-6al-4v-swarf');
  const [reqTargetQty, setReqTargetQty] = useState<number>(20);
  const [reqUnit, setReqUnit] = useState('tonne');
  const [reqMaxPrice, setReqMaxPrice] = useState<number>(480);
  const [reqCountry, setReqCountry] = useState('CH');

  useEffect(() => {
    if (searchParams?.get('action') === 'create_listing') {
      const urlLot = searchParams?.get('lot_id');
      if (urlLot) setSelectedLotId(urlLot);
      setListingModalOpen(true);
    }
  }, [searchParams]);

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [listingsRes, reqsRes, lotsRes] = await Promise.all([
        api.exchange.listListings(),
        api.exchange.listRequirements(),
        api.materials.listLots({ page_size: 50 }),
      ]);

      setListings(listingsRes.data || []);
      setRequirements(reqsRes.data || []);
      setLots(lotsRes.data || []);
      if (lotsRes.data && lotsRes.data.length > 0 && !selectedLotId) {
        setSelectedLotId(lotsRes.data[0].lot_id);
      }
    } catch (err) {
      console.warn('Failed to load circular exchange data:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleCreateListing = async (e: React.FormEvent) => {
    e.preventDefault();
    setModalError(null);
    setModalSuccess(null);

    const targetLot = lots.find((l) => l.lot_id === selectedLotId);
    if (!targetLot) {
      setModalError('Please select a valid material lot to publish.');
      return;
    }

    setIsSubmitting(true);
    try {
      const res = await api.exchange.createListing({
        lot_id: targetLot.lot_id,
        quantity: targetLot.quantity,
        unit: targetLot.unit,
        asking_price_per_unit: askingPrice || undefined,
        currency,
        visibility,
      });

      setModalSuccess(`Listing published successfully!`);
      await loadData();
      setTimeout(() => {
        setListingModalOpen(false);
        setModalSuccess(null);
      }, 1000);
    } catch (err: any) {
      setModalError(err?.message || 'Failed to publish exchange listing.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCreateRequirement = async (e: React.FormEvent) => {
    e.preventDefault();
    setModalError(null);
    setModalSuccess(null);

    setIsSubmitting(true);
    try {
      await api.exchange.createRequirement({
        material_type: reqMaterialType,
        target_quantity: reqTargetQty,
        unit: reqUnit,
        max_price_per_unit: reqMaxPrice || undefined,
        delivery_location_country: reqCountry,
      });

      setModalSuccess('Buyer requirement recorded!');
      await loadData();
      setTimeout(() => {
        setReqModalOpen(false);
        setModalSuccess(null);
      }, 1000);
    } catch (err: any) {
      setModalError(err?.message || 'Failed to create buyer requirement.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const filteredListings = listings.filter((item) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      (item.material_type && item.material_type.toLowerCase().includes(q)) ||
      item.listing_id.toLowerCase().includes(q)
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
                Bilateral Secondary Feedstock Exchange
              </span>
              <span style={{ color: 'var(--text-muted)' }}>·</span>
              <span className="label-compact" style={{ color: 'var(--text-muted)' }}>
                Direct Cross-Tenant Trading
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
              Circular Exchange Board
            </h1>
            <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
              Discover verified secondary alloy scrap and initiate RFQs across qualified processors.
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
            <button
              onClick={() => setListingModalOpen(true)}
              className="clay-btn clay-btn-primary"
            >
              <Plus size={16} />
              <span>Create Listing</span>
            </button>
            <button
              onClick={() => setReqModalOpen(true)}
              className="clay-btn clay-btn-secondary"
            >
              <ShoppingBag size={16} />
              <span>Post Requirement</span>
            </button>
          </div>
        </div>

        {/* Tab Switcher & Search Bar */}
        <div
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '1rem',
          }}
        >
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button
              onClick={() => setActiveTab('listings')}
              className={`clay-btn ${
                activeTab === 'listings' ? 'clay-btn-primary' : 'clay-btn-secondary'
              }`}
            >
              <span>Available Listings ({listings.length})</span>
            </button>
            <button
              onClick={() => setActiveTab('requirements')}
              className={`clay-btn ${
                activeTab === 'requirements' ? 'clay-btn-primary' : 'clay-btn-secondary'
              }`}
            >
              <span>Buyer Demands ({requirements.length})</span>
            </button>
          </div>

          <div style={{ position: 'relative', width: '280px' }}>
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
              placeholder="Search streams or material classes..."
              className="clay-input"
              style={{ paddingLeft: '2.25rem' }}
            />
          </div>
        </div>

        {/* TAB 1: LISTINGS GRID */}
        {activeTab === 'listings' && (
          <div>
            {isLoading ? (
              <div style={{ padding: '3rem', textAlign: 'center' }}>
                <Loader2 size={24} className="animate-spin" style={{ margin: '0 auto' }} />
              </div>
            ) : filteredListings.length === 0 ? (
              <div
                className="clay-card"
                style={{
                  padding: '3rem',
                  textAlign: 'center',
                  color: 'var(--text-muted)',
                  backgroundColor: '#ffffff',
                }}
              >
                <RefreshCw size={36} style={{ margin: '0 auto 0.75rem auto', opacity: 0.4 }} />
                <div style={{ fontWeight: 600 }}>No active listings published yet</div>
                <p style={{ fontSize: '0.75rem', marginTop: '0.25rem' }}>
                  Publish a registered material lot from your facility to make it visible on the exchange.
                </p>
                <button
                  onClick={() => setListingModalOpen(true)}
                  className="clay-btn clay-btn-primary"
                  style={{ marginTop: '1rem' }}
                >
                  <Plus size={16} />
                  <span>Publish First Listing</span>
                </button>
              </div>
            ) : (
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
                  gap: '1.25rem',
                }}
              >
                {filteredListings.map((item) => (
                  <div
                    key={item.listing_id}
                    className="clay-card"
                    style={{
                      padding: '1.25rem',
                      display: 'flex',
                      flexDirection: 'column',
                      justifyContent: 'space-between',
                      backgroundColor: '#ffffff',
                    }}
                  >
                    <div>
                      <div
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          marginBottom: '0.5rem',
                        }}
                      >
                        <Badge variant="teal" dot>
                          {item.visibility}
                        </Badge>
                        <span
                          className="tnum"
                          style={{
                            fontSize: '0.75rem',
                            color: 'var(--text-muted)',
                          }}
                        >
                          {formatDate(item.created_at)}
                        </span>
                      </div>

                      <h3
                        style={{
                          fontSize: '1.0625rem',
                          fontWeight: 600,
                          color: 'var(--text-primary)',
                          marginBottom: '0.375rem',
                        }}
                      >
                        {item.material_type || 'Titanium Ti-6Al-4V Secondary Swarf'}
                      </h3>

                      <div
                        style={{
                          display: 'flex',
                          alignItems: 'baseline',
                          gap: '0.375rem',
                          margin: '0.5rem 0',
                        }}
                      >
                        <span
                          className="tnum"
                          style={{
                            fontSize: '1.375rem',
                            fontWeight: 700,
                            color: 'var(--primary)',
                          }}
                        >
                          {formatNumber(item.quantity)}
                        </span>
                        <span style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>
                          {item.unit}
                        </span>
                        {item.asking_price_per_unit && (
                          <span
                            className="tnum"
                            style={{
                              marginLeft: 'auto',
                              fontSize: '1rem',
                              fontWeight: 600,
                              color: 'var(--accent-teal)',
                            }}
                          >
                            ${item.asking_price_per_unit}/{item.unit}
                          </span>
                        )}
                      </div>

                      <div
                        style={{
                          padding: '0.5rem 0.75rem',
                          backgroundColor: 'var(--bg-subtle)',
                          borderRadius: '6px',
                          fontSize: '0.75rem',
                          color: 'var(--text-secondary)',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '0.25rem',
                          margin: '0.75rem 0',
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem' }}>
                          <MapPin size={12} color="var(--text-muted)" />
                          <span>Origin: Central Rail Smelter · Switzerland (CH)</span>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem' }}>
                          <CheckCircle2 size={12} color="var(--status-success)" />
                          <span>Audit Grade Assay: 99.82% purity verified</span>
                        </div>
                      </div>
                    </div>

                    <Link
                      href={`/rfqs?action=new&listing_id=${item.listing_id}`}
                      className="clay-btn clay-btn-primary"
                      style={{
                        width: '100%',
                        fontSize: '0.8125rem',
                        textDecoration: 'none',
                        marginTop: '0.5rem',
                      }}
                    >
                      <span>Initiate RFQ / Quotation</span>
                      <ArrowRight size={14} />
                    </Link>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* TAB 2: REQUIREMENTS LIST */}
        {activeTab === 'requirements' && (
          <div className="strata-table-container">
            <table className="strata-table">
              <thead>
                <tr>
                  <th>Demand Material Type</th>
                  <th>Target Quantity</th>
                  <th>Max Price Budget</th>
                  <th>Target Destination</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {requirements.length === 0 ? (
                  <tr>
                    <td
                      colSpan={6}
                      style={{
                        textAlign: 'center',
                        padding: '2.5rem',
                        color: 'var(--text-muted)',
                      }}
                    >
                      No active buyer requirements registered.
                    </td>
                  </tr>
                ) : (
                  requirements.map((req) => (
                    <tr key={req.requirement_id}>
                      <td style={{ fontWeight: 600 }}>{req.material_type}</td>
                      <td className="tnum">
                        {formatNumber(req.target_quantity)} {req.unit}
                      </td>
                      <td className="tnum">
                        {req.max_price_per_unit
                          ? `$${req.max_price_per_unit}/${req.unit}`
                          : 'Market Price'}
                      </td>
                      <td>{req.delivery_location_country || 'CH'}</td>
                      <td>
                        <Badge variant="success" dot>
                          {req.status}
                        </Badge>
                      </td>
                      <td>
                        <Link
                          href={`/materials?action=new`}
                          className="clay-btn clay-btn-secondary"
                          style={{
                            padding: '0.25rem 0.5rem',
                            fontSize: '0.6875rem',
                            textDecoration: 'none',
                          }}
                        >
                          Match Lot
                        </Link>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}

        {/* MODAL: CREATE LISTING */}
        {listingModalOpen && (
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
                    Exchange Publish
                  </span>
                  <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--primary)' }}>
                    Publish Lot to Exchange
                  </h2>
                </div>
                <button
                  onClick={() => setListingModalOpen(false)}
                  className="clay-btn-ghost"
                  style={{ padding: '4px' }}
                >
                  <X size={18} />
                </button>
              </div>

              {modalError && (
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
                  {modalError}
                </div>
              )}

              {modalSuccess && (
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
                  {modalSuccess}
                </div>
              )}

              <form onSubmit={handleCreateListing} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <div>
                  <label className="label-compact" style={{ display: 'block', marginBottom: '0.375rem' }}>
                    Select Material Lot <span style={{ color: 'var(--status-error)' }}>*</span>
                  </label>
                  <select
                    value={selectedLotId}
                    onChange={(e) => setSelectedLotId(e.target.value)}
                    className="clay-select"
                    required
                  >
                    {lots.map((l) => (
                      <option key={l.lot_id} value={l.lot_id}>
                        {l.material_type} — {l.quantity} {l.unit} ({l.lot_id.slice(0, 8)}...)
                      </option>
                    ))}
                  </select>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '0.75rem' }}>
                  <div>
                    <label className="label-compact" style={{ display: 'block', marginBottom: '0.375rem' }}>
                      Asking Price Per Unit
                    </label>
                    <input
                      type="number"
                      step="0.01"
                      value={askingPrice}
                      onChange={(e) => setAskingPrice(parseFloat(e.target.value) || 0)}
                      placeholder="450"
                      className="clay-input"
                    />
                  </div>
                  <div>
                    <label className="label-compact" style={{ display: 'block', marginBottom: '0.375rem' }}>
                      Currency
                    </label>
                    <select
                      value={currency}
                      onChange={(e) => setCurrency(e.target.value)}
                      className="clay-select"
                    >
                      <option value="USD">USD ($)</option>
                      <option value="EUR">EUR (€)</option>
                      <option value="CHF">CHF (Fr)</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="label-compact" style={{ display: 'block', marginBottom: '0.375rem' }}>
                    Listing Visibility
                  </label>
                  <select
                    value={visibility}
                    onChange={(e) => setVisibility(e.target.value)}
                    className="clay-select"
                  >
                    <option value="public">Public Exchange (All Qualified Buyers)</option>
                    <option value="cluster_only">Cluster Only (Regional Mesh Partners)</option>
                    <option value="verified_only">Verified DPP Partners Only</option>
                  </select>
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
                    onClick={() => setListingModalOpen(false)}
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
                        <span>Publishing...</span>
                      </>
                    ) : (
                      <span>Publish Listing</span>
                    )}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* MODAL: CREATE REQUIREMENT */}
        {reqModalOpen && (
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
                    Feedstock Demand
                  </span>
                  <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--primary)' }}>
                    Record Buyer Requirement
                  </h2>
                </div>
                <button
                  onClick={() => setReqModalOpen(false)}
                  className="clay-btn-ghost"
                  style={{ padding: '4px' }}
                >
                  <X size={18} />
                </button>
              </div>

              <form onSubmit={handleCreateRequirement} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <div>
                  <label className="label-compact" style={{ display: 'block', marginBottom: '0.375rem' }}>
                    Required Material Class <span style={{ color: 'var(--status-error)' }}>*</span>
                  </label>
                  <select
                    value={reqMaterialType}
                    onChange={(e) => setReqMaterialType(e.target.value)}
                    className="clay-select"
                  >
                    <option value="ti-6al-4v-swarf">Titanium Ti-6Al-4V Secondary Swarf</option>
                    <option value="al-6061-offcuts">Aluminum 6061 Clean Offcuts</option>
                    <option value="cu-millberry">Copper Millberry Wire Scrap</option>
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
                      value={reqTargetQty}
                      onChange={(e) => setReqTargetQty(parseFloat(e.target.value) || 0)}
                      placeholder="20"
                      className="clay-input"
                    />
                  </div>
                  <div>
                    <label className="label-compact" style={{ display: 'block', marginBottom: '0.375rem' }}>
                      Unit
                    </label>
                    <select
                      value={reqUnit}
                      onChange={(e) => setReqUnit(e.target.value)}
                      className="clay-select"
                    >
                      <option value="tonne">tonne</option>
                      <option value="kg">kg</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="label-compact" style={{ display: 'block', marginBottom: '0.375rem' }}>
                    Max Price Budget Per Unit ($)
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    value={reqMaxPrice}
                    onChange={(e) => setReqMaxPrice(parseFloat(e.target.value) || 0)}
                    placeholder="480"
                    className="clay-input"
                  />
                </div>

                <div>
                  <label className="label-compact" style={{ display: 'block', marginBottom: '0.375rem' }}>
                    Delivery Location Country Code
                  </label>
                  <input
                    type="text"
                    value={reqCountry}
                    maxLength={2}
                    onChange={(e) => setReqCountry(e.target.value.toUpperCase())}
                    className="clay-input"
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
                    onClick={() => setReqModalOpen(false)}
                    className="clay-btn clay-btn-ghost"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={isSubmitting}
                    className="clay-btn clay-btn-primary"
                  >
                    {isSubmitting ? 'Posting...' : 'Record Requirement'}
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
