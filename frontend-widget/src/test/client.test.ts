import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  fetchTrendingStreams,
  fetchViewershipHistory,
  generateMockStreams,
  generateMockViewership,
  ApiError,
} from '../api/client';

// Mock fetch globally
const mockFetch = vi.fn();
(globalThis as unknown as { fetch: typeof fetch }).fetch = mockFetch;

describe('API Client', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('fetchTrendingStreams', () => {
    it('fetches streams successfully', async () => {
      const mockResponse = {
        streams: [
          { id: '1', title: 'Test Stream', video_id: 'abc123' },
        ],
        total: 1,
        page: 1,
        page_size: 10,
        fetched_at: new Date().toISOString(),
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const result = await fetchTrendingStreams('http://localhost:8000/api/v1', 10);
      expect(result).toEqual(mockResponse.streams);
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/streams/trending?limit=10',
        expect.any(Object)
      );
    });

    it('throws ApiError on HTTP error', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
      });

      await expect(
        fetchTrendingStreams('http://localhost:8000/api/v1', 10)
      ).rejects.toThrow(ApiError);
    });

    it('throws ApiError on network error', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      await expect(
        fetchTrendingStreams('http://localhost:8000/api/v1', 10)
      ).rejects.toThrow(ApiError);
    });
  });

  describe('fetchViewershipHistory', () => {
    it('fetches viewership data successfully', async () => {
      const mockResponse = {
        video_id: 'abc123',
        history: [
          { timestamp: '2024-01-01T00:00:00Z', viewers: 1000 },
        ],
        period_hours: 24,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const result = await fetchViewershipHistory(
        'http://localhost:8000/api/v1',
        'abc123',
        24
      );
      expect(result).toEqual(mockResponse.history);
    });

    it('uses correct URL with hours parameter', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ history: [] }),
      });

      await fetchViewershipHistory('http://localhost:8000/api/v1', 'abc123', 12);
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/streams/abc123/viewership?hours=12',
        expect.any(Object)
      );
    });
  });

  describe('generateMockStreams', () => {
    it('generates correct number of streams', () => {
      const streams = generateMockStreams(5);
      expect(streams).toHaveLength(5);
    });

    it('generates streams with required properties', () => {
      const streams = generateMockStreams(1);
      const stream = streams[0];

      expect(stream).toHaveProperty('id');
      expect(stream).toHaveProperty('video_id');
      expect(stream).toHaveProperty('title');
      expect(stream).toHaveProperty('channel_name');
      expect(stream).toHaveProperty('current_viewers');
      expect(stream).toHaveProperty('trend_score');
      expect(stream).toHaveProperty('rank');
      expect(stream.rank).toBe(1);
    });

    it('generates streams with sequential ranks', () => {
      const streams = generateMockStreams(10);
      streams.forEach((stream, index) => {
        expect(stream.rank).toBe(index + 1);
      });
    });
  });

  describe('generateMockViewership', () => {
    it('generates viewership data points', () => {
      const data = generateMockViewership(24);
      expect(data.length).toBeGreaterThan(0);
    });

    it('generates data points with required properties', () => {
      const data = generateMockViewership(24);
      const point = data[0];

      expect(point).toHaveProperty('timestamp');
      expect(point).toHaveProperty('viewers');
      expect(typeof point.viewers).toBe('number');
    });

    it('generates timestamps in chronological order', () => {
      const data = generateMockViewership(24);
      for (let i = 1; i < data.length; i++) {
        const prevTime = new Date(data[i - 1].timestamp).getTime();
        const currTime = new Date(data[i].timestamp).getTime();
        expect(currTime).toBeGreaterThan(prevTime);
      }
    });
  });
});

describe('ApiError', () => {
  it('creates error with status and message', () => {
    const error = new ApiError(404, 'Not found');
    expect(error.status).toBe(404);
    expect(error.message).toBe('Not found');
    expect(error.name).toBe('ApiError');
  });

  it('is instance of Error', () => {
    const error = new ApiError(500, 'Server error');
    expect(error).toBeInstanceOf(Error);
  });
});
