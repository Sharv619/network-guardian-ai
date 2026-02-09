import React, { useState, useEffect } from 'react';
import LoadingSpinner from './LoadingSpinner';
import CodeBlock from './CodeBlock';
import { ThreatReport } from '../types';
import ChatPanel from './ChatPanel';
import AnalysisModal from './AnalysisModal';
import { Eye as EyeIcon } from 'lucide-react';

// --- Interfaces ---
interface HistoryItem {
    domain: string;
    risk_score: string;
    category: string;
    summary: string;
    timestamp: string;
    is_anomaly?: boolean;
    anomaly_score?: number;
    adguard_metadata?: {
        reason: string;
        rule?: string;
        filter_id?: number;
        client?: string;
    };
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

const API_BASE = ""; // Relative path since Backend serves Frontend

interface DashboardProps {
    selectedModel: string;
}

const Dashboard: React.FC<DashboardProps> = ({ selectedModel }) => {
    const [activeTab, setActiveTab] = useState<'live' | 'manual' | 'chat' | 'intelligence'>('live');

    return (
        <div className="h-full flex flex-col space-y-6">
            <div className="flex space-x-4 border-b border-slate-700 pb-2 overflow-x-auto whitespace-nowrap">
                <button
                    onClick={() => setActiveTab('live')}
                    className={`pb-2 px-4 font-mono font-bold transition-colors ${activeTab === 'live'
                        ? 'text-cyan-400 border-b-2 border-cyan-400'
                        : 'text-slate-500 hover:text-slate-300'
                        }`}
                >
                    LIVE FEED
                </button>
                <button
                    onClick={() => setActiveTab('manual')}
                    className={`pb-2 px-4 font-mono font-bold transition-colors ${activeTab === 'manual'
                        ? 'text-cyan-400 border-b-2 border-cyan-400'
                        : 'text-slate-500 hover:text-slate-300'
                        }`}
                >
                    MANUAL ANALYSIS
                </button>
                <button
                    onClick={() => setActiveTab('chat')}
                    className={`pb-2 px-4 font-mono font-bold transition-colors ${activeTab === 'chat'
                        ? 'text-cyan-400 border-b-2 border-cyan-400'
                        : 'text-slate-500 hover:text-slate-300'
                        }`}
                >
                    SYSTEM CHAT
                </button>
                <button
                    onClick={() => setActiveTab('intelligence')}
                    className={`pb-2 px-4 font-mono font-bold transition-colors ${activeTab === 'intelligence'
                        ? 'text-cyan-400 border-b-2 border-cyan-400'
                        : 'text-slate-500 hover:text-slate-300'
                        }`}
                >
                    SYSTEM INTELLIGENCE 🟢 (Live)
                </button>
            </div>

            <div className="flex-grow overflow-hidden">
                {activeTab === 'live' && <LiveFeed />}
                {activeTab === 'manual' && <ManualAnalysis selectedModel={selectedModel} />}
                {activeTab === 'chat' && <ChatPanel selectedModel={selectedModel} />}
                {activeTab === 'intelligence' && <SystemIntelligence />}
            </div>
        </div>
    );
};

import { 
  LocateFixed, 
  ShieldAlert, 
  ShieldCheck, 
  Brain,
  BarChart3,
  PieChart,
  TrendingUp,
  Activity,
  Database,
  Globe,
  Wifi,
  Cpu,
  AlertTriangle,
  Shield,
  Network,
  Zap,
  Target,
  Lock,
  FileText,
  Code,
  CheckCircle2
} from 'lucide-react';

const LiveFeed: React.FC = () => {
    const [history, setHistory] = useState<HistoryItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedDomain, setSelectedDomain] = useState<string | null>(null);
    const [domainStats, setDomainStats] = useState<any>(null);
    const [isModalOpen, setIsModalOpen] = useState(false);

