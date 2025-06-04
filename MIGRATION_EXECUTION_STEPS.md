# マイグレーション実行手順

## 準備完了の確認

✅ **マイグレーションファイル作成済み**
- `supabase/migrations/20250103000000_add_content_generation_system.sql`
- `supabase/migrations/20250103000001_add_organization_team_management.sql`

✅ **package.jsonスクリプト確認済み**
```json
{
  "scripts": {
    "migration:up": "supabase migration up --linked --debug && npm run generate-types",
    "generate-types": "npx supabase gen types typescript --project-id wptklzekgtduiluwzhap --schema public > src/libs/supabase/types.ts"
  }
}
```

## 実行コマンド

### 1. フロントエンドディレクトリに移動
```bash
cd frontend
```

### 2. 環境変数確認
`.env.local` ファイルに以下が設定されていることを確認：
```bash
NEXT_PUBLIC_SUPABASE_URL=https://wptklzekgtduiluwzhap.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...
```

### 3. マイグレーション実行
```bash
npm run migration:up
```

このコマンドは以下を自動実行します：
1. Supabaseにマイグレーションを適用
2. TypeScript型定義を再生成

### 4. エラーが発生した場合
```bash
# デバッグ情報付きで再実行
supabase migration up --linked --debug

# 手動で型定義生成
npm run generate-types
```

## 実行後の確認

### 1. マイグレーション状態確認
```bash
supabase migration list --linked
```

### 2. 型定義ファイル確認
`src/libs/supabase/types.ts` に新しいテーブルの型が追加されているか確認：
- `organizations`
- `organization_memberships`
- `unified_subscriptions`
- その他新規テーブル

### 3. Supabase Dashboard確認
1. [Supabase Dashboard](https://supabase.com/dashboard) で対象プロジェクトを開く
2. **Database** → **Tables** で新しいテーブルが作成されているか確認
3. **Database** → **Policies** でRLSポリシーが設定されているか確認

## 次のステップ

1. ✅ マイグレーション実行
2. ⏳ シート管理画面の実装
3. ⏳ エンドツーエンドテスト
4. ⏳ 本番環境設定

マイグレーション完了後、完全な組織・チーム管理システムが利用可能になります。