import React, { useState, useEffect } from 'react';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Area,
  AreaChart,
} from 'recharts';
import { SystemStats, AlertStats, MLDashboard } from '../types';
import LoadingSpinner from './LoadingSpinner';
import {
  Activity,
  Shield,
  Brain,
  Database,
  AlertTriangle,
  TrendingUp,
  BarChart3,
  PieChart as PieChartIcon,
  Zap,
  Target,
  Eye,
  Settings,
  Bell,
  Key,
  Info,
} from 'lucide-react';

const API_BASE = '';

interface StatsPanelProps {
  selectedModel?: string;
}

const COLORS = {
  primary: '#06b6d4',
  secondary: '#8b5cf6',
  success: '#22c55e',
  warning: '#f59e0b',
  danger: '#ef4444',
  info: '#3b82f6',
  slate: '#64748b',
};

const StatsPanel: React.FC<StatsPanelProps> = () => {
  const [activeTab, setActiveTab] = useState<'overview' | 'ml' | 'alerts' | 'settings'>('overview');
  const [systemStats, setSystemStats] = useState<SystemStats | null>(null);
  const [alertStats, setAlertStats] = useState<AlertStats | null>(null);
  const [mlDashboard, setMlDashboard] = useState<MLDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [history, setHistory] = useState<any[]>([]);

  const fetchAllData = async () => {
    try {
      const [statsRes, alertsRes, mlRes, historyRes] = await Promise.all([
        fetch(`${API_BASE}/api/stats/system`),
        fetch(`${API_BASE}/alerts/stats`),
        fetch(`${API_BASE}/ml/dashboard`),  // Changed from /api/stats/ml/dashboard to /ml/dashboard
        fetch(`${API_BASE}/history`),
      ]);

      if (statsRes.ok) {
        const statsData = await statsRes.json();
        // Ensure all required fields exist with defaults
        setSystemStats({
          autonomy_score: statsData.autonomy_score || 0,
          local_decisions: statsData.local_decisions || 0,
          cloud_decisions: statsData.cloud_decisions || 0,
          total_decisions: statsData.total_decisions || 0,
          patterns_learned: statsData.patterns_learned || 0,
          seed_patterns: statsData.seed_patterns || 0,
          learned_patterns: statsData.learned_patterns || 0,
          classifier: statsData.classifier || { total_patterns: 0, category_distribution: {}, confidence_distribution: {} },
          cache: statsData.cache || { memory_cache_size: 0, valid_memory_entries: 0, disk_cache_exists: false, source_distribution: {}, cache_file_size: 0 },
          realtime_stats: statsData.realtime_stats || { autonomy_score: 0, local_decisions: 0, cloud_decisions: 0, total_decisions: 0, patterns_learned: 0, seed_patterns: 0, learned_patterns: 0 },
          entropy: statsData.entropy || { total_analyzed: 0, avg_entropy: 0, high_entropy_count: 0, low_entropy_count: 0, max_entropy: 0, min_entropy: 0 },
          anomaly: statsData.anomaly || { is_trained: false, total_samples: 0, min_samples_required: 0, anomalies_detected: 0, anomaly_rate: 0, recent_scores: [] },
          system_usage: statsData.system_usage || { active_integrations: [], tracker_detection: { total_detected: 0, categories: {}, detection_methods: [] } }
        });
      }
      
      if (alertsRes.ok) {
        const alertsData = await alertsRes.json();
        setAlertStats({
          total_alerts: alertsData.total_alerts || 0,
          critical_alerts: alertsData.critical_alerts || 0,
          high_alerts: alertsData.high_alerts || 0,
          medium_alerts: alertsData.medium_alerts || 0,
          low_alerts: alertsData.low_alerts || 0,
          resolved_alerts: alertsData.resolved_alerts || 0,
          pending_alerts: alertsData.pending_alerts || 0,
          acknowledged: alertsData.acknowledged || 0,
          alert_rate: alertsData.alert_rate || 0,
          current_threat_rate: alertsData.current_threat_rate || 0,
          current_anomaly_rate: alertsData.current_anomaly_rate || 0,
          by_severity: alertsData.by_severity || { high: 0, medium: 0, low: 0 },
          top_threats: alertsData.top_threats || []
        });
      }
      
      if (mlRes.ok) {
        const mlData = await mlRes.json();
        setMlDashboard({
          overview: {
            overall_accuracy: mlData.overview?.overall_accuracy || 0,
            total_analyzed: mlData.overview?.total_analyzed || 0,
            anomalies_detected: mlData.overview?.anomalies_detected || 0,
            false_positives: mlData.overview?.false_positives || 0,
            false_negatives: mlData.overview?.false_negatives || 0,
          },
          feedback: {
            total_feedback: mlData.feedback?.total_feedback || 0,
            correct_predictions: mlData.feedback?.correct_predictions || 0,
            false_positives: mlData.feedback?.false_positives || 0,
            false_negatives: mlData.feedback?.false_negatives || 0,
          },
          thresholds: {
            entropy_threshold: mlData.thresholds?.entropy_threshold || 0,
            anomaly_threshold: mlData.thresholds?.anomaly_threshold || 0,
          },
          features: {
            tld_tracked: mlData.features?.tld_tracked || 0,
            domain_patterns: mlData.features?.domain_patterns || 0,
          },
          entropy_distribution: mlData.entropy_distribution || { high: 0, medium: 0, low: 0 },
          learning_progress: mlData.learning_progress || { patterns_learned: 0, total_patterns: 0, progress_percentage: 0 },
          model_performance: mlData.model_performance || { precision: 0, recall: 0, f1_score: 0, accuracy: 0 },
          feature_importance: mlData.feature_importance || []
        });
      }
      
      if (historyRes.ok) setHistory(await historyRes.json());
    } catch (e) {
      console.error('Failed to fetch stats', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAllData();
    const interval = setInterval(fetchAllData, 5000);
    return () => clearInterval(interval);
  }, []);

  if (loading) return <LoadingSpinner />;

  // Prepare chart data
  const categoryData = systemStats?.classifier?.category_distribution
    ? Object.entries(systemStats.classifier.category_distribution).map(([name, value]) => ({
        name,
        value,
      }))
    : [];

  const alertSeverityData = alertStats?.by_severity
    ? Object.entries(alertStats.by_severity).map(([name, value]) => ({
        name: name.toUpperCase(),
        value,
      }))
    : [];

  // Mock time-series data for demo (in real app, backend would provide this)
  const trendData = [
    { time: '1m', threats: 12, anomalies: 3, safe: 45 },
    { time: '5m', threats: 18, anomalies: 5, safe: 52 },
    { time: '10m', threats: 15, anomalies: 4, safe: 48 },
    { time: '15m', threats: 22, anomalies: 7, safe: 61 },
    { time: '20m', threats: 19, anomalies: 6, safe: 55 },
  ];

  const riskDistribution = [
    { name: 'High', value: history.filter((h) => h.risk_score === 'High').length || 15, color: COLORS.danger },
    { name: 'Medium', value: history.filter((h) => h.risk_score === 'Medium').length || 25, color: COLORS.warning },
    { name: 'Low', value: history.filter((h) => h.risk_score === 'Low').length || 60, color: COLORS.success },
  ];

  const renderOverview = () => (
    <div className="space-y-6">
      {/* Key Metrics Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard
          icon={<Activity className="w-6 h-6" />}
          label="Total Decisions"
          value={systemStats?.total_decisions || 0}
          subtext="Analyzed domains"
          color="cyan"
        />
        <MetricCard
          icon={<Zap className="w-6 h-6" />}
          label="Autonomy Score"
          value={`${systemStats?.autonomy_score || 0}%`}
          subtext="Local analysis rate"
          color="purple"
        />
        <MetricCard
          icon={<Brain className="w-6 h-6" />}
          label="Patterns Learned"
          value={systemStats?.learned_patterns || 0}
          subtext="ML model patterns"
          color="yellow"
        />
        <MetricCard
          icon={<AlertTriangle className="w-6 h-6" />}
          label="Active Alerts"
          value={alertStats?.pending_alerts || 0}
          subtext="Pending alerts"
          color="red"
        />
      </div>

      {/* Vector Memory & Anomaly Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard
          icon={<Database className="w-6 h-6" />}
          label="Vector Embeddings"
          value={systemStats?.vector_memory?.total_embeddings || 0}
          subtext="Threat embeddings stored"
          color="blue"
        />
        <MetricCard
          icon={<Target className="w-6 h-6" />}
          label="Anomaly Model"
          value={systemStats?.anomaly_engine?.is_trained ? 'Trained' : 'Training'}
          subtext={`${systemStats?.anomaly_engine?.training_samples || 0} samples`}
          color={systemStats?.anomaly_engine?.is_trained ? 'green' : 'yellow'}
        />
        <MetricCard
          icon={<Activity className="w-6 h-6" />}
          label="Entropy Threshold"
          value={(systemStats?.adaptive_thresholds?.entropy_threshold || 0).toFixed(2)}
          subtext="Dynamic threshold"
          color="yellow"
        />
        <MetricCard
          icon={<Shield className="w-6 h-6" />}
          label="Total Decisions"
          value={systemStats?.total_decisions || 0}
          subtext="Domains analyzed"
          color="cyan"
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Trend Chart */}
        <div className="bg-slate-800 p-4 rounded-lg border border-slate-700">
          <h4 className="text-sm font-mono text-slate-400 uppercase mb-4 flex items-center">
            <TrendingUp className="w-4 h-4 mr-2" /> Activity Trend (Real-time)
          </h4>
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={trendData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="time" stroke="#64748b" fontSize={12} />
              <YAxis stroke="#64748b" fontSize={12} />
              <Tooltip
                contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }}
                labelStyle={{ color: '#94a3b8' }}
              />
              <Area type="monotone" dataKey="threats" stackId="1" stroke={COLORS.danger} fill={COLORS.danger} fillOpacity={0.3} name="Threats" />
              <Area type="monotone" dataKey="anomalies" stackId="1" stroke={COLORS.warning} fill={COLORS.warning} fillOpacity={0.3} name="Anomalies" />
              <Area type="monotone" dataKey="safe" stackId="1" stroke={COLORS.success} fill={COLORS.success} fillOpacity={0.3} name="Safe" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Category Distribution */}
        <div className="bg-slate-800 p-4 rounded-lg border border-slate-700">
          <h4 className="text-sm font-mono text-slate-400 uppercase mb-4 flex items-center">
            <PieChartIcon className="w-4 h-4 mr-2" /> Category Distribution
          </h4>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie
                data={categoryData}
                cx="50%"
                cy="50%"
                innerRadius={40}
                outerRadius={70}
                paddingAngle={2}
                dataKey="value"
                label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                labelLine={false}
              >
                {categoryData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={Object.values(COLORS)[index % Object.values(COLORS).length]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Risk Distribution */}
      <div className="bg-slate-800 p-4 rounded-lg border border-slate-700">
        <h4 className="text-sm font-mono text-slate-400 uppercase mb-4 flex items-center">
          <Shield className="w-4 h-4 mr-2" /> Risk Score Distribution
        </h4>
        <ResponsiveContainer width="100%" height={150}>
          <BarChart data={riskDistribution} layout="vertical">
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis type="number" stroke="#64748b" fontSize={12} />
            <YAxis dataKey="name" type="category" stroke="#64748b" fontSize={12} width={60} />
            <Tooltip
              contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }}
            />
            <Bar dataKey="value" radius={[0, 4, 4, 0]}>
              {riskDistribution.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );

  const renderML = () => (
    <div className="space-y-6">
      {/* ML Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard
          icon={<Target className="w-6 h-6" />}
          label="Accuracy"
          value={`${(mlDashboard?.overview?.overall_accuracy || 0).toFixed(1)}%`}
          subtext="Model accuracy"
          color="green"
        />
        <MetricCard
          icon={<Brain className="w-6 h-6" />}
          label="Feedback"
          value={mlDashboard?.feedback?.total_feedback || 0}
          subtext="User corrections"
          color="blue"
        />
        <MetricCard
          icon={<Zap className="w-6 h-6" />}
          label="Entropy Threshold"
          value={(mlDashboard?.thresholds?.entropy_threshold || 0).toFixed(2)}
          subtext="Dynamic threshold"
          color="yellow"
        />
        <MetricCard
          icon={<Database className="w-6 h-6" />}
          label="TLDs Tracked"
          value={mlDashboard?.features?.tld_tracked || 0}
          subtext="Top-level domains"
          color="purple"
        />
      </div>

      {/* ML Charts */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-slate-800 p-4 rounded-lg border border-slate-700">
          <h4 className="text-sm font-mono text-slate-400 uppercase mb-4">Feedback Breakdown</h4>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie
                data={[
                  { name: 'Correct', value: mlDashboard?.feedback?.correct_predictions || 0, color: COLORS.success },
                  { name: 'False Pos', value: mlDashboard?.feedback?.false_positives || 0, color: COLORS.warning },
                  { name: 'False Neg', value: mlDashboard?.feedback?.false_negatives || 0, color: COLORS.danger },
                ]}
                cx="50%"
                cy="50%"
                innerRadius={40}
                outerRadius={70}
                paddingAngle={2}
                dataKey="value"
              >
                {[
                  { name: 'Correct', value: mlDashboard?.feedback?.correct_predictions || 0, color: COLORS.success },
                  { name: 'False Pos', value: mlDashboard?.feedback?.false_positives || 0, color: COLORS.warning },
                  { name: 'False Neg', value: mlDashboard?.feedback?.false_negatives || 0, color: COLORS.danger },
                ].map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }} />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-slate-800 p-4 rounded-lg border border-slate-700">
          <h4 className="text-sm font-mono text-slate-400 uppercase mb-4">Detection Sources</h4>
          <div className="space-y-4">
            {Object.entries(systemStats?.cache?.source_distribution || {}).map(([source, count]: [string, any]) => (
              <div key={source} className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-slate-300 capitalize">{source}</span>
                  <span className="font-bold text-white">{count}</span>
                </div>
                <div className="w-full bg-slate-700 rounded-full h-2">
                  <div
                    className="bg-cyan-500 h-2 rounded-full"
                    style={{ width: `${(count / (systemStats?.total_decisions || 1)) * 100}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );

  const renderAlerts = () => (
    <div className="space-y-6">
      {/* Alert Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard
          icon={<AlertTriangle className="w-6 h-6" />}
          label="Total Alerts"
          value={alertStats?.total_alerts || 0}
          subtext="All time"
          color="red"
        />
        <MetricCard
          icon={<Eye className="w-6 h-6" />}
          label="Acknowledged"
          value={alertStats?.acknowledged || 0}
          subtext="Reviewed"
          color="green"
        />
        <MetricCard
          icon={<Activity className="w-6 h-6" />}
          label="Threat Rate"
          value={alertStats?.current_threat_rate || 0}
          subtext="Per minute"
          color="yellow"
        />
        <MetricCard
          icon={<Shield className="w-6 h-6" />}
          label="Anomaly Rate"
          value={alertStats?.current_anomaly_rate || 0}
          subtext="Per minute"
          color="purple"
        />
      </div>

      {/* Alert Severity Distribution */}
      <div className="bg-slate-800 p-4 rounded-lg border border-slate-700">
        <h4 className="text-sm font-mono text-slate-400 uppercase mb-4">Alert Severity Distribution</h4>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={alertSeverityData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="name" stroke="#64748b" fontSize={12} />
            <YAxis stroke="#64748b" fontSize={12} />
            <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }} />
            <Bar dataKey="value" radius={[4, 4, 0, 0]}>
              {alertSeverityData.map((entry, index) => {
                const colors: Record<string, string> = { HIGH: COLORS.danger, MEDIUM: COLORS.warning, LOW: COLORS.info, CRITICAL: COLORS.danger };
                return <Cell key={`cell-${index}`} fill={colors[entry.name] || COLORS.slate} />;
              })}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );

  const renderSettings = () => (
    <div className="space-y-6">
      {/* API Keys Section */}
      <div className="bg-slate-800 p-4 rounded-lg border border-slate-700">
        <h4 className="text-sm font-mono text-slate-400 uppercase mb-4 flex items-center">
          <Key className="w-4 h-4 mr-2" /> API Keys Management
        </h4>
        <div className="space-y-4">
          <p className="text-slate-400 text-sm">
            Manage API keys for authentication. Keys are created by admins.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-3 bg-slate-900 rounded border border-slate-700">
              <div className="text-xs text-slate-500 uppercase mb-1">Your API Key</div>
              <div className="flex items-center space-x-2">
                <code className="text-cyan-400 font-mono text-sm flex-grow">
                  {localStorage.getItem('api_key') || 'Not set'}
                </code>
                <button
                  onClick={() => {
                    const key = prompt('Enter API key:');
                    if (key) {
                      localStorage.setItem('api_key', key);
                    }
                  }}
                  className="text-xs bg-slate-700 hover:bg-slate-600 px-2 py-1 rounded text-slate-300"
                >
                  Update
                </button>
              </div>
            </div>
            <div className="p-3 bg-slate-900 rounded border border-slate-700">
              <div className="text-xs text-slate-500 uppercase mb-1">JWT Token</div>
              <div className="flex items-center space-x-2">
                <code className="text-purple-400 font-mono text-sm flex-grow truncate">
                  {localStorage.getItem('token') ? localStorage.getItem('token')?.substring(0, 20) + '...' : 'Not set'}
                </code>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Notification Settings */}
      <div className="bg-slate-800 p-4 rounded-lg border border-slate-700">
        <h4 className="text-sm font-mono text-slate-400 uppercase mb-4 flex items-center">
          <Bell className="w-4 h-4 mr-2" /> Notification Settings
        </h4>
        <div className="space-y-4">
          <div className="flex items-center justify-between p-3 bg-slate-900 rounded border border-slate-700">
            <div>
              <div className="text-slate-200 font-medium">Email Notifications</div>
              <div className="text-xs text-slate-500">Receive alerts via SMTP</div>
            </div>
            <button className="text-xs bg-cyan-600 hover:bg-cyan-500 px-3 py-1 rounded text-white">
              Configure
            </button>
          </div>
          <div className="flex items-center justify-between p-3 bg-slate-900 rounded border border-slate-700">
            <div>
              <div className="text-slate-200 font-medium">Slack Integration</div>
              <div className="text-xs text-slate-500">Send alerts to Slack channel</div>
            </div>
            <button className="text-xs bg-slate-700 hover:bg-slate-600 px-3 py-1 rounded text-slate-300">
              Connect
            </button>
          </div>
          <div className="flex items-center justify-between p-3 bg-slate-900 rounded border border-slate-700">
            <div>
              <div className="text-slate-200 font-medium">Discord Integration</div>
              <div className="text-xs text-slate-500">Send alerts to Discord webhook</div>
            </div>
            <button className="text-xs bg-slate-700 hover:bg-slate-600 px-3 py-1 rounded text-slate-300">
              Connect
            </button>
          </div>
        </div>
      </div>

      {/* System Info */}
      <div className="bg-slate-800 p-4 rounded-lg border border-slate-700">
        <h4 className="text-sm font-mono text-slate-400 uppercase mb-4 flex items-center">
          <Info className="w-4 h-4 mr-2" /> System Information
        </h4>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <div className="text-slate-500 text-xs uppercase">Backend</div>
            <div className="text-slate-300">Running</div>
          </div>
          <div>
            <div className="text-slate-500 text-xs uppercase">Database</div>
            <div className="text-green-400">Connected</div>
          </div>
          <div>
            <div className="text-slate-500 text-xs uppercase">WebSocket</div>
            <div className="text-green-400">Active</div>
          </div>
          <div>
            <div className="text-slate-500 text-xs uppercase">Version</div>
            <div className="text-slate-300">1.0.0</div>
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <div className="h-full flex flex-col">
      {/* Tabs */}
      <div className="flex space-x-4 border-b border-slate-700 pb-2 mb-4 overflow-x-auto">
        {[
          { id: 'overview', label: 'OVERVIEW', icon: <Activity className="w-4 h-4 mr-2" /> },
          { id: 'ml', label: 'ML DASHBOARD', icon: <Brain className="w-4 h-4 mr-2" /> },
          { id: 'alerts', label: 'ALERTS', icon: <AlertTriangle className="w-4 h-4 mr-2" /> },
          { id: 'settings', label: 'SETTINGS', icon: <Settings className="w-4 h-4 mr-2" /> },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            className={`pb-2 px-4 font-mono font-bold transition-colors flex items-center whitespace-nowrap ${
              activeTab === tab.id ? 'text-cyan-400 border-b-2 border-cyan-400' : 'text-slate-500 hover:text-slate-300'
            }`}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-grow overflow-y-auto pr-2">
        {activeTab === 'overview' && renderOverview()}
        {activeTab === 'ml' && renderML()}
        {activeTab === 'alerts' && renderAlerts()}
        {activeTab === 'settings' && renderSettings()}
      </div>
    </div>
  );
};

// Metric Card Component
const MetricCard: React.FC<{
  icon: React.ReactNode;
  label: string;
  value: string | number;
  subtext: string;
  color: 'cyan' | 'purple' | 'yellow' | 'red' | 'green' | 'blue';
}> = ({ icon, label, value, subtext, color }) => {
  const colorClasses: Record<string, string> = {
    cyan: 'text-cyan-400 border-cyan-500/30',
    purple: 'text-purple-400 border-purple-500/30',
    yellow: 'text-yellow-400 border-yellow-500/30',
    red: 'text-red-400 border-red-500/30',
    green: 'text-green-400 border-green-500/30',
    blue: 'text-blue-400 border-blue-500/30',
  };

  return (
    <div className={`bg-slate-800 p-4 rounded-lg border ${colorClasses[color]} hover:scale-[1.02] transition-transform`}>
      <div className="flex justify-between items-start mb-2">
        <span className="text-xs font-mono text-slate-500 uppercase">{label}</span>
        <div className={colorClasses[color]}>{icon}</div>
      </div>
      <div className="text-2xl font-bold text-white font-mono">{value}</div>
      <div className="text-xs text-slate-500 mt-1">{subtext}</div>
    </div>
  );
};

export default StatsPanel;
