-- 組織・チーム管理システム用のデータベーステーブル
-- 作成日: 2025-01-03
-- 目的: Clerkの組織機能と連携したシート制サブスクリプション管理

-- 1. 組織情報テーブル (Clerk Organizationsと連携)
CREATE TABLE organizations (
    id TEXT PRIMARY KEY, -- Clerk Organization ID (org_xxxxx形式)
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL, -- URL用スラッグ
    owner_user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    max_seats INTEGER NOT NULL DEFAULT 1, -- 購入済みシート数
    used_seats INTEGER NOT NULL DEFAULT 1, -- 使用中シート数
    subscription_status TEXT DEFAULT 'inactive', -- inactive, active, past_due, canceled
    stripe_customer_id TEXT, -- Stripe Customer ID
    stripe_subscription_id TEXT, -- Stripe Subscription ID
    billing_email TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. 組織メンバーシップテーブル (Clerk Membershipsと連携)
CREATE TABLE organization_memberships (
    id TEXT PRIMARY KEY, -- Clerk Membership ID (mem_xxxxx形式)
    organization_id TEXT REFERENCES organizations(id) ON DELETE CASCADE NOT NULL,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    role TEXT NOT NULL DEFAULT 'member', -- owner, admin, member
    status TEXT NOT NULL DEFAULT 'active', -- active, invited, suspended
    invited_by UUID REFERENCES auth.users(id),
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(organization_id, user_id)
);

-- 3. 組織レベルの設定テーブル
CREATE TABLE organization_settings (
    organization_id TEXT PRIMARY KEY REFERENCES organizations(id) ON DELETE CASCADE,
    default_company_name TEXT,
    default_company_description TEXT,
    default_style_guide TEXT,
    default_industry TEXT,
    branding_logo_url TEXT,
    branding_color_primary TEXT,
    branding_color_secondary TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. 個人プラン vs 組織プランの統合管理
CREATE TYPE subscription_type AS ENUM ('individual', 'team');
CREATE TYPE plan_tier AS ENUM ('free', 'basic', 'pro', 'enterprise');

-- 統合サブスクリプション管理
CREATE TABLE unified_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    -- 個人プラン用
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    -- 組織プラン用  
    organization_id TEXT REFERENCES organizations(id) ON DELETE CASCADE,
    
    subscription_type subscription_type NOT NULL,
    plan_tier plan_tier NOT NULL DEFAULT 'free',
    
    -- Stripe情報
    stripe_customer_id TEXT,
    stripe_subscription_id TEXT,
    stripe_price_id TEXT REFERENCES prices(id),
    
    -- シート制課金（組織プランの場合）
    seat_quantity INTEGER DEFAULT 1, -- 購入シート数
    seat_price_per_unit INTEGER, -- シート単価（セント）
    
    -- ステータス管理
    status subscription_status NOT NULL DEFAULT 'active',
    current_period_start TIMESTAMP WITH TIME ZONE,
    current_period_end TIMESTAMP WITH TIME ZONE,
    cancel_at_period_end BOOLEAN DEFAULT FALSE,
    
    -- 使用量制限
    monthly_article_limit INTEGER DEFAULT 5, -- 月間記事生成上限
    monthly_articles_used INTEGER DEFAULT 0, -- 今月の使用済み記事数
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- 制約：個人プランまたは組織プランのどちらか一方のみ
    CONSTRAINT check_subscription_type CHECK (
        (subscription_type = 'individual' AND user_id IS NOT NULL AND organization_id IS NULL) OR
        (subscription_type = 'team' AND user_id IS NULL AND organization_id IS NOT NULL)
    )
);

-- 5. 招待管理テーブル
CREATE TABLE organization_invitations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id TEXT REFERENCES organizations(id) ON DELETE CASCADE NOT NULL,
    email TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'member',
    invited_by UUID REFERENCES auth.users(id) NOT NULL,
    invitation_token TEXT UNIQUE NOT NULL,
    status TEXT DEFAULT 'pending', -- pending, accepted, expired, cancelled
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    accepted_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(organization_id, email)
);

-- 6. 既存テーブルに組織外部キー制約を追加
ALTER TABLE companies ADD CONSTRAINT fk_companies_organization 
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE;

ALTER TABLE article_projects ADD CONSTRAINT fk_article_projects_organization 
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE;

