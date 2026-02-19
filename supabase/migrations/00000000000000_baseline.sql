-- =============================================================
-- BASELINE MIGRATION
-- Generated from production schema dump (2026-02-18)
-- 
-- Structure: ENUMS -> TABLES -> FUNCTIONS -> CONSTRAINTS/INDEXES/TRIGGERS/POLICIES
-- Tables: 31, Enums: 7, Functions: 40
-- =============================================================


-- ===================== ENUMS =====================


CREATE TYPE "public"."generation_status" AS ENUM (
    'in_progress',
    'user_input_required',
    'paused',
    'completed',
    'error',
    'cancelled',
    'resuming',
    'auto_progressing'
);


CREATE TYPE "public"."invitation_status" AS ENUM (
    'pending',
    'accepted',
    'declined',
    'expired'
);


CREATE TYPE "public"."organization_role" AS ENUM (
    'owner',
    'admin',
    'member'
);


CREATE TYPE "public"."step_type" AS ENUM (
    'keyword_analysis',
    'persona_generation',
    'theme_proposal',
    'research_planning',
    'research_execution',
    'research_synthesis',
    'outline_generation',
    'section_writing',
    'editing',
    'custom'
);


CREATE TYPE "public"."style_template_type" AS ENUM (
    'writing_tone',
    'vocabulary',
    'structure',
    'branding',
    'seo_focus',
    'custom'
);


CREATE TYPE "public"."subscription_status" AS ENUM (
    'trialing',
    'active',
    'canceled',
    'incomplete',
    'incomplete_expired',
    'past_due',
    'unpaid',
    'paused'
);


CREATE TYPE "public"."user_subscription_status" AS ENUM (
    'active',
    'past_due',
    'canceled',
    'expired',
    'none'
);


-- ===================== TABLES =====================


CREATE TABLE IF NOT EXISTS "public"."user_subscriptions" (
    "user_id" "text" NOT NULL,
    "stripe_customer_id" "text",
    "stripe_subscription_id" "text",
    "status" "public"."user_subscription_status" DEFAULT 'none'::"public"."user_subscription_status" NOT NULL,
    "current_period_end" timestamp with time zone,
    "cancel_at_period_end" boolean DEFAULT false,
    "is_privileged" boolean DEFAULT false,
    "email" "text",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"(),
    "upgraded_to_org_id" "uuid",
    "plan_tier_id" "text" DEFAULT 'default'::"text",
    "addon_quantity" integer DEFAULT 0 NOT NULL
);


CREATE TABLE IF NOT EXISTS "public"."agent_execution_logs" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "session_id" "uuid" NOT NULL,
    "agent_name" "text" NOT NULL,
    "agent_type" "text" NOT NULL,
    "step_number" integer NOT NULL,
    "sub_step_number" integer DEFAULT 1,
    "status" "text" DEFAULT 'started'::"text" NOT NULL,
    "input_data" "jsonb" DEFAULT '{}'::"jsonb",
    "output_data" "jsonb" DEFAULT '{}'::"jsonb",
    "llm_model" "text",
    "llm_provider" "text" DEFAULT 'openai'::"text",
    "input_tokens" integer DEFAULT 0,
    "output_tokens" integer DEFAULT 0,
    "cache_tokens" integer DEFAULT 0,
    "reasoning_tokens" integer DEFAULT 0,
    "started_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "completed_at" timestamp with time zone,
    "duration_ms" integer,
    "error_message" "text",
    "error_details" "jsonb" DEFAULT '{}'::"jsonb",
    "execution_metadata" "jsonb" DEFAULT '{}'::"jsonb",
    CONSTRAINT "agent_execution_logs_status_check" CHECK (("status" = ANY (ARRAY['started'::"text", 'running'::"text", 'completed'::"text", 'failed'::"text", 'timeout'::"text"]))),
    CONSTRAINT "valid_duration" CHECK (("duration_ms" >= 0)),
    CONSTRAINT "valid_tokens" CHECK ((("input_tokens" >= 0) AND ("output_tokens" >= 0) AND ("cache_tokens" >= 0) AND ("reasoning_tokens" >= 0)))
);


CREATE TABLE IF NOT EXISTS "public"."agent_log_sessions" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "article_uuid" "uuid" NOT NULL,
    "user_id" "text" NOT NULL,
    "organization_id" "uuid",
    "initial_input" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "seo_keywords" "text"[],
    "image_mode_enabled" boolean DEFAULT false,
    "article_style_info" "jsonb" DEFAULT '{}'::"jsonb",
    "generation_theme_count" integer DEFAULT 1,
    "target_age_group" "text",
    "persona_settings" "jsonb" DEFAULT '{}'::"jsonb",
    "company_info" "jsonb" DEFAULT '{}'::"jsonb",
    "status" "text" DEFAULT 'started'::"text" NOT NULL,
    "total_steps" integer DEFAULT 0,
    "completed_steps" integer DEFAULT 0,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "completed_at" timestamp with time zone,
    "session_metadata" "jsonb" DEFAULT '{}'::"jsonb",
    CONSTRAINT "agent_log_sessions_status_check" CHECK (("status" = ANY (ARRAY['started'::"text", 'in_progress'::"text", 'completed'::"text", 'failed'::"text", 'cancelled'::"text"]))),
    CONSTRAINT "valid_step_counts" CHECK (("completed_steps" <= "total_steps"))
);


CREATE TABLE IF NOT EXISTS "public"."llm_call_logs" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "execution_id" "uuid" NOT NULL,
    "call_sequence" integer DEFAULT 1 NOT NULL,
    "api_type" "text" DEFAULT 'chat_completions'::"text" NOT NULL,
    "model_name" "text" NOT NULL,
    "provider" "text" DEFAULT 'openai'::"text" NOT NULL,
    "system_prompt" "text",
    "user_prompt" "text",
    "full_prompt_data" "jsonb" DEFAULT '{}'::"jsonb",
    "response_content" "text",
    "response_data" "jsonb" DEFAULT '{}'::"jsonb",
    "prompt_tokens" integer DEFAULT 0,
    "completion_tokens" integer DEFAULT 0,
    "total_tokens" integer DEFAULT 0,
    "cached_tokens" integer DEFAULT 0,
    "reasoning_tokens" integer DEFAULT 0,
    "response_time_ms" integer,
    "estimated_cost_usd" numeric(10,6),
    "http_status_code" integer,
    "api_response_id" "text",
    "called_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "error_type" "text",
    "error_message" "text",
    "retry_count" integer DEFAULT 0,
    CONSTRAINT "valid_cost" CHECK (("estimated_cost_usd" >= (0)::numeric)),
    CONSTRAINT "valid_tokens_llm" CHECK ((("prompt_tokens" >= 0) AND ("completion_tokens" >= 0) AND ("total_tokens" >= 0) AND ("cached_tokens" >= 0) AND ("reasoning_tokens" >= 0)))
);


CREATE TABLE IF NOT EXISTS "public"."tool_call_logs" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "execution_id" "uuid" NOT NULL,
    "tool_name" "text" NOT NULL,
    "tool_function" "text" NOT NULL,
    "call_sequence" integer DEFAULT 1 NOT NULL,
    "input_parameters" "jsonb" DEFAULT '{}'::"jsonb",
    "output_data" "jsonb" DEFAULT '{}'::"jsonb",
    "status" "text" DEFAULT 'started'::"text" NOT NULL,
    "execution_time_ms" integer,
    "data_size_bytes" integer,
    "api_calls_count" integer DEFAULT 1,
    "error_type" "text",
    "error_message" "text",
    "retry_count" integer DEFAULT 0,
    "called_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "completed_at" timestamp with time zone,
    "tool_metadata" "jsonb" DEFAULT '{}'::"jsonb",
    CONSTRAINT "tool_call_logs_status_check" CHECK (("status" = ANY (ARRAY['started'::"text", 'completed'::"text", 'failed'::"text", 'timeout'::"text"]))),
    CONSTRAINT "valid_data_size" CHECK (("data_size_bytes" >= 0)),
    CONSTRAINT "valid_execution_time" CHECK (("execution_time_ms" >= 0))
);


CREATE TABLE IF NOT EXISTS "public"."article_agent_messages" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "session_id" "uuid" NOT NULL,
    "user_id" "text" NOT NULL,
    "role" "text" NOT NULL,
    "content" "text",
    "metadata" "jsonb" DEFAULT '{}'::"jsonb",
    "sequence" bigint NOT NULL,
    "created_at" timestamp with time zone DEFAULT "timezone"('utc'::"text", "now"()) NOT NULL,
    CONSTRAINT "article_agent_messages_role_check" CHECK (("role" = ANY (ARRAY['user'::"text", 'assistant'::"text", 'system'::"text", 'tool'::"text"])))
);


CREATE TABLE IF NOT EXISTS "public"."article_agent_sessions" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "article_id" "uuid" NOT NULL,
    "user_id" "text" NOT NULL,
    "organization_id" "uuid",
    "status" "text" DEFAULT 'active'::"text" NOT NULL,
    "session_store_key" "text" NOT NULL,
    "original_content" "text",
    "working_content" "text",
    "article_title" "text",
    "metadata" "jsonb" DEFAULT '{}'::"jsonb",
    "last_activity_at" timestamp with time zone DEFAULT "timezone"('utc'::"text", "now"()) NOT NULL,
    "created_at" timestamp with time zone DEFAULT "timezone"('utc'::"text", "now"()) NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "timezone"('utc'::"text", "now"()) NOT NULL,
    "closed_at" timestamp with time zone,
    "conversation_summary" "text",
    CONSTRAINT "article_agent_sessions_status_check" CHECK (("status" = ANY (ARRAY['active'::"text", 'paused'::"text", 'closed'::"text"])))
);


CREATE TABLE IF NOT EXISTS "public"."article_edit_versions" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "article_id" "uuid" NOT NULL,
    "user_id" "text" NOT NULL,
    "version_number" integer NOT NULL,
    "title" "text",
    "content" "text" NOT NULL,
    "change_description" "text",
    "is_current" boolean DEFAULT false,
    "metadata" "jsonb" DEFAULT '{}'::"jsonb",
    "created_at" timestamp with time zone DEFAULT "now"()
);


CREATE TABLE IF NOT EXISTS "public"."article_generation_flows" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "organization_id" "uuid",
    "user_id" "text",
    "name" "text" NOT NULL,
    "description" "text",
    "is_template" boolean DEFAULT false,
    "created_at" timestamp with time zone DEFAULT "timezone"('utc'::"text", "now"()) NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "timezone"('utc'::"text", "now"()) NOT NULL,
    CONSTRAINT "flow_ownership_check" CHECK (((("organization_id" IS NOT NULL) AND ("user_id" IS NULL)) OR (("organization_id" IS NULL) AND ("user_id" IS NOT NULL)) OR (("organization_id" IS NULL) AND ("user_id" IS NULL) AND ("is_template" = true))))
);


CREATE TABLE IF NOT EXISTS "public"."article_generation_step_snapshots" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "process_id" "uuid" NOT NULL,
    "step_name" "text" NOT NULL,
    "step_index" integer DEFAULT 1 NOT NULL,
    "step_category" "text",
    "step_description" "text",
    "article_context" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "process_metadata" "jsonb" DEFAULT '{}'::"jsonb",
    "snapshot_metadata" "jsonb" DEFAULT '{}'::"jsonb",
    "can_restore" boolean DEFAULT true,
    "created_at" timestamp with time zone DEFAULT "now"(),
    "branch_id" "uuid" DEFAULT "gen_random_uuid"(),
    "parent_snapshot_id" "uuid",
    "is_active_branch" boolean DEFAULT true,
    "branch_name" "text"
);


CREATE TABLE IF NOT EXISTS "public"."articles" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "user_id" "text" NOT NULL,
    "organization_id" "uuid",
    "generation_process_id" "uuid",
    "title" "text" NOT NULL,
    "content" "text" NOT NULL,
    "keywords" "text"[],
    "target_audience" "text",
    "status" "text" DEFAULT 'draft'::"text",
    "created_at" timestamp with time zone DEFAULT "timezone"('utc'::"text", "now"()) NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "timezone"('utc'::"text", "now"()) NOT NULL
);


CREATE TABLE IF NOT EXISTS "public"."background_tasks" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "process_id" "uuid" NOT NULL,
    "task_type" "text" NOT NULL,
    "task_data" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "status" "text" DEFAULT 'pending'::"text",
    "priority" integer DEFAULT 5,
    "scheduled_for" timestamp with time zone DEFAULT "now"(),
    "started_at" timestamp with time zone,
    "completed_at" timestamp with time zone,
    "error_message" "text",
    "error_details" "jsonb",
    "retry_count" integer DEFAULT 0,
    "max_retries" integer DEFAULT 3,
    "retry_delay_seconds" integer DEFAULT 60,
    "worker_id" "text",
    "worker_hostname" "text",
    "heartbeat_at" timestamp with time zone,
    "depends_on" "uuid"[] DEFAULT '{}'::"uuid"[],
    "blocks_tasks" "uuid"[] DEFAULT '{}'::"uuid"[],
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"(),
    "created_by" "text",
    "tags" "text"[] DEFAULT '{}'::"text"[],
    "execution_time" interval,
    "estimated_duration" interval,
    "resource_usage" "jsonb" DEFAULT '{}'::"jsonb",
    CONSTRAINT "background_tasks_status_check" CHECK (("status" = ANY (ARRAY['pending'::"text", 'running'::"text", 'completed'::"text", 'failed'::"text", 'cancelled'::"text", 'paused'::"text"])))
);


CREATE TABLE IF NOT EXISTS "public"."blog_generation_state" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "user_id" "text" NOT NULL,
    "organization_id" "uuid",
    "wordpress_site_id" "uuid",
    "status" "text" DEFAULT 'pending'::"text",
    "current_step_name" "text",
    "progress_percentage" integer DEFAULT 0,
    "is_waiting_for_input" boolean DEFAULT false,
    "input_type" "text",
    "blog_context" "jsonb" DEFAULT '{}'::"jsonb",
    "user_prompt" "text",
    "reference_url" "text",
    "uploaded_images" "jsonb" DEFAULT '[]'::"jsonb",
    "response_id" "text",
    "draft_post_id" integer,
    "draft_preview_url" "text",
    "draft_edit_url" "text",
    "error_message" "text",
    "realtime_channel" "text",
    "last_realtime_event" "jsonb",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"(),
    CONSTRAINT "blog_generation_state_progress_percentage_check" CHECK ((("progress_percentage" >= 0) AND ("progress_percentage" <= 100))),
    CONSTRAINT "blog_generation_state_status_check" CHECK (("status" = ANY (ARRAY['pending'::"text", 'in_progress'::"text", 'completed'::"text", 'error'::"text", 'user_input_required'::"text", 'cancelled'::"text"])))
);


CREATE TABLE IF NOT EXISTS "public"."blog_process_events" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "process_id" "uuid" NOT NULL,
    "user_id" "text" NOT NULL,
    "event_type" "text" NOT NULL,
    "event_data" "jsonb" DEFAULT '{}'::"jsonb",
    "event_sequence" integer DEFAULT 0 NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"()
);


CREATE TABLE IF NOT EXISTS "public"."company_info" (
    "id" "text" DEFAULT ("gen_random_uuid"())::"text" NOT NULL,
    "user_id" "text" NOT NULL,
    "name" character varying(200) NOT NULL,
    "website_url" character varying(500) NOT NULL,
    "description" "text" NOT NULL,
    "usp" "text" NOT NULL,
    "target_persona" "text" NOT NULL,
    "is_default" boolean DEFAULT false NOT NULL,
    "brand_slogan" character varying(200),
    "target_keywords" character varying(500),
    "industry_terms" character varying(500),
    "avoid_terms" character varying(500),
    "popular_articles" "text",
    "target_area" character varying(200),
    "created_at" timestamp with time zone DEFAULT "timezone"('utc'::"text", "now"()) NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "timezone"('utc'::"text", "now"()) NOT NULL
);


CREATE TABLE IF NOT EXISTS "public"."flow_steps" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "flow_id" "uuid" NOT NULL,
    "step_order" integer NOT NULL,
    "step_type" "public"."step_type" NOT NULL,
    "agent_name" "text",
    "prompt_template_id" "uuid",
    "tool_config" "jsonb",
    "output_schema" "jsonb",
    "is_interactive" boolean DEFAULT false,
    "skippable" boolean DEFAULT false,
    "config" "jsonb"
);


