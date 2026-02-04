# 🔍 セキュリティ大規模調査 - 共有黒板

> **作成日時**: 2026-02-03
> **目的**: 並列エージェントによる徹底的なセキュリティ調査結果の共有

---

## 調査進捗

| エージェント | 担当領域 | ステータス | 発見数 |
|-------------|---------|-----------|-------|
| Agent-01 | Backend認証フロー | ✅ 完了 | Critical:1, High:2, Medium:3, Low:2 |
| Agent-02 | Backend Blog API | ✅ 完了 | Critical:0, High:2, Medium:4, Low:3 |
| Agent-03 | Backend Admin API | ✅ 完了 | Critical:0, High:2, Medium:4, Low:2 |
| Agent-04 | Backend Organization API | ✅ 完了 | Critical:0, High:1, Medium:2, Low:2 |
| Agent-05 | Backend Usage API | ✅ 完了 | Critical:0, High:1, Medium:3, Low:2 |
| Agent-06 | Backend Image API | ✅ 完了 | Critical:0, High:2, Medium:4, Low:2 |
| Agent-07 | Frontend API Routes (proxy) | ✅ 完了 | Critical:0, High:2, Medium:2, Low:1 |
| Agent-08 | Frontend API Routes (subscription) | ✅ 完了 | Critical:0, High:1, Medium:3, Low:2 |
| Agent-09 | Frontend API Routes (webhooks) | ✅ 完了 | Critical:0, High:2, Medium:3, Low:2 |
| Agent-10 | Frontend Middleware | ✅ 完了 | Critical:0, High:0, Medium:2, Low:2 |
| Agent-11 | Supabase RLS / DB | ✅ 完了 | Critical:1, High:3, Medium:4, Low:2 |
| Agent-12 | Clerk設定・JWT | ✅ 完了 | Critical:0, High:2, Medium:3, Low:3 |
| Agent-13 | Stripe設定・Webhook | ✅ 完了 | Critical:0, High:2, Medium:4, Low:3 |
| Agent-14 | XSS脆弱性全箇所 | ✅ 完了 | Critical:0, High:3, Medium:4, Low:2 |
| Agent-15 | 入力バリデーション | ✅ 完了 | Critical:0, High:3, Medium:6, Low:4 |
| Agent-16 | エラーハンドリング | 🔄 調査中 | - |
| Agent-17 | ログ・機密情報露出 | ✅ 完了 | Critical:0, High:3, Medium:5, Low:4 |
| Agent-18 | Docker・CI/CD | ✅ 完了 | Critical:1, High:2, Medium:3, Low:2 |
| Agent-19 | 依存パッケージ脆弱性 | ✅ 完了 | Critical:0, High:2, Medium:4, Low:3 |
| Agent-20 | 環境変数・シークレット | ✅ 完了 | Critical:0, High:3, Medium:4, Low:3 |

---

## 🚨 Critical 発見事項

### AUTH-001: DEBUG_MODEによるJWT署名検証スキップ (Agent-01)
- **ファイル**: `backend/app/common/auth.py:125-133, 34`
- **問題**: `DEBUG=true` 環境変数でJWT署名検証が完全にスキップされる
- **影響**: 攻撃者が任意のJWTを作成し、任意のユーザーになりすまし可能。本番環境で誤って設定されると全認証が無効化
- **修正**: DEBUG_MODEフラグを完全削除するか、本番環境では絶対に有効化できない仕組みを実装

### RLS-001: 15テーブルでRLS有効だがポリシー全削除 (Agent-11)
- **ファイル**: `shared/supabase/migrations/20260130000003_fix_org_clerk_compat.sql`
- **問題**: Clerk互換性修正で31個のRLSポリシーを削除し、再作成していない
- **影響**: organizations, articles, images等15テーブルがservice_role_keyでのみアクセス可能。Defense in Depthの欠如
- **修正**: Clerk互換のRLSポリシーを再作成するか、意図的であればRLSを明示的に無効化

---

## ⚠️ High 発見事項

### AUTH-002: issuer/audience検証の欠如 (Agent-01)
- **ファイル**: `backend/app/common/auth.py:139-150`
- **問題**: `jwt.decode()`でissuer/audience検証が行われていない
- **影響**: 他のClerkアプリケーション用に発行されたJWTでも認証可能（クロステナント攻撃）
- **修正**: `issuer`と`audience`パラメータを追加してClerkの値を検証

### AUTH-003: テスト用署名スキップ関数の残存 (Agent-01)
- **ファイル**: `backend/app/common/auth.py:252-258`
- **問題**: `validate_token_without_signature()` がプロダクションコードに存在
- **影響**: 誤って呼び出されると認証バイパスの可能性
- **修正**: プロダクションコードから完全に削除

### ORG-001: RLSポリシーの全面削除によるデータ分離の弱体化 (Agent-04)
- **ファイル**: `shared/supabase/migrations/20260130000003_fix_org_clerk_compat.sql`
- **問題**: Clerk互換性のため、全RLSポリシーが削除されている
- **影響**: テナント分離がアプリケーションロジックに完全依存。誤ったクエリは全組織のデータにアクセス可能
- **修正**: 全クエリにuser_id/organization_idフィルタが必須であることをコードレビューで徹底

### RLS-002: バックエンドがservice_role_keyのみ使用しRLSバイパス (Agent-11)
- **ファイル**: `backend/app/common/database.py:14-18`
- **問題**: 全DB操作がservice_role_key経由でRLSを完全バイパス
- **影響**: SQLインジェクションがあれば全テーブルの全データにアクセス可能
- **修正**: ユーザースコープ操作はanon_key + RLSポリシーの使用を検討

### RLS-006: usage_tracking/usage_logsがUSING(true)で全許可 (Agent-11)
- **ファイル**: `shared/supabase/migrations/20260202000001_add_usage_limits.sql`
- **問題**: ポリシー名は"Service role full access"だが、USING(true)で全ロールに許可
- **影響**: anon_keyでも全ユーザーの使用量データにアクセス可能
- **修正**: 適切なユーザーフィルタを追加するか、service_role専用に修正

---

## 📋 Medium 発見事項

### ORG-002: 招待トークンの有効期限が長い（7日） (Agent-04)
- **ファイル**: `backend/app/domains/organization/service.py:245`
- **問題**: 招待トークンの有効期限が7日と長め。トークン漏洩時のリスク窓口が大きい
- **修正**: 有効期限を24-72時間に短縮を検討

### ORG-003: adminによるadmin昇格が可能 (Agent-04)
- **ファイル**: `backend/app/domains/organization/service.py:145-166`
- **問題**: adminロールのユーザーが他のmemberをadminに昇格可能（権限の水平エスカレーション）
- **修正**: ownerのみがadminロールを付与できるように制限

（調査中...）

---

## 📝 Low 発見事項

### ORG-004: 組織削除時の関連データ残存 (Agent-04)
- **ファイル**: `backend/app/domains/organization/service.py:114-124`
- **問題**: articles, images等はカスケード削除されない。GDPR等のデータ削除要件に注意
- **修正**: データ保持ポリシーを文書化し、必要に応じて明示的な削除ロジックを追加

