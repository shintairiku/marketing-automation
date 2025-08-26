# ユーザー・認証ドメイン実装計画書

## 概要

本ドキュメントでは、マーケティングオートメーションプラットフォームにおけるユーザー・認証ドメインの詳細実装戦略を定義します。Clerk組織機能の統合、Google Workspace SSO制限、管理者システム、および組織管理の包括的な実装計画を提供します。

## 現状システム分析

### 既存認証システム

#### フロントエンド認証
- **ファイル**: `frontend/src/middleware.ts`
- **機能**: Clerkミドルウェアによるルート保護
- **保護ルート**: `/dashboard`, `/generate`, `/tools` など
- **公開ルート**: `/`, `/pricing`, `/sign-in`, `/sign-up`

#### バックエンド認証
- **ファイル**: `backend/app/common/auth.py`
- **機能**: JWTトークン検証、ユーザーID抽出
- **制限**: 管理者権限チェック機能なし
- **問題**: 開発モードで署名検証がスキップされている

#### データベーススキーマ
既存のデータベーススキーマは以下のとおり整備済み：

**基本テーブル** (`20240115041359_init.sql`):
- `users`: ユーザー基本情報（id, full_name, avatar_url, billing_address, payment_method）
- `customers`: Stripe顧客情報マッピング
- `products`: Stripe商品情報（name, description, image, metadata）
- `prices`: 価格設定（unit_amount, currency, type, interval）
- `subscriptions`: 個人サブスクリプション（user_id, status, price_id, quantity）

**組織管理テーブル** (`20250605152002_organizations.sql`):
- `organizations`: 組織情報（name, owner_user_id, clerk_organization_id, stripe_customer_id）
- `organization_members`: メンバーシップ（organization_id, user_id, role, clerk_membership_id）
- `invitations`: 招待管理（organization_id, email, role, status, token, expires_at）
- `organization_subscriptions`: 組織サブスクリプション（organization_id, status, price_id, quantity）

**監査ログシステム** (`20250716000000_add_agents_logging_system.sql`):
- `agent_log_sessions`: エージェント実行セッション
- `agent_execution_logs`: 個別エージェント実行ログ
- `llm_call_logs`: LLM API呼び出し詳細
- `tool_call_logs`: 外部ツール呼び出しログ
- `workflow_step_logs`: ワークフローステップ記録

**型定義**:
- `organization_role`: 'owner', 'admin', 'member'
- `invitation_status`: 'pending', 'accepted', 'declined', 'expired'
- `subscription_status`: 'trialing', 'active', 'canceled', etc.

**RLS設定**: 全テーブルで適切なRow Level Securityポリシー設定済み

### 実装ギャップ

データベーススキーマは既に完備されているが、以下の実装が不足：

1. **管理者認証システム**: Google Workspace SSO制限なし
2. **管理者監査ログシステム**: `agents_logging` とは別の管理者操作ログが必要
3. **組織ドメインサービス**: ビジネスロジック層が未実装
4. **ユーザー管理ドメイン**: ユーザーライフサイクル管理なし
5. **管理API**: 管理者向けエンドポイントなし
6. **フロントエンド組織統合**: Clerk組織機能未活用
7. **Supabase管理クライアント**: Service Role Keyによる管理者操作

## 実装戦略

### Phase 1: 管理者認証システム強化

#### 1.1 Google Workspace SSO制限実装

**目的**: 管理者アクセスを会社発行のGoogle WorkspaceアカウントによるSSOのみに制限

**実装ファイル**:
- `backend/app/common/auth.py` - 管理者検証関数追加
- `backend/app/core/config.py` - 環境変数設定
- `backend/app/middleware/admin_auth.py` - 新規作成

**機能詳細**:
- 環境変数 `ADMIN_GOOGLE_WORKSPACE_DOMAINS` でドメイン許可リスト管理
- JWTトークンの `hd` クレーム（hosted domain）検証
- `email_verified=true` 必須化
- 個人Gmail（`@gmail.com`）の明示的拒否
- バックエンドでの二重チェック（トークン改ざん対策）

**検証フロー**:
1. Clerk認証完了後、JWTトークン取得
2. トークンから `iss`, `aud`, `hd`, `email_verified` 抽出
3. ドメイン許可リスト照合
4. 管理者権限フラグ設定
5. 失敗時は403レスポンス

#### 1.2 管理者ミドルウェア実装

**ファイル**: `backend/app/middleware/admin_auth.py`

