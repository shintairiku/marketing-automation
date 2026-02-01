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
- **Payment**: Stripe (@stripe/stripe-js v8, stripe v20)
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
| GET | `/admin/stats/overview` | ダッシュボードKPI統計 |
| GET | `/admin/stats/generation-trend` | 記事生成日別推移 |
| GET | `/admin/stats/subscription-distribution` | プラン別ユーザー分布 |
| GET | `/admin/activity/recent` | 直近アクティビティ |
| GET | `/admin/usage/users` | ユーザー別使用量一覧 |

### Usage (`/usage`)
| Method | Path | 概要 |
|--------|------|------|
| GET | `/usage/current` | 現在のユーザー使用量 |
| GET | `/usage/admin/stats` | 管理者用使用量統計 |
| GET | `/usage/admin/users` | 管理者用ユーザー別使用量 |

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

### Usage & Plan Tables
| Table | 概要 |
|-------|------|
| `plan_tiers` | プラン定義マスタ (id, name, stripe_price_id, monthly_article_limit, addon_unit_amount, price_amount) |
| `usage_tracking` | 利用量追跡 (user_id, organization_id, billing_period, articles_generated, articles_limit, addon_articles_limit) |
| `usage_logs` | 使用量監査ログ (usage_tracking_id, user_id, generation_process_id) |

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
STRIPE_PRICE_ADDON_ARTICLES=          # アドオン記事追加 Price ID

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

### 7. サイドバー整理
- **ファイル**: `frontend/src/components/constant/route.ts`
- Blog グループから「連携設定」セクション（WordPress連携リンク）を削除 — WordPress連携は Settings のみに集約
- Settings「メンバー設定」→「チームメンバー設定」に文言変更
- Settings「ワードプレス連携設定」→「WordPress連携設定」に文言変更
- Settings から Instagram連携設定・LINE連携設定を削除（disabled だったものを完全除去）

### 8. 全依存パッケージ一括アップデート
#### Frontend (bun)
- `@clerk/nextjs` 6.37.0 → 6.37.1
- `@react-email/components` 0.0.36 → 1.0.6 (MAJOR)
- `@react-email/tailwind` 1.2.2 → 2.0.3 (MAJOR)
- `@stripe/stripe-js` 2.4.0 → 8.7.0 (MAJOR)
- `@supabase/ssr` 0.5.2 → 0.8.0 (MAJOR)
- `lucide-react` 0.474.0 → 0.563.0
- `react` / `react-dom` 19.2.1 → 19.2.4
- `stripe` 18.5.0 → 20.3.0 (MAJOR)
- `tailwind-merge` 2.6.0 → 2.6.1 (v3はTailwind CSS v4専用のためダウングレード)
- `next-route-handler-pipe` 1.0.5 → 2.0.0 (MAJOR)
- `@types/react` 19.0.4 → 19.2.10, `@types/react-dom` 19.0.2 → 19.2.3
- `prettier` 2.8.8 → 3.8.1, `prettier-plugin-tailwindcss` 0.3.0 → 0.7.2 (MAJOR)
- `eslint-config-prettier` 8.10.2 → 10.1.8, `eslint-plugin-simple-import-sort` 10.0.0 → 12.1.1 (MAJOR)
- `env-cmd` 10.1.0 → 11.0.0, `supabase` 2.72.9 → 2.74.5, `autoprefixer` 10.4.23 → 10.4.24
- **据え置き**: Next.js 15 (16は設定形式変更)、Tailwind 3 (4はCSS設定方式)、ESLint 8 (9はflat config)、Zod 3 (4はAPI変更)
- **ダウングレード**: `tailwind-merge` v3→v2.6.1 (v3はTailwind CSS v4専用。プロジェクトはTW v3なのでv2系が必須)

