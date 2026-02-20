-- ============================================
-- Freemium プラン導入 + トライアル機能削除
-- ============================================

-- 1. トライアル追跡カラムを削除
ALTER TABLE user_subscriptions
  DROP COLUMN IF EXISTS trial_end,
  DROP COLUMN IF EXISTS trial_granted_by,
  DROP COLUMN IF EXISTS trial_granted_at;

-- 2. トライアル用インデックスを削除
DROP INDEX IF EXISTS idx_user_subscriptions_trial_end;

-- 3. 'free' プランティアを追加 (月10記事、無料、アドオンなし)
INSERT INTO plan_tiers (id, name, stripe_price_id, monthly_article_limit, addon_unit_amount, price_amount, display_order, is_active)
VALUES ('free', 'フリープラン', NULL, 10, 0, 0, 0, true)
ON CONFLICT (id) DO NOTHING;

-- 4. DB関数を更新: trialing → active にマッピング (トライアル廃止)
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
        WHEN 'trialing' THEN 'active'::user_subscription_status
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

-- 5. 既存の未登録ユーザーをフリープランに移行
-- status='none' かつ Stripe未連携のユーザーをアクティブなフリープランに変更
UPDATE user_subscriptions
SET status = 'active', plan_tier_id = 'free'
WHERE status = 'none' AND stripe_subscription_id IS NULL;

-- 6. 既存 trialing ユーザーもフリープランに移行
UPDATE user_subscriptions
SET status = 'active', plan_tier_id = 'free'
WHERE status = 'trialing' AND stripe_subscription_id IS NULL;

-- 7. フリープランユーザー用の usage_tracking を自動作成する関数
CREATE OR REPLACE FUNCTION ensure_free_plan_usage_tracking()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_tier RECORD;
    v_period_start timestamptz;
    v_period_end timestamptz;
    v_existing_id uuid;
BEGIN
    -- フリープランの場合のみ
    IF NEW.plan_tier_id = 'free' AND NEW.status = 'active' THEN
        -- 現在の月初・月末を計算
        v_period_start := date_trunc('month', now());
        v_period_end := (date_trunc('month', now()) + interval '1 month');

        -- 既に今月のトラッキングがあるか確認
        SELECT id INTO v_existing_id
        FROM usage_tracking
        WHERE user_id = NEW.user_id
          AND billing_period_start <= now()
          AND billing_period_end > now()
        LIMIT 1;

        IF v_existing_id IS NULL THEN
            -- plan_tiers から上限を取得
            SELECT monthly_article_limit, addon_unit_amount
            INTO v_tier
            FROM plan_tiers
            WHERE id = 'free';

            -- usage_tracking を作成
            INSERT INTO usage_tracking (
                user_id,
                billing_period_start,
                billing_period_end,
                articles_generated,
                articles_limit,
                addon_articles_limit,
                plan_tier_id
            )
            VALUES (
                NEW.user_id,
                v_period_start,
                v_period_end,
                0,
                COALESCE(v_tier.monthly_article_limit, 10),
                0,
                'free'
            )
            ON CONFLICT (user_id, billing_period_start) DO NOTHING;
        END IF;
    END IF;

    RETURN NEW;
END;
$$;

-- 8. トリガー: user_subscriptions の INSERT/UPDATE 時に usage_tracking を自動作成
DROP TRIGGER IF EXISTS trg_ensure_free_plan_usage ON user_subscriptions;
CREATE TRIGGER trg_ensure_free_plan_usage
    AFTER INSERT OR UPDATE ON user_subscriptions
    FOR EACH ROW
    EXECUTE FUNCTION ensure_free_plan_usage_tracking();

-- 9. 既存フリープランユーザーの usage_tracking を一括作成
INSERT INTO usage_tracking (user_id, billing_period_start, billing_period_end, articles_generated, articles_limit, addon_articles_limit, plan_tier_id)
SELECT
    us.user_id,
    date_trunc('month', now()),
    date_trunc('month', now()) + interval '1 month',
    0,
    COALESCE(pt.monthly_article_limit, 10),
    0,
    'free'
FROM user_subscriptions us
LEFT JOIN plan_tiers pt ON pt.id = 'free'
WHERE us.plan_tier_id = 'free'
  AND us.status = 'active'
  AND NOT EXISTS (
    SELECT 1 FROM usage_tracking ut
    WHERE ut.user_id = us.user_id
      AND ut.billing_period_start <= now()
      AND ut.billing_period_end > now()
  )
ON CONFLICT (user_id, billing_period_start) DO NOTHING;
