-- Blog AI detailed trace events for admin observability
-- Captures normalized stream events from OpenAI Agents SDK per process/session/execution

CREATE TABLE IF NOT EXISTS public.blog_agent_trace_events (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    process_id uuid NOT NULL,
    session_id uuid NOT NULL,
    execution_id uuid,
    user_id text NOT NULL,
    event_sequence integer NOT NULL,
    source text DEFAULT 'agents_sdk'::text NOT NULL,
    event_type text NOT NULL,
    event_name text,
    agent_name text,
    role text,
    message_text text,
    tool_name text,
    tool_call_id text,
    response_id text,
    model_name text,
    prompt_tokens integer DEFAULT 0 NOT NULL,
    completion_tokens integer DEFAULT 0 NOT NULL,
    cached_tokens integer DEFAULT 0 NOT NULL,
    reasoning_tokens integer DEFAULT 0 NOT NULL,
    total_tokens integer DEFAULT 0 NOT NULL,
    input_payload jsonb DEFAULT '{}'::jsonb NOT NULL,
    output_payload jsonb DEFAULT '{}'::jsonb NOT NULL,
    event_metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT blog_agent_trace_events_pkey PRIMARY KEY (id),
    CONSTRAINT blog_agent_trace_events_process_id_fkey FOREIGN KEY (process_id)
        REFERENCES public.blog_generation_state(id) ON DELETE CASCADE,
    CONSTRAINT blog_agent_trace_events_session_id_fkey FOREIGN KEY (session_id)
        REFERENCES public.agent_log_sessions(id) ON DELETE CASCADE,
    CONSTRAINT blog_agent_trace_events_execution_id_fkey FOREIGN KEY (execution_id)
        REFERENCES public.agent_execution_logs(id) ON DELETE CASCADE,
    CONSTRAINT blog_agent_trace_events_non_negative_tokens CHECK (
        prompt_tokens >= 0
        AND completion_tokens >= 0
        AND cached_tokens >= 0
        AND reasoning_tokens >= 0
        AND total_tokens >= 0
    )
);

CREATE INDEX IF NOT EXISTS idx_blog_agent_trace_events_process_created
    ON public.blog_agent_trace_events USING btree (process_id, created_at);

CREATE INDEX IF NOT EXISTS idx_blog_agent_trace_events_session_sequence
    ON public.blog_agent_trace_events USING btree (session_id, event_sequence);

CREATE INDEX IF NOT EXISTS idx_blog_agent_trace_events_execution_sequence
    ON public.blog_agent_trace_events USING btree (execution_id, event_sequence)
    WHERE execution_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_blog_agent_trace_events_response_id
    ON public.blog_agent_trace_events USING btree (response_id)
    WHERE response_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_blog_agent_trace_events_tool_call_id
    ON public.blog_agent_trace_events USING btree (tool_call_id)
    WHERE tool_call_id IS NOT NULL;

ALTER TABLE public.blog_agent_trace_events ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role has full access to blog_agent_trace_events"
    ON public.blog_agent_trace_events
    USING (auth.role() = 'service_role'::text)
    WITH CHECK (auth.role() = 'service_role'::text);

CREATE POLICY "Users can view their own blog trace events"
    ON public.blog_agent_trace_events
    FOR SELECT
    USING (user_id = ((current_setting('request.jwt.claims'::text, true))::json ->> 'sub'::text));

COMMENT ON TABLE public.blog_agent_trace_events
    IS 'Blog AI 実行時の詳細トレースイベント（OpenAI Agents SDK stream events + 正規化メタデータ）';
COMMENT ON COLUMN public.blog_agent_trace_events.input_payload
    IS 'イベントの入力側ペイロード（ツール引数、raw event dataなど）';
COMMENT ON COLUMN public.blog_agent_trace_events.output_payload
    IS 'イベントの出力側ペイロード（ツール返り値、モデル出力サマリなど）';
