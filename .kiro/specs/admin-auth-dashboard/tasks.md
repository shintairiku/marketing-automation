# 実装計画

- [x] 1. 管理者認証インフラのセットアップ
  - JWTトークン検証でClerk組織メンバーシップ検証システムを作成
  - 組織メンバーシップチェックロジックを実装
  - 管理者組織IDの環境変数設定を追加
  - _要件: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6_

- [x] 1.1 Clerk組織バリデーターの実装
  - JWTトークンパーシングでClerkOrganizationValidatorクラスを作成
  - 組織メンバーシップの抽出と検証メソッドを作成
  - 管理者組織メンバーシップ検証ロジックを実装
  - 無効なトークンと組織メンバーシップに対する包括的エラー処理を追加
  - _要件: 1.1, 1.2, 1.3, 1.5_

- [x] 1.2 管理者認可ミドルウェアの作成
  - ~~エンドポイント保護のための@require_adminデコレーターを実装~~ → **自動ルート保護のAdminAuthMiddlewareを実装（より良いセキュリティ）**
  - 特権検証付きAdminAuthMiddlewareクラスを作成
  - すべての管理者操作に自動監査ログ記録を追加
  - 未許可アクセスに対する適切なエラーレスポンスを実装
  - _要件: 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 1.3 環境変数と設定の構成
  - ADMIN_ORGANIZATION_ID設定を追加 (org_31qpu3arGjKdiatiavEP9E7H3LV)
  - ADMIN_ORGANIZATION_SLUG設定をセットアップ (shintairiku-admin)
  - 本番環境でCLERK_JWT_VERIFICATION_ENABLEDを有効化
  - 管理者固有の設定でコア設定を更新
  - _要件: 1.1, 1.4, 1.6_

- [x] 2. ~~Supabase管理者クライアントインフラの実装~~ → **スキップ: 既存のサービスロールクライアントが既にRLSバイパスと管理者データベースアクセスを提供**
  - ~~サービスロールキー認証システムを作成~~ → **backend/app/common/database.pyに既に存在**
  - ~~管理者操作用のRLSバイパス機能を実装~~ → **サービスロールは本質的にRLSをバイパス**
  - ~~コネクションプールとエラー処理を追加~~ → **既に実装済み**
  - ~~管理者固有のデータベースアクセスパターンを作成~~ → **既存クライアントを使用可能**
  - _Requirements: 7.1, 7.2_

- [x] 2.1 ~~Supabase管理者クライアントの作成~~ → **スキップ: 既存のcreate_supabase_client()を使用**
  - ~~サービスロールキーでSupabaseAdminClientを実装~~ → **既に存在**
  - ~~適切な接続処理のためのコンテキストマネージャーを追加~~ → **管理者操作には不要**
  - ~~RLSバイパスで管理者クエリ実行メソッドを作成~~ → **サービスロールは既にRLSをバイパス**
  - ~~複雑な操作のためのトランザクションサポートを実装~~ → **既存クライアントで利用可能**
  - _Requirements: 7.1, 7.2_

- [x] 2.2 ~~管理者データベースビューと関数の設定~~ → **スキップ: マスター管理者は顧客データ集約ではなく内部システム運用に焦点**
  - ~~ユーザー管理インターフェース用のadmin_user_summaryビューを作成~~ → **スキップ: Clerk APIを直接使用**
  - ~~メンバー数付きのadmin_organization_summaryビューを実装~~ → **スキップ: マスター管理者内部運用には不要**
  - ~~収益分析用のadmin_subscription_metricsビューを追加~~ → **スキップ: マスター管理者内部運用には不要**
  - ~~メトリクス計算用のデータベース関数を作成~~ → **スキップ: マスター管理者内部運用には不要**
  - _Requirements: 3.3, 3.4, 4.3, 4.4_

- [x] 3. 監査ログシステムの構築
  - 包括的な管理者アクションログ記録を作成
  - GCP Cloud Logging統合を実装
  - 構造化形式で改ざん防止ログ記録を追加
  - 監査ログクエリとフィルタリング機能を作成
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_
  - **実装概要**: AdminAuditLoggerクラスを作成、自動監査ログ記録でAdminAuthMiddlewareを拡張、RLSセキュリティ付きadmin_audit_logsデータベーステーブルを追加、フィルタリング/ページネーション付きGET /admin/audit/logs APIを実装。ミニマルアプローチのGCP統合は延期。

