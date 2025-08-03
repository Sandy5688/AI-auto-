################################################################
# BEHAVIOR SCORING ENGINE - COMPLETE SUPABASE SCHEMA
# This file contains all table schemas required for the project
################################################################

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

################################################################
# CORE USER MANAGEMENT TABLES
################################################################

-- Main users table with enhanced fields
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
    CONSTRAINT users_pkey PRIMARY KEY (id)
);

-- Token usage history for tracking API usage
CREATE TABLE IF NOT EXISTS public.token_usage_history (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    tokens_used INTEGER NOT NULL,
    action TEXT NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT token_usage_history_user_id_fkey FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

################################################################
# RISK MANAGEMENT & FRAUD DETECTION TABLES
################################################################

-- User risk flags with enhanced structure
CREATE TABLE IF NOT EXISTS public.user_risk_flags (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    flag TEXT NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb,
    risk_score INTEGER DEFAULT 0,
    status TEXT DEFAULT 'active'
);

-- Remove the old unique constraint that was too restrictive
DROP INDEX IF EXISTS idx_user_risk_flags_unique;

-- Add better indexes for risk flags
CREATE INDEX IF NOT EXISTS idx_user_risk_flags_user_id ON user_risk_flags(user_id);
CREATE INDEX IF NOT EXISTS idx_user_risk_flags_timestamp ON user_risk_flags(timestamp);
CREATE INDEX IF NOT EXISTS idx_user_risk_flags_flag ON user_risk_flags(flag);

-- Detected anomalies from system monitoring
CREATE TABLE IF NOT EXISTS public.detected_anomalies (
    id BIGSERIAL PRIMARY KEY,
    anomaly_type TEXT NOT NULL,
    description TEXT NOT NULL,
    severity TEXT DEFAULT 'medium' CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    affected_users TEXT[] DEFAULT '{}',
    detected_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb,
    resolved BOOLEAN DEFAULT false,
    resolved_at TIMESTAMPTZ
);

################################################################
# CONTENT GENERATION TABLES
################################################################

-- Generated memes tracking
CREATE TABLE IF NOT EXISTS public.generated_memes (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id TEXT NOT NULL,
    prompt TEXT NOT NULL,
    tone TEXT,
    image_url TEXT,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    tokens_used INTEGER DEFAULT 1,
    used_in_nft BOOLEAN DEFAULT false,
    generation_status TEXT DEFAULT 'completed',
    api_response JSONB,
    CONSTRAINT generated_memes_user_id_fkey FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

################################################################
# SYSTEM OPERATIONS & MONITORING TABLES
################################################################

-- Job logs for scheduled tasks
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

-- System alerts for operational monitoring
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

-- Migration status tracking
CREATE TABLE IF NOT EXISTS public.migration_status (
    id BIGSERIAL PRIMARY KEY,
    migration_name TEXT UNIQUE NOT NULL,
    completed BOOLEAN DEFAULT false,
    completed_at TIMESTAMPTZ,
    migrated_users INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    migration_metadata JSONB DEFAULT '{}'::jsonb
);

################################################################
# WEBHOOK & API MONITORING TABLES
################################################################

-- Skipped payloads for webhook monitoring
CREATE TABLE IF NOT EXISTS public.skipped_payloads (
    id BIGSERIAL PRIMARY KEY,
    payload JSONB,
    reason TEXT NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    endpoint TEXT DEFAULT '/webhook',
    source_ip INET,
    user_agent TEXT,
    error_code TEXT,
    retry_attempted BOOLEAN DEFAULT false
);

################################################################
# ANALYTICS & RANKING TABLES
################################################################

-- Weekly user rankings
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
# SCHEMA MIGRATIONS & UPDATES
################################################################

-- Ensure all required columns exist (idempotent operations)
DO $$
BEGIN
    -- Add last_updated column to users table if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'users' AND column_name = 'last_updated'
    ) THEN
        ALTER TABLE users ADD COLUMN last_updated TIMESTAMPTZ DEFAULT NOW();
        RAISE NOTICE 'Added last_updated column to users table';
    END IF;

    -- Add metadata column to user_risk_flags table if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'user_risk_flags' AND column_name = 'metadata'
    ) THEN
        ALTER TABLE user_risk_flags ADD COLUMN metadata JSONB DEFAULT '{}'::jsonb;
        RAISE NOTICE 'Added metadata column to user_risk_flags table';
    END IF;

    -- Update existing users to have last_updated if null
    UPDATE users SET last_updated = NOW() WHERE last_updated IS NULL;
    
    RAISE NOTICE 'Schema migration checks completed';
