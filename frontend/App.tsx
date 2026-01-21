import React from 'react';
import Header from './components/Header';
import Dashboard from './components/Dashboard';

const App: React.FC = () => {
  return (
    <div className="min-h-screen bg-slate-900 font-sans flex flex-col">
      <Header />
      <main className="flex-grow p-4 lg:p-6 max-w-7xl mx-auto w-full">
        <Dashboard />
      </main>
    </div>
  );
};

export default App;
