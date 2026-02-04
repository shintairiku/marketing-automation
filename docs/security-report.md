# セキュリティ監査レポート

**対象**: BlogAI / Marketing Automation Platform
**監査日**: 2026-02-03
**監査者**: Claude Opus 4.5 (自動セキュリティ監査)
**対象ブランチ**: develop (コミット 58a65c3)

---

## エグゼクティブサマリー

本プラットフォームは、FastAPI バックエンド (Cloud Run) + Next.js 15 フロントエンド + Supabase (PostgreSQL) + Clerk 認証 + Stripe 課金で構成されるSaaS型ブログ自動生成サービスである。

監査の結果、**Critical 2件、High 7件、Medium 8件、Low 5件**の脆弱性を検出した。

最も深刻な問題は以下の2点:
1. **Cloud Run上のバックエンドAPIが認証なしで直接アクセス可能**: Cloud Runのパブリックエンドポイントに直接HTTPリクエストを送れば、フロントエンドのプロキシとNext.js middlewareの認証チェックを完全にバイパスできる。
2. **RLSポリシーの全面削除**: Clerk移行時にSupabaseのRow Level Securityポリシーが全テーブルから削除されており、バックエンドのservice_roleキー経由でデータベースにアクセスする全ての処理が、適切なアクセス制御なしにデータを読み書きできる状態になっている。

---

## Critical（致命的）脆弱性

### CRIT-01: Cloud Run バックエンドAPI の直接アクセスによる認証バイパス

- **場所**: `backend/main.py` (全体), Cloud Run デプロイメント構成
- **CWE**: CWE-306 (Missing Authentication for Critical Function)
- **CVSS**: 9.8 (Critical)

- **説明**:
  本アプリケーションのアーキテクチャでは、フロントエンド (Next.js) がバックエンド (FastAPI) への唯一のゲートウェイとして機能し、`/api/proxy/[...path]/route.ts` がリクエストを転送する設計になっている。しかし、Cloud Run にデプロイされたバックエンドAPIは**パブリックURLで直接アクセス可能**である。

  攻撃者が Cloud Run の URL を知っている場合（DNS、ネットワーク通信の観察、エラーメッセージのリーク等で取得可能）、フロントエンドの認証ミドルウェアを完全にバイパスし、バックエンドの全エンドポイントに直接アクセスできる。

  バックエンド側にも Clerk JWT 検証（`get_current_user_id_from_token`）は実装されているが、**一部のエンドポイントは認証なしでアクセス可能**:

  ```python
  # backend/app/domains/image_generation/endpoints.py
  @router.get("/serve/{image_filename}")
  async def serve_image(image_filename: str):
      # 認証チェックなし - 誰でもアクセス可能
  ```

  ```python
  # backend/main.py
  @app.get("/")
  async def read_root():
      return {"message": "Welcome to the SEO Article Generation API (WebSocket)!"}

  @app.get("/health")
  async def health_check():
      return {"status": "healthy", "message": "API is running", "version": "2.0.0"}
  ```

  また、Cloud Runのバックエンドに直接アクセスした場合、CORS設定 (`ALLOWED_ORIGINS`) のみが制限となるが、CORSはブラウザの制約であり、`curl` や任意のHTTPクライアントでは無視される。

- **影響**:
  - 認証なしで生成画像にアクセス可能
  - 有効な JWT トークンがあれば、フロントエンドの特権チェック（`@shintairiku.jp` ドメインチェック）やサブスクリプションチェックをバイパス可能
  - APIのバージョン情報やエンドポイント構造が露出

- **修正チェックリスト**:
  - [ ] **Cloud Run にIAM認証を設定**: Cloud Run サービスを「認証が必要」に変更し、フロントエンド（Next.js）のサービスアカウントのみにinvoker権限を付与する。もしくは Cloud Run の前段に API Gateway / Cloud Load Balancer + IAP を配置する
  - [ ] **代替策: バックエンドに独自のAPIキー認証を追加**: フロントエンドのプロキシが固定のAPIキーをヘッダーに付与し、バックエンドのミドルウェアで検証する
  - [ ] `/images/serve/{image_filename}` エンドポイントに認証チェックを追加する
  - [ ] FastAPI の `docs` / `redoc` エンドポイントを本番環境では無効化する（`app = FastAPI(docs_url=None, redoc_url=None)` を `DEBUG=false` 時に適用）

