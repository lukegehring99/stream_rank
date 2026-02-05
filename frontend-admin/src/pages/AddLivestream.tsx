import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { useCreateLivestream } from '../hooks';
import { AddLivestreamForm } from '../types';

export const AddLivestream: React.FC = () => {
  const navigate = useNavigate();
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  const createMutation = useCreateLivestream();

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<AddLivestreamForm>();

  const urlOrId = watch('url_or_id');

  // Extract video ID for preview
  React.useEffect(() => {
    if (!urlOrId) {
      setPreviewUrl(null);
      return;
    }

    let videoId = urlOrId;
    
    // Check if it's a URL
    const patterns = [
      /(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/|youtube\.com\/v\/)([a-zA-Z0-9_-]{11})/,
      /youtube\.com\/live\/([a-zA-Z0-9_-]{11})/,
    ];

    for (const pattern of patterns) {
      const match = urlOrId.match(pattern);
      if (match) {
        videoId = match[1];
        break;
      }
    }

    // Valid video ID is 11 characters
    if (/^[a-zA-Z0-9_-]{11}$/.test(videoId)) {
      setPreviewUrl(`https://img.youtube.com/vi/${videoId}/mqdefault.jpg`);
    } else {
      setPreviewUrl(null);
    }
  }, [urlOrId]);

  const onSubmit = async (data: AddLivestreamForm) => {
    await createMutation.mutateAsync(data.url_or_id);
    navigate('/livestreams');
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6 animate-fadeIn">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-2 text-sm text-gray-500">
        <Link to="/livestreams" className="hover:text-primary-600">
          Livestreams
        </Link>
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
        <span className="text-gray-900 font-medium">Add New</span>
      </nav>

      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Add Livestream</h1>
        <p className="text-gray-500 mt-1">
          Add a new YouTube livestream to track viewership
        </p>
      </div>

      {/* Form */}
      <div className="card">
        <div className="card-body">
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
            <div>
              <label htmlFor="url_or_id" className="form-label">
                YouTube URL or Video ID
              </label>
              <input
                id="url_or_id"
                type="text"
                {...register('url_or_id', {
                  required: 'Please enter a YouTube URL or video ID',
                  validate: (value) => {
                    // Basic validation - just check it's not empty
                    if (!value.trim()) return 'Please enter a YouTube URL or video ID';
                    return true;
                  },
                })}
                className={`form-input ${errors.url_or_id ? 'border-red-500' : ''}`}
                placeholder="https://www.youtube.com/watch?v=... or video ID"
              />
              {errors.url_or_id && (
                <p className="form-error">{errors.url_or_id.message}</p>
              )}
              <p className="text-sm text-gray-500 mt-2">
                You can paste a full YouTube URL or just the video ID (11 characters)
              </p>
            </div>

            {/* Preview */}
            {previewUrl && (
              <div className="p-4 bg-gray-50 rounded-lg">
                <p className="text-sm font-medium text-gray-700 mb-3">Preview</p>
                <div className="flex items-start gap-4">
                  <div className="w-40 h-24 rounded overflow-hidden bg-gray-200 flex-shrink-0">
                    <img
                      src={previewUrl}
                      alt="Video thumbnail"
                      className="w-full h-full object-cover"
                      onError={(e) => {
                        e.currentTarget.style.display = 'none';
                      }}
                    />
                  </div>
                  <div className="text-sm text-gray-500">
                    <p>
                      Thumbnail preview. The full video details will be fetched from YouTube
                      after adding.
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Supported formats */}
            <div className="p-4 bg-blue-50 rounded-lg border border-blue-100">
              <div className="flex gap-3">
                <svg className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <div className="text-sm text-blue-800">
                  <p className="font-medium mb-1">Supported formats:</p>
                  <ul className="list-disc list-inside space-y-1 text-blue-700">
                    <li>https://www.youtube.com/watch?v=VIDEO_ID</li>
                    <li>https://youtu.be/VIDEO_ID</li>
                    <li>https://www.youtube.com/live/VIDEO_ID</li>
                    <li>VIDEO_ID (11 character ID)</li>
                  </ul>
                </div>
              </div>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-3 pt-4">
              <button
                type="submit"
                disabled={createMutation.isPending}
                className="btn-primary"
              >
                {createMutation.isPending ? (
                  <>
                    <div className="spinner w-5 h-5" />
                    Adding...
                  </>
                ) : (
                  <>
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                    </svg>
                    Add Livestream
                  </>
                )}
              </button>
              <Link to="/livestreams" className="btn-secondary">
                Cancel
              </Link>
            </div>
          </form>
        </div>
      </div>

      {/* Tips */}
      <div className="card">
        <div className="card-header">
          <h3 className="text-lg font-semibold text-gray-900">Tips</h3>
        </div>
        <div className="card-body">
          <ul className="space-y-3 text-sm text-gray-600">
            <li className="flex items-start gap-3">
              <svg className="w-5 h-5 text-green-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              <span>
                The system will automatically fetch the video title, channel name, and thumbnail
                from YouTube.
              </span>
            </li>
            <li className="flex items-start gap-3">
              <svg className="w-5 h-5 text-green-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              <span>
                Viewership data will be collected automatically every few minutes for live
                streams.
              </span>
            </li>
            <li className="flex items-start gap-3">
              <svg className="w-5 h-5 text-green-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              <span>
                You can add both live streams and scheduled (upcoming) streams.
              </span>
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
};
