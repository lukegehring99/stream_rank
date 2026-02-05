import axios, { AxiosError, AxiosInstance, InternalAxiosRequestConfig } from 'axios';
import { ApiError } from '../types';

const BASE_URL = '/api/v1';

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
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
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

  getHistory: async (id: string, params?: { page?: number; page_size?: number }) => {
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
