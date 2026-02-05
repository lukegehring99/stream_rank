import { describe, it, expect, beforeEach } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useConfig } from '../hooks/useConfig';

describe('useConfig', () => {
  beforeEach(() => {
    // Reset URL before each test
    Object.defineProperty(window, 'location', {
      value: {
        search: '',
      },
      writable: true,
    });
  });

  it('returns default config when no query params', () => {
    const { result } = renderHook(() => useConfig());

    expect(result.current).toEqual({
      count: 10,
      refreshMinutes: 5,
      apiBaseUrl: 'http://localhost:8000/api/v1',
      theme: 'light',
    });
  });

  it('parses count from query params', () => {
    Object.defineProperty(window, 'location', {
      value: { search: '?count=20' },
      writable: true,
    });

    const { result } = renderHook(() => useConfig());
    expect(result.current.count).toBe(20);
  });

  it('clamps count to max 100', () => {
    Object.defineProperty(window, 'location', {
      value: { search: '?count=150' },
      writable: true,
    });

    const { result } = renderHook(() => useConfig());
    // Should fall back to default since 150 > 100
    expect(result.current.count).toBe(10);
  });

  it('parses theme from query params', () => {
    Object.defineProperty(window, 'location', {
      value: { search: '?theme=dark' },
      writable: true,
    });

    const { result } = renderHook(() => useConfig());
    expect(result.current.theme).toBe('dark');
  });

  it('parses refreshMinutes from query params', () => {
    Object.defineProperty(window, 'location', {
      value: { search: '?refreshMinutes=10' },
      writable: true,
    });

    const { result } = renderHook(() => useConfig());
    expect(result.current.refreshMinutes).toBe(10);
  });

  it('parses apiBaseUrl from query params', () => {
    Object.defineProperty(window, 'location', {
      value: { search: '?apiBaseUrl=https://api.example.com' },
      writable: true,
    });

    const { result } = renderHook(() => useConfig());
    expect(result.current.apiBaseUrl).toBe('https://api.example.com');
  });

  it('ignores invalid apiBaseUrl', () => {
    Object.defineProperty(window, 'location', {
      value: { search: '?apiBaseUrl=not-a-valid-url' },
      writable: true,
    });

    const { result } = renderHook(() => useConfig());
    expect(result.current.apiBaseUrl).toBe('http://localhost:8000/api/v1');
  });

  it('parses multiple query params', () => {
    Object.defineProperty(window, 'location', {
      value: { search: '?count=25&theme=dark&refreshMinutes=15' },
      writable: true,
    });

    const { result } = renderHook(() => useConfig());
    expect(result.current).toEqual({
      count: 25,
      refreshMinutes: 15,
      apiBaseUrl: 'http://localhost:8000/api/v1',
      theme: 'dark',
    });
  });
});
