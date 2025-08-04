##############access_logs
create table public.access_logs (
  id bigserial not null,
  user_id text not null,
  access_granted boolean null default false,
  upload_allowed boolean null,
  access_level text null,
  content_type text null,
  content_length integer null,
  event_type text not null,
  timestamp timestamp with time zone null default now(),
  metadata jsonb null default '{}'::jsonb,
  constraint access_logs_pkey primary key (id),
  constraint access_logs_user_id_fkey foreign KEY (user_id) references users (id) on delete CASCADE
) TABLESPACE pg_default;

create index IF not exists idx_access_logs_user_id on public.access_logs using btree (user_id) TABLESPACE pg_default;

create index IF not exists idx_access_logs_timestamp on public.access_logs using btree ("timestamp") TABLESPACE pg_default;

create index IF not exists idx_access_logs_event_type on public.access_logs using btree (event_type) TABLESPACE pg_default;


#####################################

create table public.admin_alerts (
  id bigserial not null,
  alert_type text not null,
  priority text null default 'MEDIUM'::text,
  summary text not null,
  details jsonb null default '{}'::jsonb,
  status text null default 'active'::text,
  assigned_to text null,
  created_at timestamp with time zone null default now(),
  resolved_at timestamp with time zone null,
  constraint admin_alerts_pkey primary key (id)
) TABLESPACE pg_default;

create index IF not exists idx_admin_alerts_status on public.admin_alerts using btree (status) TABLESPACE pg_default;

###################################

create table public.anomaly_analysis_results (
  id bigserial not null,
  analysis_timestamp timestamp with time zone null default now(),
  total_flags integer null default 0,
  flag_types jsonb null default '{}'::jsonb,
  severity_distribution jsonb null default '{}'::jsonb,
  high_risk_users_count integer null default 0,
  analysis_type text not null,
  constraint anomaly_analysis_results_pkey primary key (id)
) TABLESPACE pg_default;

##############################################

create table public.audit_logs (
  id uuid not null default gen_random_uuid (),
  audit_id character varying(50) not null,
  action_type character varying(50) not null,
  risk_level character varying(20) not null,
  user_id character varying(255) null,
  admin_user_id character varying(255) null,
  details jsonb not null,
  timestamp timestamp with time zone not null,
  source_system character varying(50) not null,
  constraint audit_logs_pkey primary key (id),
  constraint audit_logs_audit_id_key unique (audit_id),
  constraint audit_logs_risk_level_check check (
    (
      (risk_level)::text = any (
        (
          array[
            'HIGH_RISK'::character varying,
            'MEDIUM_RISK'::character varying,
            'LOW_RISK'::character varying
          ]
        )::text[]
      )
    )
  )
) TABLESPACE pg_default;

create index IF not exists idx_audit_logs_timestamp on public.audit_logs using btree ("timestamp") TABLESPACE pg_default;

create index IF not exists idx_audit_logs_risk_level on public.audit_logs using btree (risk_level) TABLESPACE pg_default;

create index IF not exists idx_audit_logs_user_id on public.audit_logs using btree (user_id) TABLESPACE pg_default;

create index IF not exists idx_audit_logs_action_type on public.audit_logs using btree (action_type) TABLESPACE pg_default;

##############################################

create table public.bot_detection_tests (
  id uuid not null default gen_random_uuid (),
  ip_address text not null,
  user_agent text null,
  bot_probability numeric(3, 2) null default 0.0,
  bot_signals text[] null default '{}'::text[],
  should_reject boolean null default false,
  rejection_reason text null,
  test_payload jsonb null,
  timestamp timestamp with time zone null default now(),
  constraint bot_detection_tests_pkey primary key (id)
) TABLESPACE pg_default;

create index IF not exists idx_bot_detection_tests_timestamp on public.bot_detection_tests using btree ("timestamp") TABLESPACE pg_default;

###############################################################

create table public.bot_detections (
  id uuid not null default gen_random_uuid (),
  ip_address text not null,
  user_agent text null,
  bot_probability numeric(3, 2) null default 0.0,
  bot_signals text[] null default '{}'::text[],
  rejection_reason text null,
  endpoint text null,
  timestamp timestamp with time zone null default now(),
  constraint bot_detections_pkey primary key (id)
) TABLESPACE pg_default;

create index IF not exists idx_bot_detections_timestamp on public.bot_detections using btree ("timestamp") TABLESPACE pg_default;

create index IF not exists idx_bot_detections_ip on public.bot_detections using btree (ip_address) TABLESPACE pg_default;

###############################################################

create table public.detected_anomalies (
  id bigserial not null,
  anomaly_type text not null,
  description text not null,
  severity text null default 'medium'::text,
  affected_users text[] null default '{}'::text[],
  detected_at timestamp with time zone null default now(),
  metadata jsonb null default '{}'::jsonb,
  resolved boolean null default false,
  resolved_at timestamp with time zone null,
  pattern_name text null,
  fingerprint_data jsonb null default '{}'::jsonb,
  risk_score integer null default 0,
  status text null default 'active'::text,
  constraint detected_anomalies_pkey primary key (id)
) TABLESPACE pg_default;