#### Backend (uv)
- `fastapi` 0.116.2 → 0.128.0
- `openai` 1.108.0 → 2.16.0 (MAJOR)
- `openai-agents` 0.3.0 → 0.7.0
- `pillow` 11.3.0 → 12.1.0 (MAJOR)
- `numpy` 1.26.4 → 2.4.2 (MAJOR — pyproject.toml の <2.0.0 制約を解除)
- `google-cloud-storage` 2.19.0 → 3.8.0 (MAJOR — <3.0.0 制約を解除)
- `google-cloud-aiplatform` 1.114.0 → 1.135.0
- `supabase` 2.19.0 → 2.27.2, `uvicorn` 0.35.0 → 0.40.0, `starlette` 0.48.0 → 0.50.0
- `google-generativeai`: FutureWarning が出る（`google.genai` への移行推奨）。機能的には問題なし
- pyproject.toml のバージョン制約をすべて解除（ピンなしに変更）
- **NOTE**: `google.generativeai` は非推奨。将来 `google.genai` に移行が必要

### 10. Blog AI 利用上限システム + 管理者ダッシュボード改善

#### 利用上限システム（Phase 1-5）

**設計方針**: Stripe Billing Meters（従量課金向け）ではなく、Supabase DBでのアプリ側追跡を採用。ハードキャップモデル（上限で生成不可）のため。

**DB マイグレーション**: `shared/supabase/migrations/20260202000001_add_usage_limits.sql`
- `plan_tiers` テーブル: プラン定義マスタ（id, name, stripe_price_id, monthly_article_limit, addon_unit_amount）
- `usage_tracking` テーブル: 利用量追跡（user_id, organization_id, billing_period_start/end, articles_generated, articles_limit, addon_articles_limit）
- `usage_logs` テーブル: 監査ログ
- `increment_usage_if_allowed()` PostgreSQL関数: FOR UPDATE ロックで原子的インクリメント
- `user_subscriptions` に `plan_tier_id` カラム追加
- `organization_subscriptions` に `plan_tier_id`, `addon_quantity` カラム追加
- RLS ポリシー設定
- デフォルトティア: 30記事/月, アドオン1ユニット=20記事, ¥29,800

**バックエンド新規ドメイン**: `backend/app/domains/usage/`
- `service.py` — UsageLimitService（check_can_generate, record_success, get_current_usage, recalculate_limits, create_tracking_for_period）
- `endpoints.py` — `GET /usage/current`, `GET /usage/admin/stats`, `GET /usage/admin/users`
- `schemas.py` — UsageInfo, UsageLimitResult, AdminUsageStats, AdminUserUsage
- `backend/app/api/router.py` にusageルーター追加

**Blog生成への統合**:
- `backend/app/domains/blog/endpoints.py` — 生成開始前に `check_can_generate()` → 429エラー
- `backend/app/domains/blog/services/generation_service.py` — 生成成功時（`_process_result`）に `record_success()` 呼び出し
- カウント対象: Blog AIのみ（SEO記事は対象外）、成功時のみカウント

**Stripeアドオン対応**:
- `frontend/src/app/api/subscription/addon/route.ts` (新規) — POST: アドオン quantity 変更、既存サブスクに追加ラインアイテムとして追加
- `frontend/src/app/api/subscription/webhook/route.ts` (改修) — `invoice.payment_succeeded` で使用量リセット、`customer.subscription.updated` でアドオン検出+上限再計算
- 環境変数: `STRIPE_PRICE_ADDON_ARTICLES` を `.env` に追加が必要

**フロントエンド利用上限UI**:
- `frontend/src/lib/subscription/index.ts` — `UsageInfo` インターフェース、`ADDON_PRICE_ID` エクスポート追加
- `frontend/src/components/subscription/subscription-guard.tsx` — `usage: UsageInfo | null` をコンテキストに追加
- `frontend/src/app/api/subscription/status/route.ts` — レスポンスに `usage` フィールド追加（Supabase usage_tracking から直接取得）
- `frontend/src/components/subscription/usage-progress-bar.tsx` (新規) — プログレスバーコンポーネント（compact/normal モード、色分け表示）
- `frontend/src/app/(settings)/settings/billing/page.tsx` — 使用量表示セクション + アドオン管理UI追加（+/-ボタンでquantity変更）
- `frontend/src/app/(tools)/blog/new/page.tsx` — 残り記事数表示、上限到達時の生成ボタン無効化、429レスポンスハンドリング

#### 管理者ダッシュボード改善（Phase 6-7）

