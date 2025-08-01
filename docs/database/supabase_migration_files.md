# Supabaseマイグレーションファイルの仕様

## 概要

このドキュメントでは、`frontend/supabase/migrations`ディレクトリに格納されているSQLマイグレーションファイルについて詳細に解説します。Supabase CLIによって管理されるこれらのファイルが、データベースのテーブル定義、RLS（Row Level Security）ポリシー、トリガー、ファンクションをどのように定義・変更しているか、主要なマイグレーションの目的と内容を解説します。

## マイグレーションシステム概要

### Supabase CLI マイグレーション管理
```bash
# マイグレーション関連コマンド
supabase migration new <migration_name>     # 新しいマイグレーション作成
supabase migration up --linked             # マイグレーション実行
supabase migration squash --linked         # マイグレーション統合
npm run generate-types                      # TypeScript型生成
```

### マイグレーションファイル命名規則
```
YYYYMMDDHHMMSS_migration_name.sql

例:
20240115041359_init.sql                    # 初期セットアップ
20250105000000_fix_user_id_for_clerk.sql   # Clerk対応
20250727000000_supabase_realtime_migration.sql # Realtime機能
```

## 主要マイグレーションファイル詳細

### 1. 初期セットアップ (`20240115041359_init.sql`)

#### Stripeユーザー・商品管理
```sql
-- ユーザーテーブル
create table users (
  id uuid references auth.users not null primary key,
  full_name text,
  avatar_url text,
  billing_address jsonb,
  payment_method jsonb
);

-- 商品テーブル（Stripe連携）
create table products (
  id text primary key,          -- Stripe Product ID
  active boolean,
  name text,
  description text,
  image text,
  metadata jsonb
);

-- 価格テーブル（Stripe連携）
create table prices (
  id text primary key,          -- Stripe Price ID
  product_id text references products,
  active boolean,
  currency text check (char_length(currency) = 3),
  unit_amount bigint,
  type pricing_type,
  interval pricing_plan_interval
);
```

**特徴**:
- **Stripe統合**: 商品・価格・顧客情報の同期
- **JSONB活用**: 柔軟なメタデータ保存
- **RLS設定**: ユーザーデータのアクセス制御

#### サブスクリプション管理
```sql
-- サブスクリプションテーブル
create table subscriptions (
  id text primary key,          -- Stripe Subscription ID
  user_id uuid references auth.users not null,
  status subscription_status,
  metadata jsonb,
  price_id text references prices,
  quantity integer,
  cancel_at_period_end boolean,
  created timestamp with time zone default timezone('utc'::text, now()) not null,
  current_period_start timestamp with time zone default timezone('utc'::text, now()) not null,
  current_period_end timestamp with time zone default timezone('utc'::text, now()) not null,
  ended_at timestamp with time zone default timezone('utc'::text, now()),
  cancel_at timestamp with time zone default timezone('utc'::text, now()),
  canceled_at timestamp with time zone default timezone('utc'::text, now()),
  trial_start timestamp with time zone default timezone('utc'::text, now()),
  trial_end timestamp with time zone default timezone('utc'::text, now())
);
```

### 2. Clerk認証対応 (`20250105000000_fix_user_id_for_clerk.sql`)

#### ユーザーID型変更
```sql
-- company_info テーブルのuser_id型をUUIDからTEXTに変更
ALTER TABLE company_info ALTER COLUMN user_id TYPE TEXT;

-- generated_articles_state テーブルのuser_id型をUUIDからTEXTに変更  
ALTER TABLE generated_articles_state ALTER COLUMN user_id TYPE TEXT;

-- images テーブルのuser_id型をUUIDからTEXTに変更
ALTER TABLE images ALTER COLUMN user_id TYPE TEXT;
```

**変更理由**:
- **Clerk互換性**: Clerk JWTの`sub`クレームは文字列形式
- **RLS対応**: `auth.uid()::text`での比較を可能に
- **統一性**: 全てのuser_idカラムを文字列型に統一

