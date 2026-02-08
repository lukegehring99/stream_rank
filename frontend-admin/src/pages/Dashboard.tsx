import React from 'react';
import { Link } from 'react-router-dom';
import { useDashboardStats, useLivestreams } from '../hooks';

interface StatCardProps {
  title: string;
  value: string | number;
  icon: React.ReactNode;
  trend?: { value: number; isPositive: boolean };
  color: 'blue' | 'green' | 'yellow' | 'purple';
}

const colorClasses = {
  blue: 'bg-blue-500',
  green: 'bg-green-500',
  yellow: 'bg-yellow-500',
  purple: 'bg-purple-500',
};

const StatCard: React.FC<StatCardProps> = ({ title, value, icon, trend, color }) => (
  <div className="card">
    <div className="card-body">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-gray-500">{title}</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">
            {typeof value === 'number' ? value.toLocaleString() : value}
          </p>
          {trend && (
            <p className={`text-sm mt-2 ${trend.isPositive ? 'text-green-600' : 'text-red-600'}`}>
              {trend.isPositive ? '↑' : '↓'} {Math.abs(trend.value)}% from yesterday
            </p>
          )}
        </div>
        <div className={`w-12 h-12 rounded-xl ${colorClasses[color]} flex items-center justify-center`}>
          {icon}
        </div>
      </div>
    </div>
  </div>
);

