import { useState, useEffect } from 'react';
import Header from './components/Header';
import Dashboard from './components/Dashboard';
import LoginPage from './components/LoginPage';
import AdminDashboard from './components/AdminDashboard';
import PricingPage from './components/PricingPage';
import UsageDashboard from './components/UsageDashboard';
import { getAvailableModels } from './services/geminiService';
import { isAuthenticated, login as apiLogin } from './services/tenantService';

const App: React.FC = () => {
  const [availableModels, setAvailableModels] = useState<string[]>(['gemini-2.0-flash']);
  const [selectedModel, setSelectedModel] = useState<string>(
    localStorage.getItem('guardian_model') || 'gemini-2.0-flash'
  );
  const [currentPage, setCurrentPage] = useState<string>('dashboard');
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const checkAuth = () => {
      setIsLoggedIn(isAuthenticated());
      setLoading(false);
    };
    
    checkAuth();
  }, []);

  useEffect(() => {
    const fetchModels = async () => {
      const models = await getAvailableModels();
      setAvailableModels(models);
      if (models.length > 0 && !models.includes(selectedModel)) {
        setSelectedModel(models[0]);
      }
    };
    fetchModels();
  }, []);

  const handleModelChange = (model: string) => {
    setSelectedModel(model);
    localStorage.setItem('guardian_model', model);
  };

  const handleLogin = () => {
    setIsLoggedIn(true);
  };

  const handleLogout = () => {
    setIsLoggedIn(false);
    setCurrentPage('dashboard');
  };

  const handleNavigate = (page: string) => {
    setCurrentPage(page);
  };

  const renderPage = () => {
    if (!isLoggedIn) {
      return <LoginPage onLogin={handleLogin} />;
    }

    switch (currentPage) {
      case 'admin':
        return <AdminDashboard />;
      case 'pricing':
        return <PricingPage />;
      case 'usage':
        return <UsageDashboard />;
      default:
        return <Dashboard selectedModel={selectedModel} />;
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-dark-950 flex items-center justify-center">
        <div className="text-accent">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-dark-950 font-sans text-dark-100 flex flex-col">
      <Header
        availableModels={availableModels}
        selectedModel={selectedModel}
        onModelChange={handleModelChange}
        onLogout={handleLogout}
        onNavigate={handleNavigate}
        currentPage={currentPage}
      />
      <main className="flex-grow p-4 lg:p-6 max-w-7xl mx-auto w-full">
        {renderPage()}
      </main>
    </div>
  );
};

export default App;
