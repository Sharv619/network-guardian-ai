
import { ThreatReport } from '../types';

const API_BASE = import.meta.env.VITE_API_BASE || '';

/**
 * Model Discovery Service
 */
export const getAvailableModels = async (): Promise<string[]> => {
    try {
        const res = await fetch(`${API_BASE}/models`);
        if (!res.ok) throw new Error('Failed to fetch models');
        const data = await res.json();
        return data.models || [];
    } catch (error) {
        console.error("Model Discovery Error:", error);
        return [];
    }
};

/**
 * BFF Pattern: Proxy analysis through Python Backend
 */
export const analyzeDomain = async (domain: string, whoisData?: any, modelId?: string): Promise<ThreatReport> => {
    try {
        const res = await fetch(`${API_BASE}/analyze`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                domain,
                registrar: whoisData?.registrar,
                age: whoisData?.age,
                organization: whoisData?.organization,
                model_id: modelId
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
export const sendChatMessage = async (message: string, modelId?: string): Promise<string> => {
    try {
        // Use the advanced chat endpoint with enhanced RAG functionality
        const res = await fetch(`${API_BASE}/chat/advanced`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                message, 
                model_id: modelId,
                include_context: true,
                search_radius: 5,
                min_similarity: 0.7
            })
        });

        if (!res.ok) throw new Error('Backend chat failed');

        const data = await res.json();
        return data.text || data.response || "No response received";
    } catch (error) {
        console.error("BFF Chat Error:", error);
        return "Sorry, I'm having trouble connecting to the Guardian Brain.";
    }
};

/**
 * Enhanced chat with context and insights
 */
export const sendAdvancedChatMessage = async (message: string, options: {
    include_context?: boolean;
    search_radius?: number;
    min_similarity?: number;
    modelId?: string;
} = {}): Promise<any> => {
    try {
        const res = await fetch(`${API_BASE}/chat/advanced`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                message, 
                model_id: options.modelId,
                include_context: options.include_context ?? true,
                search_radius: options.search_radius ?? 5,
                min_similarity: options.min_similarity ?? 0.7
            })
        });

        if (!res.ok) throw new Error('Advanced backend chat failed');

        const data = await res.json();
        return data;
    } catch (error) {
        console.error("Advanced BFF Chat Error:", error);
        throw error;
    }
};

/**
 * Search functionality with context
 */
export const searchChatHistory = async (query: string, options: {
    k?: number;
    min_similarity?: number;
    include_context?: boolean;
} = {}): Promise<any> => {
    try {
        const params = new URLSearchParams({
            k: (options.k ?? 5).toString(),
            min_similarity: (options.min_similarity ?? 0.7).toString(),
            include_context: (options.include_context ?? true).toString()
        });
        
        const res = await fetch(`${API_BASE}/chat/enhanced-search/${encodeURIComponent(query)}?${params}`);
        
        if (!res.ok) throw new Error('Chat search failed');

        const data = await res.json();
        return data;
    } catch (error) {
        console.error("Chat Search Error:", error);
        throw error;
    }
};
