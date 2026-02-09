
import { useState, useEffect } from 'react';
import Header from './components/Header';
import Dashboard from './components/Dashboard';
import { getAvailableModels } from './services/geminiService';

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
