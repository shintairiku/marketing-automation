---
paths: frontend/src/app/(admin)/**/*,backend/app/domains/admin/**/*
---

# 管理者ダッシュボード

## 認証
- `@shintairiku.jp` ドメインのユーザーのみアクセス可能
- 特権チェックは `middleware.ts` の `isPrivilegedOnlyRoute` で実施
- バックエンドは `admin_auth.py` で検証

## レスポンシブ対応パターン
- デスクトップ (md+): 左サイドバー `w-56` + メインコンテンツ (折りたたみ可能)
- モバイル (<md): Sheet コンポーネントでスライドインサイドバー
- サイドバー折りたたみ状態は `localStorage('admin-sidebar-collapsed')` で永続化
- テーブルには `overflow-x-auto` 必須

## 管理者ページ一覧
| Path | 概要 |
|------|------|
| `/admin` | ダッシュボード (KPI, チャート, アクティビティ) |
| `/admin/users` | ユーザー管理 |
| `/admin/users/[userId]` | ユーザー詳細 (使用量, サブスク, 記事付与UI) |
| `/admin/blog-usage` | 記事別Usage (コスト分析, モデル配分) |
| `/admin/blog-usage/[processId]` | プロセス詳細トレース |
| `/admin/plans` | プラン設定 (CRUD, 即時反映) |
| `/admin/inquiries` | お問い合わせ管理 |

## Blog Usage トレース
- `GET /admin/usage/blog/{process_id}/trace` で詳細データ取得
- 会話履歴、LLM call別トークン、ツール入出力、時系列イベントを表示
- キャッシュヒット率を水平バーチャートで可視化
- `formatResponseId()`: 先頭20 + ... + 末尾10 で表示

## 記事付与
- `POST /admin/users/{user_id}/grant-articles` で付与
- ダッシュボード、お問い合わせ管理、ユーザー詳細からワンクリック付与可能
