
import { ThreatReport } from '../types';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

/**
 * BFF Pattern: Proxy analysis through Python Backend
 */
export const analyzeDomain = async (domain: string, whoisData?: any): Promise<ThreatReport> => {
    try {
        const res = await fetch(`${API_BASE}/analyze`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                domain,
                registrar: whoisData?.registrar,
                age: whoisData?.age,
                organization: whoisData?.organization
            })
        });

        if (!res.ok) throw new Error('Backend analysis failed');

        const data = await res.json();
        return {
            risk_score: data.risk_score === 'High' ? 10 : data.risk_score === 'Medium' ? 5 : 2,
            category: data.category,
            explanation: data.summary,
            recommended_action: data.risk_score === 'High' ? 'Keep blocked' : 'Safe to whitelist'
        };
    } catch (error) {
        console.error("BFF Error:", error);
        throw error;
    }
};

/**
 * BFF Pattern: Proxy chat through Python Backend
 */
export const sendChatMessage = async (message: string): Promise<string> => {
    try {
        const res = await fetch(`${API_BASE}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message })
        });

        if (!res.ok) throw new Error('Backend chat failed');

        const data = await res.json();
        return data.text;
    } catch (error) {
        console.error("BFF Chat Error:", error);
        return "Sorry, I'm having trouble connecting to the Guardian Brain.";
    }
};
