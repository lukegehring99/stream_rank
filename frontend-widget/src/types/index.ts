// Stream data types matching the API response
export interface Livestream {
  id: string;
  youtube_video_id: string;
  name: string;
  channel: string;
  url: string;
  is_live: boolean;
  current_viewers: number;
  rank: number;
  trend_score: number | null;
}

export interface ViewershipDataPoint {
  timestamp: string;
  viewers: number;
}

export interface ViewershipHistory {
  video_id: string;
  data_points: ViewershipDataPoint[];
}

export interface StreamsResponse {
  items: Livestream[];
  count: number;
  cached_at: string | null;
}

export interface ViewershipResponse {
  video_id: string;
  history: ViewershipDataPoint[];
  period_hours: number;
}

// Widget configuration
export interface WidgetConfig {
  count: number;
  refreshMinutes: number;
  apiBaseUrl: string;
  theme: 'light' | 'dark';
}

export const DEFAULT_CONFIG: WidgetConfig = {
  count: 10,
  refreshMinutes: 5,
  apiBaseUrl: 'http://localhost:8000/api/v1',
  theme: 'light',
};

// Trend status helper (used for categorizing trend scores)
export type TrendStatus = 'hot' | 'rising' | 'stable' | 'cooling';

export function getTrendStatus(score: number): TrendStatus {
  if (score >= 80) return 'hot';
  if (score >= 50) return 'rising';
  if (score >= 20) return 'stable';
  return 'cooling';
}

export function formatViewerCount(count: number): string {
  if (count >= 1_000_000) {
    return `${(count / 1_000_000).toFixed(1)}M`;
  }
  if (count >= 1_000) {
    return `${(count / 1_000).toFixed(1)}K`;
  }
  return count.toLocaleString();
}

export function formatTimeAgo(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);

  if (seconds < 60) return 'Just now';
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

export function extractVideoId(url: string): string | null {
  const patterns = [
    /(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/live\/)([a-zA-Z0-9_-]{11})/,
    /^([a-zA-Z0-9_-]{11})$/,
  ];

  for (const pattern of patterns) {
    const match = url.match(pattern);
    if (match) return match[1];
  }
  return null;
}
