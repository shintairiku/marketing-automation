### 管理者バックエンド 実装マイルストーン計画

目的: 管理者向けの運用・サポート・配信・設定機能を、既存バックエンド（FastAPI）と既存DB（Supabase Postgres）に統合。要件は`requirement.md`を完全充足。DBは既存マイグレーションと仕様（`frontend/supabase/migrations/`, `docs/database/database_tables_specification.md`）を前提に、必要な新規テーブルを追加。

前提・方針
- 認証・認可: 初期は「全管理者同権限」。危険操作は確認ダイアログ/二重確認で担保（RBAC実装は見送り）。
- API設計: `backend/app/api/router.py`配下に`/admin`名前空間を追加し、機能別にサブルーター分割。
- DBアクセス: 基本はSupabase経由（Service Role Key）でPostgREST/SQL実行、または直接Postgres接続。既存RLSはユーザー用/組織用に定義済みだが、バックエンドはService Roleでバイパス。
- 監査・ログ: 重要操作の監査ログをDBに保存（後述）。
- Realtime: サポート・進捗監視はSupabase Realtimeのパブリケーションへ登録済/追加。

---

### マイルストーン0: 基盤整備（1〜2日）
目的: 管理API基盤・認証・テスト土台の最短整備

タスク/チケット
1. API基盤
   - `/admin` ルーター新設（`backend/app/api/router.py`へ登録）。
   - サブルーター雛形: `users.py`, `organizations.py`, `subscriptions.py`, `support.py`, `announcements.py`, `messages.py`, `monitoring.py`, `settings.py`, `dashboard.py`。
2. 管理者認証
   - 環境変数`ADMIN_EMAILS`（カンマ区切り）または`ADMIN_USER_IDS`で許可リスト。
   - 既存認証ミドルウェア（`backend/app/common/auth.py`想定）に管理者チェック関数追加。
   - すべての`/admin/*`エンドポイントで管理者チェック。
3. Supabase管理クライアント
   - Service Role Keyを利用する管理用クライアント実装（接続/SQL実行/ストレージは将来用）。
4. 観測性
   - 重要操作時に`agents_logging`と区別した「admin_audit_logs」出力の仕組み（DB or GCP Logs）。
5. CI/テスト
   - 管理APIの最小ユニットテスト枠組み。

受け入れ基準
- `/admin/health`が認証済み管理者のみ200、非管理者は403。
- 主要サブルーターが空でもルーティングOK。

---

### マイルストーン1: ユーザー・組織/サブスクリプション管理API（優先度: 高、3〜5日）
目的: 運用の土台となる閲覧・検索・更新APIを提供

関連DB
- 既存: `users`, `auth.users`, `customers`, `organizations`, `organization_members`, `subscriptions`, `products`, `prices`, `organization_subscriptions`

タスク/チケット
1. ユーザー管理API（/admin/users）
   - 一覧・検索・ページネーション・CSVエクスポート（email, plan, statusでフィルタ）。
   - 詳細取得（`users`+`subscriptions`+`customers`を集約）。
   - 基本情報更新（`users.full_name`, `avatar_url`など）。
   - アカウント停止/再開（ビジネスルール定義: auth側disable/flagsの扱い）。
2. 組織管理API（/admin/organizations）
   - 一覧・検索・詳細（`organizations`, `organization_members`）。
   - メンバー追加/削除（既存RLSはService Roleで回避）。
   - 所有者移行（`owner_user_id`更新+トリガー`handle_new_organization`整合性確認）。
3. サブスクリプション管理API（/admin/subscriptions）
   - 個人`subscriptions`/組織`organization_subscriptions`の一覧/詳細。
   - 請求期間・キャンセル状態の閲覧、Stripe側修正が必要な操作はWebhook経由の反映方針を明記（原則: 直接更新はしない）。
   - `products`, `prices`の参照API。
4. 監査ログ
   - 変更系APIは「誰が・何を・いつ」を記録。

受け入れ基準
- 指定条件での検索/ページネーションが正しく動作、CSV出力が実データと整合。
- 組織メンバーの増減がDBに反映され、RLSを壊さない。