- [x] 3.1 管理者監査ロガーの実装
  - 構造化ログ記録でAdminAuditLoggerクラスを作成
  - 必要なすべてのフィールドでログエントリ作成を実装
  - リモートストレージ用のGCP Cloud Logging統合を追加
  - 監査ログクエリとフィルタリングメソッドを作成
  - _Requirements: 6.1, 6.2, 6.3, 6.4_
  - **実装概要**: 構造化JSONログ記録用の単一`log_admin_action()`メソッドで`backend/app/infrastructure/admin_audit_logger.py`にAdminAuditLoggerクラスを作成し、admin_audit_logsデータベーステーブルに記録。ログクエリ用のフィルタリング/ページネーション付きGET /admin/audit/logs APIエンドポイントを追加。

- [x] 3.2 ミドルウェアと監査ログ記録の統合
  - ~~Add automatic audit logging to admin authorization middleware~~ → **✅ COMPLETE: Enhanced AdminAuthMiddleware with comprehensive structured audit logging**
  - すべての管理者操作のアクション追跡を実装
  - 認証失敗試行のセキュリティイベントログ記録を作成
  - IPアドレスとユーザーエージェント追跡を追加
  - _Requirements: 6.1, 6.2, 6.6_
  - **実装概要**: すべての管理者リクエストにAdminAuditLoggerを自動使用するように`backend/app/domains/admin/auth/middleware.py`のAdminAuthMiddlewareを拡張。IPアドレス抽出（x-forwarded-for, x-real-ip, client）、ユーザーエージェントキャプチャ、包括的メタデータログ記録を追加。管理者エンドポイントには手動ログ記録コード不要。

- [-] 4. 管理者APIルーターインフラの作成
  - ~~Set up main admin router with proper middleware chain~~ → **✅ PARTIALLY COMPLETE: Basic admin router created with middleware protection and ping endpoint**
  - 一貫したエラー処理とレスポンス形式を実装
  - レート制限とCORS設定を追加
  - OpenAPI文書生成を作成
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [ ] 4.1 管理者ルーター基盤の実装
  - ~~Create main admin router with @require_admin protection~~ → **✅ COMPLETE: Admin router uses AdminAuthMiddleware for automatic protection**
  - 一貫したエラー処理ミドルウェアをセットアップ
  - すべてのエンドポイント用の標準化レスポンス形式を実装
  - 適切なHTTPステータスコード処理を追加
  - _Requirements: 7.1, 7.2_

- [-] 4.2 レート制限とセキュリティヘッダーの追加
  - 管理者エンドポイントのレート制限を実装
  - 管理者フロントエンドアクセス用のCORSヘッダーを設定
  - 管理者APIレスポンス用のセキュリティヘッダーを追加
  - リクエスト検証ミドルウェアを作成
  - _Requirements: 7.4, 7.5_

- [ ] 5. マスター管理者内部運用ダッシュボードの実装
  - インフラヘルス監視とメトリックスを作成
  - リアルタイムシステムステータス集約を実装
  - ビジネスインテリジェンスと分析機能を追加
  - 内部運用APIエンドポイントを作成
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7_

- [-] 5.1 インフラ監視サービスの作成
  - ヘルス監視付きInfrastructureServiceを実装
  - インフラパフォーマンス用SystemMetricsCalculatorを作成
  - サービスヘルス監視とデプロイメントステータス追跡を追加
  - ビジネスメトリックスとコスト分析を実装
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [ ] 5.2 内部運用APIエンドポイントの構築
  - GET /admin/infrastructure/statusエンドポイントを作成
  - 重要システムの2分更新でリアルタイムメトリックス更新を実装
  - パフォーマンス監視データ用のRedisキャッシュレイヤーを追加
  - ビジネスインテリジェンスデータエクスポート機能を作成
  - _Requirements: 3.6, 3.7_

- [-] 6. システム設定管理サービスの実装
  - 内部システム設定管理操作を作成
  - 機能フラグと環境変数管理を実装
  - 設定検証とロールバック機能を追加
  - 設定バックアップとリストア機能を作成
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7_

