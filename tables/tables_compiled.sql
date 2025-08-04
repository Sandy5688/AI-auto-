####1 Users Table

-- Core user management with behavior scoring
CREATE TABLE public.users (
    id TEXT NOT NULL,
    behavior_score INTEGER DEFAULT 100,
    role TEXT,
    is_anonymous BOOLEAN DEFAULT false,
    encrypted_token TEXT,
    token_used INTEGER DEFAULT 0,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    user_metadata JSONB DEFAULT '{}'::jsonb,
    weekly_score INTEGER DEFAULT 0,
    is_verified BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    tokens_remaining INTEGER DEFAULT 10,
    CONSTRAINT users_pkey PRIMARY KEY (id)
);

CREATE INDEX idx_users_last_updated ON public.users USING btree (last_updated);

#### **2. User Risk Flags**

-- Risk flags assigned to users by BSE system
CREATE TABLE public.user_risk_flags (
    id UUID NOT NULL DEFAULT extensions.uuid_generate_v4(),
    user_id TEXT NOT NULL,
    flag TEXT NOT NULL,
    risk_score INTEGER,
    anomalies TEXT[],
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb,
    CONSTRAINT user_risk_flags_pkey PRIMARY KEY (id),
    CONSTRAINT user_risk_flags_user_id_key UNIQUE (user_id)
);
```

### **🤖 Bot Detection & Security Tables**

#### **3. Bot Detections**
```sql
-- Production bot detection logs
CREATE TABLE public.bot_detections (
    id UUID NOT NULL DEFAULT gen_random_uuid(),
    ip_address TEXT NOT NULL,
    user_agent TEXT,
    bot_probability NUMERIC(3,2) DEFAULT 0.0,
    bot_signals TEXT[] DEFAULT '{}'::text[],
    rejection_reason TEXT,
    endpoint TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT bot_detections_pkey PRIMARY KEY (id)
);

CREATE INDEX idx_bot_detections_timestamp ON public.bot_detections USING btree (timestamp);
CREATE INDEX idx_bot_detections_ip ON public.bot_detections USING btree (ip_address);
```

#### **4. Bot Detection Tests**
```sql
-- Testing environment for bot detection
CREATE TABLE public.bot_detection_tests (
    id UUID NOT NULL DEFAULT gen_random_uuid(),
    ip_address TEXT NOT NULL,
    user_agent TEXT,
    bot_probability NUMERIC(3,2) DEFAULT 0.0,
    bot_signals TEXT[] DEFAULT '{}'::text[],
    should_reject BOOLEAN DEFAULT false,
    rejection_reason TEXT,
    test_payload JSONB,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT bot_detection_tests_pkey PRIMARY KEY (id)
);

CREATE INDEX idx_bot_detection_tests_timestamp ON public.bot_detection_tests USING btree (timestamp);
```

#### **5. Fake Referral Detections**
```sql
-- Fake referral detection logs
CREATE TABLE public.fake_referral_detections (
    id UUID NOT NULL DEFAULT gen_random_uuid(),
    user_id TEXT,
    ip_address TEXT NOT NULL,
    fake_signals TEXT[] DEFAULT '{}'::text[],
    risk_score INTEGER DEFAULT 0,
    payload JSONB,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT fake_referral_detections_pkey PRIMARY KEY (id)
);

