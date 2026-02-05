import React, { useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { format } from 'date-fns';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { DeleteModal, Pagination } from '../components';
import {
  useLivestream,
  useViewershipHistory,
  useUpdateLivestream,
  useDeleteLivestream,
} from '../hooks';
import { EditLivestreamForm } from '../types';

export const LivestreamDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const livestreamId = id!;

  // State
  const [isEditing, setIsEditing] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [historyPage, setHistoryPage] = useState(1);

  // Queries
  const { data: stream, isLoading, isError } = useLivestream(livestreamId);
  const { data: history, isLoading: historyLoading } = useViewershipHistory(
    livestreamId,
    historyPage,
    50
  );

  // Mutations
  const updateMutation = useUpdateLivestream();
  const deleteMutation = useDeleteLivestream();

  // Form
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<EditLivestreamForm>();

  // Handlers
  const handleEdit = () => {
    if (stream) {
      reset({
        name: stream.name,
        channel: stream.channel,
        is_live: stream.is_live,
      });
      setIsEditing(true);
    }
  };

  const handleCancelEdit = () => {
    setIsEditing(false);
    reset();
  };

  const onSubmit = async (data: EditLivestreamForm) => {
    await updateMutation.mutateAsync({
      id: livestreamId,
      data: {
        name: data.name,
        channel: data.channel,
        is_live: data.is_live,
      },
    });
    setIsEditing(false);
  };

  const handleDelete = async () => {
    await deleteMutation.mutateAsync(livestreamId);
    navigate('/livestreams');
  };

  const formatViewers = (count: number) => {
    if (count >= 1000000) {
      return (count / 1000000).toFixed(1) + 'M';
    }
    if (count >= 1000) {
      return (count / 1000).toFixed(1) + 'K';
    }
    return count.toLocaleString();
  };

  // Chart data
  const chartData = history?.records
    .slice()
    .reverse()
    .map((record) => ({
      time: format(new Date(record.recorded_at), 'HH:mm'),
      viewers: record.viewer_count,
      isAnomaly: record.is_anomaly,
    }));

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="spinner w-10 h-10" />
      </div>
    );
  }

  if (isError || !stream) {
    return (
      <div className="card">
        <div className="card-body text-center py-12">
          <div className="text-red-500 mb-4">
            <svg className="w-12 h-12 mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <h3 className="text-lg font-medium text-gray-900">Livestream not found</h3>
          <p className="text-gray-500 mt-2">
            The livestream you're looking for doesn't exist or has been deleted.
          </p>
          <Link to="/livestreams" className="btn-primary mt-4">
            Back to Livestreams
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-2 text-sm text-gray-500">
        <Link to="/livestreams" className="hover:text-primary-600">
          Livestreams
        </Link>
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
        <span className="text-gray-900 font-medium truncate max-w-xs">{stream.name}</span>
      </nav>

      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-start gap-6">
        {/* Thumbnail */}
        <div className="w-full lg:w-80 flex-shrink-0">
          <div className="aspect-video rounded-xl overflow-hidden bg-gray-200">
            {stream.thumbnail_url ? (
              <img
                src={stream.thumbnail_url}
                alt={stream.name}
                className="w-full h-full object-cover"
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center text-gray-400">
                <svg className="w-12 h-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
              </div>
            )}
          </div>
          <a
            href={`https://www.youtube.com/watch?v=${stream.youtube_video_id}`}
            target="_blank"
            rel="noopener noreferrer"
            className="btn-secondary w-full mt-3"
          >
            <svg className="w-5 h-5 text-red-600" viewBox="0 0 24 24" fill="currentColor">
              <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z" />
            </svg>
            Watch on YouTube
          </a>
        </div>

        {/* Info */}
        <div className="flex-1">
          <div className="flex items-start justify-between gap-4">
            <div>
              <span
                className={`badge mb-2 ${
                  stream.is_live
                    ? 'badge-success'
                    : 'badge-gray'
                }`}
              >
                {stream.is_live ? 'live' : 'offline'}
              </span>
              {isEditing ? (
                <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
                  <div>
                    <label className="form-label">Title</label>
                    <input
                      {...register('name', { required: 'Title is required' })}
                      className={`form-input ${errors.name ? 'border-red-500' : ''}`}
                    />
                    {errors.name && <p className="form-error">{errors.name.message}</p>}
                  </div>
                  <div>
                    <label className="form-label">Channel Name</label>
                    <input
                      {...register('channel', { required: 'Channel name is required' })}
                      className={`form-input ${errors.channel ? 'border-red-500' : ''}`}
                    />
                    {errors.channel && (
                      <p className="form-error">{errors.channel.message}</p>
                    )}
                  </div>
                  <div>
                    <label className="form-label">Status</label>
                    <select {...register('is_live')} className="form-input">
                      <option value="true">Live</option>
                      <option value="false">Offline</option>
                    </select>
                  </div>
                  <div className="flex items-center gap-3">
                    <button
                      type="submit"
                      disabled={updateMutation.isPending}
                      className="btn-primary"
                    >
                      {updateMutation.isPending ? (
                        <>
                          <div className="spinner w-4 h-4" />
                          Saving...
                        </>
                      ) : (
                        'Save Changes'
                      )}
                    </button>
                    <button type="button" onClick={handleCancelEdit} className="btn-secondary">
                      Cancel
                    </button>
                  </div>
                </form>
              ) : (
                <>
                  <h1 className="text-2xl font-bold text-gray-900">{stream.name}</h1>
                  <p className="text-gray-600 mt-1">{stream.channel}</p>
                </>
              )}
            </div>
            {!isEditing && (
              <div className="flex items-center gap-2">
                <button onClick={handleEdit} className="btn-secondary btn-sm">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                  </svg>
                  Edit
                </button>
                <button onClick={() => setShowDeleteModal(true)} className="btn-danger btn-sm">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                  Delete
                </button>
              </div>
            )}
          </div>

          {/* Stats */}
          {!isEditing && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
              <div className="p-4 bg-gray-50 rounded-lg">
                <p className="text-sm text-gray-500">Current Viewers</p>
                <p className="text-xl font-bold text-gray-900">
                  {stream.current_viewers !== undefined ? formatViewers(stream.current_viewers) : '-'}
                </p>
              </div>
              <div className="p-4 bg-gray-50 rounded-lg">
                <p className="text-sm text-gray-500">Peak Viewers</p>
                <p className="text-xl font-bold text-gray-900">
                  {stream.peak_viewers !== undefined ? formatViewers(stream.peak_viewers) : '-'}
                </p>
              </div>
              <div className="p-4 bg-gray-50 rounded-lg">
                <p className="text-sm text-gray-500">Updated</p>
                <p className="text-sm font-medium text-gray-900">
                  {format(new Date(stream.updated_at), 'MMM d, yyyy HH:mm')}
                </p>
              </div>
              <div className="p-4 bg-gray-50 rounded-lg">
                <p className="text-sm text-gray-500">Added</p>
                <p className="text-sm font-medium text-gray-900">
                  {format(new Date(stream.created_at), 'MMM d, yyyy HH:mm')}
                </p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Viewership Chart */}
      <div className="card">
        <div className="card-header">
          <h3 className="text-lg font-semibold text-gray-900">Viewership History</h3>
        </div>
        <div className="card-body">
          {historyLoading ? (
            <div className="h-80 flex items-center justify-center">
              <div className="spinner w-8 h-8" />
            </div>
          ) : chartData && chartData.length > 0 ? (
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis dataKey="time" stroke="#6b7280" fontSize={12} />
                  <YAxis
                    stroke="#6b7280"
                    fontSize={12}
                    tickFormatter={(value) => formatViewers(value)}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#fff',
                      border: '1px solid #e5e7eb',
                      borderRadius: '8px',
                      boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
                    }}
                    formatter={(value: number) => [formatViewers(value), 'Viewers']}
                  />
                  <Legend />
                  <Line
                    type="monotone"
                    dataKey="viewers"
                    stroke="#3b82f6"
                    strokeWidth={2}
                    dot={false}
                    activeDot={{ r: 6 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="h-80 flex items-center justify-center text-gray-500">
              <div className="text-center">
                <svg className="w-12 h-12 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
                <p>No viewership data available yet</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Raw History Table */}
      <div className="card">
        <div className="card-header flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900">Raw Viewership Data</h3>
          {history && (
            <span className="text-sm text-gray-500">
              {history.total} records
            </span>
          )}
        </div>
        <div className="overflow-x-auto">
          <table className="data-table">
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Viewer Count</th>
                <th>Anomaly</th>
              </tr>
            </thead>
            <tbody>
              {historyLoading ? (
                [...Array(5)].map((_, i) => (
                  <tr key={i}>
                    <td><div className="h-4 bg-gray-200 rounded animate-pulse w-40" /></td>
                    <td><div className="h-4 bg-gray-200 rounded animate-pulse w-20" /></td>
                    <td><div className="h-4 bg-gray-200 rounded animate-pulse w-16" /></td>
                  </tr>
                ))
              ) : history?.records.length === 0 ? (
                <tr>
                  <td colSpan={3} className="text-center py-8 text-gray-500">
                    No viewership records yet
                  </td>
                </tr>
              ) : (
                history?.records.map((record) => (
                  <tr key={record.id}>
                    <td>{format(new Date(record.recorded_at), 'MMM d, yyyy HH:mm:ss')}</td>
                    <td className="font-medium">{record.viewer_count.toLocaleString()}</td>
                    <td>
                      {record.is_anomaly ? (
                        <span className="badge badge-warning">Yes</span>
                      ) : (
                        <span className="badge badge-gray">No</span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        {history && Math.ceil(history.total / 50) > 1 && (
          <Pagination
            currentPage={historyPage}
            totalPages={Math.ceil(history.total / 50)}
            totalItems={history.total}
            pageSize={50}
            onPageChange={setHistoryPage}
          />
        )}
      </div>

      {/* Delete Modal */}
      <DeleteModal
        isOpen={showDeleteModal}
        onClose={() => setShowDeleteModal(false)}
        onConfirm={handleDelete}
        title="Delete Livestream"
        message={`Are you sure you want to delete "${stream.name}"? This action cannot be undone and will remove all associated viewership history.`}
        isLoading={deleteMutation.isPending}
      />
    </div>
  );
};
