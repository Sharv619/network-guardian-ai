import { useState, useEffect } from 'react';
import { 
  Users, 
  Plus, 
  Search, 
  RefreshCw, 
  Shield, 
  AlertTriangle,
  CheckCircle,
  XCircle,
  Activity,
  Key,
  Loader2
} from 'lucide-react';
import {
  getTenants,
  getTenantUsage,
  getDeveloperStats,
  Tenant,
  UsageStats,
  DeveloperStats
} from '../services/tenantService';

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

const StatusBadge: React.FC<{ active: boolean }> = ({ active }) => (
  <span className={`flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${
    active ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
  }`}>
    {active ? <CheckCircle className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
    {active ? 'Active' : 'Inactive'}
  </span>
);

const AdminDashboard: React.FC = () => {
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [selectedTenant, setSelectedTenant] = useState<Tenant | null>(null);
  const [usage, setUsage] = useState<UsageStats | null>(null);
  const [devStats, setDevStats] = useState<DeveloperStats | null>(null);
  const [loadingDetails, setLoadingDetails] = useState(false);

  useEffect(() => {
    loadTenants();
  }, []);

  const loadTenants = async () => {
    try {
      setLoading(true);
      const data = await getTenants(1, 100);
      setTenants(data.tenants);
    } catch (error) {
      console.error('Failed to load tenants:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadTenantDetails = async (tenant: Tenant) => {
    setSelectedTenant(tenant);
    setLoadingDetails(true);
    
    try {
      const [usageData, statsData] = await Promise.all([
        getTenantUsage(tenant.id),
        getDeveloperStats()
      ]);
      setUsage(usageData);
      setDevStats(statsData);
    } catch (error) {
      console.error('Failed to load tenant details:', error);
    } finally {
      setLoadingDetails(false);
    }
  };

  const filteredTenants = tenants.filter(t => 
    t.name.toLowerCase().includes(search.toLowerCase()) ||
    t.subdomain.toLowerCase().includes(search.toLowerCase())
  );

  const stats = {
    total: tenants.length,
    active: tenants.filter(t => t.is_active).length,
    free: tenants.filter(t => t.subscription_tier === 'free').length,
    pro: tenants.filter(t => t.subscription_tier === 'pro').length,
    enterprise: tenants.filter(t => t.subscription_tier === 'enterprise').length,
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-dark-100 flex items-center gap-2">
            <Users className="w-6 h-6 text-accent" />
            Tenant Management
          </h2>
          <p className="text-dark-400 mt-1">Manage your customers and their subscriptions</p>
        </div>
        <button
          onClick={loadTenants}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 bg-dark-800 border border-dark-700 rounded-lg hover:border-accent/50 transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <div className="bg-dark-800/50 border border-dark-700 rounded-lg p-4">
          <div className="text-sm text-dark-400">Total Tenants</div>
          <div className="text-2xl font-bold text-dark-100 mt-1">{stats.total}</div>
        </div>
        <div className="bg-dark-800/50 border border-dark-700 rounded-lg p-4">
          <div className="text-sm text-dark-400">Active</div>
          <div className="text-2xl font-bold text-green-400 mt-1">{stats.active}</div>
        </div>
        <div className="bg-dark-800/50 border border-dark-700 rounded-lg p-4">
          <div className="text-sm text-dark-400">Free Tier</div>
          <div className="text-2xl font-bold text-gray-400 mt-1">{stats.free}</div>
        </div>
        <div className="bg-dark-800/50 border border-dark-700 rounded-lg p-4">
          <div className="text-sm text-dark-400">Pro Tier</div>
          <div className="text-2xl font-bold text-blue-400 mt-1">{stats.pro}</div>
        </div>
        <div className="bg-dark-800/50 border border-dark-700 rounded-lg p-4">
          <div className="text-sm text-dark-400">Enterprise</div>
          <div className="text-2xl font-bold text-purple-400 mt-1">{stats.enterprise}</div>
        </div>
      </div>

      <div className="grid md:grid-cols-3 gap-6">
        {/* Tenant List */}
        <div className="md:col-span-2 bg-dark-800/50 border border-dark-700 rounded-lg overflow-hidden">
          <div className="p-4 border-b border-dark-700">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-dark-400" />
              <input
                type="text"
                placeholder="Search tenants..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full pl-10 pr-4 py-2 bg-dark-900 border border-dark-700 rounded-lg text-dark-100 focus:border-accent focus:outline-none"
              />
            </div>
          </div>

          <div className="divide-y divide-dark-700 max-h-96 overflow-y-auto">
            {loading ? (
              <div className="p-8 text-center">
                <Loader2 className="w-8 h-8 animate-spin mx-auto text-accent" />
                <p className="text-dark-400 mt-2">Loading tenants...</p>
              </div>
            ) : filteredTenants.length === 0 ? (
              <div className="p-8 text-center">
                <Users className="w-8 h-8 mx-auto text-dark-500" />
                <p className="text-dark-400 mt-2">No tenants found</p>
              </div>
            ) : (
              filteredTenants.map((tenant) => (
                <button
                  key={tenant.id}
                  onClick={() => loadTenantDetails(tenant)}
                  className={`w-full p-4 flex items-center gap-4 hover:bg-dark-700/50 transition-colors ${
                    selectedTenant?.id === tenant.id ? 'bg-accent/10' : ''
                  }`}
                >
                  <div className="w-10 h-10 bg-accent/20 rounded-full flex items-center justify-center">
                    <Shield className="w-5 h-5 text-accent" />
                  </div>
                  <div className="flex-1 text-left">
                    <div className="font-medium text-dark-100">{tenant.name}</div>
                    <div className="text-sm text-dark-400">{tenant.subdomain}</div>
                  </div>
                  <div className="flex items-center gap-2">
                    <TierBadge tier={tenant.subscription_tier} />
                    <StatusBadge active={tenant.is_active} />
                  </div>
                </button>
              ))
            )}
          </div>
        </div>

        {/* Tenant Details */}
        <div className="bg-dark-800/50 border border-dark-700 rounded-lg overflow-hidden">
          {selectedTenant ? (
            loadingDetails ? (
              <div className="p-8 text-center">
                <Loader2 className="w-8 h-8 animate-spin mx-auto text-accent" />
                <p className="text-dark-400 mt-2">Loading details...</p>
              </div>
            ) : (
              <div className="p-4">
                <h3 className="font-bold text-lg text-dark-100 mb-4">{selectedTenant.name}</h3>
                
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="bg-dark-900 rounded-lg p-3">
                      <div className="text-xs text-dark-400">Domains Analyzed</div>
                      <div className="text-xl font-bold text-accent">
                        {usage?.total_domains_analyzed || 0}
                      </div>
                    </div>
                    <div className="bg-dark-900 rounded-lg p-3">
                      <div className="text-xs text-dark-400">Threats Detected</div>
                      <div className="text-xl font-bold text-red-400">
                        {usage?.threats_detected || 0}
                      </div>
                    </div>
                  </div>

                  {usage && !usage.tier_unlimited && (
                    <div>
                      <div className="flex justify-between text-sm mb-1">
                        <span className="text-dark-400">Daily Usage</span>
                        <span className="text-dark-200">
                          {usage.total_domains_analyzed} / {usage.tier_limit}
                        </span>
                      </div>
                      <div className="h-2 bg-dark-900 rounded-full overflow-hidden">
                        <div
                          className={`h-full transition-all ${
                            usage.percentage_used > 80 ? 'bg-red-500' :
                            usage.percentage_used > 50 ? 'bg-yellow-500' : 'bg-accent'
                          }`}
                          style={{ width: `${Math.min(usage.percentage_used, 100)}%` }}
                        />
                      </div>
                    </div>
                  )}

                  {usage?.tier_unlimited && (
                    <div className="bg-purple-500/10 border border-purple-500/30 rounded-lg p-3 flex items-center gap-2">
                      <Shield className="w-5 h-5 text-purple-400" />
                      <span className="text-purple-400 text-sm">Unlimited usage</span>
                    </div>
                  )}

                  <div className="border-t border-dark-700 pt-4">
                    <h4 className="text-sm font-medium text-dark-300 mb-2 flex items-center gap-2">
                      <Key className="w-4 h-4" />
                      API Keys
                    </h4>
                    <div className="bg-dark-900 rounded-lg p-3">
                      <div className="text-2xl font-bold text-dark-100">
                        {devStats?.total_api_keys || 0}
                      </div>
                      <div className="text-xs text-dark-400">
                        {devStats?.active_keys || 0} active
                      </div>
                    </div>
                  </div>

                  <div className="border-t border-dark-700 pt-4">
                    <h4 className="text-sm font-medium text-dark-300 mb-2 flex items-center gap-2">
                      <Activity className="w-4 h-4" />
                      Rate Limit
                    </h4>
                    <div className="bg-dark-900 rounded-lg p-3">
                      <div className="text-sm text-dark-200">
                        {devStats?.rate_limit.requests_per_minute || 0} requests/min
                      </div>
                      <div className="text-xs text-dark-400">
                        {devStats?.rate_limit.requests_per_day || 0} requests/day
                      </div>
                    </div>
                  </div>

                  <div className="border-t border-dark-700 pt-4">
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      <div className="text-dark-400">Tenant ID</div>
                      <div className="text-dark-200">{selectedTenant.id}</div>
                      <div className="text-dark-400">Created</div>
                      <div className="text-dark-200">
                        {new Date(selectedTenant.created_at).toLocaleDateString()}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )
          ) : (
            <div className="p-8 text-center">
              <Users className="w-8 h-8 mx-auto text-dark-500" />
              <p className="text-dark-400 mt-2">Select a tenant to view details</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AdminDashboard;
