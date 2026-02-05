import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { StreamCard } from '../components/StreamCard';
import { Livestream } from '../types';

const mockStream: Livestream = {
  id: 'test-stream-1',
  youtube_video_id: 'dQw4w9WgXcQ',
  name: 'Test Stream Title',
  channel: 'Test Channel',
  url: 'https://youtube.com/watch?v=dQw4w9WgXcQ',
  is_live: true,
  current_viewers: 15000,
  trend_score: 85,
  rank: 1,
};

describe('StreamCard', () => {
  it('renders stream information correctly', () => {
    const onSelect = vi.fn();
    render(
      <StreamCard
        stream={mockStream}
        isSelected={false}
        onSelect={onSelect}
      />
    );

    expect(screen.getByText('Test Stream Title')).toBeInTheDocument();
    expect(screen.getByText('Test Channel')).toBeInTheDocument();
    expect(screen.getByText('#1')).toBeInTheDocument();
  });

  it('displays trend badge with correct status', () => {
    const onSelect = vi.fn();
    render(
      <StreamCard
        stream={mockStream}
        isSelected={false}
        onSelect={onSelect}
      />
    );

    // Score 85 should be "Hot"
    expect(screen.getByText(/Hot/)).toBeInTheDocument();
    expect(screen.getByText(/85/)).toBeInTheDocument();
  });

  it('displays formatted viewer count', () => {
    const onSelect = vi.fn();
    render(
      <StreamCard
        stream={mockStream}
        isSelected={false}
        onSelect={onSelect}
      />
    );

    expect(screen.getByText('15.0K')).toBeInTheDocument();
  });

  it('calls onSelect when clicked', () => {
    const onSelect = vi.fn();
    render(
      <StreamCard
        stream={mockStream}
        isSelected={false}
        onSelect={onSelect}
      />
    );

    const card = screen.getByText('Test Stream Title').closest('div[class*="card"]');
    fireEvent.click(card!);

    expect(onSelect).toHaveBeenCalledWith(mockStream);
  });

  it('shows details when toggle is clicked', () => {
    const onSelect = vi.fn();
    render(
      <StreamCard
        stream={mockStream}
        isSelected={false}
        onSelect={onSelect}
      />
    );

    const toggleButton = screen.getByText('Show details');
    fireEvent.click(toggleButton);

    expect(screen.getByText('Watch on YouTube')).toBeInTheDocument();
  });

  it('applies selected styles when isSelected is true', () => {
    const onSelect = vi.fn();
    render(
      <StreamCard
        stream={mockStream}
        isSelected={true}
        onSelect={onSelect}
      />
    );

    const card = screen.getByText('Test Stream Title').closest('div[class*="card"]');
    expect(card).toHaveClass('ring-2');
  });

  it('renders different trend badges based on score', () => {
    const onSelect = vi.fn();

    // Test rising status (score 60)
    const risingStream = { ...mockStream, trend_score: 60 };
    const { rerender } = render(
      <StreamCard
        stream={risingStream}
        isSelected={false}
        onSelect={onSelect}
      />
    );
    expect(screen.getByText(/Rising/)).toBeInTheDocument();

    // Test stable status (score 30)
    const stableStream = { ...mockStream, trend_score: 30 };
    rerender(
      <StreamCard
        stream={stableStream}
        isSelected={false}
        onSelect={onSelect}
      />
    );
    expect(screen.getByText(/Stable/)).toBeInTheDocument();

    // Test cooling status (score 10)
    const coolingStream = { ...mockStream, trend_score: 10 };
    rerender(
      <StreamCard
        stream={coolingStream}
        isSelected={false}
        onSelect={onSelect}
      />
    );
    expect(screen.getByText(/Cooling/)).toBeInTheDocument();
  });
});
