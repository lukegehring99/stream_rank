import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { format } from 'date-fns';
import { anomalyConfigApi, publicApi } from '../api/client';
import { AnomalyConfigEntry, TrendingResponse } from '../types';

// Default widget URL - can be overridden via env or UI
const DEFAULT_WIDGET_URL = import.meta.env.VITE_WIDGET_URL || 'http://localhost:3000';
const GITHUB_PAGES_URL = import.meta.env.VITE_WIDGET_GITHUB_URL || '';

// Group config keys by category for better UX
const CONFIG_CATEGORIES: Record<string, { label: string; keys: string[] }> = {
  general: {
    label: 'General Settings',
    keys: ['algorithm', 'recent_window_minutes', 'baseline_hours', 'min_recent_samples', 'min_baseline_samples', 'inactive_threshold_minutes', 'logistic_midpoint', 'logistic_steepness'],
  },
  scoring: {
    label: 'Score Settings',
    keys: ['score_min', 'score_max'],
  },
  quantile: {
    label: 'Quantile Algorithm',
    keys: ['quantile_params.baseline_percentile', 'quantile_params.recent_percentile', 'quantile_params.spike_threshold', 'quantile_params.high_traffic_multiplier'],
  },
  zscore: {
    label: 'Z-Score Algorithm',
    keys: ['zscore_params.zscore_threshold', 'zscore_params.use_modified_zscore', 'zscore_params.min_std_floor', 'zscore_params.clamp_negative'],
  },
};

