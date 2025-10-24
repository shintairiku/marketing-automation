# SEO記事生成機能 データベース仕様

## 概要

本文書では、SEO記事生成機能に関連する全てのデータベーステーブルのスキーマ、役割、およびテーブル間のリレーションシップを詳細に解説します。Supabase PostgreSQLを基盤とし、Row Level Security (RLS)、Realtime機能、および包括的なログシステムを実装しています。

## データベース構成図

```
                    ┌─────────────────┐
                    │      users      │
                    │ (Auth.users)    │
                    └─────────────────┘
                            │
                            │ 1:N
                    ┌─────────────────┐
                    │   articles      │◄─┐
                    │                 │  │
                    └─────────────────┘  │
                            │            │
                            │ 1:1        │
                    ┌─────────────────┐  │
                    │generated_       │  │
                    │articles_state   │  │
                    └─────────────────┘  │
                            │            │
                ┌───────────┼────────────┼───────────┐
                │           │            │           │
                │ 1:N       │ 1:N        │ 1:N       │ 1:N
        ┌───────▼──┐ ┌──────▼──┐ ┌──────▼──┐ ┌─────▼────┐
        │process_  │ │agent_   │ │workflow_│ │image_    │
        │events    │ │log_     │ │step_    │ │place-    │
        │          │ │sessions │ │logs     │ │holders   │
        └──────────┘ └─────────┘ └─────────┘ └──────────┘
                            │
                    ┌───────┼──────┐
                    │ 1:N   │ 1:N  │
            ┌───────▼─┐  ┌──▼─────────┐
            │agent_   │  │tool_call_  │
            │execution│  │logs        │
            │_logs    │  │            │
            └─────────┘  └────────────┘
                    │
                    │ 1:N
            ┌───────▼─┐
            │llm_call_│
            │logs     │
            └─────────┘
```

## 主要テーブル詳細

### 1. articles（記事テーブル）

最終的に完成した記事を保存するメインテーブル。

```sql
CREATE TABLE articles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    organization_id UUID REFERENCES organizations(id) ON DELETE SET NULL,
    
    -- 記事メタデータ
    title TEXT NOT NULL,
    slug TEXT,
    description TEXT,
    keywords TEXT[],
    status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'published', 'archived')),
    
    -- 記事コンテンツ
    content TEXT NOT NULL,
    html_content TEXT NOT NULL,
    summary TEXT,
    
    -- SEO関連
    meta_title TEXT,
    meta_description TEXT,
    featured_image_url TEXT,
    reading_time_minutes INTEGER,
    word_count INTEGER,
    
    -- 生成関連メタデータ
    generation_metadata JSONB DEFAULT '{}',
    style_template_id TEXT,
    company_info_id TEXT,
    
    -- タイムスタンプ
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    published_at TIMESTAMPTZ
);
```

**主要フィールド説明:**
- `user_id`: 記事作成者（Clerk ID）
- `organization_id`: 組織ID（組織機能使用時）
- `content`: マークダウン形式の記事本文
- `html_content`: HTML形式の記事本文
- `generation_metadata`: 生成プロセスに関するメタデータ
- `style_template_id`: 使用したスタイルテンプレートID
- `company_info_id`: 使用した会社情報ID

**インデックス:**
```sql
CREATE INDEX idx_articles_user_id ON articles(user_id);
CREATE INDEX idx_articles_status ON articles(status);
CREATE INDEX idx_articles_created_at ON articles(created_at DESC);
CREATE INDEX idx_articles_organization_id ON articles(organization_id);
```

### 2. generated_articles_state（記事生成状態テーブル）

記事生成プロセスの状態を管理するテーブル。Supabase Realtimeとの連携に最適化。

