import { describe, it, expect } from 'vitest';
import { livestreamKeys } from '../hooks/useLivestreams';

describe('livestreamKeys', () => {
  it('should generate correct query keys', () => {
    expect(livestreamKeys.all).toEqual(['livestreams']);
    expect(livestreamKeys.lists()).toEqual(['livestreams', 'list']);
    expect(livestreamKeys.list({ page: 1, is_live: true })).toEqual([
      'livestreams',
      'list',
      { page: 1, is_live: true },
    ]);
    expect(livestreamKeys.details()).toEqual(['livestreams', 'detail']);
    expect(livestreamKeys.detail('abc-123')).toEqual(['livestreams', 'detail', 'abc-123']);
    expect(livestreamKeys.history('abc-123')).toEqual(['livestreams', 'detail', 'abc-123', 'history']);
    expect(livestreamKeys.stats()).toEqual(['livestreams', 'stats']);
  });
});

describe('Query key structure', () => {
  it('should maintain hierarchical structure for cache invalidation', () => {
    // All list queries should be invalidated when invalidating lists()
    const listKey1 = livestreamKeys.list({ page: 1 });
    const listKey2 = livestreamKeys.list({ page: 2, is_live: true });
    const listsPrefix = livestreamKeys.lists();

    expect(listKey1.slice(0, listsPrefix.length)).toEqual(listsPrefix);
    expect(listKey2.slice(0, listsPrefix.length)).toEqual(listsPrefix);
  });

  it('should maintain detail query hierarchy', () => {
    const detailKey = livestreamKeys.detail('abc-123');
    const historyKey = livestreamKeys.history('abc-123');

    expect(historyKey.slice(0, detailKey.length)).toEqual(detailKey);
  });
});
