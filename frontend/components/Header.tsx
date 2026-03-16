
import { useEffect, useState } from 'react';
import { Brain, Wifi, WifiOff } from 'lucide-react';
import { useWebSocket } from '../src/services/websocketService';
import { WebSocketMessage } from '../src/services/websocketService';

const ShieldIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8 text-cyan-400" viewBox="0 0 20 20" fill="currentColor">
    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
  </svg>
);

interface HeaderProps {
  availableModels: string[];
  selectedModel: string;
  onModelChange: (model: string) => void;
}

const Header: React.FC<HeaderProps> = ({ availableModels, selectedModel, onModelChange }) => {
  const [isHealthy, setIsHealthy] = useState<boolean | null>(null);
  const [connectionStatus, setConnectionStatus] = useState('disconnected');

  // WebSocket integration for real-time connection status
  const wsConfig = {
    url: `ws://${window.location.hostname}:8000/ws/public`,
    onConnect: () => {
      setConnectionStatus('connected');
    },
    onDisconnect: () => {
      setConnectionStatus('disconnected');
    },
    onMessage: (message: WebSocketMessage) => {
      // Handle heartbeat to maintain connection status
      if (message.event_type === 'heartbeat') {
        setConnectionStatus('connected');
      }
    },
    onError: (error) => {
      console.error('WebSocket error in header:', error);
      setConnectionStatus('error');
    }
  };

  const { webSocketService } = useWebSocket(wsConfig);

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const res = await fetch('/health');
        setIsHealthy(res.ok);
      } catch (error) {
        setIsHealthy(false);
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, 10000); // Check every 10 seconds
    return () => clearInterval(interval);
  }, []);

  const getHealthBadge = () => {
    if (isHealthy === null) {
      return (
        <div className="bg-yellow-500 text-white px-2 py-1 rounded-full text-xs font-medium animate-pulse">
          Checking...
        </div>
      );
    }
    return (
      <div className={`px-2 py-1 rounded-full text-xs font-medium ${
        isHealthy 
          ? 'bg-green-500 text-white' 
          : 'bg-red-500 text-white'
      }`}>
        {isHealthy ? 'Logic Verified' : 'System Error'}
      </div>
    );
  };

  const getConnectionBadge = () => {
    if (connectionStatus === 'connected') {
      return (
        <div className="flex items-center bg-green-500/20 px-2 py-1 rounded-full text-xs font-medium border border-green-500/30">
          <Wifi className="w-3 h-3 text-green-400 mr-1" />
          <span className="text-green-400">LIVE</span>
        </div>
      );
    } else if (connectionStatus === 'connecting') {
      return (
        <div className="flex items-center bg-yellow-500/20 px-2 py-1 rounded-full text-xs font-medium border border-yellow-500/30">
          <Wifi className="w-3 h-3 text-yellow-400 mr-1 animate-pulse" />
          <span className="text-yellow-400">CONNECTING</span>
        </div>
      );
    } else {
      return (
        <div className="flex items-center bg-red-500/20 px-2 py-1 rounded-full text-xs font-medium border border-red-500/30">
          <WifiOff className="w-3 h-3 text-red-400 mr-1" />
          <span className="text-red-400">OFFLINE</span>
        </div>
      );
    }
  };

  return (
    <header className="bg-slate-900/70 backdrop-blur-sm shadow-md p-4 sticky top-0 z-10 w-full border-b border-slate-700">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        <div className="flex items-center gap-4">
          <ShieldIcon />
          <h1 className="text-2xl font-bold text-slate-100 tracking-wider">
            Network Guardian <span className="text-cyan-400">AI</span>
          </h1>
        </div>

        <div className="flex items-center space-x-2">
          {getConnectionBadge()}
          <div className="flex items-center bg-slate-800 rounded px-3 py-1.5 border border-slate-700 hover:border-cyan-500 transition-colors">
            <Brain className="w-5 h-5 text-purple-400 mr-2" />
            <select
              value={selectedModel}
              onChange={(e) => onModelChange(e.target.value)}
              className="bg-transparent text-slate-200 text-sm font-mono focus:outline-none cursor-pointer"
            >
              {availableModels.map(m => (
                <option key={m} value={m} className="bg-slate-800">
                  {m.replace('models/', '')}
                </option>
              ))}
            </select>
          </div>
          {getHealthBadge()}
        </div>
      </div>
    </header>
  );
};

export default Header;