```sql
CREATE TABLE generated_articles_state (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    organization_id UUID REFERENCES organizations(id) ON DELETE SET NULL,
    
    -- プロセス状態
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'user_input_required', 'completed', 'error', 'paused', 'cancelled')),
    current_step_name TEXT,
    progress_percentage INTEGER DEFAULT 0,
    
    -- ユーザー入力管理
    is_waiting_for_input BOOLEAN DEFAULT FALSE,
    input_type TEXT,
    user_input_timeout TIMESTAMPTZ,
    input_reminder_sent BOOLEAN DEFAULT FALSE,
    interaction_history JSONB DEFAULT '[]'::jsonb,
    
    -- 記事コンテキスト（ArticleContextの永続化）
    article_context JSONB NOT NULL DEFAULT '{}',
    
    -- プロセス管理
    process_type TEXT DEFAULT 'article_generation',
    parent_process_id UUID REFERENCES generated_articles_state(id),
    process_tags TEXT[] DEFAULT '{}',
    
    -- 実行状態追跡
    executing_step TEXT,
    step_execution_start TIMESTAMPTZ,
    step_execution_metadata JSONB DEFAULT '{}',
    step_durations JSONB DEFAULT '{}',
    step_history JSONB DEFAULT '[]'::jsonb,
    
    -- バックグラウンドタスク管理
    background_task_id TEXT,
    task_priority INTEGER DEFAULT 5,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    
    -- Realtime連携
    realtime_channel TEXT,
    last_realtime_event JSONB,
    realtime_subscriptions JSONB DEFAULT '[]'::jsonb,
    
    -- 復帰機能
    auto_resume_eligible BOOLEAN DEFAULT FALSE,
    resume_from_step TEXT,
    last_activity_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- メタデータ
    process_metadata JSONB DEFAULT '{}',
    error_message TEXT,
    error_details JSONB DEFAULT '{}',
    
    -- 時間計測
    total_processing_time INTERVAL,
    estimated_completion_time TIMESTAMPTZ,
    
    -- タイムスタンプ
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);
```

**主要フィールド説明:**
- `article_context`: ArticleContextクラスの内容をJSON形式で保存
- `process_metadata`: プロセス固有のメタデータ（進捗、一時データ等）
- `step_history`: 完了したステップの履歴
- `realtime_channel`: Supabase Realtimeチャンネル名
- `interaction_history`: ユーザーとの対話履歴

**重要インデックス:**
```sql
CREATE INDEX idx_generated_articles_state_status ON generated_articles_state(status);
CREATE INDEX idx_generated_articles_state_user_status ON generated_articles_state(user_id, status);
CREATE INDEX idx_generated_articles_state_realtime_channel ON generated_articles_state(realtime_channel);
CREATE INDEX idx_generated_articles_state_executing_step ON generated_articles_state(executing_step) WHERE executing_step IS NOT NULL;
CREATE INDEX idx_active_processes ON generated_articles_state(id, status, updated_at) WHERE status IN ('in_progress', 'user_input_required', 'paused');
```

### 3. process_events（プロセスイベントテーブル）

Supabase Realtimeイベントストリーミング用テーブル。

```sql
CREATE TABLE process_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    process_id UUID NOT NULL REFERENCES generated_articles_state(id) ON DELETE CASCADE,
    
    -- イベント詳細
    event_type TEXT NOT NULL,
    event_data JSONB NOT NULL DEFAULT '{}',
    event_sequence INTEGER NOT NULL,
    
    -- イベントメタデータ
    created_at TIMESTAMPTZ DEFAULT NOW(),
    published_at TIMESTAMPTZ,
    acknowledged_by TEXT[] DEFAULT '{}', -- ユーザーIDの配列
    delivery_attempts INTEGER DEFAULT 0,
    
    -- イベント分類
    event_category TEXT DEFAULT 'system',
    event_priority INTEGER DEFAULT 5,
    event_source TEXT DEFAULT 'backend',
    
    -- 保持・クリーンアップ
    expires_at TIMESTAMPTZ,
    archived BOOLEAN DEFAULT FALSE,
    
    -- プロセス内でのユニーク性保証
    CONSTRAINT unique_process_sequence UNIQUE(process_id, event_sequence)
);
```

**イベントタイプ例:**
- `process_created`: プロセス作成
- `step_started`, `step_completed`: ステップ開始・完了
- `user_input_required`, `user_input_resolved`: ユーザー入力要求・解決
- `generation_completed`: 生成完了
- `generation_error`: エラー発生

**インデックス:**
```sql
CREATE INDEX idx_process_events_process_id ON process_events(process_id);
CREATE INDEX idx_process_events_created_at ON process_events(created_at DESC);
CREATE INDEX idx_process_events_type ON process_events(event_type);
CREATE INDEX idx_recent_events ON process_events(process_id, event_sequence DESC, created_at DESC);
```

### 4. image_placeholders（画像プレースホルダーテーブル）

画像生成モード使用時の画像プレースホルダー管理。

