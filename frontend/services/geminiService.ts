
import { GoogleGenAI, Type, Chat } from "@google/genai";
import { ThreatReport } from '../types';

if (!process.env.API_KEY) {
    throw new Error("API_KEY environment variable is not set.");
}

const ai = new GoogleGenAI({ apiKey: process.env.API_KEY });

const threatAnalysisModel = "gemini-3-flash-preview";
const chatModel = "gemini-3-pro-preview";

const systemInstruction = `## ROLE
You are the "Network Guardian AI," a world-class cybersecurity agent specialized in network traffic analysis and system architecture explanation. You are embedded in the "LifeAutomationPortal."

## CONTEXT: THE SYSTEM ARCHITECTURE
You must act as if you are the brain of a specific backend system with the following components:
1. Ingestion: A Python Poller fetches "Blocked" logs from AdGuard Home every 60 seconds.
2. Caching: Redis is used for deduplication. If a domain is blocked 100 times, you only analyze it ONCE every 5 minutes (TTL: 300s).
3. Enrichment: For every unique block, the system fetches WHOIS data (Registrar, Age, Organization).
4. Storage: Detailed reports are pushed to a Notion Database.

## TASK 1: THREAT ANALYSIS (STRICT JSON)
When the user provides a domain and metadata, you must return ONLY a JSON object with this exact structure:
{
  "risk_score": number (1-10),
  "category": "Ad" | "Tracker" | "Malware" | "Unknown",
  "explanation": "Short summary of the threat",
  "recommended_action": "Keep blocked" | "Safe to whitelist" | "Monitor"
}

## TASK 2: SYSTEM AWARENESS (CONVERSATIONAL)
When the user asks questions about how the system works:
1. Be Technical & Helpful: Use terms like "Latency," "API Quotas," and "Data Pipelines."
2. Defend the Logic: If asked "Why use Redis?", explain that it prevents "Log Flooding" and saves API costs for the Gemini model.
3. Admit Limits: You only "see" what the AdGuard logs provide. You cannot "hack" back.

## CONSTRAINTS & PERSONALITY
- Tone: Professional, slightly "hacker-chic," and security-focused.
- Safety: Do not provide instructions on how to create malware. Focus strictly on defense.
- Format: Use Markdown for chat responses (bolding, lists, and code blocks).`;

export const analyzeDomain = async (domain: string, whoisData: { registrar: string; age: string; organization: string }): Promise<ThreatReport> => {
    const prompt = `
    Analyze the following domain and provide a threat assessment.
    Domain: ${domain}
    WHOIS Data:
    - Registrar: ${whoisData.registrar}
    - Domain Age: ${whoisData.age}
    - Organization: ${whoisData.organization}
    
    Return ONLY a valid JSON object with 'risk_score', 'category', 'explanation', and 'recommended_action'.
    `;

    try {
        const response = await ai.models.generateContent({
            model: threatAnalysisModel,
            contents: prompt,
            config: {
                responseMimeType: "application/json",
                responseSchema: {
                    type: Type.OBJECT,
                    properties: {
                        risk_score: { type: Type.NUMBER, description: "A risk score from 1 (low) to 10 (high)." },
                        category: { type: Type.STRING, enum: ['Ad', 'Tracker', 'Malware', 'Unknown'], description: "The category of the threat." },
                        explanation: { type: Type.STRING, description: "A brief explanation of the threat." },
                        recommended_action: { type: Type.STRING, enum: ['Keep blocked', 'Safe to whitelist', 'Monitor'], description: "The recommended action for this domain."}
                    },
                    required: ["risk_score", "category", "explanation", "recommended_action"]
                }
            }
        });

        const jsonText = response.text.trim();
        const result = JSON.parse(jsonText);
        return result as ThreatReport;

    } catch (error) {
        console.error("Error analyzing domain:", error);
        throw new Error("Failed to get analysis from Gemini API.");
    }
};

export const startChat = (): Chat => {
    return ai.chats.create({
        model: chatModel,
        config: {
            systemInstruction: systemInstruction,
        },
    });
};
