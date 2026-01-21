
export interface ThreatReport {
  risk_score: number;
  category: 'Ad' | 'Tracker' | 'Malware' | 'Unknown';
  explanation: string;
  recommended_action: 'Keep blocked' | 'Safe to whitelist' | 'Monitor';
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'model';
  text: string;
}
