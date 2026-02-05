import {
  StreamsResponse,
  ViewershipResponse,
  Livestream,
  ViewershipDataPoint,
} from '../types';

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

async function fetchWithTimeout(
  url: string,
  options: RequestInit = {},
  timeout = 10000
): Promise<Response> {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    });
    clearTimeout(id);
    return response;
  } catch (error) {
    clearTimeout(id);
    if (error instanceof Error && error.name === 'AbortError') {
      throw new ApiError(408, 'Request timeout');
    }
    throw error;
  }
}

export async function fetchTrendingStreams(
  baseUrl: string,
  count: number
): Promise<Livestream[]> {
  const url = `${baseUrl}/streams/trending?limit=${count}`;

  try {
    const response = await fetchWithTimeout(url);

    if (!response.ok) {
      throw new ApiError(response.status, `HTTP error ${response.status}`);
    }

    const data: StreamsResponse = await response.json();
    return data.streams;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new ApiError(500, 'Network error: Unable to fetch streams');
  }
}

export async function fetchViewershipHistory(
  baseUrl: string,
  videoId: string,
  hours = 24
): Promise<ViewershipDataPoint[]> {
  const url = `${baseUrl}/streams/${videoId}/viewership?hours=${hours}`;

  try {
    const response = await fetchWithTimeout(url);

    if (!response.ok) {
      throw new ApiError(response.status, `HTTP error ${response.status}`);
    }

    const data: ViewershipResponse = await response.json();
    return data.history;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new ApiError(500, 'Network error: Unable to fetch viewership data');
  }
}

// Create a mock data generator for development/demo
export function generateMockStreams(count: number): Livestream[] {
  const channels = [
    { name: 'Gaming Masters', id: 'UC123gaming' },
    { name: 'Tech Talk Live', id: 'UC456tech' },
    { name: 'Music Vibes', id: 'UC789music' },
    { name: 'News 24/7', id: 'UC101news' },
    { name: 'Sports Central', id: 'UC102sports' },
    { name: 'Cooking Show', id: 'UC103cook' },
    { name: 'Science Lab', id: 'UC104science' },
    { name: 'Art Studio', id: 'UC105art' },
  ];

  const titles = [
    '🔴 LIVE: Epic Gaming Marathon',
    '🎮 Speedrun Challenge - World Record Attempt',
    '🎵 Chill Lo-Fi Beats to Study To',
    '📰 Breaking News Coverage',
    '⚽ Live Match Commentary',
    '👨‍🍳 Cooking Italian Cuisine LIVE',
    '🔬 Science Experiments You Can Try',
    '🎨 Digital Art Creation Stream',
    '💻 Coding a Full App in 24 Hours',
    '🎤 Live Concert - Acoustic Session',
  ];

  return Array.from({ length: count }, (_, i) => {
    const channel = channels[i % channels.length];
    const startedHoursAgo = Math.floor(Math.random() * 12) + 1;
    const startedAt = new Date(
      Date.now() - startedHoursAgo * 60 * 60 * 1000
    ).toISOString();

    return {
      id: `stream-${i + 1}`,
      video_id: `dQw4w9WgXc${String(i).padStart(1, '0')}`,
      title: titles[i % titles.length],
      channel_name: channel.name,
      channel_id: channel.id,
      description: `This is an amazing livestream from ${channel.name}. Join us for exciting content!`,
      thumbnail_url: `https://picsum.photos/seed/${i + 1}/320/180`,
      stream_url: `https://youtube.com/watch?v=dQw4w9WgXc${i}`,
      current_viewers: Math.floor(Math.random() * 50000) + 1000,
      trend_score: Math.floor(Math.random() * 100),
      rank: i + 1,
      started_at: startedAt,
      last_updated: new Date().toISOString(),
      tags: ['live', 'trending'],
      category: 'Entertainment',
    };
  });
}

export function generateMockViewership(hours = 24): ViewershipDataPoint[] {
  const points: ViewershipDataPoint[] = [];
  const now = Date.now();
  const interval = (hours * 60 * 60 * 1000) / 48; // 48 data points

  let baseViewers = Math.floor(Math.random() * 10000) + 5000;

  for (let i = 48; i >= 0; i--) {
    const timestamp = new Date(now - i * interval).toISOString();
    // Add some randomness but keep general trend
    const variation = (Math.random() - 0.5) * baseViewers * 0.2;
    const trend = (48 - i) * 50; // Gradual increase
    baseViewers = Math.max(1000, baseViewers + variation * 0.1);

    points.push({
      timestamp,
      viewers: Math.floor(baseViewers + trend + variation),
    });
  }

  return points;
}
