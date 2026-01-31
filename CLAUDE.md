# CLAUDE.md - 永続メモリ & 自己改善ログ

> ## **【最重要】記憶の更新は絶対に忘れるな**
> **作業の開始時・途中・完了時に必ずこのファイルを確認・更新せよ。**
> コード変更、設計変更、新しい知見、バグ修正、アーキテクチャ変更 — どんな小さな変更でも、発生したらその場で即座にこのファイルに記録すること。
> **ユーザーに「記憶を更新して」と言われる前に、自分から更新するのが当たり前。言われてからでは遅い。**
> これは最優先の義務であり、他のどんなタスクよりも優先される。

> **このファイルはClaude Codeの永続メモリであり、自己改善の記録である。**
> セッションをまたいで知識を保持し、過去の失敗・学び・判断を蓄積して次のセッションの自分をより賢くするためのファイルである。
>
> ## 運用ルール
> 1. **毎回の作業開始時**にこのファイルを読み込み、内容に従って行動する
> 2. **作業中に新しい知見・決定・変更が生じたら**、即座にこのファイルを更新する（追記・修正・削除）
> 3. **更新対象**: アーキテクチャ変更、新しい依存関係、デプロイ設定、踏んだ罠・解決策、環境差異、運用ルールなど
> 4. このファイルの情報が古くなった場合は削除・修正し、常に最新状態を維持する
> 5. **あとで思い出せるように書く**: 技術的な知見を記録する際は、調査元の公式ドキュメントURL・GitHubリポジトリ・SDKソースファイルパスなどの**情報ソース**も一緒に記録する
> 6. **セクションは自由に増減してよい**: 新しいテーマが出てきたらセクションを追加し、不要になったら統合・削除する
> 7. **自己改善**: ユーザーに指摘された間違い・非効率・判断ミスは「自己改善ログ」セクションに記録する
> 8. **常時更新の義務**: 新情報の発見、コードリーディング中の新発見、設計変更、UIの変更、技術的知見の獲得、バグの発見と修正など — あらゆる新たな情報や更新が発生した場合は**必ずその場でこのファイルを更新する**

---

## Package Management (STRICT)

- **Backend (Python)**: `uv add <package>` for dependencies. **Never use `pip install`.**
- **Frontend (JS/TS)**: `bun add <package>` for dependencies. **Never use `npm install` or `yarn add`.**
- Backend lock: `uv sync` to sync after changes
- Frontend lock: `bun install` to sync after changes

---

## プロジェクト概要

**BlogAI / Marketing Automation Platform** — AIを活用したSEO記事・ブログ記事の自動生成SaaSプラットフォーム。
WordPress連携によるブログ投稿、SEO分析、画像生成、組織管理、サブスクリプション課金を提供する。

### 主要機能
1. **SEO記事生成**: キーワード→SERP分析→ペルソナ選択→テーマ選択→アウトライン→本文執筆→編集のフルフローをAIエージェントが実行
2. **Blog AI (WordPress連携)**: WordPressサイトと接続し、AIがブログ記事を生成・投稿
3. **AI画像生成**: Google Vertex AI Imagen-4による記事用画像の自動生成
4. **組織管理**: マルチテナント対応。招待制でチームメンバー管理（owner/admin/member）
5. **サブスクリプション**: Stripe連携の個人プラン・チームプラン課金
6. **管理者ダッシュボード**: @shintairiku.jp ドメインユーザー専用の管理画面

---

## Tech Stack

### Backend
- **Framework**: FastAPI + Uvicorn (Python 3.12)
- **Package Manager**: uv
- **AI/ML**: OpenAI Agents SDK, Google Generative AI (Gemini), Google Vertex AI (Imagen-4)
- **Database**: Supabase (PostgreSQL + Realtime)
- **Authentication**: Clerk JWT (RS256, JWKS検証)
- **External APIs**: SerpAPI, Google Cloud Storage, Notion API
- **その他**: Pydantic, SQLAlchemy, httpx, BeautifulSoup4, PyJWT, sse-starlette

### Frontend
- **Framework**: Next.js 15 + React 19 + TypeScript
- **Package Manager**: Bun (Turbopack有効)
- **UI**: Tailwind CSS 3.4 + shadcn/ui (Radix UI) + Framer Motion
- **Auth**: @clerk/nextjs v6
- **DB**: @supabase/supabase-js (Realtime subscriptions)
- **Payment**: Stripe (@stripe/stripe-js)
- **Icons**: Lucide React
- **Font**: Noto Sans JP
- **Analytics**: Vercel Analytics

### Infrastructure
- **DB**: Supabase (PostgreSQL + RLS + Realtime)
- **Storage**: Google Cloud Storage (画像)
- **CI**: GitHub Actions (Docker build test)
- **Container**: Docker + docker-compose

---

## Project Structure

