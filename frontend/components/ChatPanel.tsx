
import React, { useRef, useEffect } from 'react';
import LoadingSpinner from './LoadingSpinner';
import { useChat } from '../hooks/useChat';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Eye as EyeIcon, X } from 'lucide-react';

interface ChatPanelProps {
  selectedModel?: string;
}

const ChatPanel: React.FC<ChatPanelProps> = ({ selectedModel }) => {
  const { messages, input, isLoading, handleInputChange, handleSubmit } = useChat();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(scrollToBottom, [messages]);

  const onChatSubmit = (e: React.FormEvent) => {
    handleSubmit(e, selectedModel);
  };

  return (
    <div className="bg-slate-800 rounded-lg shadow-xl h-full flex flex-col">
      <div className="p-4 border-b border-slate-700">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold text-slate-100">System Awareness Chat</h2>
            <p className="text-xs text-slate-400 mt-1">Ask about architecture, threats, or security logic</p>
          </div>
          <div className="flex gap-2">
            <span className="px-2 py-1 bg-green-900/50 text-green-400 border border-green-500/30 rounded text-xs font-mono">
              AI ACTIVE
            </span>
            <span className="px-2 py-1 bg-blue-900/50 text-blue-400 border border-blue-500/30 rounded text-xs font-mono">
              LOCAL ML
            </span>
          </div>
        </div>
      </div>
      <div className="flex-grow p-4 overflow-y-auto">
        <div className="space-y-4">
          {messages.map((msg) => (
            <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-xl px-4 py-2 rounded-lg shadow ${msg.role === 'user' ? 'bg-cyan-800 text-white' : 'bg-slate-700 text-slate-200'}`}>
                <div className="prose prose-invert prose-sm text-slate-200">
                  <ReactMarkdown 
                    remarkPlugins={[remarkGfm]}
                    className="space-y-3"
                  >
                    {msg.text}
                  </ReactMarkdown>
                </div>
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>
      </div>
      <div className="p-4 border-t border-slate-700">
        <form onSubmit={onChatSubmit} className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={handleInputChange}
            placeholder="Ask: 'How does the system work?' or 'Explain the architecture'"
            className="flex-grow bg-slate-700 border-slate-600 rounded-md shadow-sm text-slate-200 focus:outline-none focus:ring-cyan-500 focus:border-cyan-500 placeholder-slate-500"
            disabled={isLoading}
          />
          <button type="submit" disabled={isLoading || !input.trim()} className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-cyan-600 hover:bg-cyan-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-cyan-500 focus:ring-offset-slate-800 disabled:bg-slate-500 disabled:cursor-not-allowed transition-colors">
            {isLoading ? <LoadingSpinner /> : 'Send'}
          </button>
        </form>
        <div className="mt-2 text-xs text-slate-500 text-center">
          Try asking: "Show me the system architecture" or "How do you detect threats?"
        </div>
      </div>
    </div>
  );
};

export default ChatPanel;
