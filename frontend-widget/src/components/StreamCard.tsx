import React, { useState } from 'react';
import clsx from 'clsx';
import {
  Livestream,
  getTrendStatus,
  formatViewerCount,
  formatTimeAgo,
  TrendStatus,
} from '../types';

interface StreamCardProps {
  stream: Livestream;
  isSelected: boolean;
  onSelect: (stream: Livestream) => void;
}

const TrendBadge: React.FC<{ status: TrendStatus; score: number }> = ({
  status,
  score,
}) => {
  const config = {
    hot: {
      icon: '🔥',
      label: 'Hot',
      class: 'badge-hot',
    },
    rising: {
      icon: '📈',
      label: 'Rising',
      class: 'badge-rising',
    },
    stable: {
      icon: '➡️',
      label: 'Stable',
      class: 'badge-stable',
    },
    cooling: {
      icon: '📉',
      label: 'Cooling',
      class: 'badge-cooling',
    },
  };

  const { icon, label, class: badgeClass } = config[status];

  return (
    <span className={clsx('badge', badgeClass)}>
      <span className="mr-1">{icon}</span>
      {label} • {score}
    </span>
  );
};

const ViewersBadge: React.FC<{ count: number }> = ({ count }) => (
  <span className="badge bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300">
    <svg
      className="w-3 h-3 mr-1"
      fill="currentColor"
      viewBox="0 0 20 20"
    >
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

export const StreamCard: React.FC<StreamCardProps> = ({
  stream,
  isSelected,
  onSelect,
}) => {
  const [showDetails, setShowDetails] = useState(false);
  const trendStatus = getTrendStatus(stream.trend_score);

  return (
    <div
      className={clsx(
        'card card-hover cursor-pointer transition-all duration-200',
        isSelected && 'ring-2 ring-primary-500 dark:ring-primary-400 shadow-glow-sm'
      )}
      onClick={() => onSelect(stream)}
    >
      <div className="p-4">
        <div className="flex gap-4">
          {/* Rank Badge */}
          <div
            className={clsx(
              'flex-shrink-0 w-12 h-12 rounded-xl flex items-center justify-center font-bold text-lg',
              stream.rank <= 3
                ? 'bg-gradient-to-br from-primary-500 to-accent-500 text-white shadow-glow-sm'
                : 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300'
            )}
          >
            #{stream.rank}
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-slate-900 dark:text-slate-100 truncate mb-1">
              {stream.title}
            </h3>
            <p className="text-sm text-slate-500 dark:text-slate-400 truncate mb-2">
              {stream.channel_name}
            </p>
            <div className="flex flex-wrap items-center gap-2">
              <TrendBadge status={trendStatus} score={stream.trend_score} />
              <ViewersBadge count={stream.current_viewers} />
              <span className="text-xs text-slate-400 dark:text-slate-500">
                Started {formatTimeAgo(stream.started_at)}
              </span>
            </div>
          </div>

          {/* Thumbnail */}
          <div className="hidden sm:block flex-shrink-0 w-24 h-16 rounded-lg overflow-hidden bg-slate-200 dark:bg-slate-700">
            <img
              src={stream.thumbnail_url}
              alt=""
              className="w-full h-full object-cover"
              loading="lazy"
            />
          </div>
        </div>

        {/* Expandable Details */}
        <div className="mt-3">
          <button
            onClick={(e) => {
              e.stopPropagation();
              setShowDetails(!showDetails);
            }}
            className="text-xs text-primary-500 dark:text-primary-400 hover:text-primary-600 dark:hover:text-primary-300 font-medium flex items-center gap-1"
          >
            <svg
              className={clsx(
                'w-4 h-4 transition-transform duration-200',
                showDetails && 'rotate-180'
              )}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 9l-7 7-7-7"
              />
            </svg>
            {showDetails ? 'Hide details' : 'Show details'}
          </button>

          {showDetails && (
            <div className="mt-3 pt-3 border-t border-slate-100 dark:border-slate-700 animate-fade-in">
              {stream.description && (
                <p className="text-sm text-slate-600 dark:text-slate-400 mb-2 line-clamp-2">
                  {stream.description}
                </p>
              )}
              <div className="flex flex-wrap gap-2 text-xs">
                <a
                  href={stream.stream_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={(e) => e.stopPropagation()}
                  className="inline-flex items-center text-primary-500 hover:text-primary-600 dark:text-primary-400"
                >
                  <svg
                    className="w-3.5 h-3.5 mr-1"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                    />
                  </svg>
                  Watch on YouTube
                </a>
                {stream.category && (
                  <span className="text-slate-500 dark:text-slate-400">
                    • {stream.category}
                  </span>
                )}
              </div>
              {stream.tags && stream.tags.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-2">
                  {stream.tags.slice(0, 5).map((tag) => (
                    <span
                      key={tag}
                      className="px-2 py-0.5 bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400 rounded text-xs"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
