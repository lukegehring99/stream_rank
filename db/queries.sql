-- ============================================================================
-- Trending YouTube Livestreams - Common Queries Reference
-- ============================================================================

-- ============================================================================
-- DATA RETENTION: 30-Day Cleanup Query
-- Run daily via cron: 0 3 * * * mysql -e "source /path/to/cleanup.sql"
-- ============================================================================

-- Simple deletion (for smaller datasets)
DELETE FROM viewership_history 
WHERE timestamp < DATE_SUB(UTC_TIMESTAMP(), INTERVAL 30 DAY);

-- Chunked deletion (for large datasets, prevents long locks)
-- Use the stored procedure: CALL cleanup_old_viewership_data();

-- ============================================================================
-- TRENDING QUERIES
-- ============================================================================

-- Get currently live streams ranked by latest viewcount
SELECT 
    l.id,
    l.name,
    l.channel,
    l.youtube_video_id,
    v.viewcount AS current_viewers,
    v.timestamp AS last_updated
FROM livestreams l
INNER JOIN viewership_history v ON l.id = v.livestream_id
WHERE l.is_live = TRUE
  AND v.timestamp = (
      SELECT MAX(v2.timestamp) 
      FROM viewership_history v2 
      WHERE v2.livestream_id = l.id
  )
ORDER BY v.viewcount DESC
LIMIT 20;

-- Get trending streams (highest growth in last hour)
WITH recent_stats AS (
    SELECT 
        livestream_id,
        MAX(CASE WHEN timestamp >= DATE_SUB(UTC_TIMESTAMP(), INTERVAL 5 MINUTE) 
            THEN viewcount END) AS current_viewers,
        MAX(CASE WHEN timestamp BETWEEN DATE_SUB(UTC_TIMESTAMP(), INTERVAL 65 MINUTE) 
            AND DATE_SUB(UTC_TIMESTAMP(), INTERVAL 55 MINUTE) 
            THEN viewcount END) AS hour_ago_viewers
    FROM viewership_history
    WHERE timestamp >= DATE_SUB(UTC_TIMESTAMP(), INTERVAL 70 MINUTE)
    GROUP BY livestream_id
)
SELECT 
    l.id,
    l.name,
    l.channel,
    rs.current_viewers,
    rs.hour_ago_viewers,
    ROUND(((rs.current_viewers - rs.hour_ago_viewers) / rs.hour_ago_viewers) * 100, 2) AS growth_pct
FROM recent_stats rs
INNER JOIN livestreams l ON l.id = rs.livestream_id
WHERE l.is_live = TRUE
  AND rs.hour_ago_viewers > 0
  AND rs.current_viewers > rs.hour_ago_viewers
ORDER BY growth_pct DESC
LIMIT 10;

-- ============================================================================
-- ANOMALY DETECTION QUERIES
-- ============================================================================

-- Detect viewership spikes (>50% increase in 10 minutes)
WITH windowed_views AS (
    SELECT 
        livestream_id,
        timestamp,
        viewcount,
        LAG(viewcount, 2) OVER (
            PARTITION BY livestream_id 
            ORDER BY timestamp
        ) AS viewcount_10min_ago
    FROM viewership_history
    WHERE timestamp >= DATE_SUB(UTC_TIMESTAMP(), INTERVAL 1 HOUR)
)
SELECT 
    l.name,
    l.channel,
    wv.timestamp,
    wv.viewcount AS current_viewers,
    wv.viewcount_10min_ago AS previous_viewers,
    ROUND(((wv.viewcount - wv.viewcount_10min_ago) / wv.viewcount_10min_ago) * 100, 2) AS spike_pct
FROM windowed_views wv
INNER JOIN livestreams l ON l.id = wv.livestream_id
WHERE wv.viewcount_10min_ago > 0
  AND ((wv.viewcount - wv.viewcount_10min_ago) / wv.viewcount_10min_ago) > 0.5
ORDER BY spike_pct DESC;

-- Detect viewership drops (possible stream issues)
WITH windowed_views AS (
    SELECT 
        livestream_id,
        timestamp,
        viewcount,
        LAG(viewcount, 2) OVER (
            PARTITION BY livestream_id 
            ORDER BY timestamp
        ) AS viewcount_10min_ago
    FROM viewership_history
    WHERE timestamp >= DATE_SUB(UTC_TIMESTAMP(), INTERVAL 1 HOUR)
)
SELECT 
    l.name,
    l.channel,
    wv.timestamp,
    wv.viewcount AS current_viewers,
    wv.viewcount_10min_ago AS previous_viewers,
    ROUND(((wv.viewcount_10min_ago - wv.viewcount) / wv.viewcount_10min_ago) * 100, 2) AS drop_pct
FROM windowed_views wv
INNER JOIN livestreams l ON l.id = wv.livestream_id
WHERE wv.viewcount_10min_ago > 0
  AND ((wv.viewcount_10min_ago - wv.viewcount) / wv.viewcount_10min_ago) > 0.3
ORDER BY drop_pct DESC;

-- ============================================================================
-- TIME-SERIES ANALYSIS QUERIES
-- ============================================================================

-- Get viewership history for a specific stream (chart data)
SELECT 
    timestamp,
    viewcount
FROM viewership_history
WHERE livestream_id = ?
  AND timestamp BETWEEN ? AND ?
ORDER BY timestamp ASC;

-- Get hourly average viewership for a stream
SELECT 
    DATE(timestamp) AS date,
    HOUR(timestamp) AS hour,
    ROUND(AVG(viewcount)) AS avg_viewers,
    MAX(viewcount) AS peak_viewers,
    MIN(viewcount) AS min_viewers
FROM viewership_history
WHERE livestream_id = ?
  AND timestamp >= DATE_SUB(UTC_TIMESTAMP(), INTERVAL 7 DAY)
GROUP BY DATE(timestamp), HOUR(timestamp)
ORDER BY date, hour;

-- Get daily statistics for all streams
SELECT 
    l.id,
    l.name,
    l.channel,
    DATE(v.timestamp) AS date,
    ROUND(AVG(v.viewcount)) AS avg_viewers,
    MAX(v.viewcount) AS peak_viewers,
    COUNT(v.id) AS data_points
FROM livestreams l
INNER JOIN viewership_history v ON l.id = v.livestream_id
WHERE v.timestamp >= DATE_SUB(UTC_TIMESTAMP(), INTERVAL 30 DAY)
GROUP BY l.id, DATE(v.timestamp)
ORDER BY l.id, date;

-- ============================================================================
-- ADMINISTRATIVE QUERIES
-- ============================================================================

-- Check index usage (requires performance_schema)
SELECT 
    object_schema,
    object_name,
    index_name,
    count_fetch,
    count_insert,
    count_update,
    count_delete
FROM performance_schema.table_io_waits_summary_by_index_usage
WHERE object_schema = 'stream_rank'
ORDER BY count_fetch DESC;

-- Table size statistics
SELECT 
    table_name,
    table_rows,
    ROUND(data_length / 1024 / 1024, 2) AS data_size_mb,
    ROUND(index_length / 1024 / 1024, 2) AS index_size_mb,
    ROUND((data_length + index_length) / 1024 / 1024, 2) AS total_size_mb
FROM information_schema.tables
WHERE table_schema = 'stream_rank'
ORDER BY total_size_mb DESC;

-- Check for old data that needs cleanup
SELECT 
    COUNT(*) AS records_to_delete,
    MIN(timestamp) AS oldest_record,
    MAX(timestamp) AS newest_deletable
FROM viewership_history
WHERE timestamp < DATE_SUB(UTC_TIMESTAMP(), INTERVAL 30 DAY);