#### RLSポリシー更新
```sql
-- 修正されたRLSポリシー例
CREATE POLICY "Users can manage their own company info" ON company_info
  FOR ALL USING (user_id = current_setting('request.jwt.claims', true)::json->>'sub');
```

### 3. 組織管理システム (`20250605152002_organizations.sql`)

#### 組織テーブル設計
```sql
-- 組織テーブル
create table organizations (
  id uuid default gen_random_uuid() primary key,
  name text not null,
  owner_user_id uuid references auth.users not null,
  clerk_organization_id text unique,     -- Clerk連携用
  stripe_customer_id text,               -- Stripe連携用
  created_at timestamp with time zone default timezone('utc'::text, now()) not null,
  updated_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- 組織メンバーテーブル
create type organization_role as enum ('owner', 'admin', 'member');

create table organization_members (
  organization_id uuid references organizations(id) on delete cascade,
  user_id uuid references auth.users on delete cascade,
  primary key (organization_id, user_id),
  role organization_role not null default 'member',
  clerk_membership_id text,              -- Clerk連携用
  joined_at timestamp with time zone default timezone('utc'::text, now()) not null
);
```

**設計特徴**:
- **階層権限**: owner > admin > member
- **Clerk統合**: clerk_organization_id、clerk_membership_id
- **Stripe統合**: 組織レベルでの課金管理
- **カスケード削除**: 組織削除時のメンバー情報自動削除

#### 招待システム
```sql
-- 招待テーブル
create table invitations (
  id uuid default gen_random_uuid() primary key,
  organization_id uuid references organizations(id) on delete cascade not null,
  email text not null,
  role organization_role not null default 'member',
  invited_by uuid references auth.users not null,
  token text unique not null,            -- 招待トークン
  accepted boolean default false,
  expires_at timestamp with time zone not null,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);
```

### 4. 記事生成システム強化 (`20250617000000_enhance_article_generation.sql`)

#### 状態管理拡張
```sql
-- generated_articles_state テーブル拡張
ALTER TABLE generated_articles_state 
ADD COLUMN IF NOT EXISTS current_step_name TEXT,
ADD COLUMN IF NOT EXISTS progress_percentage INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS is_waiting_for_input BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS input_type TEXT,
ADD COLUMN IF NOT EXISTS last_activity_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, now()),
ADD COLUMN IF NOT EXISTS auto_resume_eligible BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS resume_from_step TEXT,
ADD COLUMN IF NOT EXISTS step_history JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS process_metadata JSONB DEFAULT '{}'::jsonb;
```

#### ステップ履歴管理機能
```sql
-- ステップ履歴追加関数
CREATE OR REPLACE FUNCTION add_step_to_history(
    process_id UUID,
    step_name TEXT,
    step_status TEXT,
    step_data JSONB DEFAULT '{}'::jsonb
)
RETURNS VOID AS $$
DECLARE
    new_step JSONB;
    current_history JSONB;
BEGIN
    -- 新しいステップエントリ作成
    new_step := jsonb_build_object(
        'step_name', step_name,
        'status', step_status,
        'timestamp', TIMEZONE('utc'::text, now()),
        'data', step_data
    );
    
    -- 現在の履歴取得
    SELECT COALESCE(step_history, '[]'::jsonb) INTO current_history
    FROM generated_articles_state 
    WHERE id = process_id;
    
    -- 履歴に新しいステップを追加
    UPDATE generated_articles_state 
    SET step_history = current_history || new_step::jsonb
    WHERE id = process_id;
END;
$$ LANGUAGE plpgsql;
```

### 5. 画像管理システム (`20250620000000_add_image_placeholders.sql`)