```
marketing-automation/
├── backend/                          # FastAPI バックエンド
│   ├── main.py                       # エントリポイント (FastAPI app, CORS, ルーティング)
│   ├── pyproject.toml                # Python依存関係 (uv管理)
│   ├── Dockerfile                    # Python 3.12-slim + uv
│   ├── .env / .env.example           # 環境変数
│   └── app/
│       ├── api/router.py             # ルーター集約
│       ├── core/
│       │   ├── config.py             # Settings (Pydantic BaseSettings)
│       │   ├── exceptions.py         # グローバル例外ハンドラ
│       │   └── logger.py             # ログ設定
│       ├── common/
│       │   ├── auth.py               # Clerk JWT検証 (verify_clerk_token)
│       │   ├── admin_auth.py         # 管理者認証 (@shintairiku.jp)
│       │   ├── database.py           # Supabaseクライアント初期化
│       │   └── schemas.py            # WebSocketメッセージ定義
│       ├── domains/
│       │   ├── seo_article/          # SEO記事生成ドメイン（最大規模）
│       │   │   ├── endpoints.py      # /articles/* エンドポイント群
│       │   │   ├── schemas/          # リクエスト/レスポンススキーマ
│       │   │   ├── services/         # 生成・管理・バージョン管理サービス
│       │   │   └── agents/           # OpenAI Agents SDK定義
│       │   ├── blog/                 # Blog AI / WordPress連携
│       │   │   ├── endpoints.py      # /blog/* エンドポイント群
│       │   │   ├── services/         # WordPress MCP, 生成サービス
│       │   │   └── schemas.py
│       │   ├── organization/         # 組織管理
│       │   │   ├── endpoints.py      # /organizations/* エンドポイント群
│       │   │   ├── service.py
│       │   │   └── schemas.py
│       │   ├── company/              # 会社情報管理
│       │   │   ├── endpoints.py      # /companies/* エンドポイント群
│       │   │   ├── service.py
│       │   │   └── schemas.py
│       │   ├── style_template/       # 文体スタイルガイド
│       │   │   ├── endpoints.py      # /style-templates/* エンドポイント群
│       │   │   ├── service.py
│       │   │   └── schemas.py
│       │   ├── image_generation/     # 画像生成
│       │   │   ├── endpoints.py      # /images/* エンドポイント群
│       │   │   ├── service.py
│       │   │   └── schemas.py
│       │   └── admin/                # 管理者ダッシュボード
│       │       ├── endpoints.py      # /admin/* エンドポイント群
│       │       └── schemas.py
│       └── infrastructure/
│           ├── external_apis/
│           │   ├── gcs_service.py    # Google Cloud Storage
│           │   ├── serpapi_service.py # SerpAPI (SERP分析)
│           │   └── notion_service.py # Notion同期
│           ├── gcp_auth.py           # GCP認証 (サービスアカウント)
│           ├── clerk_client.py       # Clerk API クライアント
│           ├── logging/              # ログシステム
│           │   ├── service.py
│           │   ├── models.py
│           │   └── agents_logging_integration.py
│           └── analysis/
│               ├── content_analyzer.py
│               └── cost_calculation_service.py
├── frontend/                         # Next.js 15 フロントエンド
│   ├── package.json                  # Bun依存関係
│   ├── next.config.js                # API proxy, 画像ドメイン設定
│   ├── tailwind.config.ts            # カスタムカラー・フォント
│   ├── Dockerfile                    # Next.js standalone
│   └── src/
│       ├── middleware.ts             # Clerk認証 + ルート保護 + 特権チェック
│       ├── app/
│       │   ├── layout.tsx            # ルートレイアウト (ClerkProvider, Noto Sans JP)
│       │   ├── auth/page.tsx         # 認証選択画面
│       │   ├── (marketing)/          # ランディングページ・pricing（リダイレクト）
│       │   ├── (dashboard)/          # ダッシュボード (特権のみ)
│       │   ├── (tools)/              # メインツール群 (SubscriptionGuard有)
│       │   │   ├── blog/             # Blog AI
│       │   │   ├── seo/              # SEO記事生成
│       │   │   ├── company-settings/ # 会社情報・スタイルガイド
│       │   │   ├── instagram/        # Instagram連携 (placeholder)
│       │   │   └── help/             # ヘルプ
│       │   ├── (settings)/           # 設定群 (SubscriptionGuardなし、未課金でもアクセス可)
│       │   │   └── settings/         # /settings/* ページ
│       │   │       ├── account/      # アカウント設定
│       │   │       ├── billing/      # 請求&プラン管理（旧pricing統合）
│       │   │       ├── members/      # チームメンバー管理
│       │   │       └── integrations/ # WordPress/Instagram/LINE連携
│       │   ├── (admin)/              # 管理者画面 (特権のみ)
│       │   ├── sign-in/              # Clerk サインイン
│       │   ├── sign-up/              # Clerk サインアップ
│       │   ├── invitation/           # 組織招待受諾
│       │   ├── pricing/              # → 認証済み:/settings/billing、未認証:/auth へリダイレクト
│       │   └── api/                  # Next.js API Routes
│       │       ├── proxy/[...path]/  # バックエンドAPIプロキシ
│       │       ├── subscription/     # Stripe checkout/portal/status/webhook
│       │       ├── organizations/    # 組織CRUD・メンバー・招待
│       │       ├── articles/         # 記事生成API
│       │       ├── companies/        # 会社情報API
│       │       ├── admin/            # 管理者API
│       │       └── webhooks/         # Clerk/Stripe webhook
│       ├── components/
│       │   ├── ui/                   # shadcn/ui コンポーネント群
│       │   ├── display/              # header, sidebar, pageTabs
│       │   ├── layout/              # AppLayoutClient
│       │   ├── subscription/         # SubscriptionGuard, SubscriptionBanner
│       │   └── seo/                  # SEO関連UI部品
│       ├── features/
│       │   ├── landing/              # LP: sections, animations, background
│       │   ├── pricing/              # Stripe連携
│       │   ├── blog/                 # ブログ生成UI
│       │   ├── article-generation/   # 記事生成UI
│       │   ├── tools/                # SEO/Instagram等ツールUI
│       │   ├── account/              # 顧客管理アクション
│       │   └── emails/               # メールテンプレート
│       ├── hooks/
│       │   ├── useArticleGenerationRealtime.ts  # Supabase Realtime記事生成追跡
│       │   ├── useSupabaseRealtime.ts           # Realtime接続管理
│       │   ├── useArticles.ts                   # 記事一覧取得
│       │   ├── useArticleVersions.ts            # バージョン管理
│       │   ├── useAutoSave.ts                   # 自動保存
│       │   ├── useDefaultCompany.ts             # デフォルト会社
│       │   ├── useAgentChat.ts                  # エージェントチャット
│       │   └── useRecoverableProcesses.ts       # 復旧可能プロセス
│       ├── lib/
│       │   ├── api.ts               # ApiClientクラス (バックエンドAPI呼び出し)
│       │   └── subscription/        # サブスクリプションロジック・型定義
│       ├── utils/                   # cn, flow-config, date-time等
│       ├── types/                   # article-generation型定義
│       ├── contexts/                # SidebarContext
│       └── styles/globals.css       # グローバルCSS
├── shared/supabase/
│   ├── config.toml                  # Supabase設定
│   └── migrations/                  # 全SQLマイグレーション (30+ファイル)
├── docs/                            # ドキュメント群
│   ├── backend/                     # API, 認証, DDD, エージェント仕様書
│   ├── frontend/                    # アーキテクチャ, コンポーネント, 状態管理
│   ├── database/                    # テーブル仕様, スキーマ, マイグレーション
│   ├── integration/                 # Clerk/Stripe/Supabase Realtime連携
│   └── overview/                    # 技術スタック全体設計思想
├── docker-compose.yml               # frontend_dev(3000), backend(8008→8000), stripe-cli
├── .github/workflows/               # CI: backend-docker-build.yml
└── .env.example                     # ルート環境変数テンプレート
```