-- 8. 使用量トラッキング
CREATE TABLE usage_tracking (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    -- 個人または組織の使用量
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    organization_id TEXT REFERENCES organizations(id) ON DELETE CASCADE,
    
    -- 使用量データ
    resource_type TEXT NOT NULL, -- 'article_generation', 'serp_analysis', etc.
    usage_count INTEGER DEFAULT 1,
    billing_period_start DATE NOT NULL,
    billing_period_end DATE NOT NULL,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- 個人または組織のどちらか一方のみ
    CONSTRAINT check_usage_owner CHECK (
        (user_id IS NOT NULL AND organization_id IS NULL) OR
        (user_id IS NULL AND organization_id IS NOT NULL)
    )
);

-- インデックス作成
CREATE INDEX idx_organizations_owner ON organizations(owner_user_id);
CREATE INDEX idx_organizations_stripe_customer ON organizations(stripe_customer_id);
CREATE INDEX idx_organization_memberships_org ON organization_memberships(organization_id);
CREATE INDEX idx_organization_memberships_user ON organization_memberships(user_id);
CREATE INDEX idx_unified_subscriptions_user ON unified_subscriptions(user_id);
CREATE INDEX idx_unified_subscriptions_org ON unified_subscriptions(organization_id);
CREATE INDEX idx_unified_subscriptions_stripe ON unified_subscriptions(stripe_subscription_id);
CREATE INDEX idx_organization_invitations_org ON organization_invitations(organization_id);
CREATE INDEX idx_organization_invitations_token ON organization_invitations(invitation_token);
CREATE INDEX idx_usage_tracking_user_period ON usage_tracking(user_id, billing_period_start);
CREATE INDEX idx_usage_tracking_org_period ON usage_tracking(organization_id, billing_period_start);

-- Row Level Security (RLS) の有効化
ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE organization_memberships ENABLE ROW LEVEL SECURITY;
ALTER TABLE organization_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE unified_subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE organization_invitations ENABLE ROW LEVEL SECURITY;
ALTER TABLE usage_tracking ENABLE ROW LEVEL SECURITY;

-- RLS ポリシー作成

-- 組織: オーナーとメンバーがアクセス可能
CREATE POLICY "Organization members can access their organization" ON organizations
FOR ALL USING (
    id IN (
        SELECT organization_id FROM organization_memberships 
        WHERE user_id = auth.uid() AND status = 'active'
    ) OR owner_user_id = auth.uid()
);

-- 組織メンバーシップ: 同じ組織のメンバーが閲覧可能、オーナー・管理者が編集可能
CREATE POLICY "Organization members can view memberships" ON organization_memberships
FOR SELECT USING (
    organization_id IN (
        SELECT organization_id FROM organization_memberships 
        WHERE user_id = auth.uid() AND status = 'active'
    )
);

CREATE POLICY "Organization owners and admins can manage memberships" ON organization_memberships
FOR ALL USING (
    organization_id IN (
        SELECT organization_id FROM organization_memberships 
        WHERE user_id = auth.uid() AND status = 'active' AND role IN ('owner', 'admin')
    )
);

-- 組織設定: オーナーと管理者のみアクセス可能
CREATE POLICY "Organization owners and admins can manage settings" ON organization_settings
FOR ALL USING (
    organization_id IN (
        SELECT organization_id FROM organization_memberships 
        WHERE user_id = auth.uid() AND status = 'active' AND role IN ('owner', 'admin')
    )
);

-- 統合サブスクリプション: 個人は自分のみ、組織はメンバーが閲覧・オーナー/管理者が編集可能
CREATE POLICY "Users can access their own subscriptions" ON unified_subscriptions
FOR ALL USING (
    user_id = auth.uid() OR
    organization_id IN (
        SELECT organization_id FROM organization_memberships 
        WHERE user_id = auth.uid() AND status = 'active'
    )
);

-- 招待: 組織メンバーが閲覧、オーナー・管理者が管理可能
CREATE POLICY "Organization members can view invitations" ON organization_invitations
FOR SELECT USING (
    organization_id IN (
        SELECT organization_id FROM organization_memberships 
        WHERE user_id = auth.uid() AND status = 'active'
    )
);

CREATE POLICY "Organization owners and admins can manage invitations" ON organization_invitations
FOR ALL USING (
    organization_id IN (
        SELECT organization_id FROM organization_memberships 
        WHERE user_id = auth.uid() AND status = 'active' AND role IN ('owner', 'admin')
    )
);

-- 使用量トラッキング: 個人は自分のみ、組織はメンバーが閲覧可能
CREATE POLICY "Users can access their usage tracking" ON usage_tracking
FOR ALL USING (
    user_id = auth.uid() OR
    organization_id IN (
        SELECT organization_id FROM organization_memberships 
        WHERE user_id = auth.uid() AND status = 'active'
    )
);

