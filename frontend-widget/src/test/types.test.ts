import { describe, it, expect } from 'vitest';
import {
  getTrendStatus,
  formatViewerCount,
  formatTimeAgo,
  extractVideoId,
} from '../types';

describe('getTrendStatus', () => {
  it('returns "hot" for score >= 80', () => {
    expect(getTrendStatus(80)).toBe('hot');
    expect(getTrendStatus(100)).toBe('hot');
    expect(getTrendStatus(95)).toBe('hot');
  });

  it('returns "rising" for score >= 50 and < 80', () => {
    expect(getTrendStatus(50)).toBe('rising');
    expect(getTrendStatus(79)).toBe('rising');
    expect(getTrendStatus(65)).toBe('rising');
  });

  it('returns "stable" for score >= 20 and < 50', () => {
    expect(getTrendStatus(20)).toBe('stable');
    expect(getTrendStatus(49)).toBe('stable');
    expect(getTrendStatus(35)).toBe('stable');
  });

  it('returns "cooling" for score < 20', () => {
    expect(getTrendStatus(0)).toBe('cooling');
    expect(getTrendStatus(19)).toBe('cooling');
    expect(getTrendStatus(10)).toBe('cooling');
  });
});

describe('formatViewerCount', () => {
  it('formats millions correctly', () => {
    expect(formatViewerCount(1000000)).toBe('1.0M');
    expect(formatViewerCount(2500000)).toBe('2.5M');
    expect(formatViewerCount(10000000)).toBe('10.0M');
  });

  it('formats thousands correctly', () => {
    expect(formatViewerCount(1000)).toBe('1.0K');
    expect(formatViewerCount(5500)).toBe('5.5K');
    expect(formatViewerCount(999999)).toBe('1000.0K');
  });

  it('formats small numbers with locale string', () => {
    expect(formatViewerCount(999)).toBe('999');
    expect(formatViewerCount(100)).toBe('100');
    expect(formatViewerCount(0)).toBe('0');
  });
});

describe('formatTimeAgo', () => {
  it('returns "Just now" for very recent times', () => {
    const now = new Date().toISOString();
    expect(formatTimeAgo(now)).toBe('Just now');
  });

  it('returns minutes for times less than an hour ago', () => {
    const fiveMinutesAgo = new Date(Date.now() - 5 * 60 * 1000).toISOString();
    expect(formatTimeAgo(fiveMinutesAgo)).toBe('5m ago');
  });

  it('returns hours for times less than a day ago', () => {
    const twoHoursAgo = new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString();
    expect(formatTimeAgo(twoHoursAgo)).toBe('2h ago');
  });

  it('returns days for times more than a day ago', () => {
    const twoDaysAgo = new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString();
    expect(formatTimeAgo(twoDaysAgo)).toBe('2d ago');
  });
});

describe('extractVideoId', () => {
  it('extracts video ID from standard YouTube URL', () => {
    expect(extractVideoId('https://youtube.com/watch?v=dQw4w9WgXcQ')).toBe('dQw4w9WgXcQ');
    expect(extractVideoId('https://www.youtube.com/watch?v=dQw4w9WgXcQ')).toBe('dQw4w9WgXcQ');
  });

  it('extracts video ID from short YouTube URL', () => {
    expect(extractVideoId('https://youtu.be/dQw4w9WgXcQ')).toBe('dQw4w9WgXcQ');
  });

  it('extracts video ID from live URL', () => {
    expect(extractVideoId('https://youtube.com/live/dQw4w9WgXcQ')).toBe('dQw4w9WgXcQ');
  });

  it('returns the ID if already a valid video ID', () => {
    expect(extractVideoId('dQw4w9WgXcQ')).toBe('dQw4w9WgXcQ');
  });

  it('returns null for invalid URLs', () => {
    expect(extractVideoId('not-a-valid-url')).toBe(null);
    expect(extractVideoId('https://example.com/video')).toBe(null);
  });
});