---

## Backend API Endpoints

### SEO Article (`/articles`)
| Method | Path | 概要 |
|--------|------|------|
| GET | `/articles/` | 記事一覧 (ページネーション・フィルタ) |
| GET | `/articles/{article_id}` | 記事詳細 |
| PATCH | `/articles/{article_id}` | 記事更新 (title, content, keywords, status) |
| PATCH | `/articles/{article_id}/status` | 公開ステータス更新 |
| POST | `/articles/{article_id}/ai-edit` | AIブロック編集 |
| POST | `/articles/generation/start` | 記事生成開始 |
| GET | `/articles/generation/{process_id}` | 生成状態取得 |
| POST | `/articles/generation/{process_id}/resume` | 生成再開 |
| POST | `/articles/generation/{process_id}/user-input` | ユーザー入力送信 |
| POST | `/articles/generation/{process_id}/pause` | 生成一時停止 |
| DELETE | `/articles/generation/{process_id}` | 生成キャンセル |
| GET | `/articles/generation/{process_id}/events` | 生成イベント取得 |
| GET | `/articles/all-processes` | 全プロセス一覧 |
| GET | `/articles/recoverable-processes` | 復旧可能プロセス |
| GET | `/articles/generation/{process_id}/realtime-info` | リアルタイム情報 |
| GET | `/articles/generation/{process_id}/snapshots` | スナップショット一覧 |
| POST | `/articles/flows/` | フロー作成 |
| GET | `/articles/flows/` | フロー一覧 |
| GET | `/articles/flows/{flow_id}` | フロー詳細 |
| PUT | `/articles/flows/{flow_id}` | フロー更新 |
| DELETE | `/articles/flows/{flow_id}` | フロー削除 |
| POST | `/articles/flows/{flow_id}/execute` | フロー実行 |
| GET | `/articles/flows/templates/` | フローテンプレート一覧 |
| POST | `/articles/flows/templates/{template_id}/copy` | テンプレートコピー |
| POST | `/articles/ai-content-generation` | AIコンテンツ生成 (Responses API) |
| POST | `/articles/ai-content-generation/upload` | ユーザーコンテンツアップロード処理 |

### Blog AI (`/blog`)
| Method | Path | 概要 |
|--------|------|------|
| GET | `/blog/connect/wordpress` | WordPress OAuthリダイレクト |
| POST | `/blog/connect/wordpress` | WordPressサイト登録 (MCP callback) |
| POST | `/blog/sites/register` | コードによるWordPress手動登録 |
| DELETE | `/blog/sites/{site_id}` | サイト解除 |
| PATCH | `/blog/sites/{site_id}/organization` | サイト組織変更 |
| GET | `/blog/sites` | 接続サイト一覧 |
| GET | `/blog/sites/{site_id}` | サイト詳細 |
| POST | `/blog/sites/{site_id}/test-connection` | 接続テスト |
| POST | `/blog/generation/start` | ブログ生成開始 |
| GET | `/blog/generation/{process_id}` | 生成状態取得 |
| POST | `/blog/generation/{process_id}/user-input` | ユーザー入力 |
| POST | `/blog/generation/{process_id}/pause` | 生成一時停止 |
| DELETE | `/blog/generation/{process_id}` | 生成キャンセル |
| POST | `/blog/ai-questions` | AI質問生成 |
| POST | `/blog/user-answers` | 回答送信→生成開始 |
| GET | `/blog/generation-history` | 生成履歴 |
| POST | `/blog/upload-image` | 画像アップロード |

### Organization (`/organizations`)
| Method | Path | 概要 |
|--------|------|------|
| POST | `/organizations/` | 組織作成 (ユーザーがowner) |
| GET | `/organizations/` | ユーザーの組織一覧 |
| GET | `/organizations/{id}` | 組織詳細 |
| PUT | `/organizations/{id}` | 組織更新 (owner/adminのみ) |
| DELETE | `/organizations/{id}` | 組織削除 (ownerのみ) |
| GET | `/organizations/{id}/members` | メンバー一覧 |
| PUT | `/organizations/{id}/members/{uid}/role` | ロール変更 |
| DELETE | `/organizations/{id}/members/{uid}` | メンバー削除 |
| POST | `/organizations/{id}/invitations` | 招待送信 (メールベース) |
| GET | `/organizations/invitations` | 受信招待一覧 |
| POST | `/organizations/invitations/respond` | 招待承諾/辞退 |
| GET | `/organizations/{id}/subscription` | サブスクリプション情報 |

