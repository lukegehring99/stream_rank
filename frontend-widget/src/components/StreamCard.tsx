import React from 'react';
import clsx from 'clsx';
import { Livestream, formatViewerCount } from '../types';

interface StreamCardProps {
  stream: Livestream;
  isSelected: boolean;
  onSelect: (stream: Livestream) => void;
}

const TrendScore: React.FC<{ score: number }> = ({ score }) => (
  <span className="trend-score">
    <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
    </svg>
    {score}
  </span>
);

const ViewerCount: React.FC<{ count: number }> = ({ count }) => (
  <span className="viewer-count">
    <svg className="w-4 h-4 text-primary-500" fill="currentColor" viewBox="0 0 20 20">
      <path d="M10 12a2 2 0 100-4 2 2 0 000 4z" />
      <path
        fillRule="evenodd"
        d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.064 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z"
        clipRule="evenodd"
      />
    </svg>
    {formatViewerCount(count)}
  </span>
);

const RankBadge: React.FC<{ rank: number }> = ({ rank }) => {
  const isTop3 = rank <= 3;
  return (
    <div className={clsx('rank-badge', isTop3 ? 'rank-badge-top' : 'rank-badge-normal')}>
      {rank}
    </div>
  );
};

const Thumbnail: React.FC<{ videoId: string; title: string }> = ({ videoId, title }) => (
  <div className="flex-shrink-0 w-24 h-14 rounded-xl overflow-hidden bg-gradient-to-br from-neutral-100 to-neutral-200 dark:from-neutral-800 dark:to-neutral-700 shadow-sm">
    <img
      src={`https://img.youtube.com/vi/${videoId}/mqdefault.jpg`}
      alt={title}
      className="w-full h-full object-cover"
      loading="lazy"
    />
  </div>
);

export const StreamCard: React.FC<StreamCardProps> = ({
  stream,
  isSelected,
  onSelect,
}) => {
  return (
    <div
      className={clsx(
        'card card-interactive p-3',
        isSelected && 'card-selected'
      )}
      onClick={() => onSelect(stream)}
    >
      <div className="flex items-center gap-3">
        {/* Rank */}
        <RankBadge rank={stream.rank} />

        {/* Content */}
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-sm text-neutral-900 dark:text-neutral-100 truncate">
            {stream.name}
          </h3>
          <p className="text-xs text-neutral-500 dark:text-neutral-400 truncate mt-0.5">
            {stream.channel}
          </p>
          <div className="flex items-center gap-2.5 mt-1.5">
            {stream.trend_score !== null && (
              <TrendScore score={stream.trend_score} />
            )}
            <ViewerCount count={stream.current_viewers} />
          </div>
        </div>

        {/* Thumbnail on the right */}
        <Thumbnail videoId={stream.youtube_video_id} title={stream.name} />
      </div>
    </div>
  );
};
