
import React from 'react';

interface CodeBlockProps {
  code: string;
}

const CodeBlock: React.FC<CodeBlockProps> = ({ code }) => {
  return (
    <div className="bg-slate-900 rounded-md p-4 overflow-x-auto">
      <pre>
        <code className="text-sm text-cyan-300 font-mono">
          {code}
        </code>
      </pre>
    </div>
  );
};

export default CodeBlock;
