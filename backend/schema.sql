-- StreamRank Database Schema
-- MySQL 8.0+

-- Create database
CREATE DATABASE IF NOT EXISTS streamrank
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE streamrank;

-- Users table for admin authentication
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_users_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Livestreams table for YouTube stream metadata
CREATE TABLE IF NOT EXISTS livestreams (
    id INT AUTO_INCREMENT PRIMARY KEY,
    public_id CHAR(36) NOT NULL UNIQUE COMMENT 'Public UUID for external references',
    youtube_video_id VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    channel VARCHAR(255) NOT NULL,
    description TEXT,
    url VARCHAR(512) NOT NULL,
    is_live BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_livestreams_public_id (public_id),
    INDEX idx_livestreams_youtube_id (youtube_video_id),
    INDEX idx_livestreams_is_live (is_live),
    INDEX idx_livestreams_channel (channel)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Viewership history table for time series data
CREATE TABLE IF NOT EXISTS viewership_history (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    livestream_id INT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    viewcount INT NOT NULL,
    
    FOREIGN KEY (livestream_id) REFERENCES livestreams(id) ON DELETE CASCADE,
    
    INDEX idx_viewership_timestamp (timestamp),
    INDEX idx_viewership_livestream_timestamp (livestream_id, timestamp),
    INDEX idx_viewership_anomaly_detection (livestream_id, timestamp, viewcount)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Stored procedure for chunked cleanup (avoids long locks)
DELIMITER //

CREATE PROCEDURE IF NOT EXISTS cleanup_old_viewership_data(IN retention_days INT, IN chunk_size INT)
BEGIN
    DECLARE done INT DEFAULT 0;
    DECLARE deleted_count INT DEFAULT 0;
    DECLARE total_deleted INT DEFAULT 0;
    DECLARE cutoff_date TIMESTAMP;
    
    SET cutoff_date = DATE_SUB(UTC_TIMESTAMP(), INTERVAL retention_days DAY);
    
    cleanup_loop: LOOP
        DELETE FROM viewership_history
        WHERE timestamp < cutoff_date
        LIMIT chunk_size;
        
        SET deleted_count = ROW_COUNT();
        SET total_deleted = total_deleted + deleted_count;
        
        IF deleted_count < chunk_size THEN
            LEAVE cleanup_loop;
        END IF;
        
        -- Small delay to prevent lock contention
        DO SLEEP(0.1);
    END LOOP cleanup_loop;
    
    SELECT total_deleted AS records_deleted;
END //

DELIMITER ;

-- Event for automatic daily cleanup (optional)
-- Uncomment to enable automatic cleanup at 3 AM UTC
/*
CREATE EVENT IF NOT EXISTS cleanup_viewership_event
ON SCHEDULE EVERY 1 DAY
STARTS (TIMESTAMP(CURRENT_DATE) + INTERVAL 1 DAY + INTERVAL 3 HOUR)
DO
    CALL cleanup_old_viewership_data(30, 1000);
*/
