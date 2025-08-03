################################################################
# MULTI-LAYER ANOMALY FLAGGER (MAF) SYSTEM - COMPLETE SCHEMA
################################################################

-- Step 1: Add missing columns to existing detected_anomalies table
DO $$
BEGIN
    -- Add pattern_name column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'detected_anomalies' AND column_name = 'pattern_name'
    ) THEN
        ALTER TABLE detected_anomalies ADD COLUMN pattern_name TEXT;
        RAISE NOTICE 'Added pattern_name column to detected_anomalies table';
    END IF;

    -- Add fingerprint_data column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'detected_anomalies' AND column_name = 'fingerprint_data'
    ) THEN
        ALTER TABLE detected_anomalies ADD COLUMN fingerprint_data JSONB DEFAULT '{}'::jsonb;
        RAISE NOTICE 'Added fingerprint_data column to detected_anomalies table';
    END IF;

    -- Add risk_score column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'detected_anomalies' AND column_name = 'risk_score'
    ) THEN
        ALTER TABLE detected_anomalies ADD COLUMN risk_score INTEGER DEFAULT 0;
        RAISE NOTICE 'Added risk_score column to detected_anomalies table';
    END IF;

    -- Add status column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'detected_anomalies' AND column_name = 'status'
    ) THEN
        ALTER TABLE detected_anomalies ADD COLUMN status TEXT DEFAULT 'active';
        RAISE NOTICE 'Added status column to detected_anomalies table';
    END IF;

    RAISE NOTICE 'All missing columns added to detected_anomalies table!';
END
$$;

