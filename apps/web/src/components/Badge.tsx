import React from 'react';
import { cn } from '@/lib/utils';

interface BadgeProps {
  children: React.ReactNode;
  variant?: 'success' | 'warning' | 'error' | 'neutral' | 'teal';
  dot?: boolean;
  className?: string;
}

export function Badge({
  children,
  variant = 'neutral',
  dot = false,
  className,
}: BadgeProps) {
  const variantClass = {
    success: 'strata-badge-success',
    warning: 'strata-badge-warning',
    error: 'strata-badge-error',
    neutral: 'strata-badge-neutral',
    teal: 'strata-badge-teal',
  }[variant];

  const dotColor = {
    success: '#286343',
    warning: '#9a6722',
    error: '#a63a35',
    neutral: '#68716a',
    teal: '#294b35',
  }[variant];

  return (
    <span className={cn('strata-badge', variantClass, className)}>
      {dot && (
        <span
          style={{
            width: '6px',
            height: '6px',
            borderRadius: '50%',
            display: 'inline-block',
            backgroundColor: dotColor,
            flexShrink: 0,
          }}
        />
      )}
      {children}
    </span>
  );
}
