import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import {
  LoadingSpinner,
  Skeleton,
  StreamCardSkeleton,
  StreamListSkeleton,
} from '../components/LoadingSpinner';

describe('LoadingSpinner', () => {
  it('renders with default props', () => {
    render(<LoadingSpinner />);
    expect(screen.getByRole('status')).toBeInTheDocument();
    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });

  it('renders with custom label', () => {
    render(<LoadingSpinner label="Fetching data..." />);
    expect(screen.getByText('Fetching data...')).toBeInTheDocument();
  });

  it('renders without label when empty string', () => {
    render(<LoadingSpinner label="" />);
    expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
  });

  it('applies correct size classes', () => {
    const { container, rerender } = render(<LoadingSpinner size="sm" />);
    expect(container.querySelector('.w-4')).toBeInTheDocument();

    rerender(<LoadingSpinner size="lg" />);
    expect(container.querySelector('.w-12')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    const { container } = render(<LoadingSpinner className="custom-class" />);
    expect(container.querySelector('.custom-class')).toBeInTheDocument();
  });
});

describe('Skeleton', () => {
  it('renders with animate-pulse class', () => {
    const { container } = render(<Skeleton />);
    expect(container.querySelector('.animate-pulse')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    const { container } = render(<Skeleton className="w-32 h-8" />);
    expect(container.querySelector('.w-32')).toBeInTheDocument();
    expect(container.querySelector('.h-8')).toBeInTheDocument();
  });
});

describe('StreamCardSkeleton', () => {
  it('renders skeleton structure', () => {
    const { container } = render(<StreamCardSkeleton />);
    const skeletons = container.querySelectorAll('.animate-pulse');
    expect(skeletons.length).toBeGreaterThan(0);
  });
});

describe('StreamListSkeleton', () => {
  it('renders default number of skeleton cards', () => {
    const { container } = render(<StreamListSkeleton />);
    const cards = container.querySelectorAll('.card');
    expect(cards.length).toBe(5);
  });

  it('renders custom number of skeleton cards', () => {
    const { container } = render(<StreamListSkeleton count={3} />);
    const cards = container.querySelectorAll('.card');
    expect(cards.length).toBe(3);
  });
});
