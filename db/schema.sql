-- ============================================================================
-- Trending YouTube Livestreams - MySQL Schema
-- Version: 1.0.0
-- Created: 2026-01-25
-- ============================================================================

-- Use UTF-8 encoding for proper Unicode support (emoji in stream titles, etc.)
SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;

-- ============================================================================
-- TABLE: livestreams
-- Purpose: Stores metadata for tracked YouTube livestreams
-- ============================================================================
CREATE TABLE IF NOT EXISTS livestreams (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    public_id CHAR(36) NOT NULL COMMENT 'Public UUID for external references',
    youtube_video_id VARCHAR(11) NOT NULL COMMENT 'YouTube video ID (always 11 chars)',
    name VARCHAR(255) NOT NULL COMMENT 'Livestream title',
    channel VARCHAR(255) NOT NULL COMMENT 'Channel name',
    description TEXT COMMENT 'Stream description',
    url VARCHAR(512) NOT NULL COMMENT 'Full YouTube URL',
    is_live BOOLEAN NOT NULL DEFAULT FALSE COMMENT 'Currently streaming',
    peak_viewers INT NOT NULL DEFAULT 0 COMMENT 'Peak viewer count',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    PRIMARY KEY (id),
    CONSTRAINT uq_public_id UNIQUE (public_id),
    CONSTRAINT uq_youtube_video_id UNIQUE (youtube_video_id)
) ENGINE=InnoDB 
  DEFAULT CHARSET=utf8mb4 
  COLLATE=utf8mb4_unicode_ci
  COMMENT='YouTube livestream metadata';