    const isPrivacyRisk = (domain: string) => {
        const keywords = ['geo', 'location', 'gps', 'telemetry', 'waa-pa'];
        return keywords.some(k => domain.toLowerCase().includes(k));
    };

    const fetchHistory = async () => {
        try {
            // Direct backend call as requested in Chaos Mode
            const res = await fetch(`${API_BASE}/history`);
            if (res.ok) {
                const data = await res.json();
                console.log("Backend Data Received:", data);
                setHistory(data);
            }
        } catch (e) {
            console.error("Failed to fetch history", e);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchHistory();
        const interval = setInterval(fetchHistory, 30000); // Poll every 30s to respect Google Sheets Quota
        return () => clearInterval(interval);
    }, []);

    if (loading && history.length === 0) return <LoadingSpinner />;

    // Handle domain click to show detailed analysis
    const handleDomainClick = async (domain: string) => {
        setSelectedDomain(domain);
        setIsModalOpen(true);
        
        try {
            // Fetch system stats for the domain
            const res = await fetch(`${API_BASE}/api/stats/system`);
            if (res.ok) {
                const data = await res.json();
                setDomainStats(data);
            }
        } catch (e) {
            console.error("Failed to fetch domain stats", e);
            setDomainStats(null);
        }
    };

    return (
        <div className="space-y-3 h-full overflow-y-auto pr-2 custom-scrollbar">
            {history.map((item, idx) => {
                const geoRisk = isPrivacyRisk(item.domain);
                const displayTime = item.timestamp && !isNaN(Date.parse(item.timestamp))
                    ? new Date(item.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})
                    : "Just Now";

                const isBlocked = item.adguard_metadata && item.adguard_metadata.reason !== 'NotFilteredNotFound';

                return (
                    <div key={idx} className={`bg-slate-800 p-4 rounded border-l-4 ${item.is_anomaly ? 'border-yellow-500 shadow-[0_0_15px_rgba(234,179,8,0.2)] animate-[pulse_3s_infinite]' : geoRisk ? 'border-red-500 bg-red-900/10' : isBlocked ? 'border-orange-500 bg-orange-950/5' : 'border-slate-600'} hover:border-cyan-500 transition-all shadow-md relative overflow-hidden group`}>
                        <div className="flex justify-between items-start mb-2">
                            <div className="flex items-center space-x-2">
                                <h3 
                                    className="text-lg font-bold text-slate-100 font-mono break-all cursor-pointer hover:text-cyan-400 transition-colors"
                                    onClick={() => handleDomainClick(item.domain)}
                                    title="Click to view detailed backend analysis"
                                >
                                    {item.domain}
                                </h3>
                                <button
                                    onClick={() => handleDomainClick(item.domain)}
                                    className="p-1 hover:bg-slate-700 rounded transition-colors opacity-0 group-hover:opacity-100"
                                    title="View detailed analysis"
                                >
                                    <EyeIcon className="w-4 h-4 text-cyan-400" />
                                </button>
                                {geoRisk && (
                                    <LocateFixed className="w-5 h-5 text-red-500 animate-pulse" />
                                )}
                                {isBlocked && (
                                    <span className="flex items-center space-x-1 px-2 py-0.5 bg-slate-700 text-cyan-400 border border-cyan-500/30 rounded text-[10px] font-mono uppercase tracking-wider">
                                        <ShieldAlert className="w-3 h-3" />
                                        <span>ADGUARD BLOCKED: {item.adguard_metadata?.rule || item.adguard_metadata?.reason}</span>
                                    </span>
                                )}
                                {item.is_anomaly && (
                                    <span className="flex items-center space-x-1 px-2 py-0.5 bg-yellow-900/50 text-yellow-400 border border-yellow-500/30 rounded text-[10px] font-mono uppercase tracking-wider animate-pulse" title="Unusual network behavior detected by local ML model.">
                                        ANOMALY
                                    </span>
                                )}
                            </div>
                            <span className="text-xs text-slate-500 font-mono">{displayTime}</span>
                        </div>

                        <div className="flex flex-wrap items-center gap-2 text-sm mb-3">
                            <RiskBadge score={item.risk_score} />
                            <span className="px-2 py-0.5 bg-slate-700 text-slate-300 rounded text-xs font-mono uppercase tracking-wide">
                                {item.category}
                            </span>
                            {geoRisk && (
                                <span className="px-2 py-0.5 bg-red-600 text-white rounded text-xs font-bold font-mono animate-pulse">
                                    GEOLOCATION ATTEMPT
                                </span>
                            )}
                            {item.summary.includes("SOC GUARD ACTIVE") && (
                                <span className="px-2 py-0.5 bg-purple-900 text-purple-200 border border-purple-700 rounded text-xs font-mono uppercase tracking-wide">
                                    Heuristic Mode
                                </span>
                            )}
                        </div>

                        {item.adguard_metadata && item.adguard_metadata.reason !== 'NotFilteredNotFound' && (
                            <div className="mb-3 p-2 bg-slate-900/50 rounded border border-slate-700/50">
                                <p className="text-[10px] uppercase font-mono text-slate-500 mb-1">AdGuard Intelligence</p>
                                <div className="flex flex-col space-y-1">
                                    <div className="flex justify-between text-xs">
                                        <span className="text-slate-400">Reason:</span>
                                        <span className="text-orange-400 font-mono">{item.adguard_metadata.reason}</span>
                                    </div>
                                    {item.adguard_metadata.rule && (
                                        <div className="flex flex-col text-xs">
                                            <span className="text-slate-400">Rule:</span>
                                            <code className="text-[10px] text-cyan-500 bg-slate-900 p-1 rounded mt-1 overflow-x-auto">{item.adguard_metadata.rule}</code>
                                        </div>
                                    )}
                                </div>
                            </div>
                        )}

                        <p className="text-slate-400 text-sm leading-relaxed font-sans border-t border-slate-700 pt-2">
                            {item.summary}
                        </p>

                        {item.is_anomaly && (
                            <div className="mt-2 text-[10px] font-mono text-yellow-500/70 italic">
                                Verified by Local Behavioral Engine (Score: {item.anomaly_score?.toFixed(4)})
                            </div>
                        )}

                        {/* Google Sheets Icon */}
                        <div className="absolute bottom-2 right-2 opacity-20 group-hover:opacity-100 transition-opacity" title="Synced to Google Sheets">
                            <svg className="w-4 h-4 text-green-500" fill="currentColor" viewBox="0 0 24 24" aria-label="Google Sheets">
                                <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zM9 17H7v-2h2v2zm0-4H7v-2h2v2zm0-4H7V7h2v2zm4 8h-2v-2h2v2zm0-4h-2v-2h2v2zm0-4h-2V7h2v2zm4 8h-2v-2h2v2zm0-4h-2v-2h2v2zm0-4h-2V7h2v2z" />
                            </svg>
                        </div>
                    </div>
                );
            })}
            {history.length === 0 && (
                <div className="text-center text-slate-500 py-10 font-mono">
                    No threats detected... yet.
                </div>
            )}

