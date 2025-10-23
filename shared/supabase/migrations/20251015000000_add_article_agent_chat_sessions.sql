/**
 * ARTICLE AGENT CHAT SESSION PERSISTENCE
 *
 * Adds persistent storage for AI editing agent chat sessions and messages so
 * conversations can be resumed across requests and server restarts.
 */

-- ============================================================================
-- 1. ARTICLE_AGENT_SESSIONS TABLE
-- ============================================================================

CREATE TABLE article_agent_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    article_id UUID NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL,
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'paused', 'closed')),
    session_store_key TEXT NOT NULL,
    original_content TEXT,
    working_content TEXT,
    article_title TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    last_activity_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    closed_at TIMESTAMPTZ,
    conversation_summary TEXT
);

COMMENT ON TABLE article_agent_sessions IS 'Persisted AI editing agent sessions for continuing conversations';
COMMENT ON COLUMN article_agent_sessions.session_store_key IS 'File key for the Agents SDK SQLite session store';
COMMENT ON COLUMN article_agent_sessions.working_content IS 'Current working HTML content managed inside the agent session';
COMMENT ON COLUMN article_agent_sessions.original_content IS 'Article HTML content at the start of the agent session';

CREATE UNIQUE INDEX idx_article_agent_sessions_active
    ON article_agent_sessions(article_id, user_id)
    WHERE status = 'active';

CREATE INDEX idx_article_agent_sessions_user_article
    ON article_agent_sessions(user_id, article_id);

-- ============================================================================
-- 2. ARTICLE_AGENT_MESSAGES TABLE
-- ============================================================================

CREATE TABLE article_agent_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES article_agent_sessions(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system', 'tool')),
    content TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    sequence BIGINT GENERATED ALWAYS AS IDENTITY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

COMMENT ON TABLE article_agent_messages IS 'Ordered chat messages exchanged within an article agent session';
COMMENT ON COLUMN article_agent_messages.sequence IS 'Monotonic sequence used for chronological ordering';

CREATE INDEX idx_article_agent_messages_session
    ON article_agent_messages(session_id);

CREATE INDEX idx_article_agent_messages_sequence
    ON article_agent_messages(session_id, sequence);

-- ============================================================================
-- 3. ROW LEVEL SECURITY
-- ============================================================================

ALTER TABLE article_agent_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE article_agent_messages ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their agent chat sessions" ON article_agent_sessions
  FOR SELECT USING (user_id = current_setting('request.jwt.claims', true)::json->>'sub');

CREATE POLICY "Users can manage their agent chat sessions" ON article_agent_sessions
  FOR ALL USING (user_id = current_setting('request.jwt.claims', true)::json->>'sub')
  WITH CHECK (user_id = current_setting('request.jwt.claims', true)::json->>'sub');

CREATE POLICY "Users can read their agent chat messages" ON article_agent_messages
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM article_agent_sessions s
      WHERE s.id = article_agent_messages.session_id
        AND s.user_id = current_setting('request.jwt.claims', true)::json->>'sub'
    )
  );

CREATE POLICY "Users can add their agent chat messages" ON article_agent_messages
  FOR INSERT WITH CHECK (
    user_id = current_setting('request.jwt.claims', true)::json->>'sub'
    AND EXISTS (
      SELECT 1 FROM article_agent_sessions s
      WHERE s.id = article_agent_messages.session_id
        AND s.user_id = current_setting('request.jwt.claims', true)::json->>'sub'
    )
  );

CREATE POLICY "Users can maintain their agent chat messages" ON article_agent_messages
  FOR UPDATE USING (
    EXISTS (
      SELECT 1 FROM article_agent_sessions s
      WHERE s.id = article_agent_messages.session_id
        AND s.user_id = current_setting('request.jwt.claims', true)::json->>'sub'
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM article_agent_sessions s
      WHERE s.id = article_agent_messages.session_id
        AND s.user_id = current_setting('request.jwt.claims', true)::json->>'sub'
    )
  );

CREATE POLICY "Users can delete their agent chat messages" ON article_agent_messages
  FOR DELETE USING (
    EXISTS (
      SELECT 1 FROM article_agent_sessions s
      WHERE s.id = article_agent_messages.session_id
        AND s.user_id = current_setting('request.jwt.claims', true)::json->>'sub'
    )
  );

-- ============================================================================
-- 4. TRIGGERS
-- ============================================================================

CREATE TRIGGER update_article_agent_sessions_updated_at
  BEFORE UPDATE ON article_agent_sessions
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- 5. REALTIME PUBLICATION
-- ============================================================================

DROP PUBLICATION IF EXISTS supabase_realtime;
CREATE PUBLICATION supabase_realtime FOR TABLE
    products,
    prices,
    organizations,
    organization_members,
    invitations,
    article_generation_flows,
    flow_steps,
    generated_articles_state,
    articles,
    images,
    process_events,
    background_tasks,
    task_dependencies,
    image_placeholders,
    company_info,
    style_guide_templates,
    agent_log_sessions,
    agent_execution_logs,
    llm_call_logs,
    tool_call_logs,
    workflow_step_logs,
    article_generation_step_snapshots,
    article_edit_versions,
    article_agent_sessions,
    article_agent_messages;

ALTER TABLE article_agent_sessions REPLICA IDENTITY FULL;
ALTER TABLE article_agent_messages REPLICA IDENTITY FULL;

-- ============================================================================
-- 6. GRANTS
-- ============================================================================

GRANT SELECT ON article_agent_sessions TO authenticated;
GRANT SELECT ON article_agent_messages TO authenticated;
