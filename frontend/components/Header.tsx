
import React from 'react';

const ShieldIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8 text-cyan-400" viewBox="0 0 20 20" fill="currentColor">
    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
  </svg>
);

const Header: React.FC = () => {
  return (
    <header className="bg-slate-900/70 backdrop-blur-sm shadow-md p-4 sticky top-0 z-10 w-full">
      <div className="max-w-7xl mx-auto flex items-center gap-4">
        <ShieldIcon />
        <h1 className="text-2xl font-bold text-slate-100 tracking-wider">
          Network Guardian <span className="text-cyan-400">AI</span>
        </h1>
      </div>
    </header>
  );
};

export default Header;
