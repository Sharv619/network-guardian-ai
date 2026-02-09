import { useState, useEffect, useCallback } from 'react';
import { sendChatMessage } from '../services/geminiService';
import { ChatMessage } from '../types';

export const useChat = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    setMessages([
      { 
        id: 'initial', 
        role: 'model', 
        text: '🛡️ Network Guardian AI Online\n\nI monitor your network traffic in real-time, analyzing DNS requests for threats using AI and local heuristics. Ask me about:\n• System architecture\n• Threat detection logic\n• Live feed analysis\n• Security recommendations' 
      }
    ]);
  }, []);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setInput(e.target.value);
  };

  const handleSubmit = useCallback(async (e: React.FormEvent, modelId?: string) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage: ChatMessage = { id: Date.now().toString(), role: 'user', text: input };
    setMessages(prev => [...prev, userMessage]);
    const userQuery = input;
    setInput('');
    setIsLoading(true);

    const modelMessageId = (Date.now() + 1).toString();
    setMessages(prev => [...prev, { id: modelMessageId, role: 'model', text: 'Thinking...' }]);

    try {
      // SRE Pattern: BFF Chat Proxy with Dynamic Model
      const response = await sendChatMessage(userQuery, modelId);

      setMessages(prev => prev.map(msg =>
        msg.id === modelMessageId ? { ...msg, text: response } : msg
      ));
    } catch (error) {
      console.error("Chat error:", error);
      setMessages(prev => prev.map(msg =>
        msg.id === modelMessageId ? { ...msg, text: "Sorry, I encountered an error. Please try again." } : msg
      ));
    } finally {
      setIsLoading(false);
    }
  }, [input, isLoading]);

  return {
    messages,
    input,
    isLoading,
    handleInputChange,
    handleSubmit
  };
};
