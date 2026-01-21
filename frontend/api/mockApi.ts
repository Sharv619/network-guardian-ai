
import { ThreatReport } from '../types';

const MOCK_LATENCY = 800; // ms

/**
 * Simulates calling the Gemini API to analyze a domain.
 */
export const mockAnalyzeDomain = (
  domain: string,
  whoisData: { registrar: string; age: string; organization: string }
): Promise<ThreatReport> => {
  console.log('Mock API: Analyzing domain', { domain, whoisData });
  
  return new Promise((resolve) => {
    setTimeout(() => {
      // Base the mock response on the domain name for some variety
      let report: ThreatReport;
      if (domain.includes('google') || domain.includes('apple')) {
        report = {
          risk_score: 2,
          category: 'Tracker',
          explanation: `The domain ${domain} is associated with ${whoisData.organization} and is used for legitimate product metrics and tracking user activity within their ecosystem.`,
          recommended_action: 'Safe to whitelist',
        };
      } else if (domain.includes('ad')) {
        report = {
          risk_score: 5,
          category: 'Ad',
          explanation: `This domain, ${domain}, is a known ad-serving network. It delivers advertisements and tracks ad performance across multiple websites.`,
          recommended_action: 'Keep blocked',
        };
      } else {
        report = {
          risk_score: 8,
          category: 'Malware',
          explanation: `The domain ${domain} has been flagged on several threat intelligence feeds. It is associated with distributing malware or phishing campaigns.`,
          recommended_action: 'Keep blocked',
        };
      }
      resolve(report);
    }, MOCK_LATENCY);
  });
};

/**
 * Simulates a streaming chat response from the Gemini API.
 */
export async function* mockStartChatStream(message: string) {
  console.log('Mock API: Starting chat stream for message:', message);
  
  const response = `This is a mock response simulating how the AI would answer your question about: "**${message}**". 
  
  Based on my system prompt, I would explain the architecture:
  - **Ingestion**: A Python poller grabs logs.
  - **Deduplication**: Redis is used with a 5-minute TTL to prevent log spam and save on API costs.
  - **Analysis**: That's me, the Gemini agent!
  
  This streaming response is delivered in chunks to simulate a real-time conversation.`;

  const words = response.split(/(\s+)/); // Split by space, keeping the space
  for (let i = 0; i < words.length; i++) {
    await new Promise(resolve => setTimeout(resolve, 30));
    yield words[i];
  }
}
