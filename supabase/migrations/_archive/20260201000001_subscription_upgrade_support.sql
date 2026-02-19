-- ============================================================================
-- サブスクリプションアップグレードサポート
-- 作成日: 2026-02-01
--
-- 目的:
-- - 個人プラン→チームプランへのアップグレード時に
--   同一 Stripe Customer / Subscription を使い回すための追跡カラムを追加
-- - Stripe 公式推奨: subscriptions.update() による in-place 更新
-- ============================================================================

-- 1. organizations テーブル: 課金ユーザーの追跡
-- サブスクリプションの支払いを行うユーザーの Clerk User ID
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS billing_user_id text;

-- 2. user_subscriptions テーブル: チームへのアップグレード追跡
-- 個人サブスクがチームプランにアップグレードされた場合、対応する organization_id を記録
ALTER TABLE user_subscriptions ADD COLUMN IF NOT EXISTS upgraded_to_org_id uuid REFERENCES organizations(id);
