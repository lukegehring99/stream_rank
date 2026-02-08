import axios, { AxiosError, AxiosInstance, InternalAxiosRequestConfig } from 'axios';
import { ApiError, AnomalyConfigEntry, AnomalyConfigListResponse } from '../types';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

// Create axios instance
export const apiClient: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem('access_token');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor to handle errors
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<ApiError>) => {
    if (error.response?.status === 401) {
      // Clear token and redirect to login
      localStorage.removeItem('access_token');
      const loginPath = `${import.meta.env.BASE_URL || '/'}login`;
      if (window.location.pathname !== loginPath) {
        window.location.href = loginPath;
      }
    }
    return Promise.reject(error);
  }
);

// Auth API
export const authApi = {
  login: async (username: string, password: string) => {
    const response = await apiClient.post('/auth/login', {
      username,
      password,
    });
    return response.data;
  },
};

// Livestreams API
export const livestreamsApi = {
  getAll: async (params?: {
    page?: number;
    page_size?: number;
    search?: string;
    is_live?: boolean;
    sort_by?: string;
    sort_order?: string;
  }) => {
    const response = await apiClient.get('/admin/livestreams', { params });
    return response.data;
  },

  getById: async (id: string) => {
    const response = await apiClient.get(`/admin/livestreams/${id}`);
    return response.data;
  },

  create: async (data: { youtube_url: string }) => {
    const response = await apiClient.post('/admin/livestreams', data);
    return response.data;
  },

  update: async (id: string, data: { name?: string; channel?: string; is_live?: boolean }) => {
    const response = await apiClient.put(`/admin/livestreams/${id}`, data);
    return response.data;
  },

  delete: async (id: string) => {
    const response = await apiClient.delete(`/admin/livestreams/${id}`);
    return response.data;
  },

  getHistory: async (id: string, params?: { 
    page?: number; 
    page_size?: number;
    start_time?: string;
    end_time?: string;
    downsample?: '1m' | '5m' | '10m' | '1hr';
  }) => {
    const response = await apiClient.get(`/admin/livestreams/${id}/history`, { params });
    return response.data;
  },

  getStats: async () => {
    const response = await apiClient.get('/admin/stats');
    return response.data;
  },
};

// Helper to extract video ID from YouTube URL
export const extractVideoId = (urlOrId: string): string => {
  // If it's already a video ID (11 characters, alphanumeric)
  if (/^[a-zA-Z0-9_-]{11}$/.test(urlOrId)) {
    return urlOrId;
  }

  // Try to extract from various YouTube URL formats
  const patterns = [
    /(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/|youtube\.com\/v\/)([a-zA-Z0-9_-]{11})/,
    /youtube\.com\/live\/([a-zA-Z0-9_-]{11})/,
  ];

  for (const pattern of patterns) {
    const match = urlOrId.match(pattern);
    if (match) {
      return match[1];
    }
  }

  // Return as-is if no pattern matches (let the backend validate)
  return urlOrId;
};

// Anomaly Config API
export const anomalyConfigApi = {
  getAll: async (): Promise<AnomalyConfigListResponse> => {
    const response = await apiClient.get('/admin/anomaly-config');
    return response.data;
  },

  update: async (key: string, value: string): Promise<{ success: boolean; entry: AnomalyConfigEntry }> => {
    const response = await apiClient.put('/admin/anomaly-config', { key, value });
    return response.data;
  },

  reset: async (key: string): Promise<{ success: boolean; entry: AnomalyConfigEntry }> => {
    const response = await apiClient.delete(`/admin/anomaly-config/${key}`);
    return response.data;
  },
};

// Public API (for fetching experimental data)
export const publicApi = {
  getTrending: async (count: number = 10) => {
    const response = await apiClient.get(`/livestreams?count=${count}`);
    return response.data;
  },

  getExperimentalTrending: async (count: number = 10) => {
    const response = await apiClient.get(`/livestreams/experimental?count=${count}`);
    return response.data;
  },
};
