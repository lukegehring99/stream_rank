import React from 'react';
import clsx from 'clsx';

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  label?: string;
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  size = 'md',
  className,
  label = 'Loading...',
}) => {
  const sizeClasses = {
    sm: 'w-4 h-4 border-2',
    md: 'w-6 h-6 border-2',
    lg: 'w-10 h-10 border-3',
  };

  return (
    <div
      className={clsx('flex flex-col items-center justify-center gap-2', className)}
      role="status"
      aria-label={label}
    >
      <div
        className={clsx(
          'rounded-full border-primary-500 border-t-transparent animate-spin',
          sizeClasses[size]
        )}
      />
      {label && (
        <span className="text-xs text-neutral-500 dark:text-neutral-400">
          {label}
        </span>
      )}
    </div>
  );
};

interface SkeletonProps {
  className?: string;
}

export const Skeleton: React.FC<SkeletonProps> = ({ className }) => (
  <div
    className={clsx(
      'animate-pulse bg-neutral-100 dark:bg-neutral-800 rounded',
      className
    )}
  />
);

export const StreamCardSkeleton: React.FC = () => (
  <div className="card p-3 animate-pulse">
    <div className="flex items-center gap-3">
      <Skeleton className="w-8 h-8 rounded-lg flex-shrink-0" />
      <div className="flex-1 space-y-2">
        <Skeleton className="h-4 w-3/4" />
        <Skeleton className="h-3 w-1/2" />
        <div className="flex gap-2 pt-0.5">
          <Skeleton className="h-5 w-12 rounded-full" />
          <Skeleton className="h-5 w-16 rounded-full" />
        </div>
      </div>
      <Skeleton className="w-24 h-14 rounded-lg flex-shrink-0" />
    </div>
  </div>
);

export const StreamListSkeleton: React.FC<{ count?: number }> = ({
  count = 5,
}) => (
  <div className="space-y-2">
    {Array.from({ length: count }, (_, i) => (
      <StreamCardSkeleton key={i} />
    ))}
  </div>
);
