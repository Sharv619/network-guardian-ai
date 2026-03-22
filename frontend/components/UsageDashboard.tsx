import { useState, useEffect } from 'react';
import { BarChart3, TrendingUp, Shield, AlertTriangle, Activity, Loader2 } from 'lucide-react';
import { 
  getTenantUsage, 
  getTenantDailyUsage, 
  getDeveloperStats,
  getCurrentTenant,
  DailyUsage,
  UsageStats,
  DeveloperStats
} from '../services/tenantService';

const UsageDashboard: React.FC = () => {
  const [usage, setUsage] = useState<UsageStats | null>(null);
  const [dailyUsage, setDailyUsage] = useState<DailyUsage[]>([]);
  const [devStats, setDevStats] = useState<DeveloperStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const tenantId = getCurrentTenant();
      
      const [usageData, dailyData, statsData] = await Promise.all([
        getTenantUsage(tenantId),
        getTenantDailyUsage(tenantId, 14),
        getDeveloperStats().catch(() => null),
      ]);
      
      setUsage(usageData);
      setDailyUsage(dailyData);
      setDevStats(statsData);
    } catch (error) {
      console.error('Failed to load usage data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-8 h-8 animate-spin text-accent" />
      </div>
    );
  }

  const maxDailyDomains = Math.max(...dailyUsage.map(d => d.domains_analyzed), 1);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-dark-100 flex items-center gap-2">
            <BarChart3 className="w-6 h-6 text-accent" />
            Usage Dashboard
          </h2>
          <p className="text-dark-400 mt-1">Monitor your API usage and quota</p>
        </div>
        <button
          onClick={loadData}
          className="px-4 py-2 bg-dark-800 border border-dark-700 rounded-lg hover:border-accent/50 transition-colors"
        >
          Refresh
        </button>
      </div>

      {/* Stats Overview */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-dark-800/50 border border-dark-700 rounded-lg p-4">
          <div className="flex items-center gap-2 text-dark-400 text-sm mb-1">
            <Activity className="w-4 h-4" />
            Total Analyzed
          </div>
          <div className="text-2xl font-bold text-accent">
            {usage?.total_domains_analyzed.toLocaleString() || 0}
          </div>
        </div>

        <div className="bg-dark-800/50 border border-dark-700 rounded-lg p-4">
          <div className="flex items-center gap-2 text-dark-400 text-sm mb-1">
            <AlertTriangle className="w-4 h-4" />
            Threats Detected
          </div>
          <div className="text-2xl font-bold text-red-400">
            {usage?.threats_detected.toLocaleString() || 0}
          </div>
        </div>

        <div className="bg-dark-800/50 border border-dark-700 rounded-lg p-4">
          <div className="flex items-center gap-2 text-dark-400 text-sm mb-1">
            <Shield className="w-4 h-4" />
            Categories
          </div>
          <div className="text-2xl font-bold text-blue-400">
            {usage?.unique_categories || 0}
          </div>
        </div>

        <div className="bg-dark-800/50 border border-dark-700 rounded-lg p-4">
          <div className="flex items-center gap-2 text-dark-400 text-sm mb-1">
            <TrendingUp className="w-4 h-4" />
            Usage
          </div>
          <div className={`text-2xl font-bold ${
            (usage?.percentage_used || 0) > 80 ? 'text-red-400' :
            (usage?.percentage_used || 0) > 50 ? 'text-yellow-400' : 'text-green-400'
          }`}>
            {usage?.percentage_used.toFixed(1) || 0}%
          </div>
        </div>
      </div>

      {/* Usage Bar */}
      {!usage?.tier_unlimited && usage && (
        <div className="bg-dark-800/50 border border-dark-700 rounded-lg p-4">
          <div className="flex justify-between items-center mb-2">
            <span className="text-dark-300">Daily Quota Usage</span>
            <span className="text-dark-100 font-medium">
              {usage.total_domains_analyzed.toLocaleString()} / {usage.tier_limit.toLocaleString()}
            </span>
          </div>
          <div className="h-4 bg-dark-900 rounded-full overflow-hidden">
            <div
              className={`h-full transition-all rounded-full ${
                usage.percentage_used > 80 ? 'bg-red-500' :
                usage.percentage_used > 50 ? 'bg-yellow-500' : 'bg-accent'
              }`}
              style={{ width: `${Math.min(usage.percentage_used, 100)}%` }}
            />
          </div>
          <div className="flex justify-between mt-2 text-sm text-dark-400">
            <span>0</span>
            <span>{Math.round(usage.tier_limit * 0.5).toLocaleString()}</span>
            <span>{usage.tier_limit.toLocaleString()}</span>
          </div>
        </div>
      )}

      {usage?.tier_unlimited && (
        <div className="bg-purple-500/10 border border-purple-500/30 rounded-lg p-4 flex items-center gap-3">
          <Shield className="w-6 h-6 text-purple-400" />
          <div>
            <div className="text-purple-400 font-medium">Unlimited Usage</div>
            <div className="text-purple-300/70 text-sm">You have unlimited API access on your Enterprise plan</div>
          </div>
        </div>
      )}

      {/* Daily Chart */}
      <div className="bg-dark-800/50 border border-dark-700 rounded-lg p-4">
        <h3 className="text-lg font-medium text-dark-100 mb-4">Daily Activity (Last 14 Days)</h3>
        
        {dailyUsage.length > 0 ? (
          <div className="h-48 flex items-end gap-2">
            {dailyUsage.map((day, i) => (
              <div key={i} className="flex-1 flex flex-col items-center gap-1">
                <div className="w-full bg-dark-900 rounded-t relative group">
                  <div
                    className="w-full bg-accent/70 hover:bg-accent rounded-t transition-colors relative"
                    style={{ 
                      height: `${Math.max((day.domains_analyzed / maxDailyDomains) * 100, 4)}%`,
                      minHeight: '4px'
                    }}
                  >
                    <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-dark-700 text-xs text-dark-100 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">
                      {day.domains_analyzed} domains
                    </div>
                  </div>
                </div>
                <span className="text-xs text-dark-500 transform -rotate-45 origin-top-left mt-2">
                  {new Date(day.date).toLocaleDateString('en', { month: 'short', day: 'numeric' })}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <div className="h-48 flex items-center justify-center text-dark-400">
            No usage data available
          </div>
        )}
      </div>

      {/* API Keys */}
      {devStats && (
        <div className="grid md:grid-cols-2 gap-4">
          <div className="bg-dark-800/50 border border-dark-700 rounded-lg p-4">
            <h3 className="text-lg font-medium text-dark-100 mb-3">API Keys</h3>
            <div className="flex items-center gap-4">
              <div className="text-3xl font-bold text-accent">{devStats.total_api_keys}</div>
              <div className="text-sm text-dark-400">
                <div>{devStats.active_keys} active</div>
                <div>{devStats.total_api_keys - devStats.active_keys} revoked</div>
              </div>
            </div>
          </div>

          <div className="bg-dark-800/50 border border-dark-700 rounded-lg p-4">
            <h3 className="text-lg font-medium text-dark-100 mb-3">Rate Limit</h3>
            <div className="flex items-center gap-4">
              <div className="text-3xl font-bold text-blue-400">
                {devStats.rate_limit.requests_per_minute}
              </div>
              <div className="text-sm text-dark-400">
                <div>requests/min</div>
                <div>{devStats.rate_limit.requests_per_day.toLocaleString()} requests/day</div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default UsageDashboard;
