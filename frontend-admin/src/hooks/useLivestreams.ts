import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { livestreamsApi } from '../api/client';
import { Livestream, LivestreamFilters, LivestreamUpdate, PaginatedResponse } from '../types';
import toast from 'react-hot-toast';

// Query keys
export const livestreamKeys = {
  all: ['livestreams'] as const,
  lists: () => [...livestreamKeys.all, 'list'] as const,
  list: (filters: LivestreamFilters) => [...livestreamKeys.lists(), filters] as const,
  details: () => [...livestreamKeys.all, 'detail'] as const,
  detail: (id: string) => [...livestreamKeys.details(), id] as const,
  history: (id: string) => [...livestreamKeys.detail(id), 'history'] as const,
  stats: () => [...livestreamKeys.all, 'stats'] as const,
};

// Fetch all livestreams with filters
export const useLivestreams = (filters: LivestreamFilters = {}) => {
  return useQuery<PaginatedResponse<Livestream>>({
    queryKey: livestreamKeys.list(filters),
    queryFn: () => livestreamsApi.getAll({
      page: filters.page || 1,
      page_size: filters.page_size || 10,
      search: filters.search,
      is_live: filters.is_live === 'all' ? undefined : filters.is_live,
      sort_by: filters.sort_by,
      sort_order: filters.sort_order,
    }),
  });
};

// Fetch single livestream
export const useLivestream = (id: string) => {
  return useQuery<Livestream>({
    queryKey: livestreamKeys.detail(id),
    queryFn: () => livestreamsApi.getById(id),
    enabled: !!id,
  });
};

// Viewership history item type
export interface ViewershipHistoryItem {
  id: number | string;
  livestream_id: number;
  timestamp: string;
  viewcount: number;
}

// Viewership history response type
export interface ViewershipHistoryResponse {
  items: ViewershipHistoryItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  livestream_id: string;
  start_time?: string;
  end_time?: string;
  downsample?: '1m' | '5m' | '10m' | '1hr';
}

// Fetch viewership history
export const useViewershipHistory = (
  id: string, 
  page: number = 1, 
  pageSize: number = 100,
  options?: {
    startTime?: string;
    endTime?: string;
    downsample?: '1m' | '5m' | '10m' | '1hr';
  }
) => {
  return useQuery<ViewershipHistoryResponse>({
    queryKey: [...livestreamKeys.history(id), page, pageSize, options?.startTime, options?.endTime, options?.downsample],
    queryFn: () => livestreamsApi.getHistory(id, { 
      page, 
      page_size: pageSize,
      start_time: options?.startTime,
      end_time: options?.endTime,
      downsample: options?.downsample,
    }),
    enabled: !!id,
  });
};

// Fetch downsampled viewership history (for overview chart)
export const useDownsampledViewershipHistory = (
  id: string,
  downsample: '1m' | '5m' | '10m' | '1hr' = '1hr',
  limit: number = 3000
) => {
  return useQuery<ViewershipHistoryResponse>({
    queryKey: [...livestreamKeys.history(id), 'downsampled', downsample, limit],
    queryFn: () => livestreamsApi.getHistory(id, { 
      page: 1, 
      page_size: limit,
      downsample,
    }),
    enabled: !!id,
    staleTime: 60000, // 1 minute - downsampled data changes less frequently
  });
};

// Fetch dashboard stats
export const useDashboardStats = () => {
  return useQuery({
    queryKey: livestreamKeys.stats(),
    queryFn: () => livestreamsApi.getStats(),
    staleTime: 30000, // 30 seconds
  });
};

// Create livestream mutation
export const useCreateLivestream = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (urlOrId: string) => {
      return livestreamsApi.create({ youtube_url: urlOrId });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: livestreamKeys.lists() });
      queryClient.invalidateQueries({ queryKey: livestreamKeys.stats() });
      toast.success('Livestream added successfully');
    },
    onError: (error: Error & { response?: { data?: { detail?: string } } }) => {
      const message = error.response?.data?.detail || 'Failed to add livestream';
      toast.error(message);
    },
  });
};

// Update livestream mutation
export const useUpdateLivestream = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: LivestreamUpdate }) => {
      return livestreamsApi.update(id, data);
    },
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: livestreamKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: livestreamKeys.lists() });
      toast.success('Livestream updated successfully');
    },
    onError: (error: Error & { response?: { data?: { detail?: string } } }) => {
      const message = error.response?.data?.detail || 'Failed to update livestream';
      toast.error(message);
    },
  });
};

// Delete livestream mutation
export const useDeleteLivestream = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => livestreamsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: livestreamKeys.lists() });
      queryClient.invalidateQueries({ queryKey: livestreamKeys.stats() });
      toast.success('Livestream deleted successfully');
    },
    onError: (error: Error & { response?: { data?: { detail?: string } } }) => {
      const message = error.response?.data?.detail || 'Failed to delete livestream';
      toast.error(message);
    },
  });
};
