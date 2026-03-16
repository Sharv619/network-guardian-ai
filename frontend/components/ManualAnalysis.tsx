import React, { useState, useEffect } from 'react';
import { 
  Database, 
  FileText, 
  Shield, 
  Brain, 
  Wifi, 
  Globe, 
  TrendingUp, 
  AlertTriangle, 
  Clock, 
  Eye, 
  Thermometer, 
  BarChart3, 
  Zap, 
  Target, 
  Network, 
  Lock, 
  Activity, 
  Cpu, 
  Code 
} from 'lucide-react';

interface ManualAnalysisProps {
  selectedModel: string;
  selectedDomainFromLiveFeed?: any; // Allow passing a specific domain from live feed
}

const ManualAnalysis: React.FC<ManualAnalysisProps> = ({ selectedModel, selectedDomainFromLiveFeed }) => {
  const [selectedSession, setSelectedSession] = useState<string | null>(null);
  const [sessionData, setSessionData] = useState<any[]>([]);

  // Update session data when selectedDomainFromLiveFeed changes
  useEffect(() => {
    if (selectedDomainFromLiveFeed) {
      setSessionData([{
        id: `session-${Date.now()}`,
        domain: selectedDomainFromLiveFeed.domain,
        timestamp: selectedDomainFromLiveFeed.timestamp,
        riskScore: selectedDomainFromLiveFeed.risk_score || 'Unknown',
        category: selectedDomainFromLiveFeed.category || 'Unknown',
        summary: selectedDomainFromLiveFeed.summary,
        isAnomaly: selectedDomainFromLiveFeed.is_anomaly || false,
        anomalyScore: selectedDomainFromLiveFeed.anomaly_score || 0,
        entropy: selectedDomainFromLiveFeed.entropy || 0,
        hasSimilarityMatch: selectedDomainFromLiveFeed.has_similarity_match || false,
        adguardMetadata: selectedDomainFromLiveFeed.adguard_metadata || {},
        analysisSource: selectedDomainFromLiveFeed.analysis_source || 'unknown'
      }]);
      setSelectedSession(`session-${Date.now()}`);
    }
  }, [selectedDomainFromLiveFeed]);

  // If no domain from live feed, use mock data
  useEffect(() => {
    if (!selectedDomainFromLiveFeed && sessionData.length === 0) {
      const mockSessions = [
        {
          id: 'session-1',
          domain: 'malicious.example.com',
          timestamp: '2024-02-10 14:30:00',
          riskScore: 'High',
          category: 'Malware',
          summary: 'Gemini AI detected malicious payload. 🛡️ LOCAL ANALYSIS confirms threat.',
          isAnomaly: true,
          anomalyScore: 0.85,
          entropy: 4.2,
          adguardMetadata: {
            reason: 'Blocked by user filter',
            rule: '||malicious.example.com^',
            filterId: 1
          }
        },
        {
          id: 'session-2',
          domain: 'tracker.adservice.com',
          timestamp: '2024-02-10 14:25:00',
          riskScore: 'Medium',
          category: 'Tracker',
          summary: 'AdGuard blocked tracking request.',
          isAnomaly: false,
          entropy: 2.1,
          adguardMetadata: {
            reason: 'Blocked by AdGuard DNS filter',
            rule: '||adservice.com^',
            filterId: 2
          }
        }
      ];
      setSessionData(mockSessions);
    }
  }, [selectedDomainFromLiveFeed, sessionData.length]);

  const ForensicMetadata = ({ session }: { session: any }) => (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      <div className="bg-slate-800 p-4 rounded-lg border border-slate-700">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-slate-400">Entropy Score</span>
          <Thermometer className="w-4 h-4 text-blue-400" />
        </div>
        <div className="text-2xl font-bold text-white">{session.entropy?.toFixed(2) || 'N/A'}</div>
        <div className="text-xs text-slate-500">Domain complexity analysis</div>
      </div>

      <div className="bg-slate-800 p-4 rounded-lg border border-slate-700">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-slate-400">Anomaly Score</span>
          <Brain className="w-4 h-4 text-yellow-400" />
        </div>
        <div className="text-2xl font-bold text-yellow-400">{session.anomalyScore?.toFixed(2) || 'N/A'}</div>
        <div className="text-xs text-slate-500">ML detection confidence</div>
      </div>

      <div className="bg-slate-800 p-4 rounded-lg border border-slate-700">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-slate-400">AdGuard Status</span>
          <Wifi className="w-4 h-4 text-orange-400" />
        </div>
        <div className="text-2xl font-bold text-orange-400">
          {session.adguardMetadata ? 'BLOCKED' : 'ALLOWED'}
        </div>
        <div className="text-xs text-slate-500">DNS filtering result</div>
      </div>

      <div className="bg-slate-800 p-4 rounded-lg border border-slate-700">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-slate-400">Analysis Source</span>
          <Globe className="w-4 h-4 text-purple-400" />
        </div>
        <div className="text-2xl font-bold text-purple-400 capitalize">{session.analysisSource || 'unknown'}</div>
        <div className="text-xs text-slate-500">Method used for analysis</div>
      </div>
    </div>
  );

  // Vector Embedding Visualization Component
  const VectorEmbeddingVisualizer = ({ session }: { session: any }) => {
    // Convert entropy and other numeric values to binary representation
    const entropyBinary = (session.entropy || 0).toString(2).replace('.', '');
    const anomalyScoreBinary = (session.anomalyScore || 0).toString(2).replace('.', '');
    
    return (
      <div className="bg-slate-800 p-4 rounded-lg border border-slate-700">
        <div className="flex items-center justify-between mb-4">
          <h4 className="text-lg font-semibold text-white">Vector Embedding Data</h4>
          <Activity className="w-5 h-5 text-cyan-400" />
        </div>
        
        <div className="space-y-4">
          <div>
            <div className="flex justify-between text-sm mb-2">
              <span className="text-slate-400">Entropy Binary Representation</span>
              <span className="text-slate-400">Length: {entropyBinary.length}</span>
            </div>
            <div className="bg-slate-900 p-3 rounded border border-slate-600 font-mono text-sm overflow-x-auto">
              {entropyBinary.substring(0, 64)}{entropyBinary.length > 64 ? '...' : ''}
            </div>
          </div>
          
          <div>
            <div className="flex justify-between text-sm mb-2">
              <span className="text-slate-400">Anomaly Score Binary</span>
              <span className="text-slate-400">Length: {anomalyScoreBinary.length}</span>
            </div>
            <div className="bg-slate-900 p-3 rounded border border-slate-600 font-mono text-sm overflow-x-auto">
              {anomalyScoreBinary.substring(0, 64)}{anomalyScoreBinary.length > 64 ? '...' : ''}
            </div>
          </div>
          
          <div className="grid grid-cols-2 gap-4 mt-4">
            <div className="bg-slate-900 p-3 rounded border border-slate-600">
              <div className="text-xs text-slate-400 mb-1">Similarity Match</div>
              <div className={`text-lg font-bold ${session.hasSimilarityMatch ? 'text-green-400' : 'text-orange-400'}`}>
                {session.hasSimilarityMatch ? 'YES' : 'NO'}
              </div>
            </div>
            <div className="bg-slate-900 p-3 rounded border border-slate-600">
              <div className="text-xs text-slate-400 mb-1">Embedding Size</div>
              <div className="text-lg font-bold text-cyan-400">
                {session.entropy ? Math.floor((session.entropy || 0) * 100) : 0} bits
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Manual Analysis</h1>
          <p className="text-sm text-slate-400">Session research and forensic metadata</p>
        </div>
        <div className="flex items-center space-x-4 text-sm text-slate-400">
          <span className="flex items-center space-x-1">
            <Database className="w-4 h-4" />
            <span>Session Research</span>
          </span>
          <span className="flex items-center space-x-1">
            <FileText className="w-4 h-4" />
            <span>Forensic Analysis</span>
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Session List */}
        <div className="lg:col-span-1">
          <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
            <h3 className="text-lg font-semibold text-white mb-4">Session Research</h3>
            <div className="space-y-3">
              {sessionData.map((session) => (
                <div
                  key={session.id}
                  onClick={() => setSelectedSession(session.id)}
                  className={`p-3 rounded-lg border cursor-pointer transition-all ${
                    selectedSession === session.id
                      ? 'border-cyan-500 bg-cyan-900/20'
                      : 'border-slate-700 hover:border-slate-600'
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-white truncate">{session.domain}</span>
                    <span className={`px-2 py-1 rounded text-xs font-bold ${
                      session.riskScore === 'High' ? 'bg-red-900/50 text-red-400' :
                      session.riskScore === 'Medium' ? 'bg-orange-900/50 text-orange-400' :
                      session.riskScore === 'Low' ? 'bg-green-900/50 text-green-400' :
                      'bg-slate-700 text-slate-300'
                    }`}>
                      {session.riskScore}
                    </span>
                  </div>
                  <div className="text-xs text-slate-400">{session.timestamp}</div>
                  <div className="text-xs text-slate-500 mt-1">{session.category}</div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Forensic Details */}
        <div className="lg:col-span-2">
          <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
            <h3 className="text-lg font-semibold text-white mb-4">Forensic Metadata</h3>
            
            {selectedSession ? (
              (() => {
                const session = sessionData.find(s => s.id === selectedSession);
                return session ? (
                  <>
                    <ForensicMetadata session={session} />
                    
                    {/* Vector Embedding Data Section */}
                    <VectorEmbeddingVisualizer session={session} />
                    
                    <div className="space-y-4 mt-6">
                      <div className="bg-slate-700 p-4 rounded-lg">
                        <h4 className="font-semibold text-white mb-2">Threat Summary</h4>
                        <p className="text-slate-300 text-sm">{session.summary}</p>
                      </div>
                      
                      {session.adguardMetadata && (
                        <div className="bg-slate-700 p-4 rounded-lg">
                          <h4 className="font-semibold text-white mb-2">AdGuard Analysis</h4>
                          <div className="grid grid-cols-2 gap-2 text-sm">
                            <div>
                              <span className="text-slate-400">Reason:</span>
                              <span className="ml-2 text-white">{session.adguardMetadata.reason}</span>
                            </div>
                            <div>
                              <span className="text-slate-400">Rule:</span>
                              <span className="ml-2 text-white">{session.adguardMetadata.rule}</span>
                            </div>
                            <div>
                              <span className="text-slate-400">Filter ID:</span>
                              <span className="ml-2 text-white">{session.adguardMetadata.filterId}</span>
                            </div>
                            <div>
                              <span className="text-slate-400">Client:</span>
                              <span className="ml-2 text-white">{session.adguardMetadata.client}</span>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  </>
                ) : (
                  <div className="text-center text-slate-400 py-8">
                    Select a session to view forensic details
                  </div>
                );
              })()
            ) : (
              <div className="text-center text-slate-400 py-8">
                Select a session from the list to view forensic metadata
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ManualAnalysis;