### ORG-005: オーナー権限の移譲機能の欠如 (Agent-04)
- **ファイル**: `backend/app/domains/organization/service.py`
- **問題**: オーナーシップを他のユーザーに移譲するAPIが存在しない
- **修正**: `POST /{org_id}/transfer-ownership` エンドポイントの実装を検討

---

## 📊 各エージェントの詳細報告

### Agent-01: Backend認証フロー
```
調査完了: 2026-02-04 (検証完了)

## 調査対象ファイル
- backend/app/common/auth.py (318行)
- backend/app/common/admin_auth.py (191行)
- backend/app/core/config.py (202行)

## 発見事項

### [CRITICAL] DEBUG_MODEによるJWT署名検証スキップ
- ファイル: backend/app/common/auth.py
- 行番号: 125-133, 34
- 問題: DEBUG=true 環境変数でJWT署名検証が完全にスキップされる
- コード:
  ```python
  DEBUG_MODE = os.getenv("DEBUG", "false").lower() == "true"
  ...
  if DEBUG_MODE:
      logger.warning("⚠️ [AUTH] DEBUG MODE: Skipping JWT signature verification!")
      decoded = jwt.decode(token, options={"verify_signature": False})
      return decoded
  ```
- 影響: 攻撃者が任意のJWTを作成し、任意のユーザーになりすまし可能
- 本番環境で誤ってDEBUG=trueが設定されると全認証が無効化される

### [HIGH] issuer/audience検証の欠如
- ファイル: backend/app/common/auth.py
- 行番号: 139-150
- 問題: jwt.decode()でissuer/audience検証が行われていない
- コード:
  ```python
  decoded = jwt.decode(
      token,
      signing_key.key,
      algorithms=["RS256"],
      options={
          "verify_signature": True,
          "verify_exp": True,
          "verify_iat": True,
          "require": ["exp", "iat", "sub"],
      }
      # iss, aud 検証なし
  )
  ```
- 影響: 他のClerkアプリケーション用に発行されたJWTでも認証可能

### [HIGH] テスト用署名スキップ関数がプロダクションコードに残存
- ファイル: backend/app/common/auth.py
- 行番号: 252-258
- 問題: validate_token_without_signature() が本番コードに存在
- コード:
  ```python
  def validate_token_without_signature(token: str) -> dict:
      """署名検証なしでトークンをデコード（デバッグ・テスト用）"""
      logger.warning("⚠️ [AUTH] validate_token_without_signature called - FOR TESTING ONLY")
      return jwt.decode(token, options={"verify_signature": False})
  ```
- 影響: 誤って呼び出されると認証バイパスの可能性

### [MEDIUM] エラーメッセージによる情報露出
- ファイル: backend/app/common/auth.py
- 行番号: 159, 225
- 問題: エラーメッセージに内部エラー詳細を露出
- コード:
  ```python
  raise HTTPException(status_code=401, detail=f"Invalid token: {e}")
  raise HTTPException(status_code=500, detail=f"Authentication error: {e}")
  ```
- 影響: 攻撃者がエラーメッセージから認証システムの詳細を推測可能

### [MEDIUM] JWKSキャッシュのレースコンディション
- ファイル: backend/app/common/auth.py
- 行番号: 86-110
- 問題: CachedJWKClientクラスにスレッドセーフでないアクセス
- コード:
  ```python
  def get_signing_key(self, token: str):
      if self._client is None or self._should_refresh():
          self._client = PyJWKClient(self.jwks_url, cache_keys=True)
          self._last_refresh = time.time()
  ```
- 影響: 複数リクエスト同時処理時にJWKSの不整合が発生する可能性

### [MEDIUM] Clerk API呼び出しのレート制限なし
- ファイル: backend/app/common/admin_auth.py
- 行番号: 33-96
- 問題: get_user_email_from_clerk_api()に対するレート制限がない
- 影響: 管理者エンドポイントへの大量リクエストでClerk APIを枯渇させる可能性

### [LOW] ログへのJWTクレーム情報出力
- ファイル: backend/app/common/auth.py
- 行番号: 155-156
- ファイル: backend/app/common/admin_auth.py
- 行番号: 119-121
- 問題: JWTクレームがログに出力される
- コード:
  ```python
  logger.info(f"🔒 [AUTH] JWT claims: iss={decoded.get('iss')}, azp={decoded.get('azp')}, exp={decoded.get('exp')}")
  ```
- 影響: ログファイルから認証情報が漏洩する可能性

### [LOW] admin_auth.pyでのHTTPException詳細露出
- ファイル: backend/app/common/admin_auth.py
- 行番号: 149
- 問題: 内部エラー詳細をHTTPレスポンスに含む
- コード:
  ```python
  raise HTTPException(detail=f"Authentication error: {e}")
  ```

## 良い実装
- RS256アルゴリズムの使用（対称鍵ではなく非対称鍵）
- JWKSエンドポイントからの公開鍵自動取得
- 有効期限(exp)と発行時刻(iat)の検証
- 必須クレーム(exp, iat, sub)の要求
- Clerk Backend APIを使った管理者メール取得（JWTにメールを含めない設計）

## 推奨修正
1. [CRITICAL] DEBUG_MODEフラグを完全に削除するか、本番環境では絶対に有効化できない仕組みを実装
2. [HIGH] issuer/audience検証を追加:
   ```python
   decoded = jwt.decode(
       token,
       signing_key.key,
       algorithms=["RS256"],
       issuer=f"https://{CLERK_FRONTEND_API}",
       audience="your-app-audience",
       options={"verify_signature": True, ...}
   )
   ```
3. [HIGH] validate_token_without_signature()をプロダクションコードから削除
4. [MEDIUM] エラーメッセージを一般化: "Authentication failed"
5. [MEDIUM] JWKSクライアントにスレッドロックを追加
6. [MEDIUM] Clerk API呼び出しにレート制限を追加
7. [LOW] ログからJWTクレーム詳細を削除（本番環境用ログレベル設定）
```

