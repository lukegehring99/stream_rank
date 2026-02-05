import React, { useState, useMemo } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { DataTable, Pagination, DeleteModal } from '../components';
import { useLivestreams, useDeleteLivestream } from '../hooks';
import { Livestream } from '../types';

export const Livestreams: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  
  // Filter state from URL params
  const page = parseInt(searchParams.get('page') || '1', 10);
  const pageSize = parseInt(searchParams.get('page_size') || '10', 10);
  const search = searchParams.get('search') || '';
  const isLiveFilter = searchParams.get('is_live');
  const sortBy = searchParams.get('sort_by') || 'created_at';
  const sortOrder = (searchParams.get('sort_order') || 'desc') as 'asc' | 'desc';

  // Local state
  const [searchInput, setSearchInput] = useState(search);
  const [deleteId, setDeleteId] = useState<string | null>(null);

  // Queries
  const { data, isLoading, isError, error } = useLivestreams({
    page,
    page_size: pageSize,
    search: search || undefined,
    is_live: isLiveFilter === null ? 'all' : isLiveFilter === 'true',
    sort_by: sortBy,
    sort_order: sortOrder,
  });

  const deleteMutation = useDeleteLivestream();

  // Update URL params
  const updateParams = (updates: Record<string, string | number | undefined>) => {
    const newParams = new URLSearchParams(searchParams);
    Object.entries(updates).forEach(([key, value]) => {
      if (value !== undefined && value !== '' && value !== 'all') {
        newParams.set(key, String(value));
      } else {
        newParams.delete(key);
      }
    });
    setSearchParams(newParams);
  };

  // Handlers
  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    updateParams({ search: searchInput, page: 1 });
  };

  const handleStatusChange = (newStatus: string) => {
    updateParams({ is_live: newStatus === 'all' ? undefined : newStatus, page: 1 });
  };

  const handleSort = (key: string) => {
    const newOrder = sortBy === key && sortOrder === 'asc' ? 'desc' : 'asc';
    updateParams({ sort_by: key, sort_order: newOrder });
  };

  const handlePageChange = (newPage: number) => {
    updateParams({ page: newPage });
  };

  const handleDelete = async () => {
    if (deleteId) {
      await deleteMutation.mutateAsync(deleteId);
      setDeleteId(null);
    }
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

  // Table columns
  const columns = useMemo(
    () => [
      {
        key: 'thumbnail',
        header: '',
        className: 'w-24',
        render: (stream: Livestream) => (
          <div className="w-20 h-12 rounded overflow-hidden bg-gray-200">
            <img
              src={`https://img.youtube.com/vi/${stream.youtube_video_id}/mqdefault.jpg`}
              alt={stream.name}
              className="w-full h-full object-cover"
            />
          </div>
        ),
      },
      {
        key: 'name',
        header: 'Title',
        sortable: true,
        render: (stream: Livestream) => (
          <div className="max-w-xs">
            <p className="font-medium text-gray-900 truncate">{stream.name}</p>
            <p className="text-sm text-gray-500 truncate">{stream.channel}</p>
          </div>
        ),
      },
      {
        key: 'is_live',
        header: 'Status',
        sortable: true,
        render: (stream: Livestream) => (
          <span
            className={`badge ${
              stream.is_live
                ? 'badge-success'
                : 'badge-gray'
            }`}
          >
            {stream.is_live ? 'live' : 'offline'}
          </span>
        ),
      },
      {
        key: 'current_viewers',
        header: 'Viewers',
        sortable: true,
        render: (stream: Livestream) => (
          <span className="font-medium">{stream.current_viewers != null ? formatViewers(stream.current_viewers) : '-'}</span>
        ),
      },
      {
        key: 'peak_viewers',
        header: 'Peak',
        sortable: true,
        render: (stream: Livestream) => (
          <span className="text-gray-600">{stream.peak_viewers != null ? formatViewers(stream.peak_viewers) : '-'}</span>
        ),
      },
      {
        key: 'created_at',
        header: 'Added',
        sortable: true,
        render: (stream: Livestream) => (
          <span className="text-gray-600">
            {parseUTC(stream.created_at).toLocaleDateString(undefined, {
              year: 'numeric',
              month: 'short',
              day: 'numeric',
            })}
          </span>
        ),
      },
      {
        key: 'actions',
        header: '',
        className: 'w-20',
        render: (stream: Livestream) => (
          <div className="flex items-center gap-1">
            <button
              onClick={(e) => {
                e.stopPropagation();
                navigate(`/livestreams/${stream.id}`);
              }}
              className="p-2 rounded-lg text-gray-400 hover:text-primary-600 hover:bg-gray-100"
              title="View details"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
              </svg>
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation();
                setDeleteId(stream.id);
              }}
              className="p-2 rounded-lg text-gray-400 hover:text-red-600 hover:bg-red-50"
              title="Delete"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          </div>
        ),
      },
    ],
    [navigate]
  );

  if (isError) {
    return (
      <div className="card">
        <div className="card-body text-center py-12">
          <div className="text-red-500 mb-4">
            <svg className="w-12 h-12 mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <h3 className="text-lg font-medium text-gray-900">Error loading livestreams</h3>
          <p className="text-gray-500 mt-2">
            {(error as Error)?.message || 'Something went wrong'}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Livestreams</h1>
          <p className="text-gray-500 mt-1">
            Manage and monitor YouTube livestreams
          </p>
        </div>
        <Link to="/livestreams/add" className="btn-primary">
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Add Stream
        </Link>
      </div>

      {/* Filters */}
      <div className="card">
        <div className="card-body">
          <div className="flex flex-col md:flex-row gap-4">
            {/* Search */}
            <form onSubmit={handleSearch} className="flex-1">
              <div className="relative">
                <input
                  type="text"
                  placeholder="Search by title or channel..."
                  value={searchInput}
                  onChange={(e) => setSearchInput(e.target.value)}
                  className="form-input !pl-12"
                />
                <svg
                  className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                {searchInput && (
                  <button
                    type="button"
                    onClick={() => {
                      setSearchInput('');
                      updateParams({ search: undefined, page: 1 });
                    }}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                )}
              </div>
            </form>

            {/* Status Filter */}
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-500">Status:</span>
              <div className="flex rounded-lg border border-gray-200 overflow-hidden">
                {[
                  { value: 'all', label: 'All' },
                  { value: 'true', label: 'Live' },
                  { value: 'false', label: 'Offline' },
                ].map((s) => (
                  <button
                    key={s.value}
                    onClick={() => handleStatusChange(s.value)}
                    className={`px-4 py-2 text-sm font-medium transition-colors ${
                      (isLiveFilter === null && s.value === 'all') || isLiveFilter === s.value
                        ? 'bg-primary-600 text-white'
                        : 'bg-white text-gray-600 hover:bg-gray-50'
                    }`}
                  >
                    {s.label}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="card overflow-hidden">
        <DataTable
          columns={columns}
          data={data?.items || []}
          keyField="id"
          isLoading={isLoading}
          emptyMessage="No livestreams found"
          onRowClick={(stream) => navigate(`/livestreams/${stream.id}`)}
          sortBy={sortBy}
          sortOrder={sortOrder}
          onSort={handleSort}
        />
        {data && data.total_pages > 1 && (
          <Pagination
            currentPage={page}
            totalPages={data.total_pages}
            totalItems={data.total}
            pageSize={pageSize}
            onPageChange={handlePageChange}
          />
        )}
      </div>

      {/* Delete Modal */}
      <DeleteModal
        isOpen={deleteId !== null}
        onClose={() => setDeleteId(null)}
        onConfirm={handleDelete}
        title="Delete Livestream"
        message="Are you sure you want to delete this livestream? This action cannot be undone and will remove all associated viewership history."
        isLoading={deleteMutation.isPending}
      />
    </div>
  );
};
