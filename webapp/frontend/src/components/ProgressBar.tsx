import React from 'react';

interface ProgressBarProps {
  progress: number; // 0-100
  message?: string;
  variant?: 'primary' | 'success' | 'warning' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  animated?: boolean;
}

export const ProgressBar: React.FC<ProgressBarProps> = ({
  progress,
  message,
  variant = 'primary',
  size = 'md',
  animated = false,
}) => {
  const sizeClasses = {
    sm: 'h-2',
    md: 'h-3',
    lg: 'h-4',
  };

  const variantClasses = {
    primary: 'bg-primary',
    success: 'bg-success',
    warning: 'bg-warning',
    danger: 'bg-danger',
  };

  return (
    <div className="w-full">
      {message && (
        <div className="flex justify-between items-center mb-2">
          <span className="text-sm font-medium text-gray-700">
            {message}
          </span>
          <span className="text-sm font-medium text-gray-500">
            {progress}%
          </span>
        </div>
      )}
      
      <div className={`w-full bg-gray-200 rounded-full ${sizeClasses[size]}`}>
        <div
          className={`
            ${variantClasses[variant]} 
            ${sizeClasses[size]} 
            rounded-full 
            transition-all 
            duration-500 
            ease-in-out
            ${animated ? 'animate-pulse' : ''}
          `}
          style={{ width: `${Math.min(Math.max(progress, 0), 100)}%` }}
        />
      </div>
    </div>
  );
};

export default ProgressBar;
