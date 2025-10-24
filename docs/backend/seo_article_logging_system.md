# SEO記事生成におけるログシステムの仕様

## 概要

本システムは、SEO記事生成プロセス全体を追跡・分析するための包括的なログシステムを提供します。OpenAI Agents SDKを使用したマルチエージェントワークフローにおいて、詳細なメトリクス、パフォーマンス測定、エラー分析、コスト追跡を実現します。

## システム構成

### アーキテクチャ概要

```
┌─────────────────────────┐
│  記事生成プロセス      │
├─────────────────────────┤
│  • キーワード分析      │
│  • ペルソナ生成        │
│  • テーマ提案          │
│  • リサーチ計画・実行  │
│  • アウトライン生成    │
│  • セクション執筆      │
│  • 最終編集            │
└─────────────────────────┘
           │
           ▼
┌─────────────────────────┐
│  MultiAgentWorkflowLogger │
└─────────────────────────┘
           │
           ▼
┌─────────────────────────┐
│   LoggingService        │
├─────────────────────────┤
│  • セッション管理      │
│  • 実行ログ記録        │
│  • LLM呼び出し追跡     │
│  • ツール呼び出し記録  │
│  • パフォーマンス計測  │
└─────────────────────────┘
           │
           ▼
┌─────────────────────────┐
│   Supabaseデータベース  │
├─────────────────────────┤
│  • agent_log_sessions  │
│  • agent_execution_logs│
│  • llm_call_logs       │
│  • tool_call_logs      │
│  • workflow_step_logs  │
└─────────────────────────┘
```

## データベーステーブル設計

### 1. agent_log_sessions（ログセッション）

記事生成セッション全体を管理するメインテーブル。

```sql
CREATE TABLE agent_log_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
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
```

**主要フィールド説明:**
- `article_uuid`: 生成対象記事のID
- `user_id`: ユーザーID（Clerk認証）
- `initial_input`: 初期入力データ（キーワード、設定等）
- `seo_keywords`: SEO対象キーワード配列
- `image_mode_enabled`: 画像生成モード有効化フラグ
- `status`: セッション状態（開始→進行中→完了/失敗/キャンセル）
- `total_steps`/`completed_steps`: 進捗管理用

### 2. agent_execution_logs（エージェント実行ログ）

各エージェントの個別実行記録を保存。

```sql
CREATE TABLE agent_execution_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES agent_log_sessions(id) ON DELETE CASCADE,
    
    -- エージェント識別情報
    agent_name TEXT NOT NULL,
    agent_type TEXT NOT NULL, -- 'research', 'persona_generation', 'theme_proposal', etc.
    step_number INTEGER NOT NULL,
    sub_step_number INTEGER DEFAULT 1,
    
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
    reasoning_tokens INTEGER DEFAULT 0, -- o1系モデル対応
    
    -- タイミング情報
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    duration_ms INTEGER,
    
    -- エラー情報
    error_message TEXT,
    error_details JSONB DEFAULT '{}',
    
    -- メタデータ
    execution_metadata JSONB DEFAULT '{}'
);
```

**エージェントタイプ一覧:**
- `keyword_analysis`: キーワード分析
- `persona_generation`: ペルソナ生成
- `theme_proposal`: テーマ提案
- `research_planning`: リサーチ計画
- `research_execution`: リサーチ実行
- `outline_creation`: アウトライン作成
- `section_writing`: セクション執筆
- `final_editing`: 最終編集

### 3. llm_call_logs（LLM呼び出しログ）

個別のLLM API呼び出し詳細を記録。

```sql
CREATE TABLE llm_call_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    execution_id UUID NOT NULL REFERENCES agent_execution_logs(id) ON DELETE CASCADE,
    
    -- 呼び出し情報
    call_sequence INTEGER NOT NULL DEFAULT 1,
    api_type TEXT NOT NULL DEFAULT 'chat_completions',
    
    -- モデル詳細
    model_name TEXT NOT NULL,
    provider TEXT NOT NULL DEFAULT 'openai',
    
    -- プロンプト情報
    system_prompt TEXT,
    user_prompt TEXT,
    full_prompt_data JSONB DEFAULT '{}',
    
    -- レスポンス情報
    response_content TEXT,
    response_data JSONB DEFAULT '{}',
    
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
    retry_count INTEGER DEFAULT 0
);
```

