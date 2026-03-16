import React, { useState, useEffect } from 'react';

import { 
  LocateFixed, 
  ShieldAlert, 
  Eye as EyeIcon,
  Wifi,
  WifiOff,
  Target,
  Activity
} from 'lucide-react';

import LoadingSpinner from './LoadingSpinner';
import CodeBlock from './CodeBlock';
import ChatPanel from './SystemAwarenessChat';
import AnalysisModal from './AnalysisModal';
import StatsPanel from './StatsPanel';
import SystemIntelligence from './SystemIntelligence';
import SkeletonLoader from './SkeletonLoader';
import { analyzeDomain } from '../services/geminiService';
import { useWebSocket } from '../src/services/websocketService';
import { HistoryItem } from '../types';



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
    const [activeTab, setActiveTab] = useState<'live' | 'manual' | 'chat' | 'stats' | 'intelligence'>('live');
    const [selectedDomainFromLiveFeed, setSelectedDomainFromLiveFeed] = useState<any>(null);

    return (
        <div className="h-full flex flex-col space-y-6">
            <div className="flex space-x-4 border-b border-dark-700 pb-2 overflow-x-auto whitespace-nowrap">
                <button
                    onClick={() => {
                        setActiveTab('live');
                        // Clear the selected domain when switching to live feed
                        setSelectedDomainFromLiveFeed(null);
                    }}
                    className={`pb-2 px-4 font-mono font-bold transition-colors ${activeTab === 'live'
                        ? 'text-accent border-b-2 border-accent'
                        : 'text-dark-500 hover:text-dark-300'
                        }`}
                >
                    LIVE FEED
                </button>
                <button
                    onClick={() => {
                        setActiveTab('manual');
                        // Keep the selected domain when switching to manual
                    }}
                    className={`pb-2 px-4 font-mono font-bold transition-colors ${activeTab === 'manual'
                        ? 'text-accent border-b-2 border-accent'
                        : 'text-dark-500 hover:text-dark-300'
                        }`}
                >
                    MANUAL ANALYSIS
                </button>
                <button
                    onClick={() => setActiveTab('chat')}
                    className={`pb-2 px-4 font-mono font-bold transition-colors ${activeTab === 'chat'
                        ? 'text-accent border-b-2 border-accent'
                        : 'text-dark-500 hover:text-dark-300'
                        }`}
                >
                    SYSTEM CHAT
                </button>
                <button
                    onClick={() => setActiveTab('stats')}
                    className={`pb-2 px-4 font-mono font-bold transition-colors ${activeTab === 'stats'
                        ? 'text-accent border-b-2 border-accent'
                        : 'text-dark-500 hover:text-dark-300'
                        }`}
                >
                    STATS PANEL
                </button>
                <button
                    onClick={() => setActiveTab('intelligence')}
                    className={`pb-2 px-4 font-mono font-bold transition-colors ${activeTab === 'intelligence'
                        ? 'text-accent border-b-2 border-accent'
                        : 'text-dark-500 hover:text-dark-300'
                        }`}
                >
                    SYSTEM INTELLIGENCE
                </button>
            </div>

            <div className="flex-grow overflow-hidden">
                {activeTab === 'live' && (
                    <LiveFeed 
                        onDomainSelect={(domain) => {
                            setSelectedDomainFromLiveFeed(domain);
                        }}
                    />
                )}
                {activeTab === 'manual' && (
                    <ManualAnalysis 
                        selectedModel={selectedModel} 
                        selectedDomainFromLiveFeed={selectedDomainFromLiveFeed}
                    />
                )}
                {activeTab === 'chat' && <ChatPanel />}
                {activeTab === 'stats' && <StatsPanel selectedModel={selectedModel} />}
                {activeTab === 'intelligence' && <SystemIntelligence selectedModel={selectedModel} />}
            </div>
        </div>
    );
};

interface LiveFeedProps {
    onDomainSelect?: (domain: any) => void;
}

