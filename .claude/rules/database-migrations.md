---
paths: shared/supabase/**/*.sql,shared/supabase/**/*.toml
---

# Database マイグレーションルール

## DB開発ワークフロー (Local → Dev → Prod)

```
LOCAL (WSL2 Docker) → npx supabase start → Studio/手書き → npx supabase db diff -f <name> → npx supabase db reset → git push develop
DEVELOP → GitHub Actions (db-migrations.yml) → Dev Supabase (dddprfuwksduqsimiylg) に自動適用
MAIN → GitHub Actions → Prod Supabase (tkkbhglcudsxcwxdyplp) に自動適用
```

## 日常手順
```bash
npx supabase start                          # 起動
npx supabase db diff -f add_new_feature     # 差分SQL自動生成
npx supabase db reset                       # 全migration再適用で検証
npx supabase stop                           # 停止
```

## Supabaseローカルポート (1542x系)
- API: `http://127.0.0.1:15421`
- DB: `127.0.0.1:15422`
- Studio: `http://127.0.0.1:15423`
- Shadow DB: `127.0.0.1:15420`
- Analytics: `127.0.0.1:15427`

Windows excluded port range (54293-54392) との衝突を避けるため 1542x 系を使用。

## 踏んだ罠
- **`99-roles.sql` クラッシュループ**: `supabase/.temp/postgres-version` に古いバージョンがキャッシュ → `rm -rf supabase/.temp` + Docker volume 削除で解決
- **pg_dump ベースライン**: statement 単位でパースすべき（行単位だと ALTER TABLE が壊れる）
- **REST API でのデータ移行**: WSL2 の IPv6 問題を回避するため REST API 経由が最も確実
- **Realtime トリガーとデータ移行の競合**: トリガー自動生成分と移行データが重複キーエラー

## 型再生成
```bash
cd frontend && bun run generate-types
```
新テーブル/カラム追加後は必ず実行。