### 4. tool_call_logs（ツール呼び出しログ）

WebSearch、SerpAPI等外部ツール呼び出しを記録。

```sql
CREATE TABLE tool_call_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    execution_id UUID NOT NULL REFERENCES agent_execution_logs(id) ON DELETE CASCADE,
    
    -- ツール情報
    tool_name TEXT NOT NULL, -- 'web_search', 'serp_api', 'file_search'
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
    api_calls_count INTEGER DEFAULT 1,
    
    -- エラーハンドリング
    error_type TEXT,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    
    -- タイムスタンプ
    called_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    
    -- メタデータ
    tool_metadata JSONB DEFAULT '{}'
);
```

### 5. workflow_step_logs（ワークフローステップログ）

各ステップの詳細記録。

```sql
CREATE TABLE workflow_step_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES agent_log_sessions(id) ON DELETE CASCADE,
    
    -- ステップ情報
    step_name TEXT NOT NULL,
    step_type TEXT NOT NULL,
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
    step_metadata JSONB DEFAULT '{}'
);
```

## ログサービス実装

### LoggingServiceクラス

ファイル位置: `/backend/app/infrastructure/logging/service.py`

#### 主要メソッド

##### 1. ログセッション管理

```python
@staticmethod
def create_log_session(
    article_uuid: str,
    user_id: str,
    organization_id: Optional[str] = None,
    initial_input: Optional[Dict[str, Any]] = None,
    seo_keywords: Optional[List[str]] = None,
    image_mode_enabled: bool = False,
    article_style_info: Optional[Dict[str, Any]] = None,
    generation_theme_count: int = 1,
    target_age_group: Optional[str] = None,
    persona_settings: Optional[Dict[str, Any]] = None,
    company_info: Optional[Dict[str, Any]] = None,
    session_metadata: Optional[Dict[str, Any]] = None
) -> str:
    """新しいログセッションを作成"""
```

**使用例:**
```python
session_id = LoggingService.create_log_session(
    article_uuid="123e4567-e89b-12d3-a456-426614174000",
    user_id="user_2y2DRx4Xb5PbvMVoVWmDluHCeFV",
    initial_input={"keywords": ["AI", "SEO", "マーケティング"]},
    seo_keywords=["AI SEO", "人工知能 マーケティング"],
    image_mode_enabled=True,
    generation_theme_count=3
)
```

##### 2. エージェント実行ログ

```python
@staticmethod
def create_execution_log(
    session_id: str,
    agent_name: str,
    agent_type: str,
    step_number: int,
    sub_step_number: int = 1,
    input_data: Optional[Dict[str, Any]] = None,
    llm_model: Optional[str] = None,
    llm_provider: str = "openai",
    execution_metadata: Optional[Dict[str, Any]] = None
) -> str:
    """エージェント実行ログを作成"""
```

**使用例:**
```python
execution_id = LoggingService.create_execution_log(
    session_id=session_id,
    agent_name="PersonaGeneratorAgent",
    agent_type="persona_generation",
    step_number=2,
    input_data={"keywords": ["AI", "SEO"], "target_age": "30-40代"},
    llm_model="gpt-4o-mini"
)
```

##### 3. LLM呼び出しログ

```python
@staticmethod
def create_llm_call_log(
    execution_id: str,
    call_sequence: int,
    api_type: str,
    model_name: str,
    provider: str = "openai",
    system_prompt: Optional[str] = None,
    user_prompt: Optional[str] = None,
    response_content: Optional[str] = None,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    total_tokens: int = 0,
    response_time_ms: Optional[int] = None,
    estimated_cost_usd: Optional[float] = None
) -> str:
    """LLM呼び出しログを作成"""
```

##### 4. ツール呼び出しログ

