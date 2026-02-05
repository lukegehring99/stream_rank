import React, { useState, useCallback, useMemo } from 'react';
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
  ReferenceArea,
} from 'recharts';
import { DeleteModal, Pagination } from '../components';
import {
  useLivestream,
  useViewershipHistory,
  useUpdateLivestream,
  useDeleteLivestream,
  useDownsampledViewershipHistory,
} from '../hooks';
import { EditLivestreamForm } from '../types';

// Type for chart data points
interface ChartDataPoint {
  time: number; // Unix timestamp for proper ordering
  displayTime: string;
  viewers: number;
  isDownsampled: boolean;
}

// Type for zoom state
interface ZoomState {
  left: number | null;
  right: number | null;
  refAreaLeft: string | null;
  refAreaRight: string | null;
  isZooming: boolean;
}

export const LivestreamDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const livestreamId = id!;

  // State
  const [isEditing, setIsEditing] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [historyPage, setHistoryPage] = useState(1);
  
  // Zoom state for the chart
  const [zoomState, setZoomState] = useState<ZoomState>({
    left: null,
    right: null,
    refAreaLeft: null,
    refAreaRight: null,
    isZooming: false,
  });
  
  // Time range for refined data fetching
  const [timeRange, setTimeRange] = useState<{ start?: string; end?: string }>({});
  const [currentResolution, setCurrentResolution] = useState<'1m' | '5m' | '10m' | '1hr'>('1hr');

  // Queries
  const { data: stream, isLoading, isError } = useLivestream(livestreamId);
  
  // Raw data for table and detailed view
  const { data: history, isLoading: historyLoading } = useViewershipHistory(
    livestreamId,
    historyPage,
    50
  );
  
  // Downsampled data for overview chart (1hr resolution)
  const { data: downsampledHistory, isLoading: downsampledLoading } = useDownsampledViewershipHistory(
    livestreamId,
    '1hr',
    1000
  );
  
  // Refined data when zoomed in
  const { data: refinedHistory, isLoading: refinedLoading } = useViewershipHistory(
    livestreamId,
    1,
    3000,
    timeRange.start && timeRange.end ? {
      startTime: timeRange.start,
      endTime: timeRange.end,
      downsample: currentResolution,
    } : undefined
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

  // Parse UTC timestamp (backend returns timestamps without Z suffix)
  const parseUTC = (timestamp: string) => {
    return new Date(timestamp.endsWith('Z') ? timestamp : timestamp + 'Z');
  };

  // Prepare chart data from downsampled or refined history
  const chartData = useMemo((): ChartDataPoint[] => {
    const sourceData = timeRange.start && timeRange.end && refinedHistory?.items 
      ? refinedHistory.items 
      : downsampledHistory?.items;
    
    if (!sourceData || sourceData.length === 0) return [];
    
    return sourceData
      .slice()
      .reverse()
      .map((record) => {
        const date = parseUTC(record.timestamp);
        return {
          time: date.getTime(),
          displayTime: format(date, 'MMM d, HH:mm'),
          viewers: record.viewcount,
          isDownsampled: typeof record.id === 'string',
        };
      });
  }, [downsampledHistory?.items, refinedHistory?.items, timeRange]);

  // Determine resolution based on zoom level
  // ~2 days -> 1min, 2-5 days -> 5min, 5-10 days -> 10min, >10 days -> 1hr
  const calculateResolutionForRange = useCallback((startTime: number, endTime: number) => {
    const rangeDays = (endTime - startTime) / (1000 * 60 * 60 * 24);
    
    if (rangeDays <= 2) {
      return '1m'; // 1 min resolution for <= 2 days
    } else if (rangeDays <= 5) {
      return '5m'; // 5 min resolution for 2-5 days
    } else if (rangeDays <= 10) {
      return '10m'; // 10 min resolution for 5-10 days
    }
    return '1hr'; // 1 hour resolution for > 10 days
  }, []);

  // Handle zoom selection start
  const handleMouseDown = (e: { activeLabel?: string }) => {
    if (e?.activeLabel) {
      setZoomState(prev => ({
        ...prev,
        refAreaLeft: e.activeLabel!,
        isZooming: true,
      }));
    }
  };

  // Handle zoom selection move
  const handleMouseMove = (e: { activeLabel?: string }) => {
    if (zoomState.isZooming && e?.activeLabel) {
      setZoomState(prev => ({
        ...prev,
        refAreaRight: e.activeLabel!,
      }));
    }
  };

  // Handle zoom selection end
  const handleMouseUp = () => {
    if (!zoomState.isZooming || !zoomState.refAreaLeft || !zoomState.refAreaRight) {
      setZoomState(prev => ({ ...prev, isZooming: false, refAreaLeft: null, refAreaRight: null }));
      return;
    }

    let left = parseInt(zoomState.refAreaLeft);
    let right = parseInt(zoomState.refAreaRight);

    if (left > right) [left, right] = [right, left];
    
    // Calculate the resolution based on the time range
    const newResolution = calculateResolutionForRange(left, right);
    
    // Update time range for refined query
    setTimeRange({
      start: new Date(left).toISOString(),
      end: new Date(right).toISOString(),
    });
    setCurrentResolution(newResolution);
    
    setZoomState({
      left,
      right,
      refAreaLeft: null,
      refAreaRight: null,
      isZooming: false,
    });
  };

  // Reset zoom
  const handleZoomReset = () => {
    setZoomState({
      left: null,
      right: null,
      refAreaLeft: null,
      refAreaRight: null,
      isZooming: false,
    });
    setTimeRange({});
    setCurrentResolution('1hr');
  };

  // Get visible chart data based on zoom
  const visibleChartData = useMemo(() => {
    if (zoomState.left !== null && zoomState.right !== null) {
      return chartData.filter(d => d.time >= zoomState.left! && d.time <= zoomState.right!);
    }
    return chartData;
  }, [chartData, zoomState.left, zoomState.right]);

  // Format axis tick based on data density
  const formatAxisTick = (timestamp: number) => {
    const date = new Date(timestamp);
    if (currentResolution === '1m' || currentResolution === '5m') {
      return format(date, 'HH:mm');
    }
    return format(date, 'MMM d, HH:mm');
  };

  // Custom tooltip
  const CustomTooltip = ({ active, payload, label }: { active?: boolean; payload?: Array<{ value: number }>; label?: number }) => {
    if (active && payload && payload.length && label) {
      const date = new Date(label);
      return (
        <div className="bg-white p-3 rounded-lg shadow-lg border border-gray-200">
          <p className="text-sm text-gray-500 mb-1">
            {format(date, 'EEEE, MMM d, yyyy')}
          </p>
          <p className="text-sm font-medium text-gray-900">
            {format(date, 'HH:mm:ss')}
          </p>
          <p className="text-lg font-bold text-blue-600 mt-1">
            {formatViewers(payload[0].value)} viewers
          </p>
          <p className="text-xs text-gray-400 mt-1">
            Resolution: {currentResolution}
          </p>
        </div>
      );
    }
    return null;
  };

  const chartLoading = downsampledLoading || (timeRange.start && refinedLoading);

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
        {/* Embedded YouTube Player */}
        <div className="w-full lg:w-96 flex-shrink-0">
          <div className="aspect-video rounded-xl overflow-hidden bg-gray-900">
            <iframe
              src={`https://www.youtube.com/embed/${stream.youtube_video_id}?autoplay=0`}
              title={stream.name}
              className="w-full h-full"
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
              allowFullScreen
            />
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
            Open in YouTube
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
                  {stream.current_viewers != null ? formatViewers(stream.current_viewers) : '-'}
                </p>
              </div>
              <div className="p-4 bg-gray-50 rounded-lg">
                <p className="text-sm text-gray-500">Peak Viewers</p>
                <p className="text-xl font-bold text-gray-900">
                  {stream.peak_viewers != null ? formatViewers(stream.peak_viewers) : '-'}
                </p>
              </div>
              <div className="p-4 bg-gray-50 rounded-lg">
                <p className="text-sm text-gray-500">Updated</p>
                <p className="text-sm font-medium text-gray-900">
                  {parseUTC(stream.updated_at).toLocaleString(undefined, {
                    year: 'numeric',
                    month: 'short',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit',
                    timeZoneName: 'short',
                  })}
                </p>
              </div>
              <div className="p-4 bg-gray-50 rounded-lg">
                <p className="text-sm text-gray-500">Added</p>
                <p className="text-sm font-medium text-gray-900">
                  {parseUTC(stream.created_at).toLocaleString(undefined, {
                    year: 'numeric',
                    month: 'short',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit',
                    timeZoneName: 'short',
                  })}
                </p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Viewership Chart */}
      <div className="card">
        <div className="card-header flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Viewership History</h3>
            <p className="text-sm text-gray-500 mt-1">
              Resolution: {currentResolution}
              {zoomState.left !== null && (
                <span className="ml-2">
                  • Viewing: {format(new Date(zoomState.left), 'MMM d, HH:mm')} - {format(new Date(zoomState.right!), 'MMM d, HH:mm')}
                </span>
              )}
            </p>
          </div>
          <div className="flex items-center gap-2">
            {(zoomState.left !== null || timeRange.start) && (
              <button
                onClick={handleZoomReset}
                className="btn-secondary btn-sm"
              >
                <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM13 10H7" />
                </svg>
                Reset Zoom
              </button>
            )}
            <span className="text-xs text-gray-400">
              Drag to zoom
            </span>
          </div>
        </div>
        <div className="card-body">
          {chartLoading ? (
            <div className="h-96 flex items-center justify-center">
              <div className="spinner w-8 h-8" />
            </div>
          ) : visibleChartData && visibleChartData.length > 0 ? (
            <div className="h-96 select-none">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart
                  data={visibleChartData}
                  onMouseDown={handleMouseDown}
                  onMouseMove={handleMouseMove}
                  onMouseUp={handleMouseUp}
                  onMouseLeave={() => {
                    if (zoomState.isZooming) {
                      setZoomState(prev => ({ ...prev, isZooming: false, refAreaLeft: null, refAreaRight: null }));
                    }
                  }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis
                    dataKey="time"
                    type="number"
                    domain={['dataMin', 'dataMax']}
                    tickFormatter={formatAxisTick}
                    stroke="#6b7280"
                    fontSize={11}
                    tick={{ fill: '#6b7280' }}
                    tickCount={8}
                  />
                  <YAxis
                    stroke="#6b7280"
                    fontSize={12}
                    tickFormatter={(value) => formatViewers(value)}
                    width={60}
                  />
                  <Tooltip content={<CustomTooltip />} />
                  <Legend 
                    formatter={() => 'Viewers'}
                    wrapperStyle={{ paddingTop: '10px' }}
                  />
                  <Line
                    type="monotone"
                    dataKey="viewers"
                    stroke="#3b82f6"
                    strokeWidth={2}
                    dot={false}
                    activeDot={{ r: 6, fill: '#3b82f6', stroke: '#fff', strokeWidth: 2 }}
                    animationDuration={300}
                  />
                  {zoomState.isZooming && zoomState.refAreaLeft && zoomState.refAreaRight && (
                    <ReferenceArea
                      x1={zoomState.refAreaLeft}
                      x2={zoomState.refAreaRight}
                      strokeOpacity={0.3}
                      fill="#3b82f6"
                      fillOpacity={0.2}
                    />
                  )}
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="h-96 flex items-center justify-center text-gray-500">
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
              </tr>
            </thead>
            <tbody>
              {historyLoading ? (
                [...Array(5)].map((_, i) => (
                  <tr key={i}>
                    <td><div className="h-4 bg-gray-200 rounded animate-pulse w-40" /></td>
                    <td><div className="h-4 bg-gray-200 rounded animate-pulse w-20" /></td>
                  </tr>
                ))
              ) : !history?.items || history.items.length === 0 ? (
                <tr>
                  <td colSpan={2} className="text-center py-8 text-gray-500">
                    No viewership records yet
                  </td>
                </tr>
              ) : (
                history.items.map((record) => (
                  <tr key={record.id}>
                    <td>{parseUTC(record.timestamp).toLocaleString(undefined, {
                      year: 'numeric',
                      month: 'short',
                      day: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                      second: '2-digit',
                      timeZoneName: 'short',
                    })}</td>
                    <td className="font-medium">{record.viewcount.toLocaleString()}</td>
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
