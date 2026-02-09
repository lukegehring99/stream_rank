import React, { useState } from 'react';
import { useConfig } from './hooks/useConfig';
import { useStreams, useViewership } from './hooks/useStreams';
import { StreamList } from './components/StreamList';
import { YouTubePlayer } from './components/YouTubePlayer';
import { ViewershipChart } from './components/ViewershipChart';
import { Livestream, formatViewerCount } from './types';

const App: React.FC = () => {
  const config = useConfig();
  const { streams, loading, error, lastUpdated, refresh } = useStreams(
    config.apiBaseUrl,
    config.count,
    config.refreshMinutes,
    config.experimental
  );

  const [selectedStream, setSelectedStream] = useState<Livestream | null>(null);

  const {
    data: viewershipData,
    loading: viewershipLoading,
    error: viewershipError,
  } = useViewership(
    config.apiBaseUrl,
    selectedStream?.youtube_video_id ?? null
  );

  const handleSelectStream = (stream: Livestream) => {
    setSelectedStream(selectedStream?.id === stream.id ? null : stream);
  };

  const handleClosePlayer = () => {
    setSelectedStream(null);
  };

  // Render the detail panel content (shared between mobile and desktop)
  const renderDetailPanel = () => {
    if (!selectedStream) return null;

    return (
      <div className="space-y-3">
        {/* YouTube Player */}
        <YouTubePlayer
          videoId={selectedStream.youtube_video_id}
          title={selectedStream.name}
          onClose={handleClosePlayer}
        />

        {/* Stream Stats */}
        <div className="card p-4">
          <div className="grid grid-cols-3 gap-4">
            <div className="text-center">
              <div className="stat-value bg-gradient-to-r from-sunny-400 to-coral-500 bg-clip-text text-transparent">
                #{selectedStream.rank}
              </div>
              <div className="stat-label">Rank</div>
            </div>
            <div className="text-center">
              <div className="stat-value bg-gradient-to-r from-accent-500 to-coral-500 bg-clip-text text-transparent">
                {selectedStream.trend_score ?? '-'}
              </div>
              <div className="stat-label">Trend</div>
            </div>
            <div className="text-center">
              <div className="stat-value bg-gradient-to-r from-primary-500 to-accent-500 bg-clip-text text-transparent">
                {formatViewerCount(selectedStream.current_viewers)}
              </div>
              <div className="stat-label">Viewers</div>
            </div>
          </div>
        </div>

        {/* Viewership Chart */}
        <div className="card p-4">
          <h3 className="text-sm font-semibold text-neutral-700 dark:text-neutral-300 mb-3">
            Viewership (Last 24 Hours)
          </h3>
          <ViewershipChart
            data={viewershipData}
            loading={viewershipLoading}
            error={viewershipError}
            theme={config.theme}
          />
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-white/70 dark:bg-neutral-950/70 backdrop-blur-xl border-b border-neutral-200/50 dark:border-neutral-800/50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-14">
            <div className="flex items-center gap-2.5">
              <div className="w-9 h-9 flex items-center justify-center">
                <img
                  src="/logo.svg"
                  alt="Logo"
                  className="w-9 h-9 object-contain"
                />
              </div>
              <div>
                <h1 className="text-base font-bold gradient-text">
                  Trending Live
                </h1>
              </div>
            </div>

            <div className="flex items-center gap-2">
              {/* Refresh Button */}
              <button
                onClick={refresh}
                disabled={loading}
                className="btn btn-ghost p-2 rounded-xl"
                title="Refresh"
              >
                <svg
                  className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`}
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
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
          {/* Stream List */}
          <div className={`${selectedStream ? 'lg:col-span-2' : 'lg:col-span-5'} transition-all duration-300`}>
            <StreamList
              streams={streams}
              loading={loading}
              error={error}
              selectedStream={selectedStream}
              onSelectStream={handleSelectStream}
              onRefresh={refresh}
              lastUpdated={lastUpdated}
              renderDetailPanel={renderDetailPanel}
            />
          </div>

          {/* Player Panel - Desktop only */}
          {selectedStream && (
            <div className="hidden lg:block lg:col-span-3 animate-fade-in">
              {renderDetailPanel()}
            </div>
          )}
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-neutral-100 dark:border-neutral-800 mt-6">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3">
          <p className="text-xs text-center text-neutral-400 dark:text-neutral-600">
            Refreshes every {config.refreshMinutes} min • YouTube Data API
          </p>
        </div>
      </footer>
    </div>
  );
};

export default App;
