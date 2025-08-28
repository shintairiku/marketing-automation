# インフラストラクチャユーティリティ


## 管理者監査ログシステム

### AdminAuditLogger

**ファイル**: `admin_audit_logger.py`

管理者の操作を構造化された形式でログ記録するためのユーティリティです。

#### 主な機能
- 管理者アクションの構造化ログ記録
- データベースへの永続化
- アプリケーションログとの連携
- エラー時の安全な処理（アプリケーションを停止させない）

#### 使用方法

```python
from app.infrastructure.admin_audit_logger import AdminAuditLogger

# インスタンス作成
audit_logger = AdminAuditLogger()

# 管理者アクションのログ記録
audit_logger.log_admin_action(
    admin_user_id="user_123",
    admin_email="admin@example.com",
    action="user_suspend",
    request_method="POST",
    request_path="/admin/users/123/suspend",
    ip_address="192.168.1.1",
    user_agent="Mozilla/5.0...",
    target_resource="user_123",
    details={"reason": "policy_violation"}
)
```

#### ログフィールド
- `timestamp`: ログ記録時刻（ISO形式）
- `admin_user_id`: 管理者のユーザーID
- `admin_email`: 管理者のメールアドレス
- `action`: 実行されたアクション（例: "admin_access", "user_suspend"）
- `request_method`: HTTPメソッド（GET, POST, PUT, DELETE）
- `request_path`: リクエストパス
- `ip_address`: クライアントIPアドレス
- `user_agent`: ユーザーエージェント
- `target_resource`: 操作対象リソース
- `details`: 追加詳細情報（JSON形式）
- `session_id`: セッションID（オプション）

### 管理者認証ミドルウェア統合

**ファイル**: `../domains/admin/auth/middleware.py`

`AdminAuthMiddleware` が自動的に `AdminAuditLogger` を使用して、管理者の認証とアクセスをログ記録します。

#### 自動記録される情報
- 管理者の認証成功
- アクセスされたエンドポイント
- リクエストメソッドとパス
- クライアントIP・ユーザーエージェント

### 監査ログクエリAPI

**エンドポイント**: `GET /admin/audit/logs`

管理者の操作履歴を検索・取得するためのAPIです。

#### パラメータ
- `limit`: 取得件数（1-500、デフォルト: 50）
- `offset`: スキップ件数（ページネーション用）
- `admin_user_filter`: ユーザーIDでフィルタ
- `action_filter`: アクション種別でフィルタ
- `start_date`: 開始日時（ISO形式）
- `end_date`: 終了日時（ISO形式）

#### 使用例

```bash
# 最新50件の監査ログを取得
curl -X GET "/admin/audit/logs"

# 特定ユーザーのログを取得
curl -X GET "/admin/audit/logs?admin_user_filter=user_123"

# 特定期間のログを取得
curl -X GET "/admin/audit/logs?start_date=2025-01-01&end_date=2025-01-31"
```

## データベース

### admin_audit_logs テーブル

**マイグレーション**: `frontend/supabase/migrations/20250828000000_add_admin_audit_logs.sql`

管理者の操作履歴を保存するテーブルです。

#### 主要な設計
- UUID主キー
- タイムスタンプインデックス（クエリ性能向上）
- RLS（Row Level Security）有効
- サービスロールのみアクセス可能

#### セキュリティ
- 管理者専用データのため、一般ユーザーはアクセス不可
- サービスロールキーが必要
- 改ざん防止のため書き込み後の変更は制限

## 運用ガイドライン

### ログ保存期間
- 推奨保存期間: 7年（コンプライアンス要件）
- 定期的なアーカイブとクリーンアップが必要

### 監視項目
- 異常なアクセスパターン
- 認証失敗の増加
- 大量データ操作
- システム設定変更

### トラブルシューティング
1. **ログが記録されない場合**: データベース接続とテーブル権限を確認
2. **パフォーマンス低下**: インデックスとクエリ最適化を確認
3. **大量ログによるストレージ圧迫**: 古いログのアーカイブを実行

## その他のインフラユーティリティ

### ログシステム（`logging/`）
- エージェント実行ログシステム
- LLM呼び出し追跡
- ツール使用履歴記録

### 外部API統合（`external_apis/`）
- SerpAPI検索サービス
- Google Cloud Storage統合
- Notion API統合

### コスト分析（`analysis/`）
- AI使用コスト計算
- パフォーマンス分析
- コンテンツ解析ツール