### Agent-02: Backend Blog API
```
調査完了: 2026-02-04

## 調査対象ファイル
- backend/app/domains/blog/endpoints.py (1466行)
- backend/app/domains/blog/schemas.py (230行)
- backend/app/domains/blog/services/crypto_service.py (141行)
- backend/app/domains/blog/services/image_utils.py (108行)
- backend/app/domains/blog/services/wordpress_mcp_service.py (690行)
- backend/app/domains/blog/services/generation_service.py (1595行)
- backend/app/domains/blog/agents/definitions.py (228行)
- backend/app/domains/blog/agents/tools.py (601行)

## 発見事項

### [HIGH] BLOG-001: ファイルパストラバーサルの潜在的リスク
- ファイル: backend/app/domains/blog/services/image_utils.py
- 行番号: 26-30
- 問題: _get_upload_dir でprocess_idをディレクトリ名として使用。UUIDv4なら安全だが、
  process_idが外部入力から来る場合、../等のパストラバーサル攻撃のリスクがある
- コード:
  def _get_upload_dir(process_id: str) -> str:
      base_dir = getattr(settings, "temp_upload_dir", None) or "/tmp/blog_uploads"
      upload_dir = os.path.join(base_dir, process_id)  # process_idが "../" を含むと危険
      os.makedirs(upload_dir, exist_ok=True)
      return upload_dir
- 影響: 任意のディレクトリへのファイル書き込み（DoSまたはサーバー侵害）
- 修正: process_idのバリデーション（UUIDv4形式チェック）を追加

### [HIGH] BLOG-002: 組織メンバーのWordPressサイト削除権限
- ファイル: backend/app/domains/blog/endpoints.py
- 行番号: 740-763
- 問題: delete_wordpress_site は組織メンバーであれば誰でもサイトを削除可能。
  ownerまたはadminのみ削除可能にすべき
- コード:
  if not result.data:
      # 組織経由のアクセスを確認して削除
      org_check = _get_org_site(supabase, site_id, user_id)
      if org_check.data:
          result = supabase.table("wordpress_sites").delete().eq("id", site_id).execute()
          # ロールチェックなしで削除
- 影響: 一般メンバーによる組織WordPressサイトの意図しない削除
- 修正: organization_membersテーブルでロール（owner/admin）を検証してから削除

### [MEDIUM] BLOG-003: WordPress認証情報の暗号化キー管理
- ファイル: backend/app/domains/blog/services/crypto_service.py
- 行番号: 31-48
- 問題: AES-256-GCMによる暗号化は適切だが、暗号化キーのローテーション機能がない
- 影響: キー漏洩時に全WordPressサイトの認証情報が危殆化
- 修正推奨: キーのバージョニング機能追加、キーローテーション時の再暗号化プロセス実装

### [MEDIUM] BLOG-004: 画像アップロード時のファイルタイプ検証不足
- ファイル: backend/app/domains/blog/endpoints.py
- 行番号: 963-1000
- 問題: 画像アップロードでファイル名の拡張子やMIMEタイプの検証がない
- 影響: 悪意のある画像ファイル（Pillow脆弱性を悪用）によるDoSやRCE
- 修正: MIMEタイプ検証とファイルサイズ制限の追加

### [MEDIUM] BLOG-005: MCPセッションIDの予測可能性
- ファイル: backend/app/domains/blog/services/wordpress_mcp_service.py
- 行番号: 156-184
- 問題: MCPセッションIDはWordPress MCP側で生成されるが、セッション固定攻撃への対策が不明
- 影響: セッションID傍受時にWordPressへの不正アクセス
- 修正推奨: MCPセッションの有効期限管理、セッションのIP/UA紐付け検証

### [MEDIUM] BLOG-006: イベントデータの機密情報露出
- ファイル: backend/app/domains/blog/endpoints.py
- 行番号: 1080-1093, 1209-1218
- 問題: blog_process_eventsにuser_answers（ユーザー回答）等の機密情報が含まれる可能性
- 影響: プロセスIDが漏洩した場合、他ユーザーの回答内容が参照される可能性
- 修正: 現状のuser_id検証は適切だが、機密情報のマスキングを検討

### [LOW] BLOG-007: エラーメッセージによる内部情報露出
- ファイル: backend/app/domains/blog/endpoints.py
- 行番号: 多数
- 問題: 例外処理で内部エラーメッセージがユーザーに返される
- 修正: ユーザー向けエラーメッセージを一般化し、詳細はログに記録

### [LOW] BLOG-008: トークンプレフィックスのログ出力
- ファイル: backend/app/domains/blog/services/wordpress_mcp_service.py
- 行番号: 76-80, 359-363
- 問題: アクセストークンの先頭8文字とSHA256ハッシュがINFOレベルでログに記録
- 修正: ログレベルをDEBUGに変更、または完全に削除

### [LOW] BLOG-009: 一時ファイルのクリーンアップ不足
- ファイル: backend/app/domains/blog/services/image_utils.py
- 行番号: 98-107
- 問題: cleanup_process_images の呼び出し箇所がない（プロセス完了時の自動クリーンアップなし）
- 修正: 生成完了/エラー/キャンセル時に自動的にクリーンアップを呼び出す

## 良い実装
- AES-256-GCM暗号化（crypto_service.py）
- 認証チェック（全エンドポイントでget_current_user依存）
- プロセス所有権検証（process_idとuser_idの両方で検証）
- 画像サイズ制限（MAX_DIMENSION = 2048）
- WebP変換による統一フォーマット
- MCPクライアントキャッシュの適切な無効化
- 組織メンバーシップ検証（_get_org_site関数）
- 使用量チェック（usage_service.check_can_generate）による429レスポンス

## 推奨修正
1. [HIGH] process_idのUUID形式バリデーション追加
2. [HIGH] 組織サイト削除のロールベースアクセス制御
3. [MEDIUM] 暗号化キーのバージョニングとローテーション機能
4. [MEDIUM] 画像MIMEタイプ検証とファイルサイズ制限
5. [MEDIUM] MCPセッションの有効期限・IP紐付け検証
6. [MEDIUM] イベントデータの機密情報マスキング検討
7. [LOW] エラーメッセージの一般化
8. [LOW] トークン情報のログレベル見直し
9. [LOW] 一時ファイルの自動クリーンアップ実装
```

### Agent-03: Backend Admin API
```
調査中...
```

### Agent-04: Backend Organization API
```
調査完了: 2026-02-04

## 調査対象ファイル
- backend/app/domains/organization/endpoints.py (269行)
- backend/app/domains/organization/service.py (342行)
- backend/app/domains/organization/schemas.py (4行 - スキーマはservice.pyに定義)
- shared/supabase/migrations/20250605152002_organizations.sql
- shared/supabase/migrations/20260130000003_fix_org_clerk_compat.sql (RLS削除)

## 発見事項

### [HIGH] ORG-001: RLSポリシーの全面削除によるデータ分離の弱体化
- ファイル: shared/supabase/migrations/20260130000003_fix_org_clerk_compat.sql
- 問題: Clerk互換性のため、全RLSポリシーが削除されている
- 影響範囲: organizations, organization_members, invitations,
  organization_subscriptions, articles, images, agent_log_sessions等
- 影響: テナント分離はアプリケーションロジックに完全依存。
  誤ったクエリは全組織のデータにアクセス可能
- 修正: 全クエリにuser_id/organization_idフィルタ必須をコードレビューで徹底

### [MEDIUM] ORG-002: 招待トークンの有効期限が長い（7日）
- ファイル: backend/app/domains/organization/service.py:245
- コード: expires_at = datetime.utcnow() + timedelta(days=7)
- 問題: 有効期限7日は長め。トークン漏洩時のリスク窓口が大きい
- 推奨: 招待トークンの有効期限を24-72時間に短縮を検討

### [MEDIUM] ORG-003: adminによるadmin昇格が可能
- ファイル: backend/app/domains/organization/service.py:145-166
- 問題: adminロールのユーザーが他のmemberをadminに昇格可能
- 影響: 権限の水平エスカレーション
- 推奨: ownerのみがadminロールを付与できるように制限

### [LOW] ORG-004: 組織削除時の関連データ残存
- ファイル: backend/app/domains/organization/service.py:114-124
- 注意: articles, images等はカスケード削除されない
- 推奨: データ保持ポリシーを文書化

### [LOW] ORG-005: オーナー権限の移譲機能の欠如
- 問題: オーナーシップを他のユーザーに移譲するAPIが存在しない
- 推奨: POST /{org_id}/transfer-ownership の実装を検討

## 良い実装
- 全エンドポイントでcurrent_user_id取得+権限チェック実施
- _user_has_access_to_org()/_user_is_org_admin()で一貫した権限検証
- 招待トークンは暗号学的に安全（secrets.token_urlsafe(32)）
- シート上限チェック実装
- オーナーのロール変更・離脱を禁止
- サブスク情報はadmin以上のみアクセス可能

## 推奨修正
1. [HIGH] RLS削除影響緩和のためテナントフィルタのユニットテスト追加
2. [MEDIUM] 招待トークン有効期限を72時間に短縮
3. [MEDIUM] adminロール付与をownerのみに制限
4. [LOW] オーナーシップ移譲機能の実装
5. [LOW] 組織削除時のデータ保持ポリシーを文書化
```

