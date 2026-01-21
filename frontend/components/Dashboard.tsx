
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

const LiveFeed: React.FC = () => {
    const [history, setHistory] = useState<HistoryItem[]>([]);
    const [loading, setLoading] = useState(true);

    const fetchHistory = async () => {
        try {
            const res = await fetch('/api/history');
            if (res.ok) {
                const data = await res.json();
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
        const interval = setInterval(fetchHistory, 10000); // Poll every 10s
        return () => clearInterval(interval);
    }, []);

    if (loading && history.length === 0) return <LoadingSpinner />;

    return (
        <div className="space-y-3 h-full overflow-y-auto pr-2 custom-scrollbar">
            {history.map((item, idx) => (
                <div key={idx} className="bg-slate-800 p-4 rounded border-l-4 border-slate-600 hover:border-cyan-500 transition-all shadow-md">
                    <div className="flex justify-between items-start mb-2">
                        <h3 className="text-lg font-bold text-slate-100 font-mono break-all">{item.domain}</h3>
                        <span className="text-xs text-slate-500 font-mono">{new Date(item.timestamp).toLocaleTimeString()}</span>
                    </div>

                    <div className="flex items-center space-x-3 text-sm mb-3">
                        <RiskBadge score={item.risk_score} />
                        <span className="px-2 py-0.5 bg-slate-700 text-slate-300 rounded text-xs font-mono uppercase tracking-wide">
                            {item.category}
                        </span>
                    </div>

                    <p className="text-slate-400 text-sm leading-relaxed font-sans border-t border-slate-700 pt-2">
                        {item.summary}
                    </p>
                </div>
            ))}
            {history.length === 0 && (
                <div className="text-center text-slate-500 py-10 font-mono">
                    No threats detected... yet.
                </div>
            )}
        </div>
    );
};

const ManualAnalysis: React.FC = () => {
    const [domain, setDomain] = useState('');
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<any>(null);

    const handleAnalyze = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!domain) return;

        setLoading(true);
        setResult(null);
        try {
            const res = await fetch('/api/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ domain })
            });
            const data = await res.json();
            setResult(data);
        } catch (error) {
            console.error(error);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="flex flex-col h-full">
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
                <div className="bg-slate-800 rounded-lg p-6 border border-slate-700 shadow-xl animate-fade-in">
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
        </div>
    );
};

const RiskBadge: React.FC<{ score: string }> = ({ score }) => {
    let color = 'bg-slate-600 text-slate-200';

    // Normalize score cases
    const s = score.toLowerCase();

    if (s === 'high') color = 'bg-red-500 text-white shadow-red-glow';
    else if (s === 'medium') color = 'bg-orange-500 text-white';
    else if (s === 'low') color = 'bg-green-500 text-white';

    return (
        <span className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${color}`}>
            {score} Risk
        </span>
    );
};

export default Dashboard;
