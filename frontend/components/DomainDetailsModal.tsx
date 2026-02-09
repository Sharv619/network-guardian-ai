import React from 'react';
import { Eye as EyeIcon, X, Globe, Shield, AlertTriangle, Brain, Database, Thermometer, TrendingUp } from 'lucide-react';

interface DomainDetailsModalProps {
  domain: string;
  isOpen: boolean;
  onClose: () => void;
  backendData: {
    autonomy_score?: number;
    local_decisions?: number;
    cloud_decisions?: number;
    classifier?: {
      total_patterns?: number;
      category_distribution?: Record<string, number>;
      confidence_distribution?: Record<string, number>;
    };
    cache?: {
      memory_cache_size?: number;
      valid_memory_entries?: number;
      disk_cache_exists?: boolean;
      cache_file_size?: number;
    };
    patterns_learned?: number;
    seed_patterns?: number;
    learned_patterns?: number;
    system_usage?: {
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
  };
}

const DomainDetailsModal: React.FC<DomainDetailsModalProps> = ({ 
  domain, 
  isOpen, 
  onClose, 
  backendData 
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-slate-800 border border-slate-700 rounded-lg shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden">
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
            className="p-2 hover:bg-slate-700 rounded-full transition-colors"
          >
            <X className="w-6 h-6 text-slate-400" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6 overflow-y-auto max-h-[calc(90vh-120px)]">
          {/* System Intelligence Section */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-slate-900/50 p-6 rounded-lg border border-slate-700">
              <h3 className="text-lg font-semibold text-white mb-4 flex items-center space-x-2">
                <Brain className="w-5 h-5 text-purple-400" />
                <span>System Intelligence</span>
              </h3>
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-slate-300">Autonomy Score</span>
                  <span className="text-2xl font-bold text-purple-400 font-mono">
                    {backendData?.autonomy_score || 0}%
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-300">Local Decisions</span>
                  <span className="text-lg font-bold text-cyan-400 font-mono">
                    {backendData?.local_decisions || 0}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-300">Cloud Decisions</span>
                  <span className="text-lg font-bold text-green-400 font-mono">
                    {backendData?.cloud_decisions || 0}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-300">Total Patterns</span>
                  <span className="text-lg font-bold text-yellow-400 font-mono">
                    {backendData?.classifier?.total_patterns || 0}
                  </span>
                </div>
              </div>
            </div>

            <div className="bg-slate-900/50 p-6 rounded-lg border border-slate-700">
              <h3 className="text-lg font-semibold text-white mb-4 flex items-center space-x-2">
                <Database className="w-5 h-5 text-cyan-400" />
                <span>Cache Performance</span>
              </h3>
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-slate-300">Memory Cache Size</span>
                  <span className="text-lg font-bold text-cyan-400 font-mono">
                    {backendData?.cache?.memory_cache_size || 0}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-300">Valid Entries</span>
                  <span className="text-lg font-bold text-green-400 font-mono">
                    {backendData?.cache?.valid_memory_entries || 0}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-300">Disk Cache</span>
                  <span className={`text-sm font-mono px-2 py-1 rounded border ${
                    backendData?.cache?.disk_cache_exists 
                      ? 'bg-green-900/50 text-green-400 border-green-500/30' 
                      : 'bg-red-900/50 text-red-400 border-red-500/30'
                  }`}>
                    {backendData?.cache?.disk_cache_exists ? 'ENABLED' : 'DISABLED'}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-300">Cache File Size</span>
                  <span className="text-sm text-slate-400 font-mono">
                    {(backendData?.cache?.cache_file_size / 1024).toFixed(2) || '0.00'} KB
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* System Usage Details */}
          {backendData?.system_usage && (
            <div className="bg-slate-900/50 p-6 rounded-lg border border-slate-700">
              <h3 className="text-lg font-semibold text-white mb-4 flex items-center space-x-2">
                <Shield className="w-5 h-5 text-blue-400" />
                <span>System Usage Details</span>
              </h3>
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Active Integrations */}
                <div className="space-y-4">
                  <h4 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Active Integrations</h4>
                  {backendData.system_usage.active_integrations.map((integration, index) => (
                    <div key={index} className="bg-slate-800 p-3 rounded border border-slate-700">
                      <div className="flex justify-between items-start mb-1">
                        <span className="text-sm font-mono text-white">{integration.name}</span>
                        <span className={`text-xs px-2 py-1 rounded font-mono ${
                          integration.status === 'ACTIVE' 
                            ? 'bg-green-900/50 text-green-400 border border-green-500/30' 
                            : 'bg-red-900/50 text-red-400 border border-red-500/30'
                        }`}>
                          {integration.status}
                        </span>
                      </div>
                      <p className="text-xs text-slate-400">{integration.description}</p>
                    </div>
                  ))}
                </div>

                {/* Tracker Detection */}
                <div className="space-y-4">
                  <h4 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Tracker Detection</h4>
                  <div className="bg-slate-800 p-3 rounded border border-slate-700">
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-sm text-slate-300">Total Detected</span>
                      <span className="text-lg font-bold text-orange-400 font-mono">
                        {backendData.system_usage.tracker_detection.total_detected}
                      </span>
                    </div>
                    <div className="space-y-2">
                      {Object.entries(backendData.system_usage.tracker_detection.categories).map(([category, count]) => (
                        <div key={category} className="flex justify-between text-xs">
                          <span className="text-slate-400 capitalize">{category}</span>
                          <span className="text-white font-mono">{count}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="bg-slate-800 p-3 rounded border border-slate-700">
                    <h5 className="text-xs text-slate-300 mb-2">Detection Methods:</h5>
                    <ul className="text-xs text-slate-400 space-y-1">
                      {backendData.system_usage.tracker_detection.detection_methods.map((method, index) => (
                        <li key={index} className="flex items-center space-x-2">
                          <span className="w-1 h-1 bg-cyan-400 rounded-full"></span>
                          <span>{method}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>

                {/* Learning Progress */}
                <div className="space-y-4">
                  <h4 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Learning Progress</h4>
                  <div className="bg-slate-800 p-4 rounded border border-slate-700">
                    <div className="space-y-3">
                      <div className="flex justify-between text-sm">
                        <span className="text-slate-300">Seed Patterns</span>
                        <span className="font-bold text-blue-400 font-mono">
                          {backendData.system_usage.learning_progress.seed_patterns}
                        </span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-slate-300">Learned Patterns</span>
                        <span className="font-bold text-purple-400 font-mono">
                          {backendData.system_usage.learning_progress.learned_patterns}
                        </span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-slate-300">Learning Rate</span>
                        <span className="font-bold text-yellow-400 font-mono">
                          {backendData.system_usage.learning_progress.learning_rate}
                        </span>
                      </div>
                      <div className="mt-4 p-3 bg-gradient-to-r from-green-900/50 to-blue-900/50 rounded border border-green-500/30">
                        <div className="text-xs text-slate-300">Next Milestone</div>
                        <div className="text-sm font-bold text-green-400 font-mono">
                          {backendData.system_usage.learning_progress.next_milestone}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Pattern Analysis */}
          <div className="bg-slate-900/50 p-6 rounded-lg border border-slate-700">
            <h3 className="text-lg font-semibold text-white mb-4 flex items-center space-x-2">
              <TrendingUp className="w-5 h-5 text-yellow-400" />
              <span>Pattern Analysis</span>
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {Object.entries(backendData?.classifier?.category_distribution || {}).map(([category, count]) => (
                <div key={category} className="bg-slate-800 p-4 rounded border border-slate-600">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-sm text-slate-300 capitalize font-mono">{category}</span>
                    <span className="text-lg font-bold text-white font-mono">{count}</span>
                  </div>
                  <div className="w-full bg-slate-700 rounded-full h-2">
                    <div 
                      className="h-2 rounded-full transition-all duration-1000"
                      style={{ 
                        width: `${(count / (backendData?.classifier?.total_patterns || 1)) * 100}%`,
                        backgroundColor: category === 'System' ? '#3b82f6' : category === 'Tracker' ? '#f59e0b' : '#ef4444'
                      }}
                    ></div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Confidence Distribution */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-slate-900/50 p-6 rounded-lg border border-slate-700">
              <h3 className="text-lg font-semibold text-white mb-4 flex items-center space-x-2">
                <Thermometer className="w-5 h-5 text-green-400" />
                <span>Confidence Distribution</span>
              </h3>
              <div className="space-y-4">
                {Object.entries(backendData?.classifier?.confidence_distribution || {}).map(([confidence, count]) => (
                  <div key={confidence} className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="text-slate-300 capitalize">{confidence} Confidence</span>
                      <span className="font-bold text-white font-mono">{count}</span>
                    </div>
                    <div className="w-full bg-slate-700 rounded-full h-2">
                      <div 
                        className="h-2 rounded-full transition-all duration-1000"
                        style={{ 
                          width: `${(count / (backendData?.classifier?.total_patterns || 1)) * 100}%`,
                          backgroundColor: confidence === 'high' ? '#10b981' : confidence === 'medium' ? '#f59e0b' : '#ef4444'
                        }}
                      ></div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="bg-slate-900/50 p-6 rounded-lg border border-slate-700">
              <h3 className="text-lg font-semibold text-white mb-4 flex items-center space-x-2">
                <AlertTriangle className="w-5 h-5 text-orange-400" />
                <span>Learning Progress</span>
              </h3>
              <div className="space-y-6">
                <div>
                  <div className="flex justify-between text-sm mb-2">
                    <span className="text-slate-300">Patterns Learned</span>
                    <span className="font-bold text-yellow-400 font-mono">{backendData?.patterns_learned || 0}/5</span>
                  </div>
                  <div className="w-full bg-slate-700 rounded-full h-3">
                    <div 
                      className="h-3 bg-yellow-500 rounded-full transition-all duration-1000"
                      style={{ width: `${((backendData?.patterns_learned || 0) / 5) * 100}%` }}
                    ></div>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="text-center p-3 bg-slate-800 rounded border border-slate-600">
                    <div className="text-2xl font-bold text-blue-400 font-mono">{backendData?.seed_patterns || 0}</div>
                    <div className="text-xs text-slate-400">Seed Patterns</div>
                  </div>
                  <div className="text-center p-3 bg-slate-800 rounded border border-slate-600">
                    <div className="text-2xl font-bold text-purple-400 font-mono">{backendData?.learned_patterns || 0}</div>
                    <div className="text-xs text-slate-400">Learned Patterns</div>
                  </div>
                </div>

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
          <div className="bg-slate-900/50 p-6 rounded-lg border border-slate-700">
            <h3 className="text-lg font-semibold text-white mb-4 flex items-center space-x-2">
              <Shield className="w-5 h-5 text-red-400" />
              <span>System Overview</span>
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="bg-slate-800 p-4 rounded-lg border border-slate-700">
                <div className="flex items-center space-x-2 mb-2">
                  <Globe className="w-4 h-4 text-orange-400" />
                  <span className="text-sm text-slate-300">AdGuard Integration</span>
                </div>
                <div className="text-2xl font-bold text-orange-400">ACTIVE</div>
                <div className="text-xs text-slate-500">DNS filtering integrated</div>
              </div>
              <div className="bg-slate-800 p-4 rounded-lg border border-slate-700">
                <div className="flex items-center space-x-2 mb-2">
                  <Brain className="w-4 h-4 text-purple-400" />
                  <span className="text-sm text-slate-300">Gemini AI Analysis</span>
                </div>
                <div className="text-2xl font-bold text-purple-400">ACTIVE</div>
                <div className="text-xs text-slate-500">Threat analysis running</div>
              </div>
              <div className="bg-slate-800 p-4 rounded-lg border border-slate-700">
                <div className="flex items-center space-x-2 mb-2">
                  <Database className="w-4 h-4 text-green-400" />
                  <span className="text-sm text-slate-300">Local ML Detection</span>
                </div>
                <div className="text-2xl font-bold text-green-400">ACTIVE</div>
                <div className="text-xs text-slate-500">Pattern detection online</div>
              </div>
              <div className="bg-slate-800 p-4 rounded-lg border border-slate-700">
                <div className="flex items-center space-x-2 mb-2">
                  <Shield className="w-4 h-4 text-red-400" />
                  <span className="text-sm text-slate-300">Threat Protection</span>
                </div>
                <div className="text-2xl font-bold text-red-400 font-mono">{backendData?.classifier?.total_patterns || 0}</div>
                <div className="text-xs text-slate-500">Active protections</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DomainDetailsModal;