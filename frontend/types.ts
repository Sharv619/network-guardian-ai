
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