#### 画像プレースホルダー管理
```sql
-- 画像プレースホルダーテーブル
CREATE TABLE image_placeholders (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  article_id UUID REFERENCES articles(id) ON DELETE CASCADE,
  placeholder_id TEXT NOT NULL,          -- 記事内のプレースホルダーID
  description_jp TEXT NOT NULL,          -- 日本語説明
  prompt_en TEXT NOT NULL,               -- 英語生成プロンプト
  position_index INTEGER NOT NULL,       -- 記事内の位置
  status TEXT DEFAULT 'pending',         -- 'pending', 'generating', 'completed', 'replaced'
  generated_image_id UUID REFERENCES images(id),
  replaced_with_image_id UUID REFERENCES images(id),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**管理機能**:
- **プレースホルダー追跡**: 記事内の画像位置とステータス管理
- **生成・置換管理**: AI生成画像と手動アップロード画像の区別
- **位置管理**: 記事内での画像の順序管理

### 6. 会社情報管理 (`20250702000000_add_company_info.sql`)

#### 会社情報テーブル設計
```sql
CREATE TABLE IF NOT EXISTS company_info (
  id TEXT PRIMARY KEY DEFAULT (gen_random_uuid()::text),
  user_id TEXT NOT NULL,                 -- Clerk対応のため文字列型
  
  -- 必須フィールド
  name VARCHAR(200) NOT NULL,
  website_url VARCHAR(500) NOT NULL,
  description TEXT NOT NULL,
  usp TEXT NOT NULL,                     -- Unique Selling Proposition
  target_persona VARCHAR(50) NOT NULL,
  
  -- デフォルト設定
  is_default BOOLEAN DEFAULT FALSE NOT NULL,
  
  -- オプションフィールド
  brand_slogan VARCHAR(200),
  target_keywords VARCHAR(500),
  industry_terms VARCHAR(500),
  avoid_terms VARCHAR(500),
  popular_articles TEXT,
  target_area VARCHAR(200),
  
  created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, now()) NOT NULL,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, now()) NOT NULL
);
```

**ビジネス価値**:
- **記事生成コンテキスト**: SEO記事生成時の企業情報提供
- **パーソナライゼーション**: 企業固有の文体・トーン設定
- **SEO最適化**: 企業特有のキーワード・用語管理

### 7. スタイルガイドテンプレート (`20250702000001_add_style_guide_templates.sql`)

#### テンプレートシステム設計
```sql
-- スタイルテンプレート種別
CREATE TYPE style_template_type AS ENUM (
  'writing_tone',      -- 文体・トーン
  'vocabulary',        -- 語彙・用語
  'structure',         -- 構造・形式
  'branding',          -- ブランディング
  'seo_focus',         -- SEO重点
  'custom'             -- カスタム
);

-- スタイルガイドテンプレートテーブル
CREATE TABLE style_guide_templates (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES auth.users NOT NULL,
  organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  description TEXT,
  template_type style_template_type DEFAULT 'custom',
  settings JSONB NOT NULL DEFAULT '{}'::jsonb,    -- テンプレート設定
  is_active BOOLEAN DEFAULT true,
  is_default BOOLEAN DEFAULT false,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);
```

#### デフォルトテンプレート制御
```sql
-- デフォルトテンプレート一意性確保関数
CREATE OR REPLACE FUNCTION ensure_single_default_style_template()
RETURNS TRIGGER AS $$
BEGIN
  IF NEW.is_default = true THEN
    -- 個人テンプレートの場合
    IF NEW.organization_id IS NULL THEN
      UPDATE style_guide_templates 
      SET is_default = false 
      WHERE user_id = NEW.user_id 
        AND organization_id IS NULL 
        AND id != NEW.id 
        AND is_default = true;
    -- 組織テンプレートの場合
    ELSE
      UPDATE style_guide_templates 
      SET is_default = false 
      WHERE organization_id = NEW.organization_id 
        AND id != NEW.id 
        AND is_default = true;
    END IF;
  END IF;
  
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

### 8. エージェントログシステム (`20250716000000_add_agents_logging_system.sql`)