```python
@staticmethod
def create_tool_call_log(
    execution_id: str,
    tool_name: str,
    tool_function: str,
    call_sequence: int,
    input_parameters: Optional[Dict[str, Any]] = None,
    output_data: Optional[Dict[str, Any]] = None,
    status: str = "started",
    execution_time_ms: Optional[int] = None
) -> str:
    """ツール呼び出しログを作成"""
```

## パフォーマンスメトリクス

### 集計ビュー

#### 1. agent_performance_metrics

```sql
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
```

#### 2. error_analysis（エラー分析ビュー）

```sql
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
```

### パフォーマンスメトリクス取得

```python
@staticmethod
def get_session_performance_metrics(session_id: str) -> Dict[str, Any]:
    """セッションのパフォーマンスメトリクスを取得"""
    try:
        # セッション情報
        session_result = supabase.table("agent_log_sessions").select("*").eq("id", session_id).execute()
        
        # 実行ログ統計
        execution_result = supabase.table("agent_execution_logs").select("*").eq("session_id", session_id).execute()
        executions = execution_result.data
        
        total_tokens = sum(
            (ex.get("input_tokens", 0) + ex.get("output_tokens", 0) + 
             ex.get("cache_tokens", 0) + ex.get("reasoning_tokens", 0))
            for ex in executions
        )
        
        metrics = {
            "session_id": session_id,
            "session_status": session["status"],
            "total_executions": len(executions),
            "total_tokens": total_tokens,
            "session_duration_ms": None,
            "executions_by_type": {},
            "llm_calls_stats": {},
            "tool_calls_stats": {}
        }
        
        return metrics
    except Exception as e:
        logger.error(f"Failed to get session performance metrics: {e}")
        raise
```

## コスト計算

### トークンベースコスト計算

```python
def _estimate_cost(self, usage) -> float:
    """トークン使用量からコストを概算"""
    model_costs = {
        "gpt-4o": {"input": 0.0025, "output": 0.01},      # per 1K tokens
        "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        "o1-preview": {"input": 0.015, "output": 0.06},
        "o1-mini": {"input": 0.003, "output": 0.012}
    }
    
    model = usage.get("model", "gpt-4o-mini")
    costs = model_costs.get(model, model_costs["gpt-4o-mini"])
    
    input_cost = (usage.get("prompt_tokens", 0) / 1000) * costs["input"]
    output_cost = (usage.get("completion_tokens", 0) / 1000) * costs["output"]
    
    return input_cost + output_cost
```

## データ保持・クリーンアップ

### 自動クリーンアップ機能

```sql
-- 古いイベントのクリーンアップ
CREATE OR REPLACE FUNCTION cleanup_old_events(days_old INTEGER DEFAULT 7)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- 指定日数より古いイベントを削除（重要なもの除く）
    DELETE FROM process_events
    WHERE created_at < (NOW() - INTERVAL '1 day' * days_old)
        AND event_type NOT IN ('process_created', 'generation_completed', 'generation_error')
        AND archived = FALSE;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    -- 重要なイベントはアーカイブ
    UPDATE process_events 
    SET archived = TRUE
    WHERE created_at < (NOW() - INTERVAL '1 day' * days_old * 2)
        AND event_type IN ('process_created', 'generation_completed', 'generation_error')
        AND archived = FALSE;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;
```

## 統合とワークフロー

### MultiAgentWorkflowLoggerとの統合

```python
from app.infrastructure.logging.service import LoggingService

class GenerationFlowManager:
    async def run_agent(self, agent, input_data, context, run_config):
        """エージェントを実行し、結果を返す（リトライ付き）"""
        
        # ログセッション作成（初回のみ）
        if not hasattr(context, 'log_session_id'):
            context.log_session_id = LoggingService.create_log_session(
                article_uuid=context.process_id,
                user_id=context.user_id,
                initial_input=input_data,
                image_mode_enabled=context.image_mode
            )
        
        # 実行ログ作成
        execution_id = LoggingService.create_execution_log(
            session_id=context.log_session_id,
            agent_name=agent.name,
            agent_type=self._get_agent_type(agent),
            step_number=self._get_current_step_number(context),
            input_data=input_data,
            llm_model=run_config.get("model", "gpt-4o-mini")
        )
        
        try:
            # エージェント実行
            result = await agent.run_streamed(input_data)
            
            # 成功時のログ更新
            LoggingService.update_execution_log(
                execution_id=execution_id,
                status="completed",
                output_data=result.output,
                input_tokens=result.usage.input_tokens,
                output_tokens=result.usage.output_tokens,
                duration_ms=result.duration
            )
            
            return result
            
        except Exception as e:
            # エラー時のログ更新
            LoggingService.update_execution_log(
                execution_id=execution_id,
                status="failed",
                error_message=str(e),
                error_details={"exception_type": type(e).__name__}
            )
            raise
```