CREATE TABLE IF NOT EXISTS "public"."generated_articles_state" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "flow_id" "uuid",
    "user_id" "text" NOT NULL,
    "organization_id" "uuid",
    "current_step_id" "uuid",
    "status" "public"."generation_status" DEFAULT 'in_progress'::"public"."generation_status" NOT NULL,
    "article_context" "jsonb" NOT NULL,
    "generated_content" "jsonb",
    "article_id" "uuid",
    "error_message" "text",
    "created_at" timestamp with time zone DEFAULT "timezone"('utc'::"text", "now"()) NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "timezone"('utc'::"text", "now"()) NOT NULL,
    "current_step_name" "text",
    "progress_percentage" integer DEFAULT 0,
    "is_waiting_for_input" boolean DEFAULT false,
    "input_type" "text",
    "last_activity_at" timestamp with time zone DEFAULT "timezone"('utc'::"text", "now"()),
    "auto_resume_eligible" boolean DEFAULT false,
    "resume_from_step" "text",
    "step_history" "jsonb" DEFAULT '[]'::"jsonb",
    "process_metadata" "jsonb" DEFAULT '{}'::"jsonb",
    "image_mode" boolean DEFAULT false,
    "image_settings" "jsonb" DEFAULT '{}'::"jsonb",
    "style_template_id" "uuid",
    "realtime_channel" "text",
    "last_realtime_event" "jsonb",
    "realtime_subscriptions" "jsonb" DEFAULT '[]'::"jsonb",
    "executing_step" "text",
    "step_execution_start" timestamp with time zone,
    "step_execution_metadata" "jsonb" DEFAULT '{}'::"jsonb",
    "background_task_id" "text",
    "task_priority" integer DEFAULT 5,
    "retry_count" integer DEFAULT 0,
    "max_retries" integer DEFAULT 3,
    "user_input_timeout" timestamp with time zone,
    "input_reminder_sent" boolean DEFAULT false,
    "interaction_history" "jsonb" DEFAULT '[]'::"jsonb",
    "process_type" "text" DEFAULT 'article_generation'::"text",
    "parent_process_id" "uuid",
    "process_tags" "text"[] DEFAULT '{}'::"text"[],
    "step_durations" "jsonb" DEFAULT '{}'::"jsonb",
    "total_processing_time" interval,
    "estimated_completion_time" timestamp with time zone,
    "current_snapshot_id" "uuid"
);


CREATE TABLE IF NOT EXISTS "public"."image_placeholders" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "article_id" "uuid",
    "generation_process_id" "uuid",
    "placeholder_id" "text" NOT NULL,
    "description_jp" "text" NOT NULL,
    "prompt_en" "text" NOT NULL,
    "position_index" integer NOT NULL,
    "replaced_with_image_id" "uuid",
    "status" "text" DEFAULT 'pending'::"text",
    "metadata" "jsonb" DEFAULT '{}'::"jsonb",
    "created_at" timestamp with time zone DEFAULT "timezone"('utc'::"text", "now"()) NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "timezone"('utc'::"text", "now"()) NOT NULL,
    CONSTRAINT "image_placeholders_status_check" CHECK (("status" = ANY (ARRAY['pending'::"text", 'replaced'::"text", 'generating'::"text"])))
);


CREATE TABLE IF NOT EXISTS "public"."images" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "user_id" "text" NOT NULL,
    "organization_id" "uuid",
    "article_id" "uuid",
    "generation_process_id" "uuid",
    "original_filename" "text",
    "file_path" "text" NOT NULL,
    "image_type" "text" NOT NULL,
    "alt_text" "text",
    "caption" "text",
    "generation_prompt" "text",
    "generation_params" "jsonb",
    "metadata" "jsonb" DEFAULT '{}'::"jsonb",
    "created_at" timestamp with time zone DEFAULT "timezone"('utc'::"text", "now"()) NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "timezone"('utc'::"text", "now"()) NOT NULL,
    "gcs_url" "text",
    "gcs_path" "text",
    "storage_type" "text" DEFAULT 'local'::"text",
    CONSTRAINT "images_image_type_check" CHECK (("image_type" = ANY (ARRAY['uploaded'::"text", 'generated'::"text"]))),
    CONSTRAINT "images_storage_type_check" CHECK (("storage_type" = ANY (ARRAY['local'::"text", 'gcs'::"text", 'hybrid'::"text"])))
);


CREATE TABLE IF NOT EXISTS "public"."invitations" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "organization_id" "uuid" NOT NULL,
    "email" "text" NOT NULL,
    "role" "public"."organization_role" DEFAULT 'member'::"public"."organization_role" NOT NULL,
    "status" "public"."invitation_status" DEFAULT 'pending'::"public"."invitation_status" NOT NULL,
    "invited_by_user_id" "text" NOT NULL,
    "token" "text" DEFAULT "encode"("extensions"."gen_random_bytes"(32), 'hex'::"text") NOT NULL,
    "expires_at" timestamp with time zone DEFAULT ("timezone"('utc'::"text", "now"()) + '7 days'::interval) NOT NULL,
    "created_at" timestamp with time zone DEFAULT "timezone"('utc'::"text", "now"()) NOT NULL
);


CREATE TABLE IF NOT EXISTS "public"."organization_members" (
    "organization_id" "uuid" NOT NULL,
    "user_id" "text" NOT NULL,
    "role" "public"."organization_role" DEFAULT 'member'::"public"."organization_role" NOT NULL,
    "clerk_membership_id" "text",
    "joined_at" timestamp with time zone DEFAULT "timezone"('utc'::"text", "now"()) NOT NULL,
    "display_name" "text",
    "email" "text"
);


CREATE TABLE IF NOT EXISTS "public"."organization_subscriptions" (
    "id" "text" NOT NULL,
    "organization_id" "uuid" NOT NULL,
    "status" "public"."subscription_status" NOT NULL,
    "metadata" "jsonb",
    "price_id" "text",
    "quantity" integer DEFAULT 1 NOT NULL,
    "cancel_at_period_end" boolean DEFAULT false,
    "created" timestamp with time zone DEFAULT "timezone"('utc'::"text", "now"()) NOT NULL,
    "current_period_start" timestamp with time zone DEFAULT "timezone"('utc'::"text", "now"()) NOT NULL,
    "current_period_end" timestamp with time zone DEFAULT "timezone"('utc'::"text", "now"()) NOT NULL,
    "ended_at" timestamp with time zone,
    "cancel_at" timestamp with time zone,
    "canceled_at" timestamp with time zone,
    "trial_start" timestamp with time zone,
    "trial_end" timestamp with time zone,
    "plan_tier_id" "text" DEFAULT 'default'::"text",
    "addon_quantity" integer DEFAULT 0 NOT NULL
);


CREATE TABLE IF NOT EXISTS "public"."organizations" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "name" "text" NOT NULL,
    "owner_user_id" "text" NOT NULL,
    "clerk_organization_id" "text",
    "stripe_customer_id" "text",
    "created_at" timestamp with time zone DEFAULT "timezone"('utc'::"text", "now"()) NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "timezone"('utc'::"text", "now"()) NOT NULL,
    "billing_user_id" "text"
);


CREATE TABLE IF NOT EXISTS "public"."plan_tiers" (
    "id" "text" NOT NULL,
    "name" "text" NOT NULL,
    "stripe_price_id" "text" NOT NULL,
    "monthly_article_limit" integer NOT NULL,
    "addon_unit_amount" integer DEFAULT 20 NOT NULL,
    "price_amount" integer NOT NULL,
    "display_order" integer DEFAULT 0 NOT NULL,
    "is_active" boolean DEFAULT true NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"()
);


CREATE TABLE IF NOT EXISTS "public"."process_events" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "process_id" "uuid" NOT NULL,
    "event_type" "text" NOT NULL,
    "event_data" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "event_sequence" integer NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"(),
    "published_at" timestamp with time zone,
    "acknowledged_by" "text"[] DEFAULT '{}'::"text"[],
    "delivery_attempts" integer DEFAULT 0,
    "event_category" "text" DEFAULT 'system'::"text",
    "event_priority" integer DEFAULT 5,
    "event_source" "text" DEFAULT 'backend'::"text",
    "expires_at" timestamp with time zone,
    "archived" boolean DEFAULT false
);


CREATE TABLE IF NOT EXISTS "public"."style_guide_templates" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "user_id" "text" NOT NULL,
    "organization_id" "uuid",
    "name" "text" NOT NULL,
    "description" "text",
    "template_type" "public"."style_template_type" DEFAULT 'custom'::"public"."style_template_type",
    "settings" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "is_active" boolean DEFAULT true,
    "is_default" boolean DEFAULT false,
    "created_at" timestamp with time zone DEFAULT "timezone"('utc'::"text", "now"()) NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "timezone"('utc'::"text", "now"()) NOT NULL
);


CREATE TABLE IF NOT EXISTS "public"."subscription_events" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "user_id" "text" NOT NULL,
    "event_type" "text" NOT NULL,
    "stripe_event_id" "text",
    "event_data" "jsonb",
    "created_at" timestamp with time zone DEFAULT "now"()
);


CREATE TABLE IF NOT EXISTS "public"."usage_logs" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "usage_tracking_id" "uuid" NOT NULL,
    "user_id" "text" NOT NULL,
    "generation_process_id" "text" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"()
);


CREATE TABLE IF NOT EXISTS "public"."usage_tracking" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "user_id" "text",
    "organization_id" "uuid",
    "billing_period_start" timestamp with time zone NOT NULL,
    "billing_period_end" timestamp with time zone NOT NULL,
    "articles_generated" integer DEFAULT 0 NOT NULL,
    "articles_limit" integer NOT NULL,
    "addon_articles_limit" integer DEFAULT 0 NOT NULL,
    "plan_tier_id" "text",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"(),
    CONSTRAINT "chk_usage_owner" CHECK (((("user_id" IS NOT NULL) AND ("organization_id" IS NULL)) OR (("user_id" IS NULL) AND ("organization_id" IS NOT NULL))))
);


CREATE TABLE IF NOT EXISTS "public"."wordpress_sites" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "user_id" "text" NOT NULL,
    "organization_id" "uuid",
    "site_url" "text" NOT NULL,
    "site_name" "text",
    "mcp_endpoint" "text" NOT NULL,
    "encrypted_credentials" "text" NOT NULL,
    "connection_status" "text" DEFAULT 'connected'::"text",
    "is_active" boolean DEFAULT false,
    "last_connected_at" timestamp with time zone,
    "last_used_at" timestamp with time zone,
    "last_error" "text",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"(),
    CONSTRAINT "wordpress_sites_connection_status_check" CHECK (("connection_status" = ANY (ARRAY['connected'::"text", 'disconnected'::"text", 'error'::"text"])))
);


CREATE TABLE IF NOT EXISTS "public"."workflow_step_logs" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "session_id" "uuid" NOT NULL,
    "step_name" "text" NOT NULL,
    "step_type" "text" NOT NULL,
    "step_order" integer NOT NULL,
    "status" "text" DEFAULT 'pending'::"text" NOT NULL,
    "step_input" "jsonb" DEFAULT '{}'::"jsonb",
    "step_output" "jsonb" DEFAULT '{}'::"jsonb",
    "intermediate_results" "jsonb" DEFAULT '{}'::"jsonb",
    "primary_execution_id" "uuid",
    "started_at" timestamp with time zone,
    "completed_at" timestamp with time zone,
    "duration_ms" integer,
    "step_metadata" "jsonb" DEFAULT '{}'::"jsonb",
    CONSTRAINT "valid_step_duration" CHECK (("duration_ms" >= 0)),
    CONSTRAINT "workflow_step_logs_status_check" CHECK (("status" = ANY (ARRAY['pending'::"text", 'running'::"text", 'completed'::"text", 'failed'::"text", 'skipped'::"text"])))
);


-- ===================== FUNCTIONS =====================


CREATE OR REPLACE FUNCTION "public"."add_step_to_history"("process_id" "uuid", "step_name" "text", "step_status" "text", "step_data" "jsonb" DEFAULT '{}'::"jsonb") RETURNS "void"
    LANGUAGE "plpgsql"
    AS $$
DECLARE
    new_step JSONB;
    current_history JSONB;
BEGIN
    -- Create new step entry
    new_step := jsonb_build_object(
        'step_name', step_name,
        'status', step_status,
        'timestamp', TIMEZONE('utc'::text, now()),
        'data', step_data
    );
    
    -- Get current history
    SELECT COALESCE(step_history, '[]'::jsonb) INTO current_history
    FROM generated_articles_state
    WHERE id = process_id;
    
    -- Add new step to history
    UPDATE generated_articles_state
    SET step_history = current_history || new_step
    WHERE id = process_id;
END;
$$;


CREATE OR REPLACE FUNCTION "public"."cleanup_old_events"("days_old" integer DEFAULT 7) RETURNS integer
    LANGUAGE "plpgsql"
    AS $$
DECLARE
  deleted_count INTEGER;
BEGIN
  -- Delete events older than specified days, but keep important ones
  DELETE FROM process_events
  WHERE created_at < (NOW() - INTERVAL '1 day' * days_old)
    AND event_type NOT IN ('process_created', 'generation_completed', 'generation_error')
    AND archived = FALSE;
  
  GET DIAGNOSTICS deleted_count = ROW_COUNT;
  
  -- Archive instead of delete for important events
  UPDATE process_events 
  SET archived = TRUE
  WHERE created_at < (NOW() - INTERVAL '1 day' * days_old * 2)
    AND event_type IN ('process_created', 'generation_completed', 'generation_error')
    AND archived = FALSE;
  
  RETURN deleted_count;
END;
$$;


CREATE OR REPLACE FUNCTION "public"."cleanup_old_processes"("days_old" integer DEFAULT 30) RETURNS integer
    LANGUAGE "plpgsql"
    AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM generated_articles_state
    WHERE status IN ('completed', 'cancelled')
    AND updated_at < (TIMEZONE('utc'::text, now()) - INTERVAL '1 day' * days_old);
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$;


CREATE OR REPLACE FUNCTION "public"."cleanup_old_snapshots"("p_days_old" integer DEFAULT 30, "p_keep_count" integer DEFAULT 10) RETURNS integer
    LANGUAGE "plpgsql"
    AS $$
DECLARE
    v_deleted_count INTEGER := 0;
BEGIN
    -- Delete old snapshots, keeping the most recent p_keep_count per process
    WITH snapshots_to_keep AS (
        SELECT id
        FROM (
            SELECT id,
                   ROW_NUMBER() OVER (PARTITION BY process_id ORDER BY created_at DESC) as rn
            FROM article_generation_step_snapshots
        ) ranked
        WHERE rn <= p_keep_count
    ),
    old_snapshots AS (
        SELECT id
        FROM article_generation_step_snapshots
        WHERE created_at < (NOW() - INTERVAL '1 day' * p_days_old)
          AND id NOT IN (SELECT id FROM snapshots_to_keep)
    )
    DELETE FROM article_generation_step_snapshots
    WHERE id IN (SELECT id FROM old_snapshots);

    GET DIAGNOSTICS v_deleted_count = ROW_COUNT;

    RETURN v_deleted_count;
END;
$$;


CREATE OR REPLACE FUNCTION "public"."create_process_event"("p_process_id" "uuid", "p_event_type" "text", "p_event_data" "jsonb" DEFAULT '{}'::"jsonb", "p_event_category" "text" DEFAULT 'manual'::"text", "p_event_source" "text" DEFAULT 'application'::"text") RETURNS "uuid"
    LANGUAGE "plpgsql"
    AS $$
DECLARE
  event_id UUID;
  next_sequence INTEGER;
BEGIN
  -- Get next sequence number
  SELECT COALESCE(MAX(event_sequence), 0) + 1 
  INTO next_sequence
  FROM process_events 
  WHERE process_id = p_process_id;
  
  -- Insert the event
  INSERT INTO process_events (
    process_id,
    event_type,
    event_data,
    event_sequence,
    event_category,
    event_source,
    published_at
  ) VALUES (
    p_process_id,
    p_event_type,
    p_event_data,
    next_sequence,
    p_event_category,
    p_event_source,
    NOW()
  ) RETURNING id INTO event_id;
  
  RETURN event_id;
END;
$$;


CREATE OR REPLACE FUNCTION "public"."create_user_subscription_record"("p_user_id" "text", "p_email" "text") RETURNS "public"."user_subscriptions"
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
DECLARE
    v_is_privileged BOOLEAN;
    v_result user_subscriptions%ROWTYPE;
BEGIN
    -- @shintairiku.jp ドメインかどうかをチェック
    v_is_privileged := p_email ILIKE '%@shintairiku.jp';

    -- レコードを挿入または更新
    INSERT INTO user_subscriptions (user_id, email, is_privileged, status)
    VALUES (p_user_id, p_email, v_is_privileged, 'none')
    ON CONFLICT (user_id) DO UPDATE SET
        email = EXCLUDED.email,
        is_privileged = EXCLUDED.is_privileged,
        updated_at = NOW()
    RETURNING * INTO v_result;

    RETURN v_result;