END
$$;

################################################################
# PERFORMANCE INDEXES
################################################################

-- Users table indexes
CREATE INDEX IF NOT EXISTS idx_users_behavior_score ON users(behavior_score);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_last_updated ON users(last_updated);

-- Token usage indexes
CREATE INDEX IF NOT EXISTS idx_token_usage_user_id ON token_usage_history(user_id);
CREATE INDEX IF NOT EXISTS idx_token_usage_timestamp ON token_usage_history(timestamp);
CREATE INDEX IF NOT EXISTS idx_token_usage_action ON token_usage_history(action);

-- Generated memes indexes
CREATE INDEX IF NOT EXISTS idx_generated_memes_user_id ON generated_memes(user_id);
CREATE INDEX IF NOT EXISTS idx_generated_memes_timestamp ON generated_memes(timestamp);
CREATE INDEX IF NOT EXISTS idx_generated_memes_tone ON generated_memes(tone);

-- Job logs indexes
CREATE INDEX IF NOT EXISTS idx_job_logs_job_name ON job_logs(job_name);
CREATE INDEX IF NOT EXISTS idx_job_logs_timestamp ON job_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_job_logs_status ON job_logs(status);

-- System alerts indexes
CREATE INDEX IF NOT EXISTS idx_system_alerts_status ON system_alerts(status);
CREATE INDEX IF NOT EXISTS idx_system_alerts_severity ON system_alerts(severity);
CREATE INDEX IF NOT EXISTS idx_system_alerts_timestamp ON system_alerts(timestamp);

-- Skipped payloads indexes
CREATE INDEX IF NOT EXISTS idx_skipped_payloads_timestamp ON skipped_payloads(timestamp);
CREATE INDEX IF NOT EXISTS idx_skipped_payloads_reason ON skipped_payloads(reason);
CREATE INDEX IF NOT EXISTS idx_skipped_payloads_endpoint ON skipped_payloads(endpoint);

-- Weekly rankings indexes
CREATE INDEX IF NOT EXISTS idx_weekly_rankings_user_id ON weekly_rankings(user_id);
CREATE INDEX IF NOT EXISTS idx_weekly_rankings_created_at ON weekly_rankings(created_at);
CREATE INDEX IF NOT EXISTS idx_weekly_rankings_rank ON weekly_rankings(rank);
CREATE INDEX IF NOT EXISTS idx_weekly_rankings_week_of ON weekly_rankings(week_of);

-- Detected anomalies indexes
CREATE INDEX IF NOT EXISTS idx_detected_anomalies_detected_at ON detected_anomalies(detected_at);
CREATE INDEX IF NOT EXISTS idx_detected_anomalies_severity ON detected_anomalies(severity);
CREATE INDEX IF NOT EXISTS idx_detected_anomalies_type ON detected_anomalies(anomaly_type);

-- Migration status indexes
CREATE INDEX IF NOT EXISTS idx_migration_status_name ON migration_status(migration_name);
CREATE INDEX IF NOT EXISTS idx_migration_status_completed ON migration_status(completed);

################################################################
# ROW LEVEL SECURITY (RLS) POLICIES
################################################################

-- Enable RLS on sensitive tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_risk_flags ENABLE ROW LEVEL SECURITY;
ALTER TABLE token_usage_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE generated_memes ENABLE ROW LEVEL SECURITY;

-- Basic RLS policies (customize based on your auth system)
CREATE POLICY "Users can view own data" ON users
    FOR SELECT USING (auth.uid()::text = id);

CREATE POLICY "Users can update own data" ON users
    FOR UPDATE USING (auth.uid()::text = id);

################################################################
# HELPFUL VIEWS FOR ANALYTICS
################################################################

-- User behavior summary view
CREATE OR REPLACE VIEW user_behavior_summary AS
SELECT 
    u.id,
    u.behavior_score,
    u.token_used,
    u.created_at,
    u.last_updated,
    COUNT(urf.id) as total_risk_flags,
    COUNT(gm.id) as total_memes_generated,
    MAX(urf.timestamp) as last_flag_date,
    MAX(gm.timestamp) as last_meme_date
