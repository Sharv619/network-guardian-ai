
import React, { useState, useEffect } from 'react';
import LoadingSpinner from './LoadingSpinner';
import CodeBlock from './CodeBlock';
import { ThreatReport } from '../types';

interface HistoryItem {
    domain: string;
    risk_score: string;
    category: string;
    summary: string;
    timestamp: string;
}

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

const Dashboard: React.FC = () => {
    const [activeTab, setActiveTab] = useState<'live' | 'manual'>('live');

    return (
        <div className="h-full flex flex-col space-y-6">
            <div className="flex space-x-4 border-b border-slate-700 pb-2">
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
            </div>

            <div className="flex-grow overflow-hidden">
                {activeTab === 'live' ? <LiveFeed /> : <ManualAnalysis />}
            </div>
        </div>
    );
};

import { LocateFixed } from 'lucide-react';

const LiveFeed: React.FC = () => {
    const [history, setHistory] = useState<HistoryItem[]>([]);
    const [loading, setLoading] = useState(true);

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
        const interval = setInterval(fetchHistory, 5000); // Poll every 5s
        return () => clearInterval(interval);
    }, []);

    if (loading && history.length === 0) return <LoadingSpinner />;

    return (
        <div className="space-y-3 h-full overflow-y-auto pr-2 custom-scrollbar">
            {history.map((item, idx) => {
                const geoRisk = isPrivacyRisk(item.domain);
                return (
                    <div key={idx} className={`bg-slate-800 p-4 rounded border-l-4 ${geoRisk ? 'border-red-500 bg-red-900/10' : 'border-slate-600'} hover:border-cyan-500 transition-all shadow-md relative overflow-hidden group`}>
                        <div className="flex justify-between items-start mb-2">
                            <div className="flex items-center space-x-2">
                                <h3 className="text-lg font-bold text-slate-100 font-mono break-all">{item.domain}</h3>
                                {geoRisk && (
                                    <LocateFixed className="w-5 h-5 text-red-500 animate-pulse" />
                                )}
                            </div>
                            <span className="text-xs text-slate-500 font-mono">{new Date(item.timestamp).toLocaleTimeString()}</span>
                        </div>

                        <div className="flex items-center space-x-3 text-sm mb-3">
                            <RiskBadge score={item.risk_score} />
                            <span className="px-2 py-0.5 bg-slate-700 text-slate-300 rounded text-xs font-mono uppercase tracking-wide">
                                {item.category}
                            </span>
                            {geoRisk && (
                                <span className="px-2 py-0.5 bg-red-600 text-white rounded text-xs font-bold font-mono animate-pulse">
                                    GEOLOCATION ATTEMPT
                                </span>
                            )}
                            {item.summary.includes("Fallback") && (
                                <span className="px-2 py-0.5 bg-purple-900 text-purple-200 border border-purple-700 rounded text-xs font-mono uppercase tracking-wide">
                                    Heuristic Mode
                                </span>
                            )}
                        </div>

                        <p className="text-slate-400 text-sm leading-relaxed font-sans border-t border-slate-700 pt-2">
                            {item.summary}
                        </p>

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
        </div>
    );
};

import { analyzeDomain } from '../services/geminiService';

const ManualAnalysis: React.FC = () => {
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
            // SRE Pattern: BFF (Backend-for-Frontend) Proxy
            const data = await analyzeDomain(domain);

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
                    {sessionHistory.map((item, idx) => (
                        <div key={idx} className="bg-slate-800/50 p-3 rounded border-l-2 border-slate-600 flex justify-between items-center hover:bg-slate-800 transition-colors">
                            <div>
                                <div className="font-mono text-slate-200 font-bold">{item.domain}</div>
                                <div className="text-xs text-slate-500">{item.category} • {item.risk_score} Risk</div>
                            </div>
                            <div className="text-xs text-slate-600 font-mono">
                                {new Date(item.timestamp).toLocaleTimeString()}
                            </div>
                        </div>
                    ))}
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

export default Dashboard;