END;
$$;


CREATE OR REPLACE FUNCTION "public"."delete_article_version"("p_version_id" "uuid") RETURNS boolean
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
DECLARE
    v_is_current BOOLEAN;
    v_article_id UUID;
BEGIN
    -- Check if this is the current version
    SELECT is_current, article_id INTO v_is_current, v_article_id
    FROM article_edit_versions
    WHERE id = p_version_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Version not found: %', p_version_id;
    END IF;

    IF v_is_current THEN
        RAISE EXCEPTION 'Cannot delete current version. Please navigate to a different version first.';
    END IF;

    -- Delete the version
    DELETE FROM article_edit_versions
    WHERE id = p_version_id;

    RETURN TRUE;
END;
$$;


CREATE OR REPLACE FUNCTION "public"."ensure_single_default_style_template"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
  -- If setting this template as default, unset all other defaults for the same user/org
  IF NEW.is_default = true THEN
    -- For personal templates
    IF NEW.organization_id IS NULL THEN
      UPDATE style_guide_templates 
      SET is_default = false 
      WHERE user_id = NEW.user_id 
        AND organization_id IS NULL 
        AND id != NEW.id 
        AND is_default = true;
    -- For organization templates
    ELSE
      UPDATE style_guide_templates 
      SET is_default = false 
      WHERE organization_id = NEW.organization_id 
        AND id != NEW.id 
        AND is_default = true;
    END IF;
  END IF;
  
  RETURN NEW;
END;
$$;


CREATE OR REPLACE FUNCTION "public"."extract_image_placeholders"("article_content" "text", "process_id" "uuid" DEFAULT NULL::"uuid", "article_id_param" "uuid" DEFAULT NULL::"uuid") RETURNS "void"
    LANGUAGE "plpgsql"
    AS $$
DECLARE
  placeholder_pattern TEXT := '<!-- IMAGE_PLACEHOLDER: ([^|]+)\|([^|]+)\|([^>]+) -->';
  match RECORD;
  counter INTEGER := 0;
BEGIN
  -- Extract all image placeholders using regex
  FOR match IN
    SELECT 
      (regexp_matches(article_content, placeholder_pattern, 'g'))[1] as placeholder_id,
      (regexp_matches(article_content, placeholder_pattern, 'g'))[2] as description_jp,
      (regexp_matches(article_content, placeholder_pattern, 'g'))[3] as prompt_en,
      (regexp_match_indices(article_content, placeholder_pattern, 'g'))[1] as position
  LOOP
    counter := counter + 1;
    
    -- Insert placeholder into image_placeholders table
    INSERT INTO image_placeholders (
      article_id, 
      generation_process_id, 
      placeholder_id, 
      description_jp, 
      prompt_en, 
      position_index
    ) VALUES (
      article_id_param,
      process_id,
      match.placeholder_id,
      match.description_jp,
      match.prompt_en,
      counter
    )
    ON CONFLICT (article_id, placeholder_id) 
    DO UPDATE SET
      description_jp = EXCLUDED.description_jp,
      prompt_en = EXCLUDED.prompt_en,
      position_index = EXCLUDED.position_index,
      updated_at = TIMEZONE('utc'::text, now());
  END LOOP;
END;
$$;


CREATE OR REPLACE FUNCTION "public"."get_article_version"("p_version_id" "uuid") RETURNS TABLE("version_id" "uuid", "article_id" "uuid", "version_number" integer, "title" "text", "content" "text", "change_description" "text", "is_current" boolean, "created_at" timestamp with time zone, "user_id" "text", "metadata" "jsonb")
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
BEGIN
    RETURN QUERY
    SELECT
        article_edit_versions.id,
        article_edit_versions.article_id,
        article_edit_versions.version_number,
        article_edit_versions.title,
        article_edit_versions.content,
        article_edit_versions.change_description,
        article_edit_versions.is_current,
        article_edit_versions.created_at,
        article_edit_versions.user_id,
        article_edit_versions.metadata
    FROM article_edit_versions
    WHERE article_edit_versions.id = p_version_id;
END;
$$;


CREATE OR REPLACE FUNCTION "public"."get_article_version_history"("p_article_id" "uuid", "p_limit" integer DEFAULT 100) RETURNS TABLE("version_id" "uuid", "version_number" integer, "title" "text", "change_description" "text", "is_current" boolean, "created_at" timestamp with time zone, "user_id" "text", "metadata" "jsonb")
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
BEGIN
    RETURN QUERY
    SELECT
        article_edit_versions.id,
        article_edit_versions.version_number,
        article_edit_versions.title,
        article_edit_versions.change_description,
        article_edit_versions.is_current,
        article_edit_versions.created_at,
        article_edit_versions.user_id,
        article_edit_versions.metadata
    FROM article_edit_versions
    WHERE article_edit_versions.article_id = p_article_id
    ORDER BY article_edit_versions.version_number DESC
    LIMIT p_limit;
END;
$$;


CREATE OR REPLACE FUNCTION "public"."get_available_snapshots"("p_process_id" "uuid") RETURNS TABLE("snapshot_id" "uuid", "step_name" "text", "step_index" integer, "step_category" "text", "step_description" "text", "created_at" timestamp with time zone, "can_restore" boolean, "branch_id" "uuid", "branch_name" "text", "is_active_branch" boolean, "parent_snapshot_id" "uuid", "is_current" boolean)
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
DECLARE
    v_current_snapshot_id UUID;
BEGIN
    -- Get current snapshot ID
    SELECT generated_articles_state.current_snapshot_id INTO v_current_snapshot_id
    FROM generated_articles_state
    WHERE generated_articles_state.id = p_process_id;

    RETURN QUERY
    SELECT
        article_generation_step_snapshots.id,
        article_generation_step_snapshots.step_name,
        article_generation_step_snapshots.step_index,
        article_generation_step_snapshots.step_category,
        article_generation_step_snapshots.step_description,
        article_generation_step_snapshots.created_at,
        article_generation_step_snapshots.can_restore,
        article_generation_step_snapshots.branch_id,
        article_generation_step_snapshots.branch_name,
        article_generation_step_snapshots.is_active_branch,
        article_generation_step_snapshots.parent_snapshot_id,
        article_generation_step_snapshots.id = v_current_snapshot_id AS is_current
    FROM article_generation_step_snapshots
    WHERE article_generation_step_snapshots.process_id = p_process_id
        AND article_generation_step_snapshots.can_restore = TRUE
    ORDER BY article_generation_step_snapshots.created_at ASC;
END;
$$;


CREATE OR REPLACE FUNCTION "public"."get_current_article_version"("p_article_id" "uuid") RETURNS "uuid"
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
DECLARE
    v_current_version_id UUID;
BEGIN
    SELECT id INTO v_current_version_id
    FROM article_edit_versions
    WHERE article_id = p_article_id
        AND is_current = TRUE
    LIMIT 1;

    RETURN v_current_version_id;
END;
$$;


CREATE OR REPLACE FUNCTION "public"."get_next_background_task"("worker_id_param" "text", "task_types" "text"[] DEFAULT NULL::"text"[]) RETURNS "uuid"
    LANGUAGE "plpgsql"
    AS $$
DECLARE
  task_id UUID;
BEGIN
  -- Get the highest priority pending task
  SELECT id INTO task_id
  FROM background_tasks
  WHERE status = 'pending'
    AND scheduled_for <= NOW()
    AND (task_types IS NULL OR task_type = ANY(task_types))
    AND (depends_on = '{}' OR NOT EXISTS (
      SELECT 1 FROM background_tasks dep 
      WHERE dep.id = ANY(background_tasks.depends_on) 
        AND dep.status NOT IN ('completed', 'cancelled')
    ))
  ORDER BY priority DESC, created_at ASC
  LIMIT 1
  FOR UPDATE SKIP LOCKED;
  
  -- Claim the task
  IF task_id IS NOT NULL THEN
    UPDATE background_tasks
    SET status = 'running',
        worker_id = worker_id_param,
        started_at = NOW(),
        heartbeat_at = NOW()
    WHERE id = task_id;
  END IF;
  
  RETURN task_id;
END;
$$;


CREATE OR REPLACE FUNCTION "public"."get_process_recovery_info"("process_id" "uuid") RETURNS TABLE("can_resume" boolean, "resume_step" "text", "current_data" "jsonb", "waiting_for_input" boolean, "input_type" "text")
    LANGUAGE "plpgsql"
    AS $$
BEGIN
    RETURN QUERY
    SELECT 
        (s.status IN ('user_input_required', 'paused', 'error') AND s.auto_resume_eligible),
        s.resume_from_step,
        s.generated_content,
        s.is_waiting_for_input,
        s.input_type
    FROM generated_articles_state s
    WHERE s.id = process_id;
END;
$$;


CREATE OR REPLACE FUNCTION "public"."get_snapshot_details"("p_snapshot_id" "uuid") RETURNS "jsonb"
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
DECLARE
    v_snapshot RECORD;
BEGIN
    SELECT
        id,
        process_id,
        step_name,
        step_index,
        step_category,
        step_description,
        article_context,
        snapshot_metadata,
        can_restore,
        created_at
    INTO v_snapshot
    FROM article_generation_step_snapshots
    WHERE id = p_snapshot_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Snapshot not found: %', p_snapshot_id;
    END IF;

    RETURN to_jsonb(v_snapshot);
END;
$$;


CREATE OR REPLACE FUNCTION "public"."handle_new_organization"() RETURNS "trigger"
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
BEGIN
  INSERT INTO organization_members (organization_id, user_id, role)
  VALUES (new.id, new.owner_user_id, 'owner');
  RETURN new;
END;
$$;


CREATE OR REPLACE FUNCTION "public"."has_active_access"("p_user_id" "text") RETURNS boolean
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
DECLARE
    v_subscription user_subscriptions%ROWTYPE;
BEGIN
    -- サブスクリプション情報を取得
    SELECT * INTO v_subscription
    FROM user_subscriptions
    WHERE user_id = p_user_id;

    -- レコードが存在しない場合はアクセス不可
    IF NOT FOUND THEN
        RETURN FALSE;
    END IF;

    -- @shintairiku.jp 特権ユーザーは常にアクセス可能
    IF v_subscription.is_privileged = TRUE THEN
        RETURN TRUE;
    END IF;

    -- アクティブなサブスクリプション
    IF v_subscription.status = 'active' THEN
        RETURN TRUE;
    END IF;

    -- キャンセル済みでも期間内ならアクセス可能
    IF v_subscription.status = 'canceled'
       AND v_subscription.current_period_end > NOW() THEN
        RETURN TRUE;
    END IF;

    -- 支払い遅延でも猶予期間中はアクセス可能（3日間の猶予）
    IF v_subscription.status = 'past_due'
       AND v_subscription.current_period_end + INTERVAL '3 days' > NOW() THEN
        RETURN TRUE;
    END IF;

    RETURN FALSE;
END;
$$;


CREATE OR REPLACE FUNCTION "public"."increment_usage_if_allowed"("p_tracking_id" "uuid") RETURNS TABLE("new_count" integer, "was_allowed" boolean)
    LANGUAGE "plpgsql"
    AS $$
DECLARE
    v_rec usage_tracking%ROWTYPE;
BEGIN
    -- FOR UPDATE でロックを取得
    SELECT * INTO v_rec FROM usage_tracking WHERE id = p_tracking_id FOR UPDATE;

    IF NOT FOUND THEN
        RETURN QUERY SELECT 0, FALSE;
        RETURN;
    END IF;

    IF v_rec.articles_generated < (v_rec.articles_limit + v_rec.addon_articles_limit) THEN
        UPDATE usage_tracking
        SET articles_generated = articles_generated + 1, updated_at = NOW()
        WHERE id = p_tracking_id;
        RETURN QUERY SELECT v_rec.articles_generated + 1, TRUE;
    ELSE
        RETURN QUERY SELECT v_rec.articles_generated, FALSE;
    END IF;
END;
$$;


CREATE OR REPLACE FUNCTION "public"."mark_process_waiting_for_input"("p_process_id" "uuid", "p_input_type" "text", "p_timeout_minutes" integer DEFAULT 30) RETURNS "void"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
  UPDATE generated_articles_state
  SET 
    is_waiting_for_input = TRUE,
    input_type = p_input_type,
    user_input_timeout = NOW() + INTERVAL '1 minute' * p_timeout_minutes,
    input_reminder_sent = FALSE,
    status = 'user_input_required'
  WHERE id = p_process_id;
  
  -- Create corresponding event
  PERFORM create_process_event(
    p_process_id,
    'user_input_required',
    jsonb_build_object(
      'input_type', p_input_type,
      'timeout_at', NOW() + INTERVAL '1 minute' * p_timeout_minutes
    ),
    'user_interaction',
    'system'
  );
END;
$$;


CREATE OR REPLACE FUNCTION "public"."migrate_image_to_gcs"("image_id_param" "uuid", "gcs_url_param" "text", "gcs_path_param" "text") RETURNS "void"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
    UPDATE images 
    SET 
        gcs_url = gcs_url_param,
        gcs_path = gcs_path_param,
        storage_type = CASE 
            WHEN file_path IS NOT NULL THEN 'hybrid'
            ELSE 'gcs'
        END,
        updated_at = TIMEZONE('utc'::text, now())
    WHERE id = image_id_param;
END;
$$;


CREATE OR REPLACE FUNCTION "public"."navigate_to_version"("p_article_id" "uuid", "p_direction" "text") RETURNS "uuid"
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
DECLARE
    v_current_version_number INTEGER;
    v_target_version_id UUID;
    v_target_version_number INTEGER;
