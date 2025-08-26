-- マルチエージェントシステム用包括的ログシステム
-- 2025-07-16: SEO記事作成におけるエージェントワークフローの完全なログ記録

-- 拡張機能の有効化
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ログセッション（記事生成セッション全体を管理）
CREATE TABLE agent_log_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    article_uuid UUID NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL,
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    
    -- 初期入力データ
    initial_input JSONB NOT NULL DEFAULT '{}',
    seo_keywords TEXT[],
    image_mode_enabled BOOLEAN DEFAULT false,
    article_style_info JSONB DEFAULT '{}',
    generation_theme_count INTEGER DEFAULT 1,
    target_age_group TEXT,
    persona_settings JSONB DEFAULT '{}',
    company_info JSONB DEFAULT '{}',
    
    -- セッション状態
    status TEXT NOT NULL DEFAULT 'started' CHECK (status IN ('started', 'in_progress', 'completed', 'failed', 'cancelled')),
    total_steps INTEGER DEFAULT 0,
    completed_steps INTEGER DEFAULT 0,
    
    -- タイムスタンプ
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    
    -- メタデータ
    session_metadata JSONB DEFAULT '{}',
    
    CONSTRAINT valid_step_counts CHECK (completed_steps <= total_steps)
);

-- エージェント実行ログ（各エージェントの個別実行記録）
CREATE TABLE agent_execution_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES agent_log_sessions(id) ON DELETE CASCADE,
    
    -- エージェント識別情報
    agent_name TEXT NOT NULL,
    agent_type TEXT NOT NULL, -- 'research', 'persona_generation', 'theme_proposal', 'outline_creation', 'section_writing', 'final_editing'
    step_number INTEGER NOT NULL,
    sub_step_number INTEGER DEFAULT 1, -- セクションライティングなど複数回実行される場合
    
    -- 実行状態
    status TEXT NOT NULL DEFAULT 'started' CHECK (status IN ('started', 'running', 'completed', 'failed', 'timeout')),
    
    -- 入力・出力データ
    input_data JSONB DEFAULT '{}',
    output_data JSONB DEFAULT '{}',
    
    -- LLMモデル情報
    llm_model TEXT,
    llm_provider TEXT DEFAULT 'openai',
    
    -- トークン使用量
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    cache_tokens INTEGER DEFAULT 0,
    reasoning_tokens INTEGER DEFAULT 0, -- o3, o4-mini用
    
    -- タイミング情報
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    duration_ms INTEGER,
    
    -- エラー情報
    error_message TEXT,
    error_details JSONB DEFAULT '{}',
    
    -- メタデータ
    execution_metadata JSONB DEFAULT '{}',
    
    CONSTRAINT valid_duration CHECK (duration_ms >= 0),
    CONSTRAINT valid_tokens CHECK (
        input_tokens >= 0 AND 
        output_tokens >= 0 AND 
        cache_tokens >= 0 AND 
        reasoning_tokens >= 0
    )
);

-- LLM呼び出しログ（個別のLLM API呼び出し詳細）
CREATE TABLE llm_call_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    execution_id UUID NOT NULL REFERENCES agent_execution_logs(id) ON DELETE CASCADE,
    
    -- 呼び出し情報
    call_sequence INTEGER NOT NULL DEFAULT 1,
    api_type TEXT NOT NULL DEFAULT 'chat_completions', -- 'chat_completions', 'responses_api', 'embeddings'
    
    -- モデル詳細
    model_name TEXT NOT NULL,
    provider TEXT NOT NULL DEFAULT 'openai',
    
    -- プロンプト情報
    system_prompt TEXT,
    user_prompt TEXT,
    full_prompt_data JSONB DEFAULT '{}', -- 完全なプロンプト構造
    
    -- レスポンス情報
    response_content TEXT,
    response_data JSONB DEFAULT '{}', -- 完全なレスポンス構造
    
    -- 使用量メトリクス
    prompt_tokens INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    cached_tokens INTEGER DEFAULT 0,
    reasoning_tokens INTEGER DEFAULT 0,
    
    -- タイミング・コスト
    response_time_ms INTEGER,
    estimated_cost_usd DECIMAL(10, 6),
    
    -- API応答ステータス
    http_status_code INTEGER,
    api_response_id TEXT, -- OpenAI response ID
    
    -- タイムスタンプ
    called_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- エラーハンドリング
    error_type TEXT,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    
    CONSTRAINT valid_tokens_llm CHECK (
        prompt_tokens >= 0 AND 
        completion_tokens >= 0 AND 
        total_tokens >= 0 AND
        cached_tokens >= 0 AND
        reasoning_tokens >= 0
    ),
    CONSTRAINT valid_cost CHECK (estimated_cost_usd >= 0)
);