### Company (`/companies`)
| Method | Path | 概要 |
|--------|------|------|
| POST | `/companies/` | 会社情報作成 |
| GET | `/companies/` | 会社情報一覧 |
| GET | `/companies/default` | デフォルト会社 |
| GET | `/companies/{id}` | 会社詳細 |
| PUT | `/companies/{id}` | 会社更新 |
| DELETE | `/companies/{id}` | 会社削除 |
| POST | `/companies/set-default` | デフォルト設定 |

### Style Template (`/style-templates`)
| Method | Path | 概要 |
|--------|------|------|
| GET | `/style-templates/` | テンプレート一覧 |
| GET | `/style-templates/{id}` | テンプレート詳細 |
| POST | `/style-templates/` | テンプレート作成 |
| PUT | `/style-templates/{id}` | テンプレート更新 |
| DELETE | `/style-templates/{id}` | テンプレート削除 (論理削除) |
| POST | `/style-templates/{id}/set-default` | デフォルト設定 |

### Image Generation (`/images`)
| Method | Path | 概要 |
|--------|------|------|
| POST | `/images/generate` | Imagen-4画像生成 |
| POST | `/images/generate-and-link` | 生成+プレースホルダリンク |
| POST | `/images/generate-from-placeholder` | プレースホルダから生成 |
| POST | `/images/upload` | GCSアップロード |
| POST | `/images/replace-placeholder` | プレースホルダ置換 |
| POST | `/images/restore-placeholder` | プレースホルダ復元 |
| GET | `/images/serve/{filename}` | ローカル画像配信 |
| GET | `/images/article-images/{article_id}` | 記事画像一覧 |
| GET | `/images/placeholder-history/{article_id}/{placeholder_id}` | プレースホルダ履歴 |

### Admin (`/admin`)
| Method | Path | 概要 |
|--------|------|------|
| GET | `/admin/users` | 全ユーザー一覧 (@shintairiku.jp限定) |
| GET | `/admin/users/{user_id}` | ユーザー詳細 |
| PATCH | `/admin/users/{user_id}/privilege` | 特権フラグ変更 |
| PATCH | `/admin/users/{user_id}/subscription` | サブスクリプション変更 |

### Health
| Method | Path | 概要 |
|--------|------|------|
| GET | `/` | APIルート (稼働確認) |
| GET | `/health` | ヘルスチェック |

---

## Frontend Routes

### Public Routes (認証不要)
| Path | 概要 |
|------|------|
| `/` | ルート → 認証済み: `/blog/new`、未認証: `/auth` にリダイレクト |
| `/auth` | サインイン/サインアップ選択画面 |
| `/sign-in` | Clerk サインイン |
| `/sign-up` | Clerk サインアップ |
| `/pricing` | リダイレクト: 認証済み→`/settings/billing`、未認証→`/auth` |
| `/invitation/accept` | 組織招待受諾 |

### Protected Routes (認証必須 + サブスクリプション必須) — `(tools)` レイアウト
| Path | 概要 |
|------|------|
| `/blog/new` | 新規ブログ記事生成 |
| `/blog/[processId]` | ブログ生成進捗・編集 |
| `/blog/history` | ブログ生成履歴 |

### Protected Routes (認証必須、サブスク不要) — `(settings)` レイアウト
| Path | 概要 |
|------|------|
| `/settings/account` | アカウント設定 |
| `/settings/billing` | 請求&プラン管理（プラン購入/変更/シート変更/Stripe Portal） |
| `/settings/members` | チームメンバー管理 |
| `/settings/integrations/wordpress` | WordPress連携 |
| `/settings/integrations/wordpress/connect` | WordPress接続 |
| `/settings/integrations/instagram` | Instagram連携 |
| `/settings/integrations/line` | LINE連携 |
| `/help/home` | ヘルプセンター |

### Privilege-Only Routes (@shintairiku.jp限定)
| Path | 概要 |
|------|------|
| `/admin` | 管理者ダッシュボード |
| `/admin/users` | ユーザー管理 |
| `/dashboard` | メインダッシュボード |
| `/dashboard/articles` | 記事管理 |
| `/seo/generate/new-article` | SEO記事生成 |
| `/seo/generate/edit-article/[id]` | SEO記事編集 |
| `/seo/manage/list` | 生成記事一覧 |
| `/seo/manage/status` | 生成ステータス |
| `/seo/manage/schedule` | 公開スケジュール |
| `/seo/analyze/dashboard` | 分析ダッシュボード |
| `/seo/analyze/report` | レポート生成 |
| `/seo/analyze/feedback` | フィードバック |
| `/seo/input/persona` | ペルソナ選択 |
| `/company-settings/company` | 会社情報管理 |
| `/company-settings/style-guide` | 文体スタイルガイド |
| `/instagram/home` | Instagram連携 |

---

## Frontend API Routes (Next.js `/api/`)

| Path | Methods | 概要 |
|------|---------|------|
| `/api/proxy/[...path]` | ALL | バックエンドAPIプロキシ (120秒タイムアウト) |
| `/api/subscription/status` | GET | サブスクリプション状態取得 |
| `/api/subscription/checkout` | POST | Stripe Checkout Session作成 (新規契約用) |
| `/api/subscription/upgrade-to-team` | POST | 個人→チームプラン アップグレード (日割り対応) |
| `/api/subscription/update-seats` | POST | チームプラン シート数変更 (増減両対応、日割り対応) |
| `/api/subscription/preview-upgrade` | POST | サブスク変更料金プレビュー (個人→チーム / シート変更 両対応) |
| `/api/subscription/portal` | POST | Stripe Customer Portal |
| `/api/subscription/webhook` | POST | Stripe Webhook受信 |
| `/api/organizations/` | GET, POST | 組織CRUD |
| `/api/organizations/[id]` | GET, PUT | 組織詳細・更新 |
| `/api/organizations/[id]/members` | GET, POST | メンバー管理 |
| `/api/organizations/[id]/members/[userId]` | DELETE | メンバー削除 |
| `/api/organizations/[id]/invitations` | GET, POST | 招待管理 |
| `/api/organizations/[id]/invitations/[invitationId]` | POST | 招待応答 |
| `/api/organizations/[id]/subscription` | GET | 組織サブスクリプション |
| `/api/articles/generation/create` | POST | 記事生成開始 |
| `/api/articles/generation/[processId]` | GET | 生成状態・スナップショット |
| `/api/companies/` | GET, POST | 会社情報 |
| `/api/companies/[id]` | GET, PUT | 会社詳細・更新 |
| `/api/companies/default` | GET | デフォルト会社 |
| `/api/companies/set-default` | POST | デフォルト設定 |
| `/api/admin/users` | GET | 管理者ユーザー一覧 |
| `/api/webhooks/clerk` | POST | Clerk Webhook |
| `/api/webhooks` | POST | 汎用Webhook |