**バックエンド管理者API拡充**: `backend/app/domains/admin/`
- `schemas.py` — OverviewStats, DailyGenerationCount, GenerationTrendResponse, SubscriptionDistribution, RecentActivity, UserUsageItem 等追加
- `service.py` — get_overview_stats(), get_generation_trend(), get_subscription_distribution(), get_recent_activity(), get_users_usage() メソッド追加
- `endpoints.py` — 以下のエンドポイント追加:
  | GET | `/admin/stats/overview` | ダッシュボードKPI統計 |
  | GET | `/admin/stats/generation-trend` | 記事生成日別推移 |
  | GET | `/admin/stats/subscription-distribution` | プラン別ユーザー分布 |
  | GET | `/admin/activity/recent` | 直近アクティビティ |
  | GET | `/admin/usage/users` | ユーザー別使用量一覧 |

**フロントエンド管理者ダッシュボード**:
- `frontend/src/app/(admin)/admin/page.tsx` — 全面リライト
  - KPIカード4つ（総ユーザー数、有料会員、月間記事生成、推定MRR）
  - recharts v3.7.0 によるエリアチャート（記事生成30日推移）
  - recharts ドーナツチャート（プラン別ユーザー分布）
  - 最近のアクティビティリスト
  - 上限に近いユーザー一覧（70%以上をハイライト）
  - ローディングスケルトン、エラーリトライ対応
- **新規依存**: `recharts` v3.7.0 (frontend package.json)

**NOTE**:
- Supabase型定義は `usage_tracking`, `plan_tiers`, `usage_logs` テーブル + `addon_quantity`, `plan_tier_id`, `upgraded_to_org_id` カラム追加後に `bun run generate-types` で再生成が必要
- DBマイグレーション適用前は一部TSエラーが出る（`usage_tracking` テーブル未認識等）が、`Record<string, unknown>` 型アサーションで回避中

### 9. Stripe v18→v20 破壊的変更対応
- **問題**: Stripe SDK v18 (Basil API `2025-03-31.basil`) で `current_period_start` / `current_period_end` が `Subscription` レベルから `subscription.items.data[0]` (SubscriptionItem) に移動
- **影響**: 旧コードは `StripeSubscriptionWithPeriod` というカスタム型拡張で `subscription.current_period_start` を読んでいたが、v18+では `undefined` になり `|| new Date().toISOString()` フォールバックが常時発火 → **サブスクリプション期間が常に現在時刻になるバグ**
- **修正**: `frontend/src/features/account/controllers/upsert-user-subscription.ts`
  - `StripeSubscriptionWithPeriod` インターフェース削除
  - `as unknown as StripeSubscriptionWithPeriod` キャスト削除
  - `subscription.items.data[0].current_period_start` / `current_period_end` から読み取るように変更
  - 未使用の `toDateTime` インポート削除
- **修正**: `frontend/src/app/api/webhooks/route.ts`
  - `StripeSubscriptionWithPeriod` インターフェース削除
  - `as unknown as StripeSubscriptionWithPeriod` → `as Stripe.Subscription` に変更
- **Webhook形式**: `stripe.webhooks.constructEvent()` は v18-v20 で変更なし。安全
- **`@stripe/stripe-js` v2→v8**: TypeScript型更新のみ。`loadStripe` は常にCDN最新版を読むため実質影響なし
- **情報ソース**: https://github.com/stripe/stripe-node/blob/master/CHANGELOG.md

### 10. 利用上限システム実装 (Phase 1-7)

#### Phase 1-2: DB + バックエンド基盤
- **新規**: `shared/supabase/migrations/20260202000001_add_usage_limits.sql`
  - `plan_tiers` テーブル（プラン定義マスタ: monthly_article_limit, addon_unit_amount）
  - `usage_tracking` テーブル（利用量追跡: articles_generated, articles_limit, addon_articles_limit）
  - `usage_logs` テーブル（監査ログ）
  - `increment_usage_if_allowed()` PostgreSQL関数（FOR UPDATE ロックで原子的インクリメント）
  - `user_subscriptions` に `plan_tier_id`, `addon_quantity` カラム追加
  - `organization_subscriptions` に `plan_tier_id`, `addon_quantity` カラム追加
  - RLSポリシー設定
