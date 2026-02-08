import { useState, useEffect, useCallback, useRef } from 'react';
import { Livestream, ViewershipDataPoint } from '../types';
import {
  fetchTrendingStreams,
  fetchViewershipHistory,
  generateMockStreams,
  generateMockViewership,
  ApiError,
} from '../api/client';

interface UseStreamsReturn {
  streams: Livestream[];
  loading: boolean;
  error: string | null;
  lastUpdated: Date | null;
  refresh: () => Promise<void>;
}

interface UseViewershipReturn {
  data: ViewershipDataPoint[];
  loading: boolean;
  error: string | null;
}

const USE_MOCK_DATA = import.meta.env.DEV && !import.meta.env.VITE_USE_REAL_API;

export function useStreams(
  apiBaseUrl: string,
  count: number,
  refreshMinutes: number,
  experimental = false
): UseStreamsReturn {
  const [streams, setStreams] = useState<Livestream[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const intervalRef = useRef<number | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      let data: Livestream[];
      if (USE_MOCK_DATA) {
        // Simulate network delay
        await new Promise((resolve) => setTimeout(resolve, 500));
        data = generateMockStreams(count);
      } else {
        data = await fetchTrendingStreams(apiBaseUrl, count, experimental);
      }

      setStreams(data);
      setLastUpdated(new Date());
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message
          : 'An unexpected error occurred';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [apiBaseUrl, count, experimental]);

  useEffect(() => {
    fetchData();

    // Set up polling interval
    intervalRef.current = window.setInterval(
      fetchData,
      refreshMinutes * 60 * 1000
    );

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [fetchData, refreshMinutes]);

  return {
    streams,
    loading,
    error,
    lastUpdated,
    refresh: fetchData,
  };
}

export function useViewership(
  apiBaseUrl: string,
  videoId: string | null,
  hours = 24
): UseViewershipReturn {
  const [data, setData] = useState<ViewershipDataPoint[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!videoId) {
      setData([]);
      return;
    }

    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);

        let history: ViewershipDataPoint[];
        if (USE_MOCK_DATA) {
          await new Promise((resolve) => setTimeout(resolve, 300));
          history = generateMockViewership(hours);
        } else {
          history = await fetchViewershipHistory(apiBaseUrl, videoId, hours);
        }

        setData(history);
      } catch (err) {
        const message =
          err instanceof ApiError
            ? err.message
            : 'Unable to load viewership data';
        setError(message);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [apiBaseUrl, videoId, hours]);

  return { data, loading, error };
}