**機能**:
- `@require_admin` デコレータ実装
- 管理者権限チェック自動化
- エラーハンドリング統一
- 監査ログ自動出力

**使用例**:
```python
@require_admin
async def admin_endpoint():
    # 管理者のみアクセス可能
    pass
```

#### 1.3 環境変数設定

**ファイル**: `backend/.env`

**必要な設定**:
- `ADMIN_GOOGLE_WORKSPACE_DOMAINS`: 許可ドメインリスト（カンマ区切り）
- `ADMIN_EMAILS`: 管理者メールアドレスリスト（カンマ区切り）
- `ADMIN_USER_IDS`: 管理者ユーザーIDリスト（カンマ区切り）
- `CLERK_JWT_VERIFICATION_ENABLED`: JWT署名検証の有効化

### Phase 2: 管理APIインフラ構築

#### 2.1 管理ルーター基盤

**ファイル**: `backend/app/api/admin/__init__.py`

**構造**:
```
backend/app/api/admin/
├── __init__.py
├── router.py           # メインの管理ルーター
├── users.py           # ユーザー管理API
├── organizations.py   # 組織管理API
├── subscriptions.py   # サブスクリプション管理API
├── support.py         # サポート機能API
├── announcements.py   # お知らせ管理API
├── messages.py        # メッセージ管理API
├── monitoring.py      # 監視・メトリクスAPI
├── settings.py        # システム設定API
└── dashboard.py       # 管理ダッシュボードAPI
```

**基本実装**:
- 全エンドポイントに `@require_admin` 適用
- 統一エラーハンドリング
- API仕様書自動生成（OpenAPI）
- レスポンス形式統一

#### 2.2 Supabase管理クライアント

**ファイル**: `backend/app/infrastructure/supabase_admin.py`

**機能**:
- Service Role Key使用
- RLS バイパス機能
- 管理者専用データアクセス
- 接続プール管理
- エラーハンドリング統一

**使用パターン**:
```python
async with get_admin_supabase_client() as client:
    # RLSをバイパスした管理者操作
    result = await client.table('users').select('*').execute()
```

#### 2.3 管理者監査ログシステム

**ファイル**: `backend/app/infrastructure/admin_audit.py`

**機能**:
- 管理者操作の全記録
- 既存の `agents_logging` システム（エージェント実行ログ）との分離
- 操作内容、対象、時刻の記録
- GCP Cloud Logging 統合
- 改ざん防止機能

**既存ログシステムとの差別化**:
既存の `agent_log_sessions`, `agent_execution_logs` 等は記事生成エージェントの実行ログであり、管理者の手動操作ログとは性質が異なる。管理者監査ログは以下を記録：

**ログ形式**:
```json
{
  "timestamp": "2025-01-20T10:30:00Z",
  "admin_user_id": "user_xxx",
  "admin_email": "admin@company.com",
  "action": "user_suspend",
  "target_resource": "user_yyy",
  "target_type": "user|organization|subscription",
  "details": {...},
  "ip_address": "192.168.1.1",
  "user_agent": "...",
  "session_id": "session_xxx"
}
```

### Phase 3: ユーザー管理ドメイン

#### 3.1 ユーザードメインサービス

**ファイル**: `backend/app/domains/user/`

**構造**:
```
backend/app/domains/user/
├── __init__.py
├── models.py          # ユーザーエンティティ
├── repository.py      # データアクセス層
├── service.py         # ビジネスロジック
├── schemas.py         # API スキーマ
└── exceptions.py      # ドメイン例外
```

**機能実装**:

**3.1.1 ユーザーライフサイクル管理**
- ユーザー作成・更新・削除
- アカウント状態管理（アクティブ/停止/削除済み）
- プロフィール情報管理
- Clerk連携によるメタデータ同期

**3.1.2 アカウント停止/再開機能**
- 管理者による停止/再開操作
- Clerk側のdisable/enable連携
- 停止理由の記録
- 自動通知システム（将来実装）

**3.1.3 ユーザー検索・フィルタリング**
- 複数条件による検索機能
- ページネーション対応
- CSVエクスポート機能
- パフォーマンス最適化

#### 3.2 ユーザー管理API

**ファイル**: `backend/app/api/admin/users.py`

**エンドポイント設計**:

```
GET    /admin/users                # ユーザー一覧・検索
GET    /admin/users/{user_id}      # ユーザー詳細
PUT    /admin/users/{user_id}      # ユーザー情報更新
POST   /admin/users/{user_id}/suspend    # アカウント停止
POST   /admin/users/{user_id}/activate   # アカウント再開
GET    /admin/users/export/csv     # CSV エクスポート
```

