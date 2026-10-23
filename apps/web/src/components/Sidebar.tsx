'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  Layers,
  ShieldCheck,
  RefreshCw,
  FileText,
  Settings,
  ChevronLeft,
  ChevronRight,
  Factory,
  Building2,
  X,
  ShoppingBag,
  Sparkles,
} from 'lucide-react';
import { useAuth } from '@/lib/auth';
import { cn } from '@/lib/utils';
import { UserRole } from '@/types';

interface SidebarProps {
  collapsed: boolean;
  onToggleCollapse: () => void;
  mobileOpen: boolean;
  onCloseMobile: () => void;
}

interface NavItem {
  label: string;
  href: string;
  icon: React.ReactNode;
  allowedRoles?: UserRole[];
  badge?: string;
  description: string;
}

export function Sidebar({
  collapsed,
  onToggleCollapse,
  mobileOpen,
  onCloseMobile,
}: SidebarProps) {
  const pathname = usePathname();
  const { user } = useAuth();
  const currentRole = user?.role || 'facility_operator';

  const navItems: NavItem[] = [
    {
      label: 'Overview',
      href: '/overview',
      icon: <LayoutDashboard size={18} />,
      description: 'Mass-balance telemetry & cluster health',
    },
    {
      label: 'Materials',
      href: '/materials',
      icon: <Layers size={18} />,
      badge: currentRole === 'facility_operator' ? 'Lots' : undefined,
      description: 'Canonical industrial material registry',
    },
    {
      label: 'ProofPath',
      href: '/proofpath',
      icon: <ShieldCheck size={18} />,
      badge: currentRole === 'facility_operator' ? 'Audit' : undefined,
      description: 'Deterministic qualification engine',
    },
    {
      label: 'Circular Exchange',
      href: '/exchange',
      icon: <RefreshCw size={18} />,
      badge: currentRole === 'buyer' ? 'Active' : undefined,
      description: 'Material listings & marketplace',
    },
    {
      label: 'Buyer Requirements',
      href: '/requirements',
      icon: <ShoppingBag size={18} />,
      description: 'Feedstock demand specifications',
    },
    {
      label: 'Matching',
      href: '/matching',
      icon: <Sparkles size={18} />,
      badge: 'Rules',
      description: 'Authoritative candidate qualification matching',
    },
    {
      label: 'RFQs & Offers',
      href: '/rfqs',
      icon: <FileText size={18} />,
      badge: currentRole === 'buyer' || currentRole === 'seller' ? 'Deals' : undefined,
      description: 'Bilateral negotiations & transactions',
    },
    {
      label: 'Settings',
      href: '/settings',
      icon: <Settings size={18} />,
      description: 'Tenant & facility node configuration',
    },
  ];

  const sidebarContent = (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        backgroundColor: '#ffffff',
        borderRight: '1px solid var(--border-subtle)',
      }}
    >
      {/* Brand Header */}
      <div
        style={{
          height: '64px',
          padding: collapsed ? '0 1rem' : '0 1.25rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: collapsed ? 'center' : 'space-between',
          borderBottom: '1px solid var(--border-subtle)',
        }}
      >
        <Link
          href="/overview"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.625rem',
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
              letterSpacing: '-0.02em',
              flexShrink: 0,
            }}
          >
            S
          </div>
          {!collapsed && (
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <span
                style={{
                  fontWeight: 700,
                  fontSize: '1rem',
                  letterSpacing: '0.04em',
                  color: 'var(--text-primary)',
                  lineHeight: 1.1,
                }}
              >
                STRATA
              </span>
              <span
                className="label-compact"
                style={{ fontSize: '0.5625rem', color: 'var(--text-muted)' }}
              >
                Circularity Engine
              </span>
            </div>
          )}
        </Link>

        {/* Mobile close button */}
        <button
          onClick={onCloseMobile}
          className="clay-btn-ghost md-hidden"
          style={{
            display: 'none',
            padding: '4px',
            cursor: 'pointer',
          }}
          aria-label="Close sidebar"
        >
          <X size={18} />
        </button>
      </div>

      {/* Navigation List */}
      <nav
        style={{
          flex: 1,
          padding: '1rem 0.75rem',
          display: 'flex',
          flexDirection: 'column',
          gap: '0.25rem',
          overflowY: 'auto',
        }}
      >
        {!collapsed && (
          <div
            className="label-compact"
            style={{
              padding: '0.25rem 0.5rem 0.5rem 0.5rem',
              color: 'var(--text-muted)',
            }}
          >
            Platform Rails
          </div>
        )}

        {navItems.map((item) => {
          const isActive =
            pathname === item.href ||
            (item.href === '/overview' && pathname === '/') ||
            (pathname?.startsWith(item.href) && item.href !== '/overview');

          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={onCloseMobile}
              title={collapsed ? item.label : undefined}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.75rem',
                padding: collapsed ? '0.625rem 0' : '0.625rem 0.75rem',
                justifyContent: collapsed ? 'center' : 'flex-start',
                borderRadius: '8px',
                textDecoration: 'none',
                color: isActive ? 'var(--primary)' : 'var(--text-secondary)',
                backgroundColor: isActive ? 'var(--bg-subtle)' : 'transparent',
                fontWeight: isActive ? 600 : 500,
                fontSize: '0.8125rem',
                border: isActive
                  ? '1px solid var(--border-subtle)'
                  : '1px solid transparent',
                transition: 'all 0.12s ease',
              }}
            >
              <div
                style={{
                  color: isActive ? 'var(--primary-container)' : 'var(--text-muted)',
                  display: 'flex',
                  alignItems: 'center',
                }}
              >
                {item.icon}
              </div>

              {!collapsed && (
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    flex: 1,
                  }}
                >
                  <span>{item.label}</span>
                  {item.badge && (
                    <span
                      style={{
                        fontSize: '0.625rem',
                        fontWeight: 700,
                        textTransform: 'uppercase',
                        padding: '1px 5px',
                        borderRadius: '4px',
                        backgroundColor: 'var(--accent-teal-subtle)',
                        color: 'var(--primary-container)',
                      }}
                    >
                      {item.badge}
                    </span>
                  )}
                </div>
              )}
            </Link>
          );
        })}
      </nav>

      {/* Role and Node Context Footer */}
      <div
        style={{
          padding: collapsed ? '0.75rem 0.5rem' : '0.875rem 1rem',
          borderTop: '1px solid var(--border-subtle)',
          backgroundColor: 'var(--bg-subtle)',
          display: 'flex',
          flexDirection: 'column',
          gap: '0.5rem',
        }}
      >
        {!collapsed ? (
          <div>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                marginBottom: '0.25rem',
              }}
            >
              <Factory size={14} color="var(--primary-container)" />
              <span
                style={{
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  color: 'var(--text-primary)',
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  maxWidth: '160px',
                }}
              >
                {user?.facility_name || 'Production Site #4'}
              </span>
            </div>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.375rem',
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
                style={{ fontSize: '0.625rem', color: 'var(--text-muted)' }}
              >
                {currentRole.replace('_', ' ')} · Node 09
              </span>
            </div>
          </div>
        ) : (
          <div
            style={{
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              width: '100%',
            }}
            title={`${user?.facility_name} (${currentRole})`}
          >
            <Building2 size={16} color="var(--primary-container)" />
          </div>
        )}

        {/* Desktop Collapse Toggle */}
        <button
          onClick={onToggleCollapse}
          className="clay-btn-ghost desktop-toggle-btn"
          style={{
            width: '100%',
            padding: '0.375rem',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            borderRadius: '6px',
            color: 'var(--text-muted)',
            cursor: 'pointer',
          }}
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
        </button>
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop Sticky Sidebar */}
      <aside
        className="sidebar-desktop"
        style={{
          width: collapsed ? '68px' : '240px',
          height: '100vh',
          position: 'sticky',
          top: 0,
          left: 0,
          zIndex: 30,
          transition: 'width 0.18s ease-in-out',
          flexShrink: 0,
        }}
      >
        {sidebarContent}
      </aside>

      {/* Mobile Drawer Overlay */}
      {mobileOpen && (
        <div
          className="sidebar-mobile-overlay"
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 50,
            display: 'flex',
          }}
        >
          {/* Backdrop blur */}
          <div
            onClick={onCloseMobile}
            style={{
              position: 'fixed',
              inset: 0,
              backgroundColor: 'rgba(18, 52, 32, 0.35)',
              backdropFilter: 'blur(2px)',
            }}
          />

          {/* Slide-over Container */}
          <div
            style={{
              position: 'relative',
              width: '280px',
              maxWidth: '85vw',
              height: '100%',
              backgroundColor: '#ffffff',
              boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)',
              zIndex: 51,
            }}
          >
            {sidebarContent}
          </div>
        </div>
      )}
    </>
  );
}
