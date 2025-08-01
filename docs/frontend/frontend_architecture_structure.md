# フロントエンドアーキテクチャとディレクトリ構造の仕様

## 概要

このドキュメントでは、Next.js App Routerで構築されたMarketing Automation フロントエンドのアーキテクチャと詳細なディレクトリ構造について解説します。App Routerのルートグループによるルーティング、`features`ディレクトリに機能単位でビジネスロジックを分割するFeature-Sliced Design、`components/ui`と`libs`の役割分担など、モダンなNext.jsアプリケーションの設計思想を詳述します。

## フロントエンドアーキテクチャ概要

### 技術スタック
```
Framework: Next.js 15.1.4 (App Router)
Language: TypeScript 5.7.3
Runtime: React 19.0.0
Styling: Tailwind CSS 3.4.17
Authentication: Clerk (v6.19.3)
Database: Supabase (v2.47.12)
Payment: Stripe
Animation: Framer Motion 12.16.0
Icons: Lucide React
```

### アーキテクチャ原則
1. **Feature-Sliced Design**: 機能単位でのコード分割
2. **App Router**: Next.js 13+ の新しいルーティングシステム
3. **Server-First**: サーバーコンポーネント優先設計
4. **Type Safety**: TypeScript による厳密な型安全性
5. **Component Composition**: 再利用可能なコンポーネント設計

## ディレクトリ構造詳細

### 全体構造
```
frontend/
├── src/                           # ソースコード
│   ├── app/                      # App Router (Pages & Layouts)
│   ├── components/               # 共通UIコンポーネント
│   ├── features/                 # 機能別ビジネスロジック
│   ├── hooks/                    # カスタムフック
│   ├── libs/                     # 外部ライブラリ統合
│   ├── styles/                   # グローバルスタイル
│   ├── types/                    # TypeScript型定義
│   ├── utils/                    # ユーティリティ関数
│   └── middleware.ts             # Next.js Middleware
├── public/                       # 静的ファイル
├── supabase/                     # Supabase設定・マイグレーション
└── 設定ファイル群
```

## App Router ディレクトリ (`src/app/`)

### ルートグループ設計
```
app/
├── (account)/                    # アカウント関連
│   └── account/
│       └── page.tsx             # アカウント設定
├── (article-generation)/        # 記事生成関連
│   └── layout.tsx               # 記事生成専用レイアウト
├── (dashboard)/                  # ダッシュボード
│   ├── dashboard/
│   │   ├── articles/
│   │   │   └── page.tsx         # 記事一覧
│   │   └── page.tsx             # ダッシュボードホーム
│   └── layout.tsx               # ダッシュボードレイアウト
├── (marketing)/                  # マーケティングページ
│   ├── pricing/
│   │   └── page.tsx             # 料金プラン
│   ├── layout.tsx               # マーケティングレイアウト
│   └── page.tsx                 # ランディングページ
└── (tools)/                      # 各種ツール
    ├── help/                    # ヘルプセクション
    ├── instagram/               # Instagram連携
    ├── seo/                     # SEOツール
    └── settings/                # 設定画面
```

### ルートグループの特徴

#### 1. `(dashboard)` - ダッシュボードエリア
```typescript
// dashboard/layout.tsx
export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1">
        <Header />
        {children}
      </main>
    </div>
  )
}
```

**特徴**:
- 統一されたサイドバー＋ヘッダーレイアウト
- 認証必須エリア
- 記事管理、設定などの管理機能

#### 2. `(tools)` - 各種ツールエリア
```
tools/
├── seo/                         # SEO関連ツール
│   ├── analyze/                 # SEO分析
│   ├── generate/                # 記事生成
│   │   ├── edit-article/[id]/   # 記事編集
│   │   └── new-article/[jobId]/ # 新規記事生成
│   ├── home/                    # SEOホーム
│   ├── input/persona/           # ペルソナ入力
│   └── manage/                  # 記事管理
├── instagram/                   # Instagram連携
├── settings/                    # 各種設定
│   ├── account/                 # アカウント設定
│   ├── billing/                 # 請求設定
│   ├── company/                 # 会社設定
│   ├── integrations/            # 連携設定
│   ├── members/                 # メンバー管理
│   └── style-guide/             # スタイルガイド
└── help/                        # ヘルプ・サポート
```

#### 3. `(marketing)` - マーケティングエリア
```typescript
// (marketing)/layout.tsx
export default function MarketingLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      <MarketingHeader />
      {children}
      <MarketingFooter />
    </div>
  )
}
```