**機能詳細**:

**3.2.1 ユーザー一覧・検索**
- クエリパラメータ: `email`, `status`, `plan`, `created_after`, `created_before`
- ページネーション: `page`, `limit`
- ソート: `sort_by`, `sort_order`
- 統合データ: `users` + `subscriptions` + `customers` + `organization_members`

**3.2.2 ユーザー詳細情報**
- 基本情報: `users` テーブルから（full_name, avatar_url, billing_address）
- サブスクリプション情報: `subscriptions` + `organization_subscriptions` から現在のプラン、課金状況
- 組織所属: `organization_members` から参加組織、ロール
- 活動履歴: `agent_log_sessions` から記事生成数、実行統計

**3.2.3 ユーザー情報更新**
- 更新可能フィールド: `full_name`, `avatar_url`
- 更新不可フィールド: `email`, `id`
- 変更履歴の記録
- Clerk との同期処理

### Phase 4: 組織ドメイン実装

#### 4.1 組織ドメインサービス

**ファイル**: `backend/app/domains/organization/`

**構造**:
```
backend/app/domains/organization/
├── __init__.py
├── models.py          # 組織エンティティ
├── repository.py      # データアクセス層
├── service.py         # ビジネスロジック
├── schemas.py         # API スキーマ
├── invitation.py      # 招待システム
└── exceptions.py      # ドメイン例外
```

**機能実装**:

**4.1.1 組織CRUD操作**
- 組織作成・更新・削除
- オーナー権限管理
- Clerk組織IDとの同期
- RLS 考慮したデータアクセス

**4.1.2 メンバー管理システム**
- メンバー追加・削除
- ロール変更（owner/admin/member）
- 権限チェック機能
- 一括操作サポート

**4.1.3 招待システム**
- 招待メール送信
- 招待トークン管理
- 有効期限チェック
- 招待承認/拒否処理

**4.1.4 Clerk組織統合**
- Clerk Organization ID 同期
- メンバーシップ同期
- ロール マッピング
- エラーハンドリング

#### 4.2 組織管理API

**ファイル**: `backend/app/api/admin/organizations.py`

**エンドポイント設計**:

```
GET    /admin/organizations                    # 組織一覧
GET    /admin/organizations/{org_id}           # 組織詳細
PUT    /admin/organizations/{org_id}           # 組織情報更新
DELETE /admin/organizations/{org_id}           # 組織削除
GET    /admin/organizations/{org_id}/members   # メンバー一覧
POST   /admin/organizations/{org_id}/members   # メンバー追加
DELETE /admin/organizations/{org_id}/members/{user_id}  # メンバー削除
PUT    /admin/organizations/{org_id}/members/{user_id}/role  # ロール変更
PUT    /admin/organizations/{org_id}/owner     # オーナー移行
```

**機能詳細**:

**4.2.1 組織一覧・検索**
- フィルタリング: `organizations.name`, `owner_user_id`, `created_at`
- メンバー数による絞り込み（`organization_members` から計算）
- サブスクリプション状態による絞り込み（`organization_subscriptions.status`）
- CSV エクスポート対応

**4.2.2 組織詳細情報**
- 基本情報: `organizations` テーブルから（name, owner_user_id, clerk_organization_id, stripe_customer_id）
- メンバー情報: `organization_members` から（user_id, role, joined_at, clerk_membership_id）
- サブスクリプション: `organization_subscriptions` + `prices` + `products` からプラン、課金状況
- 招待状況: `invitations` から（pending/accepted/declined/expired状況）
- 使用統計: `agent_log_sessions` から組織内の記事生成数、実行統計

**4.2.3 メンバー管理操作**
- 既存RLS ポリシーをService Role で回避
- ロール変更時の権限チェック
- オーナー移行時の整合性確保
- 操作ログの記録

#### 4.3 組織権限システム

**ファイル**: `backend/app/domains/organization/permissions.py`

**機能**:
- ロールベースアクセス制御
- 組織コンテキスト管理
- 権限チェック関数群
- デコレータ実装

**権限マトリックス**:
```
操作 / ロール        | owner | admin | member
組織情報更新         |   ○   |   ○   |   ×
メンバー招待         |   ○   |   ○   |   ×
メンバー削除         |   ○   |   ○   |   ×
組織削除             |   ○   |   ×   |   ×
オーナー移行         |   ○   |   ×   |   ×
```

