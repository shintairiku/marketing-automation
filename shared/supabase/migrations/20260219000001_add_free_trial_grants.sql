-- =============================================================================
-- Free Trial Grants: 管理者が特定ユーザーに無料トライアルを付与するための仕組み
-- =============================================================================

-- free_trial_grants テーブル
CREATE TABLE IF NOT EXISTS free_trial_grants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    stripe_coupon_id TEXT NOT NULL,
    duration_months INTEGER NOT NULL CHECK (duration_months > 0),
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'active', 'expired', 'revoked')),
    granted_by TEXT NOT NULL,
    note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    used_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ
);

-- インデックス
CREATE INDEX IF NOT EXISTS idx_free_trial_grants_user_id ON free_trial_grants(user_id);
CREATE INDEX IF NOT EXISTS idx_free_trial_grants_status ON free_trial_grants(status);

-- RLS
ALTER TABLE free_trial_grants ENABLE ROW LEVEL SECURITY;

-- service_role のみフルアクセス（管理者APIはservice_roleで実行）
CREATE POLICY "service_role_full_access_free_trial_grants"
    ON free_trial_grants
    FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');