---

## Database Tables (Supabase PostgreSQL)

### Core Tables
| Table | 概要 |
|-------|------|
| `users` | ユーザー情報 (RLS: 自身のみ参照/更新) |
| `organizations` | 組織 (id, name, owner_user_id, billing_user_id, stripe_customer_id) |
| `organization_members` | 組織メンバー (role: owner/admin/member) |
| `organization_invitations` | 組織招待 (email, token, status, expires_at) |
| `user_subscriptions` | 個人サブスクリプション (upgraded_to_org_id でチーム移行追跡) |
| `organization_subscriptions` | チームサブスクリプション (Stripe subscription ID = PK) |

### SEO Article Tables
| Table | 概要 |
|-------|------|
| `articles` | 記事本体 (user_id, title, content, status, generation_process_id) |
| `generated_articles_state` | 記事生成の状態管理 (Supabase Realtime対応) |
| `article_generation_flows` | 生成フロー定義 |
| `article_versions` | 記事バージョン履歴 |
| `article_contexts` | 生成コンテキスト (persona, theme, SERP, keywords) |
| `step_snapshots` | ステップスナップショット (チェックポイント復旧用) |
| `article_edit_versions` | AI編集バージョン |
| `article_agent_chat_sessions` | エージェントチャットセッション |

### Company & Style Tables
| Table | 概要 |
|-------|------|
| `company_info` | 会社情報 (name, usp, avoid_terms, target_area, is_default) |
| `style_guide_templates` | 文体テンプレート (tone, formality, sentence_length, heading/list/number_style) |

### Image Tables
| Table | 概要 |
|-------|------|
| `images` | 生成/アップロード画像 (gcs_url, image_type, alt_text, storage_type) |
| `image_placeholders` | 画像プレースホルダ (description_jp, prompt_en, status) |

### Blog Tables
| Table | 概要 |
|-------|------|
| `wordpress_sites` | WordPress接続サイト (site_url, mcp_endpoint, encrypted_credentials) |
| `blog_generation_state` | ブログ生成の状態管理 |

### System Tables
| Table | 概要 |
|-------|------|
| `agent_logs` | エージェント実行ログ |

### Migration History (30+ files)
初期化 → Clerk対応 → 組織 → フロー → 画像 → GCS → 会社情報 → スタイル → ログ → Realtime → スナップショット → ブランチ管理 → AI編集 → チャットセッション → サブスクリプション → WordPress → ブログ生成 → サブスクアップグレードサポート

---

## Authentication & Authorization

### 認証フロー
1. **Clerk** がフロントエンドのユーザー認証を管理 (Social Login, Email/Password, MFA)
2. **Next.js middleware** がルート保護と特権チェックを実行
3. バックエンドは **Clerk JWT** (RS256) をJWKSエンドポイント経由で検証
4. 管理者エンドポイントは **@shintairiku.jp** ドメインのメールを要求

### 特権ユーザーシステム
- `@shintairiku.jp` ドメインのユーザーは全機能にアクセス可能（サブスクリプション不要）
- 非特権ユーザーは `/blog/*`, `/settings/*`, `/help/*` のみアクセス可能
- 特権チェックは `middleware.ts` の `isPrivilegedOnlyRoute` で実施

### サブスクリプション
- **個人プラン**: ¥29,800/月 (Stripe)
- **チームプラン**: ¥29,800/席/月 (組織単位、2-50席)
- `SubscriptionGuard` コンポーネントがUI側でアクセス制御（`(tools)` レイアウト内のみ。`(settings)` は未課金でもアクセス可）
- `past_due` は3日間の猶予期間
- `canceled` は期間終了まで有効
- **個人→チーム移行**: `stripe.subscriptions.update()` で同一サブスク内の quantity 変更（日割り自動適用）
- 同一 Stripe Customer を個人・チームで共有（組織用に別Customer は作成しない）

---

## Key Architecture Decisions

### Backend: DDD/オニオンアーキテクチャ
- `domains/` にビジネスドメイン (seo_article, blog, organization, company, style_template, image_generation, admin)
- `infrastructure/` に外部API統合 (GCS, SerpAPI, Notion, Clerk, GCP認証)
- `common/` に横断的関心事 (認証, DB, スキーマ)
- `core/` にアプリケーション設定・例外処理

### Frontend: Feature-Based Architecture
- `features/` にドメイン単位のUI (landing, pricing, blog, article-generation, tools)
- `components/` に共通UI (shadcn/ui, display, layout)
- `hooks/` にビジネスロジック (Supabase Realtime, 記事生成, 自動保存)
- `lib/` にインフラ (ApiClient, サブスクリプション)

### Realtime State Management
- **Supabase Realtime** で記事生成の進捗をリアルタイム同期
- ポーリングは無効化（DBが信頼の源泉）
- イベント重複排除、原子的状態バリデーション
- `useArticleGenerationRealtime` フック (1,460+行) がフロントエンド側の全状態管理を担当