- **新規**: `backend/app/domains/usage/` ドメイン
  - `service.py` — UsageLimitService (check_can_generate, record_success, get_current_usage, recalculate_limits, create_tracking_for_period)
  - `endpoints.py` — `GET /usage/current`
  - `schemas.py` — UsageInfo, UsageLimitResult
- **改修**: `backend/app/api/router.py` — usageルーター追加

#### Phase 2: Blog生成への統合
- **改修**: `backend/app/domains/blog/endpoints.py` — 生成開始前に `check_can_generate()` → 429エラー
- **改修**: `backend/app/domains/blog/services/generation_service.py` — 成功時に `record_success()` 呼び出し

#### Phase 3-4: Stripeアドオン + Webhookリセット
- **新規**: `frontend/src/app/api/subscription/addon/route.ts` — アドオン管理API (POST)
  - Stripeサブスクに追加ラインアイテムとしてアドオン追加/変更/削除
  - DB (`user_subscriptions`/`organization_subscriptions`) の `addon_quantity` 更新
  - `usage_tracking.addon_articles_limit` の即時更新
- **改修**: `frontend/src/app/api/subscription/webhook/route.ts`
  - `invoice.payment_succeeded` で新請求期間のusage_trackingレコード作成（リセット）
  - `customer.subscription.updated` でアドオン変更検出 → 上限再計算
  - 個人サブスクの `addon_quantity` も保存するように修正

#### Phase 5: フロントエンドUI（利用上限）
- **改修**: `frontend/src/components/subscription/subscription-guard.tsx` — UsageInfo型追加、usage state管理
- **改修**: `frontend/src/app/api/subscription/status/route.ts` — usage_tracking情報をレスポンスに追加
- **改修**: `frontend/src/app/(settings)/settings/billing/page.tsx` — 使用量プログレスバー + アドオン管理UI追加
- **改修**: `frontend/src/app/(tools)/blog/new/page.tsx` — 残り記事数表示 + 上限到達時生成ボタン無効化

#### Phase 6-7: 管理者ダッシュボード + API
- **依存追加**: `recharts` v3.7.0 (`bun add recharts`)
- **改修**: `backend/app/domains/admin/schemas.py` — OverviewStats, GenerationTrendResponse, SubscriptionDistribution, RecentActivity, UserUsageItem, UserDetailResponse 等追加
- **改修**: `backend/app/domains/admin/service.py` — get_overview_stats, get_generation_trend, get_subscription_distribution, get_recent_activity, get_users_usage, get_user_detail メソッド追加
- **改修**: `backend/app/domains/admin/endpoints.py` — 5つの統計エンドポイント + ユーザー詳細エンドポイント追加
- **全面リライト**: `frontend/src/app/(admin)/admin/page.tsx` — KPIカード(4)、AreaChart(30日推移)、PieChart(サブスク分布)、アクティビティリスト、上限近接ユーザーリスト
- **新規**: `frontend/src/app/(admin)/admin/users/[userId]/page.tsx` — ユーザー詳細ページ（使用量、サブスク、Stripe情報、組織情報、生成履歴テーブル）
- **改修**: `frontend/src/app/(admin)/admin/users/page.tsx` — テーブル行に「詳細」リンク追加

#### バグ修正
- **組織メンバー使用量帰属**: `upgraded_to_org_id` が null の組織メンバー（招待経由）の使用量が取得できない問題。`organization_members` テーブルのフォールバック検索を3箇所に追加 (`usage/endpoints.py`, `blog/endpoints.py`, `blog/services/generation_service.py`)
- **個人addon_quantity未保存**: `user_subscriptions` テーブルに `addon_quantity` カラムがなかった。マイグレーションに追加。Webhook・addon APIで保存するように修正
- **usage_tracking即時更新**: アドオンAPI実行時に `usage_tracking.addon_articles_limit` も即時更新するように修正
- **ゼロ除算防止**: blog/new のプログレスバーで `total_limit` が0の場合の除算を防止

#### 設定方法
- **プラン記事上限**: `plan_tiers` テーブルの `monthly_article_limit` を更新（例: 30 → 50）
- **アドオン単位記事数**: `plan_tiers` テーブルの `addon_unit_amount` を更新（例: 20 → 30）
- **新ティア追加**: `plan_tiers` に新行を INSERT + Stripe で新 Price 作成
- **環境変数**: `STRIPE_PRICE_ADDON_ARTICLES` にアドオン用の Stripe Price ID を設定

