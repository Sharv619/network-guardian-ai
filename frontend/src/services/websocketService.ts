import { useEffect, useState } from 'react';

export interface WebSocketMessage {
  event_type: string;
  data: any;
  timestamp: string;
  correlation_id?: string;
}

export interface WebSocketServiceConfig {
  url: string;
  token?: string;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Event) => void;
  onMessage?: (message: WebSocketMessage) => void;
}

export class WebSocketService {
  private ws: WebSocket | null = null;
  config: WebSocketServiceConfig;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000; // Start with 1 second
  private listeners: Map<string, Set<(data: any) => void>> = new Map();

  constructor(config: WebSocketServiceConfig) {
    this.config = config;
  }

  connect(): void {
    const { url, token } = this.config;
    
    // Build query parameters
    let wsUrl = url;
    const params = new URLSearchParams();
    if (token) params.set('token', token);
    
    if (params.toString()) {
      wsUrl += `?${params.toString()}`;
    }

    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      console.log('WebSocket connected');
      this.reconnectAttempts = 0; // Reset attempts on successful connection
      if (this.config.onConnect) {
        this.config.onConnect();
      }
    };

    this.ws.onmessage = (event) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data);
        
        // Call general message handler
        if (this.config.onMessage) {
          this.config.onMessage(message);
        }

        // Call specific event type listeners
        const eventListeners = this.listeners.get(message.event_type);
        if (eventListeners) {
          eventListeners.forEach(listener => listener(message.data));
        }
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    };

    this.ws.onclose = (event) => {
      console.log('WebSocket disconnected:', event.code, event.reason);
      if (this.config.onDisconnect) {
        this.config.onDisconnect();
      }

      // Attempt to reconnect if it wasn't a manual close
      if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
        this.scheduleReconnect();
      }
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      if (this.config.onError) {
        this.config.onError(error);
      }
    };
  }

  private scheduleReconnect(): void {
    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1); // Exponential backoff
    
    console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts}) in ${delay}ms...`);
    
    setTimeout(() => {
      this.connect();
    }, delay);
  }

  sendMessage(message: any): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket is not connected. Cannot send message.');
    }
  }

  subscribe(eventType: string, callback: (data: any) => void): void {
    if (!this.listeners.has(eventType)) {
      this.listeners.set(eventType, new Set());
    }
    this.listeners.get(eventType)?.add(callback);
  }

  unsubscribe(eventType: string, callback: (data: any) => void): void {
    const eventTypeListeners = this.listeners.get(eventType);
    if (eventTypeListeners) {
      eventTypeListeners.delete(callback);
    }
  }

  disconnect(): void {
    if (this.ws) {
      this.ws.close(1000, 'Manual disconnect');
      this.ws = null;
    }
  }

  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }

  getConnectionStatus(): string {
    if (!this.ws) return 'disconnected';
    switch (this.ws.readyState) {
      case WebSocket.CONNECTING: return 'connecting';
      case WebSocket.OPEN: return 'connected';
      case WebSocket.CLOSING: return 'closing';
      case WebSocket.CLOSED: return 'disconnected';
      default: return 'unknown';
    }
  }
}

// React hook to use WebSocket service
export const useWebSocket = (config: WebSocketServiceConfig) => {
  const [webSocketService] = useState(() => {
    // Check for stored authentication tokens (token only, not apiKey for security)
    const storedToken = localStorage.getItem('token');
    
    // Override config with stored auth if not provided
    const finalConfig = {
      ...config,
      token: config.token || storedToken || undefined
      // Note: apiKey is intentionally not retrieved from localStorage for security
      // API keys should be managed securely on the backend, not exposed in frontend
    };
    
    return new WebSocketService(finalConfig);
  });
  const [connectionStatus, setConnectionStatus] = useState('disconnected');

  useEffect(() => {
    // Update status when connection changes
    const updateStatus = () => {
      setConnectionStatus(webSocketService.getConnectionStatus());
    };

    // Set up status monitoring
    webSocketService.config.onConnect = () => {
      updateStatus();
      if (config.onConnect) config.onConnect();
    };

    webSocketService.config.onDisconnect = () => {
      updateStatus();
      if (config.onDisconnect) config.onDisconnect();
    };

    webSocketService.config.onError = (error) => {
      if (config.onError) config.onError(error);
    };

    webSocketService.config.onMessage = (message) => {
      if (config.onMessage) config.onMessage(message);
    };

    // Connect to WebSocket
    webSocketService.connect();

    // Cleanup on unmount
    return () => {
      webSocketService.disconnect();
    };
  }, []);

  return { webSocketService, connectionStatus };
};