```sql
CREATE TABLE image_placeholders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    article_id UUID REFERENCES articles(id) ON DELETE CASCADE,
    process_id UUID REFERENCES generated_articles_state(id) ON DELETE CASCADE,
    
    -- プレースホルダー情報
    placeholder_text TEXT NOT NULL,
    section_index INTEGER NOT NULL,
    position_in_section INTEGER NOT NULL,
    
    -- 画像生成設定
    generation_prompt TEXT,
    style_instructions TEXT,
    aspect_ratio TEXT DEFAULT '4:3',
    
    -- 生成状態
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'generating', 'completed', 'failed')),
    
    -- 生成結果
    generated_image_url TEXT,
    gcs_path TEXT,
    generation_metadata JSONB DEFAULT '{}',
    
    -- エラー情報
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    
    -- タイムスタンプ
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    generated_at TIMESTAMPTZ
);
```

**インデックス:**
```sql
CREATE INDEX idx_image_placeholders_article_id ON image_placeholders(article_id);
CREATE INDEX idx_image_placeholders_process_id ON image_placeholders(process_id);
CREATE INDEX idx_image_placeholders_status ON image_placeholders(status);
```

### 5. company_info（会社情報テーブル）

記事生成で使用する会社情報を保存。

```sql
CREATE TABLE company_info (
    id TEXT PRIMARY KEY DEFAULT (gen_random_uuid()::text),
    user_id TEXT NOT NULL,
    
    -- 基本情報
    name VARCHAR(200) NOT NULL,
    website_url VARCHAR(500) NOT NULL,
    description TEXT NOT NULL,
    usp TEXT NOT NULL,
    target_persona VARCHAR(50) NOT NULL,
    
    -- デフォルト設定
    is_default BOOLEAN DEFAULT FALSE NOT NULL,
    
    -- 詳細設定（オプション）
    brand_slogan VARCHAR(200),
    target_keywords VARCHAR(500),
    industry_terms VARCHAR(500),
    avoid_terms VARCHAR(500),
    popular_articles TEXT,
    target_area VARCHAR(200),
    
    -- タイムスタンプ
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

**主要フィールド説明:**
- `usp`: Unique Selling Proposition（独自の価値提案）
- `target_persona`: ターゲットペルソナ
- `is_default`: ユーザーのデフォルト会社情報
- `target_keywords`: SEO対象キーワード
- `avoid_terms`: 避けるべき用語

### 6. style_guide_templates（スタイルガイドテンプレート）

記事のトーン＆マナーを定義するテンプレート。

```sql
CREATE TABLE style_guide_templates (
    id TEXT PRIMARY KEY DEFAULT (gen_random_uuid()::text),
    user_id TEXT NOT NULL,
    
    -- テンプレート基本情報
    name VARCHAR(100) NOT NULL,
    description TEXT,
    is_default BOOLEAN DEFAULT FALSE,
    
    -- スタイル設定
    tone TEXT NOT NULL, -- 'formal', 'casual', 'friendly', 'professional'
    style TEXT NOT NULL, -- 'informative', 'persuasive', 'educational', 'conversational'
    target_audience TEXT NOT NULL, -- 'general', 'business', 'technical', 'beginner'
    
    -- 詳細ガイドライン
    writing_guidelines TEXT,
    vocabulary_preferences TEXT,
    sentence_structure_preferences TEXT,
    formatting_preferences TEXT,
    
    -- 使用禁止・推奨事項
    prohibited_words TEXT[],
    preferred_phrases TEXT[],
    brand_voice_keywords TEXT[],
    
    -- その他設定
    max_sentence_length INTEGER DEFAULT 50,
    paragraph_structure_preference TEXT,
    call_to_action_style TEXT,
    
    -- メタデータ
    template_metadata JSONB DEFAULT '{}',
    
    -- タイムスタンプ
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

## ログシステム関連テーブル

### 7. agent_log_sessions（エージェントログセッション）

記事生成セッション全体のログ管理。詳細は「06_seo_article_logging_system.md」を参照。

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
    
    -- セッション状態
    status TEXT NOT NULL DEFAULT 'started',
    total_steps INTEGER DEFAULT 0,
    completed_steps INTEGER DEFAULT 0,
    
    -- タイムスタンプ
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    
    -- メタデータ
    session_metadata JSONB DEFAULT '{}'
);
```

### 8. agent_execution_logs（エージェント実行ログ）

個別エージェントの実行記録。

```sql
CREATE TABLE agent_execution_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES agent_log_sessions(id) ON DELETE CASCADE,
    
    -- エージェント情報
    agent_name TEXT NOT NULL,
    agent_type TEXT NOT NULL,
    step_number INTEGER NOT NULL,
    sub_step_number INTEGER DEFAULT 1,
    
    -- 実行状態
    status TEXT NOT NULL DEFAULT 'started',
    
    -- データ
    input_data JSONB DEFAULT '{}',
    output_data JSONB DEFAULT '{}',
    
    -- モデル・トークン情報
    llm_model TEXT,
    llm_provider TEXT DEFAULT 'openai',
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    cache_tokens INTEGER DEFAULT 0,
    reasoning_tokens INTEGER DEFAULT 0,
    
    -- タイミング
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    duration_ms INTEGER,
    
    -- エラー情報
    error_message TEXT,
    error_details JSONB DEFAULT '{}'
);
```

### 9. llm_call_logs（LLM呼び出しログ）

個別のLLM API呼び出し詳細。

```sql
CREATE TABLE llm_call_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    execution_id UUID NOT NULL REFERENCES agent_execution_logs(id) ON DELETE CASCADE,
    
    -- 呼び出し情報
    call_sequence INTEGER NOT NULL DEFAULT 1,
    api_type TEXT NOT NULL DEFAULT 'chat_completions',
    model_name TEXT NOT NULL,
    provider TEXT NOT NULL DEFAULT 'openai',
    
    -- プロンプト・レスポンス
    system_prompt TEXT,
    user_prompt TEXT,
    full_prompt_data JSONB DEFAULT '{}',
    response_content TEXT,
    response_data JSONB DEFAULT '{}',
    
    -- 使用量
    prompt_tokens INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    cached_tokens INTEGER DEFAULT 0,
    reasoning_tokens INTEGER DEFAULT 0,
    
    -- メトリクス
    response_time_ms INTEGER,
    estimated_cost_usd DECIMAL(10, 6),
    http_status_code INTEGER,
    api_response_id TEXT,
    
    -- タイムスタンプ
    called_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- エラー情報
    error_type TEXT,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0
);
```

### 10. tool_call_logs（ツール呼び出しログ）

外部ツール（WebSearch、SerpAPI等）呼び出しログ。

```sql
CREATE TABLE tool_call_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    execution_id UUID NOT NULL REFERENCES agent_execution_logs(id) ON DELETE CASCADE,
    
    -- ツール情報
    tool_name TEXT NOT NULL,
    tool_function TEXT NOT NULL,
    call_sequence INTEGER NOT NULL DEFAULT 1,
    
    -- データ
    input_parameters JSONB DEFAULT '{}',
    output_data JSONB DEFAULT '{}',
    
    -- 実行状態
    status TEXT NOT NULL DEFAULT 'started',
    execution_time_ms INTEGER,
    data_size_bytes INTEGER,
    api_calls_count INTEGER DEFAULT 1,
    
    -- エラー情報
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