### Agent-05: Backend Usage API
```
調査中...
```

### Agent-06: Backend Image API
```
調査完了: 2026-02-04

## 調査対象ファイル
- backend/app/domains/image_generation/endpoints.py (~500行)
- backend/app/domains/image_generation/service.py (~380行)
- backend/app/infrastructure/external_apis/gcs_service.py (~220行)
- backend/app/domains/blog/services/image_utils.py (~100行)

## 発見事項

### [HIGH] IMG-001: ファイルアップロードのMIME type検証なし
- ファイル: backend/app/domains/image_generation/endpoints.py
- 行番号: 259-270 (upload_image関数)
- 問題: アップロードファイルのContent-Typeを信頼し、実際のファイル内容を検証していない
- 影響: 悪意のあるファイル（PHPスクリプト、HTML等）をイメージとしてアップロード可能
- 修正: PILでファイルを開いてイメージとして有効か検証

### [HIGH] IMG-002: ファイルサイズ制限なし
- ファイル: backend/app/domains/image_generation/endpoints.py (259-280行)
- ファイル: backend/app/domains/blog/endpoints.py (1370-1430行)
- 問題: アップロードファイルサイズに上限がない
- 影響: 大容量ファイルアップロードによるDoS攻撃、ストレージコスト増大、メモリ枯渇
- 修正: FastAPIでサイズ制限（例: 10MB上限）

### [MEDIUM] IMG-003: パストラバーサル対策は実装済みだがログなし
- ファイル: backend/app/domains/image_generation/endpoints.py (330-345行)
- 良い点: resolve()を使ったパストラバーサル防御が正しく実装されている
- 改善点: 攻撃試行時に警告ログを出力すべき

### [MEDIUM] IMG-004: GCS署名付きURLを使用していない
- ファイル: backend/app/infrastructure/external_apis/gcs_service.py (85-93行)
- 問題: GCSに保存された画像が公開URLでアクセス可能（アクセス制御なし）
- 影響: URLを知っていれば誰でも画像にアクセス可能
- 修正: 署名付きURLを使用、または非公開バケット + アプリ経由でプロキシ

### [MEDIUM] IMG-005: プレースホルダーIDが推測可能
- ファイル: backend/app/domains/image_generation/endpoints.py (24-35行)
- 問題: プレースホルダーIDはクライアントから受け取り、検証が不十分
- 修正: プレースホルダーIDとユーザー/記事の関連を厳密に検証

### [MEDIUM] IMG-006: 画像メタデータに機密情報が含まれる可能性
- ファイル: backend/app/domains/image_generation/endpoints.py (110-125行)
- 問題: 画像生成のmetadataにプロンプト全文が保存され、APIレスポンスに含まれる
- 修正: metadataをフィルタリングして機密情報を除外

### [LOW] IMG-007: Blog画像のローカルパスが予測可能
- ファイル: backend/app/domains/blog/services/image_utils.py (25-29行)
- 問題: 一時ファイルパスが /tmp/blog_uploads/{process_id}/ で予測しやすい
- 修正: ファイル権限を明示的に制限 (0600)

### [LOW] IMG-008: 画像削除時の権限チェックが不完全
- ファイル: backend/app/domains/image_generation/service.py (275-285行)
- 問題: delete_image()はパスのみで削除、所有者チェックがサービス層にない

## 良い実装
- パストラバーサル対策が /serve/{filename} エンドポイントに実装済み
- Blog画像アップロードでWebP変換時にPILで画像を開いて検証
- 画像リサイズで最大2048pxに制限
- GCS upload時にUUID + 日付階層でファイル名衝突を回避
- マジックバイトによる拡張子推定 (_guess_extension_from_data)

## 推奨修正
1. [HIGH] ファイルアップロード時にPILで画像として開けるか検証
2. [HIGH] ファイルサイズ制限を追加（10MB上限推奨）
3. [MEDIUM] GCS署名付きURLの使用を検討
4. [MEDIUM] 攻撃試行時のセキュリティログ追加
5. [LOW] 一時ファイルのパーミッションを制限
```

### Agent-07: Frontend API Routes (proxy)
```
調査完了: 2026-02-04

## 調査対象ファイル
- frontend/src/app/api/proxy/[...path]/route.ts (195行)
- frontend/next.config.js (23行)
- frontend/src/middleware.ts (77行)

## 発見事項

### [HIGH] PROXY-001: プロキシルートに認証チェックがない
- ファイル: frontend/src/app/api/proxy/[...path]/route.ts
- 行番号: 全体（特に buildHeaders関数 67-77行）
- 問題: プロキシAPIルートはClerkセッション検証を行わず、Authorizationヘッダーを単純に転送
- コード:
  function buildHeaders(request: NextRequest, includeContentType = true) {
    const headers: Record<string, string> = {};
    if (includeContentType) headers['Content-Type'] = 'application/json';
    const authHeader = request.headers.get('Authorization');
    if (authHeader) headers['Authorization'] = authHeader;  // 検証なしで転送
    return headers;
  }
- 影響:
  - middleware.tsのprotectedRouteに /api/* が含まれていないため認証チェックなし
  - バックエンドのJWT検証に完全依存（Defense in Depthの原則に違反）
  - AUTH-001（DEBUG_MODE）との組み合わせで完全な認証バイパスが発生

### [HIGH] PROXY-002: SSRF（Server-Side Request Forgery）の可能性
- ファイル: frontend/src/app/api/proxy/[...path]/route.ts
- 行番号: 79-88, 92-118, 122-142
- 問題: pathパラメータのバリデーションがなく、任意のパスをバックエンドに転送可能
- コード:
  export async function GET(request: NextRequest, { params }) {
    const { path: pathArray } = await params;
    const pathString = ensureTrailingSlash(pathArray.join('/'));
    // pathStringのバリデーションなし
    const url = `${API_BASE_URL}/${pathString}`;
- 影響:
  - 内部APIエンドポイント（/health, /admin/*, /internal/*など）へのアクセス可能
  - バックエンドの未公開エンドポイント探索が可能
  - リダイレクト追従（301/302/307/308）で内部サービスへのアクセスも可能

### [MEDIUM] PROXY-003: 過度に緩いCORS設定
- ファイル: frontend/src/app/api/proxy/[...path]/route.ts
- 行番号: 58-62, 182-187
- 問題: Access-Control-Allow-Origin: * を設定
- コード:
  return NextResponse.json(data, {
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, PUT, PATCH, DELETE, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    },
  });
- 影響: 悪意のあるサイトからのクロスオリジンリクエストが可能

### [MEDIUM] PROXY-004: next.config.jsとroute.tsの二重設定・ポート不整合
- ファイル: frontend/next.config.js, frontend/src/app/api/proxy/[...path]/route.ts
- 問題: 同パスに2つの異なるプロキシ機構、フォールバックポートが異なる
- next.config.js: destination: 'http://localhost:8000/:path*'
- route.ts: API_BASE_URL = 'http://localhost:8080'
- 影響: 設定の不整合による予期せぬ動作

### [LOW] PROXY-005: 冗長なログ出力による情報露出
- ファイル: frontend/src/app/api/proxy/[...path]/route.ts
- 行番号: 85, 111
- 問題: リクエストごとにURLと認証有無をconsole.logで出力
- 影響: 認証なしリクエストパターンの分析可能、リダイレクト先URL露出

## 良い実装
- Authorization ヘッダーの転送（バックエンドでの検証を前提）
- リダイレクト時のAuthorizationヘッダー保持
- FormDataの適切なハンドリング
- 120秒のproxyTimeout設定

## 推奨修正
1. [HIGH] プロキシルートにClerkセッション検証を追加
2. [HIGH] パスのホワイトリスト検証を追加
3. [MEDIUM] CORS設定を特定オリジンのみに制限
4. [MEDIUM] next.config.jsのrewriteを削除して設定を一本化
5. [LOW] 本番環境ではログ出力を抑制
```

