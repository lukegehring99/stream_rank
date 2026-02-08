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

// Format viewer count for Y-axis with integers only (no decimals)
const formatViewerCountInteger = (count: number): string => {
  if (count >= 1_000_000) {
    return `${Math.round(count / 1_000_000)}M`;
  }
  if (count >= 1_000) {
    return `${Math.round(count / 1_000)}K`;
  }
  return Math.round(count).toLocaleString();
};

interface ViewershipChartProps {
  data: ViewershipDataPoint[];
  loading: boolean;
  error: string | null;
  theme: 'light' | 'dark';
}

// Parse UTC timestamp (backend returns timestamps without Z suffix)
const parseUTC = (timestamp: string) => {
  return new Date(timestamp.endsWith('Z') ? timestamp : timestamp + 'Z');
};

export const ViewershipChart: React.FC<ViewershipChartProps> = ({
  data,
  loading,
  error,
  theme,
}) => {
  const chartData = useMemo(() => {
    return data.map((point) => {
      const date = parseUTC(point.timestamp);
      return {
        ...point,
        time: date.toLocaleString([], {
          month: 'short',
          day: 'numeric',
          hour: '2-digit',
          minute: '2-digit',
        }),
        tooltipTime: date.toLocaleString([], {
          weekday: 'short',
          month: 'short',
          day: 'numeric',
          year: 'numeric',
          hour: '2-digit',
          minute: '2-digit',
        }),
        formattedViewers: formatViewerCount(point.viewers),
      };
    });
  }, [data]);

  // Vibrant Canva-inspired color scheme
  const colors = {
    light: {
      stroke: '#7B2FF7',
      fill: 'url(#viewershipGradientLight)',
      grid: '#f5f5f5',
      text: '#737373',
      tooltip: {
        bg: '#ffffff',
        border: '#e5e5e5',
        text: '#171717',
      },
    },
    dark: {
      stroke: '#7B2FF7',
      fill: 'url(#viewershipGradientDark)',
      grid: '#262626',
      text: '#737373',
      tooltip: {
        bg: '#171717',
        border: '#262626',
        text: '#fafafa',
      },
    },
  };

  const currentColors = colors[theme];

  if (loading) {
    return (
      <div className="h-48 flex items-center justify-center">
        <LoadingSpinner size="md" label="Loading chart..." />
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-48 flex items-center justify-center">
        <div className="text-center">
          <svg
            className="w-10 h-10 mx-auto text-neutral-300 dark:text-neutral-600 mb-2"
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
          <p className="text-sm text-neutral-500 dark:text-neutral-400">{error}</p>
        </div>
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className="h-48 flex items-center justify-center">
        <p className="text-sm text-neutral-500 dark:text-neutral-400">
          No viewership data available
        </p>
      </div>
    );
  }

  const minViewers = Math.min(...data.map((d) => d.viewers));
  const maxViewers = Math.max(...data.map((d) => d.viewers));
  const padding = (maxViewers - minViewers) * 0.1;

  return (
    <div className="h-48 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart
          data={chartData}
          margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
        >
          <defs>
            <linearGradient id="viewershipGradientLight" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#7B2FF7" stopOpacity={0.3} />
              <stop offset="50%" stopColor="#FF6B57" stopOpacity={0.15} />
              <stop offset="100%" stopColor="#FF6B57" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="viewershipGradientDark" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#7B2FF7" stopOpacity={0.4} />
              <stop offset="50%" stopColor="#FF6B57" stopOpacity={0.2} />
              <stop offset="100%" stopColor="#FF6B57" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid
            strokeDasharray="3 3"
            stroke={currentColors.grid}
            vertical={false}
          />
          <XAxis
            dataKey="time"
            tick={{ fill: currentColors.text, fontSize: 10 }}
            tickLine={false}
            axisLine={{ stroke: currentColors.grid }}
            interval="equidistantPreserveStart"
            tickMargin={15}
            padding={{ left: 10, right: 10 }}
          />
          <YAxis
            tick={{ fill: currentColors.text, fontSize: 10 }}
            tickLine={false}
            axisLine={false}
            tickFormatter={formatViewerCountInteger}
            domain={[minViewers - padding, maxViewers + padding]}
            width={45}
            allowDecimals={false}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: currentColors.tooltip.bg,
              border: `1px solid ${currentColors.tooltip.border}`,
              borderRadius: '12px',
              boxShadow: '0 4px 16px rgba(0, 0, 0, 0.1)',
              fontSize: '12px',
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
            labelFormatter={(_label, payload) => {
              if (payload && payload.length > 0) {
                return payload[0].payload.tooltipTime;
              }
              return _label;
            }}
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
              stroke: theme === 'dark' ? '#0a0a0a' : '#ffffff',
              strokeWidth: 2,
            }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
};