## Supabase機能統合

### Row Level Security (RLS)

全テーブルでRLSを有効化し、ユーザー・組織レベルでのアクセス制御を実装。

```sql
-- articles テーブルのRLS
ALTER TABLE articles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage their own articles" ON articles
    FOR ALL USING (
        user_id = current_setting('request.jwt.claims', true)::json->>'sub'
        OR 
        organization_id IN (
            SELECT organization_id FROM organization_members 
            WHERE user_id = current_setting('request.jwt.claims', true)::json->>'sub'
        )
    );

-- generated_articles_state テーブルのRLS
ALTER TABLE generated_articles_state ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can access their own generation processes" ON generated_articles_state
    FOR ALL USING (
        user_id = current_setting('request.jwt.claims', true)::json->>'sub'
        OR 
        organization_id IN (
            SELECT organization_id FROM organization_members 
            WHERE user_id = current_setting('request.jwt.claims', true)::json->>'sub'
        )
    );

-- process_events テーブルのRLS
ALTER TABLE process_events ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view events for their processes" ON process_events
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM generated_articles_state 
            WHERE id = process_events.process_id 
                AND user_id = current_setting('request.jwt.claims', true)::json->>'sub'
        )
    );
```

### Realtime Publication

```sql
-- Realtime購読対象テーブルの定義
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
    process_events,
    background_tasks,
    image_placeholders,
    company_info,
    style_guide_templates,
    agent_log_sessions,
    agent_execution_logs,
    llm_call_logs,
    tool_call_logs,
    workflow_step_logs;

-- Replica Identityの設定
ALTER TABLE process_events REPLICA IDENTITY FULL;
ALTER TABLE generated_articles_state REPLICA IDENTITY FULL;
ALTER TABLE image_placeholders REPLICA IDENTITY FULL;
```

