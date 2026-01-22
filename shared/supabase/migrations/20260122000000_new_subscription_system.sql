-- ============================================================================
-- 新しいサブスクリプションシステム
-- 作成日: 2026-01-22
--
-- 目的:
-- - シンプルな1プラン構成（月額サブスクリプション）
-- - @shintairiku.jp ユーザーは特権アクセス（無料）
-- - Clerk User IDベースの設計
-- - 堅牢な決済失敗対応
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. サブスクリプション状態の列挙型
-- ----------------------------------------------------------------------------
DO $$ BEGIN
    CREATE TYPE user_subscription_status AS ENUM (
        'active',           -- 有効なサブスクリプション
        'past_due',         -- 支払い遅延（猶予期間中）
        'canceled',         -- キャンセル済み（期間終了まで利用可能）
        'expired',          -- 期限切れ
        'none'              -- サブスクリプションなし
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- ----------------------------------------------------------------------------
-- 2. メインのユーザーサブスクリプションテーブル
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_subscriptions (
    -- Clerk User ID（例: user_2y2DRx4Xb5PbvMVoVWmDluHCeFV）
    user_id TEXT PRIMARY KEY,

    -- Stripe関連
    stripe_customer_id TEXT UNIQUE,
    stripe_subscription_id TEXT UNIQUE,

    -- サブスクリプション状態
    status user_subscription_status NOT NULL DEFAULT 'none',

    -- 現在の請求期間終了日（この日付まで利用可能）
    current_period_end TIMESTAMP WITH TIME ZONE,

    -- 期間終了時にキャンセルするかどうか
    cancel_at_period_end BOOLEAN DEFAULT FALSE,

    -- @shintairiku.jp ユーザーの特権フラグ
    is_privileged BOOLEAN DEFAULT FALSE,

    -- ユーザーのメールアドレス（キャッシュ用）
    email TEXT,

    -- 作成・更新日時
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 更新日時の自動更新トリガー
CREATE OR REPLACE FUNCTION update_user_subscriptions_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_user_subscriptions_updated_at ON user_subscriptions;
CREATE TRIGGER trigger_update_user_subscriptions_updated_at
    BEFORE UPDATE ON user_subscriptions
    FOR EACH ROW
    EXECUTE FUNCTION update_user_subscriptions_updated_at();

-- ----------------------------------------------------------------------------
-- 3. サブスクリプションイベントログ（監査用）
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS subscription_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    event_type TEXT NOT NULL,  -- 'created', 'updated', 'canceled', 'payment_failed', 'payment_succeeded'
    stripe_event_id TEXT,      -- Stripe Event ID（重複防止用）
    event_data JSONB,          -- イベントの詳細データ
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Stripeイベントの重複防止用インデックス
CREATE UNIQUE INDEX IF NOT EXISTS idx_subscription_events_stripe_event_id
    ON subscription_events(stripe_event_id)
    WHERE stripe_event_id IS NOT NULL;

-- ユーザー別のイベント検索用インデックス
CREATE INDEX IF NOT EXISTS idx_subscription_events_user_id
    ON subscription_events(user_id);

-- ----------------------------------------------------------------------------
-- 4. RLS (Row Level Security) ポリシー
-- ----------------------------------------------------------------------------
ALTER TABLE user_subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscription_events ENABLE ROW LEVEL SECURITY;

-- user_subscriptions: ユーザーは自分のサブスクリプションのみ閲覧可能
DROP POLICY IF EXISTS "Users can view own subscription" ON user_subscriptions;
CREATE POLICY "Users can view own subscription" ON user_subscriptions
    FOR SELECT
    USING (
        user_id = current_setting('request.jwt.claims', true)::json->>'sub'
    );

-- subscription_events: サービスロールのみアクセス可能（監査ログ）
DROP POLICY IF EXISTS "Service role only for subscription events" ON subscription_events;
CREATE POLICY "Service role only for subscription events" ON subscription_events
    FOR ALL
    USING (false);  -- 通常ユーザーはアクセス不可、service_roleでのみアクセス

-- ----------------------------------------------------------------------------
-- 5. アクセス判定関数
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION has_active_access(p_user_id TEXT)
RETURNS BOOLEAN AS $$
DECLARE
    v_subscription user_subscriptions%ROWTYPE;
BEGIN
    -- サブスクリプション情報を取得
    SELECT * INTO v_subscription
    FROM user_subscriptions
    WHERE user_id = p_user_id;

    -- レコードが存在しない場合はアクセス不可
    IF NOT FOUND THEN
        RETURN FALSE;
    END IF;

    -- @shintairiku.jp 特権ユーザーは常にアクセス可能
    IF v_subscription.is_privileged = TRUE THEN
        RETURN TRUE;
    END IF;

    -- アクティブなサブスクリプション
    IF v_subscription.status = 'active' THEN
        RETURN TRUE;
    END IF;

    -- キャンセル済みでも期間内ならアクセス可能
    IF v_subscription.status = 'canceled'
       AND v_subscription.current_period_end > NOW() THEN
        RETURN TRUE;
    END IF;

    -- 支払い遅延でも猶予期間中はアクセス可能（3日間の猶予）
    IF v_subscription.status = 'past_due'
       AND v_subscription.current_period_end + INTERVAL '3 days' > NOW() THEN
        RETURN TRUE;
    END IF;

    RETURN FALSE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ----------------------------------------------------------------------------
-- 6. ユーザー作成時の自動レコード作成（Clerk Webhook用）
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION create_user_subscription_record(
    p_user_id TEXT,
    p_email TEXT
)
RETURNS user_subscriptions AS $$
DECLARE
    v_is_privileged BOOLEAN;
    v_result user_subscriptions%ROWTYPE;
BEGIN
    -- @shintairiku.jp ドメインかどうかをチェック
    v_is_privileged := p_email ILIKE '%@shintairiku.jp';

    -- レコードを挿入または更新
    INSERT INTO user_subscriptions (user_id, email, is_privileged, status)
    VALUES (p_user_id, p_email, v_is_privileged, 'none')
    ON CONFLICT (user_id) DO UPDATE SET
        email = EXCLUDED.email,
        is_privileged = EXCLUDED.is_privileged,
        updated_at = NOW()
    RETURNING * INTO v_result;

    RETURN v_result;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ----------------------------------------------------------------------------
-- 7. サブスクリプション更新関数（Stripe Webhook用）
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION update_subscription_from_stripe(
    p_user_id TEXT,
    p_stripe_customer_id TEXT,
    p_stripe_subscription_id TEXT,
    p_status TEXT,
    p_current_period_end TIMESTAMP WITH TIME ZONE,
    p_cancel_at_period_end BOOLEAN DEFAULT FALSE
)
RETURNS user_subscriptions AS $$
DECLARE
    v_subscription_status user_subscription_status;
    v_result user_subscriptions%ROWTYPE;
BEGIN
    -- Stripeのステータスを内部ステータスにマッピング
    v_subscription_status := CASE p_status
        WHEN 'active' THEN 'active'::user_subscription_status
        WHEN 'trialing' THEN 'active'::user_subscription_status  -- トライアルもactive扱い
        WHEN 'past_due' THEN 'past_due'::user_subscription_status
        WHEN 'canceled' THEN 'canceled'::user_subscription_status
        WHEN 'unpaid' THEN 'expired'::user_subscription_status
        WHEN 'incomplete' THEN 'none'::user_subscription_status
        WHEN 'incomplete_expired' THEN 'expired'::user_subscription_status
        WHEN 'paused' THEN 'canceled'::user_subscription_status
        ELSE 'none'::user_subscription_status
    END;

    -- レコードを更新（存在しない場合は作成）
    INSERT INTO user_subscriptions (
        user_id,
        stripe_customer_id,
        stripe_subscription_id,
        status,
        current_period_end,
        cancel_at_period_end
    )
    VALUES (
        p_user_id,
        p_stripe_customer_id,
        p_stripe_subscription_id,
        v_subscription_status,
        p_current_period_end,
        p_cancel_at_period_end
    )
    ON CONFLICT (user_id) DO UPDATE SET
        stripe_customer_id = EXCLUDED.stripe_customer_id,
        stripe_subscription_id = EXCLUDED.stripe_subscription_id,
        status = EXCLUDED.status,
        current_period_end = EXCLUDED.current_period_end,
        cancel_at_period_end = EXCLUDED.cancel_at_period_end,
        updated_at = NOW()
    RETURNING * INTO v_result;

    RETURN v_result;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ----------------------------------------------------------------------------
-- 8. Realtime有効化
-- ----------------------------------------------------------------------------
ALTER PUBLICATION supabase_realtime ADD TABLE user_subscriptions;

-- ----------------------------------------------------------------------------
-- 9. 初期データ（既存の@shintairiku.jpユーザーを特権化）
-- 注: 実際のユーザーIDは手動で追加するか、別途スクリプトで実行
-- ----------------------------------------------------------------------------
-- INSERT INTO user_subscriptions (user_id, email, is_privileged, status)
-- VALUES ('user_xxx', 'admin@shintairiku.jp', true, 'none')
-- ON CONFLICT (user_id) DO UPDATE SET is_privileged = true;

COMMENT ON TABLE user_subscriptions IS 'ユーザーのサブスクリプション状態を管理。Clerk User IDをプライマリキーとして使用。';
COMMENT ON TABLE subscription_events IS 'サブスクリプション関連イベントの監査ログ。Stripe Webhookイベントの重複防止にも使用。';
COMMENT ON FUNCTION has_active_access(TEXT) IS 'ユーザーがアクティブなアクセス権を持っているかを判定。特権ユーザーまたはアクティブなサブスクリプションでtrue。';