export const Dashboard: React.FC = () => {
  const { data: stats, isLoading: statsLoading } = useDashboardStats();
  const { data: recentStreams, isLoading: streamsLoading } = useLivestreams({ page_size: 5 });

  const formatViewers = (count: number) => {
    if (count >= 1000000) {
      return (count / 1000000).toFixed(1) + 'M';
    }
    if (count >= 1000) {
      return (count / 1000).toFixed(1) + 'K';
    }
    return count.toString();
  };

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-500 mt-1">Welcome to Stream Rank Admin</p>
        </div>
        <Link to="/livestreams/add" className="btn-primary">
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Add Livestream
        </Link>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {statsLoading ? (
          [...Array(4)].map((_, i) => (
            <div key={i} className="card">
              <div className="card-body">
                <div className="animate-pulse">
                  <div className="h-4 bg-gray-200 rounded w-1/2 mb-3" />
                  <div className="h-8 bg-gray-200 rounded w-3/4" />
                </div>
              </div>
            </div>
          ))
        ) : (
          <>
            <StatCard
              title="Total Streams"
              value={stats?.total_streams || 0}
              color="blue"
              icon={
                <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
              }
            />
            <StatCard
              title="Live Now"
              value={stats?.live_streams || 0}
              color="green"
              icon={
                <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5.636 18.364a9 9 0 010-12.728m12.728 0a9 9 0 010 12.728m-9.9-2.829a5 5 0 010-7.07m7.072 0a5 5 0 010 7.07M13 12a1 1 0 11-2 0 1 1 0 012 0z" />
                </svg>
              }
            />
            <StatCard
              title="Total Viewers"
              value={formatViewers(stats?.total_viewers || 0)}
              color="yellow"
              icon={
                <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                </svg>
              }
            />
            <StatCard
              title="Peak Viewers Today"
              value={formatViewers(stats?.peak_viewers_today || 0)}
              color="purple"
              icon={
                <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                </svg>
              }
            />
          </>
        )}
      </div>

      {/* Quick Actions & Recent Streams */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Quick Actions */}
        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-semibold text-gray-900">Quick Actions</h3>
          </div>
          <div className="card-body space-y-3">
            <Link
              to="/livestreams/add"
              className="flex items-center gap-3 p-3 rounded-lg hover:bg-gray-50 transition-colors group"
            >
              <div className="w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center group-hover:bg-blue-200 transition-colors">
                <svg className="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
              </div>
              <div>
                <p className="font-medium text-gray-900">Add Livestream</p>
                <p className="text-sm text-gray-500">Add a new YouTube stream</p>
              </div>
            </Link>
            <Link
              to="/livestreams"
              className="flex items-center gap-3 p-3 rounded-lg hover:bg-gray-50 transition-colors group"
            >
              <div className="w-10 h-10 rounded-lg bg-green-100 flex items-center justify-center group-hover:bg-green-200 transition-colors">
                <svg className="w-5 h-5 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 10h16M4 14h16M4 18h16" />
                </svg>
              </div>
              <div>
                <p className="font-medium text-gray-900">View All Streams</p>
                <p className="text-sm text-gray-500">Manage existing streams</p>
              </div>
            </Link>
            <Link
              to="/livestreams?is_live=true"
              className="flex items-center gap-3 p-3 rounded-lg hover:bg-gray-50 transition-colors group"
            >
              <div className="w-10 h-10 rounded-lg bg-red-100 flex items-center justify-center group-hover:bg-red-200 transition-colors">
                <svg className="w-5 h-5 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5.636 18.364a9 9 0 010-12.728m12.728 0a9 9 0 010 12.728m-9.9-2.829a5 5 0 010-7.07m7.072 0a5 5 0 010 7.07M13 12a1 1 0 11-2 0 1 1 0 012 0z" />
                </svg>
              </div>
              <div>
                <p className="font-medium text-gray-900">Live Streams</p>
                <p className="text-sm text-gray-500">View currently live streams</p>
              </div>
            </Link>
          </div>
        </div>

        {/* Recent Streams */}
        <div className="card lg:col-span-2">
          <div className="card-header flex items-center justify-between">
            <h3 className="text-lg font-semibold text-gray-900">Recent Streams</h3>
            <Link to="/livestreams" className="text-sm text-primary-600 hover:text-primary-700 font-medium">
              View all →
            </Link>
          </div>
          <div className="divide-y divide-gray-200">
            {streamsLoading ? (
              [...Array(5)].map((_, i) => (
                <div key={i} className="p-4">
                  <div className="flex items-center gap-4 animate-pulse">
                    <div className="w-20 h-12 bg-gray-200 rounded" />
                    <div className="flex-1">
                      <div className="h-4 bg-gray-200 rounded w-3/4 mb-2" />
                      <div className="h-3 bg-gray-200 rounded w-1/2" />
                    </div>
                  </div>
                </div>
              ))
            ) : recentStreams?.items.length === 0 ? (
              <div className="p-8 text-center text-gray-500">
                <p>No streams yet</p>
                <Link to="/livestreams/add" className="text-primary-600 hover:text-primary-700 font-medium">
                  Add your first stream
                </Link>
              </div>
            ) : (
              recentStreams?.items.map((stream) => (
                <Link
                  key={stream.id}
                  to={`/livestreams/${stream.id}`}
                  className="flex items-center gap-4 p-4 hover:bg-gray-50 transition-colors"
                >
                  <div className="w-20 h-12 rounded overflow-hidden bg-gray-200 flex-shrink-0">
                    <img
                      src={`https://img.youtube.com/vi/${stream.youtube_video_id}/mqdefault.jpg`}
                      alt={stream.name}
                      className="w-full h-full object-cover"
                    />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-gray-900 truncate">{stream.name}</p>
                    <p className="text-sm text-gray-500 truncate">{stream.channel}</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <span
                      className={`badge ${
                        stream.is_live
                          ? 'badge-success'
                          : 'badge-gray'
                      }`}
                    >
                      {stream.is_live ? 'live' : 'offline'}
                    </span>
                    {stream.current_viewers != null && (
                      <span className="text-sm text-gray-500">
                        {formatViewers(stream.current_viewers)} viewers
                      </span>
                    )}
                  </div>
                </Link>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Activity Timeline */}
      <div className="card">
        <div className="card-header">
          <h3 className="text-lg font-semibold text-gray-900">System Status</h3>
        </div>
        <div className="card-body">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="flex items-center gap-4">
              <div className="w-3 h-3 rounded-full bg-green-500" />
              <div>
                <p className="font-medium text-gray-900">API Server</p>
                <p className="text-sm text-gray-500">Operational</p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <div className="w-3 h-3 rounded-full bg-green-500" />
              <div>
                <p className="font-medium text-gray-900">Data Worker</p>
                <p className="text-sm text-gray-500">Running</p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <div className="w-3 h-3 rounded-full bg-green-500" />
              <div>
                <p className="font-medium text-gray-900">Database</p>
                <p className="text-sm text-gray-500">Connected</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