FROM users u
LEFT JOIN user_risk_flags urf ON u.id = urf.user_id
LEFT JOIN generated_memes gm ON u.id = gm.user_id
GROUP BY u.id, u.behavior_score, u.token_used, u.created_at, u.last_updated;

-- System health monitoring view
CREATE OR REPLACE VIEW system_health_summary AS
SELECT 
    DATE(timestamp) as date,
    COUNT(*) as total_jobs,
    COUNT(CASE WHEN status = 'success' THEN 1 END) as successful_jobs,
    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_jobs,
    ROUND(COUNT(CASE WHEN status = 'success' THEN 1 END) * 100.0 / COUNT(*), 2) as success_rate
FROM job_logs
WHERE timestamp >= NOW() - INTERVAL '30 days'
GROUP BY DATE(timestamp)
ORDER BY date DESC;

################################################################
# DATA CLEANUP PROCEDURES
################################################################

-- Function to clean old logs (run periodically)
CREATE OR REPLACE FUNCTION cleanup_old_logs() RETURNS void AS $$
BEGIN
    -- Clean job logs older than 90 days
    DELETE FROM job_logs WHERE timestamp < NOW() - INTERVAL '90 days';
    
    -- Clean skipped payloads older than 30 days
    DELETE FROM skipped_payloads WHERE timestamp < NOW() - INTERVAL '30 days';
    
    -- Clean resolved alerts older than 60 days
    DELETE FROM system_alerts 
    WHERE status = 'resolved' AND resolved_at < NOW() - INTERVAL '60 days';
    
    -- Clean old weekly rankings (keep only last 52 weeks)
    DELETE FROM weekly_rankings 
    WHERE created_at < NOW() - INTERVAL '52 weeks';
    
    RAISE NOTICE 'Old logs cleanup completed';
END;
$$ LANGUAGE plpgsql;

################################################################
# INITIAL DATA SETUP
################################################################

-- Insert default system user for automated processes
INSERT INTO users (id, role, behavior_score, is_anonymous) 
VALUES ('system', 'system', 100, false)
ON CONFLICT (id) DO NOTHING;

-- Insert sample migration status for testing
INSERT INTO migration_status (migration_name, completed, completed_at)
VALUES ('initial_setup', true, NOW())
ON CONFLICT (migration_name) DO NOTHING;

################################################################
# SCHEMA VERSION TRACKING
################################################################

-- Track schema version for future migrations
CREATE TABLE IF NOT EXISTS schema_version (
    version TEXT PRIMARY KEY,
    applied_at TIMESTAMPTZ DEFAULT NOW(),
    description TEXT
);

INSERT INTO schema_version (version, description)
VALUES ('1.1.0', 'Enhanced BSE schema with multi-source payload support and migration checks')
ON CONFLICT (version) DO UPDATE SET 
    applied_at = NOW(),
    description = EXCLUDED.description;

################################################################
# USEFUL COMMENTS FOR MAINTENANCE
################################################################

COMMENT ON TABLE users IS 'Core user data with behavior scoring and token management';
COMMENT ON TABLE user_risk_flags IS 'Risk flags for fraud detection and behavior analysis';
COMMENT ON TABLE generated_memes IS 'Tracking of all generated meme content';
COMMENT ON TABLE job_logs IS 'System job execution logs for monitoring';
COMMENT ON TABLE system_alerts IS 'Operational alerts and system monitoring';
COMMENT ON TABLE weekly_rankings IS 'User ranking system based on behavior scores';
COMMENT ON TABLE detected_anomalies IS 'Automated anomaly detection results';
COMMENT ON TABLE skipped_payloads IS 'Webhook monitoring and error tracking';
COMMENT ON TABLE migration_status IS 'Database migration tracking';

-- End of Schema
################################################################

CREATE TABLE user_api_costs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id TEXT NOT NULL,
    amount DECIMAL(10,4) NOT NULL,
    service TEXT NOT NULL DEFAULT 'openai_dalle',
    model TEXT,
    size TEXT,
    quality TEXT,
    prompt_preview TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_user_api_costs_user_month ON user_api_costs(user_id, created_at);


