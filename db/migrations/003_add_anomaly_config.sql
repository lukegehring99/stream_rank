-- Migration: Add anomaly_config table for experimental settings
-- Version: 003
-- Date: 2026-02-06
-- Description: Adds anomaly_config table to store algorithm parameters

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

-- Index for fast key lookups
CREATE INDEX idx_anomaly_config_key ON anomaly_config(`key`);

SELECT 'Migration 003_add_anomaly_config completed successfully' AS result;
