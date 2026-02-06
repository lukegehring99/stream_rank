import React from 'react';
import { Livestream } from '../types';
import { StreamCard } from './StreamCard';
import { StreamListSkeleton } from './LoadingSpinner';

interface StreamListProps {
  streams: Livestream[];
  loading: boolean;
  error: string | null;
  selectedStream: Livestream | null;
  onSelectStream: (stream: Livestream) => void;
  onRefresh: () => void;
  lastUpdated: Date | null;
  renderDetailPanel?: () => React.ReactNode;
}

export const StreamList: React.FC<StreamListProps> = ({
  streams,
  loading,
  error,
  selectedStream,
  onSelectStream,
  onRefresh,
  lastUpdated,
  renderDetailPanel,
}) => {
  if (loading && streams.length === 0) {
    return <StreamListSkeleton count={5} />;
  }

  if (error && streams.length === 0) {
    return (
      <div className="card p-8 text-center">
        <div className="w-14 h-14 mx-auto mb-4 rounded-full bg-red-50 dark:bg-red-950 flex items-center justify-center">
          <svg
            className="w-7 h-7 text-red-500"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
          </svg>
        </div>
        <h3 className="text-base font-semibold text-neutral-800 dark:text-neutral-200 mb-2">
          Unable to Load Streams
        </h3>
        <p className="text-sm text-neutral-500 dark:text-neutral-400 mb-4">{error}</p>
        <button onClick={onRefresh} className="btn btn-primary">
          <svg
            className="w-4 h-4 mr-2"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
            />
          </svg>
          Try Again
        </button>
      </div>
    );
  }

  if (streams.length === 0) {
    return (
      <div className="card p-8 text-center">
        <div className="w-14 h-14 mx-auto mb-4 rounded-full bg-neutral-100 dark:bg-neutral-800 flex items-center justify-center">
          <svg
            className="w-7 h-7 text-neutral-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"
            />
          </svg>
        </div>
        <h3 className="text-base font-semibold text-neutral-800 dark:text-neutral-200 mb-2">
          No Streams Found
        </h3>
        <p className="text-sm text-neutral-500 dark:text-neutral-400">
          There are no trending streams at the moment. Check back later!
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {/* Header with last updated */}
      <div className="flex items-center justify-between px-1 mb-3">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-neutral-600 dark:text-neutral-400">
            {streams.length} streams
          </span>
          {loading && (
            <span className="flex items-center gap-1.5 text-xs text-primary-600 dark:text-primary-400">
              <span className="w-1.5 h-1.5 bg-primary-500 rounded-full animate-pulse-soft" />
              Updating
            </span>
          )}
        </div>
        {lastUpdated && (
          <span className="text-xs text-neutral-400 dark:text-neutral-500">
            {lastUpdated.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
        )}
      </div>

      {/* Stream Cards with inline detail panel on mobile */}
      {streams.map((stream, index) => (
        <React.Fragment key={stream.id}>
          <div
            className="animate-in"
            style={{ animationDelay: `${index * 40}ms` }}
          >
            <StreamCard
              stream={stream}
              isSelected={selectedStream?.id === stream.id}
              onSelect={onSelectStream}
            />
          </div>
          {/* Show detail panel below selected stream on mobile */}
          {selectedStream?.id === stream.id && renderDetailPanel && (
            <div className="lg:hidden mt-2 animate-in">
              {renderDetailPanel()}
            </div>
          )}
        </React.Fragment>
      ))}
    </div>
  );
};
