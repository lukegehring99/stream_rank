-- Migration: Add public_id column to livestreams table
-- Version: 001
-- Date: 2026-01-25
-- Description: Adds a public UUID column to hide internal auto-increment IDs

-- Check if column exists before adding
SET @column_exists = (
    SELECT COUNT(*)
    FROM information_schema.columns
    WHERE table_schema = DATABASE()
    AND table_name = 'livestreams'
    AND column_name = 'public_id'
);

-- Only add column if it doesn't exist
SET @sql = IF(@column_exists = 0,
    'ALTER TABLE livestreams ADD COLUMN public_id CHAR(36) NOT NULL COMMENT ''Public UUID for external references'' AFTER id',
    'SELECT ''Column public_id already exists'' AS message'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Generate UUIDs for existing rows that don't have one
UPDATE livestreams 
SET public_id = UUID() 
WHERE public_id IS NULL OR public_id = '';

-- Add unique constraint if it doesn't exist
SET @constraint_exists = (
    SELECT COUNT(*)
    FROM information_schema.table_constraints
    WHERE table_schema = DATABASE()
    AND table_name = 'livestreams'
    AND constraint_name = 'uq_public_id'
);

SET @sql = IF(@constraint_exists = 0,
    'ALTER TABLE livestreams ADD CONSTRAINT uq_public_id UNIQUE (public_id)',
    'SELECT ''Constraint uq_public_id already exists'' AS message'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Add index for faster lookups
SET @index_exists = (
    SELECT COUNT(*)
    FROM information_schema.statistics
    WHERE table_schema = DATABASE()
    AND table_name = 'livestreams'
    AND index_name = 'idx_livestreams_public_id'
);

SET @sql = IF(@index_exists = 0,
    'CREATE INDEX idx_livestreams_public_id ON livestreams (public_id)',
    'SELECT ''Index idx_livestreams_public_id already exists'' AS message'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SELECT 'Migration 001_add_public_id completed successfully' AS result;