### Agent-08: Frontend API Routes (subscription)
```
調査中...
```

### Agent-09: Frontend API Routes (webhooks)
```
調査完了: 2026-02-04

## 調査対象ファイル
- frontend/src/app/api/webhooks/route.ts (Stripe Webhook - 77行)
- frontend/src/app/api/webhooks/clerk/route.ts (Clerk Webhook - 178行)
- frontend/src/features/account/controllers/upsert-user-subscription.ts (97行)
- frontend/src/libs/stripe/stripe-admin.ts (19行)

## 発見事項

### [HIGH] WH-001: Stripe Webhook署名検証の早期リターン問題
- ファイル: frontend/src/app/api/webhooks/route.ts
- 行番号: 23-25
- 問題: 署名またはシークレットが欠けている場合に早期リターンするが、HTTPレスポンスを返していない
- コード: if (!sig || !webhookSecret) return;
- 影響: 署名なしリクエストでエラーレスポンスなく終了、Next.jsが不正レスポンスエラーを返す
- 修正: 明示的に400エラーレスポンスを返す

### [HIGH] WH-002: Webhook再送攻撃への耐性がない
- ファイル: 両webhookファイル
- 問題: 処理済みWebhookイベントを追跡するメカニズムがない
- 影響: 同じevent.id/svix-idのWebhookが複数回処理される可能性
- 修正: 処理済みイベントIDをDBに保存し重複チェック実装

### [MEDIUM] WH-003: Stripeエラーメッセージの情報露出
- ファイル: frontend/src/app/api/webhooks/route.ts:28
- 問題: 署名検証エラー時に内部エラーメッセージを露出
- コード: return Response.json(`Webhook Error: ${(error as any).message}`)
- 修正: 一般的なエラーメッセージに変更

### [MEDIUM] WH-004: Clerk Webhookのログ出力による情報露出
- ファイル: frontend/src/app/api/webhooks/clerk/route.ts
- 問題: ユーザーID、メールアドレス、組織ID等の機密情報がログに出力
- 修正: 本番環境でのログレベル制御か機密情報マスキング

### [MEDIUM] WH-005: 特権判定の不整合リスク
- ファイル: frontend/src/app/api/webhooks/clerk/route.ts:57-77
- 問題: is_privilegedフラグがuser.created時のみ設定、user.updatedで再評価なし
- 影響: メールアドレス変更後も特権フラグが更新されない
- 修正: user.updatedイベントで特権フラグを再評価

### [LOW] WH-006: 未処理イベントタイプのログ不足
- ファイル: frontend/src/app/api/webhooks/route.ts:65
- 問題: relevantEventsにないイベントは無視されログも残らない
- 修正: 無視されるイベントタイプもログ出力

### [LOW] WH-007: Stripeアプリ名が未設定
- ファイル: frontend/src/libs/stripe/stripe-admin.ts:11
- 問題: appInfoが "UPDATE_THIS_WITH_YOUR_STRIPE_APP_NAME" のまま
- 修正: 正しいアプリ名を設定

## 良い実装
- Clerk: svixライブラリによる署名検証（HMAC SHA256）
- Clerk: svix-id, svix-timestamp, svix-signatureのすべてを検証
- Stripe: constructEvent()による署名検証
- Clerk: 組織オーナーの重複挿入スキップロジック
- 両方: try-catchによるエラーハンドリング
- Clerk: upsertによるレコード重複防止

## 推奨修正
1. [HIGH] Stripe署名欠落時の明示的400エラーレスポンス
2. [HIGH] processed_webhook_eventsテーブル追加と重複チェック
3. [MEDIUM] エラーメッセージの一般化
4. [MEDIUM] ログレベル制御
5. [MEDIUM] user.updatedイベントハンドラ追加
6. [LOW] 無視イベントのログ出力
7. [LOW] Stripeアプリ名設定
```

### Agent-10: Frontend Middleware
```
調査中...
```

### Agent-11: Supabase RLS / DB
```
調査完了: 2026-02-04
詳細レポート: docs/agent11_rls_findings.md

## 調査対象ファイル
- shared/supabase/migrations/ (34ファイル)
- shared/supabase/config.toml
- backend/app/common/database.py
- frontend/src/libs/supabase/*.ts

## 発見事項サマリー

### [CRITICAL] RLS-001: 15テーブルでRLSポリシーが削除済み
- ファイル: 20260130000003_fix_org_clerk_compat.sql
- 問題: Clerk互換性修正で31ポリシーを削除、再作成なし
- 影響テーブル: organizations, organization_members, invitations,
  organization_subscriptions, generated_articles_state, articles,
  article_generation_flows, flow_steps, style_guide_templates, images,
  agent_log_sessions, agent_execution_logs, llm_call_logs, tool_call_logs,
  workflow_step_logs
- 影響: anon_keyでは全データアクセス不可、service_role_key依存

### [HIGH] RLS-002: バックエンドがservice_role_keyのみ使用
- ファイル: backend/app/common/database.py:14-18
- 影響: Defense in Depth欠如、SQLi耐性低下

### [HIGH] RLS-003: フロントエンドAPIルートでservice_role_key使用
- ファイル: frontend/src/libs/supabase/supabase-admin.ts
- ファイル: frontend/src/app/api/articles/generation/*.ts

### [HIGH] RLS-004: 子テーブルポリシーが削除済み親テーブルを参照
- article_generation_step_snapshots, article_edit_versions

### [MEDIUM] RLS-005: customersテーブルにポリシーなし（意図的）
### [MEDIUM] RLS-006: usage_tracking/usage_logsがUSING(true)で全許可
### [MEDIUM] RLS-007: plan_tiersが全世界に公開
### [MEDIUM] RLS-008: Realtimeがユーザー分離なし

### [LOW] RLS-009: WordPress認証情報はAES-256-GCM暗号化（良い実装）
### [LOW] RLS-010: products/pricesが公開（意図的）

## 推奨修正
1. [CRITICAL] 15テーブルのRLSポリシー再作成または明示的無効化
2. [HIGH] usage_tracking/usage_logsポリシー修正
3. [HIGH] Realtime subscriptionセキュリティ検討
4. [MEDIUM] フロントエンドのservice_role_key使用最小化
```