-- ツール呼び出しログ（WebSearch、SerpAPIなど外部ツール呼び出し）
CREATE TABLE tool_call_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    execution_id UUID NOT NULL REFERENCES agent_execution_logs(id) ON DELETE CASCADE,
    
    -- ツール情報
    tool_name TEXT NOT NULL, -- 'web_search', 'serp_api', 'file_search', 'computer_use'
    tool_function TEXT NOT NULL,
    call_sequence INTEGER NOT NULL DEFAULT 1,
    
    -- 呼び出しデータ
    input_parameters JSONB DEFAULT '{}',
    output_data JSONB DEFAULT '{}',
    
    -- 実行状態
    status TEXT NOT NULL DEFAULT 'started' CHECK (status IN ('started', 'completed', 'failed', 'timeout')),
    
    -- メトリクス
    execution_time_ms INTEGER,
    data_size_bytes INTEGER,
    api_calls_count INTEGER DEFAULT 1, -- 複数API呼び出しが必要な場合
    
    -- エラーハンドリング
    error_type TEXT,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    
    -- タイムスタンプ
    called_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    
    -- メタデータ
    tool_metadata JSONB DEFAULT '{}',
    
    CONSTRAINT valid_execution_time CHECK (execution_time_ms >= 0),
    CONSTRAINT valid_data_size CHECK (data_size_bytes >= 0)
);

-- ワークフローステップログ（各ステップの詳細記録）
CREATE TABLE workflow_step_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES agent_log_sessions(id) ON DELETE CASCADE,
    
    -- ステップ情報
    step_name TEXT NOT NULL,
    step_type TEXT NOT NULL, -- 'serp_research', 'persona_generation', 'theme_proposal', 'research_planning', 'research_execution', 'outline_creation', 'section_writing', 'final_editing'
    step_order INTEGER NOT NULL,
    
    -- ステップ状態
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed', 'skipped')),
    
    -- 入力・出力データ
    step_input JSONB DEFAULT '{}',
    step_output JSONB DEFAULT '{}',
    intermediate_results JSONB DEFAULT '{}',
    
    -- 関連する実行ログ
    primary_execution_id UUID REFERENCES agent_execution_logs(id),
    
    -- タイミング
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    duration_ms INTEGER,
    
    -- メタデータ
    step_metadata JSONB DEFAULT '{}',
    
    CONSTRAINT valid_step_duration CHECK (duration_ms >= 0)
);

-- パフォーマンスメトリクス集計ビュー
CREATE VIEW agent_performance_metrics AS
SELECT 
    als.id as session_id,
    als.article_uuid,
    als.status as session_status,
    COUNT(DISTINCT ael.id) as total_executions,
    COUNT(DISTINCT lcl.id) as total_llm_calls,
    COUNT(DISTINCT tcl.id) as total_tool_calls,
    SUM(ael.input_tokens + ael.output_tokens + ael.cache_tokens + ael.reasoning_tokens) as total_tokens,
    SUM(lcl.estimated_cost_usd) as estimated_total_cost,
    AVG(ael.duration_ms) as avg_execution_duration_ms,
    SUM(ael.duration_ms) as total_duration_ms,
    als.created_at,
    als.completed_at
FROM agent_log_sessions als
LEFT JOIN agent_execution_logs ael ON als.id = ael.session_id
LEFT JOIN llm_call_logs lcl ON ael.id = lcl.execution_id
LEFT JOIN tool_call_logs tcl ON ael.id = tcl.execution_id
GROUP BY als.id, als.article_uuid, als.status, als.created_at, als.completed_at;

-- エラー分析ビュー
CREATE VIEW error_analysis AS
SELECT 
    DATE_TRUNC('day', ael.started_at) as error_date,
    ael.agent_type,
    ael.error_message,
    COUNT(*) as error_count,
    AVG(ael.duration_ms) as avg_duration_before_error
FROM agent_execution_logs ael
WHERE ael.status = 'failed'
GROUP BY DATE_TRUNC('day', ael.started_at), ael.agent_type, ael.error_message
ORDER BY error_date DESC, error_count DESC;