create index IF not exists idx_anomalies_pattern_name on public.detected_anomalies using btree (pattern_name) TABLESPACE pg_default;

create index IF not exists idx_anomalies_risk_score on public.detected_anomalies using btree (risk_score) TABLESPACE pg_default;

create index IF not exists idx_anomalies_status on public.detected_anomalies using btree (status) TABLESPACE pg_default;

###############################################################

create table public.fake_referral_detections (
  id uuid not null default gen_random_uuid (),
  user_id text null,
  ip_address text not null,
  fake_signals text[] null default '{}'::text[],
  risk_score integer null default 0,
  payload jsonb null,
  timestamp timestamp with time zone null default now(),
  constraint fake_referral_detections_pkey primary key (id)
) TABLESPACE pg_default;

create index IF not exists idx_fake_referral_detections_timestamp on public.fake_referral_detections using btree ("timestamp") TABLESPACE pg_default;


###############################################################


create table public.fingerprint_data (
  id bigserial not null,
  user_id text not null,
  event_type text not null,
  ip_address inet not null,
  user_agent text null,
  device_hash text not null,
  timestamp timestamp with time zone null default now(),
  confidence_score numeric(3, 2) null default 0.80,
  geolocation jsonb null default '{}'::jsonb,
  browser_details jsonb null default '{}'::jsonb,
  canvas_fingerprint text null,
  webgl_fingerprint text null,
  screen_resolution text null,
  timezone text null,
  language text null,
  visitor_id text null,
  created_at timestamp with time zone null default now(),
  constraint fingerprint_data_pkey primary key (id),
  constraint fingerprint_data_user_id_fkey foreign KEY (user_id) references users (id) on delete CASCADE
) TABLESPACE pg_default;

create index IF not exists idx_fingerprint_user_id on public.fingerprint_data using btree (user_id) TABLESPACE pg_default;

create index IF not exists idx_fingerprint_timestamp on public.fingerprint_data using btree ("timestamp") TABLESPACE pg_default;

create index IF not exists idx_fingerprint_event_type on public.fingerprint_data using btree (event_type) TABLESPACE pg_default;

create index IF not exists idx_fingerprint_ip_address on public.fingerprint_data using btree (ip_address) TABLESPACE pg_default;

create index IF not exists idx_fingerprint_device_hash on public.fingerprint_data using btree (device_hash) TABLESPACE pg_default;


###############################################################


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

create index IF not exists idx_generated_memes_user_id on public.generated_memes using btree (user_id) TABLESPACE pg_default;

create index IF not exists idx_generated_memes_timestamp on public.generated_memes using btree ("timestamp") TABLESPACE pg_default;

create index IF not exists idx_generated_memes_tone on public.generated_memes using btree (tone) TABLESPACE pg_default;

create index IF not exists idx_generated_memes_user_date on public.generated_memes using btree (user_id, "timestamp") TABLESPACE pg_default;

create index IF not exists idx_generated_memes_daily_lookup on public.generated_memes using btree (user_id, "timestamp" desc) TABLESPACE pg_default;


###############################################################

create table public.job_logs (
  id uuid not null default extensions.uuid_generate_v4 (),
  job_name text not null,
  status text not null,
  timestamp timestamp with time zone null default now(),
  payload jsonb null,
  error_message text null,
  constraint job_logs_pkey primary key (id)
) TABLESPACE pg_default;


###############################################################


create table public.leaderboard (
  id bigserial not null,
  user_id text not null,
  position integer not null,
  behavior_score integer not null,
  previous_position integer null,
  position_change integer null default 0,
  created_at timestamp with time zone null default now(),
  constraint leaderboard_pkey primary key (id),
  constraint leaderboard_user_id_fkey foreign KEY (user_id) references users (id) on delete CASCADE
) TABLESPACE pg_default;

create index IF not exists idx_leaderboard_position on public.leaderboard using btree ("position") TABLESPACE pg_default;


###############################################################


create table public.logs_scheduled_jobs (
  id bigserial not null,
  job_name text not null,
  timestamp timestamp with time zone null default now(),
  status text not null,
  error_if_any text null,
  metadata jsonb null default '{}'::jsonb,
  constraint logs_scheduled_jobs_pkey primary key (id)
) TABLESPACE pg_default;

create index IF not exists idx_logs_scheduled_jobs_job_name on public.logs_scheduled_jobs using btree (job_name) TABLESPACE pg_default;

create index IF not exists idx_logs_scheduled_jobs_timestamp on public.logs_scheduled_jobs using btree ("timestamp") TABLESPACE pg_default;


###############################################################


