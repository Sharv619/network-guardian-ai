
import React, { useState } from 'react';

import { ThreatReport } from '../types';
import LoadingSpinner from './LoadingSpinner';
import CodeBlock from './CodeBlock';

const ThreatAnalysisPanel: React.FC = () => {
  const [domain, setDomain] = useState('metrics.icloud.com');
  const [registrar, setRegistrar] = useState('MarkMonitor Inc.');
  const [age, setAge] = useState('10 years');
  const [organization, setOrganization] = useState('Apple Inc.');

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [report, setReport] = useState<ThreatReport | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    setReport(null);

    try {
      const response = await fetch('/api/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          domain,
          registrar,
          age,
          organization
        }),
      });

      if (!response.ok) {
        throw new Error(`API Error: ${response.status}`);
      }

      const result = await response.json();
      setReport(result);
    } catch (err) {
      console.error(err);
      setError('Failed to analyze domain. Is the backend running?');
    } finally {
      setIsLoading(false);
    }
  };

  const getRiskColor = (score: number) => {
    if (score >= 8) return 'text-red-400';
    if (score >= 5) return 'text-yellow-400';
    return 'text-green-400';
  };

  const getRecommendationColor = (action: ThreatReport['recommended_action']) => {
    switch (action) {
      case 'Keep blocked': return 'text-red-400';
      case 'Monitor': return 'text-yellow-400';
      case 'Safe to whitelist': return 'text-green-400';
      default: return 'text-slate-400';
    }
  };


  return (
    <div className="bg-slate-800 rounded-lg shadow-xl h-full flex flex-col p-6">
      <h2 className="text-xl font-semibold text-slate-100 mb-1">Threat Analysis</h2>
      <p className="text-slate-400 mb-6">Manually analyze a domain with mock WHOIS data.</p>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="domain" className="block text-sm font-medium text-slate-300 mb-1">Domain</label>
          <input type="text" id="domain" value={domain} onChange={e => setDomain(e.target.value)} className="w-full bg-slate-700 border-slate-600 rounded-md shadow-sm text-slate-200 focus:ring-cyan-500 focus:border-cyan-500" />
        </div>
        <div>
          <label htmlFor="registrar" className="block text-sm font-medium text-slate-300 mb-1">Registrar</label>
          <input type="text" id="registrar" value={registrar} onChange={e => setRegistrar(e.target.value)} className="w-full bg-slate-700 border-slate-600 rounded-md shadow-sm text-slate-200 focus:ring-cyan-500 focus:border-cyan-500" />
        </div>
        <div>
          <label htmlFor="age" className="block text-sm font-medium text-slate-300 mb-1">Domain Age</label>
          <input type="text" id="age" value={age} onChange={e => setAge(e.target.value)} className="w-full bg-slate-700 border-slate-600 rounded-md shadow-sm text-slate-200 focus:ring-cyan-500 focus:border-cyan-500" />
        </div>
        <div>
          <label htmlFor="organization" className="block text-sm font-medium text-slate-300 mb-1">Organization</label>
          <input type="text" id="organization" value={organization} onChange={e => setOrganization(e.target.value)} className="w-full bg-slate-700 border-slate-600 rounded-md shadow-sm text-slate-200 focus:ring-cyan-500 focus:border-cyan-500" />
        </div>
        <button type="submit" disabled={isLoading} className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-cyan-600 hover:bg-cyan-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-cyan-500 focus:ring-offset-slate-800 disabled:bg-slate-500 disabled:cursor-not-allowed">
          {isLoading ? <LoadingSpinner /> : 'Analyze'}
        </button>
      </form>

      <div className="mt-6 flex-grow">
        {error && <div className="bg-red-900/50 text-red-300 p-3 rounded-md">{error}</div>}
        {report && (
          <div className="space-y-4">
            <div>
              <h3 className="text-lg font-semibold text-slate-200 mb-2">Analysis Result</h3>
              <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                <span className="font-semibold text-slate-400">Risk Score</span>
                <span className={`font-bold text-right ${getRiskColor(report.risk_score)}`}>{report.risk_score}/10</span>

                <span className="font-semibold text-slate-400">Category</span>
                <span className="text-right text-slate-200">{report.category}</span>

                <span className="font-semibold text-slate-400">Recommendation</span>
                <span className={`font-bold text-right ${getRecommendationColor(report.recommended_action)}`}>{report.recommended_action}</span>
              </div>
            </div>
            <CodeBlock code={JSON.stringify(report, null, 2)} />
          </div>
        )}
      </div>
    </div>
  );
};

export default ThreatAnalysisPanel;