### 11. マルチティア対応 + 管理画面からのプラン設定

#### Part A: バックエンド plan_tiers CRUD API
- **`backend/app/domains/admin/schemas.py`** — `PlanTierRead`, `CreatePlanTierRequest`, `UpdatePlanTierRequest`, `PlanTierListResponse`, `ApplyLimitsResult` スキーマ追加
- **`backend/app/domains/admin/service.py`** — `get_all_plan_tiers()`, `create_plan_tier()`, `update_plan_tier()`, `delete_plan_tier()` (参照チェック付き), `apply_tier_to_active_users()` (全アクティブ usage_tracking の上限を再計算) メソッド追加
- **`backend/app/domains/admin/endpoints.py`** — 5エンドポイント追加:
  | Method | Path | 概要 |
  |--------|------|------|
  | GET | `/admin/plan-tiers` | 全ティア一覧 |
  | POST | `/admin/plan-tiers` | 新規ティア作成 (ID重複チェック, 201) |
  | PATCH | `/admin/plan-tiers/{tier_id}` | ティア更新 (変更フィールドのみ) |
  | DELETE | `/admin/plan-tiers/{tier_id}` | ティア削除 (usage_tracking/user_subscriptions参照中は409) |
  | POST | `/admin/plan-tiers/{tier_id}/apply` | 全アクティブユーザーに即時反映 |

#### Part B: ハードコード 'default' 修正 (マルチティア対応の核心)
- **`frontend/src/app/api/subscription/webhook/route.ts`** — `resolvePlanTierId()` ヘルパー関数追加: Stripe subscription の base item price.id を `plan_tiers.stripe_price_id` で逆引き → 正しい `plan_tier_id` を返す（フォールバック 'default'）
  - `handleSubscriptionChange()`: `plan_tier_id` を解決し、`user_subscriptions`/`organization_subscriptions` に書き込み
  - `createUsageTrackingForNewPeriod()`: ハードコード `.eq('id', 'default')` → `resolvePlanTierId()` 結果に置換
  - `recalculateUsageLimits()`: `planTierId` パラメータ追加、ハードコード置換
- **`frontend/src/app/api/subscription/addon/route.ts`** — ハードコード `.eq('id', 'default')` → `user_subscriptions.plan_tier_id` から取得した値に置換。`Stripe` 型 import 追加
- **型安全性**: `usage_tracking`, `plan_tiers` テーブル + `plan_tier_id`, `addon_quantity` カラムが Supabase 型定義未生成のため `(supabase as any)` キャストで対応中

#### Part C: フロントエンド管理画面
- **`frontend/src/app/(admin)/admin/layout.tsx`** — ナビに「プラン設定」追加 (`Layers` アイコン)
- **`frontend/src/app/(admin)/admin/plans/page.tsx`** (新規) — プラン管理ページ
  - テーブル: ID, 名前, Stripe Price ID, 月間上限, アドオン単位, 月額, 表示順, ステータス
  - 新規作成/編集ダイアログ、削除確認、即時反映確認
  - ステータスバッジクリックで有効/無効切り替え

#### Part D: 使用量表示修正（新規サブスク時に usage_tracking が未作成の問題）

**根本原因**: 新規サブスク契約時のフロー:
1. `checkout.session.completed` → usage_tracking 作成なし
2. `customer.subscription.created` → `recalculateUsageLimits()` は UPDATE のみ（レコードがないので何も起きない）
3. 初回の `invoice.payment_succeeded` (`billing_reason='subscription_cycle'`) まで usage_tracking が作成されない
4. → `/api/subscription/status` が `usage = null` を返し、フロントエンドで使用量が非表示に

**修正箇所**:
1. **Webhook** (`webhook/route.ts`): `recalculateUsageLimits` → `ensureUsageTracking` にリネーム。UPDATE のみ → UPSERT（既存レコードがなければ INSERT）に変更
2. **Status API** (`status/route.ts`): `usage_tracking` が null でもサブスクがアクティブなら `plan_tiers` のデフォルト値でフォールバック usage を返す
3. **Billing ページ** (`billing/page.tsx`): 使用量表示条件から `hasAnyPlan` を削除（`!isPrivileged && subStatus?.usage` のみで判定）

