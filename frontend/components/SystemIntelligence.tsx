import React, { useState, useEffect } from 'react';
import { 
  Brain, 
  Cpu, 
  Shield, 
  Zap, 
  Database, 
  Globe, 
  Wifi, 
  Eye, 
  Activity, 
  Target,
  Lock,
  TrendingUp,
  Hexagon,
  Radar,
  Bot,
  Sparkles,
  Layers,
  Gauge,
  PieChart,
  BarChart
} from 'lucide-react';

interface SystemIntelligenceProps {
  selectedModel: string;
}

interface SystemStats {
  classifier: {
    total_patterns: number;
    category_distribution: Record<string, number>;
    confidence_distribution: Record<string, number>;
  };
  cache: {
    memory_cache_size: number;
    valid_memory_entries: number;
    disk_cache_exists: boolean;
    source_distribution: Record<string, number>;
    cache_file_size: number;
  };
  optimization: {
    description: string;
    benefits: string[];
  };
  autonomy_score: number;
  local_decisions: number;
  cloud_decisions: number;
  total_decisions: number;
  patterns_learned: number;
  seed_patterns: number;
  learned_patterns: number;
  system_usage?: {
    active_integrations: Array<{name: string; status: string; description: string}>;
    tracker_detection: {
      total_detected: number;
      categories: Record<string, number>;
      detection_methods: string[];
    };
  };
}

const categoryColors: Record<string, { bg: string; glow: string; icon: string }> = {
  'System': { bg: 'from-blue-500 to-cyan-400', glow: 'shadow-blue-500/50', icon: '🛡️' },
  'Tracker': { bg: 'from-amber-500 to-orange-400', glow: 'shadow-amber-500/50', icon: '👁️' },
  'Malware': { bg: 'from-red-500 to-pink-500', glow: 'shadow-red-500/50', icon: '💀' },
  'Malicious Pattern': { bg: 'from-purple-500 to-violet-400', glow: 'shadow-purple-500/50', icon: '⚠️' },
  'Privacy': { bg: 'from-emerald-500 to-teal-400', glow: 'shadow-emerald-500/50', icon: '🔒' },
  'Ads': { bg: 'from-rose-500 to-red-400', glow: 'shadow-rose-500/50', icon: '🚫' },
};