            {/* Analysis Modal */}
            <AnalysisModal
                isOpen={isModalOpen}
                onClose={() => setIsModalOpen(false)}
                domain={selectedDomain || ''}
                stats={domainStats || {
                    autonomy_score: 0,
                    local_decisions: 0,
                    cloud_decisions: 0,
                    classifier: { total_patterns: 0 },
                    cache: {
                        memory_cache_size: 0,
                        valid_memory_entries: 0,
                        disk_cache_exists: false,
                        cache_file_size: 0
                    },
                    system_usage: {
                        active_integrations: [],
                        tracker_detection: { total_detected: 0, categories: {}, detection_methods: [] },
                        learning_progress: { seed_patterns: 0, learned_patterns: 0, learning_rate: '', next_milestone: '' }
                    }
                }}
            />
        </div>
    );
};

import { analyzeDomain } from '../services/geminiService';

interface ManualAnalysisProps {
    selectedModel: string;
}

const ManualAnalysis: React.FC<ManualAnalysisProps> = ({ selectedModel }) => {
    const [domain, setDomain] = useState('');
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<any>(null);
    const [sessionHistory, setSessionHistory] = useState<HistoryItem[]>([]);

    const fetchSessionHistory = async () => {
        try {
            const res = await fetch(`${API_BASE}/manual-history`);
            if (res.ok) {
                const data = await res.json();
                setSessionHistory(data);
            }
        } catch (e) {
            console.error("Failed to fetch manual history", e);
        }
    };

    useEffect(() => {
        fetchSessionHistory();
    }, []);

    const handleAnalyze = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!domain) return;

        setLoading(true);
        setResult(null);
        try {
            // SRE Pattern: BFF (Backend-for-Frontend) Proxy with Dynamic Model Selection
            const data = await analyzeDomain(domain, null, selectedModel);

            // Map back to UI format
            setResult({
                domain,
                risk_score: data.risk_score >= 8 ? 'High' : data.risk_score >= 4 ? 'Medium' : 'Low',
                category: data.category,
                summary: data.explanation
            });
            fetchSessionHistory();
        } catch (error) {
            console.error(error);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="flex flex-col h-full overflow-y-auto pr-2 custom-scrollbar">
            <form onSubmit={handleAnalyze} className="bg-slate-800 p-5 rounded-lg border border-slate-700 mb-6 shadow-lg">
                <label className="block text-xs font-mono text-cyan-500 mb-2 uppercase tracking-widest">Target Domain</label>
                <div className="flex gap-3">
                    <input
                        type="text"
                        value={domain}
                        onChange={(e) => setDomain(e.target.value)}
                        placeholder="e.g., suspicious-site.com"
                        className="flex-grow bg-slate-900 border border-slate-600 rounded p-3 text-slate-100 focus:outline-none focus:border-cyan-500 font-mono transition-colors"
                    />
                    <button
                        type="submit"
                        disabled={loading}
                        className="bg-cyan-600 hover:bg-cyan-500 text-white font-bold py-2 px-6 rounded transition-colors disabled:opacity-50 uppercase font-mono tracking-wide"
                    >
                        {loading ? 'Scanning...' : 'Scan'}
                    </button>
                </div>
            </form>

            {result && (
                <div className="bg-slate-800 rounded-lg p-6 border border-slate-700 shadow-xl animate-fade-in mb-8">
                    <div className="flex items-center justify-between mb-6">
                        <h3 className="text-xl font-bold text-white font-mono">Scan Results</h3>
                        <RiskBadge score={result.risk_score} />
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                        <div>
                            <p className="text-xs text-slate-500 uppercase font-mono mb-1">Category</p>
                            <p className="text-lg text-slate-200">{result.category}</p>
                        </div>
                        <div>
                            <p className="text-xs text-slate-500 uppercase font-mono mb-1">Verdict</p>
                            <p className="text-lg text-slate-200">{result.summary}</p>
                        </div>
                    </div>

                    <CodeBlock code={JSON.stringify(result, null, 2)} />
                </div>
            )}

            {/* Session Research Section */}
            <div className="mt-4">
                <h3 className="text-slate-400 font-mono text-sm uppercase mb-4 border-b border-slate-700 pb-2">Session Research</h3>
                <div className="space-y-3">
                    {sessionHistory.map((item, idx) => {
                        const displayTime = item.timestamp && !isNaN(Date.parse(item.timestamp))
                            ? new Date(item.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})
                            : "Just Now";
                        return (
                            <div key={idx} className="bg-slate-800/50 p-3 rounded border-l-2 border-slate-600 flex justify-between items-center hover:bg-slate-800 transition-colors">
                                <div>
                                    <div className="font-mono text-slate-200 font-bold">{item.domain}</div>
                                    <div className="text-xs text-slate-500">{item.category} • {item.risk_score} Risk</div>
                                </div>
                                <div className="text-xs text-slate-600 font-mono">
                                    {displayTime}
                                </div>
                            </div>
                        );
                    })}
                    {sessionHistory.length === 0 && (
                        <div className="text-slate-500 text-xs font-mono italic">No manual scans this session.</div>
                    )}
                </div>
            </div>
        </div>
    );
};