#### 型生成前の注意
- `bun run generate-types` 実行後、`(supabase as any)` キャストを通常の型付きクエリに戻す必要あり
- `frontend/src/app/api/subscription/status/route.ts` も `usage_tracking` クエリに `any` キャスト追加（ビルドエラー回避）

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
- **tailwind-merge v3 非互換**: `tailwind-merge` v3 は Tailwind CSS v4 専用。Tailwind CSS v3 プロジェクトでは v2.6.x を使うこと。`bg-gradient-to-*` 等の競合解決が壊れる。**メジャーバージョンアップ時は、同じエコシステム内の他パッケージとの互換性も必ず確認すべき。**
- **openai-agents 0.7.0 注意点**: `nest_handoff_history` デフォルトが `True`→`False` に変更。ハンドオフ使用時は明示的に `True` を渡す必要がある可能性。GPT-5.1/5.2 のデフォルト reasoning effort が `'none'` に変更されたためブログ生成品質に影響する可能性あり（要テスト）。
- **ハードコード問題の見落とし**: プラン管理機能の設計時、最初の調査が浅く `plan_tier_id` が5箇所でハードコードされている問題を見逃した。ユーザーに「ちゃんとデータの整合性とれてる？」と指摘されて初めて深い調査を実施。**新機能の設計時は、関連する全データフロー（Webhook → DB → API → UI）を最初に網羅的に調査すべき。**
- **Supabase 型定義未生成による連鎖的ビルドエラー**: `plan_tiers`, `usage_tracking` テーブルが型に含まれていないため、`(supabase as any)` キャストが大量に必要になった。**新テーブル追加後は早期に `bun run generate-types` を実行し、型安全性を確保すべき。**
- **使用量表示の調査不足**: ユーザーに「使用量が全く表示されていない」と指摘されるまで、新規サブスクリプション時に `usage_tracking` が作成されない問題に気づかなかった。最初は特権ユーザーの条件のみ疑ったが、実際は全ユーザーに影響する根本的なデータフロー問題だった。**機能を実装したら、新規ユーザーが初めて使うフロー（契約直後の状態）を必ず検証すべき。UPDATE のみで INSERT がないのは典型的な初期化漏れ。**

### 12. Blog AI 画像入力機能

**概要**: Blog AIに2つのユースケースで画像入力を追加。初期入力（`/blog/new`）で画像添付、質問フェーズ（`/blog/[processId]`）でエージェントが画像を要求可能に。

**設計の核心**: エージェントがBase64に触れない `upload_user_image_to_wordpress` 複合ツール
- エージェントは `image_index` と `alt` テキストだけ渡す
- バックエンドが内部でファイル読み込み→Base64→MCP送信を完結
- 戻り値は `{media_id, url, width, height}` の小さなJSON
- Base64をツール出力/入力に載せるとトークンコストが爆発する問題を回避

**画像のエージェントへの入力**: OpenAI Responses API の `input_image` 型
```python
[{"role": "user", "content": [
    {"type": "input_text", "text": "リクエスト..."},
    {"type": "input_image", "image_url": "data:image/webp;base64,..."}
]}]
```

**WebP変換**: WordPress MCPプラグインは変換しないため、バックエンドでPillow変換してから保存

**変更ファイル一覧**:

| ファイル | 変更種別 | 概要 |
|---------|---------|------|
| `backend/app/domains/blog/services/image_utils.py` | **新規** | Pillow WebP変換ユーティリティ (convert_and_save_as_webp, read_as_base64, read_as_data_uri, cleanup_process_images) |
| `backend/app/domains/blog/services/wordpress_mcp_service.py` | 改修 | `_current_process_id` contextvar追加、`set_mcp_context()` に process_id 引数追加 |
| `backend/app/domains/blog/agents/tools.py` | 改修 | `upload_user_image_to_wordpress` 複合ツール追加、`ask_user_questions` に `input_types` 引数追加 |
| `backend/app/domains/blog/agents/definitions.py` | 改修 | プロンプトに画像活用セクション追加 |
| `backend/app/domains/blog/endpoints.py` | 改修 | `/generation/start` を multipart/form-data 対応、`/upload-image` にWebP変換追加 |
| `backend/app/domains/blog/schemas.py` | 改修 | `AIQuestion.input_type` に `image_upload` 追加 |
| `backend/app/domains/blog/services/generation_service.py` | 改修 | `_build_input_message()` / `_build_user_answer_message()` でマルチモーダル入力対応 |
| `frontend/src/app/(tools)/blog/new/page.tsx` | 改修 | 画像選択UI追加（最大5枚、プレビュー、FormData送信） |
| `frontend/src/app/(tools)/blog/[processId]/page.tsx` | 改修 | `image_upload` 質問タイプのファイルアップロードUI追加 |