### API Proxy
- フロントエンドの `/api/proxy/[...path]` がバックエンドAPIにプロキシ
- `next.config.js` の `rewrites` でも `/api/proxy/:path*` → `${NEXT_PUBLIC_API_BASE_URL}/:path*`
- 120秒の拡張タイムアウト（長時間エージェント処理対応）

---

## AI Models Configuration

### Backend Model Settings (`app/core/config.py`)
| 用途 | 環境変数 | デフォルト値 |
|------|---------|------------|
| リサーチ | `RESEARCH_MODEL` | gpt-5-mini |
| 執筆 | `WRITING_MODEL` | gpt-4o-mini |
| アウトライン | `OUTLINE_MODEL` | WRITING_MODEL |
| 編集 | `EDITING_MODEL` | gpt-4o-mini |
| SERP分析 | `SERP_ANALYSIS_MODEL` | RESEARCH_MODEL |
| ペルソナ生成 | `PERSONA_MODEL` | WRITING_MODEL |
| テーマ生成 | `THEME_MODEL` | WRITING_MODEL |
| Agents SDK | `MODEL_FOR_AGENTS` | gpt-4o-mini |
| AI記事編集エージェント | `ARTICLE_EDIT_AGENT_MODEL` | gpt-5-mini |
| AI記事編集サービス | `ARTICLE_EDIT_SERVICE_MODEL` | gpt-4o |
| AIコンテンツ生成 | `AI_CONTENT_GENERATION_MODEL` | gpt-5-mini |
| ブログ生成 | `BLOG_GENERATION_MODEL` | gpt-5.2 |
| 画像生成 | `IMAGEN_MODEL_NAME` | imagen-4.0-generate-preview-06-06 |

---

## Environment Variables

### Backend (`backend/.env`)
```env
# CORS
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001

# AI
OPENAI_API_KEY=
GEMINI_API_KEY=
SERPAPI_API_KEY=

# Database
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=

# Auth
CLERK_SECRET_KEY=
CLERK_PUBLISHABLE_KEY=

# Stripe
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=

# Google Cloud / Vertex AI
GOOGLE_CLOUD_PROJECT=
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_SERVICE_ACCOUNT_JSON=

# Image Generation
IMAGEN_MODEL_NAME=imagen-4.0-generate-preview-06-06
IMAGEN_ASPECT_RATIO=4:3
IMAGE_STORAGE_PATH=./generated_images
GCS_BUCKET_NAME=

# Blog AI
BLOG_GENERATION_MODEL=gpt-5.2
CREDENTIAL_ENCRYPTION_KEY=
FRONTEND_URL=http://localhost:3000

# Tracing
OPENAI_AGENTS_ENABLE_TRACING=true

# Debug
DEBUG=false
```

### Frontend (`frontend/.env.local`)
```env
# Supabase
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=

# Clerk
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=
CLERK_SECRET_KEY=

# Stripe
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
STRIPE_PRICE_ID=

# Backend
NEXT_PUBLIC_API_BASE_URL=http://localhost:8080
NEXT_PUBLIC_SITE_URL=http://localhost:3000
NEXT_PUBLIC_APP_URL=http://localhost:3000
```

---

## Development Commands

### Backend
```bash
cd backend
uv sync                                              # 依存同期
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8080  # 開発サーバー起動
uv run pytest tests/                                  # テスト実行
uv run python -m ruff check app                       # Lint
```

### Frontend
```bash
cd frontend
bun install                                           # 依存インストール
bun run dev                                           # 開発サーバー (Turbopack)
bun run build                                         # 本番ビルド
bun run lint                                          # ESLint
bun run generate-types                                # Supabase型生成
bun run migration:up                                  # DBマイグレーション適用
```

### Database
```bash
supabase login                                        # CLIログイン
npx supabase link --project-ref <ref>                 # プロジェクトリンク
npx supabase db push                                  # マイグレーション適用
bun run generate-types                                # TypeScript型再生成
```

### Docker
```bash
docker compose up -d frontend_dev backend             # 開発環境起動
docker compose logs -f backend                        # ログ確認
# Frontend: http://localhost:3000, Backend: http://localhost:8008
```

---

## Deployment

### Backend
- **Dockerfile**: `python:3.12-slim` + `uv` でインストール
- **起動コマンド**: `uv run uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}`
- Cloud Run等のPORT環境変数に追従

### Frontend
- **Dockerfile**: Next.js `standalone` 出力 → `node server.js`
- **ポート**: 3000

### CI/CD
- **GitHub Actions**: `backend-docker-build.yml`
  - トリガー: `backend/` 配下の変更 (push/PR to main/develop)
  - Docker Buildx + キャッシュ
  - コンテナ起動テスト + HTTPリクエストテスト

---

## Git Branching
- **main**: 本番ブランチ
- **develop**: 開発ブランチ（現在のブランチ）
- PRは `develop` → `main`

---

## Design Rules