-- Step 2: Create MAF-specific tables
-- Fingerprint data storage for device tracking
CREATE TABLE IF NOT EXISTS public.fingerprint_data (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    ip_address INET NOT NULL,
    user_agent TEXT,
    device_hash TEXT NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    confidence_score DECIMAL(3,2) DEFAULT 0.80,
    geolocation JSONB DEFAULT '{}'::jsonb,
    browser_details JSONB DEFAULT '{}'::jsonb,
    canvas_fingerprint TEXT,
    webgl_fingerprint TEXT,
    screen_resolution TEXT,
    timezone TEXT,
    language TEXT,
    visitor_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT fingerprint_data_user_id_fkey FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

-- User flag history for tracking flag changes over time
CREATE TABLE IF NOT EXISTS public.user_flag_history (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    flag_color TEXT NOT NULL CHECK (flag_color IN ('GREEN', 'YELLOW', 'RED')),
    behavior_score INTEGER,
    anomaly_count INTEGER DEFAULT 0,
    velocity_score TEXT CHECK (velocity_score IN ('low', 'medium', 'high')),
    fingerprint_id TEXT,
    confidence_score DECIMAL(3,2),
    geolocation JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    processed_by TEXT DEFAULT 'MAF',
    CONSTRAINT flag_history_user_id_fkey FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

-- MAF processing statistics
CREATE TABLE IF NOT EXISTS public.maf_statistics (
    id BIGSERIAL PRIMARY KEY,
    date DATE DEFAULT CURRENT_DATE,
    total_events_processed INTEGER DEFAULT 0,
    green_flags INTEGER DEFAULT 0,
    yellow_flags INTEGER DEFAULT 0,
    red_flags INTEGER DEFAULT 0,
    anomalies_detected INTEGER DEFAULT 0,
    false_positives INTEGER DEFAULT 0,
    processing_time_avg_ms INTEGER DEFAULT 0,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

################################################################
# MAF PERFORMANCE INDEXES
################################################################

-- Step 3: Create performance indexes for all MAF tables
-- Fingerprint data indexes
CREATE INDEX idx_fingerprint_user_id ON fingerprint_data(user_id);
CREATE INDEX idx_fingerprint_timestamp ON fingerprint_data(timestamp);
CREATE INDEX idx_fingerprint_event_type ON fingerprint_data(event_type);
CREATE INDEX idx_fingerprint_ip_address ON fingerprint_data(ip_address);
CREATE INDEX idx_fingerprint_device_hash ON fingerprint_data(device_hash);

-- User flag history indexes
CREATE INDEX idx_flag_history_user_id ON user_flag_history(user_id);
CREATE INDEX idx_flag_history_flag_color ON user_flag_history(flag_color);
CREATE INDEX idx_flag_history_created_at ON user_flag_history(created_at);

-- Enhanced detected_anomalies indexes (for new columns)
CREATE INDEX idx_anomalies_pattern_name ON detected_anomalies(pattern_name);
CREATE INDEX idx_anomalies_risk_score ON detected_anomalies(risk_score);
CREATE INDEX idx_anomalies_status ON detected_anomalies(status);

-- MAF statistics indexes
CREATE INDEX IF NOT EXISTS idx_maf_stats_date ON maf_statistics(date);

################################################################
# MAF HELPER FUNCTIONS
################################################################

-- Function to get user's recent flag distribution
CREATE OR REPLACE FUNCTION get_user_flag_distribution(
    p_user_id TEXT,
    p_days INTEGER DEFAULT 7
) RETURNS TABLE (
    flag_color TEXT,
    count BIGINT,
    percentage DECIMAL(5,2)
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ufh.flag_color,
        COUNT(*) as count,
        ROUND((COUNT(*) * 100.0 / SUM(COUNT(*)) OVER()), 2) as percentage
    FROM user_flag_history ufh
    WHERE ufh.user_id = p_user_id 
      AND ufh.created_at >= NOW() - INTERVAL '1 day' * p_days
    GROUP BY ufh.flag_color
    ORDER BY count DESC;
END;
$$ LANGUAGE plpgsql;

-- Function to detect IP-based anomalies
CREATE OR REPLACE FUNCTION detect_ip_anomalies(
    p_hours INTEGER DEFAULT 1,
    p_threshold INTEGER DEFAULT 5
) RETURNS TABLE (
    ip_address INET,
    event_count BIGINT,
    unique_users BIGINT,
    risk_score INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        fd.ip_address,
        COUNT(*) as event_count,
        COUNT(DISTINCT fd.user_id) as unique_users,
        CASE 
            WHEN COUNT(*) > p_threshold * 3 THEN 100
            WHEN COUNT(*) > p_threshold * 2 THEN 75
            WHEN COUNT(*) > p_threshold THEN 50
            ELSE 25
        END as risk_score
    FROM fingerprint_data fd
    WHERE fd.timestamp >= NOW() - INTERVAL '1 hour' * p_hours
    GROUP BY fd.ip_address
    HAVING COUNT(*) > p_threshold
    ORDER BY event_count DESC;
END;
$$ LANGUAGE plpgsql;

################################################################
# MAF ANALYTICS VIEWS
################################################################

-- Real-time anomaly dashboard view
CREATE OR REPLACE VIEW maf_dashboard AS
SELECT 
    DATE(da.detected_at) as date,
    da.pattern_name,
    da.severity,
    COUNT(*) as anomaly_count,
    AVG(da.risk_score) as avg_risk_score,
    array_agg(DISTINCT da.affected_users) as all_affected_users
FROM detected_anomalies da
WHERE da.detected_at >= NOW() - INTERVAL '24 hours'
  AND da.status = 'active'
GROUP BY DATE(da.detected_at), da.pattern_name, da.severity
ORDER BY date DESC, anomaly_count DESC;

-- User risk profile view
CREATE OR REPLACE VIEW user_risk_profiles AS
SELECT 
    u.id as user_id,
    u.behavior_score,
    ufh.flag_color as current_flag,
    COUNT(da.id) as total_anomalies,
    COUNT(CASE WHEN da.severity = 'HIGH' THEN 1 END) as high_severity_anomalies,
    MAX(ufh.created_at) as last_flagged,
    AVG(ufh.confidence_score) as avg_confidence,
    COUNT(DISTINCT fd.ip_address) as unique_ips_24h,
    COUNT(DISTINCT fd.device_hash) as unique_devices_24h
FROM users u
LEFT JOIN user_flag_history ufh ON u.id = ufh.user_id AND ufh.created_at >= NOW() - INTERVAL '24 hours'
LEFT JOIN detected_anomalies da ON u.id = ANY(da.affected_users) AND da.detected_at >= NOW() - INTERVAL '7 days'
LEFT JOIN fingerprint_data fd ON u.id = fd.user_id AND fd.timestamp >= NOW() - INTERVAL '24 hours'
GROUP BY u.id, u.behavior_score, ufh.flag_color
ORDER BY total_anomalies DESC, high_severity_anomalies DESC;

################################################################
# MAF SCHEMA VERSION TRACKING
################################################################

-- Update schema version for MAF
INSERT INTO schema_version (version, description)
VALUES ('1.2.0', 'Multi-Layer Anomaly Flagger (MAF) system with fingerprinting and real-time anomaly detection')
ON CONFLICT (version) DO UPDATE SET 
    applied_at = NOW(),
    description = EXCLUDED.description;

################################################################
# COMMENTS FOR MAF TABLES
################################################################

COMMENT ON TABLE fingerprint_data IS 'Device fingerprinting data for anomaly detection and fraud prevention';
COMMENT ON TABLE user_flag_history IS 'Historical tracking of user flag color changes (GREEN/YELLOW/RED)';
COMMENT ON TABLE maf_statistics IS 'Daily statistics for MAF system performance monitoring and analytics';

COMMENT ON COLUMN fingerprint_data.device_hash IS 'SHA256 hash of device fingerprint components for unique identification';
COMMENT ON COLUMN fingerprint_data.confidence_score IS 'FingerprintJS confidence score (0.00-1.00) indicating fingerprint reliability';
COMMENT ON COLUMN user_flag_history.flag_color IS 'Risk flag classification: GREEN (trusted), YELLOW (medium risk), RED (high risk)';
COMMENT ON COLUMN detected_anomalies.pattern_name IS 'Name of the anomaly pattern detected (e.g., same_ip_signups, rapid_actions)';
COMMENT ON COLUMN detected_anomalies.risk_score IS 'Calculated risk score (0-100) for the detected anomaly';

-- End of MAF Schema
################################################################