export const AnomalyView: React.FC = () => {
  const queryClient = useQueryClient();
  const [widgetUrl, setWidgetUrl] = useState(DEFAULT_WIDGET_URL);
  const [customUrl, setCustomUrl] = useState('');
  const [showUrlInput, setShowUrlInput] = useState(false);
  const [useExperimental, setUseExperimental] = useState(true); // Default to experimental
  const [editingKey, setEditingKey] = useState<string | null>(null);
  const [editValue, setEditValue] = useState('');
  const [configExpanded, setConfigExpanded] = useState(false);

  // Fetch trending data based on mode
  const { data: trendingData, isLoading, error, refetch } = useQuery<TrendingResponse>({
    queryKey: ['trending-debug', useExperimental],
    queryFn: async () => {
      if (useExperimental) {
        return publicApi.getExperimentalTrending(10);
      }
      return publicApi.getTrending(10);
    },
    refetchInterval: 30000,
  });

  // Fetch anomaly config
  const { data: configData, isLoading: configLoading } = useQuery({
    queryKey: ['anomaly-config'],
    queryFn: () => anomalyConfigApi.getAll(),
  });

  // Update config mutation
  const updateMutation = useMutation({
    mutationFn: ({ key, value }: { key: string; value: string }) =>
      anomalyConfigApi.update(key, value),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['anomaly-config'] });
      queryClient.invalidateQueries({ queryKey: ['trending-debug'] });
      setEditingKey(null);
      setEditValue('');
    },
  });

  // Reset config mutation
  const resetMutation = useMutation({
    mutationFn: (key: string) => anomalyConfigApi.reset(key),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['anomaly-config'] });
      queryClient.invalidateQueries({ queryKey: ['trending-debug'] });
    },
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

  const handleEditStart = (entry: AnomalyConfigEntry) => {
    setEditingKey(entry.key);
    setEditValue(entry.value);
  };

  const handleEditSave = () => {
    if (editingKey) {
      updateMutation.mutate({ key: editingKey, value: editValue });
    }
  };

  const handleEditCancel = () => {
    setEditingKey(null);
    setEditValue('');
  };

  const getConfigByKey = (key: string): AnomalyConfigEntry | undefined => {
    return configData?.items.find((item) => item.key === key);
  };

  const renderConfigInput = (entry: AnomalyConfigEntry) => {
    const isEditing = editingKey === entry.key;
    
    if (entry.type === 'bool') {
      return (
        <select
          value={isEditing ? editValue : entry.value}
          onChange={(e) => {
            if (!isEditing) {
              updateMutation.mutate({ key: entry.key, value: e.target.value });
            } else {
              setEditValue(e.target.value);
            }
          }}
          className="form-input text-sm py-1 w-24"
          disabled={updateMutation.isPending}
        >
          <option value="true">true</option>
          <option value="false">false</option>
        </select>
      );
    }

    if (entry.key === 'algorithm') {
      return (
        <select
          value={isEditing ? editValue : entry.value}
          onChange={(e) => {
            updateMutation.mutate({ key: entry.key, value: e.target.value });
          }}
          className="form-input text-sm py-1 w-32"
          disabled={updateMutation.isPending}
        >
          <option value="quantile">quantile</option>
          <option value="zscore">zscore</option>
        </select>
      );
    }

    if (isEditing) {
      return (
        <div className="flex items-center gap-2">
          <input
            type={entry.type === 'int' || entry.type === 'float' ? 'number' : 'text'}
            step={entry.type === 'float' ? '0.1' : '1'}
            value={editValue}
            onChange={(e) => setEditValue(e.target.value)}
            className="form-input text-sm py-1 w-24"
            autoFocus
          />
          <button
            onClick={handleEditSave}
            disabled={updateMutation.isPending}
            className="text-green-600 hover:text-green-700"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </button>
          <button
            onClick={handleEditCancel}
            className="text-gray-400 hover:text-gray-600"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      );
    }

    return (
      <button
        onClick={() => handleEditStart(entry)}
        className="text-sm font-mono bg-gray-100 px-2 py-1 rounded hover:bg-gray-200 transition-colors"
      >
        {entry.value}
      </button>
    );
  };

  const renderConfigCategory = (categoryKey: string, category: typeof CONFIG_CATEGORIES[string]) => {
    return (
      <div key={categoryKey} className="mb-4">
        <h4 className="text-sm font-semibold text-gray-700 mb-2">{category.label}</h4>
        <div className="space-y-2">
          {category.keys.map((key) => {
            const entry = getConfigByKey(key);
            if (!entry) return null;
            
            return (
              <div key={key} className="flex items-center justify-between py-2 px-3 bg-gray-50 rounded-lg">
                <div className="flex items-center gap-2">
                  <span className="text-sm text-gray-700 font-mono">{key}</span>
                  {entry.is_default && (
                    <span className="text-xs bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded">default</span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  {renderConfigInput(entry)}
                  {!entry.is_default && (
                    <button
                      onClick={() => resetMutation.mutate(key)}
                      disabled={resetMutation.isPending}
                      className="text-gray-400 hover:text-gray-600"
                      title="Reset to default"
                    >
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                      </svg>
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
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
        <div className="card-header flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900">Debug Information</h3>
          {/* Experimental Toggle */}
          <div className="flex items-center gap-3">
            <span className="text-sm text-gray-500">Data Source:</span>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={useExperimental}
                onChange={(e) => setUseExperimental(e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
              <span className="ml-2 text-sm font-medium text-gray-900">
                {useExperimental ? 'Experimental' : 'Production'}
              </span>
            </label>
          </div>
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
                  {useExperimental ? 'Bypassed' : cachedAt ? 'Cached' : 'Not Cached'}
                </p>
              )}
            </div>

            {/* Cached At */}
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-500">Cached At</p>
              {isLoading ? (
                <div className="h-6 bg-gray-200 rounded animate-pulse w-40 mt-1" />
              ) : useExperimental ? (
                <p className="text-sm font-medium text-gray-400">N/A (Experimental)</p>
              ) : cachedAt ? (
                <p className="text-sm font-medium text-gray-900">
                  {format(cachedAt, 'MMM d, yyyy HH:mm:ss')}
                </p>
              ) : (
                <p className="text-sm font-medium text-gray-400">-</p>
              )}
            </div>

            {/* Mode Indicator */}
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-500">Mode</p>
              <p className={`text-sm font-medium ${useExperimental ? 'text-amber-600' : 'text-green-600'}`}>
                {useExperimental ? '🧪 Experimental' : '✓ Production'}
              </p>
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

          {/* Anomaly Detection Settings (Collapsible) */}
          <div className="mt-4 pt-4 border-t border-gray-200">
            <button
              onClick={() => setConfigExpanded(!configExpanded)}
              className="flex items-center justify-between w-full text-left"
            >
              <div className="flex items-center gap-2">
                <svg
                  className={`w-4 h-4 text-gray-500 transition-transform ${configExpanded ? 'rotate-90' : ''}`}
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
                <span className="text-sm font-semibold text-gray-700">
                  Anomaly Detection Configuration
                </span>
                {useExperimental && (
                  <span className="text-xs bg-amber-100 text-amber-700 px-2 py-0.5 rounded">
                    Live - changes apply immediately
                  </span>
                )}
              </div>
              {configLoading && (
                <div className="h-4 w-4 border-2 border-gray-300 border-t-primary-600 rounded-full animate-spin" />
              )}
            </button>

            {configExpanded && configData && (
              <div className="mt-4 space-y-4">
                {Object.entries(CONFIG_CATEGORIES).map(([key, category]) =>
                  renderConfigCategory(key, category)
                )}
              </div>
            )}
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
          <div className="flex items-center gap-3">
            {useExperimental && (
              <span className="text-xs bg-amber-100 text-amber-700 px-2 py-1 rounded-full font-medium">
                Experimental Mode
              </span>
            )}
            <a
              href={useExperimental ? `${widgetUrl}?experimental=true` : widgetUrl}
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
        </div>
        <div className="relative bg-slate-900" style={{ height: '800px' }}>
          <iframe
            key={useExperimental ? 'experimental' : 'production'}
            src={useExperimental ? `${widgetUrl}?experimental=true` : widgetUrl}
            title="Public Widget Preview"
            className="absolute inset-0 w-full h-full border-0"
            sandbox="allow-scripts allow-same-origin allow-popups"
          />
        </div>
      </div>
    </div>
  );
};