**特徴**:
- 公開ページ用レイアウト
- マーケティング最適化デザイン
- 認証不要エリア

## Features ディレクトリ (`src/features/`)

### Feature-Sliced Design採用
```
features/
├── account/                     # アカウント機能
│   └── controllers/             # アカウント制御ロジック
├── article-generation/          # 記事生成機能
│   └── types.ts                # 記事生成型定義
├── emails/                      # メール機能
│   ├── tailwind.config.ts      # メール用Tailwind設定
│   └── welcome.tsx             # ウェルカムメール
├── pricing/                     # 課金機能
│   ├── actions/                # 課金アクション
│   ├── components/             # 課金UI部品
│   ├── controllers/            # 課金制御ロジック
│   ├── models/                 # 課金データモデル
│   └── types.ts               # 課金型定義
└── tools/                      # ツール機能
    ├── generate/seo/           # SEO生成ツール
    ├── instagram/              # Instagram機能
    └── seo/                    # SEO機能
```

### 機能別詳細設計

#### 1. 記事生成機能 (`features/tools/generate/seo/`)
```
seo/
├── description/                # 記事概要生成
│   └── display/
│       ├── descriptionLeftDisplay.tsx
│       ├── descriptionRightDisplay.tsx
│       └── index.tsx
├── edit/                       # 記事編集
├── headline/                   # ヘッドライン生成
├── post/                       # 投稿機能
├── theme/                      # テーマ生成
└── types/                      # SEO型定義
    └── seoStep.tsx
```

#### 2. 新記事生成機能 (`features/tools/seo/generate/new-article/`)
```
new-article/
├── component/                  # 生成プロセス用コンポーネント
│   ├── AiThinkingBox.tsx      # AI思考表示
│   ├── ArticlePreviewStyles.tsx
│   ├── BatchSectionProgress.tsx
│   ├── CompactGenerationFlow.tsx  # コンパクト生成フロー
│   ├── CompactUserInteraction.tsx # ユーザー対話
│   ├── CompletedArticleView.tsx   # 完成記事表示
│   ├── ContentGeneration.tsx
│   ├── ErrorRecoveryActions.tsx   # エラー回復
│   ├── GenerationErrorHandler.tsx
│   ├── GenerationSteps.tsx        # 生成ステップ
│   ├── PersonaSelection.tsx       # ペルソナ選択
│   ├── ProcessRecoveryDialog.tsx  # プロセス回復
│   ├── RecoverableProcessesDialog.tsx
│   ├── StepIndicator.tsx          # ステップ表示
│   └── ThemeSelection.tsx         # テーマ選択
├── display/                    # 表示コンポーネント
│   ├── ExplainDialog.tsx      # 説明ダイアログ
│   ├── GeneratedBodySection.tsx
│   ├── GeneratedOutlineSection.tsx
│   ├── GeneratedTitleSection.tsx
│   ├── GenerationProcessPage.tsx  # メイン処理ページ
│   ├── InputSection.tsx
│   ├── NewArticleStartPage.tsx
│   └── indexPage.tsx
└── hooks/                      # カスタムフック
    ├── useArticleGeneration_deprecated.ts
    └── useWebSocket_deprecated.ts
```

#### 3. 課金機能 (`features/pricing/`)
```
pricing/
├── actions/                    # サーバーアクション
│   └── create-checkout-action.ts
├── components/                 # UI コンポーネント
│   ├── price-card.tsx         # 価格カード
│   └── pricing-section.tsx    # 料金セクション
├── controllers/                # 制御ロジック
│   ├── get-products.ts        # 商品取得
│   ├── upsert-price.ts        # 価格更新
│   └── upsert-product.ts      # 商品更新
├── models/                     # データモデル
│   └── product-metadata.ts    # 商品メタデータ
└── types.ts                   # 型定義
```

## Components ディレクトリ (`src/components/`)

### UI コンポーネント体系
```
components/
├── ui/                         # shadcn/ui ベースコンポーネント
│   ├── alert-dialog.tsx       # アラートダイアログ
│   ├── button.tsx             # ボタン
│   ├── card.tsx               # カード
│   ├── dialog.tsx             # ダイアログ
│   ├── input.tsx              # 入力フィールド
│   ├── select.tsx             # セレクトボックス
│   ├── table.tsx              # テーブル
│   └── ... (その他UIパーツ)
├── display/                    # 表示コンポーネント
│   ├── header.tsx             # ヘッダー
│   ├── sidebar.tsx            # サイドバー
│   ├── pageTabs.tsx           # ページタブ
│   └── sidebarCategory.tsx    # サイドバーカテゴリ
├── seo/                       # SEO専用コンポーネント
│   ├── button/                # SEO用ボタン
│   ├── commonTitle.tsx        # 共通タイトル
│   ├── outputTitle.tsx        # 出力タイトル
│   └── seoHeaderTab.tsx       # SEOヘッダータブ
├── article-generation/        # 記事生成専用
│   └── enhanced-article-generation.tsx
├── container.tsx              # コンテナ
├── logo.tsx                   # ロゴ
└── sexy-boarder.tsx           # 装飾ボーダー
```