### Agent-12: Clerk設定・JWT
```
調査完了: 2026-02-04

## 調査対象ファイル
- backend/app/common/auth.py (JWT検証)
- backend/app/infrastructure/clerk_client.py (Clerk API クライアント)
- frontend/src/middleware.ts (Next.js Clerk統合)
- frontend/src/app/api/webhooks/clerk/route.ts (Clerk Webhook)
- backend/app/common/admin_auth.py (管理者認証)
- backend/app/core/config.py (設定)

## 発見事項

### [HIGH] CLERK-001: セッション管理でのメール取得がAPI依存
- ファイル: frontend/src/middleware.ts
- 行番号: 42-50
- 問題: getUserEmail()がClerk APIを毎リクエスト呼び出す可能性
- 影響:
  - Clerk APIへの過剰なリクエスト（DDoS増幅攻撃の可能性）
  - レート制限に達した場合、特権チェックが失敗し意図しないアクセス拒否
  - API障害時に管理者もアクセス不能になる
- 推奨: sessionClaimsにカスタムクレームとしてメールを含めるか、キャッシュ機構を導入

### [HIGH] CLERK-002: Webhook秘密鍵の検証タイミング問題
- ファイル: frontend/src/app/api/webhooks/clerk/route.ts
- 行番号: 15-18, 21-24
- 問題: CLERK_WEBHOOK_SECRETの存在チェックがリクエスト処理中
- 影響:
  - 本番環境で秘密鍵未設定でもサーバー起動成功（起動時検証なし）
  - 初回Webhookリクエスト時に初めてエラーが判明
  - エラーログに設定不備が記録され、攻撃者に情報提供

### [MEDIUM] CLERK-003: MFA（多要素認証）の未強制
- ファイル: frontend/src/middleware.ts, Clerk Dashboard設定
- 問題: Clerk側でMFAを必須設定していない場合、パスワードのみで管理者アクセス可能
- 影響:
  - @shintairiku.jp ドメインのアカウント侵害時、全管理機能にアクセス可能
  - 特権ユーザーはサブスクリプションなしで全機能使用可能
- 推奨: 管理者ドメインのユーザーにはMFA必須を設定

### [MEDIUM] CLERK-004: トークンリフレッシュ処理の不透明性
- ファイル: frontend/src/middleware.ts
- 問題: Clerkミドルウェアがトークンリフレッシュを自動処理するが、失敗時のフォールバック動作が不明確
- 影響:
  - トークン期限切れ時の挙動がClerkライブラリ依存
  - リフレッシュ失敗時にユーザーが予期しないログアウト
- 推奨: リフレッシュ失敗時の明示的なハンドリングを追加

### [MEDIUM] CLERK-005: Clerk APIキー露出リスク（環境変数管理）
- ファイル: backend/.env.example, frontend/.env.example
- 問題: CLERK_SECRET_KEY, CLERK_PUBLISHABLE_KEYの実際の形式がexampleに記載
- 影響: 攻撃者がキー形式を把握し、ブルートフォース攻撃の補助情報に
- 推奨: exampleでは your-clerk-secret-key などの一般的なプレースホルダを使用

### [LOW] CLERK-006: Clerk Client での同期HTTPリクエスト
- ファイル: backend/app/infrastructure/clerk_client.py
- 行番号: 33-67
- 問題: httpx.Client()で同期HTTPリクエストを使用（非同期ではない）
- 影響:
  - イベントループのブロッキング（FastAPIの非同期処理に影響）
  - 大量のユーザー取得時にレスポンス遅延
- 推奨: AsyncClientへの移行

### [LOW] CLERK-007: ユーザー取得のページネーション上限なし
- ファイル: backend/app/infrastructure/clerk_client.py
- 行番号: 22-67
- 問題: get_all_users()が全ユーザーを取得するまでループ（制限なし）
- 影響: ユーザー数が膨大な場合にメモリ枯渇やタイムアウト
- 推奨: 最大取得件数の制限を追加

### [LOW] CLERK-008: Webhook処理でのSupabase Admin Client使用
- ファイル: frontend/src/app/api/webhooks/clerk/route.ts
- 行番号: 6, 50
- 問題: supabaseAdminClientを使用してRLSをバイパス
- 影響:
  - Webhookリクエストが偽装された場合、RLSなしでDB操作される
  - svix署名検証は実施されているが、バイパス時の影響が大きい
- 推奨: 最小権限の原則に従い、必要な操作のみ許可するService Role設計

## 良い実装
- Clerk @clerk/nextjs v6 の clerkMiddleware() 使用（推奨パターン）
- createRouteMatcher() によるルート保護の明確な定義
- svix ライブラリによる Webhook 署名検証（業界標準）
- 管理者判定を @shintairiku.jp ドメインで実施（ホワイトリスト方式）
- Clerk Backend API経由でのメール取得（JWTにメールを含めない安全設計）
- RS256非対称鍵による署名検証（backend/app/common/auth.py）

## 推奨修正
1. [HIGH] Middlewareでのメール取得をキャッシュ化、またはsessionClaimsにカスタムクレーム追加
2. [HIGH] Webhook秘密鍵の起動時検証を追加
3. [MEDIUM] 管理者ユーザーにMFA必須を設定（Clerk Dashboard）
4. [MEDIUM] トークンリフレッシュ失敗時の明示的エラーハンドリング追加
5. [MEDIUM] .env.exampleのプレースホルダを一般化
6. [LOW] Clerk Clientを非同期化（AsyncClient使用）
7. [LOW] get_all_users()に最大取得件数制限を追加
```

### Agent-13: Stripe設定・Webhook
```
調査中...
```

### Agent-14: XSS脆弱性全箇所
```
調査中...
```

### Agent-15: 入力バリデーション
```
調査完了: 2026-02-04 (検証完了)

## 調査対象ファイル
- backend/app/domains/seo_article/schemas.py (525行)
- backend/app/domains/admin/schemas.py (196行)
- backend/app/domains/company/schemas.py (73行)
- backend/app/domains/blog/schemas.py (190行)
- backend/app/domains/blog/endpoints.py (960行)
- backend/app/domains/organization/endpoints.py (230行)
- backend/app/domains/seo_article/endpoints.py (2200行)
- backend/app/domains/image_generation/endpoints.py (750行)

## 発見事項

### [HIGH] VAL-001: user_prompt にLLMプロンプトインジェクション対策なし
- ファイル: backend/app/domains/blog/schemas.py:97-101
- 問題: max_length=2000 があるが、プロンプトインジェクション対策なし
- 影響: 悪意あるプロンプトがLLMに直接渡される可能性

### [HIGH] VAL-002: initial_keywords に配列サイズ制限なし
- ファイル: backend/app/domains/seo_article/schemas.py:27
- 問題: List[str] にサイズ制限がない
- 影響: 大量要素でDoS可能

### [HIGH] VAL-003: AIEditRequest にサイズ制限なし
- ファイル: backend/app/domains/seo_article/endpoints.py:138-143
- 問題: content, instruction, article_html に max_length なし
- 影響: メモリ枯渇の可能性

### [MEDIUM] VAL-004: site_url にURL形式バリデーションなし
- ファイル: backend/app/domains/blog/endpoints.py:77-85
- 問題: str 型でURL検証なし
- 影響: SSRF攻撃に利用可能

### [MEDIUM] VAL-005-009: その他の中程度問題
- organization name に特殊文字制限なし
- image_settings, blog_context が Dict[str, Any] で検証なし
- ファイルアップロードのサイズ事前チェックなし
- process_id/article_id のUUID検証なし

### [LOW] VAL-010-013: 低程度問題
- schemas.py が空/散在
- スタブクラスが残存

## 良い実装
- CompanyInfoBase に適切な max_length
- EmailStr, HttpUrl の使用
- num_* フィールドに ge=1 制約

## 推奨修正
1. [HIGH] List[str] に max_items 制約追加
2. [HIGH] LLM入力にサニタイズ処理追加
3. [MEDIUM] URL フィールドを HttpUrl 型に統一
4. [MEDIUM] Dict[str, Any] にスキーマ/サイズ制限定義
```