## データベース関数

### 1. プロセス状態更新とイベント発行

```sql
-- プロセス状態更新時に自動的にイベントを発行
CREATE OR REPLACE FUNCTION publish_process_event()
RETURNS TRIGGER AS $$
DECLARE
    event_data JSONB;
    channel_name TEXT;
    next_sequence INTEGER;
    event_type_name TEXT;
BEGIN
    -- チャンネル名決定
    channel_name := 'process_' || NEW.id::text;
    
    -- イベントタイプ決定
    IF TG_OP = 'INSERT' THEN
        event_type_name := 'process_created';
    ELSIF TG_OP = 'UPDATE' THEN
        IF OLD.status IS DISTINCT FROM NEW.status THEN
            event_type_name := 'status_changed';
        ELSIF OLD.current_step_name IS DISTINCT FROM NEW.current_step_name THEN
            event_type_name := 'step_changed';
        ELSE
            event_type_name := 'process_updated';
        END IF;
    ELSE
        event_type_name := 'process_changed';
    END IF;
    
    -- イベントデータ構築
    event_data := jsonb_build_object(
        'process_id', NEW.id,
        'status', NEW.status,
        'current_step', NEW.current_step_name,
        'progress_percentage', NEW.progress_percentage,
        'is_waiting_for_input', NEW.is_waiting_for_input,
        'input_type', NEW.input_type,
        'updated_at', NEW.updated_at,
        'event_type', event_type_name,
        'user_id', NEW.user_id,
        'article_context', NEW.article_context
    );
    
    -- 次のシーケンス番号を取得
    SELECT COALESCE(MAX(event_sequence), 0) + 1 
    INTO next_sequence
    FROM process_events 
    WHERE process_id = NEW.id;
    
    -- イベントレコード挿入
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
    
    -- Realtime フィールド更新
    NEW.realtime_channel := channel_name;
    NEW.last_realtime_event := event_data;
    NEW.updated_at := NOW();
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- トリガー作成
CREATE TRIGGER trigger_publish_process_event
    BEFORE INSERT OR UPDATE ON generated_articles_state
    FOR EACH ROW EXECUTE FUNCTION publish_process_event();
```

### 2. ユーザー入力管理

```sql
-- ユーザー入力待ち状態に設定
CREATE OR REPLACE FUNCTION mark_process_waiting_for_input(
    p_process_id UUID,
    p_input_type TEXT,
    p_timeout_minutes INTEGER DEFAULT 30
)
RETURNS VOID AS $$
BEGIN
    UPDATE generated_articles_state
    SET 
        is_waiting_for_input = TRUE,
        input_type = p_input_type,
        user_input_timeout = NOW() + INTERVAL '1 minute' * p_timeout_minutes,
        input_reminder_sent = FALSE,
        status = 'user_input_required'
    WHERE id = p_process_id;
    
    -- 対応するイベント作成
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
$$ LANGUAGE plpgsql;

-- ユーザー入力解決
CREATE OR REPLACE FUNCTION resolve_user_input(
    p_process_id UUID,
    p_user_response JSONB
)
RETURNS VOID AS $$
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
    
    -- 対応するイベント作成
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
$$ LANGUAGE plpgsql;
```

### 3. ステップ履歴管理

```sql
-- ステップ履歴に追加
CREATE OR REPLACE FUNCTION add_step_to_history(
    process_id UUID,
    step_name TEXT,
    step_status TEXT,
    step_data JSONB DEFAULT '{}'::jsonb
)
RETURNS VOID AS $$
DECLARE
    new_step JSONB;
    current_history JSONB;
BEGIN
    -- 新しいステップエントリ作成
    new_step := jsonb_build_object(
        'step_name', step_name,
        'status', step_status,
        'timestamp', NOW(),
        'data', step_data
    );
    
    -- 現在の履歴取得
    SELECT COALESCE(step_history, '[]'::jsonb) INTO current_history
    FROM generated_articles_state
    WHERE id = process_id;
    
    -- 履歴に追加
    UPDATE generated_articles_state
    SET step_history = current_history || new_step
    WHERE id = process_id;
END;
$$ LANGUAGE plpgsql;
```

## パフォーマンス最適化

