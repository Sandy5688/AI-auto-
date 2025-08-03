################################################################
# SCHEDULED OPERATIONS LAYER (SOL) - COMPLETE SCHEMA
# This includes existing SOL-related tables + new requirements
################################################################

################################################################
# EXISTING SOL-RELATED TABLES (from your current schema)
################################################################

-- Main users table (SOL needs this for behavior score calculations)
CREATE TABLE IF NOT EXISTS public.users (
    id TEXT NOT NULL,
    behavior_score INTEGER DEFAULT 100,
    role TEXT DEFAULT 'user',
    is_anonymous BOOLEAN DEFAULT false,
    encrypted_token TEXT,
    token_used INTEGER DEFAULT 0,
    is_verified BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    token_updated_at TIMESTAMPTZ,
    token_type TEXT DEFAULT 'api_token',
    weekly_score INTEGER DEFAULT 0,  -- Added for weekly leaderboard
    CONSTRAINT users_pkey PRIMARY KEY (id)
);

-- Token usage history (SOL analyzes this for behavior scoring)
CREATE TABLE IF NOT EXISTS public.token_usage_history (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    tokens_used INTEGER NOT NULL,
    action TEXT NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT token_usage_history_user_id_fkey FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

-- User risk flags (SOL analyzes these for scoring)
CREATE TABLE IF NOT EXISTS public.user_risk_flags (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    flag TEXT NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb,
    risk_score INTEGER DEFAULT 0,
    status TEXT DEFAULT 'active'
);

-- Detected anomalies (SOL processes these for alerts)
CREATE TABLE IF NOT EXISTS public.detected_anomalies (
    id BIGSERIAL PRIMARY KEY,
    anomaly_type TEXT NOT NULL,
    description TEXT NOT NULL,
    severity TEXT DEFAULT 'medium' CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    affected_users TEXT[] DEFAULT '{}',
    detected_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb,
    resolved BOOLEAN DEFAULT false,
    resolved_at TIMESTAMPTZ,
    pattern_name TEXT,
    fingerprint_data JSONB DEFAULT '{}'::jsonb,
    risk_score INTEGER DEFAULT 0,
    status TEXT DEFAULT 'active'
);

-- Job logs (SOL's original logging - keeping for compatibility)
CREATE TABLE IF NOT EXISTS public.job_logs (
    id BIGSERIAL PRIMARY KEY,
    job_name TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('running', 'success', 'failed', 'failed_after_retries', 'error')),
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    payload JSONB DEFAULT '{}'::jsonb,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    execution_time_ms INTEGER,
    server_info JSONB DEFAULT '{}'::jsonb
);

-- System alerts (SOL creates these for failures)
CREATE TABLE IF NOT EXISTS public.system_alerts (
    id BIGSERIAL PRIMARY KEY,
    alert_type TEXT NOT NULL,
    operation TEXT NOT NULL,
    error_message TEXT,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    severity TEXT DEFAULT 'medium' CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    status TEXT DEFAULT 'unresolved' CHECK (status IN ('unresolved', 'investigating', 'resolved', 'ignored')),
    metadata JSONB DEFAULT '{}'::jsonb,
    resolved_by TEXT,
    resolved_at TIMESTAMPTZ
);

-- Weekly rankings (SOL calculates and updates these)
CREATE TABLE IF NOT EXISTS public.weekly_rankings (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    rank INTEGER NOT NULL,
    behavior_score INTEGER NOT NULL,
    previous_rank INTEGER,
    rank_change INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    week_of DATE,
    percentile DECIMAL(5,2),
    CONSTRAINT weekly_rankings_user_id_fkey FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

################################################################
# NEW SOL-REQUIRED TABLES (client specifications)
################################################################

-- Required logs_scheduled_jobs table with exact client specifications
CREATE TABLE IF NOT EXISTS public.logs_scheduled_jobs (
    id BIGSERIAL PRIMARY KEY,
    job_name TEXT NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    status TEXT NOT NULL,
    error_if_any TEXT,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Leaderboard table for daily/weekly rankings
CREATE TABLE IF NOT EXISTS public.leaderboard (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    position INTEGER NOT NULL,
    behavior_score INTEGER NOT NULL,
    previous_position INTEGER,
    position_change INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT leaderboard_user_id_fkey FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

-- Weekly challenges table for meme challenges
CREATE TABLE IF NOT EXISTS public.weekly_challenges (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    description TEXT NOT NULL,
    reward_points INTEGER DEFAULT 0,
    start_date TIMESTAMPTZ DEFAULT NOW(),
    end_date TIMESTAMPTZ,
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Admin alerts for flagged user detection
CREATE TABLE IF NOT EXISTS public.admin_alerts (
    id BIGSERIAL PRIMARY KEY,
    alert_type TEXT NOT NULL,
    priority TEXT DEFAULT 'MEDIUM',
    summary TEXT NOT NULL,
    details JSONB DEFAULT '{}'::jsonb,
    status TEXT DEFAULT 'active',
    assigned_to TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ
);

-- Weekly leaderboard archive
CREATE TABLE IF NOT EXISTS public.weekly_leaderboard_archive (
    id BIGSERIAL PRIMARY KEY,
    week_year INTEGER NOT NULL,
    week_number INTEGER NOT NULL,
    archived_at TIMESTAMPTZ DEFAULT NOW(),
    archived_data TEXT
);

-- Anomaly analysis results storage
CREATE TABLE IF NOT EXISTS public.anomaly_analysis_results (
    id BIGSERIAL PRIMARY KEY,
    analysis_timestamp TIMESTAMPTZ DEFAULT NOW(),
    total_flags INTEGER DEFAULT 0,
    flag_types JSONB DEFAULT '{}'::jsonb,
    severity_distribution JSONB DEFAULT '{}'::jsonb,
    high_risk_users_count INTEGER DEFAULT 0,
    analysis_type TEXT NOT NULL
);

################################################################
# MAF TABLES NEEDED BY SOL (for flagged user detection)
################################################################

-- Fingerprint data (SOL analyzes for activity scoring)
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

-- User flag history (SOL processes for hourly alerts)
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

################################################################
# SOL PERFORMANCE INDEXES
################################################################

-- Existing table indexes (SOL-related)
CREATE INDEX IF NOT EXISTS idx_users_behavior_score ON users(behavior_score);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at);
CREATE INDEX IF NOT EXISTS idx_users_last_updated ON users(last_updated);
CREATE INDEX IF NOT EXISTS idx_token_usage_user_id ON token_usage_history(user_id);
CREATE INDEX IF NOT EXISTS idx_token_usage_timestamp ON token_usage_history(timestamp);
CREATE INDEX IF NOT EXISTS idx_user_risk_flags_user_id ON user_risk_flags(user_id);
CREATE INDEX IF NOT EXISTS idx_user_risk_flags_timestamp ON user_risk_flags(timestamp);
CREATE INDEX IF NOT EXISTS idx_job_logs_job_name ON job_logs(job_name);
CREATE INDEX IF NOT EXISTS idx_job_logs_timestamp ON job_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_job_logs_status ON job_logs(status);
CREATE INDEX IF NOT EXISTS idx_system_alerts_status ON system_alerts(status);
CREATE INDEX IF NOT EXISTS idx_system_alerts_timestamp ON system_alerts(timestamp);
CREATE INDEX IF NOT EXISTS idx_weekly_rankings_user_id ON weekly_rankings(user_id);
CREATE INDEX IF NOT EXISTS idx_weekly_rankings_created_at ON weekly_rankings(created_at);
CREATE INDEX IF NOT EXISTS idx_detected_anomalies_detected_at ON detected_anomalies(detected_at);
CREATE INDEX IF NOT EXISTS idx_detected_anomalies_severity ON detected_anomalies(severity);

-- New SOL table indexes
CREATE INDEX IF NOT EXISTS idx_logs_scheduled_jobs_job_name ON logs_scheduled_jobs(job_name);
CREATE INDEX IF NOT EXISTS idx_logs_scheduled_jobs_timestamp ON logs_scheduled_jobs(timestamp);
CREATE INDEX IF NOT EXISTS idx_logs_scheduled_jobs_status ON logs_scheduled_jobs(status);
CREATE INDEX IF NOT EXISTS idx_leaderboard_position ON leaderboard(position);
CREATE INDEX IF NOT EXISTS idx_leaderboard_user_id ON leaderboard(user_id);
CREATE INDEX IF NOT EXISTS idx_leaderboard_created_at ON leaderboard(created_at);
CREATE INDEX IF NOT EXISTS idx_weekly_challenges_active ON weekly_challenges(active);
CREATE INDEX IF NOT EXISTS idx_weekly_challenges_start_date ON weekly_challenges(start_date);
CREATE INDEX IF NOT EXISTS idx_admin_alerts_status ON admin_alerts(status);
CREATE INDEX IF NOT EXISTS idx_admin_alerts_priority ON admin_alerts(priority);
CREATE INDEX IF NOT EXISTS idx_admin_alerts_created_at ON admin_alerts(created_at);
CREATE INDEX IF NOT EXISTS idx_anomaly_analysis_timestamp ON anomaly_analysis_results(analysis_timestamp);
CREATE INDEX IF NOT EXISTS idx_anomaly_analysis_type ON anomaly_analysis_results(analysis_type);

-- MAF table indexes (needed by SOL)
CREATE INDEX IF NOT EXISTS idx_fingerprint_user_id ON fingerprint_data(user_id);
CREATE INDEX IF NOT EXISTS idx_fingerprint_timestamp ON fingerprint_data(timestamp);
CREATE INDEX IF NOT EXISTS idx_fingerprint_event_type ON fingerprint_data(event_type);
CREATE INDEX IF NOT EXISTS idx_flag_history_user_id ON user_flag_history(user_id);
CREATE INDEX IF NOT EXISTS idx_flag_history_created_at ON user_flag_history(created_at);
CREATE INDEX IF NOT EXISTS idx_flag_history_flag_color ON user_flag_history(flag_color);

################################################################
# SOL HELPER FUNCTIONS
################################################################

-- Function to get recent user activity (used by SOL for scoring)
CREATE OR REPLACE FUNCTION get_user_recent_activity(
    p_user_id TEXT,
    p_hours INTEGER DEFAULT 24
) RETURNS TABLE (
    event_type TEXT,
    timestamp TIMESTAMPTZ,
    ip_address INET
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        fd.event_type,
        fd.timestamp,
        fd.ip_address
    FROM fingerprint_data fd
    WHERE fd.user_id = p_user_id 
      AND fd.timestamp >= NOW() - INTERVAL '1 hour' * p_hours
    ORDER BY fd.timestamp DESC;
END;
$$ LANGUAGE plpgsql;

-- Function to calculate user stability score (used by SOL)
CREATE OR REPLACE FUNCTION calculate_user_stability(
    p_user_id TEXT
) RETURNS INTEGER AS $$
DECLARE
    account_age_days INTEGER;
    risk_flag_count INTEGER;
    stability_score INTEGER := 0;
BEGIN
    -- Calculate account age
    SELECT EXTRACT(DAY FROM NOW() - created_at) INTO account_age_days
    FROM users WHERE id = p_user_id;
    
    -- Count recent risk flags
    SELECT COUNT(*) INTO risk_flag_count
    FROM user_risk_flags 
    WHERE user_id = p_user_id 
      AND timestamp >= NOW() - INTERVAL '30 days';
    
    -- Calculate stability score
    stability_score := LEAST(10, account_age_days / 10); -- Max 10 points for age
    stability_score := stability_score - (risk_flag_count * 2); -- Penalty for flags
    
    RETURN GREATEST(0, stability_score);
END;
$$ LANGUAGE plpgsql;

-- Function to get job health summary (used by SOL monitoring)
CREATE OR REPLACE FUNCTION get_job_health_summary(
    p_days INTEGER DEFAULT 7
) RETURNS TABLE (
    job_name TEXT,
    total_runs INTEGER,
    success_rate DECIMAL(5,2),
    last_run TIMESTAMPTZ,
    last_status TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        lsj.job_name,
        COUNT(*)::INTEGER as total_runs,
        ROUND(
            (COUNT(CASE WHEN lsj.status = 'success' THEN 1 END) * 100.0 / COUNT(*))::DECIMAL, 
            2
        ) as success_rate,
        MAX(lsj.timestamp) as last_run,
        (SELECT status FROM logs_scheduled_jobs 
         WHERE job_name = lsj.job_name 
         ORDER BY timestamp DESC LIMIT 1) as last_status
    FROM logs_scheduled_jobs lsj
    WHERE lsj.timestamp >= NOW() - INTERVAL '1 day' * p_days
    GROUP BY lsj.job_name
    ORDER BY last_run DESC;
END;
$$ LANGUAGE plpgsql;

################################################################
# SOL DATA CLEANUP PROCEDURES
################################################################

-- Cleanup procedure for SOL-related old data
CREATE OR REPLACE FUNCTION cleanup_sol_old_data() RETURNS void AS $$
BEGIN
    -- Clean old scheduled job logs (keep 90 days)
    DELETE FROM logs_scheduled_jobs WHERE timestamp < NOW() - INTERVAL '90 days';
    
    -- Clean old job logs (keep 90 days)
    DELETE FROM job_logs WHERE timestamp < NOW() - INTERVAL '90 days';
    
    -- Clean old leaderboard entries (keep 8 weeks)
    DELETE FROM leaderboard WHERE created_at < NOW() - INTERVAL '8 weeks';
    
    -- Clean resolved admin alerts (keep 60 days)
    DELETE FROM admin_alerts 
    WHERE status != 'active' AND resolved_at < NOW() - INTERVAL '60 days';
    
    -- Clean old weekly rankings (keep 1 year)
    DELETE FROM weekly_rankings WHERE created_at < NOW() - INTERVAL '1 year';
    
    -- Clean old anomaly analysis results (keep 6 months)
    DELETE FROM anomaly_analysis_results WHERE analysis_timestamp < NOW() - INTERVAL '6 months';
    
    -- Clean old fingerprint data (keep 3 months)
    DELETE FROM fingerprint_data WHERE created_at < NOW() - INTERVAL '3 months';
    
    RAISE NOTICE 'SOL old data cleanup completed';
END;
$$ LANGUAGE plpgsql;

################################################################
# SOL ANALYTICS VIEWS
################################################################

-- Daily job performance view
CREATE OR REPLACE VIEW sol_daily_performance AS
SELECT 
    DATE(timestamp) as date,
    job_name,
    COUNT(*) as total_runs,
    COUNT(CASE WHEN status = 'success' THEN 1 END) as successful_runs,
    COUNT(CASE WHEN status != 'success' THEN 1 END) as failed_runs,
    ROUND(
        COUNT(CASE WHEN status = 'success' THEN 1 END) * 100.0 / COUNT(*), 
        2
    ) as success_rate
FROM logs_scheduled_jobs
WHERE timestamp >= NOW() - INTERVAL '30 days'
GROUP BY DATE(timestamp), job_name
ORDER BY date DESC, job_name;

-- User behavior score trends view
CREATE OR REPLACE VIEW user_score_trends AS
SELECT 
    u.id as user_id,
    u.behavior_score as current_score,
    COUNT(urf.id) as risk_flags_30d,
    COUNT(fd.id) as activity_events_7d,
    l.position as current_leaderboard_position,
    wr.rank as weekly_rank
FROM users u
LEFT JOIN user_risk_flags urf ON u.id = urf.user_id 
    AND urf.timestamp >= NOW() - INTERVAL '30 days'
LEFT JOIN fingerprint_data fd ON u.id = fd.user_id 
    AND fd.timestamp >= NOW() - INTERVAL '7 days'
LEFT JOIN leaderboard l ON u.id = l.user_id 
    AND l.created_at = (SELECT MAX(created_at) FROM leaderboard WHERE user_id = u.id)
LEFT JOIN weekly_rankings wr ON u.id = wr.user_id 
    AND wr.created_at = (SELECT MAX(created_at) FROM weekly_rankings WHERE user_id = u.id)
GROUP BY u.id, u.behavior_score, l.position, wr.rank
ORDER BY u.behavior_score DESC;

################################################################
# SOL COMMENTS AND DOCUMENTATION
################################################################

COMMENT ON TABLE logs_scheduled_jobs IS 'Required SOL job logging table with exact client specifications (job_name, timestamp, status, error_if_any)';
COMMENT ON TABLE leaderboard IS 'Daily leaderboard positions calculated by SOL daily refresh job';
COMMENT ON TABLE weekly_challenges IS 'Randomized meme challenges generated by SOL weekly job';
COMMENT ON TABLE admin_alerts IS 'Admin dashboard alerts generated by SOL hourly flagged user detection';
COMMENT ON TABLE weekly_leaderboard_archive IS 'Archived weekly leaderboard data for historical tracking';
COMMENT ON TABLE anomaly_analysis_results IS 'Results from SOL hourly anomaly analysis and pattern detection';

COMMENT ON FUNCTION get_user_recent_activity IS 'Helper function for SOL behavior score calculations';
COMMENT ON FUNCTION calculate_user_stability IS 'Calculate user stability score for SOL enhanced BSE scoring';
COMMENT ON FUNCTION get_job_health_summary IS 'Monitor SOL job performance and health status';
COMMENT ON FUNCTION cleanup_sol_old_data IS 'Cleanup old SOL-related data to maintain database performance';

################################################################
# SOL SCHEMA VERSION
################################################################

INSERT INTO schema_version (version, description)
VALUES ('1.2.1', 'SOL (Scheduled Operations Layer) complete schema with client requirements and MAF integration')
ON CONFLICT (version) DO UPDATE SET 
    applied_at = NOW(),
    description = EXCLUDED.description;

-- End of SOL Schema
################################################################
