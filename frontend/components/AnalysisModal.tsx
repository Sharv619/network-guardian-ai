import React from 'react';
import { Globe, X, Brain, Database, Shield, Activity, CheckCircle, AlertTriangle, Bot, Zap, Hash } from 'lucide-react';

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
    analysis_source?: string;
    entropy?: number;
}

interface AnalysisModalProps {
    isOpen: boolean;
    onClose: () => void;
    domain: string;
    analysis: HistoryItem | null;
}

const AnalysisModal: React.FC<AnalysisModalProps> = ({ 
    isOpen, 
    onClose, 
    domain, 
    analysis 
}) => {
    if (!isOpen) return null;

    const isSafe = analysis?.risk_score === 'Low' || analysis?.risk_score === 'Unknown' || !analysis?.is_anomaly;
    const isAnomaly = analysis?.is_anomaly;
    const isBlocked = analysis?.adguard_metadata && analysis.adguard_metadata.reason !== 'NotFilteredNotFound';

    // Determine entropy risk level
    const entropyValue = analysis?.entropy || 0;
    const entropyRisk = entropyValue > 4.0 ? 'HIGH' : entropyValue > 3.5 ? 'MEDIUM' : 'LOW';

    return (
        <div 
            className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4"
            onClick={onClose}
        >
            <div 
                className="bg-slate-900 border border-slate-700 rounded-xl shadow-2xl max-w-3xl w-full max-h-[90vh] overflow-hidden"
                onClick={(e) => e.stopPropagation()}
            >
                {/* Header */}
                <div className={`p-6 border-b flex items-center justify-between ${
                    isSafe ? 'bg-gradient-to-r from-green-900/30 to-emerald-900/20 border-green-500/30' :
                    isAnomaly ? 'bg-gradient-to-r from-yellow-900/30 to-orange-900/20 border-yellow-500/30' :
                    isBlocked ? 'bg-gradient-to-r from-red-900/30 to-pink-900/20 border-red-500/30' :
                    'bg-gradient-to-r from-blue-900/30 to-cyan-900/20 border-cyan-500/30'
                }`}>
                    <div className="flex items-center space-x-4">
                        <div className={`w-14 h-14 rounded-full flex items-center justify-center ${
                            isSafe ? 'bg-green-500/20' : isAnomaly ? 'bg-yellow-500/20' : isBlocked ? 'bg-red-500/20' : 'bg-cyan-500/20'
                        }`}>
                            {isSafe ? <CheckCircle className="w-7 h-7 text-green-400" /> :
                             isAnomaly ? <Bot className="w-7 h-7 text-yellow-400" /> :
                             isBlocked ? <AlertTriangle className="w-7 h-7 text-red-400" /> :
                             <Shield className="w-7 h-7 text-cyan-400" />}
                        </div>
                        <div>
                            <div className="flex items-center gap-2">
                                <h2 className="text-2xl font-bold text-white font-mono break-all">{domain}</h2>
                            </div>
                            <div className="flex items-center gap-2 mt-1 flex-wrap">
                                {isSafe ? (
                                    <span className="px-3 py-1 bg-green-500/20 text-green-400 border border-green-500/30 rounded-full text-sm font-medium flex items-center gap-1">
                                        <CheckCircle className="w-4 h-4" /> SOC GUARD ACTIVE - VERIFIED SAFE
                                    </span>
                                ) : isAnomaly ? (
                                    <span className="px-3 py-1 bg-yellow-500/20 text-yellow-400 border border-yellow-500/30 rounded-full text-sm font-medium flex items-center gap-1">
                                        <Bot className="w-4 h-4" /> BEHAVIORAL ANOMALY DETECTED
                                    </span>
                                ) : isBlocked ? (
                                    <span className="px-3 py-1 bg-red-500/20 text-red-400 border border-red-500/30 rounded-full text-sm font-medium flex items-center gap-1">
                                        <AlertTriangle className="w-4 h-4" /> ADGUARD BLOCKED
                                    </span>
                                ) : (
                                    <span className="px-3 py-1 bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 rounded-full text-sm font-medium flex items-center gap-1">
                                        <Shield className="w-4 h-4" /> ANALYSIS COMPLETE
                                    </span>
                                )}
                            </div>
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
                <div className="p-6 space-y-5 overflow-y-auto max-h-[calc(90vh-160px)]">
                    {/* Analysis Summary */}
                    <div className="bg-slate-800/50 p-5 rounded-lg border border-slate-700">
                        <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                            <Brain className="w-4 h-4" /> Analysis Summary
                        </h3>
                        <p className="text-white text-lg leading-relaxed">
                            {analysis?.summary || 'No analysis available for this domain.'}
                        </p>
                    </div>

                    {/* Technical Grid */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                        <div className="bg-slate-800/50 p-4 rounded-lg border border-slate-700">
                            <div className="text-xs text-slate-500 uppercase tracking-wider mb-1">Category</div>
                            <div className={`text-lg font-bold ${
                                analysis?.category?.includes('Malware') ? 'text-red-400' :
                                analysis?.category?.includes('Tracker') ? 'text-orange-400' :
                                analysis?.category?.includes('ZERO-DAY') ? 'text-yellow-400' :
                                analysis?.category?.includes('System') ? 'text-blue-400' :
                                'text-green-400'
                            }`}>
                                {analysis?.category || 'General Traffic'}
                            </div>
                        </div>
                        <div className="bg-slate-800/50 p-4 rounded-lg border border-slate-700">
                            <div className="text-xs text-slate-500 uppercase tracking-wider mb-1">Risk Level</div>
                            <div className={`text-lg font-bold ${
                                analysis?.risk_score === 'High' ? 'text-red-400' :
                                analysis?.risk_score === 'Medium' ? 'text-orange-400' :
                                analysis?.risk_score === 'Low' ? 'text-yellow-400' :
                                'text-green-400'
                            }`}>
                                {analysis?.risk_score || 'Unknown'}
                            </div>
                        </div>
                        <div className="bg-slate-800/50 p-4 rounded-lg border border-slate-700">
                            <div className="text-xs text-slate-500 uppercase tracking-wider mb-1 flex items-center gap-1">
                                <Hash className="w-3 h-3" /> Entropy
                            </div>
                            <div className={`text-lg font-bold ${
                                entropyRisk === 'HIGH' ? 'text-red-400' :
                                entropyRisk === 'MEDIUM' ? 'text-orange-400' :
                                'text-green-400'
                            }`}>
                                {entropyValue.toFixed(2)}
                            </div>
                            <div className="text-xs text-slate-500">{entropyRisk} RISK</div>
                        </div>
                        <div className="bg-slate-800/50 p-4 rounded-lg border border-slate-700">
                            <div className="text-xs text-slate-500 uppercase tracking-wider mb-1 flex items-center gap-1">
                                <Zap className="w-3 h-3" /> Source
                            </div>
                            <div className="text-lg font-bold text-cyan-400 capitalize">
                                {analysis?.analysis_source || 'unknown'}
                            </div>
                        </div>
                    </div>

                    {/* ML Analysis Details */}
                    {(isAnomaly || analysis?.anomaly_score !== undefined) && (
                        <div className="bg-yellow-900/20 p-5 rounded-lg border border-yellow-500/30">
                            <h3 className="text-sm font-semibold text-yellow-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                                <Bot className="w-4 h-4" /> Machine Learning Analysis
                            </h3>
                            <div className="grid grid-cols-2 gap-4 text-sm">
                                <div>
                                    <div className="text-slate-500">Anomaly Status</div>
                                    <div className={`font-bold ${analysis?.is_anomaly ? 'text-yellow-400' : 'text-green-400'}`}>
                                        {analysis?.is_anomaly ? 'ANOMALOUS BEHAVIOR' : 'Normal'}
                                    </div>
                                </div>
                                <div>
                                    <div className="text-slate-500">Anomaly Score</div>
                                    <div className="text-yellow-400 font-mono">
                                        {analysis?.anomaly_score?.toFixed(4) || '0.0000'}
                                    </div>
                                </div>
                            </div>
                            <p className="text-slate-400 text-sm mt-3">
                                {analysis?.is_anomaly 
                                    ? `The local ML model detected unusual network behavior for ${domain}. Score below -0.1 indicates potential threat.`
                                    : `The domain shows normal network behavior patterns consistent with legitimate traffic.`
                                }
                            </p>
                        </div>
                    )}

                    {/* AdGuard Metadata */}
                    {analysis?.adguard_metadata && (
                        <div className="bg-slate-800/50 p-5 rounded-lg border border-slate-700">
                            <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                                <Shield className="w-4 h-4" /> AdGuard Details
                            </h3>
                            <div className="grid grid-cols-2 gap-3 text-sm">
                                {analysis.adguard_metadata.reason && (
                                    <div>
                                        <div className="text-slate-500">Reason</div>
                                        <div className="text-slate-200 font-mono">{analysis.adguard_metadata.reason}</div>
                                    </div>
                                )}
                                {analysis.adguard_metadata.filter_id && (
                                    <div>
                                        <div className="text-slate-500">Filter ID</div>
                                        <div className="text-slate-200 font-mono">{analysis.adguard_metadata.filter_id}</div>
                                    </div>
                                )}
                                {analysis.adguard_metadata.client && (
                                    <div>
                                        <div className="text-slate-500">Client IP</div>
                                        <div className="text-slate-200 font-mono">{analysis.adguard_metadata.client}</div>
                                    </div>
                                )}
                                {analysis.adguard_metadata.rule && (
                                    <div className="col-span-2">
                                        <div className="text-slate-500">Rule</div>
                                        <div className="text-slate-200 font-mono text-xs bg-slate-900 p-2 rounded break-all">
                                            {analysis.adguard_metadata.rule}
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                    )}

                    {/* Why Assessment */}
                    <div className={`p-5 rounded-lg border ${
                        isSafe ? 'bg-green-900/20 border-green-500/30' :
                        isAnomaly ? 'bg-yellow-900/20 border-yellow-500/30' :
                        isBlocked ? 'bg-red-900/20 border-red-500/30' :
                        'bg-cyan-900/20 border-cyan-500/30'
                    }`}>
                        <h3 className="text-sm font-semibold mb-2 flex items-center gap-2">
                            {isSafe ? (
                                <>
                                    <CheckCircle className="w-4 h-4 text-green-400" />
                                    <span className="text-green-400">WHY THIS IS SAFE</span>
                                </>
                            ) : isAnomaly ? (
                                <>
                                    <Bot className="w-4 h-4 text-yellow-400" />
                                    <span className="text-yellow-400">BEHAVIORAL ANALYSIS</span>
                                </>
                            ) : isBlocked ? (
                                <>
                                    <AlertTriangle className="w-4 h-4 text-red-400" />
                                    <span className="text-red-400">WHY IT WAS BLOCKED</span>
                                </>
                            ) : (
                                <>
                                    <Shield className="w-4 h-4 text-cyan-400" />
                                    <span className="text-cyan-400">ANALYSIS RESULT</span>
                                </>
                            )}
                        </h3>
                        <div className="text-slate-300 text-sm space-y-2">
                            {isSafe ? (
                                <>
                                    <p>This domain (<strong>{domain}</strong>) was analyzed and classified as <strong>SAFE</strong>.</p>
                                    <p>• Entropy score: {entropyValue.toFixed(2)} (normal/random)</p>
                                    <p>• No blocking rules triggered</p>
                                    <p>• Analysis source: {analysis?.analysis_source || 'local heuristics'}</p>
                                </>
                            ) : isAnomaly ? (
                                <>
                                    <p>The ML model detected <strong>unusual network behavior</strong> for <strong>{domain}</strong>.</p>
                                    <p>• Anomaly score: {analysis?.anomaly_score?.toFixed(4)}</p>
                                    <p>• This could indicate suspicious activity or may be a false positive.</p>
                                    <p>• Manual review recommended.</p>
                                </>
                            ) : isBlocked ? (
                                <>
                                    <p>This domain was <strong>BLOCKED</strong> by AdGuard.</p>
                                    <p>• Reason: {analysis?.adguard_metadata?.reason || 'Blocked by filter'}</p>
                                    {analysis?.adguard_metadata?.rule && (
                                        <p>• Rule: {analysis.adguard_metadata.rule}</p>
                                    )}
                                </>
                            ) : (
                                <>
                                    <p>Domain <strong>{domain}</strong> has been analyzed.</p>
                                    <p>• Category: {analysis?.category || 'Unknown'}</p>
                                    <p>• Risk Score: {analysis?.risk_score || 'Unknown'}</p>
                                </>
                            )}
                        </div>
                    </div>

                    {/* Timestamp */}
                    <div className="text-xs text-slate-500 text-center pt-2">
                        Analysis completed: {analysis?.timestamp ? new Date(analysis.timestamp).toLocaleString() : 'Unknown'}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default AnalysisModal;
