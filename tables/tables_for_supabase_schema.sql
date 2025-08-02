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