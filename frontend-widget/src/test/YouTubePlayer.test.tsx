import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { YouTubePlayer } from '../components/YouTubePlayer';

describe('YouTubePlayer', () => {
  const defaultProps = {
    videoId: 'dQw4w9WgXcQ',
    title: 'Test Video Title',
    onClose: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the player with correct title', () => {
    render(<YouTubePlayer {...defaultProps} />);
    expect(screen.getByText('Test Video Title')).toBeInTheDocument();
  });

  it('renders YouTube iframe with correct src', () => {
    render(<YouTubePlayer {...defaultProps} />);
    const iframe = document.querySelector('iframe');
    expect(iframe).toBeInTheDocument();
    expect(iframe?.src).toContain('youtube.com/embed/dQw4w9WgXcQ');
    expect(iframe?.src).toContain('autoplay=1');
  });

  it('calls onClose when close button is clicked', () => {
    render(<YouTubePlayer {...defaultProps} />);
    const closeButton = screen.getByLabelText('Close player');
    fireEvent.click(closeButton);
    expect(defaultProps.onClose).toHaveBeenCalledTimes(1);
  });

  it('renders Open on YouTube link with correct href', () => {
    render(<YouTubePlayer {...defaultProps} />);
    const link = screen.getByText('Open on YouTube');
    expect(link).toHaveAttribute('href', 'https://youtube.com/watch?v=dQw4w9WgXcQ');
    expect(link).toHaveAttribute('target', '_blank');
    expect(link).toHaveAttribute('rel', 'noopener noreferrer');
  });

  it('renders Copy Link button', () => {
    render(<YouTubePlayer {...defaultProps} />);
    expect(screen.getByText('Copy Link')).toBeInTheDocument();
  });

  it('copies link to clipboard when Copy Link is clicked', async () => {
    const mockClipboard = {
      writeText: vi.fn().mockResolvedValue(undefined),
    };
    Object.assign(navigator, { clipboard: mockClipboard });

    render(<YouTubePlayer {...defaultProps} />);
    const copyButton = screen.getByText('Copy Link');
    fireEvent.click(copyButton);

    expect(mockClipboard.writeText).toHaveBeenCalledWith(
      'https://youtube.com/watch?v=dQw4w9WgXcQ'
    );
  });
});
