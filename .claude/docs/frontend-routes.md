# Frontend Routes

## Public Routes (認証不要)
| Path | 概要 |
|------|------|
| `/` | ルート → 認証済み: `/blog/new`、未認証: `/auth` にリダイレクト |
| `/auth` | サインイン/サインアップ選択画面 |
| `/sign-in` | Clerk サインイン |
| `/sign-up` | Clerk サインアップ |
| `/pricing` | リダイレクト: 認証済み→`/settings/billing`、未認証→`/auth` |
| `/invitation/accept` | 組織招待受諾 |
| `/offline` | PWA オフラインフォールバック |

## Protected Routes (認証必須 + サブスクリプション必須) - `(tools)` レイアウト
| Path | 概要 |
|------|------|
| `/blog/new` | 新規ブログ記事生成 |
| `/blog/[processId]` | ブログ生成進捗・編集 |
| `/blog/history` | ブログ生成履歴 |

## Protected Routes (認証必須、サブスク不要) - `(settings)` レイアウト
| Path | 概要 |
|------|------|
| `/settings/account` | アカウント設定 |
| `/settings/billing` | 請求&プラン管理（プラン購入/変更/シート変更/Stripe Portal） |
| `/settings/members` | チームメンバー管理 |
| `/settings/integrations/wordpress` | WordPress連携 |
| `/settings/integrations/wordpress/connect` | WordPress接続 |
| `/settings/integrations/instagram` | Instagram連携 |
| `/settings/integrations/line` | LINE連携 |
| `/settings/contact` | お問い合わせ |
| `/settings/install` | アプリインストールガイド |
| `/help/home` | ヘルプセンター |

## Privilege-Only Routes (@shintairiku.jp限定)
| Path | 概要 |
|------|------|
| `/admin` | 管理者ダッシュボード |
| `/admin/users` | ユーザー管理 |
| `/admin/users/[userId]` | ユーザー詳細 |
| `/admin/blog-usage` | 記事別Usage |
| `/admin/blog-usage/[processId]` | プロセス詳細トレース |
| `/admin/plans` | プラン設定 |
| `/admin/inquiries` | お問い合わせ管理 |
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

# Frontend API Routes (Next.js `/api/`)

| Path | Methods | 概要 |
|------|---------|------|
| `/api/proxy/[...path]` | ALL | バックエンドAPIプロキシ (120秒タイムアウト) |
| `/api/subscription/status` | GET | サブスクリプション状態取得 |
| `/api/subscription/checkout` | POST | Stripe Checkout Session作成 (新規契約用) |
| `/api/subscription/upgrade-to-team` | POST | 個人→チームプラン アップグレード (日割り対応) |
| `/api/subscription/update-seats` | POST | チームプラン シート数変更 |
| `/api/subscription/preview-upgrade` | POST | サブスク変更料金プレビュー |
| `/api/subscription/addon` | POST | アドオン管理 |
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
