import { useEffect, useState } from 'react';
import { Brain, Wifi, WifiOff, LogOut, User, ChevronDown } from 'lucide-react';
import { useWebSocket } from '../src/services/websocketService';
import { WebSocketMessage } from '../src/services/websocketService';
import TenantSelector from './TenantSelector';
import { isAuthenticated, logout, getUsername } from '../services/tenantService';

const ShieldIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8 text-accent" viewBox="0 0 20 20" fill="currentColor">
    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
  </svg>
);

interface HeaderProps {
  availableModels: string[];
  selectedModel: string;
  onModelChange: (model: string) => void;
  onLogout?: () => void;
  onNavigate?: (page: string) => void;
  currentPage?: string;
}

const Header: React.FC<HeaderProps> = ({ 
  availableModels, 
  selectedModel, 
  onModelChange,
  onLogout,
  onNavigate,
  currentPage = 'dashboard'
}) => {
  const [isHealthy, setIsHealthy] = useState<boolean | null>(null);
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const [showUserMenu, setShowUserMenu] = useState(false);
  const authed = isAuthenticated();
  const username = getUsername();

  const wsConfig = {
    url: `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/public`,
    onConnect: () => {
      setConnectionStatus('connected');
    },
    onDisconnect: () => {
      setConnectionStatus('disconnected');
    },
    onMessage: (message: WebSocketMessage) => {
      if (message.event_type === 'heartbeat') {
        setConnectionStatus('connected');
      }
    },
    onError: (error: any) => {
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
    const interval = setInterval(checkHealth, 10000);
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

  const handleLogout = () => {
    logout();
    setShowUserMenu(false);
    onLogout?.();
  };

  const navItems = [
    { id: 'dashboard', label: 'Dashboard' },
    { id: 'admin', label: 'Admin' },
    { id: 'usage', label: 'Usage' },
    { id: 'pricing', label: 'Pricing' },
  ];

  return (
    <header className="bg-dark-950/80 backdrop-blur-md shadow-soft border-b border-dark-800 p-4 sticky top-0 z-50 w-full">
      <div className="max-w-7xl mx-auto">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-3">
              <ShieldIcon />
              <h1 className="text-2xl font-display font-bold text-dark-100 tracking-tight">
                Network Guardian <span className="text-accent">AI</span>
              </h1>
            </div>

            {authed && (
              <nav className="hidden md:flex items-center gap-1">
                {navItems.map((item) => (
                  <button
                    key={item.id}
                    onClick={() => onNavigate?.(item.id)}
                    className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                      currentPage === item.id
                        ? 'bg-accent/20 text-accent'
                        : 'text-dark-400 hover:text-dark-200 hover:bg-dark-800'
                    }`}
                  >
                    {item.label}
                  </button>
                ))}
              </nav>
            )}
          </div>

          <div className="flex items-center space-x-3">
            {getConnectionBadge()}
            
            {authed ? (
              <>
                <TenantSelector />
                
                <div className="relative">
                  <button
                    onClick={() => setShowUserMenu(!showUserMenu)}
                    className="flex items-center gap-2 px-3 py-2 bg-dark-800 border border-dark-700 rounded-lg hover:border-accent/50 transition-colors"
                  >
                    <User className="w-4 h-4 text-dark-400" />
                    <span className="text-sm text-dark-200 hidden sm:inline">{username || 'User'}</span>
                    <ChevronDown className="w-4 h-4 text-dark-400" />
                  </button>

                  {showUserMenu && (
                    <div className="absolute top-full right-0 mt-2 w-48 bg-dark-800 border border-dark-700 rounded-lg shadow-xl overflow-hidden">
                      <div className="p-2">
                        <div className="px-3 py-2 text-sm text-dark-400 border-b border-dark-700">
                          Signed in as <span className="text-dark-200">{username}</span>
                        </div>
                        <button
                          onClick={handleLogout}
                          className="w-full mt-1 px-3 py-2 text-left text-sm text-red-400 hover:bg-dark-700 rounded flex items-center gap-2"
                        >
                          <LogOut className="w-4 h-4" />
                          Sign out
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              </>
            ) : (
              <div className="flex items-center bg-dark-800 rounded-lg px-3 py-2 border border-dark-700 hover:border-accent/50 transition-colors">
                <Brain className="w-4 h-4 text-accent-muted mr-2" />
                <select
                  value={selectedModel}
                  onChange={(e) => onModelChange(e.target.value)}
                  className="bg-transparent text-dark-200 text-sm font-mono focus:outline-none cursor-pointer"
                >
                  {availableModels.map(m => (
                    <option key={m} value={m} className="bg-dark-800">
                      {m.replace('models/', '')}
                    </option>
                  ))}
                </select>
              </div>
            )}

            {getHealthBadge()}
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;
