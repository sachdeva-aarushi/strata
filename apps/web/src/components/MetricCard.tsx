import React from 'react';
import { cn } from '@/lib/utils';

interface MetricCardProps {
  label: string;
  value: string | number;
  unit?: string;
  subtext?: string;
  delta?: string;
  deltaType?: 'positive' | 'negative' | 'neutral';
  icon?: React.ReactNode;
  className?: string;
}

export function MetricCard({
  label,
  value,
  unit,
  subtext,
  delta,
  deltaType = 'neutral',
  icon,
  className,
}: MetricCardProps) {
  return (
    <div
      className={cn('clay-card', className)}
      style={{
        padding: '1.125rem 1.25rem',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
        <span className="label-compact">{label}</span>
        {icon && (
          <div
            style={{
              color: 'var(--text-muted)',
              display: 'flex',
              alignItems: 'center',
            }}
          >
            {icon}
          </div>
        )}
      </div>

      <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.375rem', marginBottom: '0.25rem' }}>
        <span
          className="tnum"
          style={{
            fontSize: '1.75rem',
            fontWeight: 700,
            color: 'var(--primary)',
            lineHeight: 1.1,
          }}
        >
          {value}
        </span>
        {unit && (
          <span
            style={{
              fontSize: '0.8125rem',
              color: 'var(--text-muted)',
              fontWeight: 500,
            }}
          >
            {unit}
          </span>
        )}
      </div>

      {(subtext || delta) && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.25rem' }}>
          {delta && (
            <span
              className="tnum"
              style={{
                fontSize: '0.75rem',
                fontWeight: 600,
                color:
                  deltaType === 'positive'
                    ? 'var(--status-success)'
                    : deltaType === 'negative'
                    ? 'var(--status-error)'
                    : 'var(--text-muted)',
              }}
            >
              {delta}
            </span>
          )}
          {subtext && (
            <span
              style={{
                fontSize: '0.75rem',
                color: 'var(--text-muted)',
              }}
            >
              {subtext}
            </span>
          )}
        </div>
      )}
    </div>
  );
}