- **参考**: [OWASP API Security Top 10 - API2:2023 Broken Authentication](https://owasp.org/API-Security/editions/2023/en/0xa2-broken-authentication/)

---

### CRIT-02: Supabase RLSポリシーの全面削除

- **場所**: `shared/supabase/migrations/20260130000003_fix_org_clerk_compat.sql`
- **CWE**: CWE-862 (Missing Authorization)
- **CVSS**: 9.1 (Critical)

- **説明**:
  Clerk 移行時に `auth.uid()` に依存していたRLSポリシーがすべて削除された。削除されたポリシーは以下のテーブルに及ぶ:

  ```sql
  -- 20260130000003_fix_org_clerk_compat.sql より抜粋
  DROP POLICY IF EXISTS "Organization owners can manage their organizations" ON organizations;
  DROP POLICY IF EXISTS "Organization members can view their organizations" ON organizations;
  DROP POLICY IF EXISTS "Organization owners and admins can manage members" ON organization_members;
  DROP POLICY IF EXISTS "Members can view organization memberships" ON organization_members;
  DROP POLICY IF EXISTS "Users can manage their own generation processes" ON generated_articles_state;
  DROP POLICY IF EXISTS "Users can manage their own articles" ON articles;
  -- ... 他多数（合計20以上のポリシー）
  ```

  RLSは有効（`ENABLE ROW LEVEL SECURITY`）のままだが、**ポリシーが存在しない**。

  バックエンドは `supabase_service_role_key` を使用しているため、RLSはバイパスされ実質影響しないが、以下のリスクがある:
  1. フロントエンドの Supabase クライアント（anon key使用）が Realtime サブスクリプションでデータを取得する際、ポリシーがないため**全データへのアクセスが拒否される**（意図しない動作）
  2. 万が一 anon key がクライアントに露出した場合（`NEXT_PUBLIC_SUPABASE_ANON_KEY` はクライアントに送信される）、RLSポリシーがないためデータへの直接アクセスが不可能になるが、**新しいポリシーを定義せず「全て拒否」の状態を放置するのは防御の不備**である
  3. バックエンドの認証ロジックにバグがあった場合、RLSという第二の防衛ラインが機能しない

- **影響**:
  - データベースの多層防御が崩壊している
  - バックエンドの認証バイパスが即座にデータ漏洩に繋がる

- **修正チェックリスト**:
  - [ ] Clerk JWT の `sub` クレームを使用する新しい RLS ポリシーを全テーブルに作成する。Supabase の `request.jwt.claims` を使って Clerk トークンからユーザーIDを取得する方式に移行する
  - [ ] 新マイグレーションファイルを作成し、以下のテーブルに最低限のポリシーを追加:
    - `organizations`: メンバーのみ参照可能
    - `organization_members`: 自身のメンバーシップのみ参照可能
    - `articles`: 自身の記事のみ参照/更新可能
    - `generated_articles_state`: 自身のプロセスのみ参照/更新可能
    - `wordpress_sites`: 自身のサイトのみ参照可能
  - [ ] フロントエンドの Supabase Realtime サブスクリプションが正常に動作するか検証する

- **参考**: [Supabase RLS Guide](https://supabase.com/docs/guides/auth/row-level-security), [OWASP - Broken Access Control](https://owasp.org/Top10/A01_2021-Broken_Access_Control/)

---

## High（高）脆弱性

### HIGH-01: DEBUG モードによるJWT署名検証スキップ

- **場所**: `backend/app/common/auth.py` 139-146行目
- **CWE**: CWE-287 (Improper Authentication)

- **説明**:
  `DEBUG=true` 環境変数が設定されている場合、JWT署名検証が完全にスキップされる:

  ```python
  # backend/app/common/auth.py
  if DEBUG_MODE:
      logger.warning("⚠️ [AUTH] DEBUG MODE: Skipping JWT signature verification!")
      try:
          decoded = jwt.decode(token, options={"verify_signature": False})
          return decoded
  ```

  攻撃者が任意のJWTトークンを偽造し、任意のユーザーになりすますことが可能。Cloud Run の環境変数に `DEBUG=true` が設定されていた場合、本番環境で悪用される。

- **影響**: 完全な認証バイパス、任意のユーザーへのなりすまし

- **修正チェックリスト**:
  - [ ] `DEBUG_MODE` による署名検証スキップを完全に削除する。デバッグ用の検証スキップは開発環境でも使用すべきではない
  - [ ] Cloud Run のデプロイメントで `DEBUG` 環境変数が `false` に設定されていることを確認する
  - [ ] `validate_token_without_signature()` 関数も削除する（テスト用であっても本番コードに含めるべきではない）
  - [ ] CI/CD パイプラインで `DEBUG=true` が本番デプロイに含まれないことをチェックする

---

### HIGH-02: APIレート制限の欠如

- **場所**: `backend/main.py`, 全エンドポイント
- **CWE**: CWE-770 (Allocation of Resources Without Limits or Throttling)

- **説明**:
  バックエンドAPIにはグローバルなレート制限が一切実装されていない。特に以下のエンドポイントが危険:
  - `POST /blog/generation/start` - AI記事生成（OpenAI API呼び出し、高コスト）
  - `POST /articles/generation/start` - SEO記事生成（同上）
  - `POST /images/generate` - 画像生成（Vertex AI呼び出し、高コスト）
  - `POST /blog/ai-questions` - AI質問生成

  使用量制限（`usage_service.check_can_generate`）は月間の記事数上限のみで、**1分あたりのリクエスト数**を制限していない。

- **影響**:
  - APIの過負荷によるサービス拒否（DoS）
  - AI API呼び出しによる莫大なコスト発生（OpenAI/Vertex AI の請求）
  - 正当なユーザーのサービス品質低下

- **修正チェックリスト**:
  - [ ] `slowapi` または FastAPI の依存ライブラリを使ってグローバルレート制限を追加する
  - [ ] AI生成エンドポイントには厳格なレート制限を設定する（例: ユーザーあたり 5 req/min）
  - [ ] 認証なしのエンドポイント（`/health`, `/images/serve/*`）にはIPベースのレート制限を設定する
  - [ ] Cloud Run のサービス設定で最大同時リクエスト数を適切に設定する

---

### HIGH-03: フロントエンドプロキシのオープンリレー

- **場所**: `frontend/src/app/api/proxy/[...path]/route.ts`
- **CWE**: CWE-918 (Server-Side Request Forgery - SSRF)

- **説明**:
  フロントエンドのAPIプロキシは、パスを結合してバックエンドに転送するが、パスの検証やホワイトリストチェックが行われていない:

  ```typescript
  // frontend/src/app/api/proxy/[...path]/route.ts
  const url = `${API_BASE_URL}/${pathString}${searchParams ? `?${searchParams}` : ''}`;
  const response = await fetchWithRedirect(url, { method: 'GET', headers });
  ```

  `API_BASE_URL` は環境変数で固定されているため直接的なSSRFリスクは限定的だが、以下の問題がある:
  1. **認証ヘッダーの無条件転送**: リクエストにAuthorizationヘッダーがあれば、そのままバックエンドに転送される。プロキシ自体には認証チェックがない
  2. **CORS ヘッダー `Access-Control-Allow-Origin: *`**: プロキシのレスポンスに `*` が設定されており、任意のオリジンからプロキシ経由でバックエンドにアクセス可能

  ```typescript
  headers: {
      'Access-Control-Allow-Origin': '*',  // 危険
  }
  ```

- **影響**:
  - 任意のWebサイトからプロキシ経由でバックエンドAPIにアクセス可能
  - 認証トークンがあれば、悪意のあるサイトからユーザーの操作を代行可能

- **修正チェックリスト**:
  - [ ] プロキシのレスポンスから `Access-Control-Allow-Origin: *` を削除する。Next.js のフロントエンド自体がオリジンなので、クロスオリジンヘッダーは不要
  - [ ] プロキシにClerk認証チェック（`auth()` の呼び出し）を追加し、認証されたリクエストのみ転送する
  - [ ] 転送先パスのホワイトリスト（許可するAPIプレフィックスのリスト）を実装する

---

### HIGH-04: セキュリティヘッダーの欠如

- **場所**: `backend/main.py`, `frontend/next.config.js`
- **CWE**: CWE-693 (Protection Mechanism Failure)

- **説明**:
  バックエンド・フロントエンド共に、以下のセキュリティヘッダーが設定されていない:
  - `Strict-Transport-Security` (HSTS)
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `Content-Security-Policy`
  - `Referrer-Policy`
  - `Permissions-Policy`

- **影響**: クリックジャッキング、MIMEスニッフィング、HTTPSダウングレード攻撃のリスク

- **修正チェックリスト**:
  - [ ] `next.config.js` に `headers()` 関数を追加し、セキュリティヘッダーを設定する:
    ```javascript
    async headers() {
      return [{
        source: '/(.*)',
        headers: [
          { key: 'X-Frame-Options', value: 'DENY' },
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
          { key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=()' },
          { key: 'Strict-Transport-Security', value: 'max-age=63072000; includeSubDomains; preload' },
        ],
      }];
    }
    ```
  - [ ] バックエンドにも `starlette.middleware` でセキュリティヘッダーを追加する

---

### HIGH-05: XSS脆弱性 - dangerouslySetInnerHTML の多用

- **場所**: 以下のフロントエンドファイル（合計19箇所以上）
  - `frontend/src/features/tools/seo/generate/edit-article/EditArticlePage.tsx` (5箇所)
  - `frontend/src/features/tools/seo/generate/new-article/component/CompactGenerationFlow.tsx` (4箇所)
  - `frontend/src/features/tools/seo/generate/new-article/component/CompletedArticleView.tsx` (1箇所)
  - `frontend/src/features/tools/seo/generate/new-article/component/ContentGeneration.tsx` (1箇所)
  - `frontend/src/features/tools/seo/manage/list/display/indexPage.tsx` (1箇所)
  - `frontend/src/features/tools/seo/generate/edit-article/components/UnifiedDiffViewer.tsx` (3箇所)
  - `frontend/src/components/article-generation/enhanced-article-generation.tsx` (1箇所)
- **CWE**: CWE-79 (Cross-Site Scripting)

- **説明**:
  AI生成コンテンツ（HTMLを含む記事本文）が `dangerouslySetInnerHTML` でサニタイズなしにレンダリングされている:

  ```tsx
  // frontend/src/features/tools/seo/generate/edit-article/EditArticlePage.tsx:1515
  dangerouslySetInnerHTML={{ __html: block.content }}

  // frontend/src/features/tools/seo/manage/list/display/indexPage.tsx:473
  dangerouslySetInnerHTML={{ __html: selectedArticle.content }}
  ```

  AI生成コンテンツは信頼できるソースとはいえ、以下のリスクがある:
  1. AIモデルのプロンプトインジェクションにより悪意のあるスクリプトが生成される可能性
  2. 外部参考URL（`reference_url`）からスクレイピングしたコンテンツにXSSペイロードが含まれる可能性
  3. ユーザーが記事を編集する際にスクリプトを挿入する可能性

- **影響**: Stored XSS、セッションハイジャック、クレデンシャル窃取

- **修正チェックリスト**:
  - [ ] `DOMPurify` ライブラリを導入し、`dangerouslySetInnerHTML` に渡す前に全てのHTMLをサニタイズする
  - [ ] バックエンド側でも記事保存時にHTMLサニタイズを実行する（許可タグのホワイトリスト方式）
  - [ ] `Content-Security-Policy` ヘッダーで `script-src 'self'` を設定し、インラインスクリプトの実行を防ぐ

---

### HIGH-06: バックエンドが全てservice_roleキーでDBアクセス

- **場所**: `backend/app/common/database.py` 12行目
- **CWE**: CWE-250 (Execution with Unnecessary Privileges)

- **説明**:
  バックエンドの全てのDB操作が `supabase_service_role_key` を使用しており、RLSを完全にバイパスしている:

  ```python
  # backend/app/common/database.py
  def create_supabase_client() -> Client:
      supabase_client = create_client(
          settings.supabase_url,
          settings.supabase_service_role_key  # RLSバイパス
      )
      return supabase_client
  ```

  CRIT-02 と組み合わせると、バックエンドの認証ロジックの一箇所でもバグがあれば、全テーブルの全データにアクセスできる。

- **影響**: 認証バイパス時のデータ漏洩範囲が最大化される

- **修正チェックリスト**:
  - [ ] 読み取り操作には anon key + RLSポリシーを使用するSupabaseクライアントを作成し、認証済みユーザーのJWTトークンを設定する
  - [ ] service_role キーの使用は Webhook処理やバックグラウンドタスクなど、ユーザーコンテキストがない処理に限定する
  - [ ] 各エンドポイントで `user_id` によるフィルタリングが確実に行われていることをユニットテストで検証する

---

### HIGH-07: Stripe Webhook シークレット未設定時の処理続行

- **場所**: `frontend/src/app/api/subscription/webhook/route.ts` 52-58行目
- **CWE**: CWE-347 (Improper Verification of Cryptographic Signature)

- **説明**:
  Webhook シークレットが未設定の場合、エラーレスポンスは返されるが、`webhookSecret` の存在チェックは条件付きで行われている。シークレットが空文字列 (`""`) の場合、`constructEvent` が呼ばれる可能性がある:

  ```typescript
  const webhookSecret = process.env.STRIPE_WEBHOOK_SECRET;
  // webhookSecret が undefined ならバリデーションされるが、
  // "" (空文字) の場合の動作が Stripe SDK のバージョンに依存する
  ```

  更に、Webhook の重複チェックが `subscription_events` テーブルに依存しているが、初回のイベントは検証なしに処理される可能性がある。

- **修正チェックリスト**:
  - [ ] `!webhookSecret` を `!webhookSecret || webhookSecret.trim() === ''` に変更する
  - [ ] アプリケーション起動時に `STRIPE_WEBHOOK_SECRET` の存在を検証し、未設定なら起動を拒否する
  - [ ] Webhook エンドポイントのIP制限を検討する（Stripe の [IP アドレスリスト](https://docs.stripe.com/ips)）

---

## Medium（中）脆弱性

### MED-01: 機密情報を含むエラーメッセージの露出

- **場所**: 複数ファイル（以下は代表例）
  - `backend/app/domains/image_generation/endpoints.py` 276, 379, 507, 538行目
  - `backend/app/core/exceptions.py` 20-23行目
  - `backend/app/common/auth.py` 180行目
- **CWE**: CWE-209 (Generation of Error Message Containing Sensitive Information)

- **説明**:
  例外の内容がそのままHTTPレスポンスに含まれている:

  ```python
  # backend/app/domains/image_generation/endpoints.py
  raise HTTPException(status_code=500, detail=f"予期せぬエラーが発生しました: {str(e)}")
  raise HTTPException(status_code=500, detail=f"画像置き換えに失敗しました: {str(e)}")
  ```

  ```python
  # backend/app/core/exceptions.py
  content={"detail": f"An unexpected internal server error occurred: {type(exc).__name__}"},
  ```

  ```python
  # backend/app/common/auth.py
  raise HTTPException(status_code=500, detail=f"Authentication error: {e}")
  ```

  例外メッセージにはファイルパス、DB接続情報、内部実装の詳細が含まれる可能性がある。

- **修正チェックリスト**:
  - [ ] 本番環境では内部エラーの詳細をレスポンスに含めない。`DEBUG=false` 時は汎用メッセージのみ返す
  - [ ] `generic_exception_handler` を修正し、本番環境では `type(exc).__name__` をレスポンスに含めない
  - [ ] エラーの詳細はサーバーサイドのログにのみ記録する

---

### MED-02: CORS設定の不備

- **場所**: `backend/main.py` 23-33行目
- **CWE**: CWE-942 (Permissive Cross-domain Policy)

- **説明**:
  CORS設定で `allow_headers=["*"]` が使用されており、`allow_credentials=True` と組み合わされている:

  ```python
  app.add_middleware(
      CORSMiddleware,
      allow_origins=allowed_origins,
      allow_credentials=True,
      allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
      allow_headers=["*"],  # 全ヘッダーを許可
  )
  ```

  `allow_credentials=True` と `allow_origins=["*"]` の組み合わせはブラウザにブロックされるが、`ALLOWED_ORIGINS` が適切に設定されていない場合（デフォルト値 `http://localhost:3000`）、本番環境で意図しないオリジンからのアクセスを許可する可能性がある。

- **修正チェックリスト**:
  - [ ] `allow_headers` を必要なヘッダーのみに限定する（`["Content-Type", "Authorization"]`）
  - [ ] 本番環境の `ALLOWED_ORIGINS` に正確な本番ドメインのみが設定されていることを確認する
  - [ ] `ALLOWED_ORIGINS` のデフォルト値を空にし、未設定時はCORSを拒否する

---

### MED-03: ファイルアップロードの不十分な検証

- **場所**:
  - `backend/app/domains/blog/endpoints.py` (upload_image, start_blog_generation)
  - `backend/app/domains/image_generation/endpoints.py` (upload_image)
  - `backend/app/domains/blog/services/image_utils.py`
- **CWE**: CWE-434 (Unrestricted Upload of File with Dangerous Type)

- **説明**:
  画像アップロード処理で以下の検証が不足:

  ```python
  # backend/app/domains/blog/endpoints.py - start_blog_generation
  files: List[UploadFile] = File(default=[], description="記事に含めたい画像（最大5枚）")
  # ファイルサイズの制限がない
  # Content-Type の検証がない
  # マジックバイトの検証がない
  ```

  `image_utils.py` の `convert_and_save_as_webp` は Pillow で画像を開くが、Pillow は悪意のある画像ファイルによるDoS攻撃（画像爆弾/decompression bomb）に脆弱な場合がある:

  ```python
  # backend/app/domains/blog/services/image_utils.py
  img = Image.open(io.BytesIO(image_bytes))
  # Pillow の MAX_IMAGE_PIXELS はデフォルトで ~178M ピクセルだが、
  # メモリ消費は依然として大きい
  ```

- **修正チェックリスト**:
  - [ ] ファイルサイズの上限を設定する（例: 10MB）
  - [ ] Content-Type を画像フォーマットのみに制限する（`image/jpeg`, `image/png`, `image/webp`, `image/gif`）
  - [ ] Pillow の `Image.MAX_IMAGE_PIXELS` を明示的に設定する
  - [ ] ファイル名のサニタイズを強化する（パストラバーサル文字の除去）

---

### MED-04: APIキーのログ出力

- **場所**: `backend/app/core/config.py` 133行目
- **CWE**: CWE-532 (Insertion of Sensitive Information into Log File)

- **説明**:
  OpenAI APIキーの最初の8文字がログに出力されている:

  ```python
  # backend/app/core/config.py
  print(f"OpenAI API キーを設定しました: {settings.openai_api_key[:8]}...")
  ```

  また、JWT検証時にトークンの長さやクレーム内容がINFOレベルでログに記録されている:

  ```python
  # backend/app/common/auth.py
  logger.info(f"🔒 [AUTH] Processing JWT token, length: {len(token)}")
  logger.info(f"🔒 [AUTH] JWT claims: iss={decoded.get('iss')}, azp={decoded.get('azp')}, exp={decoded.get('exp')}")
  ```

- **修正チェックリスト**:
  - [ ] APIキーの部分出力をログから削除する
  - [ ] JWT クレームのログレベルを `DEBUG` に変更する
  - [ ] 本番環境でのログレベルを `WARNING` 以上に設定する

---

### MED-05: 依存パッケージのバージョン固定なし

- **場所**: `backend/pyproject.toml`
- **CWE**: CWE-1104 (Use of Unmaintained Third Party Components)

- **説明**:
  バックエンドの全依存パッケージがバージョン制約なし（ピンなし）で指定されている:

  ```toml
  dependencies = [
      "fastapi",       # バージョン指定なし
      "openai",        # バージョン指定なし
      "supabase",      # バージョン指定なし
      "pyjwt",         # バージョン指定なし
      # ...
  ]
  ```

  `uv.lock` で固定されるが、`uv sync` 実行時に意図しないメジャーアップデートが適用される可能性がある。

- **修正チェックリスト**:
  - [ ] 最低限メジャーバージョンを固定する（例: `"fastapi>=0.128,<1.0"`）
  - [ ] セキュリティに重要なパッケージ（`pyjwt`, `cryptography`）は特に慎重にバージョン管理する
  - [ ] `uv.lock` をGitにコミットし、CI/CDで `--frozen` フラグを使用する
  - [ ] 定期的に `pip-audit` や `safety` で脆弱性スキャンを実行する

---

### MED-06: Docker コンテナの非rootユーザー未使用

- **場所**: `backend/Dockerfile`
- **CWE**: CWE-250 (Execution with Unnecessary Privileges)

- **説明**:
  Dockerfileでrootユーザーのまま実行されている:

  ```dockerfile
  FROM python:3.12-slim
  WORKDIR /app
  COPY . .
  CMD ["sh", "-c", "uv run uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
  # USER ディレクティブがない = rootで実行
  ```

- **修正チェックリスト**:
  - [ ] `Dockerfile` にnonrootユーザーを追加する:
    ```dockerfile
    RUN groupadd -r appuser && useradd -r -g appuser appuser
    USER appuser
    ```
  - [ ] `/tmp/blog_uploads` や画像保存ディレクトリの書き込み権限を `appuser` に設定する

---

### MED-07: Supabase Service Role キーのフロントエンド配置

- **場所**: `frontend/src/libs/supabase/supabase-admin.ts`
- **CWE**: CWE-798 (Use of Hard-coded Credentials)

- **説明**:
  `SUPABASE_SERVICE_ROLE_KEY` がフロントエンドのNext.jsサーバーサイドコードで使用されている:

  ```typescript
  // frontend/src/libs/supabase/supabase-admin.ts
  export const supabaseAdminClient = createClient<Database>(
    getEnvVar(process.env.NEXT_PUBLIC_SUPABASE_URL, 'NEXT_PUBLIC_SUPABASE_URL'),
    getEnvVar(process.env.SUPABASE_SERVICE_ROLE_KEY, 'SUPABASE_SERVICE_ROLE_KEY')
  );
  ```

  このキーは `NEXT_PUBLIC_` プレフィックスがないためクライアントには送信されないが、Next.js のサーバーサイドコード全体（API Routes, Server Components, middleware）からアクセス可能。Service Role キーが漏洩した場合、RLSバイパスで全データにアクセスできる。

- **修正チェックリスト**:
  - [ ] フロントエンドでの `service_role_key` 使用を最小限に抑え、必要な処理をバックエンドに移動することを検討する
  - [ ] 環境変数の名前を `SUPABASE_SERVICE_ROLE_KEY` から `__INTERNAL_SUPABASE_SERVICE_ROLE_KEY` 等に変更し、誤用を防ぐ
  - [ ] 最低限、Webhook ハンドラーと subscription status API のみで使用するように制限する

---

### MED-08: docker-compose.yml でのシークレット露出リスク

- **場所**: `docker-compose.yml` 26-29行目
- **CWE**: CWE-312 (Cleartext Storage of Sensitive Information)

- **説明**:
  `docker-compose.yml` のビルド引数に機密情報が含まれている:

  ```yaml
  frontend_prod:
    build:
      args:
        STRIPE_SECRET_KEY: ${STRIPE_SECRET_KEY}
        SUPABASE_SERVICE_ROLE_KEY: ${SUPABASE_SERVICE_ROLE_KEY}
  ```

  これらの値はDockerイメージのビルドレイヤーに含まれ、`docker history` で確認可能。

- **修正チェックリスト**:
  - [ ] ビルド引数ではなく、ランタイムの環境変数としてのみ渡す
  - [ ] Docker の `--secret` 機能を使用する
  - [ ] `.env` ファイルが `.gitignore` に含まれていることを確認する（確認済み: 含まれている）

---

## Low（低）脆弱性

### LOW-01: 画像配信エンドポイントのパストラバーサル対策の不完全性

- **場所**: `backend/app/domains/image_generation/endpoints.py` (`serve_image`)
- **CWE**: CWE-22 (Path Traversal)

- **説明**:
  パストラバーサル対策は実装されているが、`resolve()` による正規化のみに依存している:

  ```python
  image_path = storage_path / image_filename
  if not str(image_path.resolve()).startswith(str(storage_path.resolve())):
      raise HTTPException(status_code=400, detail="Invalid file path")
  ```

  シンボリックリンクを使った攻撃には脆弱な可能性がある。また、認証チェックがないため（CRIT-01に関連）、URLの推測で画像にアクセス可能。

- **修正チェックリスト**:
  - [ ] `image_filename` に `..` や `/` が含まれていないことを正規表現でチェックする
  - [ ] 認証チェックを追加する
  - [ ] ファイル名をUUIDベースに統一し、元のファイル名を推測不可能にする

---

### LOW-02: JWT の `issuer` 検証の欠如

- **場所**: `backend/app/common/auth.py` 155-166行目
- **CWE**: CWE-345 (Insufficient Verification of Data Authenticity)

- **説明**:
  JWT検証時に `issuer` (iss) と `audience` (aud/azp) の検証が行われていない:

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
          # issuer, audience の検証がない
      }
  )
  ```

- **修正チェックリスト**:
  - [ ] `options` に `"verify_iss": True` を追加し、`issuer` パラメータにClerkのissuer URLを設定する
  - [ ] `audience` (azp) の検証も追加する

---

### LOW-03: CI/CDパイプラインでのセキュリティスキャン欠如

- **場所**: `.github/workflows/backend-docker-build.yml`
- **CWE**: CWE-1395 (Dependency on Vulnerable Third-Party Component)

- **説明**:
  CI/CDパイプラインにはDockerビルドテストのみが含まれ、以下が欠如:
  - 依存パッケージの脆弱性スキャン
  - SAST（静的アプリケーションセキュリティテスト）
  - Dockerイメージのセキュリティスキャン
  - シークレットの検出

- **修正チェックリスト**:
  - [ ] `pip-audit` / `safety` によるPython依存パッケージスキャンをCIに追加する
  - [ ] `npm audit` / `bun audit` によるフロントエンド依存パッケージスキャンを追加する
  - [ ] `trivy` によるDockerイメージスキャンを追加する
  - [ ] `gitleaks` によるシークレット検出を追加する

---

### LOW-04: `cryptography` ライブラリの間接依存

- **場所**: `backend/pyproject.toml` (間接依存)
- **CWE**: CWE-327 (Use of a Broken or Risky Cryptographic Algorithm)

- **説明**:
  WordPress認証情報の暗号化に `cryptography` ライブラリの AES-256-GCM が使用されているが、`pyproject.toml` に直接の依存として明記されていない。間接依存としてインストールされるため、バージョン管理が不十分。

- **修正チェックリスト**:
  - [ ] `cryptography` を `pyproject.toml` の明示的な依存に追加する
  - [ ] バージョンを固定し、既知の脆弱性がないことを確認する

---

### LOW-05: 管理者認証でのClerk APIへの毎回のアクセス

- **場所**: `backend/app/common/admin_auth.py`
- **CWE**: CWE-400 (Uncontrolled Resource Consumption)

- **説明**:
  管理者認証チェックのたびにClerk APIにHTTPリクエストが発生する。キャッシュが実装されていないため、管理者ダッシュボードのページロード時に複数のAPI呼び出しが発生し、レイテンシ増加とClerk API レート制限のリスクがある。

- **修正チェックリスト**:
  - [ ] Clerk JWTのカスタムクレームにメールアドレスを含めるようClerkダッシュボードで設定する
  - [ ] メールアドレスのキャッシュ（TTL付き）を実装する
  - [ ] フォールバックとしてDB（`user_subscriptions.email`）からメールを取得する

---

## セキュリティ全般の推奨事項

- [ ] **セキュリティテストの自動化**: OWASP ZAP やBurp Suite によるDAST（動的テスト）を定期的に実行する
- [ ] **ログの集約と監視**: Cloud Logging / Cloud Monitoring で不正アクセスパターンを検出するアラートを設定する
- [ ] **インシデント対応計画**: セキュリティインシデント発生時の連絡先、対応手順、エスカレーションパスを文書化する
- [ ] **定期的な依存パッケージ更新**: Dependabot / Renovate を導入し、セキュリティパッチを自動的に適用する
- [ ] **ペネトレーションテスト**: 本番デプロイ前に第三者によるペネトレーションテストを実施する
- [ ] **バックアップと暗号化**: Supabase のバックアップが暗号化されていることを確認する
- [ ] **アクセスログの保持**: 全APIエンドポイントのアクセスログを最低90日間保持する

---

## セキュリティ態勢改善計画（優先順位順）

| 優先度 | 対策 | 予想工数 | 影響 |
|--------|------|----------|------|
| 1 | Cloud Run のIAM認証設定 (CRIT-01) | 2-4時間 | バックエンドへの直接アクセスを遮断 |
| 2 | RLSポリシーの再構築 (CRIT-02) | 8-16時間 | データベースの多層防御を復活 |
| 3 | DEBUG モードの署名スキップ削除 (HIGH-01) | 30分 | 認証バイパスリスクを排除 |
| 4 | レート制限の実装 (HIGH-02) | 4-8時間 | DoS/コスト攻撃を防止 |
| 5 | セキュリティヘッダーの追加 (HIGH-04) | 1-2時間 | 基本的なブラウザセキュリティを強化 |
| 6 | XSSサニタイズの実装 (HIGH-05) | 4-8時間 | Stored XSSを防止 |
| 7 | フロントエンドプロキシの修正 (HIGH-03) | 2-4時間 | CORS/認証バイパスを防止 |
| 8 | エラーメッセージの修正 (MED-01) | 2-4時間 | 情報漏洩を防止 |
| 9 | CI/CDセキュリティスキャン追加 (LOW-03) | 2-4時間 | 継続的なセキュリティ監視 |
| 10 | その他のMedium/Low修正 | 8-16時間 | 全体的なセキュリティ態勢強化 |

---

*本レポートは自動セキュリティ監査ツールによる静的コード分析に基づいています。実行時のテストや侵入テストは含まれていません。*
