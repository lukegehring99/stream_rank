-- Seed data for development
-- Run after schema.sql

USE streamrank;

-- Insert default admin user (password: admin123)
-- Hash generated with bcrypt
INSERT INTO users (username, password_hash) VALUES
    ('admin', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.VttYf/1X0CCzZu')
ON DUPLICATE KEY UPDATE username = username;

-- Insert sample livestreams (real volcano monitoring streams)
INSERT INTO livestreams (youtube_video_id, name, channel, description, url, is_live) VALUES
    ('hYKGqKC6y54', 'Kilauea Volcano Live', 'USGS Volcanoes', 
     'Live view of Kilauea Volcano, Hawaii. Streams eruption activity when occurring.',
     'https://www.youtube.com/watch?v=hYKGqKC6y54', TRUE),
    
    ('FfCPLwGlVps', 'Fagradalsfjall Volcano Iceland', 'RUV', 
     'Live stream of Fagradalsfjall volcanic activity in Iceland.',
     'https://www.youtube.com/watch?v=FfCPLwGlVps', TRUE),
    
    ('BA-9QzIcr3c', 'Mount Etna Live', 'Skyline Webcams', 
     'Live HD webcam stream of Mount Etna, Sicily.',
     'https://www.youtube.com/watch?v=BA-9QzIcr3c', TRUE),
    
    ('2LPLNxqvTi0', 'ISS Live Earth View', 'NASA', 
     'Live HD views of Earth from the International Space Station.',
     'https://www.youtube.com/watch?v=2LPLNxqvTi0', TRUE),
    
    ('86YLFOog4GM', 'Yellowstone Geyser Cam', 'Yellowstone NPS', 
     'Live view of Old Faithful and other geysers in Yellowstone.',
     'https://www.youtube.com/watch?v=86YLFOog4GM', TRUE)
ON DUPLICATE KEY UPDATE name = VALUES(name);

-- Insert sample viewership data (last 24 hours with varying patterns)
-- This creates realistic-looking data for testing anomaly detection

-- Generate viewership for each livestream
INSERT INTO viewership_history (livestream_id, timestamp, viewcount)
SELECT 
    ls.id,
    DATE_SUB(UTC_TIMESTAMP(), INTERVAL seq.n MINUTE) as timestamp,
    -- Base viewers + random variation + time-based pattern
    FLOOR(
        CASE ls.id
            WHEN 1 THEN 500  -- Kilauea base
            WHEN 2 THEN 300  -- Fagradalsfjall base
            WHEN 3 THEN 200  -- Etna base
            WHEN 4 THEN 1000 -- ISS base (popular)
            WHEN 5 THEN 150  -- Yellowstone base
        END
        * (1 + 0.3 * SIN(seq.n * 0.1))  -- Daily pattern
        * (0.8 + 0.4 * RAND())           -- Random variation
        -- Add spike for Kilauea in recent data (simulating eruption)
        + CASE WHEN ls.id = 1 AND seq.n < 30 THEN 2000 ELSE 0 END
    ) as viewcount
FROM livestreams ls
CROSS JOIN (
    -- Generate sequence 0-1440 (24 hours * 60 minutes / 3 minute intervals = 480 points)
    SELECT a.N + b.N * 10 + c.N * 100 as n
    FROM 
        (SELECT 0 AS N UNION SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 
         UNION SELECT 5 UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9) a,
        (SELECT 0 AS N UNION SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 
         UNION SELECT 5 UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9) b,
        (SELECT 0 AS N UNION SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4) c
    WHERE a.N + b.N * 10 + c.N * 100 < 480
) seq
WHERE seq.n % 3 = 0;  -- Every 3 minutes