create table public.maf_statistics (
  id bigserial not null,
  date date null default CURRENT_DATE,
  total_events_processed integer null default 0,
  green_flags integer null default 0,
  yellow_flags integer null default 0,
  red_flags integer null default 0,
  anomalies_detected integer null default 0,
  false_positives integer null default 0,
  processing_time_avg_ms integer null default 0,
  updated_at timestamp with time zone null default now(),
  constraint maf_statistics_pkey primary key (id)
) TABLESPACE pg_default;


###############################################################

create table public.system_configs (
  id uuid not null default gen_random_uuid (),
  config_type character varying(50) not null,
  config_data jsonb not null,
  is_active boolean null default true,
  created_by character varying(255) not null,
  created_at timestamp with time zone null default now(),
  constraint system_configs_pkey primary key (id)
) TABLESPACE pg_default;

create index IF not exists idx_system_configs_type_active on public.system_configs using btree (config_type, is_active) TABLESPACE pg_default;


###############################################################


create table public.token_usage_history (
  id serial not null,
  user_id text null,
  tokens_used integer not null,
  action text not null,
  timestamp timestamp with time zone null default now(),
  constraint token_usage_history_pkey primary key (id),
  constraint token_usage_history_user_id_fkey foreign KEY (user_id) references users (id)
) TABLESPACE pg_default;


###############################################################

create table public.user_api_costs (
  id uuid not null default gen_random_uuid (),
  user_id text not null,
  amount numeric(10, 4) not null,
  service text not null default 'openai_dalle'::text,
  model text null,
  size text null,
  quality text null,
  prompt_preview text null,
  created_at timestamp with time zone null default now(),
  constraint user_api_costs_pkey primary key (id)
) TABLESPACE pg_default;

create index IF not exists idx_user_api_costs_user_month on public.user_api_costs using btree (user_id, created_at) TABLESPACE pg_default;


###############################################################

create table public.user_flag_history (
  id bigserial not null,
  user_id text not null,
  flag_color text not null,
  behavior_score integer null,
  anomaly_count integer null default 0,
  velocity_score text null,
  fingerprint_id text null,
  confidence_score numeric(3, 2) null,
  geolocation jsonb null default '{}'::jsonb,
  created_at timestamp with time zone null default now(),
  processed_by text null default 'MAF'::text,
  constraint user_flag_history_pkey primary key (id),
  constraint flag_history_user_id_fkey foreign KEY (user_id) references users (id) on delete CASCADE,
  constraint user_flag_history_flag_color_check check (
    (
      flag_color = any (array['GREEN'::text, 'YELLOW'::text, 'RED'::text])
    )
  ),
  constraint user_flag_history_velocity_score_check check (
    (
      velocity_score = any (array['low'::text, 'medium'::text, 'high'::text])
    )
  )
) TABLESPACE pg_default;

create index IF not exists idx_flag_history_user_id on public.user_flag_history using btree (user_id) TABLESPACE pg_default;

create index IF not exists idx_flag_history_flag_color on public.user_flag_history using btree (flag_color) TABLESPACE pg_default;

create index IF not exists idx_flag_history_created_at on public.user_flag_history using btree (created_at) TABLESPACE pg_default;


###############################################################

create table public.user_risk_flags (
  id uuid not null default extensions.uuid_generate_v4 (),
  user_id text not null,
  flag text not null,
  risk_score integer null,
  anomalies text[] null,
  timestamp timestamp with time zone null default now(),
  metadata jsonb null default '{}'::jsonb,
  constraint user_risk_flags_pkey primary key (id),
  constraint user_risk_flags_user_id_key unique (user_id)
) TABLESPACE pg_default;


###############################################################


create table public.users (
  id text not null,
  behavior_score integer null default 100,
  role text null,
  is_anonymous boolean null default false,
  encrypted_token text null,
  token_used integer null default 0,
  last_updated timestamp with time zone null default now(),
  user_metadata jsonb null default '{}'::jsonb,
  weekly_score integer null default 0,
  is_verified boolean null default false,
  created_at timestamp with time zone null default now(),
  tokens_remaining integer null default 10,
  constraint users_pkey primary key (id)
) TABLESPACE pg_default;

create index IF not exists idx_users_last_updated on public.users using btree (last_updated) TABLESPACE pg_default;


###############################################################

create table public.weekly_challenges (
  id text not null,
  type text not null,
  description text not null,
  reward_points integer null default 0,
  start_date timestamp with time zone null default now(),
  end_date timestamp with time zone null,
  active boolean null default true,
  created_at timestamp with time zone null default now(),
  constraint weekly_challenges_pkey primary key (id)
) TABLESPACE pg_default;

create index IF not exists idx_weekly_challenges_active on public.weekly_challenges using btree (active) TABLESPACE pg_default;


###############################################################

create table public.weekly_leaderboard_archive (
  id bigserial not null,
  week_year integer not null,
  week_number integer not null,
  archived_at timestamp with time zone null default now(),
  archived_data text null,
  constraint weekly_leaderboard_archive_pkey primary key (id)
) TABLESPACE pg_default;