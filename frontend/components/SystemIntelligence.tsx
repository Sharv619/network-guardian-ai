import React, { useState, useEffect } from 'react';
import { 
  Brain, 
  Cpu, 
  Network, 
  Shield, 
  Zap, 
  TrendingUp, 
  Database, 
  Globe, 
  Wifi, 
  Eye, 
  Thermometer, 
  BarChart3, 
  Target, 
  Lock, 
  Activity, 
  Code, 
  FileText, 
  AlertTriangle
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
}

const SystemIntelligence: React.FC<SystemIntelligenceProps> = ({ selectedModel }) => {
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchSystemStats = async () => {
    try {
      // Fetch from backend API (same container, relative path)
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
    // Poll for updates every 5 seconds
    const interval = setInterval(fetchSystemStats, 5000);
    return () => clearInterval(interval);
  }, []);

  if (error) {
    return (
      <div className="bg-red-900/20 border border-red-800 rounded-lg p-6 text-red-400">
        <div className="flex items-center space-x-2 mb-2">
          <AlertTriangle className="w-5 h-5" />
          <span className="font-semibold">Connection Error</span>
        </div>
        <p>{error}</p>
        <p className="text-sm text-red-500 mt-2">Please ensure the backend is running on port 8000</p>
      </div>
    );
  }

  if (!stats) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500 mx-auto"></div>
          <p className="mt-4 text-slate-400">Loading system intelligence...</p>
        </div>
      </div>
    );
  }

  // Calculate autonomy percentage
  const autonomyPercentage = stats.total_decisions > 0 
    ? Math.round((stats.local_decisions / stats.total_decisions) * 100)
    : 0;

  // Prepare chart data
  const categoryData = Object.entries(stats.classifier.category_distribution).map(([name, value]) => ({
    name: name,
    value: value,
    color: name === 'System' ? '#3b82f6' : name === 'Tracker' ? '#f59e0b' : '#ef4444'
  }));

  const confidenceData = Object.entries(stats.classifier.confidence_distribution).map(([name, value]) => ({
    name: name.charAt(0) + name.slice(1).toLowerCase(),
    value: value,
    color: name === 'high' ? '#10b981' : name === 'medium' ? '#f59e0b' : '#ef4444'
  }));

  const decisionData = [
    { name: 'Local', value: stats.local_decisions, color: '#8b5cf6' },
    { name: 'Cloud', value: stats.cloud_decisions, color: '#10b981' }
  ];

  return (
    <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-white">System Intelligence</h1>
            <p className="text-sm text-slate-400">Live system analytics and performance metrics</p>
          </div>
          <div className="flex items-center space-x-6 text-sm text-slate-400">
            <div className="text-right">
              <div className="text-xs text-slate-500">Autonomy Score</div>
              <div className="text-2xl font-bold text-purple-400">{autonomyPercentage}%</div>
            </div>
            <div className="text-right">
              <div className="text-xs text-slate-500">Total Patterns</div>
              <div className="text-2xl font-bold text-cyan-400">{stats.classifier.total_patterns}</div>
            </div>
            <div className="text-right">
              <div className="text-xs text-slate-500">Active Decisions</div>
              <div className="text-2xl font-bold text-green-400">{stats.total_decisions}</div>
            </div>
          </div>
        </div>

      {/* Interactive Analytics Dashboard */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Decision Distribution Pie Chart */}
        <div className="bg-slate-800 p-6 rounded-lg border border-slate-700">
          <h4 className="text-lg font-bold text-white mb-4 font-mono flex items-center">
            <Brain className="w-5 h-5 text-purple-400 mr-2" />
            Decision Distribution
          </h4>
          <div className="h-64 flex items-center justify-center">
            <svg width="200" height="200" className="relative">
              {/* Local Decisions Slice */}
              <path
                d={`M 100 100 L 100 0 A 100 100 0 ${autonomyPercentage > 50 ? 1 : 0} 1 ${100 + 100 * Math.cos((autonomyPercentage * Math.PI) / 180)} ${100 - 100 * Math.sin((autonomyPercentage * Math.PI) / 180)} Z`}
                fill="#8b5cf6"
                opacity="0.8"
              />
              {/* Cloud Decisions Slice */}
              <path
                d={`M 100 100 L ${100 + 100 * Math.cos((autonomyPercentage * Math.PI) / 180)} ${100 - 100 * Math.sin((autonomyPercentage * Math.PI) / 180)} A 100 100 0 ${autonomyPercentage < 50 ? 1 : 0} 0 100 0 Z`}
                fill="#10b981"
                opacity="0.8"
              />
              {/* Center Circle */}
              <circle cx="100" cy="100" r="40" fill="#1f2937" stroke="#374151" strokeWidth="2"/>
              <text x="100" y="95" textAnchor="middle" className="text-white text-lg font-bold">{autonomyPercentage}%</text>
              <text x="100" y="115" textAnchor="middle" className="text-slate-400 text-xs">Local</text>
            </svg>
          </div>
          <div className="mt-4 grid grid-cols-2 gap-4 text-sm">
            <div className="flex items-center space-x-2">
              <div className="w-3 h-3 bg-purple-500 rounded-full"></div>
              <span className="text-slate-300">Local Decisions</span>
              <span className="ml-auto font-bold text-white">{stats.local_decisions}</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-3 h-3 bg-green-500 rounded-full"></div>
              <span className="text-slate-300">Cloud Decisions</span>
              <span className="ml-auto font-bold text-white">{stats.cloud_decisions}</span>
            </div>
          </div>
        </div>

        {/* Pattern Analysis Bar Chart */}
        <div className="bg-slate-800 p-6 rounded-lg border border-slate-700">
          <h4 className="text-lg font-bold text-white mb-4 font-mono flex items-center">
            <Zap className="w-5 h-5 text-yellow-400 mr-2" />
            Pattern Analysis
          </h4>
          <div className="space-y-6">
            {categoryData.map((item, index) => (
              <div key={index} className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-slate-300 capitalize font-mono">{item.name}</span>
                  <span className="font-bold text-white font-mono">{item.value}</span>
                </div>
                <div className="w-full bg-slate-700 rounded-full h-4">
                  <div 
                    className="h-4 rounded-full transition-all duration-1000"
                    style={{ 
                      width: `${(item.value / stats.classifier.total_patterns) * 100}%`,
                      backgroundColor: item.color
                    }}
                  ></div>
                </div>
              </div>
            ))}
            <div className="pt-4 border-t border-slate-700">
              <div className="flex justify-between text-sm font-mono">
                <span className="text-slate-400">Total Patterns</span>
                <span className="text-cyan-400 font-bold">{stats.classifier.total_patterns}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Performance Metrics Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Cache Performance */}
        <div className="bg-slate-800 p-6 rounded-lg border border-slate-700">
          <h4 className="text-lg font-bold text-white mb-4 font-mono flex items-center">
            <Database className="w-5 h-5 text-cyan-400 mr-2" />
            Cache Performance
          </h4>
          <div className="space-y-4">
            <div>
              <div className="flex justify-between text-sm mb-2">
                <span className="text-slate-300">Valid Memory Entries</span>
                <span className="font-bold text-cyan-400">{stats.cache.valid_memory_entries}</span>
              </div>
              <div className="w-full bg-slate-700 rounded-full h-3">
                <div 
                  className="h-3 bg-cyan-500 rounded-full transition-all duration-1000"
                  style={{ width: `${Math.min(stats.cache.valid_memory_entries * 20, 100)}%` }}
                ></div>
              </div>
            </div>
            <div>
              <div className="flex justify-between text-sm mb-2">
                <span className="text-slate-300">Memory Cache Size</span>
                <span className="font-bold text-purple-400">{stats.cache.memory_cache_size}</span>
              </div>
              <div className="w-full bg-slate-700 rounded-full h-3">
                <div 
                  className="h-3 bg-purple-500 rounded-full transition-all duration-1000"
                  style={{ width: `${Math.min(stats.cache.memory_cache_size * 10, 100)}%` }}
                ></div>
              </div>
            </div>
            <div className="mt-4 p-3 bg-slate-900/50 rounded border border-slate-600">
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-400">Disk Cache</span>
                <span className={`text-xs font-mono px-2 py-1 rounded border ${
                  stats.cache.disk_cache_exists 
                    ? 'bg-green-900/50 text-green-400 border-green-500/30' 
                    : 'bg-red-900/50 text-red-400 border-red-500/30'
                }`}>
                  {stats.cache.disk_cache_exists ? 'ENABLED' : 'DISABLED'}
                </span>
              </div>
              <div className="text-xs text-slate-500 mt-1">File size: {(stats.cache.cache_file_size / 1024).toFixed(2)} KB</div>
            </div>
          </div>
        </div>

        {/* Confidence Distribution */}
        <div className="bg-slate-800 p-6 rounded-lg border border-slate-700">
          <h4 className="text-lg font-bold text-white mb-4 font-mono flex items-center">
            <Target className="w-5 h-5 text-green-400 mr-2" />
            Confidence Distribution
          </h4>
          <div className="space-y-4">
            {confidenceData.map((item, index) => (
              <div key={index} className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-slate-300 capitalize">{item.name} Confidence</span>
                  <span className="font-bold text-white">{item.value}</span>
                </div>
                <div className="w-full bg-slate-700 rounded-full h-2">
                  <div 
                    className="h-2 rounded-full transition-all duration-1000"
                    style={{ 
                      width: `${(item.value / (stats.classifier.total_patterns || 1)) * 100}%`,
                      backgroundColor: item.color
                    }}
                  ></div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Learning Progress */}
        <div className="bg-slate-800 p-6 rounded-lg border border-slate-700">
          <h4 className="text-lg font-bold text-white mb-4 font-mono flex items-center">
            <Activity className="w-5 h-5 text-yellow-400 mr-2" />
            Learning Progress
          </h4>
          <div className="space-y-6">
            {/* Patterns Learned */}
            <div>
              <div className="flex justify-between text-sm mb-2">
                <span className="text-slate-300">Patterns Learned</span>
                <span className="font-bold text-yellow-400">{stats.patterns_learned}/5</span>
              </div>
              <div className="w-full bg-slate-700 rounded-full h-3">
                <div 
                  className="h-3 bg-yellow-500 rounded-full transition-all duration-1000"
                  style={{ width: `${(stats.patterns_learned / 5) * 100}%` }}
                ></div>
              </div>
            </div>

            {/* Seed vs Learned */}
            <div className="grid grid-cols-2 gap-4">
              <div className="text-center p-3 bg-slate-900/50 rounded border border-slate-600">
                <div className="text-2xl font-bold text-blue-400">{stats.seed_patterns}</div>
                <div className="text-xs text-slate-400">Seed Patterns</div>
              </div>
              <div className="text-center p-3 bg-slate-900/50 rounded border border-slate-600">
                <div className="text-2xl font-bold text-purple-400">{stats.learned_patterns}</div>
                <div className="text-xs text-slate-400">Learned Patterns</div>
              </div>
            </div>

            {/* System Status */}
            <div className="p-4 bg-gradient-to-r from-green-900/50 to-blue-900/50 rounded border border-green-500/30">
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-300">System Status</span>
                <div className="flex space-x-2">
                  <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
                  <span className="text-xs font-mono bg-green-900/50 text-green-400 px-2 py-1 rounded border border-green-500/30">
                    OPERATIONAL
                  </span>
                </div>
              </div>
              <div className="text-xs text-slate-400 mt-1">All systems active and learning</div>
            </div>
          </div>
        </div>
      </div>

      {/* System Overview */}
      <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
        <h3 className="text-lg font-semibold text-white mb-4 flex items-center space-x-2">
          <Network className="w-5 h-5 text-blue-400" />
          <span>System Overview</span>
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-slate-700 p-4 rounded-lg">
            <div className="flex items-center space-x-2 mb-2">
              <Wifi className="w-4 h-4 text-orange-400" />
              <span className="text-sm text-slate-300">AdGuard Integration</span>
            </div>
            <div className="text-2xl font-bold text-orange-400">ACTIVE</div>
            <div className="text-xs text-slate-500">DNS filtering integrated</div>
          </div>
          <div className="bg-slate-700 p-4 rounded-lg">
            <div className="flex items-center space-x-2 mb-2">
              <Brain className="w-4 h-4 text-purple-400" />
              <span className="text-sm text-slate-300">Gemini AI Analysis</span>
            </div>
            <div className="text-2xl font-bold text-purple-400">ACTIVE</div>
            <div className="text-xs text-slate-500">Threat analysis running</div>
          </div>
          <div className="bg-slate-700 p-4 rounded-lg">
            <div className="flex items-center space-x-2 mb-2">
              <Cpu className="w-4 h-4 text-green-400" />
              <span className="text-sm text-slate-300">Local ML Detection</span>
            </div>
            <div className="text-2xl font-bold text-green-400">ACTIVE</div>
            <div className="text-xs text-slate-500">Pattern detection online</div>
          </div>
          <div className="bg-slate-700 p-4 rounded-lg">
            <div className="flex items-center space-x-2 mb-2">
              <Shield className="w-4 h-4 text-red-400" />
              <span className="text-sm text-slate-300">Threat Protection</span>
            </div>
            <div className="text-2xl font-bold text-red-400">{stats.classifier.total_patterns}</div>
            <div className="text-xs text-slate-500">Active protections</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SystemIntelligence;