### shadcn/ui コンポーネントシステム
```typescript
// components/ui/button.tsx の例
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/utils/cn"

const buttonVariants = cva(
  "inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-primary/90",
        destructive: "bg-destructive text-destructive-foreground hover:bg-destructive/90",
        outline: "border border-input bg-background hover:bg-accent hover:text-accent-foreground",
        secondary: "bg-secondary text-secondary-foreground hover:bg-secondary/80",
        ghost: "hover:bg-accent hover:text-accent-foreground",
        link: "text-primary underline-offset-4 hover:underline",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-9 rounded-md px-3",
        lg: "h-11 rounded-md px-8",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)
```

## Hooks ディレクトリ (`src/hooks/`)

### カスタムフック体系
```
hooks/
├── useArticleGenerationRealtime.ts  # 記事生成リアルタイム
├── useArticles.ts                   # 記事管理
├── useDefaultCompany.ts             # デフォルト会社
├── useRecoverableProcesses.ts       # 復帰可能プロセス
├── useSupabaseRealtime.ts           # Supabase リアルタイム
├── useApiTest.ts                    # API テスト
└── use-toast.ts                     # トースト通知
```

### 主要カスタムフックの詳細

#### 1. `useSupabaseRealtime.ts`
```typescript
export const useSupabaseRealtime = ({
  processId,
  userId,
  onEvent,
  onError,
  onStatusChange,
  autoConnect = true,
}: UseSupabaseRealtimeOptions) => {
  const [isConnected, setIsConnected] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  // リアルタイム接続管理
  // イベント処理
  // エラーハンドリング
  
  return {
    isConnected,
    error,
    connect,
    disconnect,
    fetchProcessData,
  }
}
```

#### 2. `useArticleGenerationRealtime.ts`
```typescript
export const useArticleGenerationRealtime = ({ 
  processId, 
  userId,
  autoConnect = true 
}: UseArticleGenerationRealtimeOptions) => {
  const [state, setState] = useState<GenerationState>({
    currentStep: 'keyword_analyzing',
    steps: [...],
    isWaitingForInput: false,
    // ...状態管理
  })
  
  // Supabase Realtime との統合
  // 生成プロセス状態管理
  // ユーザーインタラクション処理
  
  return {
    state,
    actions: {
      selectPersona,
      approveTheme,
      approveOutline,
      // ...ユーザーアクション
    },
    connectionState,
  }
}
```

## Libs ディレクトリ (`src/libs/`)

### 外部ライブラリ統合
```
libs/
├── api/                        # API クライアント
├── stripe/                     # Stripe 統合
│   └── stripe-admin.ts        # Stripe 管理機能
└── supabase/                   # Supabase 統合
    ├── supabase-admin.ts      # 管理用クライアント
    ├── supabase-client.ts     # ブラウザクライアント
    ├── supabase-middleware-client.ts  # ミドルウェア用
    ├── supabase-server-client.ts      # サーバー用
    └── types.ts               # Supabase 型定義
```

### Supabase クライアント統合
```typescript
// supabase-client.ts (ブラウザ用)
import { createBrowserClient } from '@supabase/ssr'

export const supabase = createBrowserClient<Database>(
  getEnvVar(process.env.NEXT_PUBLIC_SUPABASE_URL, 'NEXT_PUBLIC_SUPABASE_URL'),
  getEnvVar(process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY, 'NEXT_PUBLIC_SUPABASE_ANON_KEY')
)

// supabase-server-client.ts (サーバー用)
import { createServerClient } from '@supabase/ssr'

export function createClient(cookieStore: ReadonlyRequestCookies) {
  return createServerClient<Database>(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        get(name: string) {
          return cookieStore.get(name)?.value
        },
      },
    }
  )
}
```

## Types ディレクトリ (`src/types/`)

### 型定義管理
```
types/
├── action-response.ts          # アクション応答型
└── article-generation.ts      # 記事生成型
```