-- Bot detection logs
CREATE TABLE bot_detections (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    ip_address TEXT NOT NULL,
    user_agent TEXT,
    bot_probability DECIMAL(3,2) DEFAULT 0.0,
    bot_signals TEXT[] DEFAULT '{}',
    rejection_reason TEXT,
    endpoint TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Fake referral detection logs
CREATE TABLE fake_referral_detections (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id TEXT,
    ip_address TEXT NOT NULL,
    fake_signals TEXT[] DEFAULT '{}',
    risk_score INTEGER DEFAULT 0,
    payload JSONB,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Bot detection tests (for the test endpoint)
CREATE TABLE bot_detection_tests (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    ip_address TEXT NOT NULL,
    user_agent TEXT,
    bot_probability DECIMAL(3,2) DEFAULT 0.0,
    bot_signals TEXT[] DEFAULT '{}',
    should_reject BOOLEAN DEFAULT FALSE,
    rejection_reason TEXT,
    test_payload JSONB,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for better performance
CREATE INDEX idx_bot_detections_timestamp ON bot_detections(timestamp);
CREATE INDEX idx_fake_referral_detections_timestamp ON fake_referral_detections(timestamp);
CREATE INDEX idx_bot_detection_tests_timestamp ON bot_detection_tests(timestamp);


-- Create generated_memes table
CREATE TABLE generated_memes (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    image_url TEXT NOT NULL,
    prompt TEXT NOT NULL,
    tone TEXT NOT NULL CHECK (tone IN ('sarcastic', 'witty', 'crypto', 'relatable', 'dark humor')),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add tokens_remaining field to users table if it doesn't exist
ALTER TABLE users ADD COLUMN IF NOT EXISTS tokens_remaining INTEGER DEFAULT 10;

-- Create indexes for better performance
CREATE INDEX idx_generated_memes_user_id ON generated_memes(user_id);
CREATE INDEX idx_generated_memes_timestamp ON generated_memes(timestamp);
CREATE INDEX idx_generated_memes_tone ON generated_memes(tone);

-- Create index for daily generation queries
CREATE INDEX idx_generated_memes_user_date ON generated_memes(user_id, timestamp);


-- Create generated_memes table (NEW)
CREATE TABLE IF NOT EXISTS generated_memes (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    image_url TEXT NOT NULL,
    prompt TEXT NOT NULL,
    tone TEXT NOT NULL CHECK (tone IN ('sarcastic', 'witty', 'crypto', 'relatable', 'dark humor')),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add tokens_remaining field to users table if it doesn't exist
ALTER TABLE users ADD COLUMN IF NOT EXISTS tokens_remaining INTEGER DEFAULT 10;

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_generated_memes_user_id ON generated_memes(user_id);
CREATE INDEX IF NOT EXISTS idx_generated_memes_timestamp ON generated_memes(timestamp);
CREATE INDEX IF NOT EXISTS idx_generated_memes_tone ON generated_memes(tone);
CREATE INDEX IF NOT EXISTS idx_generated_memes_user_date ON generated_memes(user_id, timestamp);

-- FIXED: Composite index for daily generation queries (without partial index predicate)
CREATE INDEX IF NOT EXISTS idx_generated_memes_daily_lookup ON generated_memes(user_id, timestamp DESC);


#############################################
-- System configurations table
CREATE TABLE IF NOT EXISTS system_configs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    config_type VARCHAR(50) NOT NULL,
    config_data JSONB NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_by VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Comprehensive audit logs table
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    audit_id VARCHAR(50) UNIQUE NOT NULL,
    action_type VARCHAR(50) NOT NULL,
    risk_level VARCHAR(20) NOT NULL CHECK (risk_level IN ('HIGH_RISK', 'MEDIUM_RISK', 'LOW_RISK')),
    user_id VARCHAR(255),
    admin_user_id VARCHAR(255),
    details JSONB NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    source_system VARCHAR(50) NOT NULL
);

-- Bot detections table (if not exists)
CREATE TABLE IF NOT EXISTS bot_detections (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id VARCHAR(255),
    ip_address INET,
    user_agent TEXT,
    bot_probability DECIMAL(3,2),
    bot_signals JSONB,
    detection_method VARCHAR(50),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_system_configs_type_active ON system_configs(config_type, is_active);
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_logs_risk_level ON audit_logs(risk_level);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action_type ON audit_logs(action_type);
CREATE INDEX IF NOT EXISTS idx_bot_detections_timestamp ON bot_detections(timestamp);
CREATE INDEX IF NOT EXISTS idx_bot_detections_ip ON bot_detections(ip_address);
