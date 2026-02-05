import React, { useMemo } from 'react';
import {
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Area,
  AreaChart,
} from 'recharts';
import { ViewershipDataPoint, formatViewerCount } from '../types';
import { LoadingSpinner } from './LoadingSpinner';

interface ViewershipChartProps {
  data: ViewershipDataPoint[];
  loading: boolean;
  error: string | null;
  theme: 'light' | 'dark';
}

export const ViewershipChart: React.FC<ViewershipChartProps> = ({
  data,
  loading,
  error,
  theme,
}) => {
  const chartData = useMemo(() => {
    return data.map((point) => ({
      ...point,
      time: new Date(point.timestamp).toLocaleTimeString([], {
        hour: '2-digit',
        minute: '2-digit',
      }),
      formattedViewers: formatViewerCount(point.viewers),
    }));
  }, [data]);

  const colors = {
    light: {
      stroke: '#0ea5e9',
      fill: 'url(#viewershipGradientLight)',
      grid: '#e2e8f0',
      text: '#64748b',
      tooltip: {
        bg: '#ffffff',
        border: '#e2e8f0',
        text: '#1e293b',
      },
    },
    dark: {
      stroke: '#38bdf8',
      fill: 'url(#viewershipGradientDark)',
      grid: '#334155',
      text: '#94a3b8',
      tooltip: {
        bg: '#1e293b',
        border: '#475569',
        text: '#f1f5f9',
      },
    },
  };

  const currentColors = colors[theme];

  if (loading) {
    return (
      <div className="h-64 flex items-center justify-center">
        <LoadingSpinner size="md" label="Loading chart..." />
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-64 flex items-center justify-center">
        <div className="text-center">
          <svg
            className="w-12 h-12 mx-auto text-slate-400 dark:text-slate-500 mb-2"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
            />
          </svg>
          <p className="text-sm text-slate-500 dark:text-slate-400">{error}</p>
        </div>
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className="h-64 flex items-center justify-center">
        <p className="text-sm text-slate-500 dark:text-slate-400">
          No viewership data available
        </p>
      </div>
    );
  }

  const minViewers = Math.min(...data.map((d) => d.viewers));
  const maxViewers = Math.max(...data.map((d) => d.viewers));
  const padding = (maxViewers - minViewers) * 0.1;

  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart
          data={chartData}
          margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
        >
          <defs>
            <linearGradient id="viewershipGradientLight" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#0ea5e9" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#0ea5e9" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="viewershipGradientDark" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#38bdf8" stopOpacity={0.4} />
              <stop offset="95%" stopColor="#38bdf8" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid
            strokeDasharray="3 3"
            stroke={currentColors.grid}
            vertical={false}
          />
          <XAxis
            dataKey="time"
            tick={{ fill: currentColors.text, fontSize: 11 }}
            tickLine={false}
            axisLine={{ stroke: currentColors.grid }}
            interval="preserveStartEnd"
            minTickGap={50}
          />
          <YAxis
            tick={{ fill: currentColors.text, fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            tickFormatter={formatViewerCount}
            domain={[minViewers - padding, maxViewers + padding]}
            width={50}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: currentColors.tooltip.bg,
              border: `1px solid ${currentColors.tooltip.border}`,
              borderRadius: '8px',
              boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
            }}
            labelStyle={{
              color: currentColors.tooltip.text,
              fontWeight: 600,
              marginBottom: '4px',
            }}
            itemStyle={{ color: currentColors.tooltip.text }}
            formatter={(value: number) => [
              formatViewerCount(value) + ' viewers',
              '',
            ]}
            labelFormatter={(label) => `Time: ${label}`}
          />
          <Area
            type="monotone"
            dataKey="viewers"
            stroke={currentColors.stroke}
            strokeWidth={2}
            fill={currentColors.fill}
            dot={false}
            activeDot={{
              r: 4,
              fill: currentColors.stroke,
              stroke: theme === 'dark' ? '#0f172a' : '#ffffff',
              strokeWidth: 2,
            }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
};
