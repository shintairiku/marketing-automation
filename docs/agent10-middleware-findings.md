# Agent-10: Frontend Middleware Security Analysis

**調査完了**: 2026-02-04

## 調査対象ファイル
- frontend/src/middleware.ts (97行)

## ルート保護マッピング

### Protected Routes (認証必須):
| パターン | 実際のルート | 保護状態 |
|---------|-------------|---------|
| /admin(.*) | /admin, /admin/users, /admin/blog-usage, /admin/plans | Protected + Privileged |
| /dashboard(.*) | /dashboard, /dashboard/articles | Protected + Privileged |
| /account(.*) | /account (route group) | Protected |
| /generate(.*) | N/A | Protected |
| /edit(.*) | N/A | Protected |
| /tools(.*) | /tools/generate/seo | Protected |
| /seo(.*) | /seo/* (多数) | Protected + Privileged |
| /instagram(.*) | /instagram/home | Protected + Privileged |
| /line(.*) | N/A | Protected + Privileged |
| /blog(.*) | /blog/new, /blog/[processId], /blog/history | Protected |
| /settings(.*) | /settings/*, /settings/integrations/* | Protected |
| /company-settings(.*) | /company-settings/* | Protected + Privileged |
| /help(.*) | /help/* | Protected |

### Public Routes (認証不要):
| パターン | 実際のルート | 備考 |
|---------|-------------|------|
| /pricing | /pricing | リダイレクト先 |
| /auth | /auth | サインイン選択 |
| /sign-in(.*) | /sign-in/[[...sign-in]] | Clerk |
| /sign-up(.*) | /sign-up/[[...sign-up]] | Clerk |
| /invitation(.*) | /invitation/accept | 招待受諾 |
| /api/webhooks(.*) | /api/webhooks, /api/webhooks/clerk | Webhook |

### 保護されていないルート (潜在的問題):
| ルート | 状態 | 問題 |
|--------|------|------|
| /user-profile(.*) | 未保護 | isProtectedRouteに含まれていない |
| /api/* (webhooks以外) | 不明確 | Middlewareで明示的に保護されていない |

---

## 発見事項

### [MEDIUM] MWD-001: /user-profile ルートが保護されていない
- **ファイル**: frontend/src/middleware.ts
- **行番号**: 7-19 (isProtectedRoute定義)
- **問題**: /user-profile パスが isProtectedRoute に含まれていない
- **実際のルート**: /user-profile/[[...user-profile]] (Clerk UserProfile コンポーネント)
- **影響**:
  - Clerk UserProfile 自体が認証を要求するため実害は限定的
  - しかし、ミドルウェアレベルでの保護がないため、認証前にページがロードされる可能性あり
  - 他の /user-profile 配下に新ルートを追加した場合に保護漏れのリスク
- **修正**: isProtectedRoute に /user-profile(.*) を追加

### [MEDIUM] MWD-002: API Routes の保護が不明確
- **ファイル**: frontend/src/middleware.ts
- **行番号**: 30-35 (isPublicRoute定義), 56-88 (matcher config)
- **問題**:
  - /api/webhooks(.*) のみ明示的にpublic指定
  - 他の /api/* ルートは isProtectedRoute にも isPublicRoute にも含まれていない
  - 結果: `if (!isPublicRoute(req) && isProtectedRoute(req))` が false となりチェックをスキップ
- **影響**:
  - /api/proxy/*, /api/subscription/*, /api/organizations/*, /api/admin/* 等がミドルウェアレベルでは認証チェックされない
  - 各API Route内で auth() を呼んでいるが、一貫性がない可能性
- **修正**: /api/(.*) を isProtectedRoute に追加し、webhooksのみ除外
- **関連**: PROXY-001 (Agent-07) との相互作用で認証バイパスリスクが増大

### [LOW] MWD-003: 特権チェックでClerk API呼び出しが毎回発生
- **ファイル**: frontend/src/middleware.ts
- **行番号**: 49-56, 78-82
- **問題**:
  - isPrivilegedOnlyRoute へのアクセス時、毎回 getUserEmail(userId) を呼び出し
  - これは Clerk Backend API への HTTP リクエスト
- **影響**:
  - パフォーマンス低下
  - Clerk API レート制限への影響
  - リクエストごとに追加のレイテンシ
- **修正案**:
  1. Clerk の Session Claims にメールを含める設定を追加
  2. または、メール情報をキャッシュ（ただしミドルウェアでのキャッシュは複雑）
  3. JWTカスタムクレームにドメイン情報を含める

### [LOW] MWD-004: パスマッチングの一貫性
- **ファイル**: frontend/src/middleware.ts
- **行番号**: 7-19
- **問題**:
  - 一部のパスは (.*) ワイルドカードを使用
  - Next.js Route Groups (括弧付き) は URL に影響しないため問題なし
  - ただし /tools ルートグループ (tools) 内のルートと、実際の /tools パスが混在
- **影響**:
  - /tools/generate/seo (実ルート) と (tools)/blog/* (Route Group内) の両方が存在
  - 混乱の原因になり得る
- **修正**: ドキュメント化して整理

### [INFO] MWD-005: リダイレクトループの可能性は低い
- **分析結果**:
  - / -> ログイン済み: /blog/new / 未ログイン: /auth
  - /auth は public route -> リダイレクトなし
  - /blog/new は protected route -> 未ログインなら /sign-in?redirect_url=...
  - /sign-in は public route -> リダイレクトなし
- **結論**: 正常なフローではリダイレクトループは発生しない

### [INFO] MWD-006: ヘッダー操作の安全性
- **分析結果**:
  - ミドルウェアはカスタムヘッダーを追加していない
  - Clerk ミドルウェア (clerkMiddleware) がセッション情報を処理
  - NextResponse.redirect() と NextResponse.next() のみ使用
- **結論**: ヘッダーインジェクションの脆弱性は見当たらない

---

## 良い実装
- Clerk ミドルウェアラッパーを使用した標準的な認証フロー
- 特権ユーザーのメールドメインチェック（ハードコードだが安全）
- Route matcher パターンの使用（可読性が高い）
- Sign-in リダイレクト時に redirect_url を保持

---

## 推奨修正

### 1. [MEDIUM] /user-profile(.*) を isProtectedRoute に追加:
```typescript
const isProtectedRoute = createRouteMatcher([
  '/admin(.*)',
  '/dashboard(.*)',
  '/account(.*)',
  '/generate(.*)',
  '/edit(.*)',
  '/tools(.*)',
  '/seo(.*)',
  '/instagram(.*)',
  '/line(.*)',
  '/blog(.*)',
  '/settings(.*)',
  '/company-settings(.*)',
  '/help(.*)',
  '/user-profile(.*)', // 追加
]);
```

### 2. [MEDIUM] API Routes の保護を明確化:
- 各 API Route で一貫した認証チェックを確認
- または /api/(?!webhooks)(.*) を isProtectedRoute に追加

### 3. [LOW] 特権チェックの最適化（Clerk カスタムクレーム使用）:
- Clerk Dashboard -> Sessions -> Customize session token
- user.emailAddresses[0].emailAddress をクレームに追加
- ミドルウェアで sessionClaims.email から直接取得

---

## API Routes の個別認証状態

| Route | 認証方式 | 備考 |
|-------|---------|------|
| /api/proxy/* | auth header 転送 | バックエンドで検証 |
| /api/admin/* | auth() + getToken() | 明示的チェック |
| /api/subscription/* | auth() | 各ルートで実装 |
| /api/organizations/* | auth() | 各ルートで実装 |
| /api/webhooks/* | Webhook署名検証 | Stripe/Clerk |

---

## 相互関係

### MWD-002 と Agent-07 PROXY-001 の相互作用
- API Routes のミドルウェア保護がなく、プロキシルートも独自認証なしのため、Defense in Depth が機能していない
- AUTH-001 (DEBUG_MODE) との組み合わせで、バックエンドのJWT検証もスキップ可能

### 攻撃シナリオ
1. 攻撃者が /api/proxy/admin/users にリクエスト
2. ミドルウェアは /api/* を保護対象と認識しないためスルー
3. プロキシルートは Authorization ヘッダーを検証せずバックエンドに転送
4. バックエンドで DEBUG=true なら任意のJWTで認証バイパス

---

## 発見数サマリー
- Critical: 0
- High: 0
- Medium: 2
- Low: 2