#### マルチエージェントログ設計
```sql
-- ログセッション（記事生成セッション全体）
CREATE TABLE agent_log_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    article_uuid UUID NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL,
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    
    -- 初期入力データ
    initial_input JSONB NOT NULL DEFAULT '{}',
    seo_keywords TEXT[],
    image_mode_enabled BOOLEAN DEFAULT false,
    article_style_info JSONB DEFAULT '{}',
    generation_theme_count INTEGER DEFAULT 1,
    target_age_group TEXT,
    persona_settings JSONB DEFAULT '{}',
    company_info JSONB DEFAULT '{}',
    
    -- セッション状態
    status TEXT NOT NULL DEFAULT 'started' CHECK (status IN ('started', 'in_progress', 'completed', 'failed', 'cancelled')),
    total_steps INTEGER DEFAULT 0,
    completed_steps INTEGER DEFAULT 0,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    
    session_metadata JSONB DEFAULT '{}'
);

-- エージェント実行ログ
CREATE TABLE agent_execution_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES agent_log_sessions(id) ON DELETE CASCADE,
    
    -- エージェント識別
    agent_name TEXT NOT NULL,
    agent_type TEXT NOT NULL,
    step_number INTEGER NOT NULL,
    sub_step_number INTEGER DEFAULT 1,
    
    -- 実行状態
    status TEXT NOT NULL DEFAULT 'started' CHECK (status IN ('started', 'running', 'completed', 'failed', 'timeout')),
    
    -- 入出力データ
    input_data JSONB DEFAULT '{}',
    output_data JSONB DEFAULT '{}',
    
    -- LLM情報
    llm_model TEXT,
    llm_provider TEXT DEFAULT 'openai',
    
    -- トークン使用量
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    cache_tokens INTEGER DEFAULT 0,
    reasoning_tokens INTEGER DEFAULT 0,
    
    -- タイミング
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    duration_ms INTEGER,
    
    -- エラー情報
    error_message TEXT,
    error_details JSONB DEFAULT '{}',
    
    execution_metadata JSONB DEFAULT '{}'
);
```

**ログシステムの価値**:
- **パフォーマンス分析**: 各エージェント・ステップの実行時間測定
- **コスト管理**: トークン使用量の詳細な追跡
- **エラー分析**: 失敗パターンの特定と改善
- **品質向上**: 生成プロセスの最適化データ

### 9. Supabase Realtime移行 (`20250727000000_supabase_realtime_migration.sql`)

#### Realtime対応拡張
```sql
-- 既存テーブルのRealtime拡張
ALTER TABLE generated_articles_state 
ADD COLUMN IF NOT EXISTS realtime_channel TEXT,
ADD COLUMN IF NOT EXISTS last_realtime_event JSONB,
ADD COLUMN IF NOT EXISTS realtime_subscriptions JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS executing_step TEXT,
ADD COLUMN IF NOT EXISTS step_execution_start TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS step_execution_metadata JSONB DEFAULT '{}'::jsonb,
ADD COLUMN IF NOT EXISTS background_task_id TEXT,
ADD COLUMN IF NOT EXISTS task_priority INTEGER DEFAULT 5,
ADD COLUMN IF NOT EXISTS retry_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS max_retries INTEGER DEFAULT 3;

-- プロセスイベントテーブル
CREATE TABLE IF NOT EXISTS process_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  process_id UUID NOT NULL REFERENCES generated_articles_state(id) ON DELETE CASCADE,
  
  -- イベント詳細
  event_type TEXT NOT NULL,
  event_data JSONB NOT NULL DEFAULT '{}'::jsonb,
  event_sequence INTEGER NOT NULL,
  
  -- イベントメタデータ
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  published_at TIMESTAMP WITH TIME ZONE,
  acknowledged_by TEXT[] DEFAULT '{}',
  delivery_attempts INTEGER DEFAULT 0,
  
  -- イベント分類
  event_category TEXT DEFAULT 'system',
  event_priority INTEGER DEFAULT 5,
  event_source TEXT DEFAULT 'backend'
);
```

