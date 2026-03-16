import React from 'react';

interface SkeletonLoaderProps {
  className?: string;
  count?: number;
  variant?: 'card' | 'text' | 'list-item' | 'table-row';
}

const SkeletonLoader: React.FC<SkeletonLoaderProps> = ({ 
  className = '', 
  count = 1, 
  variant = 'card' 
}) => {
  const baseClasses = 'animate-pulse bg-slate-700/50 rounded';
  
  const variantClasses = {
    card: 'h-24 rounded-lg',
    text: 'h-4 rounded',
    'list-item': 'h-16 rounded-lg',
    'table-row': 'h-12 rounded'
  };
  
  const classes = `${baseClasses} ${variantClasses[variant]} ${className}`;
  
  return (
    <div className="space-y-2">
      {Array.from({ length: count }).map((_, index) => (
        <div key={index} className={classes} />
      ))}
    </div>
  );
};

export default SkeletonLoader;