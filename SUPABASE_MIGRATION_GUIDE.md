# Supabaseマイグレーション実行ガイド

## 1. マイグレーション実行前の準備

### 現在のマイグレーションファイル確認
```bash
ls -la supabase/migrations/
```

以下のファイルが存在することを確認：
- `20240115041359_init.sql` (既存の初期設定)
- `20250103000000_add_content_generation_system.sql` (記事生成システム)
- `20250103000001_add_organization_team_management.sql` (組織・チーム管理)

### 環境変数の設定
`.env.local` に以下が設定されていることを確認：

```bash
# Supabase設定
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

## 2. Supabase CLIを使用したマイグレーション

### Supabase CLIのインストール（未インストールの場合）
```bash
npm install -g supabase
# または
npm install supabase --save-dev
```

### プロジェクトへのリンク
```bash
# プロジェクトIDを指定してリンク
supabase link --project-ref wptklzekgtduiluwzhap

# または環境変数を使用
npm run supabase:link
```

### ローカル環境でのテスト（推奨）
```bash
# ローカルSupabaseを起動
supabase start

# マイグレーションを適用
supabase migration up

# 動作確認後、停止
supabase stop
```

### 本番環境への適用
```bash
# 本番環境にマイグレーションを適用
supabase migration up --linked

# 型定義の再生成
npm run generate-types
```

## 3. 手動での実行（Supabase Web UIを使用）

### 方法1: SQL Editorを使用
1. [Supabase Dashboard](https://supabase.com/dashboard) にログイン
2. 対象プロジェクトを選択
3. 左サイドバーの **SQL Editor** をクリック
4. 各マイグレーションファイルの内容をコピー&ペーストして実行

#### 実行順序（重要）
1. **先に** `20250103000000_add_content_generation_system.sql` を実行
2. **その後** `20250103000001_add_organization_team_management.sql` を実行

### 方法2: Database Migrationsページを使用
1. Supabase Dashboard → **Database** → **Migrations**
2. マイグレーションファイルをアップロード
3. 順番に実行

## 4. マイグレーション実行確認

### テーブル作成確認
```sql
-- 組織・チーム管理テーブルの確認
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN (
  'organizations',
  'organization_memberships', 
  'organization_settings',
  'unified_subscriptions',
  'organization_invitations',
  'usage_tracking'
);

-- 記事生成システムテーブルの確認  
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN (
  'companies',
  'article_projects',
  'serp_analyses',
  'generated_personas',
  'research_plans',
  'articles'
);
```

### RLS (Row Level Security) 確認
```sql
-- RLSが有効化されているテーブルを確認
SELECT schemaname, tablename, rowsecurity 
FROM pg_tables 
WHERE schemaname = 'public' 
AND rowsecurity = true;
```

### ポリシー確認
```sql
-- RLSポリシーの確認
SELECT schemaname, tablename, policyname, cmd, qual
FROM pg_policies 
WHERE schemaname = 'public';
```

## 5. 型定義の更新

### TypeScript型定義の再生成
```bash
# package.jsonのスクリプトを使用
npm run generate-types

# または直接実行
npx supabase gen types typescript --project-id wptklzekgtduiluwzhap --schema public > src/libs/supabase/types.ts
```

### 型定義ファイルの確認
生成された `src/libs/supabase/types.ts` に新しいテーブルの型が含まれていることを確認：
- `organizations`
- `organization_memberships`
- `unified_subscriptions`
- その他の新しいテーブル

## 6. トラブルシューティング

### よくあるエラーと対処法

#### エラー: "relation already exists"
```sql
-- 既存テーブルを確認
\dt

-- 必要に応じて削除（注意：データが失われます）
DROP TABLE IF EXISTS table_name CASCADE;
```

#### エラー: "permission denied"
- サービスロールキーが正しく設定されているか確認
- プロジェクトIDが正しいか確認

#### エラー: "syntax error"
- SQLファイルの文法を確認
- コメント行の問題がないか確認

### ログ確認
```bash
# Supabaseのログを確認
supabase logs

# 特定のマイグレーションのログ
supabase logs --filter="migration"
```

## 7. マイグレーション完了後の動作確認

### 基本的な動作確認
```sql
-- 組織作成テスト
INSERT INTO organizations (id, name, slug, owner_user_id, max_seats) 
VALUES ('org_test123', 'テスト組織', 'test-org', 'user_test123', 5);

-- メンバーシップ作成テスト  
INSERT INTO organization_memberships (id, organization_id, user_id, role, status)
VALUES ('mem_test123', 'org_test123', 'user_test123', 'owner', 'active');

-- データ確認
SELECT * FROM organizations WHERE id = 'org_test123';
SELECT * FROM organization_memberships WHERE organization_id = 'org_test123';

-- テストデータ削除
DELETE FROM organization_memberships WHERE id = 'mem_test123';
DELETE FROM organizations WHERE id = 'org_test123';
```

### フロントエンドでの動作確認
1. 組織作成機能のテスト
2. メンバー招待機能のテスト
3. Stripe Webhookの動作確認
4. 記事生成プロセスの動作確認

## 8. 次のステップ

1. ✅ マイグレーション実行
2. ✅ 型定義更新  
3. ⏳ アプリケーションのテスト
4. ⏳ 本番データベースへの適用（本番環境の場合）

マイグレーション完了後、組織・チーム管理機能とシート制サブスクリプションが利用可能になります。