**エンドポイント変更**:
- `POST /blog/generation/start`: JSON body → multipart/form-data (user_prompt, wordpress_site_id, reference_url?, files[])
- `POST /blog/generation/{process_id}/upload-image`: WebP変換追加

**技術的知見**:
- OpenAI Agents SDK `Runner.run_streamed()` は `input` に `[{role, content: [{input_text}, {input_image}...]}]` リスト形式を受け付ける
- `previous_response_id` 使用時もマルチモーダルリストをそのまま渡せる
- contextvars で process_id をエージェントツールに渡す（スレッドセーフ）
- WordPress MCP の `wp-mcp-upload-media` は `source` に Base64 data URI を受け付け、`filename` の拡張子でフォーマットが決まる

---

### 13. Blog AI コスト/ログ調査メモ (2026-02-01)

- **agent_log_sessions.article_uuid は実質 process_id 用途**: `backend/app/domains/seo_article/services/_generation_flow_manager.py` で `article_uuid=process_id` として既に運用されている（FKは削除済み）。Blog AI でも `process_id` を流用可能。
- **SEO記事のログ実装は未完成**: `log_agent_execution()` がダミーで実ログ記録なし。`_generation_utils.py` に `extract_token_usage_from_result()` / `log_tool_calls()` があるが、呼び出し元がほぼ無い。
- **Blog AI はトークン/コスト未記録**: `backend/app/domains/blog/services/generation_service.py` は `Runner.run_streamed()` の usage を保存していない。`blog_generation_state.response_id` は未使用で、実際は `blog_context.last_response_id` に保存している。
- **ツール呼び出しの集約ポイント**: Blog AI の WordPressツールは全て `call_wordpress_mcp_tool()` 経由（`backend/app/domains/blog/services/wordpress_mcp_service.py`）。ここが tool_call_logs などのフック候補。

### 14. Blog AI コスト/ログ実装 (2026-02-01)

- **Blog AI の LLMログ連携を実装**: `backend/app/domains/blog/services/generation_service.py` にログセッション作成・実行ログ・LLM呼び出しログ・ツール呼び出しログを追加。`agent_log_sessions.article_uuid` に `process_id` を保存（既存SEOと同方式）。
- **使用量抽出ロジック**: Agents SDK `request_usage_entries` → 正規化 → 集計。取得不可の場合は `raw_responses` から usage を抽出してフォールバック。
- **ツールログ**: `ToolCallItem`/`ToolCallOutputItem` をストリーミングで捕捉し `tool_call_logs` を作成/更新。
- **管理画面に Blog AI 使用量を追加**:
  - `backend/app/domains/admin/schemas.py` に `BlogAiUsageStats` 追加
  - `backend/app/domains/admin/service.py` が `agent_log_sessions/llm_call_logs/tool_call_logs` を集計
  - `frontend/src/app/(admin)/admin/users/[userId]/page.tsx` に Blog AI 使用量カード追加
- **モデル料金更新**: `backend/app/infrastructure/analysis/cost_calculation_service.py` に GPT‑5/5.1/5.2/mini/nano/pro の料金を追加。推論トークンの二重課金を避けるガードを追加。


> ## **【最重要・再掲】記憶の更新は絶対に忘れるな**
> **このファイルの冒頭にも書いたが、改めて念押しする。**
> 作業が完了したら、コミットする前に、必ずこのファイルに変更内容を記録せよ。
> 新しいファイルを作成した、既存ファイルを変更した、設計を変更した、バグを見つけた、知見を得た — すべて記録対象。
> **「後で更新しよう」は禁止。今すぐ更新せよ。**
