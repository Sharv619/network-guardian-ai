
export interface ThreatReport {
  risk_score: number;
  category: 'Ad' | 'Tracker' | 'Malware' | 'Unknown';
  explanation: string;
  recommended_action: 'Keep blocked' | 'Safe to whitelist' | 'Monitor';
}

export interface HistoryItem {
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
  has_similarity_match?: boolean;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'model';
  text: string;
}

export interface SystemStats {
  autonomy_score: number;
  local_decisions: number;
  cloud_decisions: number;
  total_decisions: number;
  patterns_learned: number;
  seed_patterns: number;
  learned_patterns: number;
  classifier: {
    total_domains: number;
    category_distribution: Record<string, number>;
    accuracy: number;
    confidence: number;
  };
  cache: {
    total_cached: number;
    hit_rate: number;
    memory_usage: number;
    source_distribution: Record<string, number>;
  };
  realtime_stats: {
    autonomy_score: number;
    local_decisions: number;
    cloud_decisions: number;
    total_decisions: number;
    patterns_learned: number;
    seed_patterns: number;
    learned_patterns: number;
  };
  entropy: {
    total_analyzed: number;
    avg_entropy: number;
    high_entropy_count: number;
    low_entropy_count: number;
    max_entropy: number;
    min_entropy: number;
  };
  anomaly: {
    is_trained: boolean;
    total_samples: number;
    min_samples_required: number;
    anomalies_detected: number;
    anomaly_rate: number;
    recent_scores: number[];
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
  vector_memory?: {
    total_embeddings: number;
    memory_size: number;
    query_performance: number;
  };
  anomaly_engine?: {
    is_trained: boolean;
    training_samples: number;
    detection_rate: number;
  };
  adaptive_thresholds?: {
    entropy_threshold: number;
    anomaly_threshold: number;
  };
}

export interface AlertStats {
  total_alerts: number;
  critical_alerts: number;
  high_alerts: number;
  medium_alerts: number;
  low_alerts: number;
  resolved_alerts: number;
  pending_alerts: number;
  acknowledged: number;
  alert_rate: number;
  current_threat_rate: number;
  current_anomaly_rate: number;
  by_severity: {
    high: number;
    medium: number;
    low: number;
  };
  top_threats: Array<{
    domain: string;
    risk_score: number;
    category: string;
    count: number;
  }>;
}

export interface MLDashboard {
  overview: {
    overall_accuracy: number;
    total_analyzed: number;
    anomalies_detected: number;
    false_positives: number;
    false_negatives: number;
  };
  feedback: {
    total_feedback: number;
    correct_predictions: number;
    false_positives: number;
    false_negatives: number;
  };
  thresholds: {
    entropy_threshold: number;
    anomaly_threshold: number;
  };
  features: {
    tld_tracked: number;
    domain_patterns: number;
  };
  entropy_distribution: {
    high: number;
    medium: number;
    low: number;
  };
  learning_progress: {
    patterns_learned: number;
    total_patterns: number;
    progress_percentage: number;
  };
  model_performance: {
    precision: number;
    recall: number;
    f1_score: number;
    accuracy: number;
  };
  feature_importance: Array<{
    feature: string;
    importance: number;
  }>;
}
