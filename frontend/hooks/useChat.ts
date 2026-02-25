import { useState, useEffect, useCallback } from 'react';
import { sendChatMessage, sendAdvancedChatMessage } from '../services/geminiService';
import { ChatMessage } from '../types';

export const useChat = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [chatContext, setChatContext] = useState<any>(null);

  useEffect(() => {
    setMessages([
      { 
        id: 'initial', 
        role: 'model', 
        text: '🛡️ Network Guardian AI Online\n\nI monitor your network traffic in real-time, analyzing DNS requests for threats using AI and local heuristics. Ask me about:\n• System architecture\n• Threat detection logic\n• Live feed analysis\n• Security recommendations\n• Domain analysis and threat patterns' 
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
    setMessages(prev => [...prev, { id: modelMessageId, role: 'model', text: 'Analyzing with enhanced RAG...' }]);

    try {
      // Use advanced chat with enhanced RAG functionality
      const response = await sendAdvancedChatMessage(userQuery, {
        modelId,
        include_context: true,
        search_radius: 5,
        min_similarity: 0.7
      });

      // Update chat context if available
      if (response.context) {
        setChatContext(response.context);
      }

      const displayText = response.text || response.response || "No response received";

      setMessages(prev => prev.map(msg =>
        msg.id === modelMessageId ? { ...msg, text: displayText } : msg
      ));
    } catch (error) {
      console.error("Advanced chat error:", error);
      setMessages(prev => prev.map(msg =>
        msg.id === modelMessageId ? { ...msg, text: "Sorry, I encountered an error. Falling back to basic analysis." } : msg
      ));
      
      // Fallback to basic chat
      try {
        const fallbackResponse = await sendChatMessage(userQuery, modelId);
        setMessages(prev => prev.map(msg =>
          msg.id === modelMessageId ? { ...msg, text: fallbackResponse } : msg
        ));
      } catch (fallbackError) {
        console.error("Fallback chat also failed:", fallbackError);
      }
    } finally {
      setIsLoading(false);
    }
  }, [input, isLoading]);

  const getChatContext = () => {
    return chatContext;
  };

  return {
    messages,
    input,
    isLoading,
    chatContext,
    handleInputChange,
    handleSubmit,
    getChatContext
  };
};
