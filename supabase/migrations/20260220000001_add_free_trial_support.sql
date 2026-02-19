-- ============================================
-- 無料トライアルサポート
-- ============================================

-- 1. user_subscription_status enum に 'trialing' を追加
-- PostgreSQL 12+ ではトランザクション内で ALTER TYPE ADD VALUE が可能
ALTER TYPE user_subscription_status ADD VALUE IF NOT EXISTS 'trialing' BEFORE 'active';

-- 2. user_subscriptions にトライアル追跡カラムを追加
ALTER TABLE user_subscriptions
  ADD COLUMN IF NOT EXISTS trial_end timestamptz,
  ADD COLUMN IF NOT EXISTS trial_granted_by text,
  ADD COLUMN IF NOT EXISTS trial_granted_at timestamptz;

-- 3. アクティブなトライアルを効率的に検索するためのインデックス
CREATE INDEX IF NOT EXISTS idx_user_subscriptions_trial_end
  ON user_subscriptions (trial_end)
  WHERE trial_end IS NOT NULL AND status = 'trialing';

-- 4. DB関数 update_subscription_from_stripe を更新
-- trialing を独立したステータスとして保存するように変更
CREATE OR REPLACE FUNCTION "public"."update_subscription_from_stripe"(
  "p_user_id" "text",
  "p_stripe_customer_id" "text",
  "p_stripe_subscription_id" "text",
  "p_status" "text",
  "p_current_period_end" timestamp with time zone,
  "p_cancel_at_period_end" boolean DEFAULT false
) RETURNS "public"."user_subscriptions"
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
DECLARE
    v_subscription_status user_subscription_status;
    v_result user_subscriptions%ROWTYPE;
BEGIN
    -- Stripeのステータスを内部ステータスにマッピング
    v_subscription_status := CASE p_status
        WHEN 'active' THEN 'active'::user_subscription_status
        WHEN 'trialing' THEN 'trialing'::user_subscription_status
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
    ON CONFLICT (user_id) DO UPDATE
    SET
        stripe_customer_id = EXCLUDED.stripe_customer_id,
        stripe_subscription_id = EXCLUDED.stripe_subscription_id,
        status = EXCLUDED.status,
        current_period_end = EXCLUDED.current_period_end,
        cancel_at_period_end = EXCLUDED.cancel_at_period_end,
        updated_at = now()
    RETURNING * INTO v_result;

    RETURN v_result;
END;
$$;