### インデックス戦略

```sql
-- 複合インデックス（クエリパフォーマンス向上）
CREATE INDEX idx_articles_user_status_created ON articles(user_id, status, created_at DESC);
CREATE INDEX idx_generated_articles_state_user_status_updated ON generated_articles_state(user_id, status, updated_at DESC);

-- 部分インデックス（条件付きクエリ最適化）
CREATE INDEX idx_active_processes ON generated_articles_state(id, status, updated_at)
    WHERE status IN ('in_progress', 'user_input_required', 'paused');

CREATE INDEX idx_events_cleanup ON process_events(created_at, archived)
    WHERE archived = FALSE;

-- JSONB インデックス（記事コンテキスト検索）
CREATE INDEX idx_article_context_gin ON generated_articles_state USING GIN (article_context);
CREATE INDEX idx_process_metadata_gin ON generated_articles_state USING GIN (process_metadata);
```

### パーティショニング戦略（大規模運用時）

```sql
-- process_events テーブルの月次パーティション（例）
CREATE TABLE process_events_2025_01 PARTITION OF process_events
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

CREATE TABLE process_events_2025_02 PARTITION OF process_events
    FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');
```

## データ保持・アーカイブ戦略

### 自動クリーンアップ

```sql
-- 古いプロセスイベントのクリーンアップ
CREATE OR REPLACE FUNCTION cleanup_old_events(days_old INTEGER DEFAULT 7)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
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

-- 完了済みプロセスのクリーンアップ
CREATE OR REPLACE FUNCTION cleanup_old_processes(days_old INTEGER DEFAULT 30)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM generated_articles_state
    WHERE status IN ('completed', 'cancelled')
        AND updated_at < (NOW() - INTERVAL '1 day' * days_old);
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;
```

### 定期メンテナンス

```sql
-- 毎日実行するメンテナンススクリプト
CREATE OR REPLACE FUNCTION daily_maintenance()
RETURNS TEXT AS $$
DECLARE
    cleaned_events INTEGER;
    cleaned_processes INTEGER;
    result TEXT;
BEGIN
    -- イベントクリーンアップ
    SELECT cleanup_old_events(7) INTO cleaned_events;
    
    -- プロセスクリーンアップ
    SELECT cleanup_old_processes(30) INTO cleaned_processes;
    
    -- 統計更新
    ANALYZE articles;
    ANALYZE generated_articles_state;
    ANALYZE process_events;
    
    result := format('Maintenance completed: %s events cleaned, %s processes cleaned', 
                    cleaned_events, cleaned_processes);
    
    RETURN result;
END;
$$ LANGUAGE plpgsql;
```

## 監視とメトリクス

### システム監視用ビュー

```sql
-- アクティブプロセス監視
CREATE VIEW active_processes_summary AS
SELECT 
    status,
    COUNT(*) as process_count,
    AVG(progress_percentage) as avg_progress,
    MIN(created_at) as oldest_process,
    MAX(updated_at) as latest_activity
FROM generated_articles_state
WHERE status IN ('in_progress', 'user_input_required', 'paused')
GROUP BY status;

-- エラー傾向分析
CREATE VIEW error_trends AS
SELECT 
    DATE_TRUNC('hour', created_at) as error_hour,
    COUNT(*) as error_count,
    array_agg(DISTINCT error_message) as error_types
FROM generated_articles_state
WHERE status = 'error'
    AND created_at > NOW() - INTERVAL '24 hours'
GROUP BY DATE_TRUNC('hour', created_at)
ORDER BY error_hour DESC;

-- 処理性能メトリクス
CREATE VIEW performance_metrics AS
SELECT 
    current_step_name,
    COUNT(*) as step_executions,
    AVG(EXTRACT(EPOCH FROM (updated_at - created_at))) as avg_duration_seconds,
    MIN(EXTRACT(EPOCH FROM (updated_at - created_at))) as min_duration_seconds,
    MAX(EXTRACT(EPOCH FROM (updated_at - created_at))) as max_duration_seconds
FROM generated_articles_state
WHERE status = 'completed'
    AND created_at > NOW() - INTERVAL '7 days'
GROUP BY current_step_name;
```

## まとめ

本データベース設計は、SEO記事生成機能の複雑な要求を満たしながら、スケーラビリティ、保守性、監視可能性を確保しています。Supabase Realtimeとの密接な統合により、リアルタイムな状態同期と効率的なユーザー体験を実現します。