BEGIN
    -- Get current version number
    SELECT version_number INTO v_current_version_number
    FROM article_edit_versions
    WHERE article_id = p_article_id
        AND is_current = TRUE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'No current version found for article %', p_article_id;
    END IF;

    -- Find target version based on direction
    IF p_direction = 'next' THEN
        SELECT id, version_number INTO v_target_version_id, v_target_version_number
        FROM article_edit_versions
        WHERE article_id = p_article_id
            AND version_number > v_current_version_number
        ORDER BY version_number ASC
        LIMIT 1;
    ELSIF p_direction = 'previous' THEN
        SELECT id, version_number INTO v_target_version_id, v_target_version_number
        FROM article_edit_versions
        WHERE article_id = p_article_id
            AND version_number < v_current_version_number
        ORDER BY version_number DESC
        LIMIT 1;
    ELSE
        RAISE EXCEPTION 'Invalid direction: %. Must be "next" or "previous"', p_direction;
    END IF;

    IF v_target_version_id IS NULL THEN
        RAISE EXCEPTION 'No % version available', p_direction;
    END IF;

    -- Update current markers (don't create new version, just navigate)
    UPDATE article_edit_versions
    SET is_current = FALSE
    WHERE article_id = p_article_id;

    UPDATE article_edit_versions
    SET is_current = TRUE
    WHERE id = v_target_version_id;

    -- Update article content to match target version
    UPDATE articles
    SET
        title = (SELECT title FROM article_edit_versions WHERE id = v_target_version_id),
        content = (SELECT content FROM article_edit_versions WHERE id = v_target_version_id),
        updated_at = NOW()
    WHERE id = p_article_id;

    RETURN v_target_version_id;
END;
$$;


CREATE OR REPLACE FUNCTION "public"."publish_process_event"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
DECLARE
  event_data JSONB;
  channel_name TEXT;
  next_sequence INTEGER;
  event_type_name TEXT;
BEGIN
  -- Determine channel name (process-specific)
  channel_name := 'process_' || NEW.id::text;
  
  -- Determine event type based on operation and changes
  IF TG_OP = 'INSERT' THEN
    event_type_name := 'process_created';
  ELSIF TG_OP = 'UPDATE' THEN
    -- More specific event types based on what changed
    IF OLD.status IS DISTINCT FROM NEW.status THEN
      event_type_name := 'status_changed';
    ELSIF OLD.current_step_name IS DISTINCT FROM NEW.current_step_name THEN
      event_type_name := 'step_changed';
    ELSIF OLD.progress_percentage IS DISTINCT FROM NEW.progress_percentage THEN
      event_type_name := 'progress_updated';
    ELSIF OLD.is_waiting_for_input IS DISTINCT FROM NEW.is_waiting_for_input THEN
      event_type_name := CASE 
        WHEN NEW.is_waiting_for_input THEN 'input_required' 
        ELSE 'input_resolved' 
      END;
    ELSE
      event_type_name := 'process_updated';
    END IF;
  ELSE
    event_type_name := 'process_changed';
  END IF;
  
  -- Prepare comprehensive event data
  event_data := jsonb_build_object(
    'process_id', NEW.id,
    'status', NEW.status,
    'current_step', NEW.current_step_name,
    'executing_step', NEW.executing_step,
    'progress_percentage', NEW.progress_percentage,
    'is_waiting_for_input', NEW.is_waiting_for_input,
    'input_type', NEW.input_type,
    'updated_at', NEW.updated_at,
    'event_type', event_type_name,
    'user_id', NEW.user_id,
    'organization_id', NEW.organization_id,
    'background_task_id', NEW.background_task_id,
    'retry_count', NEW.retry_count,
    'error_message', NEW.error_message,
    -- Include relevant context data
    'article_context', NEW.article_context,
    'process_metadata', NEW.process_metadata,
    'step_history', NEW.step_history,
    -- Change tracking for updates
    'changes', CASE WHEN TG_OP = 'UPDATE' THEN
      jsonb_build_object(
        'status', jsonb_build_object('old', OLD.status, 'new', NEW.status),
        'current_step', jsonb_build_object('old', OLD.current_step_name, 'new', NEW.current_step_name),
        'progress', jsonb_build_object('old', OLD.progress_percentage, 'new', NEW.progress_percentage)
      )
    ELSE NULL END
  );
  
  -- Get next sequence number for this process
  SELECT COALESCE(MAX(event_sequence), 0) + 1 
  INTO next_sequence
  FROM process_events 
  WHERE process_id = NEW.id;
  
  -- Insert event record (now the parent record exists, so no foreign key violation)
  INSERT INTO process_events (
    process_id, 
    event_type, 
    event_data, 
    event_sequence,
    event_category,
    event_source,
    published_at
  ) VALUES (
    NEW.id,
    event_type_name,
    event_data,
    next_sequence,
    'process_state',
    'database_trigger',
    NOW()
  );
  
  RETURN NEW;
END;
$$;


CREATE OR REPLACE FUNCTION "public"."replace_placeholder_with_image"("article_id_param" "uuid", "placeholder_id_param" "text", "image_id_param" "uuid", "image_url" "text", "alt_text_param" "text" DEFAULT ''::"text") RETURNS "void"
    LANGUAGE "plpgsql"
    AS $$
DECLARE
  current_content TEXT;
  placeholder_pattern TEXT;
  replacement_html TEXT;
  updated_content TEXT;
BEGIN
  -- Get current article content
  SELECT content INTO current_content FROM articles WHERE id = article_id_param;
  
  -- Create placeholder pattern for this specific placeholder
  placeholder_pattern := '<!-- IMAGE_PLACEHOLDER: ' || placeholder_id_param || '\|[^>]+ -->';
  
  -- Create replacement HTML
  replacement_html := '<img src="' || image_url || '" alt="' || alt_text_param || '" class="article-image" />';
  
  -- Replace placeholder with image HTML
  updated_content := regexp_replace(current_content, placeholder_pattern, replacement_html, 'g');
  
  -- Update article content
  UPDATE articles SET content = updated_content WHERE id = article_id_param;
  
  -- Update placeholder status
  UPDATE image_placeholders 
  SET 
    replaced_with_image_id = image_id_param,
    status = 'replaced',
    updated_at = TIMEZONE('utc'::text, now())
  WHERE article_id = article_id_param AND placeholder_id = placeholder_id_param;
END;
$$;


CREATE OR REPLACE FUNCTION "public"."resolve_user_input"("p_process_id" "uuid", "p_user_response" "jsonb") RETURNS "void"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
  UPDATE generated_articles_state
  SET 
    is_waiting_for_input = FALSE,
    input_type = NULL,
    user_input_timeout = NULL,
    input_reminder_sent = FALSE,
    status = 'in_progress',
    interaction_history = interaction_history || jsonb_build_object(
      'timestamp', NOW(),
      'action', 'input_resolved',
      'response', p_user_response
    )
  WHERE id = p_process_id;
  
  -- Create corresponding event
  PERFORM create_process_event(
    p_process_id,
    'user_input_resolved',
    jsonb_build_object(
      'user_response', p_user_response,
      'resolved_at', NOW()
    ),
    'user_interaction',
    'system'
  );
END;
$$;


CREATE OR REPLACE FUNCTION "public"."restore_article_version"("p_version_id" "uuid", "p_create_new_version" boolean DEFAULT true) RETURNS "jsonb"
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
DECLARE
    v_version RECORD;
    v_new_version_id UUID;
BEGIN
    -- Get the version data
    SELECT
        article_id,
        version_number,
        title,
        content,
        user_id
    INTO v_version
    FROM article_edit_versions
    WHERE id = p_version_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Version not found: %', p_version_id;
    END IF;

    -- Update the article with the version content
    UPDATE articles
    SET
        title = v_version.title,
        content = v_version.content,
        updated_at = NOW()
    WHERE id = v_version.article_id;

    IF p_create_new_version THEN
        -- Create a new version for this restoration
        v_new_version_id := save_article_version(
            v_version.article_id,
            v_version.user_id,
            v_version.title,
            v_version.content,
            'バージョン ' || v_version.version_number || ' から復元',
            jsonb_build_object(
                'restored_from_version', v_version.version_number,
                'restored_from_version_id', p_version_id,
                'restored_at', NOW()
            )
        );
    ELSE
        -- Just mark this version as current
        UPDATE article_edit_versions
        SET is_current = FALSE
        WHERE article_id = v_version.article_id;

        UPDATE article_edit_versions
        SET is_current = TRUE
        WHERE id = p_version_id;

        v_new_version_id := p_version_id;
    END IF;

    RETURN jsonb_build_object(
        'success', true,
        'article_id', v_version.article_id,
        'restored_version_number', v_version.version_number,
        'new_version_id', v_new_version_id,
        'created_new_version', p_create_new_version
    );
END;
$$;


CREATE OR REPLACE FUNCTION "public"."restore_from_snapshot"("p_snapshot_id" "uuid", "p_create_new_branch" boolean DEFAULT false) RETURNS "jsonb"
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
DECLARE
    v_process_id UUID;
    v_step_name TEXT;
    v_article_context JSONB;
    v_branch_id UUID;
    v_snapshot_branch_id UUID;
BEGIN
    -- Retrieve snapshot data
    SELECT
        process_id,
        step_name,
        article_context,
        branch_id
    INTO v_process_id, v_step_name, v_article_context, v_snapshot_branch_id
    FROM article_generation_step_snapshots
    WHERE id = p_snapshot_id AND can_restore = TRUE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Snapshot not found or cannot be restored: %', p_snapshot_id;
    END IF;

    -- Get current active branch
    SELECT branch_id INTO v_branch_id
    FROM article_generation_step_snapshots
    WHERE process_id = v_process_id
      AND is_active_branch = TRUE
    ORDER BY created_at DESC
    LIMIT 1;

    -- If restore point is on a different branch, switch branches
    IF v_snapshot_branch_id != v_branch_id THEN
        -- Deactivate all branches for this process
        UPDATE article_generation_step_snapshots
        SET is_active_branch = FALSE
        WHERE process_id = v_process_id;

        -- Activate the snapshot's branch
        UPDATE article_generation_step_snapshots
        SET is_active_branch = TRUE
        WHERE process_id = v_process_id
          AND branch_id = v_snapshot_branch_id;

        v_branch_id := v_snapshot_branch_id;
    END IF;

    -- Add restoration metadata to context
    v_article_context := jsonb_set(
        v_article_context,
        '{_restoration_metadata}',
        jsonb_build_object(
            'restored_from_snapshot', p_snapshot_id,
            'restored_at', NOW(),
            'branch_id', v_branch_id
        )
    );

    -- Update process state - NO NEW SNAPSHOT CREATED, just move HEAD
    UPDATE generated_articles_state
    SET
        current_step_name = v_step_name,
        article_context = v_article_context,
        current_snapshot_id = p_snapshot_id,  -- Move HEAD to this snapshot
        status = CASE
            WHEN v_step_name IN ('persona_generated', 'theme_proposed', 'outline_generated')
            THEN 'user_input_required'::generation_status
            ELSE 'in_progress'::generation_status
        END,
        is_waiting_for_input = CASE
            WHEN v_step_name IN ('persona_generated', 'theme_proposed', 'outline_generated')
            THEN TRUE
            ELSE FALSE
        END,
        input_type = CASE
            WHEN v_step_name = 'persona_generated' THEN 'select_persona'
            WHEN v_step_name = 'theme_proposed' THEN 'select_theme'
            WHEN v_step_name = 'outline_generated' THEN 'approve_outline'
            ELSE NULL
        END,
        updated_at = NOW(),
        last_activity_at = NOW()
    WHERE id = v_process_id;

    -- Create process event for restoration
    PERFORM create_process_event(
        v_process_id,
        'snapshot_restored',
        jsonb_build_object(
            'snapshot_id', p_snapshot_id,
            'restored_step', v_step_name,
            'branch_id', v_branch_id,
            'restored_at', NOW()
        )
    );

    RETURN jsonb_build_object(
        'process_id', v_process_id,
        'step_name', v_step_name,
        'branch_id', v_branch_id,
        'created_new_branch', FALSE  -- Never create new branch on restore
    );
END;
$$;


CREATE OR REPLACE FUNCTION "public"."save_article_version"("p_article_id" "uuid", "p_user_id" "text", "p_title" "text", "p_content" "text", "p_change_description" "text" DEFAULT NULL::"text", "p_metadata" "jsonb" DEFAULT '{}'::"jsonb", "p_max_versions" integer DEFAULT 50) RETURNS "uuid"
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
DECLARE
    v_version_id UUID;
    v_next_version_number INTEGER;
    v_version_count INTEGER;
    v_versions_to_delete INTEGER;
BEGIN
    -- Get the next version number for this article
    SELECT COALESCE(MAX(version_number), 0) + 1 INTO v_next_version_number
    FROM article_edit_versions
    WHERE article_id = p_article_id;

    -- Mark all existing versions as not current
    UPDATE article_edit_versions
    SET is_current = FALSE
    WHERE article_id = p_article_id;

    -- Insert new version
    INSERT INTO article_edit_versions (
        article_id,
        user_id,
        version_number,
        title,
        content,
        change_description,
        is_current,
        metadata,
        created_at
    ) VALUES (
        p_article_id,
        p_user_id,
        v_next_version_number,
        p_title,
        p_content,
        COALESCE(
            p_change_description,
            CASE
                WHEN v_next_version_number = 1 THEN '初期バージョン'
                ELSE 'バージョン ' || v_next_version_number
            END
        ),
        TRUE, -- New version is current
        p_metadata,
        NOW()
    )
    RETURNING id INTO v_version_id;

    -- Check if we need to clean up old versions
    SELECT COUNT(*) INTO v_version_count
    FROM article_edit_versions
    WHERE article_id = p_article_id;

    IF v_version_count > p_max_versions THEN
        v_versions_to_delete := v_version_count - p_max_versions;

        -- Delete oldest versions (keeping the most recent p_max_versions)
        DELETE FROM article_edit_versions
        WHERE id IN (
            SELECT id
            FROM article_edit_versions
            WHERE article_id = p_article_id
            ORDER BY version_number ASC
            LIMIT v_versions_to_delete
        );

        RAISE NOTICE 'Deleted % old version(s) for article %', v_versions_to_delete, p_article_id;
    END IF;

    RETURN v_version_id;
END;
$$;


CREATE OR REPLACE FUNCTION "public"."save_step_snapshot"("p_process_id" "uuid", "p_step_name" "text", "p_article_context" "jsonb", "p_step_description" "text" DEFAULT NULL::"text", "p_step_category" "text" DEFAULT 'autonomous'::"text", "p_snapshot_metadata" "jsonb" DEFAULT '{}'::"jsonb", "p_branch_id" "uuid" DEFAULT NULL::"uuid") RETURNS "uuid"
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
DECLARE
    v_snapshot_id UUID;
    v_step_index INTEGER;
    v_branch_id UUID;
    v_parent_snapshot_id UUID;
    v_branch_name TEXT;
    v_current_snapshot_id UUID;
    v_current_branch_id UUID;
    v_should_create_new_branch BOOLEAN := FALSE;
    v_latest_in_branch UUID;
BEGIN
    -- Get current snapshot and branch info
    SELECT current_snapshot_id INTO v_current_snapshot_id
    FROM generated_articles_state
    WHERE id = p_process_id;

    -- If we have a current snapshot, check if we need to branch
    IF v_current_snapshot_id IS NOT NULL THEN
        -- Get current snapshot's branch
        SELECT branch_id INTO v_current_branch_id
        FROM article_generation_step_snapshots
        WHERE id = v_current_snapshot_id;

        -- Check if current snapshot is the latest in its branch
        SELECT id INTO v_latest_in_branch
        FROM article_generation_step_snapshots
        WHERE process_id = p_process_id
          AND branch_id = v_current_branch_id
        ORDER BY created_at DESC
        LIMIT 1;

        -- If current snapshot is NOT the latest, we're creating a branch
        IF v_latest_in_branch != v_current_snapshot_id THEN
            v_should_create_new_branch := TRUE;
            -- Parent is the snapshot we're branching FROM (the current position)
            v_parent_snapshot_id := v_current_snapshot_id;
        ELSE
            -- Continue on same branch, parent is current snapshot
            v_parent_snapshot_id := v_current_snapshot_id;
        END IF;
    END IF;

    -- Determine branch_id
    IF p_branch_id IS NOT NULL THEN
        -- Explicitly provided branch ID
        v_branch_id := p_branch_id;
        v_branch_name := NULL; -- Will be set by caller
    ELSIF v_should_create_new_branch THEN
        -- Create new branch (diverging from current snapshot)
        v_branch_id := gen_random_uuid();
        v_branch_name := '分岐 ' || TO_CHAR(NOW(), 'YYYY-MM-DD HH24:MI');

        -- Deactivate all branches for this process
        UPDATE article_generation_step_snapshots
        SET is_active_branch = FALSE
        WHERE process_id = p_process_id;
    ELSE
        -- Continue on current active branch
        IF v_current_snapshot_id IS NOT NULL THEN
            -- Use current branch
            v_branch_id := v_current_branch_id;
            v_branch_name := (
                SELECT branch_name FROM article_generation_step_snapshots
                WHERE branch_id = v_branch_id
                LIMIT 1
            );

            -- FIX: Deactivate all snapshots in this branch before adding new one
            UPDATE article_generation_step_snapshots
            SET is_active_branch = FALSE
            WHERE process_id = p_process_id
              AND branch_id = v_branch_id;
        ELSE
            -- First snapshot ever (main branch)
            v_branch_id := gen_random_uuid();
            v_branch_name := 'メインブランチ';
            v_parent_snapshot_id := NULL;
        END IF;
    END IF;

    -- Calculate step_index for this step/branch combination
    SELECT COALESCE(MAX(step_index), 0) + 1 INTO v_step_index
    FROM article_generation_step_snapshots
    WHERE process_id = p_process_id
      AND step_name = p_step_name
      AND branch_id = v_branch_id;

    -- Insert new snapshot
    INSERT INTO article_generation_step_snapshots (
        process_id,
        step_name,
        step_index,
        step_category,
        step_description,
        article_context,
        snapshot_metadata,
        branch_id,
        parent_snapshot_id,
        is_active_branch,
        branch_name,
        can_restore,
        created_at
    ) VALUES (
        p_process_id,
        p_step_name,
        v_step_index,
        p_step_category,
        p_step_description,
        p_article_context,
        p_snapshot_metadata,
        v_branch_id,
        v_parent_snapshot_id,
        TRUE,  -- New snapshot is always on active branch
        COALESCE(v_branch_name, 'メインブランチ'),
        TRUE,
        NOW()
    ) RETURNING id INTO v_snapshot_id;

    -- Update process's current_snapshot_id (move HEAD)
    UPDATE generated_articles_state
    SET current_snapshot_id = v_snapshot_id
    WHERE id = p_process_id;

    RETURN v_snapshot_id;
END;
$$;


CREATE OR REPLACE FUNCTION "public"."set_realtime_channel"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
  -- Set realtime channel name and updated timestamp
  NEW.realtime_channel := 'process_' || NEW.id::text;
  NEW.updated_at := NOW();
  
  RETURN NEW;
END;
$$;


CREATE OR REPLACE FUNCTION "public"."switch_to_branch"("p_process_id" "uuid", "p_branch_id" "uuid") RETURNS boolean
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
DECLARE
    v_latest_snapshot_id UUID;
    v_article_context JSONB;
    v_step_name TEXT;
BEGIN
    -- Verify branch exists for this process
    SELECT id, article_context, step_name
    INTO v_latest_snapshot_id, v_article_context, v_step_name
    FROM article_generation_step_snapshots
    WHERE process_id = p_process_id
      AND branch_id = p_branch_id
    ORDER BY created_at DESC
    LIMIT 1;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Branch % not found for process %', p_branch_id, p_process_id;
    END IF;

    -- Deactivate all branches for this process
    UPDATE article_generation_step_snapshots
    SET is_active_branch = FALSE
    WHERE process_id = p_process_id;

    -- Activate the target branch
    UPDATE article_generation_step_snapshots
    SET is_active_branch = TRUE
    WHERE process_id = p_process_id
      AND branch_id = p_branch_id;

    -- Update process state to reflect the branch
    UPDATE generated_articles_state
    SET
        current_step_name = v_step_name,
        article_context = v_article_context,
        updated_at = NOW(),
        last_activity_at = NOW()
    WHERE id = p_process_id;

    RETURN TRUE;
END;
$$;


CREATE OR REPLACE FUNCTION "public"."update_agent_log_sessions_timestamp"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


CREATE OR REPLACE FUNCTION "public"."update_article_image_urls"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
DECLARE
    article_record RECORD;
    old_url TEXT;
    new_url TEXT;
    updated_content TEXT;
BEGIN
    -- Only process if GCS URL is being added/updated
    IF NEW.gcs_url IS DISTINCT FROM OLD.gcs_url AND NEW.gcs_url IS NOT NULL THEN
        -- Find articles that reference this image
        FOR article_record IN 
            SELECT DISTINCT a.id, a.content 
            FROM articles a
            WHERE a.content LIKE '%' || 
                CASE 
                    WHEN OLD.file_path LIKE '%/%' THEN 
                        split_part(OLD.file_path, '/', -1)
                    ELSE 
                        OLD.file_path
                END || '%'
        LOOP
            -- Construct old and new URLs
            old_url := 'http://localhost:8008/images/' || 
                CASE 
                    WHEN OLD.file_path LIKE '%/%' THEN 
                        split_part(OLD.file_path, '/', -1)
                    ELSE 
                        OLD.file_path
                END;
            new_url := NEW.gcs_url;
            
            -- Replace URLs in article content
            updated_content := REPLACE(article_record.content, old_url, new_url);
            
            -- Update article if content changed
            IF updated_content != article_record.content THEN
                UPDATE articles 
                SET 
                    content = updated_content,
                    updated_at = TIMEZONE('utc'::text, now())
                WHERE id = article_record.id;
                
                RAISE NOTICE 'Updated image URLs in article %', article_record.id;
            END IF;
        END LOOP;
    END IF;
    
    RETURN NEW;
END;
$$;


CREATE OR REPLACE FUNCTION "public"."update_blog_generation_state_updated_at"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


CREATE OR REPLACE FUNCTION "public"."update_last_activity"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
    NEW.last_activity_at = TIMEZONE('utc'::text, now());
    RETURN NEW;
END;
$$;


CREATE OR REPLACE FUNCTION "public"."update_subscription_from_stripe"("p_user_id" "text", "p_stripe_customer_id" "text", "p_stripe_subscription_id" "text", "p_status" "text", "p_current_period_end" timestamp with time zone, "p_cancel_at_period_end" boolean DEFAULT false) RETURNS "public"."user_subscriptions"
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
DECLARE
    v_subscription_status user_subscription_status;
    v_result user_subscriptions%ROWTYPE;
BEGIN
    -- Stripeのステータスを内部ステータスにマッピング
    v_subscription_status := CASE p_status
        WHEN 'active' THEN 'active'::user_subscription_status
        WHEN 'trialing' THEN 'active'::user_subscription_status  -- トライアルもactive扱い
        WHEN 'past_due' THEN 'past_due'::user_subscription_status
        WHEN 'canceled' THEN 'canceled'::user_subscription_status
        WHEN 'unpaid' THEN 'expired'::user_subscription_status
        WHEN 'incomplete' THEN 'none'::user_subscription_status
        WHEN 'incomplete_expired' THEN 'expired'::user_subscription_status
        WHEN 'paused' THEN 'canceled'::user_subscription_status
        ELSE 'none'::user_subscription_status
    END;

    -- レコードを更新（存在しない場合は作成）
    INSERT INTO user_subscriptions (
        user_id,
        stripe_customer_id,
        stripe_subscription_id,
        status,
        current_period_end,
        cancel_at_period_end
    )
    VALUES (
        p_user_id,
        p_stripe_customer_id,
        p_stripe_subscription_id,
        v_subscription_status,
        p_current_period_end,
        p_cancel_at_period_end
    )
    ON CONFLICT (user_id) DO UPDATE SET
        stripe_customer_id = EXCLUDED.stripe_customer_id,
        stripe_subscription_id = EXCLUDED.stripe_subscription_id,
        status = EXCLUDED.status,
        current_period_end = EXCLUDED.current_period_end,
        cancel_at_period_end = EXCLUDED.cancel_at_period_end,
        updated_at = NOW()
    RETURNING * INTO v_result;

    RETURN v_result;
END;
$$;


CREATE OR REPLACE FUNCTION "public"."update_task_status"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
  -- Update timestamps based on status changes
  IF TG_OP = 'UPDATE' THEN
    IF OLD.status != NEW.status THEN
      CASE NEW.status
        WHEN 'running' THEN
          NEW.started_at := NOW();
          NEW.heartbeat_at := NOW();
        WHEN 'completed', 'failed', 'cancelled' THEN
          NEW.completed_at := NOW();
          IF NEW.started_at IS NOT NULL THEN
            NEW.execution_time := NOW() - NEW.started_at;
          END IF;
        ELSE
          -- Keep existing timestamps
      END CASE;
    END IF;
  END IF;
  
  -- Always update the updated_at timestamp
  NEW.updated_at := NOW();
  
  RETURN NEW;
END;
$$;


CREATE OR REPLACE FUNCTION "public"."update_updated_at_column"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$;


CREATE OR REPLACE FUNCTION "public"."update_user_subscriptions_updated_at"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


CREATE OR REPLACE FUNCTION "public"."update_wordpress_sites_updated_at"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


-- ===================== CONSTRAINTS, INDEXES, TRIGGERS, POLICIES =====================


COMMENT ON FUNCTION "public"."cleanup_old_snapshots"("p_days_old" integer, "p_keep_count" integer) IS 'Clean up old snapshots while preserving recent ones';


COMMENT ON TABLE "public"."user_subscriptions" IS 'ユーザーのサブスクリプション状態を管理。Clerk User IDをプライマリキーとして使用。';


COMMENT ON FUNCTION "public"."delete_article_version"("p_version_id" "uuid") IS 'Delete a specific version (cannot delete current version)';


COMMENT ON FUNCTION "public"."get_article_version"("p_version_id" "uuid") IS 'Get details of a specific version';


COMMENT ON FUNCTION "public"."get_article_version_history"("p_article_id" "uuid", "p_limit" integer) IS 'Retrieve version history for an article in reverse chronological order';


COMMENT ON FUNCTION "public"."get_available_snapshots"("p_process_id" "uuid") IS 'Get all snapshots with current position indicator (like git log with HEAD marker)';


COMMENT ON FUNCTION "public"."get_current_article_version"("p_article_id" "uuid") IS 'Get the current version ID for an article';


COMMENT ON FUNCTION "public"."get_snapshot_details"("p_snapshot_id" "uuid") IS 'Get detailed information about a specific snapshot';


COMMENT ON FUNCTION "public"."has_active_access"("p_user_id" "text") IS 'ユーザーがアクティブなアクセス権を持っているかを判定。特権ユーザーまたはアクティブなサブスクリプションでtrue。';


COMMENT ON FUNCTION "public"."migrate_image_to_gcs"("image_id_param" "uuid", "gcs_url_param" "text", "gcs_path_param" "text") IS 'Migrates an existing image record to include GCS information';


COMMENT ON FUNCTION "public"."navigate_to_version"("p_article_id" "uuid", "p_direction" "text") IS 'Navigate to next or previous version without creating a new version';


COMMENT ON FUNCTION "public"."restore_article_version"("p_version_id" "uuid", "p_create_new_version" boolean) IS 'Restore an article to a specific version, optionally creating a new version';


COMMENT ON FUNCTION "public"."restore_from_snapshot"("p_snapshot_id" "uuid", "p_create_new_branch" boolean) IS 'Restore process to a snapshot position (like git checkout) - does NOT create new snapshots';


COMMENT ON FUNCTION "public"."save_article_version"("p_article_id" "uuid", "p_user_id" "text", "p_title" "text", "p_content" "text", "p_change_description" "text", "p_metadata" "jsonb", "p_max_versions" integer) IS 'Save a new version of an article and automatically manage version limits';


COMMENT ON FUNCTION "public"."save_step_snapshot"("p_process_id" "uuid", "p_step_name" "text", "p_article_context" "jsonb", "p_step_description" "text", "p_step_category" "text", "p_snapshot_metadata" "jsonb", "p_branch_id" "uuid") IS 'Save snapshot with proper is_active_branch management - only one active snapshot per branch';


COMMENT ON FUNCTION "public"."switch_to_branch"("p_process_id" "uuid", "p_branch_id" "uuid") IS 'Switch active branch for a process without creating a new branch';


COMMENT ON TABLE "public"."agent_execution_logs" IS '個別エージェントの実行ログと詳細メトリクス';


COMMENT ON TABLE "public"."agent_log_sessions" IS 'マルチエージェントシステムでの記事生成セッション全体のログ';


COMMENT ON TABLE "public"."llm_call_logs" IS 'LLM API呼び出しの詳細ログとトークン使用量';


COMMENT ON TABLE "public"."tool_call_logs" IS '外部ツール（WebSearch、SerpAPIなど）の呼び出しログ';


ALTER TABLE ONLY "public"."article_agent_messages" REPLICA IDENTITY FULL;


COMMENT ON TABLE "public"."article_agent_messages" IS 'Ordered chat messages exchanged within an article agent session';


COMMENT ON COLUMN "public"."article_agent_messages"."sequence" IS 'Monotonic sequence used for chronological ordering';


ALTER TABLE "public"."article_agent_messages" ALTER COLUMN "sequence" ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME "public"."article_agent_messages_sequence_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


ALTER TABLE ONLY "public"."article_agent_sessions" REPLICA IDENTITY FULL;


COMMENT ON TABLE "public"."article_agent_sessions" IS 'Persisted AI editing agent sessions for continuing conversations';


COMMENT ON COLUMN "public"."article_agent_sessions"."session_store_key" IS 'File key for the Agents SDK SQLite session store';


COMMENT ON COLUMN "public"."article_agent_sessions"."original_content" IS 'Article HTML content at the start of the agent session';


COMMENT ON COLUMN "public"."article_agent_sessions"."working_content" IS 'Current working HTML content managed inside the agent session';


ALTER TABLE ONLY "public"."article_edit_versions" REPLICA IDENTITY FULL;


COMMENT ON TABLE "public"."article_edit_versions" IS 'Version history for article edits - tracks all saved versions';


COMMENT ON COLUMN "public"."article_edit_versions"."version_number" IS 'Sequential version number starting from 1';


COMMENT ON COLUMN "public"."article_edit_versions"."change_description" IS 'User-provided or auto-generated description of changes';


COMMENT ON COLUMN "public"."article_edit_versions"."is_current" IS 'Indicates the current active version (HEAD)';


COMMENT ON COLUMN "public"."article_edit_versions"."metadata" IS 'Additional version metadata (word count, character count, etc.)';


ALTER TABLE ONLY "public"."article_generation_step_snapshots" REPLICA IDENTITY FULL;


COMMENT ON TABLE "public"."article_generation_step_snapshots" IS 'Snapshots of article generation process at each step for navigation';


COMMENT ON COLUMN "public"."article_generation_step_snapshots"."step_index" IS 'Index for handling multiple passes through same step (e.g., regeneration)';


COMMENT ON COLUMN "public"."article_generation_step_snapshots"."step_category" IS 'Step category: autonomous, user_input, transition, terminal';


COMMENT ON COLUMN "public"."article_generation_step_snapshots"."article_context" IS 'Complete ArticleContext JSON snapshot';


COMMENT ON COLUMN "public"."article_generation_step_snapshots"."can_restore" IS 'Whether restoration to this step is permitted';


COMMENT ON COLUMN "public"."article_generation_step_snapshots"."branch_id" IS 'Unique identifier for this branch - all snapshots in same branch share this ID';


COMMENT ON COLUMN "public"."article_generation_step_snapshots"."parent_snapshot_id" IS 'The snapshot this branch was created from (null for main branch)';


COMMENT ON COLUMN "public"."article_generation_step_snapshots"."is_active_branch" IS 'Whether this branch is currently active for the process';


COMMENT ON COLUMN "public"."article_generation_step_snapshots"."branch_name" IS 'User-friendly branch name (e.g., "Main", "Persona variant 1")';


ALTER TABLE ONLY "public"."background_tasks" REPLICA IDENTITY FULL;


COMMENT ON TABLE "public"."background_tasks" IS 'Background task queue for article generation processes';


COMMENT ON COLUMN "public"."background_tasks"."depends_on" IS 'Array of task IDs this task depends on';


COMMENT ON COLUMN "public"."background_tasks"."blocks_tasks" IS 'Array of task IDs blocked by this task';


COMMENT ON COLUMN "public"."background_tasks"."resource_usage" IS 'JSON tracking CPU, memory, API calls etc.';


ALTER TABLE ONLY "public"."blog_generation_state" REPLICA IDENTITY FULL;


COMMENT ON TABLE "public"."blog_generation_state" IS 'ブログAI生成プロセスの状態管理';


COMMENT ON COLUMN "public"."blog_generation_state"."blog_context" IS 'エージェントのコンテキストデータ（JSON）';


COMMENT ON COLUMN "public"."blog_generation_state"."uploaded_images" IS 'アップロードされた画像情報の配列';


COMMENT ON COLUMN "public"."blog_generation_state"."response_id" IS 'OpenAI Responses APIのレスポンスID（バックグラウンド実行用）';


ALTER TABLE ONLY "public"."blog_process_events" REPLICA IDENTITY FULL;


COMMENT ON TABLE "public"."blog_process_events" IS 'ブログ生成プロセスのRealtimeイベント';


COMMENT ON TABLE "public"."company_info" IS 'Stores company information for users to use in SEO article generation';


COMMENT ON COLUMN "public"."company_info"."user_id" IS 'Clerk user ID who owns this company information';


COMMENT ON COLUMN "public"."company_info"."name" IS 'Company name';


COMMENT ON COLUMN "public"."company_info"."website_url" IS 'Company website URL';


COMMENT ON COLUMN "public"."company_info"."description" IS 'Company description/overview';


COMMENT ON COLUMN "public"."company_info"."usp" IS 'Unique Selling Proposition - company strengths and differentiators';


COMMENT ON COLUMN "public"."company_info"."target_persona" IS 'Target customer persona (detailed description)';


COMMENT ON COLUMN "public"."company_info"."is_default" IS 'Whether this is the default company for the user';


COMMENT ON COLUMN "public"."company_info"."brand_slogan" IS 'Brand slogan or catchphrase (optional)';


COMMENT ON COLUMN "public"."company_info"."target_keywords" IS 'Keywords for SEO targeting (optional)';


COMMENT ON COLUMN "public"."company_info"."industry_terms" IS 'Industry-specific terms to use (optional)';


COMMENT ON COLUMN "public"."company_info"."avoid_terms" IS 'Terms to avoid in content (optional)';


COMMENT ON COLUMN "public"."company_info"."popular_articles" IS 'Popular article titles/URLs for reference (optional)';


COMMENT ON COLUMN "public"."company_info"."target_area" IS 'Target geographic area or local keywords (optional)';


ALTER TABLE ONLY "public"."generated_articles_state" REPLICA IDENTITY FULL;


COMMENT ON TABLE "public"."generated_articles_state" IS 'Article generation state table (SSE event logging rolled back)';


COMMENT ON COLUMN "public"."generated_articles_state"."flow_id" IS 'Optional flow ID for flow-based generation. NULL for traditional generation.';


COMMENT ON COLUMN "public"."generated_articles_state"."current_step_name" IS 'Human-readable name of the current step';


COMMENT ON COLUMN "public"."generated_articles_state"."progress_percentage" IS 'Overall progress percentage (0-100)';


COMMENT ON COLUMN "public"."generated_articles_state"."is_waiting_for_input" IS 'Whether the process is waiting for user input';


COMMENT ON COLUMN "public"."generated_articles_state"."input_type" IS 'Type of input required (select_persona, approve_plan, etc.)';


COMMENT ON COLUMN "public"."generated_articles_state"."last_activity_at" IS 'Timestamp of last activity on this process';


COMMENT ON COLUMN "public"."generated_articles_state"."auto_resume_eligible" IS 'Whether this process can be automatically resumed';


COMMENT ON COLUMN "public"."generated_articles_state"."resume_from_step" IS 'Step to resume from when restarting';


COMMENT ON COLUMN "public"."generated_articles_state"."step_history" IS 'Array of completed steps with timestamps and data';


COMMENT ON COLUMN "public"."generated_articles_state"."process_metadata" IS 'Additional metadata for the process (research progress, etc.)';


COMMENT ON COLUMN "public"."generated_articles_state"."image_mode" IS 'Whether this generation process includes image placeholders';


COMMENT ON COLUMN "public"."generated_articles_state"."image_settings" IS 'Image generation settings and preferences';


COMMENT ON COLUMN "public"."generated_articles_state"."realtime_channel" IS 'Supabase Realtime channel name for this process';


COMMENT ON COLUMN "public"."generated_articles_state"."executing_step" IS 'Currently executing step (may differ from current_step_name)';


COMMENT ON COLUMN "public"."generated_articles_state"."background_task_id" IS 'ID of the background task processing this step';


COMMENT ON COLUMN "public"."generated_articles_state"."user_input_timeout" IS 'When user input request expires';


COMMENT ON COLUMN "public"."generated_articles_state"."interaction_history" IS 'History of user interactions with this process';


COMMENT ON COLUMN "public"."generated_articles_state"."current_snapshot_id" IS 'Current snapshot position (like git HEAD) - shows which snapshot the process is currently at';


COMMENT ON TABLE "public"."image_placeholders" IS 'Tracks image placeholders in articles before they are replaced with actual images';


COMMENT ON TABLE "public"."images" IS 'Stores uploaded and generated images for articles';


COMMENT ON COLUMN "public"."images"."gcs_url" IS 'Public URL for image stored in Google Cloud Storage';


COMMENT ON COLUMN "public"."images"."gcs_path" IS 'Path within GCS bucket (e.g., images/2025/06/25/filename.jpg)';


COMMENT ON COLUMN "public"."images"."storage_type" IS 'Storage location: local, gcs, or hybrid (both)';


ALTER TABLE ONLY "public"."process_events" REPLICA IDENTITY FULL;


COMMENT ON TABLE "public"."process_events" IS 'Real-time events for article generation processes';


COMMENT ON COLUMN "public"."process_events"."event_sequence" IS 'Sequential number ensuring event order per process';


COMMENT ON COLUMN "public"."process_events"."acknowledged_by" IS 'Array of user IDs who have acknowledged this event';


COMMENT ON COLUMN "public"."process_events"."delivery_attempts" IS 'Number of times event delivery was attempted';


COMMENT ON COLUMN "public"."process_events"."expires_at" IS 'When this event should be cleaned up';


COMMENT ON TABLE "public"."style_guide_templates" IS 'Store reusable style guide templates for article generation';


COMMENT ON COLUMN "public"."style_guide_templates"."template_type" IS 'Category of the style template for organization';


COMMENT ON COLUMN "public"."style_guide_templates"."settings" IS 'JSON object containing style guide configuration (tone, vocabulary, structure, etc.)';


COMMENT ON COLUMN "public"."style_guide_templates"."is_default" IS 'Whether this template is the default for the user/organization';


COMMENT ON TABLE "public"."subscription_events" IS 'サブスクリプション関連イベントの監査ログ。Stripe Webhookイベントの重複防止にも使用。';


COMMENT ON TABLE "public"."wordpress_sites" IS 'WordPress MCP連携サイト情報';


COMMENT ON COLUMN "public"."wordpress_sites"."encrypted_credentials" IS 'AES-256-GCMで暗号化されたMCP認証情報（access_token, api_key, api_secret）';


COMMENT ON COLUMN "public"."wordpress_sites"."connection_status" IS '接続状態: connected, disconnected, error';


COMMENT ON COLUMN "public"."wordpress_sites"."is_active" IS '現在アクティブなサイト（複数サイト対応時に使用）';


COMMENT ON TABLE "public"."workflow_step_logs" IS 'ワークフローの各ステップの実行状況';


ALTER TABLE ONLY "public"."agent_execution_logs"
    ADD CONSTRAINT "agent_execution_logs_pkey" PRIMARY KEY ("id");


ALTER TABLE ONLY "public"."agent_log_sessions"
    ADD CONSTRAINT "agent_log_sessions_pkey" PRIMARY KEY ("id");


ALTER TABLE ONLY "public"."article_agent_messages"
    ADD CONSTRAINT "article_agent_messages_pkey" PRIMARY KEY ("id");


ALTER TABLE ONLY "public"."article_agent_sessions"
    ADD CONSTRAINT "article_agent_sessions_pkey" PRIMARY KEY ("id");


ALTER TABLE ONLY "public"."article_edit_versions"
    ADD CONSTRAINT "article_edit_versions_pkey" PRIMARY KEY ("id");


ALTER TABLE ONLY "public"."article_generation_flows"
    ADD CONSTRAINT "article_generation_flows_pkey" PRIMARY KEY ("id");


ALTER TABLE ONLY "public"."article_generation_step_snapshots"
    ADD CONSTRAINT "article_generation_step_snapshots_pkey" PRIMARY KEY ("id");


ALTER TABLE ONLY "public"."articles"
    ADD CONSTRAINT "articles_pkey" PRIMARY KEY ("id");


ALTER TABLE ONLY "public"."background_tasks"
    ADD CONSTRAINT "background_tasks_pkey" PRIMARY KEY ("id");


ALTER TABLE ONLY "public"."blog_generation_state"
    ADD CONSTRAINT "blog_generation_state_pkey" PRIMARY KEY ("id");


ALTER TABLE ONLY "public"."blog_process_events"
    ADD CONSTRAINT "blog_process_events_pkey" PRIMARY KEY ("id");


ALTER TABLE ONLY "public"."company_info"
    ADD CONSTRAINT "company_info_pkey" PRIMARY KEY ("id");


ALTER TABLE ONLY "public"."flow_steps"
    ADD CONSTRAINT "flow_steps_flow_id_step_order_key" UNIQUE ("flow_id", "step_order");


ALTER TABLE ONLY "public"."flow_steps"
    ADD CONSTRAINT "flow_steps_pkey" PRIMARY KEY ("id");


ALTER TABLE ONLY "public"."generated_articles_state"
    ADD CONSTRAINT "generated_articles_state_pkey" PRIMARY KEY ("id");


ALTER TABLE ONLY "public"."image_placeholders"
    ADD CONSTRAINT "image_placeholders_article_id_placeholder_id_key" UNIQUE ("article_id", "placeholder_id");


ALTER TABLE ONLY "public"."image_placeholders"
    ADD CONSTRAINT "image_placeholders_pkey" PRIMARY KEY ("id");


ALTER TABLE ONLY "public"."images"
    ADD CONSTRAINT "images_pkey" PRIMARY KEY ("id");


ALTER TABLE ONLY "public"."invitations"
    ADD CONSTRAINT "invitations_pkey" PRIMARY KEY ("id");


ALTER TABLE ONLY "public"."invitations"
    ADD CONSTRAINT "invitations_token_key" UNIQUE ("token");


ALTER TABLE ONLY "public"."llm_call_logs"
    ADD CONSTRAINT "llm_call_logs_pkey" PRIMARY KEY ("id");


ALTER TABLE ONLY "public"."organization_members"
    ADD CONSTRAINT "organization_members_pkey" PRIMARY KEY ("organization_id", "user_id");


ALTER TABLE ONLY "public"."organization_subscriptions"
    ADD CONSTRAINT "organization_subscriptions_pkey" PRIMARY KEY ("id");


ALTER TABLE ONLY "public"."organizations"
    ADD CONSTRAINT "organizations_clerk_organization_id_key" UNIQUE ("clerk_organization_id");


ALTER TABLE ONLY "public"."organizations"
    ADD CONSTRAINT "organizations_pkey" PRIMARY KEY ("id");


ALTER TABLE ONLY "public"."plan_tiers"
    ADD CONSTRAINT "plan_tiers_pkey" PRIMARY KEY ("id");


ALTER TABLE ONLY "public"."process_events"
    ADD CONSTRAINT "process_events_pkey" PRIMARY KEY ("id");


ALTER TABLE ONLY "public"."style_guide_templates"
    ADD CONSTRAINT "style_guide_templates_pkey" PRIMARY KEY ("id");


ALTER TABLE ONLY "public"."subscription_events"
    ADD CONSTRAINT "subscription_events_pkey" PRIMARY KEY ("id");


ALTER TABLE ONLY "public"."tool_call_logs"
    ADD CONSTRAINT "tool_call_logs_pkey" PRIMARY KEY ("id");


ALTER TABLE ONLY "public"."article_edit_versions"
    ADD CONSTRAINT "unique_article_version" UNIQUE ("article_id", "version_number");


ALTER TABLE ONLY "public"."process_events"
    ADD CONSTRAINT "unique_process_sequence" UNIQUE ("process_id", "event_sequence");


ALTER TABLE ONLY "public"."article_generation_step_snapshots"
    ADD CONSTRAINT "unique_process_step_branch" UNIQUE ("process_id", "step_name", "step_index", "branch_id");


COMMENT ON CONSTRAINT "unique_process_step_branch" ON "public"."article_generation_step_snapshots" IS 'Ensures one snapshot per process/step/index/branch combination, allowing different branches to have same step';


ALTER TABLE ONLY "public"."wordpress_sites"
    ADD CONSTRAINT "unique_site_per_user" UNIQUE ("user_id", "site_url");


ALTER TABLE ONLY "public"."usage_tracking"
    ADD CONSTRAINT "uq_usage_org_period" UNIQUE ("organization_id", "billing_period_start");


ALTER TABLE ONLY "public"."usage_tracking"
    ADD CONSTRAINT "uq_usage_user_period" UNIQUE ("user_id", "billing_period_start");


ALTER TABLE ONLY "public"."usage_logs"
    ADD CONSTRAINT "usage_logs_pkey" PRIMARY KEY ("id");


ALTER TABLE ONLY "public"."usage_tracking"
    ADD CONSTRAINT "usage_tracking_pkey" PRIMARY KEY ("id");


ALTER TABLE ONLY "public"."user_subscriptions"
    ADD CONSTRAINT "user_subscriptions_pkey" PRIMARY KEY ("user_id");


ALTER TABLE ONLY "public"."user_subscriptions"
    ADD CONSTRAINT "user_subscriptions_stripe_customer_id_key" UNIQUE ("stripe_customer_id");


ALTER TABLE ONLY "public"."user_subscriptions"
    ADD CONSTRAINT "user_subscriptions_stripe_subscription_id_key" UNIQUE ("stripe_subscription_id");


ALTER TABLE ONLY "public"."wordpress_sites"
    ADD CONSTRAINT "wordpress_sites_pkey" PRIMARY KEY ("id");


ALTER TABLE ONLY "public"."workflow_step_logs"
    ADD CONSTRAINT "workflow_step_logs_pkey" PRIMARY KEY ("id");


CREATE INDEX "idx_active_processes" ON "public"."generated_articles_state" USING "btree" ("id", "status", "updated_at") WHERE ("status" = ANY (ARRAY['in_progress'::"public"."generation_status", 'user_input_required'::"public"."generation_status", 'paused'::"public"."generation_status"]));


CREATE INDEX "idx_agent_execution_logs_agent_type" ON "public"."agent_execution_logs" USING "btree" ("agent_type");


CREATE INDEX "idx_agent_execution_logs_session_id" ON "public"."agent_execution_logs" USING "btree" ("session_id");


CREATE INDEX "idx_agent_execution_logs_started_at" ON "public"."agent_execution_logs" USING "btree" ("started_at");


CREATE INDEX "idx_agent_execution_logs_status" ON "public"."agent_execution_logs" USING "btree" ("status");


CREATE INDEX "idx_agent_log_sessions_article_uuid" ON "public"."agent_log_sessions" USING "btree" ("article_uuid");


CREATE INDEX "idx_agent_log_sessions_created_at" ON "public"."agent_log_sessions" USING "btree" ("created_at");


CREATE INDEX "idx_agent_log_sessions_status" ON "public"."agent_log_sessions" USING "btree" ("status");


CREATE INDEX "idx_agent_log_sessions_user_org" ON "public"."agent_log_sessions" USING "btree" ("user_id", "organization_id");


CREATE INDEX "idx_article_agent_messages_sequence" ON "public"."article_agent_messages" USING "btree" ("session_id", "sequence");


CREATE INDEX "idx_article_agent_messages_session" ON "public"."article_agent_messages" USING "btree" ("session_id");


CREATE UNIQUE INDEX "idx_article_agent_sessions_active" ON "public"."article_agent_sessions" USING "btree" ("article_id", "user_id") WHERE ("status" = 'active'::"text");


CREATE INDEX "idx_article_agent_sessions_user_article" ON "public"."article_agent_sessions" USING "btree" ("user_id", "article_id");


CREATE INDEX "idx_article_versions_article_created" ON "public"."article_edit_versions" USING "btree" ("article_id", "created_at" DESC);


CREATE INDEX "idx_article_versions_article_id" ON "public"."article_edit_versions" USING "btree" ("article_id");


CREATE INDEX "idx_article_versions_article_version" ON "public"."article_edit_versions" USING "btree" ("article_id", "version_number" DESC);


CREATE INDEX "idx_article_versions_created_at" ON "public"."article_edit_versions" USING "btree" ("created_at" DESC);


CREATE INDEX "idx_article_versions_is_current" ON "public"."article_edit_versions" USING "btree" ("article_id", "is_current") WHERE ("is_current" = true);


CREATE INDEX "idx_article_versions_user" ON "public"."article_edit_versions" USING "btree" ("user_id");


CREATE INDEX "idx_articles_content_length" ON "public"."articles" USING "btree" ("generation_process_id", "length"("content") DESC) WHERE ("generation_process_id" IS NOT NULL);


CREATE INDEX "idx_articles_generation_process_id_updated_at" ON "public"."articles" USING "btree" ("generation_process_id", "updated_at" DESC) WHERE ("generation_process_id" IS NOT NULL);


CREATE INDEX "idx_background_tasks_priority_status" ON "public"."background_tasks" USING "btree" ("priority" DESC, "status");


CREATE INDEX "idx_background_tasks_process_id" ON "public"."background_tasks" USING "btree" ("process_id");


CREATE INDEX "idx_background_tasks_retry" ON "public"."background_tasks" USING "btree" ("retry_count", "max_retries") WHERE (("status" = 'failed'::"text") AND ("retry_count" < "max_retries"));


CREATE INDEX "idx_background_tasks_scheduled" ON "public"."background_tasks" USING "btree" ("scheduled_for") WHERE ("status" = ANY (ARRAY['pending'::"text", 'paused'::"text"]));


CREATE INDEX "idx_background_tasks_status" ON "public"."background_tasks" USING "btree" ("status");


CREATE INDEX "idx_background_tasks_type" ON "public"."background_tasks" USING "btree" ("task_type");


CREATE INDEX "idx_background_tasks_worker" ON "public"."background_tasks" USING "btree" ("worker_id") WHERE ("worker_id" IS NOT NULL);


CREATE INDEX "idx_blog_generation_active" ON "public"."blog_generation_state" USING "btree" ("id", "status", "updated_at") WHERE ("status" = ANY (ARRAY['in_progress'::"text", 'user_input_required'::"text", 'pending'::"text"]));


CREATE INDEX "idx_blog_generation_channel" ON "public"."blog_generation_state" USING "btree" ("realtime_channel");


CREATE INDEX "idx_blog_generation_response_id" ON "public"."blog_generation_state" USING "btree" ("response_id");


CREATE INDEX "idx_blog_generation_site" ON "public"."blog_generation_state" USING "btree" ("wordpress_site_id");


CREATE INDEX "idx_blog_generation_status" ON "public"."blog_generation_state" USING "btree" ("status");


CREATE INDEX "idx_blog_generation_user" ON "public"."blog_generation_state" USING "btree" ("user_id");


CREATE INDEX "idx_blog_process_events_created" ON "public"."blog_process_events" USING "btree" ("created_at" DESC);


CREATE INDEX "idx_blog_process_events_process" ON "public"."blog_process_events" USING "btree" ("process_id", "event_sequence");


CREATE INDEX "idx_blog_process_events_user" ON "public"."blog_process_events" USING "btree" ("user_id");


CREATE INDEX "idx_company_info_user_default" ON "public"."company_info" USING "btree" ("user_id", "is_default");


CREATE INDEX "idx_company_info_user_id" ON "public"."company_info" USING "btree" ("user_id");


CREATE INDEX "idx_events_cleanup" ON "public"."process_events" USING "btree" ("created_at", "archived") WHERE ("archived" = false);


CREATE INDEX "idx_generated_articles_current_snapshot" ON "public"."generated_articles_state" USING "btree" ("current_snapshot_id");


CREATE INDEX "idx_generated_articles_state_background_task" ON "public"."generated_articles_state" USING "btree" ("background_task_id") WHERE ("background_task_id" IS NOT NULL);


CREATE INDEX "idx_generated_articles_state_executing_step" ON "public"."generated_articles_state" USING "btree" ("executing_step") WHERE ("executing_step" IS NOT NULL);


CREATE INDEX "idx_generated_articles_state_last_activity" ON "public"."generated_articles_state" USING "btree" ("last_activity_at" DESC);


CREATE INDEX "idx_generated_articles_state_process_type" ON "public"."generated_articles_state" USING "btree" ("process_type");


CREATE INDEX "idx_generated_articles_state_realtime_channel" ON "public"."generated_articles_state" USING "btree" ("realtime_channel");


CREATE INDEX "idx_generated_articles_state_status" ON "public"."generated_articles_state" USING "btree" ("status");


CREATE INDEX "idx_generated_articles_state_style_template" ON "public"."generated_articles_state" USING "btree" ("style_template_id");


CREATE INDEX "idx_generated_articles_state_user_input_timeout" ON "public"."generated_articles_state" USING "btree" ("user_input_timeout") WHERE ("user_input_timeout" IS NOT NULL);


CREATE INDEX "idx_generated_articles_state_user_status" ON "public"."generated_articles_state" USING "btree" ("user_id", "status");


CREATE INDEX "idx_image_placeholders_article_id" ON "public"."image_placeholders" USING "btree" ("article_id");


CREATE INDEX "idx_image_placeholders_generation_process_id" ON "public"."image_placeholders" USING "btree" ("generation_process_id");


CREATE INDEX "idx_image_placeholders_status" ON "public"."image_placeholders" USING "btree" ("status");


CREATE INDEX "idx_images_article_id" ON "public"."images" USING "btree" ("article_id");


CREATE INDEX "idx_images_gcs_path" ON "public"."images" USING "btree" ("gcs_path") WHERE ("gcs_path" IS NOT NULL);


CREATE INDEX "idx_images_generation_process_id" ON "public"."images" USING "btree" ("generation_process_id");


CREATE INDEX "idx_images_image_type" ON "public"."images" USING "btree" ("image_type");


CREATE INDEX "idx_images_storage_type" ON "public"."images" USING "btree" ("storage_type");


CREATE INDEX "idx_images_user_id" ON "public"."images" USING "btree" ("user_id");


CREATE INDEX "idx_llm_call_logs_called_at" ON "public"."llm_call_logs" USING "btree" ("called_at");


CREATE INDEX "idx_llm_call_logs_execution_id" ON "public"."llm_call_logs" USING "btree" ("execution_id");


CREATE INDEX "idx_llm_call_logs_model_name" ON "public"."llm_call_logs" USING "btree" ("model_name");


CREATE INDEX "idx_organizations_clerk_org_id" ON "public"."organizations" USING "btree" ("clerk_organization_id");


CREATE INDEX "idx_process_events_category" ON "public"."process_events" USING "btree" ("event_category");


CREATE INDEX "idx_process_events_created_at" ON "public"."process_events" USING "btree" ("created_at" DESC);


CREATE INDEX "idx_process_events_process_id" ON "public"."process_events" USING "btree" ("process_id");


CREATE INDEX "idx_process_events_published" ON "public"."process_events" USING "btree" ("published_at" DESC) WHERE ("published_at" IS NOT NULL);


CREATE INDEX "idx_process_events_type" ON "public"."process_events" USING "btree" ("event_type");


CREATE INDEX "idx_process_events_undelivered" ON "public"."process_events" USING "btree" ("process_id", "event_sequence") WHERE (("delivery_attempts" < 3) AND ("acknowledged_by" = '{}'::"text"[]));


CREATE INDEX "idx_recent_events" ON "public"."process_events" USING "btree" ("process_id", "event_sequence" DESC, "created_at" DESC);


CREATE INDEX "idx_snapshots_active_branch" ON "public"."article_generation_step_snapshots" USING "btree" ("process_id", "is_active_branch") WHERE ("is_active_branch" = true);


CREATE INDEX "idx_snapshots_branch_id" ON "public"."article_generation_step_snapshots" USING "btree" ("branch_id");


CREATE INDEX "idx_snapshots_parent_snapshot" ON "public"."article_generation_step_snapshots" USING "btree" ("parent_snapshot_id");


CREATE INDEX "idx_snapshots_process_branch" ON "public"."article_generation_step_snapshots" USING "btree" ("process_id", "branch_id");


CREATE INDEX "idx_step_snapshots_can_restore" ON "public"."article_generation_step_snapshots" USING "btree" ("can_restore") WHERE ("can_restore" = true);


CREATE INDEX "idx_step_snapshots_category" ON "public"."article_generation_step_snapshots" USING "btree" ("step_category");


CREATE INDEX "idx_step_snapshots_created_at" ON "public"."article_generation_step_snapshots" USING "btree" ("created_at" DESC);


CREATE INDEX "idx_step_snapshots_process_created" ON "public"."article_generation_step_snapshots" USING "btree" ("process_id", "created_at" DESC);


CREATE INDEX "idx_step_snapshots_process_id" ON "public"."article_generation_step_snapshots" USING "btree" ("process_id");


CREATE INDEX "idx_step_snapshots_step_name" ON "public"."article_generation_step_snapshots" USING "btree" ("step_name");


CREATE INDEX "idx_style_guide_templates_active" ON "public"."style_guide_templates" USING "btree" ("is_active") WHERE ("is_active" = true);


CREATE INDEX "idx_style_guide_templates_org_id" ON "public"."style_guide_templates" USING "btree" ("organization_id");


CREATE INDEX "idx_style_guide_templates_user_id" ON "public"."style_guide_templates" USING "btree" ("user_id");


CREATE UNIQUE INDEX "idx_subscription_events_stripe_event_id" ON "public"."subscription_events" USING "btree" ("stripe_event_id") WHERE ("stripe_event_id" IS NOT NULL);


CREATE INDEX "idx_subscription_events_user_id" ON "public"."subscription_events" USING "btree" ("user_id");


CREATE INDEX "idx_task_queue" ON "public"."background_tasks" USING "btree" ("status", "priority" DESC, "scheduled_for") WHERE ("status" = ANY (ARRAY['pending'::"text", 'running'::"text"]));


CREATE INDEX "idx_tool_call_logs_called_at" ON "public"."tool_call_logs" USING "btree" ("called_at");


CREATE INDEX "idx_tool_call_logs_execution_id" ON "public"."tool_call_logs" USING "btree" ("execution_id");


CREATE INDEX "idx_tool_call_logs_tool_name" ON "public"."tool_call_logs" USING "btree" ("tool_name");


CREATE INDEX "idx_usage_logs_created" ON "public"."usage_logs" USING "btree" ("created_at" DESC);


CREATE INDEX "idx_usage_logs_tracking" ON "public"."usage_logs" USING "btree" ("usage_tracking_id");


CREATE INDEX "idx_usage_tracking_org_period" ON "public"."usage_tracking" USING "btree" ("organization_id", "billing_period_end" DESC) WHERE ("organization_id" IS NOT NULL);


CREATE INDEX "idx_usage_tracking_user_period" ON "public"."usage_tracking" USING "btree" ("user_id", "billing_period_end" DESC) WHERE ("user_id" IS NOT NULL);


CREATE INDEX "idx_wordpress_sites_org" ON "public"."wordpress_sites" USING "btree" ("organization_id");


CREATE INDEX "idx_wordpress_sites_status" ON "public"."wordpress_sites" USING "btree" ("connection_status");


CREATE INDEX "idx_wordpress_sites_user_id" ON "public"."wordpress_sites" USING "btree" ("user_id");


CREATE INDEX "idx_workflow_step_logs_session_id" ON "public"."workflow_step_logs" USING "btree" ("session_id");


CREATE INDEX "idx_workflow_step_logs_step_type" ON "public"."workflow_step_logs" USING "btree" ("step_type");


CREATE UNIQUE INDEX "unique_generation_process_id" ON "public"."articles" USING "btree" ("generation_process_id") WHERE ("generation_process_id" IS NOT NULL);


COMMENT ON INDEX "public"."unique_generation_process_id" IS 'Ensures only one article per generation process to prevent duplicates';


CREATE OR REPLACE TRIGGER "ensure_single_default_style_template_trigger" BEFORE INSERT OR UPDATE ON "public"."style_guide_templates" FOR EACH ROW WHEN (("new"."is_default" = true)) EXECUTE FUNCTION "public"."ensure_single_default_style_template"();


CREATE OR REPLACE TRIGGER "on_organization_created" AFTER INSERT ON "public"."organizations" FOR EACH ROW EXECUTE FUNCTION "public"."handle_new_organization"();


CREATE OR REPLACE TRIGGER "trigger_blog_generation_state_updated_at" BEFORE UPDATE ON "public"."blog_generation_state" FOR EACH ROW EXECUTE FUNCTION "public"."update_blog_generation_state_updated_at"();


CREATE OR REPLACE TRIGGER "trigger_publish_process_event" AFTER INSERT OR UPDATE ON "public"."generated_articles_state" FOR EACH ROW EXECUTE FUNCTION "public"."publish_process_event"();


CREATE OR REPLACE TRIGGER "trigger_set_realtime_channel" BEFORE INSERT ON "public"."generated_articles_state" FOR EACH ROW EXECUTE FUNCTION "public"."set_realtime_channel"();


CREATE OR REPLACE TRIGGER "trigger_update_article_image_urls" AFTER UPDATE ON "public"."images" FOR EACH ROW EXECUTE FUNCTION "public"."update_article_image_urls"();


CREATE OR REPLACE TRIGGER "trigger_update_last_activity" BEFORE UPDATE ON "public"."generated_articles_state" FOR EACH ROW EXECUTE FUNCTION "public"."update_last_activity"();


CREATE OR REPLACE TRIGGER "trigger_update_task_status" BEFORE INSERT OR UPDATE ON "public"."background_tasks" FOR EACH ROW EXECUTE FUNCTION "public"."update_task_status"();


CREATE OR REPLACE TRIGGER "trigger_update_user_subscriptions_updated_at" BEFORE UPDATE ON "public"."user_subscriptions" FOR EACH ROW EXECUTE FUNCTION "public"."update_user_subscriptions_updated_at"();


CREATE OR REPLACE TRIGGER "trigger_wordpress_sites_updated_at" BEFORE UPDATE ON "public"."wordpress_sites" FOR EACH ROW EXECUTE FUNCTION "public"."update_wordpress_sites_updated_at"();


CREATE OR REPLACE TRIGGER "update_agent_log_sessions_timestamp" BEFORE UPDATE ON "public"."agent_log_sessions" FOR EACH ROW EXECUTE FUNCTION "public"."update_agent_log_sessions_timestamp"();


CREATE OR REPLACE TRIGGER "update_article_agent_sessions_updated_at" BEFORE UPDATE ON "public"."article_agent_sessions" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();


CREATE OR REPLACE TRIGGER "update_article_generation_flows_updated_at" BEFORE UPDATE ON "public"."article_generation_flows" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();


CREATE OR REPLACE TRIGGER "update_articles_updated_at" BEFORE UPDATE ON "public"."articles" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();


CREATE OR REPLACE TRIGGER "update_company_info_updated_at" BEFORE UPDATE ON "public"."company_info" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();


CREATE OR REPLACE TRIGGER "update_generated_articles_state_updated_at" BEFORE UPDATE ON "public"."generated_articles_state" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();


CREATE OR REPLACE TRIGGER "update_image_placeholders_updated_at" BEFORE UPDATE ON "public"."image_placeholders" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();


CREATE OR REPLACE TRIGGER "update_images_updated_at" BEFORE UPDATE ON "public"."images" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();


CREATE OR REPLACE TRIGGER "update_organizations_updated_at" BEFORE UPDATE ON "public"."organizations" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();


CREATE OR REPLACE TRIGGER "update_style_guide_templates_updated_at" BEFORE UPDATE ON "public"."style_guide_templates" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();


ALTER TABLE ONLY "public"."agent_execution_logs"
    ADD CONSTRAINT "agent_execution_logs_session_id_fkey" FOREIGN KEY ("session_id") REFERENCES "public"."agent_log_sessions"("id") ON DELETE CASCADE;


ALTER TABLE ONLY "public"."article_agent_messages"
    ADD CONSTRAINT "article_agent_messages_session_id_fkey" FOREIGN KEY ("session_id") REFERENCES "public"."article_agent_sessions"("id") ON DELETE CASCADE;


ALTER TABLE ONLY "public"."article_agent_sessions"
    ADD CONSTRAINT "article_agent_sessions_article_id_fkey" FOREIGN KEY ("article_id") REFERENCES "public"."articles"("id") ON DELETE CASCADE;


ALTER TABLE ONLY "public"."article_agent_sessions"
    ADD CONSTRAINT "article_agent_sessions_organization_id_fkey" FOREIGN KEY ("organization_id") REFERENCES "public"."organizations"("id") ON DELETE CASCADE;


ALTER TABLE ONLY "public"."article_edit_versions"
    ADD CONSTRAINT "article_edit_versions_article_id_fkey" FOREIGN KEY ("article_id") REFERENCES "public"."articles"("id") ON DELETE CASCADE;


ALTER TABLE ONLY "public"."article_generation_flows"
    ADD CONSTRAINT "article_generation_flows_organization_id_fkey" FOREIGN KEY ("organization_id") REFERENCES "public"."organizations"("id") ON DELETE CASCADE;


ALTER TABLE ONLY "public"."article_generation_step_snapshots"
    ADD CONSTRAINT "article_generation_step_snapshots_parent_snapshot_id_fkey" FOREIGN KEY ("parent_snapshot_id") REFERENCES "public"."article_generation_step_snapshots"("id") ON DELETE SET NULL;


ALTER TABLE ONLY "public"."article_generation_step_snapshots"
    ADD CONSTRAINT "article_generation_step_snapshots_process_id_fkey" FOREIGN KEY ("process_id") REFERENCES "public"."generated_articles_state"("id") ON DELETE CASCADE;


ALTER TABLE ONLY "public"."articles"
    ADD CONSTRAINT "articles_generation_process_id_fkey" FOREIGN KEY ("generation_process_id") REFERENCES "public"."generated_articles_state"("id");


ALTER TABLE ONLY "public"."articles"
    ADD CONSTRAINT "articles_organization_id_fkey" FOREIGN KEY ("organization_id") REFERENCES "public"."organizations"("id");


ALTER TABLE ONLY "public"."background_tasks"
    ADD CONSTRAINT "background_tasks_process_id_fkey" FOREIGN KEY ("process_id") REFERENCES "public"."generated_articles_state"("id") ON DELETE CASCADE;


ALTER TABLE ONLY "public"."blog_generation_state"
    ADD CONSTRAINT "blog_generation_state_organization_id_fkey" FOREIGN KEY ("organization_id") REFERENCES "public"."organizations"("id") ON DELETE SET NULL;


ALTER TABLE ONLY "public"."blog_generation_state"
    ADD CONSTRAINT "blog_generation_state_wordpress_site_id_fkey" FOREIGN KEY ("wordpress_site_id") REFERENCES "public"."wordpress_sites"("id") ON DELETE SET NULL;


ALTER TABLE ONLY "public"."blog_process_events"
    ADD CONSTRAINT "blog_process_events_process_id_fkey" FOREIGN KEY ("process_id") REFERENCES "public"."blog_generation_state"("id") ON DELETE CASCADE;


ALTER TABLE ONLY "public"."flow_steps"
    ADD CONSTRAINT "flow_steps_flow_id_fkey" FOREIGN KEY ("flow_id") REFERENCES "public"."article_generation_flows"("id") ON DELETE CASCADE;


ALTER TABLE ONLY "public"."generated_articles_state"
    ADD CONSTRAINT "generated_articles_state_current_snapshot_id_fkey" FOREIGN KEY ("current_snapshot_id") REFERENCES "public"."article_generation_step_snapshots"("id") ON DELETE SET NULL;


ALTER TABLE ONLY "public"."generated_articles_state"
    ADD CONSTRAINT "generated_articles_state_current_step_id_fkey" FOREIGN KEY ("current_step_id") REFERENCES "public"."flow_steps"("id");


ALTER TABLE ONLY "public"."generated_articles_state"
    ADD CONSTRAINT "generated_articles_state_flow_id_fkey" FOREIGN KEY ("flow_id") REFERENCES "public"."article_generation_flows"("id") ON DELETE CASCADE;


ALTER TABLE ONLY "public"."generated_articles_state"
    ADD CONSTRAINT "generated_articles_state_organization_id_fkey" FOREIGN KEY ("organization_id") REFERENCES "public"."organizations"("id");


ALTER TABLE ONLY "public"."generated_articles_state"
    ADD CONSTRAINT "generated_articles_state_parent_process_id_fkey" FOREIGN KEY ("parent_process_id") REFERENCES "public"."generated_articles_state"("id");


ALTER TABLE ONLY "public"."generated_articles_state"
    ADD CONSTRAINT "generated_articles_state_style_template_id_fkey" FOREIGN KEY ("style_template_id") REFERENCES "public"."style_guide_templates"("id");


ALTER TABLE ONLY "public"."image_placeholders"
    ADD CONSTRAINT "image_placeholders_article_id_fkey" FOREIGN KEY ("article_id") REFERENCES "public"."articles"("id");


ALTER TABLE ONLY "public"."image_placeholders"
    ADD CONSTRAINT "image_placeholders_generation_process_id_fkey" FOREIGN KEY ("generation_process_id") REFERENCES "public"."generated_articles_state"("id");


ALTER TABLE ONLY "public"."image_placeholders"
    ADD CONSTRAINT "image_placeholders_replaced_with_image_id_fkey" FOREIGN KEY ("replaced_with_image_id") REFERENCES "public"."images"("id");


ALTER TABLE ONLY "public"."images"
    ADD CONSTRAINT "images_article_id_fkey" FOREIGN KEY ("article_id") REFERENCES "public"."articles"("id");


ALTER TABLE ONLY "public"."images"
    ADD CONSTRAINT "images_generation_process_id_fkey" FOREIGN KEY ("generation_process_id") REFERENCES "public"."generated_articles_state"("id");


ALTER TABLE ONLY "public"."images"
    ADD CONSTRAINT "images_organization_id_fkey" FOREIGN KEY ("organization_id") REFERENCES "public"."organizations"("id");


ALTER TABLE ONLY "public"."invitations"
    ADD CONSTRAINT "invitations_organization_id_fkey" FOREIGN KEY ("organization_id") REFERENCES "public"."organizations"("id") ON DELETE CASCADE;


ALTER TABLE ONLY "public"."llm_call_logs"
    ADD CONSTRAINT "llm_call_logs_execution_id_fkey" FOREIGN KEY ("execution_id") REFERENCES "public"."agent_execution_logs"("id") ON DELETE CASCADE;


ALTER TABLE ONLY "public"."organization_members"
    ADD CONSTRAINT "organization_members_organization_id_fkey" FOREIGN KEY ("organization_id") REFERENCES "public"."organizations"("id") ON DELETE CASCADE;


ALTER TABLE ONLY "public"."organization_subscriptions"
    ADD CONSTRAINT "organization_subscriptions_organization_id_fkey" FOREIGN KEY ("organization_id") REFERENCES "public"."organizations"("id") ON DELETE CASCADE;


ALTER TABLE ONLY "public"."organization_subscriptions"
    ADD CONSTRAINT "organization_subscriptions_plan_tier_id_fkey" FOREIGN KEY ("plan_tier_id") REFERENCES "public"."plan_tiers"("id");


ALTER TABLE ONLY "public"."process_events"
    ADD CONSTRAINT "process_events_process_id_fkey" FOREIGN KEY ("process_id") REFERENCES "public"."generated_articles_state"("id") ON DELETE CASCADE;


ALTER TABLE ONLY "public"."style_guide_templates"
    ADD CONSTRAINT "style_guide_templates_organization_id_fkey" FOREIGN KEY ("organization_id") REFERENCES "public"."organizations"("id") ON DELETE CASCADE;


ALTER TABLE ONLY "public"."tool_call_logs"
    ADD CONSTRAINT "tool_call_logs_execution_id_fkey" FOREIGN KEY ("execution_id") REFERENCES "public"."agent_execution_logs"("id") ON DELETE CASCADE;


ALTER TABLE ONLY "public"."usage_logs"
    ADD CONSTRAINT "usage_logs_usage_tracking_id_fkey" FOREIGN KEY ("usage_tracking_id") REFERENCES "public"."usage_tracking"("id") ON DELETE CASCADE;


ALTER TABLE ONLY "public"."usage_tracking"
    ADD CONSTRAINT "usage_tracking_organization_id_fkey" FOREIGN KEY ("organization_id") REFERENCES "public"."organizations"("id") ON DELETE CASCADE;


ALTER TABLE ONLY "public"."usage_tracking"
    ADD CONSTRAINT "usage_tracking_plan_tier_id_fkey" FOREIGN KEY ("plan_tier_id") REFERENCES "public"."plan_tiers"("id");


ALTER TABLE ONLY "public"."user_subscriptions"
    ADD CONSTRAINT "user_subscriptions_plan_tier_id_fkey" FOREIGN KEY ("plan_tier_id") REFERENCES "public"."plan_tiers"("id");


ALTER TABLE ONLY "public"."user_subscriptions"
    ADD CONSTRAINT "user_subscriptions_upgraded_to_org_id_fkey" FOREIGN KEY ("upgraded_to_org_id") REFERENCES "public"."organizations"("id");


ALTER TABLE ONLY "public"."wordpress_sites"
    ADD CONSTRAINT "wordpress_sites_organization_id_fkey" FOREIGN KEY ("organization_id") REFERENCES "public"."organizations"("id") ON DELETE SET NULL;


ALTER TABLE ONLY "public"."workflow_step_logs"
    ADD CONSTRAINT "workflow_step_logs_primary_execution_id_fkey" FOREIGN KEY ("primary_execution_id") REFERENCES "public"."agent_execution_logs"("id");


ALTER TABLE ONLY "public"."workflow_step_logs"
    ADD CONSTRAINT "workflow_step_logs_session_id_fkey" FOREIGN KEY ("session_id") REFERENCES "public"."agent_log_sessions"("id") ON DELETE CASCADE;


CREATE POLICY "Anyone can read plan tiers" ON "public"."plan_tiers" FOR SELECT USING (true);


CREATE POLICY "Service role full access to usage_logs" ON "public"."usage_logs" USING (true);


CREATE POLICY "Service role full access to usage_tracking" ON "public"."usage_tracking" USING (true);


CREATE POLICY "Service role has full access to blog_generation_state" ON "public"."blog_generation_state" USING (("auth"."role"() = 'service_role'::"text")) WITH CHECK (("auth"."role"() = 'service_role'::"text"));


CREATE POLICY "Service role has full access to blog_process_events" ON "public"."blog_process_events" USING (("auth"."role"() = 'service_role'::"text")) WITH CHECK (("auth"."role"() = 'service_role'::"text"));


CREATE POLICY "Service role has full access to wordpress_sites" ON "public"."wordpress_sites" USING (("auth"."role"() = 'service_role'::"text")) WITH CHECK (("auth"."role"() = 'service_role'::"text"));


CREATE POLICY "Service role only for subscription events" ON "public"."subscription_events" USING (false);


CREATE POLICY "System can insert events" ON "public"."process_events" FOR INSERT WITH CHECK (true);


CREATE POLICY "System can manage background tasks" ON "public"."background_tasks" WITH CHECK (true);


CREATE POLICY "Users can access their own article versions" ON "public"."article_edit_versions" USING ((EXISTS ( SELECT 1
   FROM "public"."articles"
  WHERE (("articles"."id" = "article_edit_versions"."article_id") AND ("articles"."user_id" = (("current_setting"('request.jwt.claims'::"text", true))::json ->> 'sub'::"text"))))));


CREATE POLICY "Users can access their own process snapshots" ON "public"."article_generation_step_snapshots" USING ((EXISTS ( SELECT 1
   FROM "public"."generated_articles_state"
  WHERE (("generated_articles_state"."id" = "article_generation_step_snapshots"."process_id") AND ("generated_articles_state"."user_id" = (("current_setting"('request.jwt.claims'::"text", true))::json ->> 'sub'::"text"))))));


CREATE POLICY "Users can acknowledge their events" ON "public"."process_events" FOR UPDATE USING ((EXISTS ( SELECT 1
   FROM "public"."generated_articles_state"
  WHERE (("generated_articles_state"."id" = "process_events"."process_id") AND ("generated_articles_state"."user_id" = (("current_setting"('request.jwt.claims'::"text", true))::json ->> 'sub'::"text")))))) WITH CHECK ((EXISTS ( SELECT 1
   FROM "public"."generated_articles_state"
  WHERE (("generated_articles_state"."id" = "process_events"."process_id") AND ("generated_articles_state"."user_id" = (("current_setting"('request.jwt.claims'::"text", true))::json ->> 'sub'::"text"))))));


CREATE POLICY "Users can add their agent chat messages" ON "public"."article_agent_messages" FOR INSERT WITH CHECK ((("user_id" = (("current_setting"('request.jwt.claims'::"text", true))::json ->> 'sub'::"text")) AND (EXISTS ( SELECT 1
   FROM "public"."article_agent_sessions" "s"
  WHERE (("s"."id" = "article_agent_messages"."session_id") AND ("s"."user_id" = (("current_setting"('request.jwt.claims'::"text", true))::json ->> 'sub'::"text")))))));


CREATE POLICY "Users can delete their agent chat messages" ON "public"."article_agent_messages" FOR DELETE USING ((EXISTS ( SELECT 1
   FROM "public"."article_agent_sessions" "s"
  WHERE (("s"."id" = "article_agent_messages"."session_id") AND ("s"."user_id" = (("current_setting"('request.jwt.claims'::"text", true))::json ->> 'sub'::"text"))))));


CREATE POLICY "Users can delete their own WordPress sites" ON "public"."wordpress_sites" FOR DELETE USING (("user_id" = (("current_setting"('request.jwt.claims'::"text", true))::json ->> 'sub'::"text")));


CREATE POLICY "Users can delete their own blog generations" ON "public"."blog_generation_state" FOR DELETE USING (("user_id" = (("current_setting"('request.jwt.claims'::"text", true))::json ->> 'sub'::"text")));


CREATE POLICY "Users can insert their own WordPress sites" ON "public"."wordpress_sites" FOR INSERT WITH CHECK (("user_id" = (("current_setting"('request.jwt.claims'::"text", true))::json ->> 'sub'::"text")));


CREATE POLICY "Users can insert their own blog generations" ON "public"."blog_generation_state" FOR INSERT WITH CHECK (("user_id" = (("current_setting"('request.jwt.claims'::"text", true))::json ->> 'sub'::"text")));


CREATE POLICY "Users can maintain their agent chat messages" ON "public"."article_agent_messages" FOR UPDATE USING ((EXISTS ( SELECT 1
   FROM "public"."article_agent_sessions" "s"
  WHERE (("s"."id" = "article_agent_messages"."session_id") AND ("s"."user_id" = (("current_setting"('request.jwt.claims'::"text", true))::json ->> 'sub'::"text")))))) WITH CHECK ((EXISTS ( SELECT 1
   FROM "public"."article_agent_sessions" "s"
  WHERE (("s"."id" = "article_agent_messages"."session_id") AND ("s"."user_id" = (("current_setting"('request.jwt.claims'::"text", true))::json ->> 'sub'::"text"))))));


CREATE POLICY "Users can manage placeholders for their own articles" ON "public"."image_placeholders" USING ((EXISTS ( SELECT 1
   FROM "public"."articles"
  WHERE (("articles"."id" = "image_placeholders"."article_id") AND ("articles"."user_id" = (("current_setting"('request.jwt.claims'::"text", true))::json ->> 'sub'::"text"))))));


CREATE POLICY "Users can manage their agent chat sessions" ON "public"."article_agent_sessions" USING (("user_id" = (("current_setting"('request.jwt.claims'::"text", true))::json ->> 'sub'::"text"))) WITH CHECK (("user_id" = (("current_setting"('request.jwt.claims'::"text", true))::json ->> 'sub'::"text")));


CREATE POLICY "Users can manage their own company info" ON "public"."company_info" USING (("user_id" = (("current_setting"('request.jwt.claims'::"text", true))::json ->> 'sub'::"text")));


CREATE POLICY "Users can read their agent chat messages" ON "public"."article_agent_messages" FOR SELECT USING ((EXISTS ( SELECT 1
   FROM "public"."article_agent_sessions" "s"
  WHERE (("s"."id" = "article_agent_messages"."session_id") AND ("s"."user_id" = (("current_setting"('request.jwt.claims'::"text", true))::json ->> 'sub'::"text"))))));


CREATE POLICY "Users can update their own WordPress sites" ON "public"."wordpress_sites" FOR UPDATE USING (("user_id" = (("current_setting"('request.jwt.claims'::"text", true))::json ->> 'sub'::"text")));


CREATE POLICY "Users can update their own blog generations" ON "public"."blog_generation_state" FOR UPDATE USING (("user_id" = (("current_setting"('request.jwt.claims'::"text", true))::json ->> 'sub'::"text")));


CREATE POLICY "Users can view events for their processes" ON "public"."process_events" FOR SELECT USING ((EXISTS ( SELECT 1
   FROM "public"."generated_articles_state"
  WHERE (("generated_articles_state"."id" = "process_events"."process_id") AND ("generated_articles_state"."user_id" = (("current_setting"('request.jwt.claims'::"text", true))::json ->> 'sub'::"text"))))));


CREATE POLICY "Users can view own subscription" ON "public"."user_subscriptions" FOR SELECT USING (("user_id" = (("current_setting"('request.jwt.claims'::"text", true))::json ->> 'sub'::"text")));


CREATE POLICY "Users can view tasks for their processes" ON "public"."background_tasks" FOR SELECT USING ((EXISTS ( SELECT 1
   FROM "public"."generated_articles_state"
  WHERE (("generated_articles_state"."id" = "background_tasks"."process_id") AND ("generated_articles_state"."user_id" = (("current_setting"('request.jwt.claims'::"text", true))::json ->> 'sub'::"text"))))));


CREATE POLICY "Users can view their agent chat sessions" ON "public"."article_agent_sessions" FOR SELECT USING (("user_id" = (("current_setting"('request.jwt.claims'::"text", true))::json ->> 'sub'::"text")));


CREATE POLICY "Users can view their own WordPress sites" ON "public"."wordpress_sites" FOR SELECT USING (("user_id" = (("current_setting"('request.jwt.claims'::"text", true))::json ->> 'sub'::"text")));


CREATE POLICY "Users can view their own blog events" ON "public"."blog_process_events" FOR SELECT USING (("user_id" = (("current_setting"('request.jwt.claims'::"text", true))::json ->> 'sub'::"text")));


CREATE POLICY "Users can view their own blog generations" ON "public"."blog_generation_state" FOR SELECT USING (("user_id" = (("current_setting"('request.jwt.claims'::"text", true))::json ->> 'sub'::"text")));


ALTER TABLE "public"."agent_execution_logs" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."agent_log_sessions" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."article_agent_messages" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."article_agent_sessions" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."article_edit_versions" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."article_generation_flows" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."article_generation_step_snapshots" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."articles" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."background_tasks" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."blog_generation_state" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."blog_process_events" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."company_info" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."flow_steps" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."image_placeholders" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."images" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."invitations" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."llm_call_logs" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."organization_members" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."organization_subscriptions" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."organizations" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."plan_tiers" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."process_events" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."style_guide_templates" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."subscription_events" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."tool_call_logs" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."usage_logs" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."usage_tracking" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."user_subscriptions" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."wordpress_sites" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."workflow_step_logs" ENABLE ROW LEVEL SECURITY;


ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "postgres";

ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "anon";

ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "authenticated";

ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "service_role";


ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "postgres";

ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "anon";

ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "authenticated";

ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "service_role";


ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "postgres";

ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "anon";

ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "authenticated";

ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "service_role";


-- ===================== REALTIME PUBLICATION =====================
DROP PUBLICATION IF EXISTS supabase_realtime;
CREATE PUBLICATION supabase_realtime FOR TABLE
  generated_articles_state,
  articles,
  blog_generation_state,
  blog_process_events,
  process_events,
  user_subscriptions;
