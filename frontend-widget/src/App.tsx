import React, { useState } from 'react';
import { useConfig } from './hooks/useConfig';
import { useStreams, useViewership } from './hooks/useStreams';
import { StreamList } from './components/StreamList';
import { YouTubePlayer } from './components/YouTubePlayer';
import { ViewershipChart } from './components/ViewershipChart';
import { Livestream } from './types';

const App: React.FC = () => {
  const config = useConfig();
  const { streams, loading, error, lastUpdated, refresh } = useStreams(
    config.apiBaseUrl,
    config.count,
    config.refreshMinutes
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

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800">
      {/* Header */}
      <header className="sticky top-0 z-50 glass border-b border-slate-200/50 dark:border-slate-700/50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center shadow-glow-sm">
                <svg
                  className="w-6 h-6 text-white"
                  fill="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z" />
                </svg>
              </div>
              <div>
                <h1 className="text-xl font-bold gradient-text">
                  Trending Livestreams
                </h1>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Real-time YouTube stream rankings
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              {/* Refresh Button */}
              <button
                onClick={refresh}
                disabled={loading}
                className="btn btn-ghost p-2"
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

              {/* Config Info */}
              <div className="hidden sm:flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
                <span className="px-2 py-1 rounded bg-slate-100 dark:bg-slate-700">
                  {config.count} streams
                </span>
                <span className="px-2 py-1 rounded bg-slate-100 dark:bg-slate-700">
                  {config.refreshMinutes}m refresh
                </span>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
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
            />
          </div>

          {/* Player Panel */}
          {selectedStream && (
            <div className="lg:col-span-3 space-y-4 animate-slide-in">
              {/* YouTube Player */}
              <YouTubePlayer
                videoId={selectedStream.youtube_video_id}
                title={selectedStream.name}
                onClose={handleClosePlayer}
              />

              {/* Stream Stats */}
              <div className="card p-4">
                <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3">
                  Stream Statistics
                </h3>
                <div className="grid grid-cols-3 gap-4">
                  <div className="text-center">
                    <div className="stat-value text-primary-500">
                      #{selectedStream.rank}
                    </div>
                    <div className="stat-label">Rank</div>
                  </div>
                  <div className="text-center">
                    <div className="stat-value text-accent-500">
                      {selectedStream.trend_score}
                    </div>
                    <div className="stat-label">Trend Score</div>
                  </div>
                  <div className="text-center">
                    <div className="stat-value text-green-500">
                      {selectedStream.current_viewers.toLocaleString()}
                    </div>
                    <div className="stat-label">Viewers</div>
                  </div>
                </div>
              </div>

              {/* Viewership Chart */}
              <div className="card p-4">
                <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3">
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
          )}
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-200 dark:border-slate-700 mt-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <p className="text-xs text-center text-slate-400 dark:text-slate-500">
            Data refreshes every {config.refreshMinutes} minutes •{' '}
            Powered by YouTube Data API
          </p>
        </div>
      </footer>
    </div>
  );
};

export default App;
