
import { useState, useEffect } from 'react';
import Header from './components/Header';
import Dashboard from './components/Dashboard';
import { getAvailableModels } from './services/geminiService';
import { HistoryItem } from './types';

const App: React.FC = () => {
  const [availableModels, setAvailableModels] = useState<string[]>(['gemini-2.0-flash']);
  const [selectedModel, setSelectedModel] = useState<string>(
    localStorage.getItem('guardian_model') || 'gemini-2.0-flash'
  );

  useEffect(() => {
    const fetchModels = async () => {
      const models = await getAvailableModels();
      setAvailableModels(models);
      // If our selected model is no longer in the list, fallback to first available
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

  // Mock history items for demonstration
  const mockHistoryItems: HistoryItem[] = [
    {
      domain: 'malicious.example.com',
      risk_score: 'High',
      category: 'Malware',
      summary: 'Gemini AI detected malicious payload. 🛡️ LOCAL ANALYSIS confirms threat.',
      timestamp: '2024-02-10 14:30:00',
      is_anomaly: true,
      anomaly_score: 0.85,
      adguard_metadata: {
        reason: 'Blocked by user filter',
        rule: '||malicious.example.com^',
        filter_id: 1
      },
      has_similarity_match: true
    },
    {
      domain: 'tracker.adservice.com',
      risk_score: 'Medium',
      category: 'Tracker',
      summary: 'AdGuard blocked tracking request.',
      timestamp: '2024-02-10 14:25:00',
      is_anomaly: false,
      adguard_metadata: {
        reason: 'Blocked by AdGuard DNS filter',
        rule: '||adservice.com^',
        filter_id: 2
      }
    },
    {
      domain: 'safe.example.com',
      risk_score: 'Low',
      category: 'Safe',
      summary: 'No threats detected.',
      timestamp: '2024-02-10 14:20:00',
      is_anomaly: false
    }
  ];

  return (
    <div className="min-h-screen bg-slate-900 font-sans flex flex-col">
      <Header
        availableModels={availableModels}
        selectedModel={selectedModel}
        onModelChange={handleModelChange}
      />
      <main className="flex-grow p-4 lg:p-6 max-w-7xl mx-auto w-full">
        <Dashboard selectedModel={selectedModel} />
      </main>
    </div>
  );
};

export default App;