---

### マイルストーン2: 問い合わせ・サポート管理（優先度: 高、4〜6日）
目的: 受付・対応・通知のワークフローをDB+APIで実装

新規DB（仕様は`requirement.md`に基づく）
- `support_tickets`（受付、カテゴリ、状態、優先度、関連ユーザー/組織、担当者、SLA）
- `support_messages`（スレッド内メッセージ: 管理者/ユーザー発言、添付ID）
- `support_attachments`（ファイルメタ、GCS/ローカルURL、参照権限）

DBマイグレーション
- 3テーブルの作成、`updated_at`トリガー、基本インデックス。
- Realtime対象へ追加、RLS: ユーザー側閲覧用途も将来考慮（初期は管理専用でもOK）。

API（/admin/support）
- チケット一覧（状態/優先度/未読/担当者フィルタ、並び替え）。
- チケット作成/状態更新/担当アサイン/タグ管理。
- メッセージ追加（AI返信下書き生成フックは将来: `image_generation`/LLM呼び出しは別途）。
- 添付アップロード（GCS連携は既存`images`と同様の列設計を参考: `gcs_url`, `storage_type`）。
- チャットワーク通知（新規/エスカレーション時）。

受け入れ基準
- 新規チケット→Realtimeイベント発火→通知送信。
- 状態遷移（open→in_progress→resolved→closed）が監査可能。

---

### マイルストーン3: お知らせ・投稿管理（優先度: 高、3〜5日）
目的: お知らせ/メンテ情報のCRUDと予約公開

新規DB
- `announcements`（タイトル, 本文, ステータス[draft/published/scheduled], カテゴリ, 公開日時）
- `announcement_categories`（名称, 表示順）
- `announcement_schedules`（予約レコード。将来のジョブトラッキングに使用）

DBマイグレーション
- 3テーブル作成、`updated_at`トリガー、インデックス（公開日時, ステータス）。
- Realtime追加（フロントのプレビュー/公開反映用）。

API（/admin/announcements）
- CRUD、プレビュー（HTMLサニタイズ方針定義）。
- 予約公開: 既存`background_tasks`を利用し「publish_announcement」タスクを登録/実行。

受け入れ基準
- 予約時間に自動公開、履歴が残る。

---

### マイルストーン4: メッセージ・通知管理（優先度: 高、5〜8日）
目的: セグメント配信/登録・解除通知/テンプレート管理の最小実装

新規DB
- `email_campaigns`（件名, 本文テンプレ, ターゲット定義[簡易SQL/属性条件], 送信状態）
- `email_templates`（システム/用途別テンプレ）
- `notification_settings`（登録/解除/緊急メールの受信設定）
- `message_delivery_logs`（配信結果、エラー、再送情報）

API（/admin/messages）
- テンプレCRUD、キャンペーン作成/テスト送信、本番送信キュー投入。
- セグメント解決（ユーザー/組織/プラン/最終アクティブなどの条件→SQLに変換）。
- 配信は外部メールサービスを抽象化（SendGrid/Resend等に差し替え可能なAdapter）。
- Webhook受信（バウンス/スパム/開封）で`message_delivery_logs`更新。

受け入れ基準
- 小規模テスト配信で成功/失敗が記録される。
- 登録/解除通知の自動送出が可能（ユーザー/サブスク作成/解約イベントのフック）。

---

### マイルストーン5: 記事生成・利用状況監視（優先度: 中、3〜5日）
目的: 生成系の可視化/トラブルシュートのための参照API

利用DB（既存）
- `generated_articles_state`, `articles`, `agent_log_sessions`, `agent_execution_logs`, `llm_call_logs`, `tool_call_logs`, `workflow_step_logs`
- 既存ビュー: `agent_performance_metrics`, `error_analysis`

API（/admin/monitoring）
- プロセス一覧/詳細（アクティブ/エラー/停止中フィルタ）。
- セッション別メトリクス・ビュー取得（上記ビュー利用）。
- LLM/Tool呼び出しの履歴/エラー詳細取得、CSV出力。

受け入れ基準
- 特定セッションの実行履歴が時系列で追える。

