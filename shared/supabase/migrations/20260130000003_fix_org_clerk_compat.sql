/**
 * Organization テーブル Clerk 互換性修正
 *
 * 問題:
 *   - user_id カラムが uuid 型で auth.users を参照 → Clerk ID (text) と型不一致
 *   - RLS ポリシーが auth.uid() に依存 → Clerk 環境では常に NULL
 *
 * 修正:
 *   - auth.users への FK 制約を削除
 *   - user_id カラムを TEXT 型に変更（Clerk ID 格納用）
 *   - RLS ポリシーを削除（backend が service_role で操作するため不要）
 *   - organization_members に display_name, email カラム追加
 */

-- ============================================
-- 1. RLS ポリシーを全て削除
--    organization_members.user_id を参照する全テーブルのポリシーを含む
-- ============================================

-- organizations テーブル
DROP POLICY IF EXISTS "Organization owners can manage their organizations" ON organizations;
DROP POLICY IF EXISTS "Organization members can view their organizations" ON organizations;

-- organization_members テーブル
DROP POLICY IF EXISTS "Organization owners and admins can manage members" ON organization_members;
DROP POLICY IF EXISTS "Members can view organization memberships" ON organization_members;

-- invitations テーブル
DROP POLICY IF EXISTS "Organization owners and admins can manage invitations" ON invitations;
DROP POLICY IF EXISTS "Users can view invitations sent to them" ON invitations;

-- organization_subscriptions テーブル
DROP POLICY IF EXISTS "Organization owners and admins can view subscriptions" ON organization_subscriptions;

-- generated_articles_state テーブル（organization_members.user_id を参照）
DROP POLICY IF EXISTS "Organization members can view organization generations" ON generated_articles_state;
DROP POLICY IF EXISTS "Users can manage their own generation processes" ON generated_articles_state;
DROP POLICY IF EXISTS "Users can resume their own processes" ON generated_articles_state;

-- articles テーブル（organization_members.user_id を参照）
DROP POLICY IF EXISTS "Organization members can view organization articles" ON articles;
DROP POLICY IF EXISTS "Users can manage their own articles" ON articles;

-- article_generation_flows テーブル（organization_members.user_id を参照）
DROP POLICY IF EXISTS "Organization members can view organization flows" ON article_generation_flows;
DROP POLICY IF EXISTS "Organization admins can manage organization flows" ON article_generation_flows;
DROP POLICY IF EXISTS "Users can manage their own flows" ON article_generation_flows;
DROP POLICY IF EXISTS "Anyone can view template flows" ON article_generation_flows;
DROP POLICY IF EXISTS "Users can view flows they have access to" ON article_generation_flows;
DROP POLICY IF EXISTS "Users can manage flows they own or have admin access to" ON article_generation_flows;

-- flow_steps テーブル（organization_members.user_id を参照）
DROP POLICY IF EXISTS "Users can view flow steps they have access to" ON flow_steps;
DROP POLICY IF EXISTS "Users can manage flow steps they can manage" ON flow_steps;
DROP POLICY IF EXISTS "Users can manage flow steps they can manage" ON flow_steps;

-- style_guide_templates テーブル（organization_members.user_id を参照）
DROP POLICY IF EXISTS "Users can manage their own style guide templates" ON style_guide_templates;
DROP POLICY IF EXISTS "Organization members can view organization style templates" ON style_guide_templates;
DROP POLICY IF EXISTS "Organization admins can manage organization style templates" ON style_guide_templates;

-- images テーブル（organization_members.user_id を参照）
DROP POLICY IF EXISTS "Organization members can view organization images" ON images;
DROP POLICY IF EXISTS "Users can manage their own images" ON images;

-- agent_log_sessions テーブル（organization_members.user_id を参照）
DROP POLICY IF EXISTS "Users can access their own agent sessions" ON agent_log_sessions;

-- agent_execution_logs テーブル（agent_log_sessions 経由で organization_members.user_id を参照）
DROP POLICY IF EXISTS "Users can access execution logs for their sessions" ON agent_execution_logs;

-- llm_call_logs テーブル（agent_log_sessions 経由で organization_members.user_id を参照）
DROP POLICY IF EXISTS "Users can access llm logs for their sessions" ON llm_call_logs;

-- tool_call_logs テーブル（agent_log_sessions 経由で organization_members.user_id を参照）
DROP POLICY IF EXISTS "Users can access tool logs for their sessions" ON tool_call_logs;

-- workflow_step_logs テーブル（agent_log_sessions 経由で organization_members.user_id を参照）
DROP POLICY IF EXISTS "Users can access workflow logs for their sessions" ON workflow_step_logs;

-- ============================================
-- 2. organization_members の FK 削除 + 型変更
-- ============================================
ALTER TABLE organization_members DROP CONSTRAINT IF EXISTS organization_members_user_id_fkey;
ALTER TABLE organization_members ALTER COLUMN user_id TYPE text USING user_id::text;

-- display_name と email カラム追加（Clerk から取得した情報を格納）
ALTER TABLE organization_members ADD COLUMN IF NOT EXISTS display_name text;
ALTER TABLE organization_members ADD COLUMN IF NOT EXISTS email text;

-- ============================================
-- 3. organizations の FK 削除 + 型変更
-- ============================================
ALTER TABLE organizations DROP CONSTRAINT IF EXISTS organizations_owner_user_id_fkey;
ALTER TABLE organizations ALTER COLUMN owner_user_id TYPE text USING owner_user_id::text;

-- ============================================
-- 4. invitations の FK 削除 + 型変更
-- ============================================
ALTER TABLE invitations DROP CONSTRAINT IF EXISTS invitations_invited_by_user_id_fkey;
ALTER TABLE invitations ALTER COLUMN invited_by_user_id TYPE text USING invited_by_user_id::text;

-- ============================================
-- 5. organization_subscriptions の prices FK 削除
-- ============================================
ALTER TABLE organization_subscriptions DROP CONSTRAINT IF EXISTS organization_subscriptions_price_id_fkey;

-- ============================================
-- 6. トリガー関数を再作成（型変更に対応）
-- ============================================
CREATE OR REPLACE FUNCTION handle_new_organization()
RETURNS trigger AS $$
BEGIN
  INSERT INTO organization_members (organization_id, user_id, role)
  VALUES (new.id, new.owner_user_id, 'owner');
  RETURN new;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