### Phase 5: フロントエンド組織統合

#### 5.1 Clerk組織コンポーネント統合

**ファイル**: `frontend/src/components/organization/`

**構造**:
```
frontend/src/components/organization/
├── CreateOrganization.tsx      # 組織作成ダイアログ
├── OrganizationProfile.tsx     # 組織プロフィール管理
├── OrganizationSwitcher.tsx    # 組織切り替えUI
├── OrganizationMembersList.tsx # メンバー一覧
├── InviteMembersDialog.tsx     # メンバー招待
└── OrganizationSettings.tsx    # 組織設定
```

**機能実装**:

**5.1.1 組織作成フロー**
- Clerk組織作成API呼び出し
- Supabase組織レコード作成
- 初期設定ウィザード
- エラーハンドリング

**5.1.2 組織切り替えUI**
- 現在の組織表示
- 組織一覧ドロップダウン
- 切り替え時のコンテキスト更新
- ローディング状態管理

**5.1.3 メンバー管理UI**
- メンバー一覧表示
- 招待フォーム
- ロール変更機能
- リアルタイム更新

#### 5.2 認証フロー拡張

**ファイル**: `frontend/src/hooks/useAuth.ts`

**機能拡張**:
- 組織コンテキスト管理
- 権限チェック関数
- 組織切り替えハンドリング
- エラー状態管理

**使用例**:
```typescript
const { user, organization, permissions } = useAuth();

if (permissions.canInviteMembers) {
  // メンバー招待UI表示
}
```

#### 5.3 ルート保護拡張

**ファイル**: `frontend/src/middleware.ts`

**拡張機能**:
- 組織必須ルートの定義
- 組織メンバーシップチェック
- ロールベースアクセス制御
- 組織作成へのリダイレクト

### Phase 6: サブスクリプション管理統合

#### 6.1 サブスクリプション管理API

**ファイル**: `backend/app/api/admin/subscriptions.py`

**エンドポイント設計**:

```
GET    /admin/subscriptions              # サブスクリプション一覧
GET    /admin/subscriptions/{sub_id}     # サブスクリプション詳細
GET    /admin/users/{user_id}/subscriptions     # ユーザーのサブスクリプション
GET    /admin/organizations/{org_id}/subscriptions  # 組織のサブスクリプション
GET    /admin/products                   # 商品一覧
GET    /admin/prices                     # 価格一覧
```

**機能詳細**:

**6.1.1 サブスクリプション一覧**
- 個人・組織サブスクリプション統合表示（`subscriptions` + `organization_subscriptions`）
- ステータス別フィルタリング（`subscription_status` enum）
- 課金期間による絞り込み（`prices.interval`, `prices.interval_count`）
- 収益レポート機能（`prices.unit_amount` * `quantity`）

**6.1.2 サブスクリプション詳細**
- Stripe連携データ表示（metadata, stripe_customer_id）
- 課金履歴（current_period_start/end, trial_start/end）
- プラン詳細（`products.name`, `prices.unit_amount`, `prices.currency`）
- キャンセル予定情報（cancel_at_period_end, canceled_at, cancel_at）

**注意事項**: 
- 直接的なサブスクリプション変更は行わない
- Stripe Webhook経由での同期が原則
- 表示・監視機能に特化

### Phase 7: 監査・監視システム

#### 7.1 管理者監査ログ

**ファイル**: `backend/app/infrastructure/admin_audit.py`

**ログ対象操作**:
- ユーザー情報変更
- アカウント停止/再開
- 組織メンバー変更
- サブスクリプション状態確認
- システム設定変更

**ログフォーマット**:
```json
{
  "timestamp": "ISO8601",
  "admin_user_id": "string",
  "admin_email": "string", 
  "action": "enum",
  "target_type": "user|organization|subscription",
  "target_id": "string",
  "changes": {...},
  "request_ip": "string",
  "user_agent": "string",
  "session_id": "string"
}
```

#### 7.2 監視ダッシュボード

**ファイル**: `backend/app/api/admin/monitoring.py`

**メトリクス**:
- アクティブユーザー数（`users` テーブルから）
- 新規登録数（`users.created_at` から日次/週次/月次）
- サブスクリプション変更数（`subscriptions` + `organization_subscriptions` の status 変更）
- API使用量統計（`agent_log_sessions`, `agent_execution_logs` から）
- エラー発生率（`agent_execution_logs.status = 'failed'` から）
- トークン使用量（`llm_call_logs` から）
- 組織作成・参加動向（`organizations`, `organization_members` から）

