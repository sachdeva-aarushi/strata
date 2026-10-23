'use client';

import { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { AuthUser, OrgType, UserRole } from '@/types';

export interface AuthContextType {
  user: AuthUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, role?: UserRole) => Promise<AuthUser>;
  register: (name: string, email: string, role?: UserRole) => Promise<AuthUser>;
  logout: () => void;
  switchRole: (newRole: UserRole) => void;
  updateOnboarding: (data: {
    org_name: string;
    org_type: OrgType;
    facility_name: string;
    facility_country: string;
    facility_type?: 'generator' | 'receiver' | 'aggregator';
  }) => void;
  getAuthHeaders: () => Record<string, string>;
}

const STORAGE_KEY = 'strata_auth_session';

const DEFAULT_USER: AuthUser = {
  user_id: '00000000-0000-0000-0000-000000000002',
  org_id: '00000000-0000-0000-0000-000000000001',
  role: 'facility_operator',
  cluster_ids: ['00000000-0000-0000-0000-000000000003'],
  email: 'operator@plant-line.com',
  name: 'Dr. Hélène Vance',
  facility_id: '00000000-0000-0000-0000-000000000010',
  facility_name: 'Central Rail Smelter & Foundry #4',
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        setUser(JSON.parse(stored));
      } else {
        // Seed default authenticated industrial session for seamless exploration
        setUser(DEFAULT_USER);
        localStorage.setItem(STORAGE_KEY, JSON.stringify(DEFAULT_USER));
      }
    } catch (e) {
      console.warn('Failed to parse auth session from localStorage', e);
      setUser(DEFAULT_USER);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const login = async (email: string, role: UserRole = 'facility_operator'): Promise<AuthUser> => {
    setIsLoading(true);
    // Simulate brief handshake
    await new Promise((resolve) => setTimeout(resolve, 600));

    const updatedUser: AuthUser = {
      ...DEFAULT_USER,
      email,
      role,
    };
    setUser(updatedUser);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(updatedUser));
    setIsLoading(false);
    return updatedUser;
  };

  const register = async (name: string, email: string, role: UserRole = 'facility_operator'): Promise<AuthUser> => {
    setIsLoading(true);
    await new Promise((resolve) => setTimeout(resolve, 700));

    const newUser: AuthUser = {
      user_id: '00000000-0000-0000-0000-' + Math.floor(Math.random() * 1000000000000).toString().padStart(12, '0'),
      org_id: '00000000-0000-0000-0000-' + Math.floor(Math.random() * 1000000000000).toString().padStart(12, '0'),
      role,
      cluster_ids: ['00000000-0000-0000-0000-000000000003'],
      email,
      name,
      facility_id: '00000000-0000-0000-0000-000000000010',
      facility_name: 'Main Production Site',
    };
    setUser(newUser);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(newUser));
    setIsLoading(false);
    return newUser;
  };

  const logout = () => {
    localStorage.removeItem(STORAGE_KEY);
    setUser(null);
  };

  const switchRole = (newRole: UserRole) => {
    if (!user) return;
    const updated = { ...user, role: newRole };
    setUser(updated);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
  };

  const updateOnboarding = (data: {
    org_name: string;
    org_type: OrgType;
    facility_name: string;
    facility_country: string;
    facility_type?: 'generator' | 'receiver' | 'aggregator';
  }) => {
    if (!user) return;
    const updated: AuthUser = {
      ...user,
      facility_name: data.facility_name,
    };
    setUser(updated);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
  };

  const getAuthHeaders = (): Record<string, string> => {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    if (user) {
      headers['X-User-Id'] = user.user_id;
      headers['X-Org-Id'] = user.org_id;
      headers['X-Role'] = user.role;
    }
    return headers;
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        login,
        register,
        logout,
        switchRole,
        updateOnboarding,
        getAuthHeaders,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
