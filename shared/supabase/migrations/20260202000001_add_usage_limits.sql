-- =====================================================
-- 利用上限システム: plan_tiers, usage_tracking, usage_logs
-- =====================================================

-- プラン定義マスタ
CREATE TABLE IF NOT EXISTS plan_tiers (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    stripe_price_id TEXT NOT NULL,
    monthly_article_limit INTEGER NOT NULL,
    addon_unit_amount INTEGER NOT NULL DEFAULT 20,
    price_amount INTEGER NOT NULL,
    display_order INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 初期データ（現行プランに対応）
-- NOTE: stripe_price_id は後から UPDATE plan_tiers SET stripe_price_id = 'price_xxx' WHERE id = 'default'; で設定すること
-- monthly_article_limit: 月間記事生成上限（プランの基本上限）
-- addon_unit_amount: アドオン1ユニットあたりの追加記事数
-- これらの値を変更すれば、全ユーザーの次回請求サイクルから新上限が適用される
INSERT INTO plan_tiers (id, name, stripe_price_id, monthly_article_limit, addon_unit_amount, price_amount, display_order)
VALUES ('default', '標準プラン', 'PLACEHOLDER', 30, 20, 29800, 1)
ON CONFLICT (id) DO NOTHING;

-- 利用量追跡テーブル
CREATE TABLE IF NOT EXISTS usage_tracking (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT,
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    billing_period_start TIMESTAMPTZ NOT NULL,
    billing_period_end TIMESTAMPTZ NOT NULL,
    articles_generated INTEGER NOT NULL DEFAULT 0,
    articles_limit INTEGER NOT NULL,
    addon_articles_limit INTEGER NOT NULL DEFAULT 0,
    plan_tier_id TEXT REFERENCES plan_tiers(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT chk_usage_owner CHECK (
        (user_id IS NOT NULL AND organization_id IS NULL) OR
        (user_id IS NULL AND organization_id IS NOT NULL)
    ),
    CONSTRAINT uq_usage_user_period UNIQUE (user_id, billing_period_start),
    CONSTRAINT uq_usage_org_period UNIQUE (organization_id, billing_period_start)
);

CREATE INDEX IF NOT EXISTS idx_usage_tracking_user_period
    ON usage_tracking(user_id, billing_period_end DESC) WHERE user_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_usage_tracking_org_period
    ON usage_tracking(organization_id, billing_period_end DESC) WHERE organization_id IS NOT NULL;

-- 利用量監査ログ
CREATE TABLE IF NOT EXISTS usage_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    usage_tracking_id UUID REFERENCES usage_tracking(id) ON DELETE CASCADE NOT NULL,
    user_id TEXT NOT NULL,
    generation_process_id TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_usage_logs_tracking ON usage_logs(usage_tracking_id);
CREATE INDEX IF NOT EXISTS idx_usage_logs_created ON usage_logs(created_at DESC);

-- 既存テーブルへの変更
ALTER TABLE user_subscriptions ADD COLUMN IF NOT EXISTS plan_tier_id TEXT REFERENCES plan_tiers(id) DEFAULT 'default';
ALTER TABLE user_subscriptions ADD COLUMN IF NOT EXISTS addon_quantity INTEGER NOT NULL DEFAULT 0;
ALTER TABLE organization_subscriptions ADD COLUMN IF NOT EXISTS plan_tier_id TEXT REFERENCES plan_tiers(id) DEFAULT 'default';
ALTER TABLE organization_subscriptions ADD COLUMN IF NOT EXISTS addon_quantity INTEGER NOT NULL DEFAULT 0;

-- =====================================================
-- 原子的インクリメント関数（競合条件防止）
-- =====================================================
CREATE OR REPLACE FUNCTION increment_usage_if_allowed(p_tracking_id UUID)
RETURNS TABLE(new_count INTEGER, was_allowed BOOLEAN) AS $$
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
$$ LANGUAGE plpgsql;

-- =====================================================
-- RLS ポリシー
-- =====================================================

-- plan_tiers: 誰でも読み取り可
ALTER TABLE plan_tiers ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Anyone can read plan tiers" ON plan_tiers FOR SELECT USING (true);

-- usage_tracking: service_role でアクセス (バックエンドから操作)
ALTER TABLE usage_tracking ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role full access to usage_tracking" ON usage_tracking FOR ALL USING (true);

-- usage_logs: service_role でアクセス
ALTER TABLE usage_logs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role full access to usage_logs" ON usage_logs FOR ALL USING (true);
