import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { format } from 'date-fns';

// Default widget URL - can be overridden via env or UI
const DEFAULT_WIDGET_URL = import.meta.env.VITE_WIDGET_URL || 'http://localhost:3000';
const GITHUB_PAGES_URL = import.meta.env.VITE_WIDGET_GITHUB_URL || '';

interface TrendingResponse {
  items: Array<{
    id: string;
    youtube_video_id: string;
    name: string;
    channel: string;
    current_viewers: number;
    rank: number;
    trend_score: number;
  }>;
  count: number;
  cached_at: string | null;
}

export const AnomalyView: React.FC = () => {
  const [widgetUrl, setWidgetUrl] = useState(DEFAULT_WIDGET_URL);
  const [customUrl, setCustomUrl] = useState('');
  const [showUrlInput, setShowUrlInput] = useState(false);

  // Fetch trending data to get cached_at info
  const { data: trendingData, isLoading, error, refetch } = useQuery<TrendingResponse>({
    queryKey: ['trending-debug'],
    queryFn: async () => {
      const response = await fetch('/api/v1/livestreams?count=10');
      if (!response.ok) throw new Error('Failed to fetch trending data');
      return response.json();
    },
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  // Parse UTC timestamp
  const parseUTC = (timestamp: string | null) => {
    if (!timestamp) return null;
    return new Date(timestamp.endsWith('Z') ? timestamp : timestamp + 'Z');
  };

  const cachedAt = trendingData?.cached_at ? parseUTC(trendingData.cached_at) : null;

  const handleUrlPresetChange = (preset: string) => {
    if (preset === 'local') {
      setWidgetUrl(DEFAULT_WIDGET_URL);
      setShowUrlInput(false);
    } else if (preset === 'github' && GITHUB_PAGES_URL) {
      setWidgetUrl(GITHUB_PAGES_URL);
      setShowUrlInput(false);
    } else if (preset === 'custom') {
      setShowUrlInput(true);
    }
  };

  const applyCustomUrl = () => {
    if (customUrl.trim()) {
      setWidgetUrl(customUrl.trim());
      setShowUrlInput(false);
    }
  };

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Anomaly View</h1>
          <p className="text-gray-500 mt-1">
            Preview the public trending view and debug anomaly detection
          </p>
        </div>
        <button
          onClick={() => refetch()}
          className="btn-secondary btn-sm"
        >
          <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Refresh Debug Info
        </button>
      </div>

      {/* Debug Info Panel */}
      <div className="card">
        <div className="card-header">
          <h3 className="text-lg font-semibold text-gray-900">Debug Information</h3>
        </div>
        <div className="card-body">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Cache Status */}
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-500">Cache Status</p>
              {isLoading ? (
                <div className="h-6 bg-gray-200 rounded animate-pulse w-24 mt-1" />
              ) : error ? (
                <p className="text-sm font-medium text-red-600">Error</p>
              ) : (
                <p className="text-sm font-medium text-gray-900">
                  {cachedAt ? 'Cached' : 'Not Cached'}
                </p>
              )}
            </div>

            {/* Cached At */}
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-500">Cached At</p>
              {isLoading ? (
                <div className="h-6 bg-gray-200 rounded animate-pulse w-40 mt-1" />
              ) : cachedAt ? (
                <p className="text-sm font-medium text-gray-900">
                  {format(cachedAt, 'MMM d, yyyy HH:mm:ss')}
                </p>
              ) : (
                <p className="text-sm font-medium text-gray-400">-</p>
              )}
            </div>

            {/* Cache Age */}
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-500">Cache Age</p>
              {isLoading ? (
                <div className="h-6 bg-gray-200 rounded animate-pulse w-20 mt-1" />
              ) : cachedAt ? (
                <p className="text-sm font-medium text-gray-900">
                  {Math.round((Date.now() - cachedAt.getTime()) / 1000)}s ago
                </p>
              ) : (
                <p className="text-sm font-medium text-gray-400">-</p>
              )}
            </div>

            {/* Streams Count */}
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-500">Trending Streams</p>
              {isLoading ? (
                <div className="h-6 bg-gray-200 rounded animate-pulse w-12 mt-1" />
              ) : (
                <p className="text-sm font-medium text-gray-900">
                  {trendingData?.count ?? 0}
                </p>
              )}
            </div>
          </div>

          {/* Future: Anomaly Detection Dropdown */}
          <div className="mt-4 pt-4 border-t border-gray-200">
            <p className="text-xs text-gray-400 mb-2">
              Future controls: Anomaly detection method selector will be added here
            </p>
            <select 
              disabled 
              className="form-input w-full md:w-64 opacity-50 cursor-not-allowed"
            >
              <option>Quantile Strategy (default)</option>
              <option>Z-Score Strategy</option>
              <option>Percent Change Strategy</option>
            </select>
          </div>
        </div>
      </div>

      {/* Widget URL Configuration */}
      <div className="card">
        <div className="card-header flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900">Widget Source</h3>
          <div className="flex items-center gap-2">
            <select
              onChange={(e) => handleUrlPresetChange(e.target.value)}
              className="form-input text-sm py-1"
              defaultValue="local"
            >
              <option value="local">Local Development (localhost:3000)</option>
              {GITHUB_PAGES_URL && (
                <option value="github">GitHub Pages</option>
              )}
              <option value="custom">Custom URL...</option>
            </select>
          </div>
        </div>
        
        {showUrlInput && (
          <div className="px-6 py-3 border-b border-gray-200 bg-gray-50">
            <div className="flex gap-2">
              <input
                type="url"
                value={customUrl}
                onChange={(e) => setCustomUrl(e.target.value)}
                placeholder="https://yourusername.github.io/stream-rank-widget/"
                className="form-input flex-1"
              />
              <button
                onClick={applyCustomUrl}
                className="btn-primary"
              >
                Apply
              </button>
              <button
                onClick={() => setShowUrlInput(false)}
                className="btn-secondary"
              >
                Cancel
              </button>
            </div>
          </div>
        )}
        
        <div className="p-2 bg-gray-100 text-xs text-gray-500 flex items-center gap-2">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
          </svg>
          <span className="truncate">{widgetUrl}</span>
        </div>
      </div>

      {/* Public Widget Preview (iframe) */}
      <div className="card overflow-hidden">
        <div className="card-header flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900">Public Widget Preview</h3>
          <a
            href={widgetUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm text-primary-600 hover:text-primary-700 flex items-center gap-1"
          >
            Open in New Tab
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
          </a>
        </div>
        <div className="relative bg-slate-900" style={{ height: '800px' }}>
          <iframe
            src={widgetUrl}
            title="Public Widget Preview"
            className="absolute inset-0 w-full h-full border-0"
            sandbox="allow-scripts allow-same-origin allow-popups"
          />
        </div>
      </div>
    </div>
  );
};