- [-] 6.1 システム設定サービスの作成
  - 設定CRUD操作でSystemConfigServiceを実装
  - パーセンテージロールアウトで機能フラグ管理を追加
  - 検証付き環境変数管理を作成
  - 設定変更追跡と履歴を実装
  - _Requirements: 4.1, 4.2, 4.3_

- [-] 6.2 設定デプロイメント管理の実装
  - 検証付き設定デプロイメント機能を作成
  - 失敗した設定変更のロールバック機能を実装
  - 設定バックアップとリストア手順を追加
  - 環境間の設定同期を作成
  - _Requirements: 4.4, 4.5, 4.7_

- [-] 6.3 システム設定 APIエンドポイントの構築
  - 設定表示用のGET /admin/configエンドポイントを作成
  - 設定更新用のPUT /admin/configを実装
  - 設定デプロイメント用のPOST /admin/config/deployを追加
  - 設定ロールバック用のPOST /admin/config/rollbackを作成
  - 設定バックアップエクスポート用のGET /admin/config/backupを追加
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_

- [-] 7. インフラおよびサービス管理の実装
  - インフラ監視と管理操作を作成
  - デプロイメントとサービスヘルス管理を実装
  - インシデント管理とメンテナンススケジュールを追加
  - サービススケールとリソース管理を作成
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6_

- [ ] 7.1 インフラ管理サービスの作成
  - サービス監視付きInfrastructureManagementServiceを実装
  - デプロイメント管理とヘルスチェック機能を追加
  - サービススケールとリソース割り当てコントロールを作成
  - インフラコスト追跡と最適化を実装
  - _Requirements: 5.1, 5.3_

- [-] 7.2 デプロイメントとメンテナンス管理の実装
  - デプロイメントトリガーとロールバック機能を作成
  - メンテナンスウィンドウスケジュールと通知を実装
  - インシデント管理とエスカレーション手順を追加
  - サービス依存マッピングと影響分析を作成
  - _Requirements: 5.2, 5.4_

- [-] 7.3 インフラ管理APIエンドポイントの構築
  - サービスステータス用のGET /admin/infrastructure/servicesエンドポイントを作成
  - デプロイメント管理用のPOST /admin/infrastructure/deployを実装
  - リソーススケール用のPUT /admin/infrastructure/scaleを追加
  - メンテナンススケジュール用のPOST /admin/infrastructure/maintenanceを作成
  - インシデント管理用のGET /admin/infrastructure/incidentsを追加
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [-] 7.4 サービス監視とアラートの実装
  - リアルタイムサービスヘルス監視を作成
  - サービス障害用の自動アラートを実装
  - パフォーマンス監視とキャパシティプランニングを追加
  - サービス依存追跡と障害影響分析を作成
  - _Requirements: 5.6_

- [-] 8. ビジネスインテリジェンスと分析システムの作成
  - ビジネス分析とレポート機能を実装
  - コスト分析と収益性追跡を作成
  - 予測分析と予測を追加
  - ビジネスインテリジェンスAPIエンドポイントを作成
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

- [-] 8.1 ビジネス分析サービスの実装
  - 収益とコスト追跡でBusinessAnalyticsServiceを作成
  - 使用状況分析と機能採用メトリックスを実装
  - サービスとインフラ別コスト分解分析を追加
  - キャパシティプランニングと成長予測用の予測分析を作成
  - _Requirements: 8.1, 8.2, 8.4_

- [-] 8.2 ビジネスインテリジェンスAPIエンドポイントの構築
  - 収益分析用のGET /admin/analytics/revenueエンドポイントを作成
  - コスト分析用のGET /admin/analytics/costsを実装
  - 使用パターン分析用のGET /admin/analytics/usageを追加
  - 予測分析用のGET /admin/analytics/forecastingを作成
  - カスタムレポート生成用のPOST /admin/analytics/reportsを追加
  - _Requirements: 8.1, 8.2, 8.3, 8.4_

- [ ] 9. 包括的エラー処理の実装
  - 管理者固有の例外クラスを作成
  - 一貫したエラーレスポンス形式を実装
  - 適切なHTTPステータスコードマッピングを追加
  - エラーログ記録と監視を作成
  - _Requirements: 7.2, 9.4_

