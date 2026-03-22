// Tenant & Multi-tenancy API Service

const API_BASE = import.meta.env.VITE_API_BASE || '';
const getTenantId = () => localStorage.getItem('tenant_id') || '1';
const getAuthToken = () => localStorage.getItem('auth_token');

interface RequestOptions {
  method?: string;
  body?: any;
  headers?: Record<string, string>;
}

async function apiRequest<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const token = getAuthToken();
  const tenantId = getTenantId();
  
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'X-Tenant-ID': tenantId,
    ...options.headers,
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  try {
    const res = await fetch(`${API_BASE}${endpoint}`, {
      method: options.method || 'GET',
      headers,
      body: options.body ? JSON.stringify(options.body) : undefined,
    });

    if (!res.ok) {
      const error = await res.json().catch(() => ({ detail: 'Request failed' }));
      throw new Error(error.detail || `HTTP ${res.status}`);
    }

    return res.json();
  } catch (error) {
    console.error(`API Error [${endpoint}]:`, error);
    throw error;
  }
}

// Types
export interface Tenant {
  id: number;
  name: string;
  subdomain: string;
  api_key: string;
  is_active: boolean;
  subscription_tier: 'free' | 'pro' | 'enterprise';
  stripe_customer_id?: string;
  created_at: string;
  updated_at: string;
}

export interface TenantListResponse {
  tenants: Tenant[];
  total: number;
  page: number;
  size: number;
}

export interface UsageStats {
  tenant_id: number;
  total_domains_analyzed: number;
  threats_detected: number;
  unique_categories: number;
  subscription_tier: string;
  tier_limit: number;
  tier_unlimited: boolean;
  percentage_used: number;
}

export interface DailyUsage {
  date: string;
  domains_analyzed: number;
  threats_detected: number;
}

export interface PricingTier {
  tier: string;
  name: string;
  price_monthly: number;
  price_yearly: number;
  requests_per_day: number;
  requests_per_minute: number;
  features: string[];
}

export interface PricingInfo {
  tiers: Record<string, PricingTier>;
  current_tier: string;
}

export interface Subscription {
  subscription_id: string | null;
  customer_id: string;
  status: string;
  tier: string;
  current_period_end: string | null;
  cancel_at_period_end: boolean;
}

export interface DeveloperStats {
  tenant_id: number;
  total_api_keys: number;
  active_keys: number;
  total_requests: number;
  rate_limit: {
    tier: string;
    requests_per_minute: number;
    requests_per_day: number;
    current_usage: number;
    remaining: number;
    reset_at: string;
  };
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface RegisterRequest {
  username: string;
  email: string;
  password: string;
  company_name: string;
  subscription_tier?: string;
}

export interface RegisterResponse {
  user_id: string;
  tenant_id: number;
  username: string;
  email: string;
  company_name: string;
  subscription_tier: string;
  message: string;
}

// Auth API
export const login = async (username: string, password: string): Promise<LoginResponse> => {
  return apiRequest<LoginResponse>('/auth/token', {
    method: 'POST',
    body: { username, password },
  });
};

export const register = async (data: RegisterRequest): Promise<RegisterResponse> => {
  return apiRequest<RegisterResponse>('/auth/register', {
    method: 'POST',
    body: data,
  });
};

export const logout = () => {
  localStorage.removeItem('auth_token');
  localStorage.removeItem('tenant_id');
  localStorage.removeItem('username');
};

// Tenant API
export const getTenants = async (page = 1, size = 10): Promise<TenantListResponse> => {
  return apiRequest<TenantListResponse>(`/tenants/?page=${page}&size=${size}`);
};

export const getTenant = async (id: number): Promise<Tenant> => {
  return apiRequest<Tenant>(`/tenants/${id}`);
};

export const getTenantUsage = async (id: number): Promise<UsageStats> => {
  return apiRequest<UsageStats>(`/tenants/${id}/usage`);
};

export const getTenantDailyUsage = async (id: number, days = 7): Promise<DailyUsage[]> => {
  return apiRequest<DailyUsage[]>(`/tenants/${id}/usage/daily?days=${days}`);
};

export const createTenant = async (data: Partial<Tenant>): Promise<Tenant> => {
  return apiRequest<Tenant>('/tenants/', {
    method: 'POST',
    body: data,
  });
};

export const updateTenant = async (id: number, data: Partial<Tenant>): Promise<Tenant> => {
  return apiRequest<Tenant>(`/tenants/${id}`, {
    method: 'PUT',
    body: data,
  });
};

export const activateTenant = async (id: number): Promise<Tenant> => {
  return apiRequest<Tenant>(`/tenants/${id}/activate`, {
    method: 'POST',
  });
};

export const deactivateTenant = async (id: number): Promise<Tenant> => {
  return apiRequest<Tenant>(`/tenants/${id}/deactivate`, {
    method: 'POST',
  });
};

// Billing API
export const getPricing = async (): Promise<PricingInfo> => {
  return apiRequest<PricingInfo>('/billing/pricing');
};

export const getSubscription = async (): Promise<Subscription> => {
  return apiRequest<Subscription>('/billing/subscription');
};

export const createCheckout = async (tier: string, successUrl: string, cancelUrl: string) => {
  return apiRequest('/billing/checkout', {
    method: 'POST',
    body: { tier, success_url: successUrl, cancel_url: cancelUrl },
  });
};

export const createPortal = async (returnUrl: string) => {
  return apiRequest('/billing/portal', {
    method: 'POST',
    body: { return_url: returnUrl },
  });
};

export const cancelSubscription = async (immediately = false) => {
  return apiRequest(`/billing/cancel?immediately=${immediately}`, {
    method: 'POST',
  });
};

export const getUsage = async (): Promise<any> => {
  return apiRequest('/billing/usage');
};

// Developer API
export const getDeveloperStats = async (): Promise<DeveloperStats> => {
  return apiRequest<DeveloperStats>('/developer/stats');
};

export const getRateLimit = async () => {
  return apiRequest('/developer/rate-limit');
};

export const generateApiKey = async (name: string, expiresDays = 365) => {
  return apiRequest('/developer/api-keys', {
    method: 'POST',
    body: { name, expires_days: expiresDays },
  });
};

export const revokeApiKey = async (name: string) => {
  return apiRequest(`/developer/api-keys/${encodeURIComponent(name)}`, {
    method: 'DELETE',
  });
};

// Tenant context helpers
export const setCurrentTenant = (tenantId: number) => {
  localStorage.setItem('tenant_id', tenantId.toString());
};

export const getCurrentTenant = (): number => {
  return parseInt(localStorage.getItem('tenant_id') || '1', 10);
};

export const setAuthToken = (token: string) => {
  localStorage.setItem('auth_token', token);
};

export const isAuthenticated = (): boolean => {
  return !!localStorage.getItem('auth_token');
};

export const getUsername = (): string | null => {
  return localStorage.getItem('username');
};

export const setUsername = (username: string) => {
  localStorage.setItem('username', username);
};