## セキュリティとプライバシー

### Row Level Security (RLS)

```sql
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
```

### データマスキング

機密情報の自動マスキング機能：

```python
def mask_sensitive_data(prompt_data: Dict[str, Any]) -> Dict[str, Any]:
    """機密情報をマスキング"""
    sensitive_patterns = [
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
        r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b',              # Credit card
        r'\b\d{3}-\d{2}-\d{4}\b'                                  # SSN
    ]
    
    masked_data = prompt_data.copy()
    for key, value in masked_data.items():
        if isinstance(value, str):
            for pattern in sensitive_patterns:
                masked_data[key] = re.sub(pattern, "***MASKED***", value)
    
    return masked_data
```

## 監視とアラート

### メトリクス監視

```python
async def monitor_performance_metrics():
    """パフォーマンスメトリクスの監視"""
    
    # 異常な実行時間の検出
    long_running_sessions = supabase.table("agent_log_sessions").select("*").gte("duration_ms", 300000).execute()
    
    # 高頻度エラーの検出
    error_rates = supabase.rpc("get_error_rates_by_agent_type").execute()
    
    # コスト異常の検出
    high_cost_sessions = supabase.table("agent_performance_metrics").select("*").gte("estimated_total_cost", 1.0).execute()
    
    # アラート送信ロジック
    if high_cost_sessions.data:
        await send_cost_alert(high_cost_sessions.data)
```

## 活用例

### 1. パフォーマンス分析

```python
# エージェント別パフォーマンス比較
performance_data = LoggingService.get_agent_performance_comparison(
    start_date="2025-01-01",
    end_date="2025-01-31"
)

# 結果例
{
    "persona_generation": {
        "avg_duration_ms": 15000,
        "avg_tokens": 2500,
        "success_rate": 0.95,
        "avg_cost": 0.05
    },
    "section_writing": {
        "avg_duration_ms": 45000,
        "avg_tokens": 8000,
        "success_rate": 0.98,
        "avg_cost": 0.15
    }
}
```

### 2. コスト最適化

```python
# 月次コストレポート
cost_report = LoggingService.generate_cost_report(
    user_id="user_2y2DRx4Xb5PbvMVoVWmDluHCeFV",
    month="2025-01"
)

# 結果例
{
    "total_cost": 15.75,
    "cost_by_agent_type": {
        "section_writing": 8.50,
        "research_execution": 3.25,
        "persona_generation": 2.00,
        "other": 2.00
    },
    "cost_by_model": {
        "gpt-4o-mini": 12.00,
        "gpt-4o": 3.75
    }
}
```

### 3. エラー分析

```python
# エラーパターン分析
error_analysis = LoggingService.analyze_error_patterns(
    days_back=7
)

# 結果例
{
    "most_common_errors": [
        {
            "agent_type": "research_execution",
            "error_message": "API rate limit exceeded",
            "count": 15,
            "avg_retry_success_rate": 0.8
        }
    ],
    "error_trends": {
        "total_errors_week": 25,
        "total_errors_prev_week": 18,
        "trend": "increasing"
    }
}
```

## まとめ

本ログシステムは、SEO記事生成プロセスの透明性、追跡可能性、最適化を実現する包括的なソリューションです。詳細なメトリクス収集により、システムの改善点を特定し、コスト効率とパフォーマンスの向上を継続的に達成できます。
