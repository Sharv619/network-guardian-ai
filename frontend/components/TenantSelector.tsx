import { useState, useEffect } from 'react';
import { Building2, ChevronDown, Check, RefreshCw, Shield } from 'lucide-react';
import { 
  getTenants, 
  getTenantUsage, 
  Tenant, 
  UsageStats, 
  setCurrentTenant,
  isAuthenticated 
} from '../services/tenantService';

interface TenantSelectorProps {
  onTenantChange?: (tenant: Tenant) => void;
}

const TierBadge: React.FC<{ tier: string }> = ({ tier }) => {
  const colors = {
    free: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
    pro: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
    enterprise: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
  };
  
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-medium border ${colors[tier as keyof typeof colors] || colors.free}`}>
      {tier.toUpperCase()}
    </span>
  );
};

const TenantSelector: React.FC<TenantSelectorProps> = ({ onTenantChange }) => {
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [currentTenant, setCurrent] = useState<Tenant | null>(null);
  const [usage, setUsage] = useState<UsageStats | null>(null);
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isAuthenticated()) {
      loadTenants();
    }
  }, []);

  const loadTenants = async () => {
    try {
      setLoading(true);
      const data = await getTenants(1, 100);
      setTenants(data.tenants);
      
      const savedTenantId = parseInt(localStorage.getItem('tenant_id') || '1', 10);
      const selected = data.tenants.find(t => t.id === savedTenantId) || data.tenants[0];
      if (selected) {
        selectTenant(selected);
      }
    } catch (error) {
      console.error('Failed to load tenants:', error);
    } finally {
      setLoading(false);
    }
  };

  const selectTenant = async (tenant: Tenant) => {
    setCurrent(tenant);
    setCurrentTenant(tenant.id);
    setIsOpen(false);
    
    try {
      const usageData = await getTenantUsage(tenant.id);
      setUsage(usageData);
    } catch (error) {
      console.error('Failed to load usage:', error);
    }
    
    onTenantChange?.(tenant);
  };

  if (!isAuthenticated()) {
    return null;
  }

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-3 px-4 py-2 bg-dark-800 border border-dark-700 rounded-lg hover:border-accent/50 transition-colors"
      >
        <Building2 className="w-4 h-4 text-accent" />
        <div className="text-left">
          <div className="text-sm font-medium text-dark-100">
            {currentTenant?.name || 'Select Tenant'}
          </div>
          {currentTenant && (
            <div className="flex items-center gap-2">
              <TierBadge tier={currentTenant.subscription_tier} />
              {usage && (
                <span className="text-xs text-dark-400">
                  {usage.percentage_used}% used
                </span>
              )}
            </div>
          )}
        </div>
        <ChevronDown className={`w-4 h-4 text-dark-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <div className="absolute top-full right-0 mt-2 w-80 bg-dark-800 border border-dark-700 rounded-lg shadow-xl z-50 overflow-hidden">
          <div className="p-3 border-b border-dark-700 flex items-center justify-between">
            <span className="text-sm font-medium text-dark-300">Switch Tenant</span>
            <button
              onClick={loadTenants}
              className="p-1 hover:bg-dark-700 rounded transition-colors"
              disabled={loading}
            >
              <RefreshCw className={`w-4 h-4 text-dark-400 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>
          
          <div className="max-h-64 overflow-y-auto">
            {tenants.map((tenant) => (
              <button
                key={tenant.id}
                onClick={() => selectTenant(tenant)}
                className={`w-full px-4 py-3 flex items-start gap-3 hover:bg-dark-700 transition-colors ${
                  currentTenant?.id === tenant.id ? 'bg-accent/10' : ''
                }`}
              >
                <div className="flex-1 text-left">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-dark-100">{tenant.name}</span>
                    {currentTenant?.id === tenant.id && (
                      <Check className="w-4 h-4 text-accent" />
                    )}
                  </div>
                  <div className="text-xs text-dark-400 mt-1">
                    ID: {tenant.id} • {tenant.subdomain}
                  </div>
                  <div className="mt-1">
                    <TierBadge tier={tenant.subscription_tier} />
                  </div>
                </div>
                {!tenant.is_active && (
                  <span className="px-2 py-0.5 bg-red-500/20 text-red-400 text-xs rounded">
                    Inactive
                  </span>
                )}
              </button>
            ))}
          </div>
          
          {tenants.length === 0 && !loading && (
            <div className="p-4 text-center text-dark-400">
              <Shield className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p className="text-sm">No tenants found</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default TenantSelector;