---

### マイルストーン6: ダッシュボード（優先度: 中、2〜3日）
目的: 運用KPI・警告の集約API

API（/admin/dashboard）
- 当日/週/月の新規ユーザー、アクティブ数、売上推定（Stripeサマリーの参照/キャッシュ）。
- エラー件数（`error_analysis`）、失敗プロセス数、未読サポート件数、保留決済件数の集約。

受け入れ基準
- 主要KPIが1クエリ（複数内部集計可）で取得可能、表示に1秒以内。

---

### マイルストーン7: システム設定（優先度: 高、2〜3日）
目的: 運営情報・お知らせ設定・メール設定

新規DB
- `system_settings`（キー/値, JSON設定, 連絡先, フッター文言）
- （必要に応じて）`maintenance_schedules`

API（/admin/settings）
- システム基本情報のCRUD。
- お知らせ・メール設定の既定値管理。

受け入れ基準
- 設定の変更が即時反映（キャッシュ無効化ポリシー明記）。

---

### マイルストーン8: セキュリティ/運用・品質保証（並行/締め 3日）
目的: 本番運用可能な品質・安全性

タスク/チケット
- 入力バリデーション（Pydantic Schemas整備）、レートリミット（重要操作）。
- 監査ログ: すべての更新/削除に対し`admin_audit_logs`テーブルを追加（id, actor, action, resource, before/after, created_at）。
- エラーハンドリング統一、通知（致命エラー時にチャットワーク/メール）。
- CI: 型チェック、Lint、主要APIのE2Eスモーク。
- 本番環境の環境変数・秘密情報管理（Service Role Key, 外部メールAPI Key, ChatWork Token）。

受け入れ基準
- 重要更新がすべて監査可能。主要APIに自動テストあり。シークレットは流出リスクなし。

---

### 主要エンドポイント（抜粋・想定）
- GET /admin/health
- GET /admin/dashboard/summary
- GET /admin/users, GET /admin/users/{id}, PATCH /admin/users/{id}
- GET /admin/organizations, GET /admin/organizations/{id}, POST /admin/organizations/{id}/members, DELETE /admin/organizations/{id}/members/{userId}
- GET /admin/subscriptions, GET /admin/prices, GET /admin/products
- GET/POST/PATCH /admin/support/tickets, GET/POST /admin/support/tickets/{id}/messages, POST /admin/support/tickets/{id}/attachments
- GET/POST/PATCH /admin/announcements, POST /admin/announcements/{id}/schedule
- GET/POST /admin/messages/campaigns, POST /admin/messages/campaigns/{id}/send, GET /admin/messages/logs
- GET /admin/monitoring/processes, GET /admin/monitoring/sessions/{id}, GET /admin/monitoring/llm-calls
- GET/PUT /admin/settings

---

### データベース マイグレーション一覧（新規）
この管理者機能で追加する主なテーブル（命名は上記参照）
- support_tickets, support_messages, support_attachments
- announcements, announcement_categories, announcement_schedules
- email_campaigns, email_templates, notification_settings, message_delivery_logs
- system_settings, (任意) maintenance_schedules
- admin_audit_logs（監査用）

各テーブルに対して:
- RLS: 管理APIはService Roleで操作、将来のユーザー側UI公開分は厳密RLS。
- Realtime publication: サポート/お知らせは購読対象に追加。
- インデックス: ステータス/作成日時/外部キー複合インデックス。

---

### リスクと先行課題
- Stripe側操作の扱い: 原則Webhook反映で整合。直接DB更新は不可にする。
- セグメント配信の仕様: 第1弾は固定フィルタ+簡易条件。高度なビルダーは将来課題。
- サポート添付のストレージ: 初期はローカル/GCSハイブリッド（既存`images`の`storage_type`設計を踏襲）。

---

### 完了の定義（DoD）
- `requirement.md`の高優先項目（ユーザー/組織・サブスク、サポート、通知/お知らせ、設定）が運用可能。
- ダッシュボード/監視で当日運用の気づきが得られる。
- 監査・通知・エラーハンドリング・最低限の自動テストが整備。


