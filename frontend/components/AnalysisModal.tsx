import React from 'react';
import { Globe, X, Brain, Database, Shield, Activity, FileSpreadsheet } from 'lucide-react';

interface SystemStats {
    autonomy_score: number;
    local_decisions: number;
    cloud_decisions: number;
    classifier: {
        total_patterns: number;
    };
    cache: {
        memory_cache_size: number;
        valid_memory_entries: number;
        disk_cache_exists: boolean;
        cache_file_size: number;
    };
    system_usage: {
        active_integrations: Array<{
            name: string;
            status: string;
            description: string;
        }>;
        tracker_detection: {
            total_detected: number;
            categories: Record<string, number>;
            detection_methods: string[];
        };
        learning_progress: {
            seed_patterns: number;
            learned_patterns: number;
            learning_rate: string;
            next_milestone: string;
        };
    };
}

interface AnalysisModalProps {
    isOpen: boolean;
    onClose: () => void;
    domain: string;
    stats: SystemStats;
}

const AnalysisModal: React.FC<AnalysisModalProps> = ({ 
    isOpen, 
    onClose, 
    domain, 
    stats 
}) => {
    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-slate-900 border border-slate-700 rounded-lg shadow-2xl max-w-6xl w-full max-h-[90vh] overflow-hidden">
                {/* Header */}
                <div className="flex items-center justify-between p-6 border-b border-slate-700">
                    <div className="flex items-center space-x-4">
                        <div className="w-12 h-12 bg-gradient-to-br from-purple-600 to-blue-500 rounded-full flex items-center justify-center">
                            <Globe className="w-6 h-6 text-white" />
                        </div>
                        <div>
                            <h2 className="text-2xl font-bold text-white font-mono">{domain}</h2>
                            <p className="text-slate-400 text-sm">Complete Backend Analysis</p>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 hover:bg-slate-800 rounded-full transition-colors"
                    >
                        <X className="w-6 h-6 text-slate-400" />
                    </button>
                </div>

                {/* Content */}
                <div className="p-6 space-y-6 overflow-y-auto max-h-[calc(90vh-120px)]">
                    {/* Section 1: Top Row - Two Equal Cards */}
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        {/* System Intelligence Card */}
                        <div className="bg-slate-800/50 p-6 rounded-lg border border-slate-700">
                            <h3 className="text-lg font-semibold text-white mb-4 flex items-center space-x-2">
                                <Brain className="w-5 h-5 text-purple-400" />
                                <span>System Intelligence</span>
                            </h3>
                            <div className="space-y-4">
                                <div className="flex justify-between items-center">
                                    <span className="text-slate-300">Autonomy Score</span>
                                    <span className="text-2xl font-bold text-purple-400 font-mono">
                                        {stats.autonomy_score}%
                                    </span>
                                </div>
                                <div className="flex justify-between items-center">
                                    <span className="text-slate-300">Local Decisions</span>
                                    <span className="text-lg font-bold text-cyan-400 font-mono">
                                        {stats.local_decisions}
                                    </span>
                                </div>
                                <div className="flex justify-between items-center">
                                    <span className="text-slate-300">Cloud Decisions</span>
                                    <span className="text-lg font-bold text-blue-400 font-mono">
                                        {stats.cloud_decisions}
                                    </span>
                                </div>
                                <div className="flex justify-between items-center">
                                    <span className="text-slate-300">Total Patterns</span>
                                    <span className="text-lg font-bold text-yellow-400 font-mono">
                                        {stats.classifier.total_patterns}
                                    </span>
                                </div>
                            </div>
                        </div>

                        {/* Cache Performance Card */}
                        <div className="bg-slate-800/50 p-6 rounded-lg border border-slate-700">
                            <h3 className="text-lg font-semibold text-white mb-4 flex items-center space-x-2">
                                <Database className="w-5 h-5 text-cyan-400" />
                                <span>Cache Performance</span>
                            </h3>
                            <div className="space-y-4">
                                <div className="flex justify-between items-center">
                                    <span className="text-slate-300">Memory Cache Size</span>
                                    <span className="text-lg font-bold text-cyan-400 font-mono">
                                        {stats.cache.memory_cache_size}
                                    </span>
                                </div>
                                <div className="flex justify-between items-center">
                                    <span className="text-slate-300">Valid Entries</span>
                                    <span className="text-lg font-bold text-cyan-400 font-mono">
                                        {stats.cache.valid_memory_entries}
                                    </span>
                                </div>
                                <div className="flex justify-between items-center">
                                    <span className="text-slate-300">Disk Cache</span>
                                    <span className={`text-sm font-mono px-3 py-1 rounded border ${
                                        stats.cache.disk_cache_exists 
                                            ? 'bg-green-900/50 text-green-400 border-green-500/30' 
                                            : 'bg-red-900/50 text-red-400 border-red-500/30'
                                    }`}>
                                        {stats.cache.disk_cache_exists ? 'ENABLED' : 'DISABLED'}
                                    </span>
                                </div>
                                <div className="flex justify-between items-center">
                                    <span className="text-slate-300">Cache File Size</span>
                                    <span className="text-sm text-slate-400 font-mono">
                                        {(stats.cache.cache_file_size / 1024).toFixed(2)} KB
                                    </span>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Section 2: Bottom Panel - System Usage Details */}
                    <div className="bg-slate-800/50 p-6 rounded-lg border border-slate-700">
                        <h3 className="text-lg font-semibold text-white mb-6 flex items-center space-x-2">
                            <Shield className="w-5 h-5 text-blue-400" />
                            <span>System Usage Details</span>
                        </h3>
                        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
                            {/* Column 1: Active Integrations */}
                            <div className="space-y-4">
                                <h4 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Active Integrations</h4>
                                {stats.system_usage.active_integrations.map((integration, index) => (
                                    <div key={index} className="bg-slate-700 p-4 rounded border border-slate-600">
                                        <div className="flex justify-between items-start mb-2">
                                            <span className="text-sm font-mono text-white">{integration.name}</span>
                                            <span className="text-xs px-2 py-1 rounded font-mono bg-green-900/50 text-green-400 border border-green-500/30">
                                                {integration.status}
                                            </span>
                                        </div>
                                        <p className="text-xs text-slate-400">{integration.description}</p>
                                    </div>
                                ))}
                            </div>

                            {/* Column 2: Tracker Detection */}
                            <div className="space-y-4">
                                <h4 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Tracker Detection</h4>
                                <div className="bg-slate-700 p-4 rounded border border-slate-600">
                                    <div className="flex justify-between items-center mb-3">
                                        <span className="text-sm text-slate-300">Total Detected</span>
                                        <span className="text-2xl font-bold text-orange-400 font-mono">
                                            {stats.system_usage.tracker_detection.total_detected}
                                        </span>
                                    </div>
                                    <div className="space-y-2">
                                        {Object.entries(stats.system_usage.tracker_detection.categories).map(([category, count]) => (
                                            <div key={category} className="flex justify-between text-sm">
                                                <span className="text-slate-400 capitalize">{category}</span>
                                                <span className="text-white font-mono">{count}</span>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                                <div className="bg-slate-700 p-4 rounded border border-slate-600">
                                    <h5 className="text-xs text-slate-300 mb-2">Detection Methods:</h5>
                                    <ul className="text-xs text-slate-400 space-y-1">
                                        {stats.system_usage.tracker_detection.detection_methods.map((method, index) => (
                                            <li key={index} className="flex items-center space-x-2">
                                                <span className="w-1 h-1 bg-cyan-400 rounded-full"></span>
                                                <span>{method}</span>
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            </div>

                            {/* Column 3: Learning Progress */}
                            <div className="space-y-4">
                                <h4 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Learning Progress</h4>
                                <div className="bg-slate-700 p-4 rounded border border-slate-600">
                                    <div className="space-y-3">
                                        <div className="flex justify-between text-sm">
                                            <span className="text-slate-300">Seed Patterns</span>
                                            <span className="font-bold text-blue-400 font-mono">
                                                {stats.system_usage.learning_progress.seed_patterns}
                                            </span>
                                        </div>
                                        <div className="flex justify-between text-sm">
                                            <span className="text-slate-300">Learned Patterns</span>
                                            <span className="font-bold text-purple-400 font-mono">
                                                {stats.system_usage.learning_progress.learned_patterns}
                                            </span>
                                        </div>
                                        <div className="flex justify-between text-sm">
                                            <span className="text-slate-300">Learning Rate</span>
                                            <span className="font-bold text-yellow-400 font-mono">
                                                {stats.system_usage.learning_progress.learning_rate}
                                            </span>
                                        </div>
                                    </div>
                                </div>
                                <div className="bg-gradient-to-r from-green-900/50 to-blue-900/50 p-4 rounded border border-green-500/30">
                                    <div className="text-xs text-slate-300 mb-1">Next Milestone</div>
                                    <div className="text-sm font-bold text-green-400 font-mono">
                                        {stats.system_usage.learning_progress.next_milestone}
                                    </div>
                                </div>
                            </div>

                            {/* Column 4: Google Sheets Integration */}
                            <div className="space-y-4">
                                <h4 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Google Sheets Integration</h4>
                                <div className="bg-slate-700 p-4 rounded border border-slate-600">
                                    <div className="flex items-center space-x-3 mb-3">
                                        <svg className="w-5 h-5 text-green-400" fill="currentColor" viewBox="0 0 24 24">
                                            <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zM9 17H7v-2h2v2zm0-4H7v-2h2v2zm0-4H7V7h2v2zm4 8h-2v-2h2v2zm0-4h-2v-2h2v2zm0-4h-2V7h2v2zm4 8h-2v-2h2v2zm0-4h-2v-2h2v2zm0-4h-2V7h2v2z"/>
                                        </svg>
                                        <div>
                                            <div className="text-sm font-bold text-white">Threat Log Synchronization</div>
                                            <div className="text-xs text-slate-400">Real-time data backup</div>
                                        </div>
                                    </div>
                                    <div className="space-y-2">
                                        <div className="flex justify-between text-sm">
                                            <span className="text-slate-300">Last Sync</span>
                                            <span className="text-green-400 font-mono">Just Now</span>
                                        </div>
                                        <div className="flex justify-between text-sm">
                                            <span className="text-slate-300">Total Records</span>
                                            <span className="text-cyan-400 font-mono">Live Count</span>
                                        </div>
                                        <div className="flex justify-between text-sm">
                                            <span className="text-slate-300">Domain Examples</span>
                                            <span className="text-purple-400 font-mono">googlevideo.com</span>
                                        </div>
                                    </div>
                                </div>
                                <div className="bg-gradient-to-r from-blue-900/50 to-green-900/50 p-3 rounded border border-blue-500/30">
                                    <div className="text-xs text-slate-300 mb-1">Domain Analysis</div>
                                    <div className="text-xs text-blue-400 font-mono">
                                        rr8---sn-v2u0n-hxad.googlevideo.com
                                    </div>
                                    <div className="text-xs text-slate-400 mt-1">
                                        YouTube video streaming domain - System/Tracker classification
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default AnalysisModal;