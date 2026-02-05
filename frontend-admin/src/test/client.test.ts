import { describe, it, expect, beforeEach } from 'vitest';
import { extractVideoId } from '../api/client';

describe('extractVideoId', () => {
  it('should return the video ID if given a plain 11-character ID', () => {
    expect(extractVideoId('dQw4w9WgXcQ')).toBe('dQw4w9WgXcQ');
  });

  it('should extract video ID from standard YouTube watch URL', () => {
    expect(extractVideoId('https://www.youtube.com/watch?v=dQw4w9WgXcQ')).toBe('dQw4w9WgXcQ');
    expect(extractVideoId('https://youtube.com/watch?v=dQw4w9WgXcQ')).toBe('dQw4w9WgXcQ');
  });

  it('should extract video ID from short youtu.be URL', () => {
    expect(extractVideoId('https://youtu.be/dQw4w9WgXcQ')).toBe('dQw4w9WgXcQ');
  });

  it('should extract video ID from embed URL', () => {
    expect(extractVideoId('https://www.youtube.com/embed/dQw4w9WgXcQ')).toBe('dQw4w9WgXcQ');
  });

  it('should extract video ID from live URL', () => {
    expect(extractVideoId('https://www.youtube.com/live/dQw4w9WgXcQ')).toBe('dQw4w9WgXcQ');
  });

  it('should handle URLs with extra parameters', () => {
    expect(extractVideoId('https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=120')).toBe('dQw4w9WgXcQ');
  });

  it('should return input as-is if no pattern matches', () => {
    expect(extractVideoId('invalid-url')).toBe('invalid-url');
  });
});

describe('localStorage token management', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('should store and retrieve access token', () => {
    const token = 'test-token-123';
    localStorage.setItem('access_token', token);
    expect(localStorage.getItem('access_token')).toBe(token);
  });

  it('should remove access token on logout', () => {
    localStorage.setItem('access_token', 'test-token');
    localStorage.removeItem('access_token');
    expect(localStorage.getItem('access_token')).toBeNull();
  });
});
