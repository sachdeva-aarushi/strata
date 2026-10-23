'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { Menu, ChevronDown, User, LogOut, Check, Building, Plus } from 'lucide-react';
import { useAuth } from '@/lib/auth';
import { Badge } from '@/components/Badge';
import { UserRole } from '@/types';

interface NavbarProps {
  onOpenMobileMenu: () => void;
}

export function Navbar({ onOpenMobileMenu }: NavbarProps) {
  const { user, switchRole, logout } = useAuth();
  const [roleMenuOpen, setRoleMenuOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);

  const roles: { id: UserRole; label: string; desc: string }[] = [
    { id: 'facility_operator', label: 'Facility Operator', desc: 'Material lots & ProofPath qualification' },
    { id: 'buyer', label: 'Industrial Buyer', desc: 'Requirements, exchange matching, RFQs' },
    { id: 'seller', label: 'Material Seller', desc: 'Circular exchange listings & offers' },
    { id: 'admin', label: 'System Administrator', desc: 'Workspace & cluster configuration' },
  ];

  return (
    <header
      style={{
        height: '64px',
        backgroundColor: '#ffffff',
        borderBottom: '1px solid var(--border-subtle)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 1.5rem',
        position: 'sticky',
        top: 0,
        zIndex: 20,
      }}
    >
      {/* Left section: Hamburger button & Node breadcrumb */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        <button
          onClick={onOpenMobileMenu}
          className="clay-btn-ghost md-show"
          style={{
            padding: '0.375rem',
            borderRadius: '6px',
            color: 'var(--text-primary)',
            cursor: 'pointer',
          }}
          aria-label="Open navigation menu"
        >
          <Menu size={20} />
        </button>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
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
            <span
              className="label-compact"
              style={{ fontSize: '0.625rem', color: 'var(--text-secondary)' }}
            >
              Cluster Central · Nominal
            </span>
          </div>

          <span
            style={{
              fontSize: '0.8125rem',
              color: 'var(--text-muted)',
              display: 'none',
            }}
            className="sm-inline"
          >
            {user?.name || 'Dr. Hélène Vance'}
          </span>
        </div>
      </div>

      {/* Right section: Quick action + Role switcher + Profile */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
        <Link
          href="/materials?action=new"
          className="clay-btn clay-btn-primary"
          style={{
            fontSize: '0.75rem',
            padding: '0.375rem 0.75rem',
            gap: '0.375rem',
          }}
        >
          <Plus size={14} />
          <span>Register Lot</span>
        </Link>

        {/* Role Selector Pill */}
        <div style={{ position: 'relative' }}>
          <button
            onClick={() => {
              setRoleMenuOpen(!roleMenuOpen);
              setUserMenuOpen(false);
            }}
            className="clay-btn clay-btn-secondary"
            style={{
              fontSize: '0.75rem',
              padding: '0.375rem 0.625rem',
              gap: '0.375rem',
              borderRadius: '6px',
            }}
          >
            <span className="label-compact" style={{ fontSize: '0.625rem' }}>
              Role:
            </span>
            <span style={{ fontWeight: 600 }}>
              {user?.role ? user.role.replace('_', ' ') : 'Operator'}
            </span>
            <ChevronDown size={14} />
          </button>

          {roleMenuOpen && (
            <div
              className="clay-card"
              style={{
                position: 'absolute',
                right: 0,
                top: 'calc(100% + 6px)',
                width: '240px',
                padding: '0.5rem',
                zIndex: 40,
                backgroundColor: '#ffffff',
              }}
            >
              <div
                className="label-compact"
                style={{ padding: '0.375rem 0.5rem', color: 'var(--text-muted)' }}
              >
                Switch Persona
              </div>
              {roles.map((r) => (
                <button
                  key={r.id}
                  onClick={() => {
                    switchRole(r.id);
                    setRoleMenuOpen(false);
                  }}
                  style={{
                    width: '100%',
                    textAlign: 'left',
                    padding: '0.5rem',
                    borderRadius: '6px',
                    border: 'none',
                    backgroundColor:
                      user?.role === r.id ? 'var(--bg-subtle)' : 'transparent',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                  }}
                >
                  <div>
                    <div
                      style={{
                        fontSize: '0.8125rem',
                        fontWeight: 600,
                        color: 'var(--text-primary)',
                      }}
                    >
                      {r.label}
                    </div>
                    <div
                      style={{
                        fontSize: '0.6875rem',
                        color: 'var(--text-muted)',
                      }}
                    >
                      {r.desc}
                    </div>
                  </div>
                  {user?.role === r.id && (
                    <Check size={14} color="var(--primary-container)" />
                  )}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* User profile avatar & dropdown */}
        <div style={{ position: 'relative' }}>
          <button
            onClick={() => {
              setUserMenuOpen(!userMenuOpen);
              setRoleMenuOpen(false);
            }}
            style={{
              width: '32px',
              height: '32px',
              borderRadius: '50%',
              backgroundColor: 'var(--primary-container)',
              color: '#ffffff',
              border: 'none',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontWeight: 600,
              fontSize: '0.8125rem',
            }}
            title={user?.email || 'User Account'}
          >
            {user?.name ? user.name[0] : 'U'}
          </button>

          {userMenuOpen && (
            <div
              className="clay-card"
              style={{
                position: 'absolute',
                right: 0,
                top: 'calc(100% + 6px)',
                width: '220px',
                padding: '0.5rem',
                zIndex: 40,
                backgroundColor: '#ffffff',
              }}
            >
              <div
                style={{
                  padding: '0.5rem',
                  borderBottom: '1px solid var(--border-subtle)',
                  marginBottom: '0.375rem',
                }}
              >
                <div style={{ fontWeight: 600, fontSize: '0.8125rem' }}>
                  {user?.name || 'Operator'}
                </div>
                <div
                  style={{
                    fontSize: '0.6875rem',
                    color: 'var(--text-muted)',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                  }}
                >
                  {user?.email || 'operator@plant-line.com'}
                </div>
              </div>

              <Link
                href="/onboarding"
                onClick={() => setUserMenuOpen(false)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  padding: '0.5rem',
                  fontSize: '0.8125rem',
                  color: 'var(--text-secondary)',
                  textDecoration: 'none',
                  borderRadius: '6px',
                }}
              >
                <Building size={14} />
                <span>Onboarding Setup</span>
              </Link>

              <Link
                href="/login"
                onClick={() => {
                  logout();
                  setUserMenuOpen(false);
                }}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  padding: '0.5rem',
                  fontSize: '0.8125rem',
                  color: 'var(--status-error)',
                  textDecoration: 'none',
                  borderRadius: '6px',
                }}
              >
                <LogOut size={14} />
                <span>Sign Out</span>
              </Link>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