### Agent-16: エラーハンドリング
```
調査中...
```

### Agent-17: ログ・機密情報露出
```
調査完了: 2026-02-04

## 調査対象ファイル
- backend/app/ 配下の全Pythonファイル (logger使用箇所: 200+箇所)
- frontend/src/ 配下の全TypeScriptファイル (console使用箇所: 150+箇所)

## 発見事項

### [HIGH] LOG-001: APIキー部分露出 (SerpAPI)
- ファイル: backend/app/infrastructure/external_apis/serpapi_service.py
- 行番号: 353
- 問題: SerpAPI呼び出し時にAPIキーの末尾4文字をログ出力
- コード: print(f"...API Key: {str(settings.serpapi_key)[-4:]}")
- 影響: APIキーの一部が露出し、ブルートフォース攻撃の足がかりになる可能性

### [HIGH] LOG-002: OpenAI APIキー部分露出
- ファイル: backend/app/core/config.py
- 行番号: 163
- 問題: 起動時にOpenAI APIキーの先頭8文字をログ出力
- コード: print(f"OpenAI API キーを設定しました: {settings.openai_api_key[:8]}...")
- 影響: APIキープレフィックスの露出によりキー形式・プロバイダーが特定可能

### [HIGH] LOG-003: JWTトークンプレフィックス露出 (Frontend)
- ファイル: frontend/src/features/tools/seo/generate/new-article/display/GenerationProcessPage.tsx:86-87
- ファイル: frontend/src/hooks/useSupabaseRealtime.ts:177
- 問題: JWTトークンの先頭20文字をconsole.logで出力
- 影響: ブラウザコンソールからJWTヘッダー部分が漏洩、トークン構造が特定可能

### [MEDIUM] LOG-004: メールアドレスのログ出力
- ファイル: backend/app/common/admin_auth.py (行: 98, 167, 173)
- ファイル: frontend/src/app/(admin)/admin/layout.tsx (行: 36, 41)
- 問題: 管理者認証時にユーザーのメールアドレスをログ出力
- 影響: PII(個人情報)がログに残り、漏洩時にプライバシー侵害のリスク

### [MEDIUM] LOG-005: user_idの過剰なログ出力
- ファイル: 複数のバックエンドファイル (50+箇所)
- 主な箇所: generation_service.py, endpoints.py, admin/service.py
- 問題: user_idがINFOレベルで広範にログ出力
- 影響: ユーザー行動の追跡が可能、ログ分析による個人特定のリスク

### [MEDIUM] LOG-006: 詳細エラー情報のログ出力
- ファイル: backend/app/core/exceptions.py (行: 43, 53)
- 問題: グローバル例外ハンドラがスタックトレースをprint出力
- 影響: 本番環境で詳細なスタックトレースが出力、内部実装が露出

### [MEDIUM] LOG-007: logger.exception()の広範な使用
- ファイル: generation_service.py, auth.py:253, admin_auth.py:186 等 (20+箇所)
- 問題: logger.exception()が詳細なスタックトレースを出力
- 影響: 本番ログに詳細なデバッグ情報が残り、攻撃者に有用な情報を提供

### [MEDIUM] LOG-008: JWTクレーム情報のログ出力
- ファイル: backend/app/common/auth.py:221, admin_auth.py:149-150
- 問題: JWTのクレーム(iss, azp等)がINFO/DEBUGレベルでログ出力
- 影響: 認証システムの設定情報がログに露出

### [LOW] LOG-009: デバッグ用print文の残存
- ファイル: backend/app/domains/seo_article/services/article_agent_service.py
- 行番号: 254, 510, 708-712, 791, 810-815, 862-914
- 問題: 開発用のprint文が多数残存
- 影響: 本番環境で不要な出力、パフォーマンスとログ可読性に影響

### [LOW] LOG-010: Rich console.printの残存
- ファイル: backend/app/domains/seo_article/services/_generation_flow_manager.py (50+箇所)
- 問題: Rich libraryのconsole.printがデバッグ出力として残存
- 影響: 本番環境で装飾付きのデバッグ出力が混入

### [LOW] LOG-011: Stripe Webhook署名シークレット存在確認ログ
- ファイル: frontend/src/app/api/subscription/webhook/route.ts:44
- 問題: Webhook署名検証失敗時に「Missing signature or webhook secret」をログ出力
- 影響: シークレット設定の有無が外部から推測可能

### [LOW] LOG-012: 招待メール送信のログ
- ファイル: backend/app/domains/organization/service.py:351
- 問題: 招待メールアドレスをINFOレベルでログ出力
- 影響: メールアドレスがログファイルに残存

## 良い実装
- Stripe APIキーはログに出力されていない
- Supabase Service Role Keyはログに出力されていない
- Clerk Secret Keyはログに出力されていない
- 認証成功時のログはuser_idのみで、トークン全体は出力していない

## 推奨修正

### 即時対応が必要
1. [HIGH] LOG-001, LOG-002: APIキーの部分露出を完全に削除
2. [HIGH] LOG-003: フロントエンドのJWTトークンログを削除

### 中期対応
3. [MEDIUM] LOG-004: メールアドレスはマスク処理を適用
4. [MEDIUM] LOG-006, LOG-007: 本番環境でのスタックトレース出力を無効化
5. [MEDIUM] LOG-008: JWTクレームのログ出力をDEBUGレベルに変更

### 長期対応
6. [LOW] LOG-009, LOG-010: 全てのprint/console.printを標準loggerに統一
7. [LOW] ログレベルポリシーの策定

## 相互関係
- Agent-01 (Backend認証フロー): LOG-003, LOG-008は認証システムのログ露出と関連
- Agent-16 (エラーハンドリング): LOG-006, LOG-007はエラーハンドリング設計と関連
- Agent-20 (環境変数・シークレット): LOG-001, LOG-002はシークレット管理と関連
```