#### バックグラウンドタスク管理
```sql
-- バックグラウンドタスクテーブル
CREATE TABLE IF NOT EXISTS background_tasks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  process_id UUID REFERENCES generated_articles_state(id) ON DELETE CASCADE,
  task_type TEXT NOT NULL,
  task_data JSONB NOT NULL DEFAULT '{}'::jsonb,
  status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),
  priority INTEGER DEFAULT 5,
  retry_count INTEGER DEFAULT 0,
  max_retries INTEGER DEFAULT 3,
  scheduled_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  started_at TIMESTAMP WITH TIME ZONE,
  completed_at TIMESTAMP WITH TIME ZONE,
  error_message TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

## マイグレーション設計パターン

### 1. RLSポリシー設計
```sql
-- 基本パターン: ユーザー自身のデータアクセス
CREATE POLICY "Users can manage their own data" ON table_name
  FOR ALL USING (user_id = current_setting('request.jwt.claims', true)::json->>'sub');

-- 組織パターン: 組織メンバーのアクセス
CREATE POLICY "Organization members can access data" ON table_name
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM organization_members 
      WHERE organization_members.organization_id = table_name.organization_id 
      AND organization_members.user_id::text = current_setting('request.jwt.claims', true)::json->>'sub'
    )
  );
```

### 2. JSONB活用パターン
```sql
-- 設定データの格納
settings JSONB NOT NULL DEFAULT '{}'::jsonb

-- 配列データの格納
step_history JSONB DEFAULT '[]'::jsonb

-- 検索可能インデックス
CREATE INDEX idx_table_json_field ON table_name USING GIN ((settings->'field_name'));
```

### 3. トリガー・関数パターン
```sql
-- updated_at自動更新
CREATE TRIGGER update_table_updated_at
  BEFORE UPDATE ON table_name
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ビジネスロジック制約
CREATE OR REPLACE FUNCTION ensure_business_rule()
RETURNS TRIGGER AS $$
BEGIN
  -- ビジネスルール実装
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

### 4. Realtime連携パターン
```sql
-- Realtime パブリケーション更新
DROP PUBLICATION IF EXISTS supabase_realtime;
CREATE PUBLICATION supabase_realtime FOR TABLE 
  table1, table2, table3;

-- RLS対応でのRealtime
ALTER TABLE table_name REPLICA IDENTITY FULL;
```

## マイグレーションのベストプラクティス

### 1. 安全なマイグレーション
```sql
-- 条件付きオブジェクト作成
CREATE TABLE IF NOT EXISTS table_name (...);
CREATE INDEX IF NOT EXISTS idx_name ON table_name(column);

-- 既存データ保護
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'enum_name') THEN
        CREATE TYPE enum_name AS ENUM ('value1', 'value2');
    END IF;
END $$;
```

### 2. パフォーマンス最適化
```sql
-- 適切なインデックス設計
CREATE INDEX idx_table_user_status ON table_name(user_id, status);
CREATE INDEX idx_table_created_at ON table_name(created_at DESC);

-- 部分インデックス活用
CREATE INDEX idx_table_active ON table_name(status) WHERE status = 'active';
```

### 3. データ整合性確保
```sql
-- 外部キー制約
REFERENCES parent_table(id) ON DELETE CASCADE

-- チェック制約
CHECK (status IN ('pending', 'completed', 'failed'))

-- 一意制約
UNIQUE (user_id, organization_id)
```

## まとめ

Supabaseマイグレーションファイルは、Marketing Automation プラットフォームの包括的なデータベース設計を実現しています：

### 設計の特徴
1. **段階的発展**: 機能追加に応じた漸進的なスキーマ拡張
2. **セキュリティ重視**: RLSによる厳密なアクセス制御
3. **パフォーマンス配慮**: 適切なインデックス設計
4. **拡張性確保**: JSONB活用による柔軟なデータ構造
5. **統合性**: Clerk・Stripe・Realtimeとの seamless な連携

### ビジネス価値
1. **マルチテナント対応**: 組織・個人両レベルでのデータ管理
2. **リアルタイム体験**: 即座な状態同期とユーザー通知
3. **監査機能**: 包括的なログ・追跡システム
4. **スケーラビリティ**: 大量データ・同時ユーザーへの対応
5. **保守性**: 明確な構造と豊富なドキュメント

このマイグレーション設計により、エンタープライズレベルの信頼性と拡張性を持つマーケティング自動化プラットフォームのデータ基盤が構築されています。