### 記事生成型定義の例
```typescript
// article-generation.ts
export interface GenerationState {
  currentStep: string
  steps: GenerationStep[]
  isWaitingForInput: boolean
  personas?: PersonaData[]
  themes?: ThemeData[]
  researchPlan?: ResearchPlan
  outline?: OutlineData
  generatedContent?: string
  finalArticle?: ArticleData
  articleId?: string
  error?: string
  researchProgress?: ResearchProgress
  sectionsProgress?: SectionsProgress
  completedSections: CompletedSection[]
}

export interface GenerationStep {
  id: string
  name: string
  status: StepStatus
}

export type StepStatus = 'pending' | 'in_progress' | 'completed' | 'error' | 'skipped'
```

## Middleware設計 (`src/middleware.ts`)

### 認証フロー管理
```typescript
import { clerkMiddleware, createRouteMatcher } from '@clerk/nextjs/server'

// 保護されたルート定義
const isProtectedRoute = createRouteMatcher([
  '/dashboard(.*)',
  '/account(.*)',
  '/tools(.*)',
  '/seo(.*)',
])

// 公開ルート定義
const isPublicRoute = createRouteMatcher([
  '/',
  '/pricing',
  '/sign-in(.*)',
  '/sign-up(.*)',
  '/api/webhooks(.*)',
])

export default clerkMiddleware(async (authObject, req) => {
  if (!isPublicRoute(req) && isProtectedRoute(req)) {
    const { userId } = await authObject()
    if (!userId) {
      const signInUrl = new URL('/sign-in', req.url)
      signInUrl.searchParams.set('redirect_url', req.url)
      return NextResponse.redirect(signInUrl)
    }
  }
  return NextResponse.next()
})
```

## スタイリングシステム

### Tailwind CSS設定
```typescript
// tailwind.config.ts
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
    './src/features/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        // カスタムカラー定義
      },
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
    require('tailwindcss-animate'),
  ],
}
```

### グローバルスタイル (`src/styles/globals.css`)
```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --background: 0 0% 100%;
    --foreground: 222.2 84% 4.9%;
    --card: 0 0% 100%;
    --card-foreground: 222.2 84% 4.9%;
    /* CSS カスタムプロパティ定義 */
  }

  * {
    @apply border-border;
  }
  
  body {
    @apply bg-background text-foreground;
  }
}
```

## パフォーマンス最適化

### Next.js App Router最適化
1. **Server Components**: デフォルトでサーバーサイド実行
2. **Client Components**: `'use client'` 指定で必要な場合のみ
3. **Streaming SSR**: 段階的な画面表示
4. **Static Generation**: 可能な限り静的生成
5. **Image Optimization**: Next.js Image コンポーネント活用

### バンドル最適化
```typescript
// next.config.js
module.exports = {
  experimental: {
    optimizePackageImports: ['lucide-react', '@radix-ui/react-icons'],
  },
  images: {
    domains: ['storage.googleapis.com'],
  },
}
```

## 開発体験（DX）向上

### TypeScript設定
```json
// tsconfig.json
{
  "compilerOptions": {
    "target": "es5",
    "lib": ["dom", "dom.iterable", "es6"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "forceConsistentCasingInFileNames": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "node",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{"name": "next"}],
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  }
}
```

### ESLint・Prettier設定
```json
// .eslintrc.json
{
  "extends": [
    "next/core-web-vitals",
    "prettier",
    "plugin:@typescript-eslint/recommended"
  ],
  "plugins": ["simple-import-sort", "tailwindcss"],
  "rules": {
    "simple-import-sort/imports": "error",
    "simple-import-sort/exports": "error",
    "tailwindcss/classnames-order": "warn"
  }
}
```

## まとめ

Next.js App Routerを活用したフロントエンドアーキテクチャは、以下の利点を提供します：

### 設計上の利点
1. **Feature-Sliced Design**: 機能単位での責務分離
2. **App Router**: 直感的なファイルベースルーティング
3. **Type Safety**: TypeScriptによる型安全性
4. **Component Composition**: 再利用可能なUI設計
5. **Server-First**: パフォーマンス最適化

### 開発効率
1. **Hot Reload**: 高速な開発サイクル
2. **IntelliSense**: 優れた開発者体験
3. **Linting**: コード品質の自動確保
4. **Testing**: 包括的なテスト環境

### ユーザー体験
1. **高速なページロード**: SSR・SSG活用
2. **SEO最適化**: メタデータ管理
3. **アクセシビリティ**: ARIA準拠UI
4. **レスポンシブ**: モバイルファースト設計

このアーキテクチャにより、スケーラブルで保守性の高いマーケティング自動化フロントエンドが実現されています。