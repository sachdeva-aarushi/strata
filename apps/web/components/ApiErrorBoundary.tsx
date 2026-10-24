'use client';

import React, { Component, ReactNode, ErrorInfo } from 'react';
import { ApiError } from '../lib/api/client';

interface Props {
  children: ReactNode;
  fallback?: (error: Error, reset: () => void) => ReactNode;
  onReset?: () => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ApiErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ApiErrorBoundary caught error:', error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
    if (this.props.onReset) {
      this.props.onReset();
    }
  };

  private obfuscateEndpoint(endpoint?: string): string {
    if (!endpoint) return 'Unknown endpoint';
    try {
      const url = new URL(endpoint, 'http://localhost');
      return url.pathname;
    } catch {
      return endpoint.split('?')[0];
    }
  }

  render() {
    if (this.state.hasError && this.state.error) {
      if (this.props.fallback) {
        return this.props.fallback(this.state.error, this.handleReset);
      }

      const error = this.state.error;
      const isApiError = error instanceof ApiError;
      const status = isApiError ? (error as ApiError).status : 500;
      const endpoint = isApiError ? this.obfuscateEndpoint((error as ApiError).endpoint) : undefined;
      const isDev = process.env.NODE_ENV === 'development';

      return (
        <div
          role="alert"
          style={{
            padding: '2rem',
            margin: '1.5rem auto',
            maxWidth: '640px',
            backgroundColor: '#FEF2F2',
            border: '1px solid #F87171',
            borderRadius: '8px',
            color: '#1A1A1A',
            fontFamily: 'Inter, system-ui, sans-serif'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
            <span style={{ fontSize: '1.5rem', color: '#DC2626' }} aria-hidden="true">⚠️</span>
            <h3 style={{ margin: 0, fontSize: '1.125rem', fontWeight: 600, color: '#991B1B' }}>
              Connection or Request Failed
            </h3>
          </div>

          <p style={{ margin: '0 0 0.75rem 0', fontSize: '0.875rem', color: '#4B5563' }}>
            {error.message || 'An unexpected error occurred while communicating with the STRATA API.'}
          </p>

          <div
            style={{
              fontSize: '0.75rem',
              backgroundColor: '#FFFFFF',
              padding: '0.75rem',
              borderRadius: '6px',
              border: '1px solid #E5E7EB',
              marginBottom: '1rem'
            }}
          >
            <div><strong>Status Code:</strong> {status}</div>
            {endpoint && <div><strong>Endpoint:</strong> {endpoint}</div>}
          </div>

          <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
            <button
              onClick={this.handleReset}
              style={{
                backgroundColor: '#0F4C81',
                color: '#FFFFFF',
                border: 'none',
                borderRadius: '6px',
                padding: '0.5rem 1rem',
                fontSize: '0.875rem',
                fontWeight: 500,
                cursor: 'pointer'
              }}
            >
              Retry Request
            </button>
          </div>

          {isDev && (
            <details style={{ marginTop: '1rem', fontSize: '0.75rem', color: '#6B7280' }}>
              <summary style={{ cursor: 'pointer', fontWeight: 500 }}>Technical Details (Dev Only)</summary>
              <pre
                style={{
                  marginTop: '0.5rem',
                  padding: '0.75rem',
                  backgroundColor: '#1E293B',
                  color: '#F8FAFC',
                  borderRadius: '4px',
                  overflowX: 'auto',
                  whiteSpace: 'pre-wrap',
                  fontSize: '0.7rem'
                }}
              >
                {error.stack || JSON.stringify(error, null, 2)}
              </pre>
            </details>
          )}
        </div>
      );
    }

    return this.props.children;
  }
}
