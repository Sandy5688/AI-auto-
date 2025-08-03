-- Access logs table for AGK
CREATE TABLE IF NOT EXISTS public.access_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    access_granted BOOLEAN DEFAULT false,
    upload_allowed BOOLEAN DEFAULT NULL,
    access_level TEXT,
    content_type TEXT,
    content_length INTEGER,
    event_type TEXT NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb,
    CONSTRAINT access_logs_user_id_fkey FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

-- Add user_metadata column to users table if not exists
ALTER TABLE users ADD COLUMN IF NOT EXISTS user_metadata JSONB DEFAULT '{}'::jsonb;

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_access_logs_user_id ON access_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_access_logs_timestamp ON access_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_access_logs_event_type ON access_logs(event_type);