### Agent-18: Docker・CI/CD
```
調査完了: 2026-02-04

## 調査対象ファイル
- backend/Dockerfile (25行)
- frontend/Dockerfile (61行)
- docker-compose.yml (70行)
- .github/workflows/backend-docker-build.yml (55行)

## 発見事項

### [CRITICAL] DOCKER-001: 機密情報がDockerビルドキャッシュ・レイヤーに残存
- ファイル: frontend/Dockerfile:20-27
- 問題: ARGとENVで機密情報(STRIPE_SECRET_KEY, SUPABASE_SERVICE_ROLE_KEY)をビルド時に渡す
- 影響: Dockerイメージのレイヤーに機密情報が永続的に埋め込まれる。docker historyで露出
- 修正: ランタイム環境変数としてのみ渡す

### [HIGH] DOCKER-002: Backendコンテナがrootユーザーで実行
- ファイル: backend/Dockerfile
- 問題: USERディレクティブがなく、デフォルトのrootユーザーで実行
- 影響: コンテナエスケープ攻撃時にホストのroot権限取得の可能性
- 修正: RUN useradd + USER appuser

### [HIGH] DOCKER-003: docker-composeでStripe APIキーが平文でコマンドに渡される
- ファイル: docker-compose.yml:52
- 問題: stripe-cliサービスでAPIキーがcommandに直接記述
- 影響: docker compose ps/ps auxでAPIキーが露出
- 修正: 環境変数経由でstripe-cliに渡す

### [MEDIUM] DOCKER-004: ベースイメージのセキュリティスキャンなし
- ファイル: backend/Dockerfile, frontend/Dockerfile
- 問題: python:3.12-slim, node:22-alpine のセキュリティ検証なし
- 修正: CI/CDにTrivy等のコンテナスキャンを追加

### [MEDIUM] DOCKER-005: CI/CDでセキュリティスキャンが未実施
- ファイル: .github/workflows/backend-docker-build.yml
- 問題: ビルドテストのみで脆弱性スキャンなし
- 修正: Trivy脆弱性スキャナをCI/CDに追加

### [MEDIUM] DOCKER-006: docker-composeで開発用ボリュームマウントのリスク
- ファイル: docker-compose.yml:21-23,36
- 問題: ソースコードディレクトリがそのままマウント、.envファイル等も含まれる
- 修正: 本番環境ではボリュームマウントなし

### [LOW] DOCKER-007: .dockerignoreファイルの不在
- ファイル: backend/, frontend/
- 問題: 不要なファイル(.git, .env等)がビルドコンテキストに含まれる
- 修正: .dockerignoreを追加

### [LOW] DOCKER-008: イメージタグのバージョン固定なし
- ファイル: backend/Dockerfile, frontend/Dockerfile
- 問題: 浮動タグ(python:3.12-slim等)で再現性のないビルド
- 修正: SHA256ダイジェスト使用

## 良い実装
- frontendでnodeユーザーへの切り替え (USER node)
- マルチステージビルドの使用
- standalone出力によるイメージサイズ最小化
- ネットワーク分離（app_network使用）
- CI/CDでのビルドテスト実施

## 推奨修正
1. [CRITICAL] フロントエンドDockerfileから機密情報のARG/ENV削除
2. [HIGH] バックエンドDockerfileに非rootユーザー設定を追加
3. [HIGH] stripe-cliコマンドからAPIキー直接指定を削除
4. [MEDIUM] CI/CDにコンテナ脆弱性スキャン追加
5. [LOW] .dockerignoreファイルの追加

## 相互関係
- Agent-17: DOCKER-001はシークレット管理と関連
- Agent-20: DOCKER-001, DOCKER-003はシークレット管理と関連
```

### Agent-19: 依存パッケージ脆弱性
```
調査完了: 2026-02-04

## 調査対象ファイル
- backend/pyproject.toml
- backend/uv.lock (462KB, 115パッケージ)
- frontend/package.json
- frontend/bun.lockb (452KB)
- frontend/package-lock.json (415KB)

## 発見事項

### [HIGH] DEP-001: バージョン固定なしの依存関係定義
- ファイル: backend/pyproject.toml
- 問題: 全ての依存関係がバージョン未指定（フローティング依存）
- 影響:
  - サプライチェーン攻撃のリスク増大（悪意あるバージョンが自動取得される可能性）
  - ビルドの再現性がない（異なる環境で異なるバージョンがインストールされる）
- 備考: uv.lock は存在するが、CI/CDで lock ファイルを使用しているか要確認

### [HIGH] DEP-002: google-generativeai パッケージの非推奨警告
- ファイル: backend/pyproject.toml, backend/uv.lock
- 現在のバージョン: google-generativeai 0.8.6
- 問題: google-generativeai は非推奨で google-genai への移行が推奨されている
- 影響: 将来的なセキュリティパッチが提供されない可能性

### [MEDIUM] DEP-003: 暗号化ライブラリのバージョン監視不足
- ファイル: backend/uv.lock
- 現在: cryptography 46.0.4, pyjwt 2.11.0
- 推奨: Dependabot/Renovate等の自動更新ツールを導入

### [MEDIUM] DEP-004: psycopg2-binary の使用
- ファイル: backend/pyproject.toml
- 問題: 本番では psycopg2（ソースビルド）推奨

### [MEDIUM] DEP-005: フロントエンド大量Majorアップデート
- @stripe/stripe-js 2.4.0->8.7.0, stripe 18.5.0->20.3.0 etc.
- 推奨: 各Majorアップデートのセキュリティ変更点を確認

### [MEDIUM] DEP-006: ESLint 8.x の使用
- 現在: eslint 8.57.1（v9はflat config。意図的据え置き）

### [LOW] DEP-007: 開発依存関係のセキュリティ
- pytest, prettier, eslint-* 等も定期監査推奨

### [LOW] DEP-008: 未使用パッケージの可能性
- geist/geist-ui/@geist-ui/core, classnames/clsx, react-icons/lucide-react
- 攻撃対象面積増大。未使用パッケージの特定・削除推奨

### [LOW] DEP-009: lock ファイルの同期状態
- bun.lockb と package-lock.json の両方が存在
- 推奨: bun.lockb に統一、package-lock.json 削除

## 主要パッケージのバージョン一覧

### Backend (Python)
fastapi 0.128.0, uvicorn 0.40.0, openai 2.16.0, openai-agents 0.7.0
pydantic 2.12.5, cryptography 46.0.4, pyjwt 2.11.0, sqlalchemy 2.0.46
google-generativeai 0.8.6 (非推奨 -> google-genai 1.61.0 移行推奨)

### Frontend (Node.js)
next 15.5.11, react 19.2.4, @clerk/nextjs 6.37.1, stripe 20.3.0
@supabase/supabase-js 2.93.3, zod 3.25.76, tailwindcss 3.4.19

## 良い実装
- uv.lock が存在しロックファイルで依存関係がピン留め
- メジャーバージョンの更新履歴がCLAUDE.mdに記録されている
- 一部パッケージは意図的に据え置き判断

## 推奨修正
1. [HIGH] pyproject.toml に最低バージョン制約を追加
2. [HIGH] google-generativeai -> google-genai への移行計画を策定
3. [MEDIUM] Dependabot/Renovate による自動セキュリティ更新を設定
4. [MEDIUM] CI/CDでuv.lock/bun.lockbを使用した再現可能ビルドを確認
5. [LOW] 未使用パッケージの特定・削除（depcheck等のツール使用）
6. [LOW] package-lock.json を削除し bun.lockb に統一
```

### Agent-20: 環境変数・シークレット
```
調査中...
```

---

## 🔗 相互関係・依存関係の発見

（調査中...）

---

## ✅ 推奨修正アクション（優先順位付き）

（調査完了後に集約...）

---