const RiskBadge: React.FC<{ score: string }> = ({ score }) => {
    let color = 'bg-slate-600 text-slate-200';

    // Normalize score cases
    const s = score.toLowerCase();

    if (s === 'high') color = 'bg-red-500 text-white shadow-red-glow animate-pulse';
    else if (s === 'medium') color = 'bg-orange-500 text-white';
    else if (s === 'low') color = 'bg-green-500 text-white';

    return (
        <span className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${color}`}>
            {score} Risk
        </span>
    );
};

// Chart components
const CacheBarChart: React.FC<{ cacheStats: any }> = ({ cacheStats }) => {
  const data = [
    { label: 'Cache Hits', value: cacheStats?.hit_rate || 85, color: 'bg-green-500' },
    { label: 'Cache Misses', value: cacheStats?.miss_rate || 15, color: 'bg-red-500' }
  ];

  return (
    <div className="space-y-4">
      {data.map((item, index) => (
        <div key={index} className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-slate-300">{item.label}</span>
            <span className="font-bold text-white">{item.value}%</span>
          </div>
          <div className="w-full bg-slate-700 rounded-full h-2">
            <div 
              className={`${item.color}`} 
              style={{ width: `${item.value}%` }}
            ></div>
          </div>
        </div>
      ))}
    </div>
  );
};

const SourceDistributionPieChart: React.FC<{ sourceDistribution: any }> = ({ sourceDistribution }) => {
  const data = [
    { label: 'Gemini', value: sourceDistribution?.gemini || 45, color: '#a855f7' }, // purple
    { label: 'Local ML', value: sourceDistribution?.local_ml || 30, color: '#22c55e' }, // green
    { label: 'AdGuard', value: sourceDistribution?.adguard || 25, color: '#f59e0b' } // orange
  ];

  // Calculate cumulative angles for pie slices
  const total = data.reduce((sum, item) => sum + item.value, 0);
  let cumulativeAngle = 0;

  return (
    <div className="space-y-4">
      {/* Pie Chart Visualization */}
      <div className="relative">
        <div className="w-32 h-32 mx-auto relative">
          {data.map((item, index) => {
            const sliceAngle = (item.value / total) * 360;
            const transform = `rotate(${cumulativeAngle}deg)`;
            const currentCumulative = cumulativeAngle;
            cumulativeAngle += sliceAngle;
            
            return (
              <div
                key={index}
                className="absolute inset-0"
                style={{
                  clipPath: `polygon(50% 50%, 50% 0%, ${50 + 50 * Math.cos((sliceAngle * Math.PI) / 180)}% ${50 - 50 * Math.sin((sliceAngle * Math.PI) / 180)}%)`,
                }}
              >
                <div
                  className="absolute inset-0 border-l-8 border-t-8"
                  style={{
                    borderColor: `${item.color} transparent transparent ${item.color}`,
                    transform,
                    borderRadius: '50%',
                  }}
                />
              </div>
            );
          })}
          {/* Center circle */}
          <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-16 h-16 bg-slate-800 rounded-full border-2 border-slate-700 flex items-center justify-center">
            <span className="text-xs font-mono text-slate-400">Total</span>
          </div>
        </div>
      </div>

      {/* Legend */}
      <div className="space-y-2">
        {data.map((item, index) => (
          <div key={index} className="flex items-center justify-between text-sm">
            <div className="flex items-center space-x-2">
              <div 
                className="w-3 h-3 rounded-full" 
                style={{ backgroundColor: item.color }}
              />
              <span className="text-slate-300">{item.label}</span>
            </div>
            <span className="font-bold text-white">{item.value}%</span>
          </div>
        ))}
      </div>
      <div className="text-xs text-slate-400 text-center">Data source distribution</div>
    </div>
  );
};

const PatternLearningChart: React.FC<{ classifierStats: any }> = ({ classifierStats }) => {
  const data = [
    { label: 'Patterns Learned', value: classifierStats?.patterns_learned || 1234, color: 'bg-gradient-to-r from-blue-500 to-cyan-500', max: 2000 },
    { label: 'Accuracy', value: classifierStats?.accuracy || 92.5, color: 'bg-gradient-to-r from-green-500 to-emerald-500', max: 100 },
    { label: 'False Positives', value: classifierStats?.false_positives || 3.2, color: 'bg-gradient-to-r from-red-500 to-orange-500', max: 10 }
  ];

  return (
    <div className="space-y-6">
      {data.map((item, index) => {
        const percentage = item.value > item.max ? 100 : (item.value / item.max) * 100;
        return (
          <div key={index} className="space-y-3">
            <div className="flex items-center justify-between text-sm">
              <span className="text-slate-300 font-mono">{item.label}</span>
              <span className="font-bold text-white font-mono">{item.value}</span>
            </div>
            <div className="w-full bg-slate-700 rounded-full h-3 border border-slate-600/50">
              <div 
                className={`${item.color} h-3 rounded-full transition-all duration-1000 ease-out shadow-lg`}
                style={{ width: `${percentage}%` }}
              ></div>
            </div>
            <div className="flex justify-between text-xs text-slate-500 font-mono">
              <span>0</span>
              <span>{item.max}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
};

// --- NEW COMPONENT: System Intelligence ---
const SystemIntelligence: React.FC = () => {
    const [stats, setStats] = useState<SystemStats | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const fetchStats = async () => {
        try {
            const res = await fetch(`${API_BASE}/api/stats/system`);
            if (res.ok) {
                const data = await res.json();
                console.log("System Intelligence Data Received:", data);
                console.log("🟢 TRACER BULLET: Successfully connected to backend /api/stats/system");
                setStats(data);
                setError(null);
            } else {
                throw new Error(`HTTP ${res.status}: ${res.statusText}`);
            }
        } catch (e) {
            console.error("Failed to fetch system stats", e);
            setError("Failed to connect to backend system intelligence");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchStats();
        const interval = setInterval(fetchStats, 5000); // Update every 5s
        return () => clearInterval(interval);
    }, []);

    if (loading && !stats) return <LoadingSpinner />;
    if (error) return <div className="text-red-500 font-mono p-10">{error}</div>;
    if (!stats) return <div className="text-slate-500 font-mono p-10">Waiting for backend telemetry...</div>;

    return (
        <div className="space-y-6 h-full overflow-y-auto pr-2 custom-scrollbar pb-10">
            {/* Top Row: Key Metrics */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <StatCard 
                    label="Autonomy Score" 
                    value={`${stats.autonomy_score}%`} 
                    icon={<Brain className="text-purple-400" />} 
                    subtext="Local Decision Rate"
                />
                <StatCard 
                    label="Learned Patterns" 
                    value={stats.patterns_learned} 
                    icon={<Zap className="text-yellow-400" />} 
                    subtext={`${stats.seed_patterns} Seed + ${stats.learned_patterns} New`}
                />
                <StatCard 
                    label="Total Decisions" 
                    value={stats.total_decisions} 
                    icon={<ShieldCheck className="text-green-400" />} 
                    subtext="Local + Cloud Analysis"
                />
                <StatCard 
                    label="Cache Efficiency" 
                    value={`${stats.cache.valid_memory_entries}`} 
                    icon={<Database className="text-cyan-400" />} 
                    subtext="Active Memory Entries"
                />
            </div>

            {/* Middle Section: Optimization & Benefits */}
            <div className="bg-slate-800/50 border border-cyan-500/20 rounded-lg p-6">
                <div className="flex items-start space-x-4">
                    <div className="bg-cyan-500/20 p-3 rounded-lg">
                        <TrendingUp className="text-cyan-400 w-6 h-6" />
                    </div>
                    <div className="flex-grow">
                        <h3 className="text-xl font-bold text-white mb-2 font-mono">Smart Routing Optimization</h3>
                        <p className="text-slate-400 mb-4">{stats.optimization.description}</p>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                            {stats.optimization.benefits.map((benefit, i) => (
                                <div key={i} className="flex items-center space-x-2 text-sm text-slate-300 bg-slate-900/50 p-2 rounded">
                                    <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                                    <span>{benefit}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>

            {/* Bottom Section: Classifier & Cache Breakdown */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="bg-slate-800 p-5 rounded-lg border border-slate-700">
                    <h4 className="text-sm font-mono text-slate-400 uppercase mb-4 flex items-center">
                        <Target className="w-4 h-4 mr-2" /> Classifier Distribution
                    </h4>
                    <div className="space-y-4">
                        {Object.entries(stats.classifier.category_distribution).map(([cat, count]) => (
                            <div key={cat} className="space-y-1">
                                <div className="flex justify-between text-xs font-mono text-slate-300">
                                    <span>{cat}</span>
                                    <span>{count} patterns</span>
                                </div>
                                <div className="w-full bg-slate-900 h-2 rounded-full overflow-hidden">
                                    <div 
                                        className="bg-cyan-500 h-full" 
                                        style={{ width: `${(count / stats.classifier.total_patterns) * 100}%` }}
                                    />
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                <div className="bg-slate-800 p-5 rounded-lg border border-slate-700">
                    <h4 className="text-sm font-mono text-slate-400 uppercase mb-4 flex items-center">
                        <Database className="w-4 h-4 mr-2" /> Cache Intelligence
                    </h4>
                    <div className="grid grid-cols-2 gap-4">
                        <div className="p-3 bg-slate-900 rounded border border-slate-700/50">
                            <span className="text-[10px] text-slate-500 block">MEMORY SIZE</span>
                            <span className="text-cyan-400 font-bold font-mono">{stats.cache.memory_cache_size}</span>
                        </div>
                        <div className="p-3 bg-slate-900 rounded border border-slate-700/50">
                            <span className="text-[10px] text-slate-500 block">FILE SIZE</span>
                            <span className="text-cyan-400 font-mono font-bold">
                                {(stats.cache.cache_file_size / 1024).toFixed(2)} KB
                            </span>
                        </div>
                    </div>
                    <div className="mt-4">
                         <span className="text-[10px] text-slate-500 block mb-2 uppercase">Decision Sources</span>
                         <div className="flex items-center h-4 w-full bg-slate-900 rounded-full overflow-hidden">
                            <div className="bg-emerald-500 h-full" style={{width: '60%'}} title="Local" />
                            <div className="bg-purple-500 h-full" style={{width: '30%'}} title="Cloud" />
                            <div className="bg-slate-700 h-full" style={{width: '10%'}} title="Cached" />
                         </div>
                         <div className="flex justify-between mt-2 text-[10px] font-mono text-slate-500 uppercase">
                            <span>Local: {stats.local_decisions}</span>
                            <span>Cloud: {stats.cloud_decisions}</span>
                         </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

// Helper Stat Card
const StatCard: React.FC<{ label: string, value: any, icon: any, subtext: string }> = ({ label, value, icon, subtext }) => (
    <div className="bg-slate-800 p-4 rounded-lg border border-slate-700 hover:border-cyan-500 transition-colors">
        <div className="flex justify-between items-start mb-2">
            <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider">{label}</span>
            {icon}
        </div>
        <div className="text-2xl font-bold text-white font-mono">{value}</div>
        <div className="text-[10px] text-slate-400 mt-1 font-mono">{subtext}</div>
    </div>
);


export default Dashboard;