'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  Factory,
  CheckCircle2,
  ArrowRight,
  ArrowLeft,
  Building2,
  Recycle,
  Warehouse,
  Truck,
  Network,
  Scale,
  ShieldCheck,
  Check,
  Loader2,
  FileCheck,
} from 'lucide-react';
import { useAuth } from '@/lib/auth';
import { OrgType } from '@/types';

export default function OnboardingPage() {
  const router = useRouter();
  const { user, updateOnboarding } = useAuth();

  // Wizard Step: 1 = Org Type, 2 = Org Details, 3 = Facility Info
  const [step, setStep] = useState<1 | 2 | 3>(1);

  // Step 1: Org Classification
  const [orgType, setOrgType] = useState<OrgType>('manufacturer');

  // Step 2: Org Details
  const [legalName, setLegalName] = useState(
    user?.facility_name ? 'Nordic Smelting & Secondary Alloy AG' : ''
  );
  const [taxId, setTaxId] = useState('CHE-814.902.115');
  const [jurisdiction, setJurisdiction] = useState('CH-SG');
  const [domain, setDomain] = useState('nordicsmelting.ch');
  const [contactName, setContactName] = useState(user?.name || 'Dr. Hélène Vance');
  const [contactRole, setContactRole] = useState(
    'Head of Secondary Metallurgy & Circular Streams'
  );
  const [regulatoryFramework, setRegulatoryFramework] = useState(
    'EU Waste Shipment (EC) No 1013/2006 & Swiss VVEA'
  );

  // Step 3: Facility Information
  const [facilityName, setFacilityName] = useState(
    user?.facility_name || 'Central Rail Smelter & Foundry #4'
  );
  const [facilityCountry, setFacilityCountry] = useState('CH');
  const [postalCode, setPostalCode] = useState('9470');
  const [facilityType, setFacilityType] = useState<'generator' | 'receiver' | 'aggregator'>(
    'generator'
  );
  const [capacityTpa, setCapacityTpa] = useState<number>(45000);
  const [clusterId, setClusterId] = useState('00000000-0000-0000-0000-000000000003');
  const [zoneId, setZoneId] = useState('ZONE-RHINE-02');

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [draftSaved, setDraftSaved] = useState(false);

  const orgClassifications: {
    id: OrgType;
    title: string;
    description: string;
    telemetry: string;
    icon: React.ReactNode;
  }[] = [
    {
      id: 'manufacturer',
      title: 'Facility or Manufacturer',
      description:
        'Discrete machining, automotive, aerospace, or industrial plants generating swarf, scrap, or offcuts.',
      telemetry: 'High Ingot/Swarf Delta',
      icon: <Factory size={22} />,
    },
    {
      id: 'processor',
      title: 'Recycler or Processor',
      description:
        'Smelters, refiners, hydrometallurgical recovery, pyrometallurgy, and certified secondary ingot casting.',
      telemetry: 'Chemical Assay Feeds',
      icon: <Recycle size={22} />,
    },
    {
      id: 'aggregator',
      title: 'Waste Handler or Aggregator',
      description:
        'Licensed secondary material logistics depots, sorting yards, shredders, and bulk densification hubs.',
      telemetry: 'Weighbridge & Moisture',
      icon: <Warehouse size={22} />,
    },
    {
      id: 'logistics',
      title: 'Logistics Partner',
      description:
        'ADR-certified bulk haulage, multimodal rail freight, and maritime container handlers.',
      telemetry: 'Geofence & Custody Sign',
      icon: <Truck size={22} />,
    },
    {
      id: 'cluster',
      title: 'Industrial Cluster',
      description:
        'Eco-industrial parks, multi-tenant waste-heat cascades, shared secondary metallurgy zones.',
      telemetry: 'Multi-Node Bilateral Mesh',
      icon: <Network size={22} />,
    },
    {
      id: 'municipality',
      title: 'Municipal Authority',
      description:
        'Statutory regional environmental councils, Basel Convention inspectors, and national waste registrars.',
      telemetry: 'Compliance Audit TAP',
      icon: <Scale size={22} />,
    },
  ];

  const handleNext = () => {
    if (step === 1) {
      setStep(2);
    } else if (step === 2) {
      setStep(3);
    } else {
      // Complete Onboarding
      setIsSubmitting(true);
      setTimeout(() => {
        updateOnboarding({
          org_name: legalName || 'Nordic Smelting & Secondary Alloy AG',
          org_type: orgType,
          facility_name: facilityName || 'Main Production Site',
          facility_country: facilityCountry,
          facility_type: facilityType,
        });
        setIsSubmitting(false);
        router.push('/overview');
      }, 700);
    }
  };

  const handleSaveDraft = () => {
    setDraftSaved(true);
    setTimeout(() => setDraftSaved(false), 2000);
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        backgroundColor: 'var(--bg-canvas)',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      {/* Header bar */}
      <header
        style={{
          height: '64px',
          backgroundColor: '#ffffff',
          borderBottom: '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 2rem',
          position: 'sticky',
          top: 0,
          zIndex: 30,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <Link
            href="/overview"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
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
                fontSize: '1rem',
                fontWeight: 700,
                letterSpacing: '0.04em',
                color: 'var(--text-primary)',
              }}
            >
              STRATA
            </span>
          </Link>
          <span
            className="label-compact"
            style={{
              padding: '0.2rem 0.5rem',
              backgroundColor: 'var(--accent-teal-subtle)',
              color: 'var(--primary-container)',
              borderRadius: '4px',
            }}
          >
            TENANT PROVISIONING
          </span>
        </div>

        {/* Step indicator pills */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.375rem',
              fontSize: '0.8125rem',
              fontWeight: 600,
              color: step === 1 ? 'var(--primary)' : 'var(--text-muted)',
            }}
          >
            <span
              style={{
                width: '20px',
                height: '20px',
                borderRadius: '50%',
                backgroundColor: step === 1 ? 'var(--primary-container)' : 'var(--bg-subtle)',
                color: step === 1 ? '#ffffff' : 'var(--text-muted)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '0.6875rem',
              }}
            >
              1
            </span>
            <span className="sm-inline" style={{ display: 'none' }}>
              Classification
            </span>
          </div>

          <span style={{ color: 'var(--border-strong)' }}>——</span>

          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.375rem',
              fontSize: '0.8125rem',
              fontWeight: 600,
              color: step === 2 ? 'var(--primary)' : 'var(--text-muted)',
            }}
          >
            <span
              style={{
                width: '20px',
                height: '20px',
                borderRadius: '50%',
                backgroundColor: step === 2 ? 'var(--primary-container)' : 'var(--bg-subtle)',
                color: step === 2 ? '#ffffff' : 'var(--text-muted)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '0.6875rem',
              }}
            >
              2
            </span>
            <span className="sm-inline" style={{ display: 'none' }}>
              Legal Entity
            </span>
          </div>

          <span style={{ color: 'var(--border-strong)' }}>——</span>

          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.375rem',
              fontSize: '0.8125rem',
              fontWeight: 600,
              color: step === 3 ? 'var(--primary)' : 'var(--text-muted)',
            }}
          >
            <span
              style={{
                width: '20px',
                height: '20px',
                borderRadius: '50%',
                backgroundColor: step === 3 ? 'var(--primary-container)' : 'var(--bg-subtle)',
                color: step === 3 ? '#ffffff' : 'var(--text-muted)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '0.6875rem',
              }}
            >
              3
            </span>
            <span className="sm-inline" style={{ display: 'none' }}>
              Facility Site
            </span>
          </div>
        </div>
      </header>

      {/* Main Form Body */}
      <main
        style={{
          flex: 1,
          maxWidth: '1200px',
          width: '100%',
          margin: '0 auto',
          padding: '2rem 1.5rem 6rem 1.5rem',
        }}
      >
        {/* Step Header */}
        <div style={{ marginBottom: '2rem' }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              marginBottom: '0.375rem',
            }}
          >
            <span
              className="label-compact"
              style={{
                padding: '0.15rem 0.5rem',
                backgroundColor: 'var(--primary-container)',
                color: '#ffffff',
                borderRadius: '4px',
              }}
            >
              Step {step} of 3
            </span>
            <span style={{ color: 'var(--text-muted)' }}>/</span>
            <span
              style={{
                fontSize: '0.8125rem',
                fontWeight: 600,
                color: 'var(--primary)',
              }}
            >
              {step === 1 && 'Circularity Role Classification'}
              {step === 2 && 'Organization Legal & Regulatory Identity'}
              {step === 3 && 'Facility Node Configuration'}
            </span>
          </div>

          <h1
            className="font-serif"
            style={{
              fontSize: '1.875rem',
              fontWeight: 500,
              color: 'var(--primary)',
              letterSpacing: '-0.015em',
            }}
          >
            {step === 1 && 'Select Your Circularity Stream Role'}
            {step === 2 && 'Register Corporate & Regulatory Entity'}
            {step === 3 && 'Configure Primary Production Site'}
          </h1>
          <p
            style={{
              color: 'var(--text-secondary)',
              fontSize: '0.875rem',
              maxWidth: '720px',
              marginTop: '0.375rem',
            }}
          >
            {step === 1 &&
              'Your stream role configures default mass-balance conversion formulas, evidence schemas, and circular exchange matching rules.'}
            {step === 2 &&
              'Statutory entity details are anchored to your tenant ID to generate audit-ready Digital Product Passports (DPPs).'}
            {step === 3 &&
              'Facilities anchor physical inventory lots, geolocation coordinates, and regional cluster synergy mappings.'}
          </p>
        </div>

        {/* STEP 1: Organization Classification */}
        {step === 1 && (
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
              gap: '1rem',
            }}
          >
            {orgClassifications.map((item) => {
              const isSelected = orgType === item.id;
              return (
                <div
                  key={item.id}
                  onClick={() => setOrgType(item.id)}
                  className={`clay-card-interactive ${
                    isSelected ? 'clay-card-selected' : ''
                  }`}
                  style={{
                    padding: '1.25rem',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                  }}
                >
                  <div>
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        marginBottom: '0.875rem',
                      }}
                    >
                      <div
                        style={{
                          width: '40px',
                          height: '40px',
                          borderRadius: '8px',
                          backgroundColor: isSelected
                            ? 'var(--primary-container)'
                            : 'var(--bg-subtle)',
                          color: isSelected ? '#ffffff' : 'var(--text-primary)',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                        }}
                      >
                        {item.icon}
                      </div>

                      <div
                        style={{
                          width: '20px',
                          height: '20px',
                          borderRadius: '50%',
                          border: isSelected
                            ? '6px solid var(--primary-container)'
                            : '2px solid var(--border-strong)',
                          backgroundColor: '#ffffff',
                          transition: 'all 0.15s ease',
                        }}
                      />
                    </div>

                    <h3
                      style={{
                        fontSize: '1rem',
                        fontWeight: 600,
                        color: 'var(--text-primary)',
                        marginBottom: '0.375rem',
                      }}
                    >
                      {item.title}
                    </h3>
                    <p
                      style={{
                        fontSize: '0.8125rem',
                        color: 'var(--text-secondary)',
                        lineHeight: 1.5,
                      }}
                    >
                      {item.description}
                    </p>
                  </div>

                  <div
                    style={{
                      marginTop: '1.25rem',
                      paddingTop: '0.75rem',
                      borderTop: '1px solid var(--border-subtle)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                    }}
                  >
                    <span
                      className="label-compact"
                      style={{
                        fontSize: '0.625rem',
                        color: isSelected
                          ? 'var(--primary-container)'
                          : 'var(--text-muted)',
                      }}
                    >
                      Telemetry: {item.telemetry}
                    </span>
                    <ShieldCheck
                      size={14}
                      color={
                        isSelected ? 'var(--primary-container)' : 'var(--text-muted)'
                      }
                    />
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* STEP 2: Organization Details */}
        {step === 2 && (
          <div
            className="clay-card"
            style={{ padding: '2rem', backgroundColor: '#ffffff', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}
          >
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
                gap: '1.25rem',
              }}
            >
              <div>
                <label className="label-compact" style={{ display: 'block', marginBottom: '0.375rem' }}>
                  Legal Incorporated Name <span style={{ color: 'var(--status-error)' }}>*</span>
                </label>
                <input
                  type="text"
                  value={legalName}
                  onChange={(e) => setLegalName(e.target.value)}
                  placeholder="Nordic Smelting & Secondary Alloy AG"
                  className="clay-input"
                  required
                />
                <span style={{ fontSize: '0.6875rem', color: 'var(--text-muted)', marginTop: '0.25rem', display: 'block' }}>
                  Statutory register cross-reference enabled.
                </span>
              </div>

              <div>
                <label className="label-compact" style={{ display: 'block', marginBottom: '0.375rem' }}>
                  Commercial Register UID / Tax ID
                </label>
                <input
                  type="text"
                  value={taxId}
                  onChange={(e) => setTaxId(e.target.value)}
                  placeholder="CHE-814.902.115"
                  className="clay-input"
                />
              </div>

              <div>
                <label className="label-compact" style={{ display: 'block', marginBottom: '0.375rem' }}>
                  Business Domain
                </label>
                <input
                  type="text"
                  value={domain}
                  onChange={(e) => setDomain(e.target.value)}
                  placeholder="nordicsmelting.ch"
                  className="clay-input"
                />
              </div>

              <div>
                <label className="label-compact" style={{ display: 'block', marginBottom: '0.375rem' }}>
                  Jurisdiction &amp; Region
                </label>
                <select
                  value={jurisdiction}
                  onChange={(e) => setJurisdiction(e.target.value)}
                  className="clay-select"
                >
                  <option value="CH-SG">CHE · Switzerland — St. Gallen (Rhine Valley)</option>
                  <option value="DE-BW">DEU · Germany — Baden-Württemberg</option>
                  <option value="SE-BD">SWE · Sweden — Norrbotten Green Metals Zone</option>
                  <option value="AT-VO">AUT · Austria — Vorarlberg</option>
                  <option value="US-PA">USA · Pennsylvania Industrial Basin</option>
                </select>
              </div>

              <div>
                <label className="label-compact" style={{ display: 'block', marginBottom: '0.375rem' }}>
                  Primary Operational Signatory
                </label>
                <input
                  type="text"
                  value={contactName}
                  onChange={(e) => setContactName(e.target.value)}
                  placeholder="Dr. Hélène Vance"
                  className="clay-input"
                />
              </div>

              <div>
                <label className="label-compact" style={{ display: 'block', marginBottom: '0.375rem' }}>
                  Signatory Title &amp; Role
                </label>
                <input
                  type="text"
                  value={contactRole}
                  onChange={(e) => setContactRole(e.target.value)}
                  placeholder="Head of Secondary Metallurgy"
                  className="clay-input"
                />
              </div>
            </div>

            <div>
              <label className="label-compact" style={{ display: 'block', marginBottom: '0.375rem' }}>
                Primary Regulatory Framework
              </label>
              <input
                type="text"
                value={regulatoryFramework}
                onChange={(e) => setRegulatoryFramework(e.target.value)}
                className="clay-input"
              />
              <span style={{ fontSize: '0.6875rem', color: 'var(--text-muted)', marginTop: '0.25rem', display: 'block' }}>
                Sets default fiscal carbon pricing boundary and customs declarations.
              </span>
            </div>
          </div>
        )}

        {/* STEP 3: Facility Site Information */}
        {step === 3 && (
          <div
            className="clay-card"
            style={{ padding: '2rem', backgroundColor: '#ffffff', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}
          >
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
                gap: '1.25rem',
              }}
            >
              <div>
                <label className="label-compact" style={{ display: 'block', marginBottom: '0.375rem' }}>
                  Facility Site Name <span style={{ color: 'var(--status-error)' }}>*</span>
                </label>
                <input
                  type="text"
                  value={facilityName}
                  onChange={(e) => setFacilityName(e.target.value)}
                  placeholder="Central Rail Smelter & Foundry #4"
                  className="clay-input"
                  required
                />
              </div>

              <div>
                <label className="label-compact" style={{ display: 'block', marginBottom: '0.375rem' }}>
                  Facility Type Role
                </label>
                <select
                  value={facilityType}
                  onChange={(e) => setFacilityType(e.target.value as any)}
                  className="clay-select"
                >
                  <option value="generator">Generator (Produces secondary scrap/byproducts)</option>
                  <option value="receiver">Receiver (Consumes or refines secondary material)</option>
                  <option value="aggregator">Aggregator / Processing Depot</option>
                </select>
              </div>

              <div>
                <label className="label-compact" style={{ display: 'block', marginBottom: '0.375rem' }}>
                  Location Country Code
                </label>
                <input
                  type="text"
                  value={facilityCountry}
                  onChange={(e) => setFacilityCountry(e.target.value.toUpperCase())}
                  placeholder="CH"
                  maxLength={2}
                  className="clay-input"
                />
              </div>

              <div>
                <label className="label-compact" style={{ display: 'block', marginBottom: '0.375rem' }}>
                  Postal / ZIP Code
                </label>
                <input
                  type="text"
                  value={postalCode}
                  onChange={(e) => setPostalCode(e.target.value)}
                  placeholder="9470"
                  className="clay-input"
                />
              </div>

              <div>
                <label className="label-compact" style={{ display: 'block', marginBottom: '0.375rem' }}>
                  Annual Processing Capacity (TPA)
                </label>
                <input
                  type="number"
                  value={capacityTpa}
                  onChange={(e) => setCapacityTpa(parseFloat(e.target.value) || 0)}
                  placeholder="45000"
                  className="clay-input"
                />
              </div>

              <div>
                <label className="label-compact" style={{ display: 'block', marginBottom: '0.375rem' }}>
                  Regional Industrial Cluster ID
                </label>
                <input
                  type="text"
                  value={clusterId}
                  onChange={(e) => setClusterId(e.target.value)}
                  className="clay-input"
                />
              </div>
            </div>

            <div
              style={{
                padding: '1rem',
                borderRadius: '8px',
                backgroundColor: 'var(--bg-subtle)',
                border: '1px solid var(--border-subtle)',
                display: 'flex',
                alignItems: 'center',
                gap: '0.75rem',
              }}
            >
              <FileCheck size={20} color="var(--primary-container)" />
              <div style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
                <strong>Automated Facility Anchoring:</strong> Material lots registered from this
                facility will inherit validated ISO geolocation tokens and EU 1013/2006 compliance tags.
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Sticky Bottom Action Bar */}
      <footer
        style={{
          position: 'fixed',
          bottom: 0,
          left: 0,
          right: 0,
          backgroundColor: 'rgba(255, 255, 255, 0.95)',
          backdropFilter: 'blur(8px)',
          borderTop: '1px solid var(--border-subtle)',
          padding: '1rem 2rem',
          zIndex: 40,
        }}
      >
        <div
          style={{
            maxWidth: '1200px',
            margin: '0 auto',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div>
            {step > 1 ? (
              <button
                type="button"
                onClick={() => setStep((step - 1) as any)}
                className="clay-btn clay-btn-ghost"
              >
                <ArrowLeft size={16} />
                <span>Back</span>
              </button>
            ) : (
              <Link href="/overview" className="clay-btn clay-btn-ghost">
                Skip to Dashboard
              </Link>
            )}
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <button
              type="button"
              onClick={handleSaveDraft}
              className="clay-btn clay-btn-secondary"
            >
              {draftSaved ? (
                <>
                  <Check size={14} color="var(--status-success)" />
                  <span>Draft Saved</span>
                </>
              ) : (
                <span>Save Draft</span>
              )}
            </button>

            <button
              type="button"
              disabled={isSubmitting}
              onClick={handleNext}
              className="clay-btn clay-btn-primary"
              style={{ minWidth: '180px' }}
            >
              {isSubmitting ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  <span>Configuring Site...</span>
                </>
              ) : (
                <>
                  <span>
                    {step < 3 ? 'Continue to Next Step' : 'Complete Setup & Launch'}
                  </span>
                  <ArrowRight size={16} />
                </>
              )}
            </button>
          </div>
        </div>
      </footer>
    </div>
  );
}
