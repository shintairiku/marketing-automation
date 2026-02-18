-- =====================================================
-- WordPress連携テーブル
-- ブログAI機能でWordPress MCPと連携するためのサイト情報を管理
-- =====================================================

-- WordPress連携サイトテーブル
CREATE TABLE IF NOT EXISTS wordpress_sites (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    organization_id UUID REFERENCES organizations(id) ON DELETE SET NULL,

    -- サイト情報
    site_url TEXT NOT NULL,
    site_name TEXT,
    mcp_endpoint TEXT NOT NULL,

    -- 認証情報（AES-256-GCM暗号化）
    encrypted_credentials TEXT NOT NULL,

    -- 接続状態
    connection_status TEXT DEFAULT 'connected'
        CHECK (connection_status IN ('connected', 'disconnected', 'error')),
    is_active BOOLEAN DEFAULT FALSE,
    last_connected_at TIMESTAMP WITH TIME ZONE,
    last_used_at TIMESTAMP WITH TIME ZONE,
    last_error TEXT,

    -- メタデータ
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- ユニーク制約（同一ユーザーが同じサイトを複数登録しない）
    CONSTRAINT unique_site_per_user UNIQUE(user_id, site_url)
);

-- インデックス
CREATE INDEX IF NOT EXISTS idx_wordpress_sites_user_id
    ON wordpress_sites(user_id);
CREATE INDEX IF NOT EXISTS idx_wordpress_sites_status
    ON wordpress_sites(connection_status);
CREATE INDEX IF NOT EXISTS idx_wordpress_sites_org
    ON wordpress_sites(organization_id);

-- RLS有効化
ALTER TABLE wordpress_sites ENABLE ROW LEVEL SECURITY;

-- RLSポリシー: ユーザーは自分のサイトのみ管理可能
CREATE POLICY "Users can view their own WordPress sites"
    ON wordpress_sites FOR SELECT
    USING (user_id = current_setting('request.jwt.claims', true)::json->>'sub');

CREATE POLICY "Users can insert their own WordPress sites"
    ON wordpress_sites FOR INSERT
    WITH CHECK (user_id = current_setting('request.jwt.claims', true)::json->>'sub');

CREATE POLICY "Users can update their own WordPress sites"
    ON wordpress_sites FOR UPDATE
    USING (user_id = current_setting('request.jwt.claims', true)::json->>'sub');

CREATE POLICY "Users can delete their own WordPress sites"
    ON wordpress_sites FOR DELETE
    USING (user_id = current_setting('request.jwt.claims', true)::json->>'sub');

-- Service Role用ポリシー（バックエンド用）
CREATE POLICY "Service role has full access to wordpress_sites"
    ON wordpress_sites FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- updated_at自動更新トリガー
CREATE OR REPLACE FUNCTION update_wordpress_sites_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_wordpress_sites_updated_at
    BEFORE UPDATE ON wordpress_sites
    FOR EACH ROW
    EXECUTE FUNCTION update_wordpress_sites_updated_at();

-- コメント
COMMENT ON TABLE wordpress_sites IS 'WordPress MCP連携サイト情報';
COMMENT ON COLUMN wordpress_sites.encrypted_credentials IS 'AES-256-GCMで暗号化されたMCP認証情報（access_token, api_key, api_secret）';
COMMENT ON COLUMN wordpress_sites.connection_status IS '接続状態: connected, disconnected, error';
COMMENT ON COLUMN wordpress_sites.is_active IS '現在アクティブなサイト（複数サイト対応時に使用）';
