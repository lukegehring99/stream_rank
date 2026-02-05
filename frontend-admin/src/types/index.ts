// Livestream types
export interface Livestream {
  id: string;
  youtube_video_id: string;
  name: string;
  channel: string;
  description: string | null;
  url: string;
  is_live: boolean;
  created_at: string;
  updated_at: string;
  // Optional fields that may not always be present
  thumbnail_url?: string | null;
  current_viewers?: number;
  peak_viewers?: number;
}

export interface LivestreamCreate {
  youtube_video_id?: string;
  youtube_url?: string;
  name: string;
  channel: string;
  description?: string;
  is_live?: boolean;
}

export interface LivestreamUpdate {
  name?: string;
  channel?: string;
  description?: string;
  is_live?: boolean;
}

// Viewership types
export interface ViewershipRecord {
  id: number;
  livestream_id: string;
  viewer_count: number;
  recorded_at: string;
  is_anomaly: boolean;
}

export interface ViewershipHistory {
  livestream_id: string;
  records: ViewershipRecord[];
  total_records: number;
}

// Auth types
export interface LoginCredentials {
  username: string;
  password: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
}

export interface User {
  username: string;
  role: string;
}

// API response types
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ApiError {
  detail: string;
  status_code?: number;
}

// Dashboard types
export interface DashboardStats {
  total_streams: number;
  live_streams: number;
  total_viewers: number;
  peak_viewers_today: number;
}

// Filter types
export interface LivestreamFilters {
  search?: string;
  is_live?: boolean | 'all';
  page?: number;
  page_size?: number;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

// Form types
export interface AddLivestreamForm {
  url_or_id: string;
}

export interface EditLivestreamForm {
  name: string;
  channel: string;
  is_live: boolean;
}
