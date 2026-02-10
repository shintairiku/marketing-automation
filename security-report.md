# セキュリティ監査レポート

**対象**: BlogAI / Marketing Automation Platform
**監査日**: 2026-02-10
**監査範囲**: バックエンド (FastAPI/Python), フロントエンド (Next.js 15/TypeScript), データベース (Supabase/PostgreSQL), インフラ (Docker, Cloud Run, Vercel)
**監査者**: Claude Opus 4.6 (自動セキュリティ監査)

---

## エグゼクティブサマリー

本プラットフォームは、Clerk JWT認証、AES-256-GCM暗号化、Cloud Run IAM認証など、多くのセキュリティ対策が既に実装されている。しかし、監査の結果、**Critical 2件、High 7件、Medium 9件、Low 6件**の脆弱性が発見された。

最も深刻な問題は以下の通り:
1. **RLSポリシーの大量削除** -- 多数のテーブルでRow Level Securityが無効化されており、service_role keyの漏洩時にデータベース全体が露出する
2. **認証なしの画像配信エンドポイント** -- `/images/serve/{filename}` に認証が不要で、生成画像が公開状態
3. **APIレート制限の欠如** -- 全エンドポイントにレート制限がなく、DoS攻撃やリソース枯渇に脆弱
4. **セキュリティヘッダーの未設定** -- CSP, HSTS, X-Frame-Options等のHTTPセキュリティヘッダーが皆無

全体的なリスク評価: **中〜高**

---

## Critical (重大) 脆弱性

### C-1: RLSポリシーの大量削除によるデータベース保護の喪失

- **場所**: `/home/als0028/study/shintairiku/marketing-automation/shared/supabase/migrations/20260130000003_fix_org_clerk_compat.sql`
- **説明**: Clerk IDとauth.uid()の型不一致を解決するため、organizations, organization_members, invitations, organization_subscriptions, generated_articles_state, articles, article_generation_flows, flow_steps, style_guide_templates, images, agent_log_sessions等、**15テーブル以上のRLSポリシーが削除**されている。RLS自体は有効だが、ポリシーが存在しないため、`service_role` key以外からの全アクセスがデフォルトで拒否される。問題は`service_role` keyが漏洩した場合、テーブル全体のデータが認可チェックなしで直接操作可能になる点。さらにフロントエンドでも`supabaseAdminClient`が`SUPABASE_SERVICE_ROLE_KEY`を使用しており、このキーの漏洩は壊滅的な影響を持つ。
- **影響**: Supabase service_role keyの漏洩時に全ユーザーデータ(記事、組織、サブスクリプション、WordPress認証情報を含む)が完全に露出。RLSポリシーによる二重防御が機能しない。
- **対処チェックリスト**:
  - [ ] Clerk IDベースの新しいRLSポリシーを設計・実装する。`auth.uid()`ではなく、カスタムJWT claimまたは`current_setting('request.jwt.claims')`でClerk user_idを取得する方式を検討
  - [ ] 最低限、`service_role`以外のアクセス（`anon` key経由）に対してデータを保護するRLSポリシーを全テーブルに追加
  - [ ] フロントエンドでの`supabaseAdminClient`（service_role key）の使用箇所を最小限に限定し、可能な限りバックエンドAPI経由に移行
  - [ ] `usage_tracking`, `usage_logs`テーブルの`FOR ALL USING (true)`ポリシーを、適切なuser_id/organization_idベースのポリシーに置換
