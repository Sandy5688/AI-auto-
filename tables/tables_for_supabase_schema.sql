################################################################
##users_table
create table public.users (
  id text not null,
  behavior_score integer null default 100,
  role text null,
  is_anonymous boolean null default false,
  encrypted_token text null,
  token_used integer null default 0,
  constraint users_pkey primary key (id)
) TABLESPACE pg_default;

##generated_memes
create table public.generated_memes (
  id uuid not null default extensions.uuid_generate_v4 (),
  user_id text not null,
  prompt text not null,
  tone text null,
  image_url text null,
  timestamp timestamp with time zone null default now(),
  token_used integer null,
  used_in_nft boolean null default false,
  constraint generated_memes_pkey primary key (id)
) TABLESPACE pg_default;

##user_risk_flags
create table public.user_risk_flags (
  id uuid not null default extensions.uuid_generate_v4 (),
  user_id text not null,
  flag text not null,
  risk_score integer null,
  anomalies text[] null,
  timestamp timestamp with time zone null default now(),
  constraint user_risk_flags_pkey primary key (id),
  constraint user_risk_flags_user_id_key unique (user_id)
) TABLESPACE pg_default;

##token_usage_history
create table public.token_usage_history (
  id serial not null,
  user_id text null,
  tokens_used integer not null,
  action text not null,
  timestamp timestamp with time zone null default now(),
  constraint token_usage_history_pkey primary key (id),
  constraint token_usage_history_user_id_fkey foreign KEY (user_id) references users (id)
) TABLESPACE pg_default;

##job_logs
create table public.job_logs (
  id uuid not null default extensions.uuid_generate_v4 (),
  job_name text not null,
  status text not null,
  timestamp timestamp with time zone null default now(),
  payload jsonb null,
  error_message text null,
  constraint job_logs_pkey primary key (id)
) TABLESPACE pg_default;

#####################################################
-- Create table for tracking skipped payloads
CREATE TABLE IF NOT EXISTS skipped_payloads (
    id BIGSERIAL PRIMARY KEY,
    payload JSONB,
    reason TEXT NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    endpoint TEXT DEFAULT '/webhook'
);

-- Add index for faster queries
CREATE INDEX IF NOT EXISTS idx_skipped_payloads_timestamp ON skipped_payloads(timestamp);
CREATE INDEX IF NOT EXISTS idx_skipped_payloads_reason ON skipped_payloads(reason);

-- Ensure user_risk_flags table has proper structure
CREATE TABLE IF NOT EXISTS user_risk_flags (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    flag TEXT NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Add composite index to prevent duplicates and speed up queries
CREATE UNIQUE INDEX IF NOT EXISTS idx_user_risk_flags_unique ON user_risk_flags(user_id, flag, timestamp);
CREATE INDEX IF NOT EXISTS idx_user_risk_flags_user_id ON user_risk_flags(user_id);

-- Create migration status tracking table
CREATE TABLE IF NOT EXISTS migration_status (
    id BIGSERIAL PRIMARY KEY,
    migration_name TEXT UNIQUE NOT NULL,
    completed BOOLEAN DEFAULT FALSE,
    completed_at TIMESTAMPTZ,
    migrated_users INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add index for faster lookups
CREATE INDEX IF NOT EXISTS idx_migration_status_name ON migration_status(migration_name);

#############################################################################

-- Enhanced job logs table (if not exists)
CREATE TABLE IF NOT EXISTS job_logs (
    id BIGSERIAL PRIMARY KEY,
    job_name TEXT NOT NULL,
    status TEXT NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    payload JSONB DEFAULT '{}'::jsonb,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0
);

-- System alerts table for failure notifications
CREATE TABLE IF NOT EXISTS system_alerts (
    id BIGSERIAL PRIMARY KEY,
    alert_type TEXT NOT NULL,
    operation TEXT NOT NULL,
    error_message TEXT,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    severity TEXT DEFAULT 'medium',
    status TEXT DEFAULT 'unresolved',
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Weekly rankings table
CREATE TABLE IF NOT EXISTS weekly_rankings (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    rank INTEGER NOT NULL,
    behavior_score INTEGER NOT NULL,
    previous_rank INTEGER,
    rank_change INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Detected anomalies table
CREATE TABLE IF NOT EXISTS detected_anomalies (
    id BIGSERIAL PRIMARY KEY,
    anomaly_type TEXT NOT NULL,
    description TEXT NOT NULL,
    severity TEXT DEFAULT 'medium',
    affected_users TEXT[] DEFAULT '{}',
    detected_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Add indexes for better performance
CREATE INDEX IF NOT EXISTS idx_job_logs_job_name ON job_logs(job_name);
CREATE INDEX IF NOT EXISTS idx_job_logs_timestamp ON job_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_system_alerts_status ON system_alerts(status);
CREATE INDEX IF NOT EXISTS idx_weekly_rankings_user_id ON weekly_rankings(user_id);
CREATE INDEX IF NOT EXISTS idx_weekly_rankings_created_at ON weekly_rankings(created_at);
CREATE INDEX IF NOT EXISTS idx_detected_anomalies_detected_at ON detected_anomalies(detected_at);
