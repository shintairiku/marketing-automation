-- 簡単な修正: 外部キー制約のみ削除
-- 2025-07-16: article_uuidの外部キー制約を削除（型変更は行わない）

-- ビューを一時的に削除
DROP VIEW IF EXISTS agent_performance_metrics;
DROP VIEW IF EXISTS error_analysis;

-- 外部キー制約を削除
DO $$ 
BEGIN
    -- agent_log_sessions テーブルの外部キー制約を削除
    IF EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'agent_log_sessions_article_uuid_fkey' 
        AND table_name = 'agent_log_sessions'
    ) THEN
        ALTER TABLE agent_log_sessions DROP CONSTRAINT agent_log_sessions_article_uuid_fkey;
    END IF;
    
    -- organization_id の外部キー制約も削除
    IF EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'agent_log_sessions_organization_id_fkey' 
        AND table_name = 'agent_log_sessions'
    ) THEN
        ALTER TABLE agent_log_sessions DROP CONSTRAINT agent_log_sessions_organization_id_fkey;
    END IF;
END $$;

-- ビューを再作成
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