CREATE INDEX idx_fake_referral_detections_timestamp ON public.fake_referral_detections USING btree (timestamp);
```

#### **6. Fingerprint Data**
```sql
-- Device fingerprinting data for MAF
CREATE TABLE public.fingerprint_data (
    id BIGSERIAL NOT NULL,
    user_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    ip_address INET NOT NULL,
    user_agent TEXT,
    device_hash TEXT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    confidence_score NUMERIC(3,2) DEFAULT 0.80,
    geolocation JSONB DEFAULT '{}'::jsonb,
    browser_details JSONB DEFAULT '{}'::jsonb,
    canvas_fingerprint TEXT,
    webgl_fingerprint TEXT,
    screen_resolution TEXT,
    timezone TEXT,
    language TEXT,
    visitor_id TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT fingerprint_data_pkey PRIMARY KEY (id),
    CONSTRAINT fingerprint_data_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX idx_fingerprint_user_id ON public.fingerprint_data USING btree (user_id);
CREATE INDEX idx_fingerprint_timestamp ON public.fingerprint_data USING btree (timestamp);
CREATE INDEX idx_fingerprint_event_type ON public.fingerprint_data USING btree (event_type);
CREATE INDEX idx_fingerprint_ip_address ON public.fingerprint_data USING btree (ip_address);
CREATE INDEX idx_fingerprint_device_hash ON public.fingerprint_data USING btree (device_hash);
```

### **🎨 Meme Generation Tables**

#### **7. Generated Memes**
```sql
-- Meme generation tracking with tone support
CREATE TABLE public.generated_memes (
    id UUID NOT NULL DEFAULT extensions.uuid_generate_v4(),
    user_id TEXT NOT NULL,
    prompt TEXT NOT NULL,
    tone TEXT,
    image_url TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    token_used INTEGER,
    used_in_nft BOOLEAN DEFAULT false,
    CONSTRAINT generated_memes_pkey PRIMARY KEY (id)
);

CREATE INDEX idx_generated_memes_user_id ON public.generated_memes USING btree (user_id);
CREATE INDEX idx_generated_memes_timestamp ON public.generated_memes USING btree (timestamp);
CREATE INDEX idx_generated_memes_tone ON public.generated_memes USING btree (tone);
CREATE INDEX idx_generated_memes_user_date ON public.generated_memes USING btree (user_id, timestamp);
CREATE INDEX idx_generated_memes_daily_lookup ON public.generated_memes USING btree (user_id, timestamp DESC);
```

#### **8. User API Costs**
```sql
-- Track OpenAI API costs per user
CREATE TABLE public.user_api_costs (
    id UUID NOT NULL DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    amount NUMERIC(10,4) NOT NULL,
    service TEXT NOT NULL DEFAULT 'openai_dalle',
    model TEXT,
    size TEXT,
    quality TEXT,
    prompt_preview TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT user_api_costs_pkey PRIMARY KEY (id)
);

CREATE INDEX idx_user_api_costs_user_month ON public.user_api_costs USING btree (user_id, created_at);
```

### **📊 Analytics & Monitoring Tables**

#### **9. Access Logs**
```sql
-- API access logging for AGK
CREATE TABLE public.access_logs (
    id BIGSERIAL NOT NULL,
    user_id TEXT NOT NULL,
    access_granted BOOLEAN DEFAULT false,
    upload_allowed BOOLEAN,
    access_level TEXT,
    content_type TEXT,
    content_length INTEGER,
    event_type TEXT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb,
    CONSTRAINT access_logs_pkey PRIMARY KEY (id),
    CONSTRAINT access_logs_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX idx_access_logs_user_id ON public.access_logs USING btree (user_id);
CREATE INDEX idx_access_logs_timestamp ON public.access_logs USING btree (timestamp);
CREATE INDEX idx_access_logs_event_type ON public.access_logs USING btree (event_type);
```

#### **10. User Flag History**
```sql
-- Historical tracking of user flags for MAF
CREATE TABLE public.user_flag_history (
    id BIGSERIAL NOT NULL,
    user_id TEXT NOT NULL,
    flag_color TEXT NOT NULL,
    behavior_score INTEGER,
    anomaly_count INTEGER DEFAULT 0,
    velocity_score TEXT,
    fingerprint_id TEXT,
    confidence_score NUMERIC(3,2),
    geolocation JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processed_by TEXT DEFAULT 'MAF',
    CONSTRAINT user_flag_history_pkey PRIMARY KEY (id),
    CONSTRAINT flag_history_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT user_flag_history_flag_color_check CHECK (flag_color = ANY (ARRAY['GREEN', 'YELLOW', 'RED'])),
    CONSTRAINT user_flag_history_velocity_score_check CHECK (velocity_score = ANY (ARRAY['low', 'medium', 'high']))
);

CREATE INDEX idx_flag_history_user_id ON public.user_flag_history USING btree (user_id);
CREATE INDEX idx_flag_history_flag_color ON public.user_flag_history USING btree (flag_color);
CREATE INDEX idx_flag_history_created_at ON public.user_flag_history USING btree (created_at);
```

#### **11. Detected Anomalies**
```sql
-- Anomaly detection results for SOL
CREATE TABLE public.detected_anomalies (
    id BIGSERIAL NOT NULL,
    anomaly_type TEXT NOT NULL,
    description TEXT NOT NULL,
    severity TEXT DEFAULT 'medium',
    affected_users TEXT[] DEFAULT '{}'::text[],
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb,
    resolved BOOLEAN DEFAULT false,
    resolved_at TIMESTAMP WITH TIME ZONE,
    pattern_name TEXT,
    fingerprint_data JSONB DEFAULT '{}'::jsonb,
    risk_score INTEGER DEFAULT 0,
    status TEXT DEFAULT 'active',
    CONSTRAINT detected_anomalies_pkey PRIMARY KEY (id)
);

CREATE INDEX idx_anomalies_pattern_name ON public.detected_anomalies USING btree (pattern_name);
CREATE INDEX idx_anomalies_risk_score ON public.detected_anomalies USING btree (risk_score);
CREATE INDEX idx_anomalies_status ON public.detected_anomalies USING btree (status);
```

### **🏆 Leaderboard Tables**

#### **12. Leaderboard**
```sql
-- Real-time user rankings
CREATE TABLE public.leaderboard (
    id BIGSERIAL NOT NULL,
    user_id TEXT NOT NULL,
    position INTEGER NOT NULL,
    behavior_score INTEGER NOT NULL,
    previous_position INTEGER,
    position_change INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT leaderboard_pkey PRIMARY KEY (id),
    CONSTRAINT leaderboard_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX idx_leaderboard_position ON public.leaderboard USING btree (position);
```

#### **13. Weekly Leaderboard Archive**
```sql
-- Weekly leaderboard snapshots
CREATE TABLE public.weekly_leaderboard_archive (
    id BIGSERIAL NOT NULL,
    week_year INTEGER NOT NULL,
    week_number INTEGER NOT NULL,
    archived_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    archived_data TEXT,
    CONSTRAINT weekly_leaderboard_archive_pkey PRIMARY KEY (id)
);
```

#### **14. Weekly Challenges**
```sql
-- Weekly challenges for users
CREATE TABLE public.weekly_challenges (
    id TEXT NOT NULL,
    type TEXT NOT NULL,
    description TEXT NOT NULL,
    reward_points INTEGER DEFAULT 0,
    start_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    end_date TIMESTAMP WITH TIME ZONE,
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT weekly_challenges_pkey PRIMARY KEY (id)
);

CREATE INDEX idx_weekly_challenges_active ON public.weekly_challenges USING btree (active);
```

### **⚙️ System Management Tables**

#### **15. System Configs**
```sql
-- Dynamic system configuration for modular management
CREATE TABLE public.system_configs (
    id UUID NOT NULL DEFAULT gen_random_uuid(),
    config_type VARCHAR(50) NOT NULL,
    config_data JSONB NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_by VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT system_configs_pkey PRIMARY KEY (id)
);

CREATE INDEX idx_system_configs_type_active ON public.system_configs USING btree (config_type, is_active);
```

#### **16. Audit Logs**
```sql
-- Comprehensive audit logging for compliance
CREATE TABLE public.audit_logs (
    id UUID NOT NULL DEFAULT gen_random_uuid(),
    audit_id VARCHAR(50) NOT NULL,
    action_type VARCHAR(50) NOT NULL,
    risk_level VARCHAR(20) NOT NULL,
    user_id VARCHAR(255),
    admin_user_id VARCHAR(255),
    details JSONB NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    source_system VARCHAR(50) NOT NULL,
    CONSTRAINT audit_logs_pkey PRIMARY KEY (id),
    CONSTRAINT audit_logs_audit_id_key UNIQUE (audit_id),
    CONSTRAINT audit_logs_risk_level_check CHECK (risk_level IN ('HIGH_RISK', 'MEDIUM_RISK', 'LOW_RISK'))
);

CREATE INDEX idx_audit_logs_timestamp ON public.audit_logs USING btree (timestamp);
CREATE INDEX idx_audit_logs_risk_level ON public.audit_logs USING btree (risk_level);
CREATE INDEX idx_audit_logs_user_id ON public.audit_logs USING btree (user_id);
CREATE INDEX idx_audit_logs_action_type ON public.audit_logs USING btree (action_type);
```

#### **17. Token Usage History**
```sql
-- Track token consumption across all features
CREATE TABLE public.token_usage_history (
    id SERIAL NOT NULL,
    user_id TEXT,
    tokens_used INTEGER NOT NULL,
    action TEXT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT token_usage_history_pkey PRIMARY KEY (id),
    CONSTRAINT token_usage_history_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id)
);
```

### **🔧 System Administration Tables**

#### **18. Job Logs**
```sql
-- Background job execution tracking
CREATE TABLE public.job_logs (
    id UUID NOT NULL DEFAULT extensions.uuid_generate_v4(),
    job_name TEXT NOT NULL,
    status TEXT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    payload JSONB,
    error_message TEXT,
    CONSTRAINT job_logs_pkey PRIMARY KEY (id)
);
```

#### **19. Scheduled Jobs Logs**
```sql
-- Scheduled job monitoring
CREATE TABLE public.logs_scheduled_jobs (
    id BIGSERIAL NOT NULL,
    job_name TEXT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    status TEXT NOT NULL,
    error_if_any TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    CONSTRAINT logs_scheduled_jobs_pkey PRIMARY KEY (id)
);

CREATE INDEX idx_logs_scheduled_jobs_job_name ON public.logs_scheduled_jobs USING btree (job_name);
CREATE INDEX idx_logs_scheduled_jobs_timestamp ON public.logs_scheduled_jobs USING btree (timestamp);
```

#### **20. Admin Alerts**
```sql
-- Administrative alerts and notifications
CREATE TABLE public.admin_alerts (
    id BIGSERIAL NOT NULL,
    alert_type TEXT NOT NULL,
    priority TEXT DEFAULT 'MEDIUM',
    summary TEXT NOT NULL,
    details JSONB DEFAULT '{}'::jsonb,
    status TEXT DEFAULT 'active',
    assigned_to TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    resolved_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT admin_alerts_pkey PRIMARY KEY (id)
);

CREATE INDEX idx_admin_alerts_status ON public.admin_alerts USING btree (status);
```

#### **21. MAF Statistics**
```sql
-- Multi-Account Filter performance statistics
CREATE TABLE public.maf_statistics (
    id BIGSERIAL NOT NULL,
    date DATE DEFAULT CURRENT_DATE,
    total_events_processed INTEGER DEFAULT 0,
    green_flags INTEGER DEFAULT 0,
    yellow_flags INTEGER DEFAULT 0,
    red_flags INTEGER DEFAULT 0,
    anomalies_detected INTEGER DEFAULT 0,
    false_positives INTEGER DEFAULT 0,
    processing_time_avg_ms INTEGER DEFAULT 0,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT maf_statistics_pkey PRIMARY KEY (id)
);
```

#### **22. Anomaly Analysis Results**
```sql
-- Analysis results from anomaly detection
CREATE TABLE public.anomaly_analysis_results (
    id BIGSERIAL NOT NULL,
    analysis_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    total_flags INTEGER DEFAULT 0,
    flag_types JSONB DEFAULT '{}'::jsonb,
    severity_distribution JSONB DEFAULT '{}'::jsonb,
    high_risk_users_count INTEGER DEFAULT 0,
    analysis_type TEXT NOT NULL,
    CONSTRAINT anomaly_analysis_results_pkey PRIMARY KEY (id)
);
```