- [x] 9.1 管理者例外階層の作成
  - ~~Implement AdminAuthenticationError and subclasses~~ → **✅ COMPLETE: Comprehensive exception hierarchy already implemented**
  - ~~Create InvalidOrganizationError and OrganizationMembershipRequiredError~~ → **✅ COMPLETE: All exception classes implemented**
  - 一般的な管理者操作失敗用のAdminOperationErrorを追加
  - ~~Create proper error message formatting~~ → **✅ COMPLETE: Error formatting implemented**
  - _Requirements: 7.2_

- [ ] 9.2 エラー処理ミドルウェアの実装
  - 管理者エンドポイント用のグローバルエラーハンドラーを作成
  - 一貫したエラーレスポンス形式を実装
  - 適切な重要度レベルでエラーログ記録を追加
  - エラー監視とアラート統合を作成
  - _Requirements: 7.2, 9.4_

- [-] 10. パフォーマンス最適化とキャッシュの追加
  - ダッシュボードメトリックス用のRedisキャッシュを実装
  - 適切なインデックシングでデータベースクエリ最適化を追加
  - 管理者操作用のコネクションプールを作成
  - レスポンス圧縮と最適化を実装
  - _Requirements: 3.6, 3.7, 9.4, 9.5_

- [-] 10.1 キャッシュレイヤーの実装
  - 5分TTLでダッシュボードメトリックス用のRedisキャッシュをセットアップ
  - データ変更用のキャッシュ無効化戦略を作成
  - 頻繁アクセスデータ用のキャッシュウォーミングを実装
  - キャッシュ監視とパフォーマンスメトリックスを追加
  - _Requirements: 3.6, 3.7_

- [ ] 10.2 データベースパフォーマンスの最適化
  - 管理者クエリ用のデータベースインデックスを作成
  - 大量データセット用のクエリ最適化を実装
  - コネクションプール設定を追加
  - データベースパフォーマンス監視を作成
  - _Requirements: 9.4, 9.5_

- [-] 11. 包括的テストスイートの作成
  - すべての管理者コンポーネントのユニットテストを実装
  - 認証フローの統合テストを作成
  - ダッシュボードと一括操作のパフォーマンステストを追加
  - 管理者ワークフローのエンドツーエンドテストを作成
  - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

- [ ] 11.1 認証コンポーネントのユニットテストを作成
  - 様々な組織メンバーシップシナリオでClerkOrganizationValidatorをテスト
  - 管理者認可ミドルウェアのテストを作成
  - JWTトークン検証と組織メンバーシップ検証をテスト
  - 監査ログ機能のテストを追加
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 6.1_

- [ ] 11.2 管理者APIの統合テストを作成
  - 完全な管理者認証フローをテスト
  - ユーザー管理操作のテストを作成
  - 組織管理機能をテスト
  - ダッシュボードメトリックスとシステム設定のテストを追加
  - _Requirements: 3.1, 4.1, 5.1, 8.1_

- [ ] 11.3 パフォーマンスと負荷テストの実装
  - 同時管理者ユーザー下でダッシュボード読み込みをテスト
  - 一括ユーザー操作の負荷テストを作成
  - 大量データセットでデータベースパフォーマンスをテスト
  - キャッシュパフォーマンスと無効化のテストを追加
  - _Requirements: 3.7, 9.4, 9.5_

- [-] 12. 監視と可観測性のセットアップ
  - すべての管理者操作の構造化ログ記録を実装
  - パフォーマンスメトリックス収集を作成
  - セキュリティイベント監視とアラートを追加
  - 管理者操作ダッシュボードを作成
  - _Requirements: 6.4, 6.5, 6.6, 9.4_

- [-] 12.1 監視インフラの実装
  - JSON形式で構造化ログ記録をセットアップ
  - 管理者操作用のパフォーマンスメトリックス収集を作成
  - 認証失敗のセキュリティイベント監視を実装
  - 異常な管理者活動パターンのアラートを追加
  - _Requirements: 6.4, 6.5, 6.6_

- [-] 12.2 管理者操作ダッシュボードの作成
  - 管理者システムヘルス用の監視ダッシュボードを構築
  - 管理者操作頻度のメトリックス可視化を作成
  - セキュリティイベント用のアラートダッシュボードを実装
  - APIレスポンス時間のパフォーマンス監視を追加
  - _Requirements: 6.4, 6.6, 9.4_