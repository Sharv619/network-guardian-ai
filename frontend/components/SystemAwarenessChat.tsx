import React, { useState, useEffect, useRef } from 'react';
import LoadingSpinner from './LoadingSpinner';
import { Send, Bot, Shield, Database, Brain, Wifi } from 'lucide-react';

interface SystemMessage {
    id: string;
    text: string;
    timestamp: string;
    isUser: boolean;
}

const API_BASE = "";

const SystemAwarenessChat: React.FC = () => {
    const [messages, setMessages] = useState<SystemMessage[]>([
        {
            id: '1',
            text: "🛡️ Network Guardian System Awareness Online\n\nI'm monitoring your network in real-time, analyzing DNS requests for threats using AI and local heuristics. Ask me about:\n• Live threat analysis\n• System architecture\n• Security recommendations\n• Threat detection logic",
            timestamp: new Date().toLocaleTimeString(),
            isUser: false
        }
    ]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!input.trim() || loading) return;

        const userMessage: SystemMessage = {
            id: Date.now().toString(),
            text: input,
            timestamp: new Date().toLocaleTimeString(),
            isUser: true
        };

        setMessages(prev => [...prev, userMessage]);
        setInput('');
        setLoading(true);

        try {
            const response = await fetch(`${API_BASE}/system-chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: input,
                    model_id: "gemini-1.5-flash"
                })
            });

            if (response.ok) {
                const data = await response.json();
                const aiMessage: SystemMessage = {
                    id: (Date.now() + 1).toString(),
                    text: data.text,
                    timestamp: new Date().toLocaleTimeString(),
                    isUser: false
                };
                setMessages(prev => [...prev, aiMessage]);
            } else {
                throw new Error('API Error');
            }
        } catch (error) {
            const errorMessage: SystemMessage = {
                id: (Date.now() + 1).toString(),
                text: "I'm currently experiencing connectivity issues. Please try again in a moment.",
                timestamp: new Date().toLocaleTimeString(),
                isUser: false
            };
            setMessages(prev => [...prev, errorMessage]);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="bg-slate-800 rounded-lg border border-slate-700 shadow-xl flex flex-col h-full">
            {/* Header */}
            <div className="p-4 border-b border-slate-700 bg-slate-900/50">
                <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                        <div className="w-3 h-3 bg-green-400 rounded-full animate-pulse"></div>
                        <div>
                            <h3 className="text-lg font-bold text-white">System Awareness Chat</h3>
                            <p className="text-xs text-slate-400">Live feed focused intelligence</p>
                        </div>
                    </div>
                    <div className="flex space-x-2 text-xs text-slate-500">
                        <span className="flex items-center space-x-1">
                            <Shield className="w-3 h-3" />
                            <span>AI ACTIVE</span>
                        </span>
                        <span className="flex items-center space-x-1">
                            <Database className="w-3 h-3" />
                            <span>LOCAL ML</span>
                        </span>
                    </div>
                </div>
            </div>

            {/* Messages */}
            <div className="flex-grow overflow-y-auto p-4 space-y-4 custom-scrollbar">
                {messages.map((message) => (
                    <div
                        key={message.id}
                        className={`flex ${message.isUser ? 'justify-end' : 'justify-start'}`}
                    >
                        <div
                            className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                                message.isUser
                                    ? 'bg-cyan-600 text-white'
                                    : 'bg-slate-700 text-slate-100'
                            }`}
                        >
                            <div className="text-xs text-slate-400 mb-1">
                                {message.isUser ? 'You' : '🛡️ Network Guardian AI'}
                            </div>
                            <div className="whitespace-pre-wrap text-sm leading-relaxed">
                                {message.text}
                            </div>
                            <div className="text-xs text-slate-500 mt-2 text-right">
                                {message.timestamp}
                            </div>
                        </div>
                    </div>
                ))}
                {loading && (
                    <div className="flex justify-start">
                        <div className="bg-slate-700 text-slate-100 px-4 py-2 rounded-lg">
                            <div className="flex items-center space-x-2">
                                <LoadingSpinner />
                                <span>Processing...</span>
                            </div>
                        </div>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <div className="p-4 border-t border-slate-700 bg-slate-900/50">
                <form onSubmit={handleSubmit} className="flex gap-3">
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder="Ask about live threats, system architecture, or security logic..."
                        className="flex-grow bg-slate-700 border border-slate-600 rounded-lg px-4 py-2 text-white placeholder-slate-400 focus:outline-none focus:border-cyan-500"
                        disabled={loading}
                    />
                    <button
                        type="submit"
                        disabled={!input.trim() || loading}
                        className="bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 disabled:cursor-not-allowed text-white p-2 rounded-lg transition-colors"
                    >
                        <Send className="w-5 h-5" />
                    </button>
                </form>
                <div className="text-xs text-slate-500 mt-2 text-center">
                    Tip: Ask about "recent threats", "system architecture", or "security recommendations"
                </div>
            </div>
        </div>
    );
};

export default SystemAwarenessChat;