- **Font**: Noto Sans JP (weights: 400-700)
- **Primary Color**: custom-orange (#E5581C)
- **Light Color**: custom-orange-light (#FFF2ED)
- **Component Library**: shadcn/ui (Radix UI)
- **Animation**: Framer Motion
- **Icons**: Lucide React

---

## Stripe サブスクリプション設計知見

> **情報ソース**: Stripe公式ドキュメント (2026-02時点で調査)
> - https://docs.stripe.com/billing/subscriptions/prorations
> - https://docs.stripe.com/billing/subscriptions/upgrade-downgrade
> - https://docs.stripe.com/api/subscriptions/update
> - https://docs.stripe.com/api/subscriptions/cancel
> - https://docs.stripe.com/billing/subscriptions/cancel
> - https://docs.stripe.com/api/checkout/sessions/create
> - https://docs.stripe.com/billing/subscriptions/pending-updates

### 核心ルール
1. **Stripe Checkout は新規サブスク作成専用**。既存サブスクの変更（アップグレード・ダウングレード）はできない。
2. **プラン変更は `stripe.subscriptions.update()` を使う**。同一 Customer 上で items を更新すると、Stripe が自動的に日割り計算する。
3. **同一 Stripe Customer を使うべき**。Customer を分けると日割りクレジットが別Customer に滞留し適用されない。

### `proration_behavior` パラメータ (subscriptions.update)
| 値 | 動作 |
|---|---|
| `create_prorations` (デフォルト) | 日割りアイテム作成、次回請求に加算 |
| `always_invoice` | 日割りアイテム作成 + 即時請求/クレジット |
| `none` | 日割りなし |

### `prorate` パラメータ (subscriptions.cancel)
- **非推奨ではない** (2026年2月時点で有効)
- boolean値。`true` にすると未使用分のクレジットを顧客残高に付与
- **自動返金はしない**。返金するには Refund API を別途使用する必要がある

### `payment_behavior` パラメータ
| 値 | 動作 |
|---|---|
| `allow_incomplete` (デフォルト) | 支払い失敗 → `past_due` に遷移 |
| `pending_if_incomplete` | 支払い失敗 → 変更を保留。23時間で自動期限切れ |
| `error_if_incomplete` | 支払い失敗 → HTTP 402 エラーを返す |

### キャンセル方式
| 方式 | 動作 |
|---|---|
| `cancel_at_period_end: true` | 期末キャンセル。返金不要。**取り消し可能** |
| `stripe.subscriptions.cancel()` | 即時キャンセル。返金は手動 |
| `cancel_at: timestamp` | カスタム日時キャンセル。クレジット自動生成（返金不可、残高のみ） |

### `pending_if_incomplete` の制限事項
> **情報ソース**: https://docs.stripe.com/billing/subscriptions/pending-updates-reference
- `payment_behavior: 'pending_if_incomplete'` 使用時、同時に更新できるパラメータは **items, proration_behavior, proration_date, billing_cycle_anchor, trial_end** 等に限定される
- **`metadata` は同時更新不可**。items 更新と metadata 更新は2回に分けて `subscriptions.update()` を呼ぶ必要がある
- サポートされないパラメータを渡すと `StripeInvalidRequestError` が発生する

### `invoices.createPreview` によるプロレーション事前計算
> **情報ソース**: https://docs.stripe.com/api/invoices/create_preview
- `subscription` + `subscription_details.items` で quantity 変更後の請求額をプレビュー可能
- `subscription_details.proration_date` を渡すと正確なプロレーション計算ができる
- Stripe v18 では明細の `proration` フラグは `line.parent.subscription_item_details.proration` に移動

### 本プロジェクトでの適用
- **個人→チーム移行**: `subscriptions.update()` で quantity を 1→N に変更
- **パラメータ**: `proration_behavior: 'always_invoice'` + `payment_behavior: 'pending_if_incomplete'`
- **2段階更新**: items 更新（pending_if_incomplete）→ metadata 更新（別呼び出し）の順で実行
- **料金プレビュー**: アップグレード実行前に `invoices.createPreview()` で差額を表示する確認モーダルを挟む
- **結果**: 未使用分の個人プラン料金がクレジットとして差し引かれ、チームプランとの差額のみ即座に請求
- **Stripe Customer**: 個人もチームも同一 Customer を共有。`organizations.billing_user_id` で課金者を追跡

### orgオーナー離脱時
- Stripe はサブスクの Customer 変更を **許可していない**
- 旧オーナーの sub を `cancel_at_period_end: true` → 新オーナーの Customer で新 sub を `trial_end: 旧期末` で作成
- 初期は管理者手動対応

---

## セッション内の変更履歴 (2026-02-01)

### 1. ルートページ LP 廃止
- `middleware.ts`: `/` を public から削除。未ログイン→`/auth`、ログイン済み→`/blog/new` にリダイレクト
- `frontend/src/app/auth/page.tsx`: sign-in / sign-up 選択画面を新規作成
- LP ファイル群 `(marketing)/page.tsx` はファイルとして残存（リダイレクトにより実質無効化）

### 2. フォント変更
- Montserrat + Montserrat Alternates → **Noto Sans JP** に変更
- `layout.tsx`, `tailwind.config.ts` を更新。`font-sans` / `font-alt` ともに Noto Sans JP を参照

### 3. サブスクリプション アップグレード改修 (Stripe公式推奨)
- **新規**: `frontend/src/app/api/subscription/upgrade-to-team/route.ts`
  - `stripe.subscriptions.update()` で既存サブスクの quantity を変更（日割り自動）
  - `proration_behavior: 'always_invoice'`, `payment_behavior: 'pending_if_incomplete'`
- **改修**: `checkout/route.ts` — 個人サブスク契約中のチーム購入は 409 で upgrade-to-team へ誘導。新規チームは同一 Customer を使用
- **改修**: `webhook/route.ts` — 個人サブスクキャンセル処理を削除。subscription 更新時に org 遷移をハンドル
- **改修**: `pricing/page.tsx` — アップグレード時は API 直接呼び出し（Checkout リダイレクトなし）。日割り説明に更新
- **DB**: `20260201000001_subscription_upgrade_support.sql`
  - `organizations.billing_user_id` (text) — 課金ユーザー追跡
  - `user_subscriptions.upgraded_to_org_id` (uuid) — チーム移行追跡
- **NOTE**: マイグレーション適用前は Supabase 型定義に新カラムが含まれないため、`Record<string, unknown>` 型アサーションで対応中。`bun run generate-types` で型再生成が必要

### 4. アップグレード確認モーダル & Stripeエラー修正
- **新規**: `frontend/src/app/api/subscription/preview-upgrade/route.ts`
  - `stripe.invoices.createPreview()` で日割り差額を事前計算するAPI
  - プロレーション明細（クレジット・新料金）と合計請求額を返却
- **改修**: `pricing/page.tsx` — アップグレードボタン押下時に即時決済せず、確認モーダルを表示
  - プレビューAPIで差額取得 → モーダルに明細表示 → ユーザー確認後に実行
  - `Dialog` コンポーネント使用、プラン変更サマリー・料金明細・合計額を表示
- **修正**: `upgrade-to-team/route.ts`
  - `pending_if_incomplete` と `metadata` の同時更新はStripe非対応 → `subscriptions.update()` を2回に分離
  - エラーハンドリング: `error.message.includes('pending')` → Stripeエラー型による正確な判定に変更
- **修正**: `portal/route.ts`
  - `NEXT_PUBLIC_APP_URL` 未設定時のフォールバック `http://localhost:3000` を追加

### 5. チームプラン シート数変更機能
- **新規**: `frontend/src/app/api/subscription/update-seats/route.ts`
  - `stripe.subscriptions.update()` で既存チームプランの quantity を変更
  - owner/admin のみ実行可能（role チェック）
  - 増減両方に対応。日割り自動適用（`always_invoice` + `pending_if_incomplete`）
- **改修**: `frontend/src/app/api/subscription/preview-upgrade/route.ts`
  - 個人→チームのアップグレードプレビューに加え、チームプラン内のシート変更プレビューにも対応
  - チームプランが存在する場合は `organization_subscriptions` 経由でプレビュー
- **改修**: `pricing/page.tsx`
  - 「現在のプラン」カードにシート数変更UI追加（Select + 変更ボタン）
  - シート変更確認モーダル: プレビュー → 明細表示 → 確認後に実行
  - シート削減時はクレジット表示（次回請求から差し引き）

### 6. Pricing → Settings/Billing 移行
- **新規**: `frontend/src/app/(settings)/layout.tsx`
  - `(tools)` レイアウトと同じだが **`SubscriptionGuard` なし**。`SubscriptionProvider` + `AppLayoutClient` + `SubscriptionBanner` のみ
  - 未課金ユーザーも `/settings/*` にアクセス可能に
- **移動**: `(tools)/settings/*` → `(settings)/settings/*`
  - `account`, `billing`, `members`, `integrations/*` すべて移動
  - URL パスは変更なし（Next.js route group はURLに影響しない）
  - `(tools)/settings/` ディレクトリは削除
- **リライト**: `frontend/src/app/(settings)/settings/billing/page.tsx`
  - 旧 pricing ページ (999行) の全機能を統合した請求&プラン管理ページ
  - プラン選択タブ、シート数セレクター、Checkout フロー、アップグレード確認モーダル、シート変更確認モーダル、FAQ、Stripe Portal
  - `successUrl`/`cancelUrl` を `/settings/billing?subscription=...` に変更
  - 現在のプラン状態表示（ステータスバッジ、期間情報、シート変更UI）
- **変換**: `frontend/src/app/(marketing)/pricing/page.tsx`
  - 999行 → サーバーコンポーネントのリダイレクト（認証済み→`/settings/billing`、未認証→`/auth`）
- **更新**: 全 `/pricing` 参照を `/settings/billing` に変更
  - `subscription-guard.tsx` (redirectTo, バナーリンク)
  - `members/page.tsx` (チームプラン購入ボタン)
  - `checkout/route.ts` (デフォルト cancelUrl)
  - `navigation.tsx` (モバイルナビ)
  - `sidebar.tsx` (サイドバーリンク)
- **修正**: `auth/page.tsx` — ESLint import順序エラー修正

---

## 自己改善ログ

> ユーザーから指摘された失敗・判断ミス・非効率を記録し、同じ過ちを繰り返さないための学習記録。

### 2026-02-01
- **Next.js キャッシュ問題**: フォント変更後に `.next` キャッシュが古いビルドを参照し `montserrat is not defined` エラーが発生。ファイル内容は正しかったが `.next` 削除+再起動が必要だった。コード変更後にランタイムエラーが出た場合は、まずキャッシュクリアを確認すべき。
- **Stripe 設計の初期実装ミス**: 個人と組織で別々の Stripe Customer を作成する設計は、Stripe 公式の推奨に反していた。日割りクレジットが別 Customer に滞留し実質機能しない問題があった。**外部 API 連携の設計時は、必ず公式ドキュメントの推奨パターンを先に調査すべき。**
- **Stripe `pending_if_incomplete` の制限見落とし**: `payment_behavior: 'pending_if_incomplete'` と `metadata` を同時に渡して `StripeInvalidRequestError` が発生。**Stripe APIパラメータの組み合わせ制限は公式ドキュメント (pending-updates-reference) で事前に確認すべき。**
- **環境変数フォールバック不足**: `NEXT_PUBLIC_APP_URL` 未設定で Portal の `return_url` が空文字列になりStripeエラー。**環境変数を使うURLは必ずフォールバック値を設定すべき。**
- **即時決済のUX問題**: アップグレードボタン押下で即座に決済が走る実装は、ユーザーに確認の余地がなかった。**課金を伴うアクションは必ず確認ステップを挟むべき。** `invoices.createPreview()` でプレビューを見せてから実行する設計が適切。
- **ビルドコマンド**: フロントエンドのビルドは `bun run build` を使う。`npx next build` ではなく。`.next` キャッシュの削除は通常不要（ルートグループ変更時等の特殊ケースのみ）。
- **記憶の更新忘れ**: 作業完了後は必ず CLAUDE.md を更新する。ユーザーに言われる前に自主的に行うべき。

---

> ## **【最重要・再掲】記憶の更新は絶対に忘れるな**
> **このファイルの冒頭にも書いたが、改めて念押しする。**
> 作業が完了したら、コミットする前に、必ずこのファイルに変更内容を記録せよ。
> 新しいファイルを作成した、既存ファイルを変更した、設計を変更した、バグを見つけた、知見を得た — すべて記録対象。
> **「後で更新しよう」は禁止。今すぐ更新せよ。**