const LiveFeed: React.FC<LiveFeedProps> = ({ onDomainSelect }) => {
    const [history, setHistory] = useState<HistoryItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedDomain, setSelectedDomain] = useState<string | null>(null);
    const [selectedAnalysis, setSelectedAnalysis] = useState<HistoryItem | null>(null);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [riskFilter, setRiskFilter] = useState<'all' | 'high'>('high'); // Default to HIGH only
    const [connectionStatus, setConnectionStatus] = useState('disconnected');

    const isPrivacyRisk = (domain: string) => {
        const keywords = ['geo', 'location', 'gps', 'telemetry', 'waa-pa'];
        return keywords.some(k => domain.toLowerCase().includes(k));
    };

    // Store subscriptions in ref to avoid re-creating on every render
    const wsConfig = {
        url: `ws://${window.location.hostname}:8000/ws/public`,
        onConnect: () => {
            setConnectionStatus('connected');
            // Only fetch history once on initial load
            if (history.length === 0) {
                fetchHistory();
            }
        },
        onDisconnect: () => {
            setConnectionStatus('disconnected');
        },
        onMessage: (message) => {
            // Handle heartbeat and other messages
            if (message.event_type === 'heartbeat') {
                setConnectionStatus('connected');
            }
            // Handle threat detection messages
            if (message.event_type === 'threat_detected') {
                console.log('threat_detected received:', message.data);
                setHistory(prev => {
                    // Check for duplicates by domain and timestamp
                    const isDuplicate = prev.some(item => 
                        item.domain === message.data.domain && 
                        Math.abs(new Date(item.timestamp).getTime() - new Date(message.data.timestamp).getTime()) < 1000
                    );
                    if (isDuplicate) {
                        console.log('Skipping duplicate threat:', message.data.domain);
                        return prev;
                    }
                    return [message.data, ...prev.slice(0, 99)]; // Keep only latest 100 items
                });
            }
            // Handle anomaly detection messages
            if (message.event_type === 'anomaly_detected') {
                console.log('anomaly_detected received:', message.data);
                setHistory(prev => {
                    const isDuplicate = prev.some(item => 
                        item.domain === message.data.domain && 
                        Math.abs(new Date(item.timestamp).getTime() - new Date(message.data.timestamp).getTime()) < 1000
                    );
                    if (isDuplicate) {
                        console.log('Skipping duplicate anomaly:', message.data.domain);
                        return prev;
                    }
                    return [message.data, ...prev.slice(0, 99)];
                });
            }
        },
        onError: (error) => {
            console.error('WebSocket error:', error);
            setConnectionStatus('error');
        }
    };

    const { webSocketService } = useWebSocket(wsConfig);

    const fetchHistory = async () => {
        try {
            const res = await fetch(`${API_BASE}/history`);
            if (res.ok) {
                const data = await res.json();
                console.log("Backend Data Received:", data);
                setHistory(data);
                setLoading(false);
            }
        } catch (e) {
            console.error("Failed to fetch history", e);
            setLoading(false);
        }
    };

    // Filter history based on risk level
    const filteredHistory = riskFilter === 'high' 
        ? history.filter(item => {
            const score = item.risk_score?.toLowerCase() || '';
            return score.includes('high') || score === 'critical';
        })
        : history;

    // Handle domain click to show detailed analysis
    const handleDomainClick = (domain: string, analysis: HistoryItem) => {
        setSelectedDomain(domain);
        setSelectedAnalysis(analysis);
        setIsModalOpen(true);
    };
    
    // Handle domain selection for manual analysis
    const handleDomainSelectForManual = (domain: string, analysis: HistoryItem) => {
        if (onDomainSelect) {
            // Pass the full analysis data to the manual analysis component
            onDomainSelect(analysis);
        }
    };

    if (loading && history.length === 0) {
      return (
        <div className="space-y-3 h-full overflow-y-auto pr-2 custom-scrollbar p-4">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <div className="flex items-center bg-yellow-500/20 px-2 py-1 rounded-full text-xs font-medium">
                <Wifi className="w-3 h-3 text-yellow-400 mr-1 animate-pulse" />
                <span className="text-yellow-100">INITIALIZING</span>
              </div>
              <span className="text-dark-300 text-sm font-mono">• Connecting...</span>
            </div>
          </div>
          <SkeletonLoader variant="list-item" count={5} className="w-full" />
        </div>
      );
    }

    return (
        <div className="space-y-3 h-full overflow-y-auto pr-2 custom-scrollbar">
            {/* Connection Status Indicator */}
            <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                    {connectionStatus === 'connected' ? (
                        <>
                            <Wifi className="w-4 h-4 text-green-500" />
                            <span className="text-green-500 text-sm font-mono">LIVE</span>
                        </>
                    ) : connectionStatus === 'connecting' ? (
                        <>
                            <Wifi className="w-4 h-4 text-yellow-500 animate-pulse" />
                            <span className="text-yellow-500 text-sm font-mono">CONNECTING</span>
                        </>
                    ) : (
                        <>
                            <WifiOff className="w-4 h-4 text-red-500" />
                            <span className="text-red-500 text-sm font-mono">DISCONNECTED</span>
                        </>
                    )}
                    <span className="text-dark-300 text-sm font-mono">• {history.length} records</span>
                </div>
                
                {/* Risk Filter Buttons */}
                <div className="flex gap-2">
                    <button
                        onClick={() => setRiskFilter('high')}
                        className={`px-3 py-1 rounded text-sm font-mono transition-colors ${
                            riskFilter === 'high' 
                            ? 'bg-red-600 text-white' 
                            : 'bg-dark-700 text-dark-400 hover:bg-dark-600'
                        }`}
                    >
                        🔴 HIGH RISK ONLY
                    </button>
                    <button
                        onClick={() => setRiskFilter('all')}
                        className={`px-3 py-1 rounded text-sm font-mono transition-colors ${
                            riskFilter === 'all' 
                            ? 'bg-accent text-white' 
                            : 'bg-dark-700 text-dark-400 hover:bg-dark-600'
                        }`}
                    >
                        📋 ALL THREATS
                    </button>
                </div>
            </div>
            
            {filteredHistory.map((item, idx) => {
                const geoRisk = isPrivacyRisk(item.domain);
                const displayTime = item.timestamp && !isNaN(Date.parse(item.timestamp))
                    ? new Date(item.timestamp).toLocaleString([], {
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                        second: '2-digit'
                      })
                    : "Unknown";

                const isBlocked = item.adguard_metadata && item.adguard_metadata.reason !== 'NotFilteredNotFound';

                return (
                    <div key={item.timestamp + idx} className={`bg-dark-800 p-4 rounded border-l-4 ${item.is_anomaly ? 'border-yellow-500 shadow-[0_0_15px_rgba(234,179,8,0.2)] animate-[pulse_3s_infinite]' : geoRisk ? 'border-red-500 bg-red-900/10' : isBlocked ? 'border-orange-500 bg-orange-950/5' : 'border-dark-600'} hover:border-accent transition-all shadow-md relative overflow-hidden group`}>
                        <div className="flex justify-between items-start mb-2">
                            <div className="flex items-center space-x-2">
                                <h3 
                                    className="text-lg font-bold text-dark-100 font-mono break-all cursor-pointer hover:text-accent transition-colors"
                                    onClick={() => handleDomainClick(item.domain, item)}
                                    title="Click to view detailed backend analysis"
                                >
                                    {item.domain}
                                </h3>
                                <button
                                    onClick={() => handleDomainClick(item.domain, item)}
                                    className="p-1 hover:bg-dark-700 rounded transition-colors opacity-0 group-hover:opacity-100"
                                    title="View detailed analysis"
                                >
                                    <EyeIcon className="w-4 h-4 text-accent" />
                                </button>
                                <button
                                    onClick={() => handleDomainSelectForManual(item.domain, item)}
                                    className="p-1 hover:bg-dark-700 rounded transition-colors opacity-0 group-hover:opacity-100"
                                    title="Copy to Manual Analysis"
                                >
                                    <Target className="w-4 h-4 text-blue-400" />
                                </button>
                                {geoRisk && (
                                    <LocateFixed className="w-5 h-5 text-red-500 animate-pulse" />
                                )}
                                {isBlocked && (
                                    <span className="flex items-center space-x-1 px-2 py-0.5 bg-dark-700 text-accent border border-accent/30 rounded text-[10px] font-mono uppercase tracking-wider">
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
                            <span className="text-xs text-dark-400 font-mono">{displayTime}</span>
                        </div>

                        <div className="flex flex-wrap items-center gap-2 text-sm mb-3">
                            <RiskBadge score={item.risk_score} />
                            <span className="px-2 py-0.5 bg-dark-700 text-dark-300 rounded text-xs font-mono uppercase tracking-wide">
                                {item.category}
                            </span>
                            {geoRisk && (
                                <span className="px-2 py-0.5 bg-red-600 text-white rounded text-xs font-bold font-mono animate-pulse">
                                    GEOLOCATION ATTEMPT
                                </span>
                            )}
                            {/* Remove the SOC GUARD ACTIVE tag as requested */}
                        </div>

                        {item.adguard_metadata && item.adguard_metadata.reason !== 'NotFilteredNotFound' && (
                            <div className="mb-3 px-3 py-2 border-l-2 border-orange-500/50">
                                <p className="text-[10px] uppercase font-mono text-dark-400 mb-1">AdGuard Intelligence</p>
                                <div className="flex flex-col space-y-1">
                                    <div className="flex justify-between text-xs">
                                        <span className="text-dark-400">Reason:</span>
                                        <span className="text-orange-300 font-mono">{item.adguard_metadata.reason}</span>
                                    </div>
                                    {item.adguard_metadata.rule && (
                                        <div className="flex flex-col text-xs">
                                            <span className="text-dark-400">Rule:</span>
                                            <code className="text-[10px] text-accent-light bg-dark-900 p-1 rounded mt-1 overflow-x-auto">{item.adguard_metadata.rule}</code>
                                        </div>
                                    )}
                                </div>
                            </div>
                        )}

                        <p className="text-dark-400 text-sm leading-relaxed font-sans border-t border-dark-700 pt-2">
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
                <div className="text-center text-dark-500 py-10 font-mono">
                    No threats detected... yet.
                </div>
            )}

            {/* Analysis Modal */}
            <AnalysisModal
                isOpen={isModalOpen}
                onClose={() => setIsModalOpen(false)}
                domain={selectedDomain || ''}
                analysis={selectedAnalysis}
            />
        </div>
    );
};

interface ManualAnalysisProps {
    selectedModel: string;
    selectedDomainFromLiveFeed?: any;
}

const ManualAnalysis: React.FC<ManualAnalysisProps> = ({ selectedModel, selectedDomainFromLiveFeed }) => {
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

    // When a domain is selected from live feed, update the form
    useEffect(() => {
        if (selectedDomainFromLiveFeed) {
            setDomain(selectedDomainFromLiveFeed.domain || '');
            setResult({
                domain: selectedDomainFromLiveFeed.domain,
                risk_score: selectedDomainFromLiveFeed.risk_score,
                category: selectedDomainFromLiveFeed.category,
                summary: selectedDomainFromLiveFeed.summary,
                is_anomaly: selectedDomainFromLiveFeed.is_anomaly,
                anomaly_score: selectedDomainFromLiveFeed.anomaly_score,
                entropy: selectedDomainFromLiveFeed.entropy,
                adguard_metadata: selectedDomainFromLiveFeed.adguard_metadata,
                analysis_source: selectedDomainFromLiveFeed.analysis_source
            });
        }
    }, [selectedDomainFromLiveFeed]);

    // Vector Embedding Visualization Component
    const VectorEmbeddingVisualizer = ({ result }: { result: any }) => {
        if (!result) return null;
        
        // Convert entropy and other numeric values to binary representation
        const entropyBinary = (result.entropy || 0).toString(2).replace('.', '');
        const anomalyScoreBinary = (result.anomaly_score || 0).toString(2).replace('.', '');
        
        return (
            <div className="bg-dark-800 p-4 rounded-lg border border-dark-700 mb-6">
                <div className="flex items-center justify-between mb-4">
                    <h4 className="text-lg font-semibold text-white">Vector Embedding Data</h4>
                    <Activity className="w-5 h-5 text-accent" />
                </div>
                
                <div className="space-y-4">
                    <div>
                        <div className="flex justify-between text-sm mb-2">
                            <span className="text-dark-400">Entropy Binary Representation</span>
                            <span className="text-dark-400">Length: {entropyBinary.length}</span>
                        </div>
                        <div className="bg-dark-900 p-3 rounded border border-dark-600 font-mono text-sm overflow-x-auto">
                            {entropyBinary.substring(0, 64)}{entropyBinary.length > 64 ? '...' : ''}
                        </div>
                    </div>
                    
                    <div>
                        <div className="flex justify-between text-sm mb-2">
                            <span className="text-dark-400">Anomaly Score Binary</span>
                            <span className="text-dark-400">Length: {anomalyScoreBinary.length}</span>
                        </div>
                        <div className="bg-dark-900 p-3 rounded border border-dark-600 font-mono text-sm overflow-x-auto">
                            {anomalyScoreBinary.substring(0, 64)}{anomalyScoreBinary.length > 64 ? '...' : ''}
                        </div>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-4 mt-4">
                        <div className="bg-dark-900 p-3 rounded border border-dark-600">
                            <div className="text-xs text-dark-400 mb-1">Similarity Match</div>
                            <div className="text-lg font-bold text-accent">
                                {result.has_similarity_match ? 'YES' : 'NO'}
                            </div>
                        </div>
                        <div className="bg-dark-900 p-3 rounded border border-dark-600">
                            <div className="text-xs text-dark-400 mb-1">Embedding Size</div>
                            <div className="text-lg font-bold text-accent">
                                {result.entropy ? Math.floor((result.entropy || 0) * 100) : 0} bits
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        );
    };

    return (
        <div className="flex flex-col h-full overflow-y-auto pr-2 custom-scrollbar">
            <form onSubmit={handleAnalyze} className="bg-dark-800 p-5 rounded-lg border border-dark-700 mb-6 shadow-lg">
                <label className="block text-xs font-mono text-accent-light mb-2 uppercase tracking-widest">Target Domain</label>
                <div className="flex gap-3">
                    <input
                        type="text"
                        value={domain}
                        onChange={(e) => setDomain(e.target.value)}
                        placeholder="e.g., suspicious-site.com"
                        className="flex-grow bg-dark-900 border border-dark-600 rounded p-3 text-dark-100 focus:outline-none focus:border-accent font-mono transition-colors"
                    />
                    <button
                        type="submit"
                        disabled={loading}
                        className="bg-accent hover:bg-accent text-white font-bold py-2 px-6 rounded transition-colors disabled:opacity-50 uppercase font-mono tracking-wide"
                    >
                        {loading ? 'Scanning...' : 'Scan'}
                    </button>
                </div>
            </form>

            {result && (
                <div className="bg-dark-800 rounded-lg p-6 border border-dark-700 shadow-xl animate-fade-in mb-8">
                    <div className="flex items-center justify-between mb-6">
                        <h3 className="text-xl font-bold text-white font-mono">Scan Results</h3>
                        <RiskBadge score={result.risk_score} />
                    </div>

                    {/* Vector Embedding Data Section */}
                    <VectorEmbeddingVisualizer result={result} />

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                        <div>
                            <p className="text-xs text-dark-500 uppercase font-mono mb-1">Category</p>
                            <p className="text-lg text-dark-200">{result.category}</p>
                        </div>
                        <div>
                            <p className="text-xs text-dark-500 uppercase font-mono mb-1">Verdict</p>
                            <p className="text-lg text-dark-200">{result.summary}</p>
                        </div>
                        
                        {/* Additional forensic data from live feed */}
                        {result.entropy !== undefined && (
                            <div>
                                <p className="text-xs text-dark-500 uppercase font-mono mb-1">Entropy Score</p>
                                <p className="text-lg text-white font-mono">{result.entropy?.toFixed(2)}</p>
                            </div>
                        )}
                        {result.is_anomaly !== undefined && (
                            <div>
                                <p className="text-xs text-dark-500 uppercase font-mono mb-1">Anomaly Score</p>
                                <p className="text-lg text-white font-mono">{result.anomaly_score?.toFixed(4)}</p>
                            </div>
                        )}
                        {result.analysis_source && (
                            <div>
                                <p className="text-xs text-dark-500 uppercase font-mono mb-1">Analysis Source</p>
                                <p className="text-lg text-white font-mono capitalize">{result.analysis_source}</p>
                            </div>
                        )}
                    </div>

                    <CodeBlock code={JSON.stringify(result, null, 2)} />
                </div>
            )}

            {/* Session Research Section */}
            <div className="mt-4">
                <h3 className="text-dark-400 font-mono text-sm uppercase mb-4 border-b border-dark-700 pb-2">Session Research</h3>
                <div className="space-y-3">
                    {sessionHistory.map((item, idx) => {
                        const displayTime = item.timestamp && !isNaN(Date.parse(item.timestamp))
                            ? new Date(item.timestamp).toLocaleString([], {
                                month: 'short',
                                day: 'numeric',
                                hour: '2-digit',
                                minute: '2-digit'
                              })
                            : "Unknown";
                        return (
                            <div key={idx} className="bg-dark-800/50 p-3 rounded border-l-2 border-dark-600 flex justify-between items-center hover:bg-dark-800 transition-colors">
                                <div>
                                    <div className="font-mono text-dark-200 font-bold">{item.domain}</div>
                                    <div className="text-xs text-dark-500">{item.category} • {item.risk_score} Risk</div>
                                </div>
                                <div className="text-xs text-dark-600 font-mono">
                                    {displayTime}
                                </div>
                            </div>
                        );
                    })}
                    {sessionHistory.length === 0 && (
                        <div className="text-dark-500 text-xs font-mono italic">No manual scans this session.</div>
                    )}
                </div>
            </div>
        </div>
    );
};

// Import Activity icon if not already available


const RiskBadge: React.FC<{ score: string }> = ({ score }) => {
    let color = 'bg-dark-600 text-dark-200';

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
            <span className="text-dark-300">{item.label}</span>
            <span className="font-bold text-white">{item.value}%</span>
          </div>
          <div className="w-full bg-dark-700 rounded-full h-2">
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
          <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-16 h-16 bg-dark-800 rounded-full border-2 border-dark-700 flex items-center justify-center">
            <span className="text-xs font-mono text-dark-400">Total</span>
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
              <span className="text-dark-300">{item.label}</span>
            </div>
            <span className="font-bold text-white">{item.value}%</span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default Dashboard;
