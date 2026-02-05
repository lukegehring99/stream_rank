-- Migration: Add peak_viewers column to livestreams table
-- Version: 002
-- Date: 2026-02-05
-- Description: Adds peak_viewers column to track the highest viewer count for each stream

-- Check if column exists before adding
SET @column_exists = (
    SELECT COUNT(*)
    FROM information_schema.columns
    WHERE table_schema = DATABASE()
    AND table_name = 'livestreams'
    AND column_name = 'peak_viewers'
);

-- Only add column if it doesn't exist
SET @sql = IF(@column_exists = 0,
    'ALTER TABLE livestreams ADD COLUMN peak_viewers INT UNSIGNED NOT NULL DEFAULT 0 COMMENT ''Peak viewer count'' AFTER is_live',
    'SELECT ''Column peak_viewers already exists'' AS message'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Initialize peak_viewers from existing viewership history (max viewcount per stream)
UPDATE livestreams ls
SET peak_viewers = COALESCE((
    SELECT MAX(viewcount)
    FROM viewership_history vh
    WHERE vh.livestream_id = ls.id
), 0);

SELECT 'Migration 002_add_peak_viewers completed successfully' AS result;
