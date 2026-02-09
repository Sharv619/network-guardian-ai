
import { } from 'react';
import { Brain } from 'lucide-react';

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
          <div className="bg-green-500 text-white px-2 py-1 rounded-full text-xs font-medium">
            Logic Verified
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;
