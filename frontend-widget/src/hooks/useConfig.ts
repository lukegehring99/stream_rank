import { useMemo, useEffect } from 'react';
import { WidgetConfig, DEFAULT_CONFIG } from '../types';

function parseQueryParams(): Partial<WidgetConfig> {
  const params = new URLSearchParams(window.location.search);
  const config: Partial<WidgetConfig> = {};

  const count = params.get('count');
  if (count) {
    const parsed = parseInt(count, 10);
    if (!isNaN(parsed) && parsed > 0 && parsed <= 100) {
      config.count = parsed;
    }
  }

  const refreshMinutes = params.get('refreshMinutes');
  if (refreshMinutes) {
    const parsed = parseInt(refreshMinutes, 10);
    if (!isNaN(parsed) && parsed >= 1 && parsed <= 60) {
      config.refreshMinutes = parsed;
    }
  }

  const apiBaseUrl = params.get('apiBaseUrl');
  if (apiBaseUrl) {
    try {
      new URL(apiBaseUrl);
      config.apiBaseUrl = apiBaseUrl;
    } catch {
      // Invalid URL, ignore
    }
  }

  const theme = params.get('theme');
  if (theme === 'light' || theme === 'dark') {
    config.theme = theme;
  }

  // Hidden experimental flag - not exposed in public UI
  const experimental = params.get('experimental');
  if (experimental === 'true' || experimental === '1') {
    config.experimental = true;
  }

  return config;
}

export function useConfig(): WidgetConfig {
  const config = useMemo(() => {
    const queryParams = parseQueryParams();
    return {
      ...DEFAULT_CONFIG,
      ...queryParams,
    };
  }, []);

  // Apply theme to document
  useEffect(() => {
    const root = document.documentElement;
    if (config.theme === 'dark') {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
  }, [config.theme]);

  return config;
}