-- ============================================================================
-- TABLE: viewership_history
-- Purpose: Time-series data tracking viewer counts over time
-- ============================================================================
CREATE TABLE IF NOT EXISTS viewership_history (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    livestream_id BIGINT UNSIGNED NOT NULL,
    timestamp DATETIME NOT NULL COMMENT 'UTC timestamp of measurement',
    viewcount INT UNSIGNED NOT NULL DEFAULT 0 COMMENT 'Concurrent viewer count',
    
    PRIMARY KEY (id),
    
    -- Foreign key constraint with CASCADE delete
    -- When a livestream is deleted, all its viewership history is also deleted
    CONSTRAINT fk_viewership_livestream
        FOREIGN KEY (livestream_id) 
        REFERENCES livestreams(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB 
  DEFAULT CHARSET=utf8mb4 
  COLLATE=utf8mb4_unicode_ci
  COMMENT='Time-series viewership data';

-- ============================================================================
-- TABLE: users
-- Purpose: Admin user authentication
-- ============================================================================
CREATE TABLE IF NOT EXISTS users (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    username VARCHAR(50) NOT NULL,
    password_hash VARCHAR(255) NOT NULL COMMENT 'bcrypt hash',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (id),
    CONSTRAINT uq_username UNIQUE (username)
) ENGINE=InnoDB 
  DEFAULT CHARSET=utf8mb4 
  COLLATE=utf8mb4_unicode_ci
  COMMENT='Admin user accounts';

-- ============================================================================
-- INDEXES
-- ============================================================================

-- -----------------------------------------------------------------------------
-- Index: idx_livestreams_public_id
-- Purpose: Fast lookup by public UUID
-- Justification: API endpoints use public_id for external identification
-- -----------------------------------------------------------------------------
CREATE INDEX idx_livestreams_public_id 
    ON livestreams(public_id);

-- -----------------------------------------------------------------------------
-- Index: idx_livestreams_is_live
-- Purpose: Fast filtering of currently live streams for the main dashboard
-- Justification: Frequent queries filter by is_live=TRUE to show active streams
-- -----------------------------------------------------------------------------
CREATE INDEX idx_livestreams_is_live 
    ON livestreams(is_live);

-- -----------------------------------------------------------------------------
-- Index: idx_livestreams_channel
-- Purpose: Fast lookup of streams by channel name
-- Justification: Users often search/filter by channel
-- -----------------------------------------------------------------------------
CREATE INDEX idx_livestreams_channel 
    ON livestreams(channel);

-- -----------------------------------------------------------------------------
-- Index: idx_viewership_timestamp
-- Purpose: Efficient time-range queries for historical data
-- Justification: Core query pattern - fetching viewership within date ranges
-- -----------------------------------------------------------------------------
CREATE INDEX idx_viewership_timestamp 
    ON viewership_history(timestamp);

-- -----------------------------------------------------------------------------
-- Index: idx_viewership_livestream_timestamp (COMPOSITE)
-- Purpose: Optimal performance for per-stream time-series queries
-- Justification: Most common query pattern - get viewership for specific stream
--                within a time range. Composite index allows index-only scans.
-- -----------------------------------------------------------------------------
CREATE INDEX idx_viewership_livestream_timestamp 
    ON viewership_history(livestream_id, timestamp);

-- -----------------------------------------------------------------------------
-- Index: idx_viewership_anomaly_detection (COMPOSITE)
-- Purpose: Efficient anomaly detection queries
-- Justification: Anomaly detection needs to scan viewcount values within time
--                windows per stream. This index supports queries like:
--                "Find streams where viewcount changed by >X% in last Y minutes"
-- -----------------------------------------------------------------------------
CREATE INDEX idx_viewership_anomaly_detection 
    ON viewership_history(livestream_id, timestamp, viewcount);

-- -----------------------------------------------------------------------------
-- Index: idx_viewership_trending (COMPOSITE)  
-- Purpose: Support trending/ranking queries
-- Justification: Queries that rank streams by recent viewcount need to scan
--                by timestamp first, then aggregate by livestream_id
-- -----------------------------------------------------------------------------
CREATE INDEX idx_viewership_trending 
    ON viewership_history(timestamp, livestream_id, viewcount);

-- ============================================================================
-- DATA RETENTION - 30 Day Cleanup Query
-- ============================================================================
-- Run this query daily via cron job or scheduled event to maintain 30-day retention
-- 
-- DELETE FROM viewership_history 
-- WHERE timestamp < DATE_SUB(UTC_TIMESTAMP(), INTERVAL 30 DAY);
--
-- For large tables, use chunked deletion to avoid long locks:
-- ============================================================================

-- ============================================================================
-- TABLE: anomaly_config
-- Purpose: Stores anomaly detection configuration parameters
-- ============================================================================
CREATE TABLE IF NOT EXISTS anomaly_config (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `key` VARCHAR(100) NOT NULL COMMENT 'Parameter key (e.g., algorithm, quantile_params.baseline_percentile)',
    `type` VARCHAR(50) NOT NULL COMMENT 'Python type (str, int, float, bool)',
    `value` VARCHAR(255) NOT NULL COMMENT 'Stringified value',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    PRIMARY KEY (id),
    CONSTRAINT uq_anomaly_config_key UNIQUE (`key`)
) ENGINE=InnoDB 
  DEFAULT CHARSET=utf8mb4 
  COLLATE=utf8mb4_unicode_ci
  COMMENT='Anomaly detection configuration';

CREATE INDEX idx_anomaly_config_key ON anomaly_config(`key`);

-- ============================================================================
-- Stored Procedures
-- ============================================================================

DELIMITER //

CREATE PROCEDURE cleanup_old_viewership_data()
BEGIN
    DECLARE rows_deleted INT DEFAULT 1;
    DECLARE cutoff_date DATETIME;
    
    SET cutoff_date = DATE_SUB(UTC_TIMESTAMP(), INTERVAL 30 DAY);
    
    -- Delete in chunks of 10,000 rows to avoid long-running transactions
    WHILE rows_deleted > 0 DO
        DELETE FROM viewership_history 
        WHERE timestamp < cutoff_date 
        LIMIT 10000;
        
        SET rows_deleted = ROW_COUNT();
        
        -- Small delay to reduce replication lag and allow other queries
        DO SLEEP(0.1);
    END WHILE;
END //

DELIMITER ;

-- ============================================================================
-- MySQL Event Scheduler for automatic cleanup (optional)
-- Requires: SET GLOBAL event_scheduler = ON;
-- ============================================================================

CREATE EVENT IF NOT EXISTS evt_cleanup_viewership_history
ON SCHEDULE EVERY 1 DAY
STARTS (TIMESTAMP(CURRENT_DATE) + INTERVAL 3 HOUR) -- Run at 3 AM
DO CALL cleanup_old_viewership_data();
