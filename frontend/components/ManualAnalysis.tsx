import React, { useState } from 'react';
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
}

const ManualAnalysis: React.FC<ManualAnalysisProps> = ({ selectedModel }) => {
  const [selectedSession, setSelectedSession] = useState<string | null>(null);

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
      adguardMetadata: {
        reason: 'Blocked by AdGuard DNS filter',
        rule: '||adservice.com^',
        filterId: 2
      }
    }
  ];

  const ForensicMetadata = ({ session }: { session: any }) => (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      <div className="bg-slate-800 p-4 rounded-lg border border-slate-700">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-slate-400">Entropy Score</span>
          <Thermometer className="w-4 h-4 text-blue-400" />
        </div>
        <div className="text-2xl font-bold text-white">{session.anomalyScore?.toFixed(2) || 'N/A'}</div>
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
          <span className="text-sm text-slate-400">AI Analysis</span>
          <Globe className="w-4 h-4 text-purple-400" />
        </div>
        <div className="text-2xl font-bold text-purple-400">ACTIVE</div>
        <div className="text-xs text-slate-500">Gemini threat assessment</div>
      </div>
    </div>
  );

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
              {mockSessions.map((session) => (
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
                    <span className="text-sm font-medium text-white">{session.domain}</span>
                    <span className={`px-2 py-1 rounded text-xs font-bold ${
                      session.riskScore === 'High' ? 'bg-red-900/50 text-red-400' :
                      session.riskScore === 'Medium' ? 'bg-orange-900/50 text-orange-400' :
                      'bg-green-900/50 text-green-400'
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
                const session = mockSessions.find(s => s.id === selectedSession);
                return session ? (
                  <>
                    <ForensicMetadata session={session} />
                    <div className="space-y-4">
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