-- インデックス作成
CREATE INDEX idx_agent_log_sessions_article_uuid ON agent_log_sessions(article_uuid);
CREATE INDEX idx_agent_log_sessions_user_org ON agent_log_sessions(user_id, organization_id);
CREATE INDEX idx_agent_log_sessions_status ON agent_log_sessions(status);
CREATE INDEX idx_agent_log_sessions_created_at ON agent_log_sessions(created_at);

CREATE INDEX idx_agent_execution_logs_session_id ON agent_execution_logs(session_id);
CREATE INDEX idx_agent_execution_logs_agent_type ON agent_execution_logs(agent_type);
CREATE INDEX idx_agent_execution_logs_status ON agent_execution_logs(status);
CREATE INDEX idx_agent_execution_logs_started_at ON agent_execution_logs(started_at);

CREATE INDEX idx_llm_call_logs_execution_id ON llm_call_logs(execution_id);
CREATE INDEX idx_llm_call_logs_model_name ON llm_call_logs(model_name);
CREATE INDEX idx_llm_call_logs_called_at ON llm_call_logs(called_at);

CREATE INDEX idx_tool_call_logs_execution_id ON tool_call_logs(execution_id);
CREATE INDEX idx_tool_call_logs_tool_name ON tool_call_logs(tool_name);
CREATE INDEX idx_tool_call_logs_called_at ON tool_call_logs(called_at);

CREATE INDEX idx_workflow_step_logs_session_id ON workflow_step_logs(session_id);
CREATE INDEX idx_workflow_step_logs_step_type ON workflow_step_logs(step_type);

-- RLSポリシー設定
ALTER TABLE agent_log_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_execution_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE llm_call_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE tool_call_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE workflow_step_logs ENABLE ROW LEVEL SECURITY;

-- ユーザーは自分のセッションのみアクセス可能
CREATE POLICY "Users can access their own agent sessions" ON agent_log_sessions
    FOR ALL USING (
        auth.uid()::text = user_id OR 
        organization_id IN (
            SELECT organization_id FROM organization_members 
            WHERE user_id = auth.uid()::text
        )
    );

-- 実行ログは関連するセッションのユーザーのみアクセス可能
CREATE POLICY "Users can access execution logs for their sessions" ON agent_execution_logs
    FOR ALL USING (
        session_id IN (
            SELECT id FROM agent_log_sessions 
            WHERE auth.uid()::text = user_id OR 
            organization_id IN (
                SELECT organization_id FROM organization_members 
                WHERE user_id = auth.uid()::text
            )
        )
    );

CREATE POLICY "Users can access llm logs for their sessions" ON llm_call_logs
    FOR ALL USING (
        execution_id IN (
            SELECT ael.id FROM agent_execution_logs ael
            JOIN agent_log_sessions als ON ael.session_id = als.id
            WHERE auth.uid()::text = als.user_id OR 
            als.organization_id IN (
                SELECT organization_id FROM organization_members 
                WHERE user_id = auth.uid()::text
            )
        )
    );

CREATE POLICY "Users can access tool logs for their sessions" ON tool_call_logs
    FOR ALL USING (
        execution_id IN (
            SELECT ael.id FROM agent_execution_logs ael
            JOIN agent_log_sessions als ON ael.session_id = als.id
            WHERE auth.uid()::text = als.user_id OR 
            als.organization_id IN (
                SELECT organization_id FROM organization_members 
                WHERE user_id = auth.uid()::text
            )
        )
    );

CREATE POLICY "Users can access workflow logs for their sessions" ON workflow_step_logs
    FOR ALL USING (
        session_id IN (
            SELECT id FROM agent_log_sessions 
            WHERE auth.uid()::text = user_id OR 
            organization_id IN (
                SELECT organization_id FROM organization_members 
                WHERE user_id = auth.uid()::text
            )
        )
    );

-- 自動更新トリガー
CREATE OR REPLACE FUNCTION update_agent_log_sessions_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_agent_log_sessions_timestamp
    BEFORE UPDATE ON agent_log_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_agent_log_sessions_timestamp();

-- コメント追加
COMMENT ON TABLE agent_log_sessions IS 'マルチエージェントシステムでの記事生成セッション全体のログ';
COMMENT ON TABLE agent_execution_logs IS '個別エージェントの実行ログと詳細メトリクス';
COMMENT ON TABLE llm_call_logs IS 'LLM API呼び出しの詳細ログとトークン使用量';
COMMENT ON TABLE tool_call_logs IS '外部ツール（WebSearch、SerpAPIなど）の呼び出しログ';
COMMENT ON TABLE workflow_step_logs IS 'ワークフローの各ステップの実行状況';