**アラート機能**:
- 異常値検知
- 管理者通知
- ダッシュボード表示
- 履歴データ保持

### Phase 8: テスト・品質保証

#### 8.1 ユニットテスト

**ファイル**: `backend/tests/domains/`

**テスト対象**:
- 認証ミドルウェア
- ドメインサービス
- API エンドポイント
- 権限チェック機能

**テストカバレッジ**: 90%以上を目標

#### 8.2 統合テスト

**ファイル**: `backend/tests/integration/`

**テストシナリオ**:
- 管理者ログイン〜操作完了
- 組織作成〜メンバー招待
- ユーザー停止〜再開
- Clerk連携シナリオ

#### 8.3 E2Eテスト

**ファイル**: `frontend/tests/e2e/`

**テストツール**: Playwright
**テストシナリオ**:
- 管理画面ログイン
- 組織管理操作
- ユーザー管理操作
- エラーハンドリング

## セキュリティ考慮事項

### 1. 管理者権限管理

- **最小権限の原則**: 必要最小限の権限のみ付与
- **多要素認証**: Google Workspace MFA 必須
- **セッション管理**: 適切なタイムアウト設定
- **IP制限**: 管理者アクセスIP制限（将来実装）

### 2. データアクセス制御

- **RLS バイパス**: Service Role使用時の適切な制御
- **監査ログ**: 全管理者操作の記録
- **データ暗号化**: 機密情報の暗号化保存
- **アクセスログ**: 詳細なアクセス記録

### 3. API セキュリティ

- **レート制限**: 管理API のレート制限
- **CORS設定**: 適切なオリジン制限
- **JWT検証**: 本番環境での署名検証必須
- **エラーハンドリング**: 情報漏洩防止

## パフォーマンス最適化

### 1. データベース最適化

- **インデックス設計**: 検索クエリの最適化
- **クエリ最適化**: N+1問題の回避
- **接続プール**: 適切な接続数管理
- **キャッシュ戦略**: Redis活用（将来実装）

### 2. API パフォーマンス

- **ページネーション**: 大量データの効率的処理
- **非同期処理**: 重い処理の非同期化
- **レスポンス最適化**: 不要データの除外
- **バックグラウンド処理**: 長時間処理の分離

## 運用・保守

### 1. ログ管理

- **ログローテーション**: 適切なログ保持期間
- **ログ分析**: 異常検知とアラート
- **パフォーマンス監視**: レスポンス時間監視
- **エラー追跡**: エラー発生時の追跡

### 2. バックアップ・復旧

- **データバックアップ**: 定期的なバックアップ
- **災害復旧**: 復旧手順の整備
- **データ整合性**: 定期的な整合性チェック
- **ロールバック**: 問題発生時のロールバック手順

## マイグレーション計画

### 1. 段階的リリース

1. **Phase 1**: 管理者認証システム（週1）
2. **Phase 2**: 管理API基盤（週2）
3. **Phase 3**: ユーザー管理機能（週3-4）
4. **Phase 4**: 組織管理機能（週5-6）
5. **Phase 5**: フロントエンド統合（週7-8）

### 2. データマイグレーション

- **既存データ**: 現在のユーザーデータ維持
- **Clerk連携**: 段階的なClerk組織統合
- **互換性**: 既存機能への影響最小化
- **ロールバック**: 問題発生時の復旧計画

## 成功指標・KPI

### 1. 技術指標

- **API レスポンス時間**: 95%のリクエストが500ms以内
- **エラー率**: 0.1%以下
- **テストカバレッジ**: 90%以上
- **セキュリティ脆弱性**: 0件

### 2. 運用指標

- **管理者操作効率**: 従来比50%削減
- **ユーザーサポート**: 自動化により工数50%削減
- **組織導入率**: 全企業ユーザーの80%が組織機能利用
- **システム稼働率**: 99.9%以上

## 結論

本実装計画は、堅牢で拡張性があり、セキュアなユーザー・認証ドメインの構築を目指しています。Google Workspace SSO制限による管理者権限管理、Clerk組織機能との統合、包括的な監査システムにより、エンタープライズレベルの要件を満たす実装を実現します。

段階的なリリース計画により、既存システムへの影響を最小限に抑えつつ、継続的な価値提供を行います。適切なテスト戦略とセキュリティ対策により、高品質で信頼性の高いシステムを構築します。