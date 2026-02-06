import React from 'react';

interface YouTubePlayerProps {
  videoId: string;
  title: string;
  onClose: () => void;
}

export const YouTubePlayer: React.FC<YouTubePlayerProps> = ({
  videoId,
  title,
  onClose,
}) => {
  return (
    <div className="card overflow-hidden animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-neutral-100 dark:border-neutral-800">
        <h3 className="font-semibold text-sm text-neutral-900 dark:text-neutral-100 truncate pr-4">
          {title}
        </h3>
        <button
          onClick={onClose}
          className="p-1.5 rounded-lg text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors"
          aria-label="Close player"
        >
          <svg
            className="w-5 h-5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </button>
      </div>

      {/* Player */}
      <div className="relative w-full" style={{ paddingTop: '56.25%' }}>
        <iframe
          className="absolute inset-0 w-full h-full"
          src={`https://www.youtube.com/embed/${videoId}?autoplay=1&rel=0`}
          title={title}
          frameBorder="0"
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
          allowFullScreen
        />
      </div>

      {/* Actions */}
      <div className="px-4 py-2.5 bg-gradient-to-r from-neutral-50 to-purple-50/50 dark:from-neutral-900 dark:to-purple-950/30 border-t border-neutral-100 dark:border-neutral-800">
        <div className="flex items-center gap-2">
          <a
            href={`https://youtube.com/watch?v=${videoId}`}
            target="_blank"
            rel="noopener noreferrer"
            className="btn btn-primary text-xs py-1.5 px-3"
          >
            <svg
              className="w-4 h-4 mr-1.5"
              fill="currentColor"
              viewBox="0 0 24 24"
            >
              <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z" />
            </svg>
            Watch on YouTube
          </a>
          <button
            onClick={() => {
              navigator.clipboard.writeText(
                `https://youtube.com/watch?v=${videoId}`
              );
            }}
            className="btn btn-ghost text-xs py-1.5 px-3"
          >
            <svg
              className="w-4 h-4 mr-1.5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
              />
            </svg>
            Copy Link
          </button>
        </div>
      </div>
    </div>
  );
};