const SystemIntelligence: React.FC<SystemIntelligenceProps> = ({ selectedModel }) => {
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'patterns' | 'performance'>('overview');
  const [alertBox, setAlertBox] = useState<{title: string; message: string; type: 'info' | 'success' | 'warning'} | null>(null);

  const fetchSystemStats = async () => {
    try {
      const response = await fetch('/api/stats/system');
      if (!response.ok) throw new Error('Failed to fetch system stats');
      const data = await response.json();
      setStats(data);
      setError(null);
    } catch (err) {
      console.error('Error fetching system stats:', err);
      setError('Unable to fetch live system data');
    }
  };

  useEffect(() => {
    fetchSystemStats();
    const interval = setInterval(fetchSystemStats, 5000);
    return () => clearInterval(interval);
  }, []);

  if (error || !stats) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center p-8">
        <div className="bg-slate-900/80 backdrop-blur-xl border border-red-500/30 rounded-2xl p-8 text-center max-w-md">
          <div className="w-20 h-20 mx-auto mb-4 rounded-full bg-red-500/20 flex items-center justify-center">
            <Radar className="w-10 h-10 text-red-400" />
          </div>
          <h2 className="text-2xl font-bold text-white mb-2">Connection Lost</h2>
          <p className="text-slate-400">{error || 'Connecting to backend...'}</p>
        </div>
      </div>
    );
  }

  const autonomyPercentage = stats.total_decisions > 0 
    ? Math.round((stats.local_decisions / stats.total_decisions) * 100)
    : 0;

  const categoryData = Object.entries(stats.classifier.category_distribution).map(([name, value]) => ({
    name,
    value,
    ...(categoryColors[name] || { bg: 'from-slate-500 to-slate-400', glow: 'shadow-slate-500/50', icon: '📊' })
  }));

  const totalCategoryCount = Object.values(stats.classifier.category_distribution).reduce((a, b) => a + b, 0);

  return (
    <div className="min-h-screen bg-slate-950 p-6 space-y-6">
      {/* Hero Header */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-slate-900 via-purple-900/20 to-slate-900 border border-purple-500/20 p-8">
        <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxwYXRoIGQ9Ik0zNiAxOGMtOS45NDEgMC0xOCA4LjA1OS0xOCAxOHM4LjA1OSAxOCAxOCAxOCAxOC04LjA1OSAxOC0xOC04LjA1OS0xOC0xOC0xOHptMCAzMmMtNy43MzIgMC0xNC02LjI2OC0xNC0xNHM2LjI2OC0xNCAxNC0xNCAxNCA2LjI2OCAxNCAxNC02LjI2OCAxNC0xNHoiIGZpbGw9IiNmZmYiIGZpbGwtb3BhY2l0eT0iLjAyIi8+PC9nPjwvc3ZnPg==')] opacity-30"></div>
        
        <div className="relative flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
          <div className="flex items-center gap-4">
            <div className="relative">
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-purple-500 to-cyan-400 flex items-center justify-center animate-pulse">
                <Brain className="w-8 h-8 text-white" />
              </div>
              <div className="absolute -top-1 -right-1 w-4 h-4 bg-green-400 rounded-full animate-ping"></div>
            </div>
            <div>
              <h1 className="text-4xl font-black bg-gradient-to-r from-white via-purple-200 to-cyan-200 bg-clip-text text-transparent">
                NETWORK GUARDIAN
              </h1>
              <p className="text-slate-400 flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-purple-400" />
                AI-Powered Threat Detection System
              </p>
            </div>
          </div>

          <div className="flex gap-3">
            <StatCard 
              label="Autonomy Score" 
              value={`${autonomyPercentage}%`} 
              icon={<Gauge className="w-5 h-5" />}
              color="purple"
              onClick={() => setAlertBox({
                title: 'Autonomy Score',
                message: `Local Analysis Rate: ${autonomyPercentage}% of decisions made locally without cloud API calls.\n\nThis shows how effectively the system uses local ML heuristics (entropy, metadata classification, anomaly detection) to reduce Gemini API usage and costs.`,
                type: 'info'
              })}
            />
            <StatCard 
              label="Learned Patterns" 
              value={`${stats.patterns_learned}`}
              icon={<Layers className="w-5 h-5" />}
              color="cyan"
              onClick={() => setAlertBox({
                title: 'Pattern Intelligence',
                message: `Seed Patterns: ${stats.seed_patterns}\nLearned Patterns: ${stats.learned_patterns}\n\nThe system learns from analyzed domains to improve detection. Each pattern represents a learned threat signature.`,
                type: 'success'
              })}
            />
            <StatCard 
              label="Total Decisions" 
              value={stats.total_decisions.toString()} 
              icon={<Bot className="w-5 h-5" />}
              color="green"
              onClick={() => setAlertBox({
                title: 'Decision Analysis',
                message: `Local Decisions: ${stats.local_decisions}\nCloud Decisions: ${stats.cloud_decisions}\nTotal: ${stats.total_decisions}\n\nLocal = entropy/metadata analysis\nCloud = Gemini AI analysis`,
                type: 'info'
              })}
            />
            <StatCard 
              label="Cache Efficiency" 
              value={`${stats.cache.valid_memory_entries}`}
              icon={<Database className="w-5 h-5" />}
              color="amber"
              onClick={() => setAlertBox({
                title: 'Cache Intelligence',
                message: `Memory Entries: ${stats.cache.valid_memory_entries}\nCache Size: ${stats.cache.memory_cache_size}\nDisk Cache: ${stats.cache.disk_cache_exists ? 'Active' : 'Inactive'}\nFile Size: ${(stats.cache.cache_file_size / 1024).toFixed(2)} KB\n\nCaching reduces redundant domain analysis and improves response times.`,
                type: 'warning'
              })}
            />
          </div>
        </div>
      </div>

      {/* Alert Box Modal */}
      {alertBox && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className={`max-w-md w-full rounded-2xl p-6 border ${
            alertBox.type === 'info' ? 'bg-blue-900/90 border-blue-500/50' :
            alertBox.type === 'success' ? 'bg-green-900/90 border-green-500/50' :
            'bg-amber-900/90 border-amber-500/50'
          }`}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xl font-bold text-white">{alertBox.title}</h3>
              <button 
                onClick={() => setAlertBox(null)}
                className="text-white/60 hover:text-white text-2xl"
              >
                ×
              </button>
            </div>
            <p className="text-white/80 whitespace-pre-line">{alertBox.message}</p>
            <button 
              onClick={() => setAlertBox(null)}
              className={`mt-6 w-full py-2 rounded-lg font-medium ${
                alertBox.type === 'info' ? 'bg-blue-600 hover:bg-blue-500' :
                alertBox.type === 'success' ? 'bg-green-600 hover:bg-green-500' :
                'bg-amber-600 hover:bg-amber-500'
              } text-white transition-colors`}
            >
              Close
            </button>
          </div>
        </div>
      )}

      {/* Tab Navigation */}
      <div className="flex gap-2 p-1 bg-slate-900/50 rounded-xl w-fit">
        {[
          { id: 'overview', label: 'Overview', icon: <Radar className="w-4 h-4" /> },
          { id: 'patterns', label: 'Pattern Intelligence', icon: <Hexagon className="w-4 h-4" /> },
          { id: 'performance', label: 'Performance', icon: <TrendingUp className="w-4 h-4" /> },
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as typeof activeTab)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all ${
              activeTab === tab.id 
                ? 'bg-purple-600 text-white shadow-lg shadow-purple-500/25' 
                : 'text-slate-400 hover:text-white hover:bg-slate-800'
            }`}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {/* Overview Tab */}
      {activeTab === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Autonomy Ring */}
          <div className="lg:col-span-1 bg-gradient-to-br from-slate-900 to-slate-800 rounded-3xl border border-slate-700/50 p-6">
            <h3 className="text-lg font-bold text-white mb-6 flex items-center gap-2">
              <Brain className="w-5 h-5 text-purple-400" />
              Decision Autonomy
            </h3>
            <div className="relative w-48 h-48 mx-auto">
              <svg className="w-full h-full transform -rotate-90">
                <circle cx="96" cy="96" r="88" fill="none" stroke="#1e293b" strokeWidth="12" />
                <circle 
                  cx="96" cy="96" r="88" fill="none" 
                  stroke="url(#autonomyGradient)" strokeWidth="12"
                  strokeLinecap="round"
                  strokeDasharray={`${autonomyPercentage * 5.52} 552`}
                  className="transition-all duration-1000"
                />
                <defs>
                  <linearGradient id="autonomyGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%" stopColor="#8b5cf6" />
                    <stop offset="100%" stopColor="#06b6d4" />
                  </linearGradient>
                </defs>
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-5xl font-black text-white">{autonomyPercentage}%</span>
                <span className="text-slate-400 text-sm">Local Processing</span>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3 mt-6">
              <div className="bg-slate-800/50 rounded-xl p-3 text-center">
                <div className="text-2xl font-bold text-purple-400">{stats.local_decisions}</div>
                <div className="text-xs text-slate-500">Local</div>
              </div>
              <div className="bg-slate-800/50 rounded-xl p-3 text-center">
                <div className="text-2xl font-bold text-cyan-400">{stats.cloud_decisions}</div>
                <div className="text-xs text-slate-500">Cloud</div>
              </div>
            </div>
          </div>

          {/* Pattern Distribution - Hexagonal */}
          <div className="lg:col-span-2 bg-gradient-to-br from-slate-900 to-slate-800 rounded-3xl border border-slate-700/50 p-6">
            <h3 className="text-lg font-bold text-white mb-6 flex items-center gap-2">
              <Hexagon className="w-5 h-5 text-amber-400" />
              Threat Pattern Intelligence
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-3 gap-4">
              {categoryData.map((cat, idx) => (
                <div 
                  key={cat.name}
                  className={`relative group bg-gradient-to-br ${cat.bg} rounded-2xl p-4 shadow-lg ${cat.glow} hover:scale-105 transition-all duration-300 cursor-pointer overflow-hidden`}
                  style={{ animationDelay: `${idx * 100}ms` }}
                >
                  <div className="absolute top-2 right-2 text-3xl opacity-30">{cat.icon}</div>
                  <div className="relative">
                    <div className="text-4xl font-black text-white drop-shadow-lg">{cat.value}</div>
                    <div className="text-white/80 font-medium truncate">{cat.name}</div>
                    <div className="text-white/60 text-xs">
                      {((cat.value / totalCategoryCount) * 100).toFixed(0)}% of threats
                    </div>
                  </div>
                  <div className="absolute bottom-0 left-0 right-0 h-1 bg-white/30">
                    <div className="h-full bg-white/60 transition-all duration-500" style={{ width: `${(cat.value / totalCategoryCount) * 100}%` }}></div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Patterns Tab */}
      {activeTab === 'patterns' && (
        <div className="space-y-6">
          {/* Pattern Learning Progress */}
          <div className="bg-gradient-to-br from-slate-900 to-slate-800 rounded-3xl border border-slate-700/50 p-6">
            <h3 className="text-lg font-bold text-white mb-6 flex items-center gap-2">
              <Activity className="w-5 h-5 text-green-400" />
              Pattern Learning Engine
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              {[
                { label: 'Seed Patterns', value: stats.seed_patterns, color: 'blue', icon: <Sparkles className="w-5 h-5" /> },
                { label: 'Learned', value: stats.learned_patterns, color: 'purple', icon: <Brain className="w-5 h-5" /> },
                { label: 'Total Active', value: stats.patterns_learned, color: 'amber', icon: <Layers className="w-5 h-5" /> },
                { label: 'Confidence', value: '95%', color: 'green', icon: <Target className="w-5 h-5" /> },
              ].map((item, idx) => (
                <div key={idx} className="bg-slate-800/50 rounded-2xl p-5 border border-slate-700/50 hover:border-slate-600/50 transition-all">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-slate-400 text-sm">{item.label}</span>
                    <span className={`text-${item.color}-400`}>{item.icon}</span>
                  </div>
                  <div className={`text-3xl font-black text-${item.color}-400`}>{item.value}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Category Breakdown */}
          <div className="bg-gradient-to-br from-slate-900 to-slate-800 rounded-3xl border border-slate-700/50 p-6">
            <h3 className="text-lg font-bold text-white mb-6 flex items-center gap-2">
              <PieChart className="w-5 h-5 text-rose-400" />
              Threat Category Breakdown
            </h3>
            <div className="space-y-4">
              {categoryData.map((cat) => (
                <div key={cat.name} className="group">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-3">
                      <span className="text-2xl">{cat.icon}</span>
                      <span className="text-white font-medium">{cat.name}</span>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-slate-400">{cat.value} patterns</span>
                      <span className="text-white font-bold">
                        {totalCategoryCount > 0 ? ((cat.value / totalCategoryCount) * 100).toFixed(1) : 0}%
                      </span>
                    </div>
                  </div>
                  <div className="h-3 bg-slate-800 rounded-full overflow-hidden">
                    <div 
                      className={`h-full bg-gradient-to-r ${cat.bg} rounded-full transition-all duration-1000 group-hover:opacity-80`}
                      style={{ width: `${totalCategoryCount > 0 ? (cat.value / totalCategoryCount) * 100 : 0}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Performance Tab */}
      {activeTab === 'performance' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Cache Performance */}
          <div className="bg-gradient-to-br from-slate-900 to-slate-800 rounded-3xl border border-slate-700/50 p-6">
            <h3 className="text-lg font-bold text-white mb-6 flex items-center gap-2">
              <Database className="w-5 h-5 text-cyan-400" />
              Cache Intelligence
            </h3>
            <div className="grid grid-cols-2 gap-4 mb-6">
              <div className="bg-slate-800/50 rounded-2xl p-4">
                <div className="text-slate-400 text-sm mb-1">Memory Entries</div>
                <div className="text-3xl font-bold text-cyan-400">{stats.cache.valid_memory_entries}</div>
              </div>
              <div className="bg-slate-800/50 rounded-2xl p-4">
                <div className="text-slate-400 text-sm mb-1">Cache Size</div>
                <div className="text-3xl font-bold text-purple-400">{stats.cache.memory_cache_size}</div>
              </div>
            </div>
            <div className="space-y-3">
              <div className="flex items-center justify-between p-3 bg-slate-800/30 rounded-xl">
                <span className="text-slate-300">Disk Cache</span>
                <span className={`px-3 py-1 rounded-full text-xs font-bold ${
                  stats.cache.disk_cache_exists 
                    ? 'bg-green-500/20 text-green-400 border border-green-500/30' 
                    : 'bg-slate-700 text-slate-400'
                }`}>
                  {stats.cache.disk_cache_exists ? 'ACTIVE' : 'INACTIVE'}
                </span>
              </div>
              <div className="flex items-center justify-between p-3 bg-slate-800/30 rounded-xl">
                <span className="text-slate-300">Cache File</span>
                <span className="text-white font-mono">{(stats.cache.cache_file_size / 1024).toFixed(2)} KB</span>
              </div>
            </div>
          </div>

          {/* System Integrations */}
          <div className="bg-gradient-to-br from-slate-900 to-slate-800 rounded-3xl border border-slate-700/50 p-6">
            <h3 className="text-lg font-bold text-white mb-6 flex items-center gap-2">
              <Cpu className="w-5 h-5 text-green-400" />
              Active Integrations
            </h3>
            <div className="space-y-3">
              {stats.system_usage?.active_integrations.map((integration, idx) => (
                <div 
                  key={idx}
                  className="flex items-center justify-between p-4 bg-slate-800/30 rounded-xl border border-slate-700/30 hover:border-green-500/30 transition-all"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-green-500/20 flex items-center justify-center">
                      <Wifi className="w-5 h-5 text-green-400" />
                    </div>
                    <div>
                      <div className="text-white font-medium">{integration.name}</div>
                      <div className="text-slate-500 text-xs">{integration.description}</div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
                    <span className="text-green-400 text-sm font-medium">ACTIVE</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

const StatCard: React.FC<{
  label: string; 
  value: string; 
  icon: React.ReactNode; 
  color: string;
  onClick?: () => void;
}> = ({ label, value, icon, color, onClick }) => {
  const colorClasses = {
    purple: { border: 'border-purple-500/20 hover:border-purple-500/40', text: 'text-purple-400', bg: 'bg-purple-900/90' },
    cyan: { border: 'border-cyan-500/20 hover:border-cyan-500/40', text: 'text-cyan-400', bg: 'bg-cyan-900/90' },
    green: { border: 'border-green-500/20 hover:border-green-500/40', text: 'text-green-400', bg: 'bg-green-900/90' },
    amber: { border: 'border-amber-500/20 hover:border-amber-500/40', text: 'text-amber-400', bg: 'bg-amber-900/90' },
  };
  const c = colorClasses[color as keyof typeof colorClasses] || colorClasses.purple;
  
  return (
    <button 
      onClick={onClick}
      className={`bg-slate-800/50 backdrop-blur-xl rounded-2xl p-4 border ${c.border} transition-all hover:scale-105 text-left w-full cursor-pointer hover:bg-slate-700/50`}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="text-slate-400 text-xs">{label}</span>
        <span className={c.text}>{icon}</span>
      </div>
      <div className={`text-2xl font-black ${c.text}`}>{value}</div>
    </button>
  );
};

export default SystemIntelligence;
