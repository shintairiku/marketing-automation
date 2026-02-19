-- =====================================================
-- ブログ生成状態テーブル
-- ブログAI機能の生成プロセス状態を管理（Realtime対応）
-- =====================================================

-- ブログ生成状態テーブル
CREATE TABLE IF NOT EXISTS blog_generation_state (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    organization_id UUID REFERENCES organizations(id) ON DELETE SET NULL,
    wordpress_site_id UUID REFERENCES wordpress_sites(id) ON DELETE SET NULL,

    -- プロセス状態
    status TEXT DEFAULT 'pending'
        CHECK (status IN ('pending', 'in_progress', 'completed', 'error', 'user_input_required', 'cancelled')),
    current_step_name TEXT,
    progress_percentage INTEGER DEFAULT 0 CHECK (progress_percentage >= 0 AND progress_percentage <= 100),

    -- ユーザー入力待ち
    is_waiting_for_input BOOLEAN DEFAULT FALSE,
    input_type TEXT,  -- 'additional_info', 'approve_draft', 'upload_image' など

    -- コンテキストデータ（JSON）
    blog_context JSONB DEFAULT '{}'::jsonb,

    -- ユーザー入力データ
    user_prompt TEXT,  -- どんな記事を作りたいか
    reference_url TEXT,  -- 参考記事URL

    -- アップロード画像管理
    uploaded_images JSONB DEFAULT '[]'::jsonb,  -- [{local_path, wp_media_id, wp_url, filename}]

    -- OpenAI Responses API
    response_id TEXT,  -- バックグラウンド実行用

    -- 結果
    draft_post_id INTEGER,
    draft_preview_url TEXT,
    draft_edit_url TEXT,
    error_message TEXT,

    -- Realtime
    realtime_channel TEXT,
    last_realtime_event JSONB,

    -- タイムスタンプ
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- インデックス
CREATE INDEX IF NOT EXISTS idx_blog_generation_user
    ON blog_generation_state(user_id);
CREATE INDEX IF NOT EXISTS idx_blog_generation_status
    ON blog_generation_state(status);
CREATE INDEX IF NOT EXISTS idx_blog_generation_site
    ON blog_generation_state(wordpress_site_id);
CREATE INDEX IF NOT EXISTS idx_blog_generation_channel
    ON blog_generation_state(realtime_channel);
CREATE INDEX IF NOT EXISTS idx_blog_generation_response_id
    ON blog_generation_state(response_id);

-- アクティブプロセス用部分インデックス
CREATE INDEX IF NOT EXISTS idx_blog_generation_active
    ON blog_generation_state(id, status, updated_at)
    WHERE status IN ('in_progress', 'user_input_required', 'pending');

-- Realtime有効化
ALTER TABLE blog_generation_state REPLICA IDENTITY FULL;

-- Realtime publicationに追加
DO $$
BEGIN
    -- publicationが存在するか確認して追加
    IF EXISTS (SELECT 1 FROM pg_publication WHERE pubname = 'supabase_realtime') THEN
        ALTER PUBLICATION supabase_realtime ADD TABLE blog_generation_state;
    END IF;
EXCEPTION WHEN duplicate_object THEN
    -- すでに追加されている場合は無視
    NULL;
END $$;

-- RLS有効化
ALTER TABLE blog_generation_state ENABLE ROW LEVEL SECURITY;

-- RLSポリシー
CREATE POLICY "Users can view their own blog generations"
    ON blog_generation_state FOR SELECT
    USING (user_id = current_setting('request.jwt.claims', true)::json->>'sub');

CREATE POLICY "Users can insert their own blog generations"
    ON blog_generation_state FOR INSERT
    WITH CHECK (user_id = current_setting('request.jwt.claims', true)::json->>'sub');

CREATE POLICY "Users can update their own blog generations"
    ON blog_generation_state FOR UPDATE
    USING (user_id = current_setting('request.jwt.claims', true)::json->>'sub');

CREATE POLICY "Users can delete their own blog generations"
    ON blog_generation_state FOR DELETE
    USING (user_id = current_setting('request.jwt.claims', true)::json->>'sub');

-- Service Role用ポリシー（バックエンド用）
CREATE POLICY "Service role has full access to blog_generation_state"
    ON blog_generation_state FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- updated_at自動更新トリガー
CREATE OR REPLACE FUNCTION update_blog_generation_state_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_blog_generation_state_updated_at
    BEFORE UPDATE ON blog_generation_state
    FOR EACH ROW
    EXECUTE FUNCTION update_blog_generation_state_updated_at();

-- =====================================================
-- ブログ生成イベントテーブル（Realtime用）
-- =====================================================
CREATE TABLE IF NOT EXISTS blog_process_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    process_id UUID NOT NULL REFERENCES blog_generation_state(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL,

    -- イベント情報
    event_type TEXT NOT NULL,
    event_data JSONB DEFAULT '{}'::jsonb,
    event_sequence INTEGER NOT NULL DEFAULT 0,

    -- タイムスタンプ
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- インデックス
CREATE INDEX IF NOT EXISTS idx_blog_process_events_process
    ON blog_process_events(process_id, event_sequence);
CREATE INDEX IF NOT EXISTS idx_blog_process_events_user
    ON blog_process_events(user_id);
CREATE INDEX IF NOT EXISTS idx_blog_process_events_created
    ON blog_process_events(created_at DESC);

-- Realtime有効化
ALTER TABLE blog_process_events REPLICA IDENTITY FULL;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_publication WHERE pubname = 'supabase_realtime') THEN
        ALTER PUBLICATION supabase_realtime ADD TABLE blog_process_events;
    END IF;
EXCEPTION WHEN duplicate_object THEN
    NULL;
END $$;

-- RLS有効化
ALTER TABLE blog_process_events ENABLE ROW LEVEL SECURITY;

-- RLSポリシー
CREATE POLICY "Users can view their own blog events"
    ON blog_process_events FOR SELECT
    USING (user_id = current_setting('request.jwt.claims', true)::json->>'sub');

CREATE POLICY "Service role has full access to blog_process_events"
    ON blog_process_events FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- コメント
COMMENT ON TABLE blog_generation_state IS 'ブログAI生成プロセスの状態管理';
COMMENT ON COLUMN blog_generation_state.blog_context IS 'エージェントのコンテキストデータ（JSON）';
COMMENT ON COLUMN blog_generation_state.response_id IS 'OpenAI Responses APIのレスポンスID（バックグラウンド実行用）';
COMMENT ON COLUMN blog_generation_state.uploaded_images IS 'アップロードされた画像情報の配列';
COMMENT ON TABLE blog_process_events IS 'ブログ生成プロセスのRealtimeイベント';