-- 既存テーブルのRLSポリシー更新

-- 企業テーブル: 組織所有の場合は組織メンバーがアクセス可能
DROP POLICY IF EXISTS "Users can manage their own companies" ON companies;
CREATE POLICY "Users can manage companies" ON companies
FOR ALL USING (
    user_id = auth.uid() OR
    organization_id IN (
        SELECT organization_id FROM organization_memberships 
        WHERE user_id = auth.uid() AND status = 'active'
    )
);

-- プロジェクトテーブル: 組織所有の場合は組織メンバーがアクセス可能
DROP POLICY IF EXISTS "Users can manage their own projects" ON article_projects;
CREATE POLICY "Users can manage projects" ON article_projects
FOR ALL USING (
    user_id = auth.uid() OR
    organization_id IN (
        SELECT organization_id FROM organization_memberships 
        WHERE user_id = auth.uid() AND status = 'active'
    )
);

-- その他の関連テーブルのポリシーも組織対応に更新
DROP POLICY IF EXISTS "Users can access serp analyses for their projects" ON serp_analyses;
CREATE POLICY "Users can access serp analyses for their projects" ON serp_analyses
FOR ALL USING (EXISTS (
  SELECT 1 FROM article_projects 
  WHERE article_projects.id = serp_analyses.project_id 
  AND (
    article_projects.user_id = auth.uid() OR
    article_projects.organization_id IN (
        SELECT organization_id FROM organization_memberships 
        WHERE user_id = auth.uid() AND status = 'active'
    )
  )
));

-- 自動更新トリガー
CREATE TRIGGER update_organizations_updated_at BEFORE UPDATE ON organizations
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_organization_settings_updated_at BEFORE UPDATE ON organization_settings
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_unified_subscriptions_updated_at BEFORE UPDATE ON unified_subscriptions
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 組織のシート使用量を自動更新する関数
CREATE OR REPLACE FUNCTION update_organization_seat_usage()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        -- メンバー追加時、使用シート数を増加
        UPDATE organizations 
        SET used_seats = used_seats + 1 
        WHERE id = NEW.organization_id;
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        -- メンバー削除時、使用シート数を減少
        UPDATE organizations 
        SET used_seats = used_seats - 1 
        WHERE id = OLD.organization_id;
        RETURN OLD;
    ELSIF TG_OP = 'UPDATE' THEN
        -- ステータス変更時の処理
        IF OLD.status = 'active' AND NEW.status != 'active' THEN
            UPDATE organizations 
            SET used_seats = used_seats - 1 
            WHERE id = NEW.organization_id;
        ELSIF OLD.status != 'active' AND NEW.status = 'active' THEN
            UPDATE organizations 
            SET used_seats = used_seats + 1 
            WHERE id = NEW.organization_id;
        END IF;
        RETURN NEW;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_organization_seat_usage
AFTER INSERT OR UPDATE OR DELETE ON organization_memberships
FOR EACH ROW EXECUTE FUNCTION update_organization_seat_usage();

-- シート制限チェック関数
CREATE OR REPLACE FUNCTION check_seat_limit()
RETURNS TRIGGER AS $$
DECLARE
    org_max_seats INTEGER;
    org_used_seats INTEGER;
BEGIN
    -- 新しいメンバー追加時のみチェック
    IF TG_OP = 'INSERT' OR (TG_OP = 'UPDATE' AND OLD.status != 'active' AND NEW.status = 'active') THEN
        SELECT max_seats, used_seats INTO org_max_seats, org_used_seats
        FROM organizations 
        WHERE id = NEW.organization_id;
        
        IF org_used_seats >= org_max_seats THEN
            RAISE EXCEPTION 'Cannot add member: organization has reached maximum seat limit (% / %)', org_used_seats, org_max_seats;
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_check_seat_limit
BEFORE INSERT OR UPDATE ON organization_memberships
FOR EACH ROW EXECUTE FUNCTION check_seat_limit();

-- リアルタイム機能の有効化（必要に応じて）
/*
ALTER PUBLICATION supabase_realtime ADD TABLE organizations;
ALTER PUBLICATION supabase_realtime ADD TABLE organization_memberships;
ALTER PUBLICATION supabase_realtime ADD TABLE organization_invitations;
ALTER PUBLICATION supabase_realtime ADD TABLE unified_subscriptions;
*/