- **参考**: [Supabase RLS with custom JWT](https://supabase.com/docs/guides/auth/row-level-security), [CWE-862: Missing Authorization](https://cwe.mitre.org/data/definitions/862.html)

### C-2: 署名検証なしトークンデコード関数のプロダクションコード残存

- **場所**: `/home/als0028/study/shintairiku/marketing-automation/backend/app/common/auth.py` (297-304行目)
- **説明**: `validate_token_without_signature()` 関数が本番コードに残存している。現時点で他のコードから呼び出されてはいないが、この関数は署名検証をバイパスしてJWTをデコードするため、誤って使用されると任意のJWTを受け入れてしまう。
  ```python
  def validate_token_without_signature(token: str) -> dict:
      """署名検証なしでトークンをデコード（デバッグ・テスト用）"""
      logger.warning("validate_token_without_signature called - FOR TESTING ONLY")
      return jwt.decode(token, options={"verify_signature": False})
  ```
- **影響**: 開発者が誤ってこの関数を使用した場合、認証バイパスが発生し、任意のユーザーになりすまし可能
- **対処チェックリスト**:
  - [ ] `validate_token_without_signature` 関数を本番コードから完全に削除する
  - [ ] テスト用にこの関数が必要であれば、テストファイル内にのみ定義する
- **参考**: [CWE-345: Insufficient Verification of Data Authenticity](https://cwe.mitre.org/data/definitions/345.html)

---

## High (高) 脆弱性

### H-1: 全APIエンドポイントにレート制限がない

- **場所**: `/home/als0028/study/shintairiku/marketing-automation/backend/main.py` 全体
- **説明**: FastAPIアプリケーションにレート制限ミドルウェアが一切実装されていない。AI記事生成 (`/articles/generation/start`, `/blog/generation/start`)、画像生成 (`/images/generate`)、認証チェック等の高コストなエンドポイントを含む全エンドポイントが無制限に呼び出し可能。
- **影響**: DoS攻撃によるサービス停止、OpenAI/Vertex AI APIコストの爆発的増加、ブルートフォース攻撃
- **対処チェックリスト**:
  - [ ] `slowapi` または同等のレート制限ライブラリを導入する
    ```python
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address

    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    app.add_exception_handler(429, _rate_limit_exceeded_handler)

    # AI生成エンドポイントに厳しい制限を適用
    @router.post("/generation/start")
    @limiter.limit("5/minute")
    async def start_generation(...):
    ```
  - [ ] エンドポイントの種類に応じた段階的レート制限を設定（例: 認証系 10回/分, AI生成系 5回/分, 読み取り系 60回/分）
  - [ ] ユーザーIDベースのレート制限も検討（IPベースだけでは不十分）
- **参考**: [OWASP API4:2023 Unrestricted Resource Consumption](https://owasp.org/API-Security/editions/2023/en/0xa4-unrestricted-resource-consumption/)

### H-2: HTTPセキュリティヘッダーの完全な欠如

- **場所**: `/home/als0028/study/shintairiku/marketing-automation/frontend/next.config.js`
- **説明**: Next.jsの設定にセキュリティヘッダーが一切定義されていない。Content-Security-Policy (CSP)、Strict-Transport-Security (HSTS)、X-Frame-Options、X-Content-Type-Options、Referrer-Policy、Permissions-Policy のいずれも設定されていない。
- **影響**: クリックジャッキング攻撃、MIMEタイプスニッフィング、外部リソースインジェクション、SSL Stripping攻撃への脆弱性
- **対処チェックリスト**:
  - [ ] `next.config.js` に以下のセキュリティヘッダーを追加:
    ```javascript
    const nextConfig = {
      async headers() {
        return [
          {
            source: '/(.*)',
            headers: [
              { key: 'X-Frame-Options', value: 'DENY' },
              { key: 'X-Content-Type-Options', value: 'nosniff' },
              { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
              { key: 'X-XSS-Protection', value: '1; mode=block' },
              { key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=()' },
              {
                key: 'Strict-Transport-Security',
                value: 'max-age=63072000; includeSubDomains; preload'
              },
              {
                key: 'Content-Security-Policy',
                value: "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' https://js.stripe.com https://*.clerk.accounts.dev; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: blob: https://storage.googleapis.com https://images.unsplash.com https://*.clerk.accounts.dev; connect-src 'self' https://*.supabase.co wss://*.supabase.co https://api.stripe.com https://*.clerk.accounts.dev https://*.run.app; frame-src https://js.stripe.com https://*.clerk.accounts.dev;"
              },
            ],
          },
        ];
      },
      // ... 既存の設定
    };
    ```
- **参考**: [OWASP Secure Headers Project](https://owasp.org/www-project-secure-headers/)

### H-3: 認証なしの画像配信エンドポイント

- **場所**: `/home/als0028/study/shintairiku/marketing-automation/backend/app/domains/image_generation/endpoints.py` (487-517行目)
- **説明**: `GET /images/serve/{image_filename}` エンドポイントに認証が設定されていない。ファイル名を知っていれば誰でもアクセス可能。UUIDベースのファイル名は推測困難だが、URLが共有された場合やログに記録された場合にアクセス可能。
  ```python
  @router.get("/serve/{image_filename}")
  async def serve_image(image_filename: str):
      # 認証チェックなし
  ```
- **影響**: 生成された画像（ビジネス情報を含む可能性あり）への不正アクセス
- **対処チェックリスト**:
  - [ ] `Depends(get_current_user_id_from_token)` を追加し、画像の所有者チェックを実装
  - [ ] GCS経由で配信する場合は、署名付きURLを使用して時間制限付きアクセスにする
  - [ ] あるいは、このエンドポイントが公開配信用途であれば、その旨をドキュメント化し、機密画像が格納されないことを保証する
- **参考**: [CWE-306: Missing Authentication for Critical Function](https://cwe.mitre.org/data/definitions/306.html)

### H-4: SSRF (Server-Side Request Forgery) リスク -- WordPress接続URL

- **場所**: `/home/als0028/study/shintairiku/marketing-automation/backend/app/domains/blog/endpoints.py` (453-636行目) `register_wordpress_site_by_url()`
- **説明**: ユーザーが入力した接続URLに対して、バックエンドが直接HTTPリクエストを送信する。URLのバリデーションが `scheme` と `netloc` の存在チェックのみで、内部ネットワークアドレス（`localhost`, `127.0.0.1`, `10.x.x.x`, `192.168.x.x`, `169.254.169.254` など）への接続を防止するチェックがない。
  ```python
  parsed = urlparse(connection_url)
  if not parsed.scheme or not parsed.netloc:
      raise HTTPException(...)
  # 内部IPアドレスのチェックなし
  register_endpoint = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
  async with httpx.AsyncClient(timeout=30.0) as client:
      register_response = await client.post(register_endpoint, ...)
  ```
- **影響**: Cloud Runメタデータサービス (`169.254.169.254`) へのアクセスによるサービスアカウントトークンの窃取、内部ネットワークのスキャン、内部サービスへの攻撃
- **対処チェックリスト**:
  - [ ] URLのホスト部分をIPアドレスに解決し、プライベートIPレンジをブロックするバリデーションを追加:
    ```python
    import ipaddress
    import socket

    def is_safe_url(url: str) -> bool:
        parsed = urlparse(url)
        hostname = parsed.hostname
        if not hostname:
            return False
        # 直接IPアドレスが指定された場合
        try:
            ip = ipaddress.ip_address(hostname)
            return ip.is_global  # プライベート/リンクローカル/ループバックを除外
        except ValueError:
            pass
        # ドメイン名の場合はDNS解決
        try:
            for info in socket.getaddrinfo(hostname, None):
                ip = ipaddress.ip_address(info[4][0])
                if not ip.is_global:
                    return False
        except socket.gaierror:
            return False
        return True
    ```
  - [ ] 許可するスキームを `https` のみに制限 (`http` は開発環境のみ)
  - [ ] DNS rebinding攻撃対策として、解決したIPアドレスでリクエストを送信する
- **参考**: [CWE-918: Server-Side Request Forgery](https://cwe.mitre.org/data/definitions/918.html), [OWASP SSRF Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html)

### H-5: プロキシルートの過度に広いCORSヘッダー

- **場所**: `/home/als0028/study/shintairiku/marketing-automation/frontend/src/app/api/proxy/[...path]/route.ts` (73行目, 228行目)
- **説明**: プロキシのレスポンスおよびOPTIONSハンドラが `Access-Control-Allow-Origin: *` を返している。これはフロントエンドのAPIプロキシであり、任意のオリジンからバックエンドAPIにアクセス可能な状態になっている。
  ```typescript
  return NextResponse.json(data, {
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, PUT, PATCH, DELETE, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    },
  });
  ```
- **影響**: 悪意あるサイトから認証付きリクエストをプロキシ経由で送信可能。ユーザーのセッションを利用したCSRF攻撃の土台となる。
- **対処チェックリスト**:
  - [ ] `Access-Control-Allow-Origin` をリクエストの `Origin` ヘッダーに基づいてホワイトリストで検証し、許可されたオリジンのみ返すように変更:
    ```typescript
    const ALLOWED_ORIGINS = [
      process.env.NEXT_PUBLIC_APP_URL,
      'http://localhost:3000',
    ].filter(Boolean);

    const origin = request.headers.get('origin');
    const corsOrigin = ALLOWED_ORIGINS.includes(origin || '') ? origin : ALLOWED_ORIGINS[0];
    ```
  - [ ] `Access-Control-Allow-Credentials: true` を設定する場合は、必ずワイルドカードを使用しない
- **参考**: [CWE-942: Permissive Cross-domain Policy](https://cwe.mitre.org/data/definitions/942.html)

### H-6: ファイルアップロードの不十分なバリデーション

- **場所**: `/home/als0028/study/shintairiku/marketing-automation/backend/app/domains/blog/endpoints.py` (912-1050行目), `/home/als0028/study/shintairiku/marketing-automation/backend/app/domains/blog/services/image_utils.py`
- **説明**: ブログ画像アップロードエンドポイントで、以下のバリデーションが不足している:
  1. **ファイルサイズの制限なし**: `file.size` のチェックがなく、巨大ファイルのアップロードによるディスク枯渇が可能
  2. **MIMEタイプ/拡張子のチェックなし**: `content_type` の検証がなく、画像以外のファイル（実行可能ファイル等）がアップロード可能
  3. **ファイル内容のマジックバイト検証なし**: `Pillow.Image.open()` が失敗時に例外が発生するが、細工された画像ファイルによるPillow脆弱性の悪用リスク
  ```python
  for file in files:
      if file.filename and file.size and file.size > 0:
          content = await file.read()  # サイズ制限なし
          local_path = convert_and_save_as_webp(content, ...)  # 内容検証なし
  ```
- **影響**: ディスクスペース枯渇によるDoS、画像処理ライブラリの脆弱性を利用したRCE (Pillowの既知のCVE)
- **対処チェックリスト**:
  - [ ] ファイルサイズ制限を追加（例: 10MB）:
    ```python
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    for file in files:
        if file.size and file.size > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail=f"ファイルサイズが上限({MAX_FILE_SIZE // (1024*1024)}MB)を超えています")
    ```
  - [ ] MIMEタイプのホワイトリストを追加:
    ```python
    ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="許可されていないファイル形式です")
    ```
  - [ ] Pillowを常に最新バージョンに維持する（現在: v12.1.0 -- 確認済み）
- **参考**: [CWE-434: Unrestricted Upload of File with Dangerous Type](https://cwe.mitre.org/data/definitions/434.html)

### H-7: APIキーのログ出力

- **場所**: `/home/als0028/study/shintairiku/marketing-automation/backend/app/core/config.py` (163行目)
- **説明**: OpenAI APIキーの先頭8文字がアプリケーション起動時にprint文で出力されている:
  ```python
  print(f"OpenAI API キーを設定しました: {settings.openai_api_key[:8]}...")
  ```
  Cloud Runのログはデフォルトで保持され、ログ閲覧権限を持つユーザーがキーの一部を確認可能。
- **影響**: APIキーの部分的な漏洩。ログ閲覧権限を持つ攻撃者がキー推測に利用可能。
- **対処チェックリスト**:
  - [ ] APIキーの内容をログに出力しない。代わりにキーの存在/不在のみをログに記録:
    ```python
    print(f"OpenAI API キーを設定しました (長さ: {len(settings.openai_api_key)}文字)")
    ```
  - [ ] 全ての `print()` 文を適切な `logging` 呼び出しに置き換え、ログレベルで制御可能にする
- **参考**: [CWE-532: Insertion of Sensitive Information into Log File](https://cwe.mitre.org/data/definitions/532.html)

---

## Medium (中) 脆弱性

### M-1: CSRF保護の欠如

- **場所**: フロントエンド全体, 特にAPIルート (`/home/als0028/study/shintairiku/marketing-automation/frontend/src/app/api/`)
- **説明**: Next.js APIルートにCSRFトークンの検証が実装されていない。Clerk認証は`Authorization`ヘッダーベースのためCookie経由のCSRFには直接影響しないが、Stripeの webhook 以外の状態変更APIルート (`checkout`, `upgrade-to-team`, `update-seats`, `addon`) はCookieベースのClerkセッション認証 (`auth()`) を使用しており、CSRF攻撃の対象となりうる。
- **影響**: 悪意あるサイトからユーザーに代わってサブスクリプション変更、アドオン購入等の操作が実行される可能性
- **対処チェックリスト**:
  - [ ] 状態変更を行うAPIルートに `Origin` または `Referer` ヘッダーの検証を追加
  - [ ] またはCSRFトークンライブラリの導入を検討（`csrf` パッケージ等）
  - [ ] `SameSite=Strict` (または `Lax`) Cookie属性の使用をClerk設定で確認
- **参考**: [OWASP CSRF Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)

### M-2: dangerouslySetInnerHTMLによるXSSリスク

- **場所**: `/home/als0028/study/shintairiku/marketing-automation/frontend/src/features/tools/seo/` 配下の複数ファイル (18箇所以上)
  - `manage/list/display/indexPage.tsx` (473行目)
  - `generate/new-article/component/ContentGeneration.tsx` (159行目)
  - `generate/new-article/component/CompletedArticleView.tsx` (214行目)
  - `generate/edit-article/EditArticlePage.tsx` (1515, 1521, 2037, 2046, 2271行目)
  - `generate/edit-article/components/UnifiedDiffViewer.tsx` (37, 89, 105行目)
- **説明**: AIが生成したHTMLコンテンツが `dangerouslySetInnerHTML` で直接レンダリングされている。AIモデルの出力にXSSペイロードが含まれる可能性がある（プロンプトインジェクション経由）。バックエンドには `sanitize_dom()` と `enhanced_sanitize_dom()` 関数が存在するが、全出力パスでサニタイゼーションが適用されているか不明。
- **影響**: 保存型XSS攻撃、ユーザーのセッショントークン窃取、アカウント乗っ取り
- **対処チェックリスト**:
  - [ ] `rehype-sanitize` (既にフロントエンド依存にある) を使用して、全てのHTML出力をサニタイズしてからレンダリングする
  - [ ] バックエンドの `sanitize_dom()` がAI生成コンテンツの全出力パスで適用されていることを確認
  - [ ] `dangerouslySetInnerHTML` の使用箇所を一覧化し、各箇所でサニタイゼーションが行われていることを検証するテストを追加
- **参考**: [CWE-79: Improper Neutralization of Input During Web Page Generation](https://cwe.mitre.org/data/definitions/79.html)

### M-3: Supabase service_role keyのフロントエンド使用

- **場所**: `/home/als0028/study/shintairiku/marketing-automation/frontend/src/libs/supabase/supabase-admin.ts`
- **説明**: フロントエンドのサーバーサイドコード（API Routes）で `SUPABASE_SERVICE_ROLE_KEY` を使用した `supabaseAdminClient` が作成されている。このクライアントはRLSをバイパスするフルアクセス権限を持つ。Next.jsのAPI Routesはサーバーサイドで実行されるためクライアントには直接露出しないが、攻撃者がSSRF等でサーバー環境変数にアクセスした場合のリスクが高い。
- **影響**: 環境変数の漏洩時にデータベース全体への無制限アクセス
- **対処チェックリスト**:
  - [ ] service_role keyの使用を最小限のAPI Routeに限定する
  - [ ] 可能な限りバックエンドAPIを経由し、フロントエンドでは anon key + RLS のみを使用する設計に移行を検討
  - [ ] Vercelの環境変数を「Preview」「Development」では別の値にする

### M-4: Docker Composeの本番環境シークレット

- **場所**: `/home/als0028/study/shintairiku/marketing-automation/docker-compose.yml` (production stage)
- **説明**: Docker Composeのビルドステージで `STRIPE_SECRET_KEY` と `SUPABASE_SERVICE_ROLE_KEY` がビルド引数 (`ARG`) として渡されている:
  ```yaml
  frontend_prod:
    build:
      args:
        STRIPE_SECRET_KEY: ${STRIPE_SECRET_KEY}
        SUPABASE_SERVICE_ROLE_KEY: ${SUPABASE_SERVICE_ROLE_KEY}
  ```
  Dockerビルド引数はイメージレイヤーに残り、`docker history` で確認可能。
- **影響**: Dockerイメージからシークレットの抽出が可能
- **対処チェックリスト**:
  - [ ] ビルド引数でシークレットを渡さない。代わりにランタイム環境変数として渡す
  - [ ] Next.jsの`standalone`出力では、これらの値はビルド時には不要（サーバーサイドのみ使用するため）
  - [ ] Docker BuildKitのsecretマウント機能の使用を検討:
    ```dockerfile
    RUN --mount=type=secret,id=stripe_key ...
    ```
- **参考**: [CWE-798: Use of Hard-coded Credentials](https://cwe.mitre.org/data/definitions/798.html)

### M-5: 例外ハンドラでの内部情報漏洩

- **場所**: `/home/als0028/study/shintairiku/marketing-automation/backend/app/core/exceptions.py` (全体), `/home/als0028/study/shintairiku/marketing-automation/backend/app/common/auth.py` (258行目)
- **説明**: 複数の箇所で例外メッセージがクライアントに返却されている:
  ```python
  # exceptions.py
  content={"detail": f"An unexpected internal server error occurred: {type(exc).__name__}"}

  # auth.py
  raise HTTPException(status_code=500, detail=f"Authentication error: {e}")
  ```
  例外の型名や内部エラーメッセージが攻撃者に技術スタックやバグの詳細を漏洩する。
- **影響**: 内部実装の情報漏洩、攻撃者による脆弱性特定の手がかり
- **対処チェックリスト**:
  - [ ] 本番環境では汎用エラーメッセージのみを返し、詳細はログにのみ記録:
    ```python
    async def generic_exception_handler(request, exc):
        logger.error(f"Unhandled exception: {type(exc).__name__} - {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )
    ```
  - [ ] `DEBUG=true` の場合のみ詳細エラーを返すように条件分岐を追加

### M-6: OpenAI Agents SDK トレーシングの機密データ設定

- **場所**: `/home/als0028/study/shintairiku/marketing-automation/backend/.env.example` (27行目)
- **説明**: `.env.example` に `OPENAI_AGENTS_TRACE_INCLUDE_SENSITIVE_DATA=true` が設定されている。この設定が本番環境にも適用された場合、OpenAIのトレーシングシステムにユーザーのプロンプト、生成コンテンツ、ツール入出力が送信される。
- **影響**: ユーザーの記事内容やビジネス情報がOpenAIのトレーシングサービスに保存される
- **対処チェックリスト**:
  - [ ] `.env.example` のデフォルト値を `false` に変更
  - [ ] 本番環境で `OPENAI_AGENTS_TRACE_INCLUDE_SENSITIVE_DATA=false` が設定されていることを確認
  - [ ] `store=False` オプションがAI API呼び出し時に使用されていることを確認

### M-7: 依存パッケージのバージョン固定なし

- **場所**: `/home/als0028/study/shintairiku/marketing-automation/backend/pyproject.toml`
- **説明**: バックエンドの全Python依存パッケージがバージョン制約なし（ピンなし）で定義されている:
  ```toml
  dependencies = [
      "fastapi",
      "uvicorn[standard]",
      "openai",
      # ... 全てバージョン指定なし
  ]
  ```
  `uv.lock` が存在するため日常の開発では問題ないが、ロックファイルの再生成時に予期しないバージョンアップが発生し、新たな脆弱性を取り込むリスクがある。
- **影響**: サプライチェーン攻撃のリスク増加、依存パッケージの脆弱性バージョンへの意図しないアップグレード
- **対処チェックリスト**:
  - [ ] メジャーバージョン制約を追加（例: `"fastapi>=0.128,<1.0"`, `"openai>=2.16,<3.0"`）
  - [ ] GitHub DependabotまたはRenovateを導入して依存パッケージの脆弱性を自動検出
  - [ ] CI/CDパイプラインに `pip-audit` または `safety` による脆弱性スキャンを追加

### M-8: GCPサービスアカウントJSONの環境変数格納

- **場所**: `/home/als0028/study/shintairiku/marketing-automation/backend/app/infrastructure/gcp_auth.py`, `/home/als0028/study/shintairiku/marketing-automation/backend/app/core/config.py` (88行目)
- **説明**: GCPサービスアカウントの秘密鍵を含むJSON全体が `GOOGLE_SERVICE_ACCOUNT_JSON` 環境変数に格納されている。Cloud Run環境変数はGCPコンソールやCLIからアクセス可能。
- **影響**: 環境変数が漏洩した場合、GCPリソースへの完全なアクセス
- **対処チェックリスト**:
  - [ ] Cloud Run上ではWorkload Identity Federationを使用し、サービスアカウントキーの使用を廃止
  - [ ] ローカル開発のみサービスアカウントキーを使用し、`GOOGLE_SERVICE_ACCOUNT_JSON_FILE` でファイルパスを指定
  - [ ] Secret ManagerでサービスアカウントJSONを管理し、Cloud Runにはシークレットとしてマウント

### M-9: パストラバーサル攻撃の潜在的リスク

- **場所**: `/home/als0028/study/shintairiku/marketing-automation/backend/app/domains/image_generation/endpoints.py` (487-517行目)
- **説明**: `serve_image` エンドポイントにはパストラバーサル防止のチェックが存在するが、`image_path.resolve()` の呼び出し順序に注意が必要。`image_path` は `storage_path / image_filename` で構築されるが、存在チェック (`image_path.exists()`) の後にパストラバーサルチェックが行われる。ファイル名に `../` が含まれる場合、`exists()` チェックが先に実行され、シンボリックリンク経由での回避の可能性がゼロではない。
  ```python
  image_path = storage_path / image_filename
  if not image_path.exists():  # 先にファイル存在確認
      raise HTTPException(status_code=404)
  # その後にパストラバーサルチェック
  if not str(image_path.resolve()).startswith(str(storage_path.resolve())):
      raise HTTPException(status_code=400)
  ```
- **影響**: ファイルシステム上の任意のファイル読み取り（条件が整った場合）
- **対処チェックリスト**:
  - [ ] パストラバーサルチェックを存在チェックの前に移動する
  - [ ] ファイル名からパスセパレータを除去するバリデーションを追加:
    ```python
    import re
    if re.search(r'[/\\]|\.\.', image_filename):
        raise HTTPException(status_code=400, detail="Invalid filename")
    ```
  - [ ] 認証も追加する（H-3参照）

---

## Low (低) 脆弱性

### L-1: .gitignoreに特定のサービスアカウントファイル名がハードコード

- **場所**: `/home/als0028/study/shintairiku/marketing-automation/.gitignore`
- **説明**: 特定のサービスアカウントファイル名がハードコードされている:
  ```
  marketing-automation-461305-f94de589a90c.json
  marketing-automation-461305-d3821e14ba9f.json
  backend/marketing-automation-461305-f4cb0b7367b7.json
  ```
  これらのファイル名はGCPプロジェクトIDとキーIDを含んでおり、プロジェクトの識別情報が漏洩している。また、将来のキーローテーションで異なるファイル名が使用された場合、.gitignoreに追加し忘れるリスクがある。
- **影響**: GCPプロジェクトIDの漏洩（低リスク）、将来のキーファイルのコミットリスク
- **対処チェックリスト**:
  - [ ] 特定ファイル名の代わりにワイルドカードパターンを使用:
    ```gitignore
    *.json
    !package.json
    !tsconfig.json
    # または
    *-service-account*.json
    *-key*.json
    ```
  - [ ] `git-secrets` や `pre-commit` フックで認証情報のコミットを防止

### L-2: Cloud Run環境変数の`NEXT_PUBLIC_API_BASE_URL`公開

- **場所**: `/home/als0028/study/shintairiku/marketing-automation/frontend/.env.example` (21行目)
- **説明**: Cloud RunのURLが`.env.example`にコミットされている:
  ```
  NEXT_PUBLIC_API_BASE_URL=https://marketing-automation-742231208085.asia-northeast1.run.app
  ```
  `NEXT_PUBLIC_` プレフィックスのため、このURLはクライアントサイドのJavaScriptバンドルにも含まれる。Cloud Runが非公開化されている場合は直接アクセスできないが、サービス名やプロジェクト番号が漏洩する。
- **影響**: インフラ構成情報の漏洩（攻撃の偵察に利用される可能性）
- **対処チェックリスト**:
  - [ ] `.env.example`にはプレースホルダー値のみを記載:
    ```
    NEXT_PUBLIC_API_BASE_URL=https://YOUR_CLOUD_RUN_URL.run.app
    ```
  - [ ] 実際のURLはデプロイ設定（Vercel環境変数等）でのみ管理

### L-3: フロントエンドDockerfileのbuild stageにシークレットARGが存在

- **場所**: `/home/als0028/study/shintairiku/marketing-automation/frontend/Dockerfile` (builder stage)
- **説明**: M-4と関連。Dockerfileのビルダーステージに `STRIPE_SECRET_KEY` と `SUPABASE_SERVICE_ROLE_KEY` がARGとして定義されている。中間イメージレイヤーにこれらの値が残存する可能性がある。
- **影響**: M-4参照

### L-4: CIパイプラインにセキュリティスキャンが未実装

- **場所**: `/home/als0028/study/shintairiku/marketing-automation/.github/workflows/backend-docker-build.yml`
- **説明**: GitHub Actionsのワークフローはビルドと簡易起動テストのみ。SAST (静的アプリケーションセキュリティテスト)、依存脆弱性スキャン、Dockerイメージスキャン、シークレット検出が含まれていない。
- **影響**: 脆弱性やシークレットの漏洩がCI段階で検出されない
- **対処チェックリスト**:
  - [ ] `trivy` によるDockerイメージ脆弱性スキャンを追加:
    ```yaml
    - name: Scan image with Trivy
      uses: aquasecurity/trivy-action@master
      with:
        image-ref: marketing-automation-backend:test
        severity: 'CRITICAL,HIGH'
    ```
  - [ ] `pip-audit` による Python 依存脆弱性スキャンを追加
  - [ ] `gitleaks` によるシークレット検出を追加
  - [ ] `npm audit` / `bun audit` によるフロントエンド依存脆弱性スキャンを追加

### L-5: Dockerコンテナの非rootユーザー未使用（バックエンド）

- **場所**: `/home/als0028/study/shintairiku/marketing-automation/backend/Dockerfile`
- **説明**: バックエンドのDockerfileがrootユーザーでアプリケーションを実行している。`USER` 命令が含まれていない（フロントエンドのDockerfileは `USER node` を使用している）。
- **影響**: コンテナ内でコード実行の脆弱性が発生した場合、root権限でシステムにアクセス可能
- **対処チェックリスト**:
  - [ ] 非rootユーザーを作成してアプリケーションを実行:
    ```dockerfile
    RUN groupadd -r appuser && useradd -r -g appuser appuser
    RUN chown -R appuser:appuser /app
    USER appuser
    CMD ["sh", "-c", "uv run uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
    ```

### L-6: 開発環境用設定の本番混入リスク

- **場所**: `/home/als0028/study/shintairiku/marketing-automation/docker-compose.yml` (frontend_dev service)
- **説明**: `docker-compose.yml` の `frontend_dev` サービスに `NEXT_PUBLIC_ENABLE_COMPANY_MOCK: "true"` が設定されている。開発環境でのモックデータ有効化フラグだが、この設定が本番に混入するリスクがある。
- **影響**: 本番環境でモックデータが表示される可能性

---

## 一般セキュリティ推奨事項

- [ ] **定期的な依存パッケージ更新**: `pip-audit` (Python) と `npm audit` / Trivy (Node.js) を月次で実行し、既知のCVEを持つパッケージを更新する
- [ ] **セキュリティログの一元管理**: Cloud Loggingに全認証イベント、管理者操作、エラーを集約し、アラートを設定する
- [ ] **Webhook署名検証の強化**: Stripe webhookは `constructEvent()` で署名検証済み（確認済み）。Clerk webhookも `svix` で署名検証済み（確認済み）。今後新しいwebhookを追加する際も必ず署名検証を実装すること
- [ ] **API ドキュメントのアクセス制限**: FastAPIのデフォルトで `/docs` (Swagger UI) と `/redoc` が公開されている。本番環境では `app = FastAPI(docs_url=None, redoc_url=None)` で無効化を検討
- [ ] **セッション管理**: ClerkのJWT有効期限 (`exp`) が適切に設定されていることを確認。短い有効期限（5-15分）+ リフレッシュトークン方式を推奨
- [ ] **WordPress認証情報の暗号化鍵ローテーション**: `CREDENTIAL_ENCRYPTION_KEY` のローテーション手順を文書化し、定期的に実施する
- [ ] **Supabase Realtimeのセキュリティ**: Realtimeチャネル (`blog_generation:{process_id}`) の購読が認証済みユーザーに制限されていることを確認

---

## セキュリティ態勢改善計画（優先順位付き）

### フェーズ1: 緊急対応（1-2週間）
1. `validate_token_without_signature` 関数の削除 (C-2)
2. APIレート制限の導入 (H-1)
3. HTTPセキュリティヘッダーの追加 (H-2)
4. 画像配信エンドポイントへの認証追加 (H-3)
5. SSRF防止バリデーションの追加 (H-4)
6. プロキシルートのCORS修正 (H-5)
7. ファイルアップロードバリデーション強化 (H-6)
8. APIキーのログ出力停止 (H-7)

### フェーズ2: 重要改善（2-4週間）
9. RLSポリシーの再設計・実装 (C-1)
10. ファイルアップロードのサイズ・タイプ制限 (H-6)
11. XSSサニタイゼーションの統一 (M-2)
12. Dockerビルドシークレットの修正 (M-4)
13. 例外ハンドラの情報漏洩修正 (M-5)
14. CIパイプラインへのセキュリティスキャン追加 (L-4)

### フェーズ3: 継続的改善（1-3ヶ月）
15. Workload Identity Federationへの移行 (M-8)
16. service_role keyのフロントエンド使用最小化 (M-3)
17. 依存パッケージバージョン制約の追加 (M-7)
18. 本番FastAPIドキュメントの無効化
19. セキュリティ監査の定期実施（四半期ごと）
20. ペネトレーションテストの実施

---

*このレポートは2026年2月10日時点のコードベースに基づいて作成されました。新しいコード変更により、新たな脆弱性が導入される可能性があります。定期的なセキュリティレビューを推奨します。*
