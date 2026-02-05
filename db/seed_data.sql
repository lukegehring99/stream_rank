-- ============================================================================
-- Trending YouTube Livestreams - Seed Data for Development
-- ============================================================================

USE streamrank;

-- ============================================================================
-- USERS (password is 'admin123' hashed with bcrypt)
-- ============================================================================
INSERT INTO users (username, password_hash, created_at) VALUES
('admin', '$2b$12$BbhCO8mlUDM33FNLi3PxGehqXthYLg3cJmoxP8NysIdWwtQq.T14i', NOW()),
('moderator', '$2b$12$BbhCO8mlUDM33FNLi3PxGehqXthYLg3cJmoxP8NysIdWwtQq.T14i', NOW());

-- ============================================================================
-- LIVESTREAMS
-- ============================================================================
INSERT INTO livestreams (youtube_video_id, name, channel, description, url, is_live, created_at) VALUES
('dQw4w9WgXcQ', '24/7 Lo-Fi Hip Hop Radio - Beats to Relax/Study To', 'Lofi Girl', 
 'Welcome to the Lofi Girl livestream! Chill beats for studying, relaxing, and working.', 
 'https://www.youtube.com/watch?v=dQw4w9WgXcQ', TRUE, NOW()),

('jfKfPfyJRdk', 'lofi hip hop radio 📚 beats to study/relax to', 'Lofi Girl',
 'Listen to the Lofi Girl/Chillhop playlist on Spotify: https://open.spotify.com/...',
 'https://www.youtube.com/watch?v=jfKfPfyJRdk', TRUE, NOW()),

('5qap5aO4i9A', 'lofi hip hop radio - sad & sleepy beats 😴', 'Lofi Girl',
 'Tune in to this sleepy lo-fi beats radio station.',
 'https://www.youtube.com/watch?v=5qap5aO4i9A', TRUE, NOW()),

('rUxyKA_-grg', '📺 24/7 Synthwave Radio - Retrowave - Outrun', 'Synthwave Goose',
 'Non-stop synthwave, retrowave, and outrun music.',
 'https://www.youtube.com/watch?v=rUxyKA_-grg', TRUE, NOW()),

('hHW1oY26kxQ', 'Space Ambient Music LIVE 24/7 🚀 Relaxing Space Journey', 'Relaxation Ambient Music',
 'Explore the cosmos with ambient space music for deep relaxation and focus.',
 'https://www.youtube.com/watch?v=hHW1oY26kxQ', TRUE, NOW()),

('21qNxnCS8WU', 'Jazz Radio 🎷 Relaxing Jazz Music 24/7', 'Cafe Music BGM Channel',
 'Relaxing jazz music for working, studying, and chilling.',
 'https://www.youtube.com/watch?v=21qNxnCS8WU', FALSE, NOW()),

('M7lc1UVf-VE', '🔴 NASA Live: Official Stream of NASA TV', 'NASA',
 'Direct from America\'s space program, NASA TV brings you live coverage of launches and more.',
 'https://www.youtube.com/watch?v=M7lc1UVf-VE', TRUE, NOW()),

('86YLFOog4GM', 'ChilledCow - 24/7 lofi hip hop beats', 'ChilledCow Archive',
 'The original ChilledCow stream archive. RIP the studying girl.',
 'https://www.youtube.com/watch?v=86YLFOog4GM', FALSE, NOW());

-- ============================================================================
-- VIEWERSHIP_HISTORY (Simulated time-series data for the past 7 days)
-- ============================================================================

-- Generate viewership data using a stored procedure for realistic patterns
DELIMITER //

CREATE PROCEDURE generate_seed_viewership()
BEGIN
    DECLARE i INT DEFAULT 0;
    DECLARE stream_id BIGINT;
    DECLARE base_viewers INT;
    DECLARE current_ts DATETIME;
    DECLARE viewer_variance INT;
    
    -- Loop through each livestream
    DECLARE done INT DEFAULT FALSE;
    DECLARE stream_cursor CURSOR FOR SELECT id FROM livestreams;
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = TRUE;
    
    OPEN stream_cursor;
    
    stream_loop: LOOP
        FETCH stream_cursor INTO stream_id;
        IF done THEN
            LEAVE stream_loop;
        END IF;
        
        -- Set base viewers based on stream (some streams are more popular)
        SET base_viewers = 5000 + (stream_id * 3000);
        
        -- Generate data points every 5 minutes for the past 7 days
        -- 7 days * 24 hours * 12 (5-min intervals) = 2016 data points per stream
        SET i = 0;
        WHILE i < 2016 DO
            SET current_ts = DATE_SUB(UTC_TIMESTAMP(), INTERVAL (i * 5) MINUTE);
            
            -- Add some realistic variance (+/- 20% with occasional spikes)
            SET viewer_variance = base_viewers * (80 + FLOOR(RAND() * 40)) / 100;
            
            -- Simulate peak hours (more viewers during evening hours)
            IF HOUR(current_ts) BETWEEN 18 AND 23 THEN
                SET viewer_variance = viewer_variance * 1.5;
            END IF;
            
            -- Simulate weekend boost
            IF DAYOFWEEK(current_ts) IN (1, 7) THEN
                SET viewer_variance = viewer_variance * 1.2;
            END IF;
            
            INSERT INTO viewership_history (livestream_id, timestamp, viewcount)
            VALUES (stream_id, current_ts, viewer_variance);
            
            SET i = i + 1;
        END WHILE;
    END LOOP;
    
    CLOSE stream_cursor;
END //

DELIMITER ;

-- Execute the seed procedure
CALL generate_seed_viewership();

-- Clean up the procedure after use
DROP PROCEDURE IF EXISTS generate_seed_viewership;

-- ============================================================================
-- Quick verification queries
-- ============================================================================
-- SELECT COUNT(*) AS total_viewership_records FROM viewership_history;
-- SELECT l.name, COUNT(v.id) AS data_points, AVG(v.viewcount) AS avg_viewers
-- FROM livestreams l
-- LEFT JOIN viewership_history v ON l.id = v.livestream_id
-- GROUP BY l.id;
