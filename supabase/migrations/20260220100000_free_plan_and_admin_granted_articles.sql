-- =============================================================
-- Free Plan + Admin Granted Articles
-- =============================================================
-- 1. Add 'free' plan tier (10 articles/month, no cost)
-- 2. Add admin_granted_articles column to usage_tracking
-- 3. Update increment_usage_if_allowed() to include admin_granted_articles
-- 4. Allow NULL stripe_price_id in plan_tiers (free plan has no Stripe price)

-- 1. Allow NULL stripe_price_id (free plan has no Stripe price)
ALTER TABLE plan_tiers ALTER COLUMN stripe_price_id DROP NOT NULL;

-- 2. Insert 'free' plan tier
INSERT INTO plan_tiers (id, name, stripe_price_id, monthly_article_limit, addon_unit_amount, price_amount, display_order, is_active)
VALUES ('free', 'フリープラン', NULL, 10, 0, 0, 0, true)
ON CONFLICT (id) DO NOTHING;

-- 3. Add admin_granted_articles to usage_tracking
ALTER TABLE usage_tracking ADD COLUMN IF NOT EXISTS admin_granted_articles INTEGER DEFAULT 0 NOT NULL;

-- 4. Update increment_usage_if_allowed() to include admin_granted_articles in total limit
CREATE OR REPLACE FUNCTION "public"."increment_usage_if_allowed"("p_tracking_id" "uuid") RETURNS TABLE("new_count" integer, "was_allowed" boolean)
    LANGUAGE "plpgsql"
    AS $$
DECLARE
    v_rec usage_tracking%ROWTYPE;
BEGIN
    -- FOR UPDATE でロックを取得
    SELECT * INTO v_rec FROM usage_tracking WHERE id = p_tracking_id FOR UPDATE;

    IF NOT FOUND THEN
        RETURN QUERY SELECT 0, FALSE;
        RETURN;
    END IF;

    -- total_limit = articles_limit + addon_articles_limit + admin_granted_articles
    IF v_rec.articles_generated < (v_rec.articles_limit + v_rec.addon_articles_limit + v_rec.admin_granted_articles) THEN
        UPDATE usage_tracking
        SET articles_generated = articles_generated + 1, updated_at = NOW()
        WHERE id = p_tracking_id;
        RETURN QUERY SELECT v_rec.articles_generated + 1, TRUE;
    ELSE
        RETURN QUERY SELECT v_rec.articles_generated, FALSE;
    END IF;
END;
$$;
