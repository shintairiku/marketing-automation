# UIコンポーネントと主要パッケージの仕様

## 概要

本ドキュメントでは、フロントエンドで使用されているUIコンポーネントライブラリと主要なNPMパッケージについて詳細に解説します。本プロジェクトは、**shadcn/ui**をベースとしたモダンなUIコンポーネント、**Tailwind CSS**によるユーティリティファーストなスタイリング、**Framer Motion**による滑らかなアニメーション、そして**Lucide React**による豊富なアイコンセットを組み合わせた、統一性とカスタマイズ性を両立したデザインシステムを採用しています。

## 1. UIコンポーネントライブラリ

### 1.1 shadcn/ui + Radix UI Foundation

#### アーキテクチャ概要
- **shadcn/ui**: コピー&ペーストスタイルのコンポーネントライブラリ
- **Radix UI**: アクセシブルで無スタイルなプリミティブコンポーネント
- **場所**: `/frontend/src/components/ui/`

#### 採用されているRadix UIコンポーネント
```json
{
  "@radix-ui/react-alert-dialog": "^1.1.14",
  "@radix-ui/react-avatar": "^1.1.10",
  "@radix-ui/react-checkbox": "^1.3.2",
  "@radix-ui/react-collapsible": "^1.1.4",
  "@radix-ui/react-dialog": "^1.1.14",
  "@radix-ui/react-dropdown-menu": "^2.1.7",
  "@radix-ui/react-icons": "^1.3.2",
  "@radix-ui/react-label": "^2.1.6",
  "@radix-ui/react-popover": "^1.1.14",
  "@radix-ui/react-progress": "^1.1.7",
  "@radix-ui/react-scroll-area": "^1.2.9",
  "@radix-ui/react-select": "^2.2.5",
  "@radix-ui/react-separator": "^1.1.7",
  "@radix-ui/react-slider": "^1.3.5",
  "@radix-ui/react-slot": "^1.2.3",
  "@radix-ui/react-switch": "^1.2.5",
  "@radix-ui/react-tabs": "^1.1.4",
  "@radix-ui/react-toast": "^1.2.7"
}
```

### 1.2 主要UIコンポーネント詳細

#### Button コンポーネント
**ファイル**: `/frontend/src/components/ui/button.tsx`

```typescript
const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground shadow hover:bg-primary/90",
        destructive: "bg-destructive text-destructive-foreground shadow-sm hover:bg-destructive/90",
        outline: "border border-input bg-background shadow-sm hover:bg-accent hover:text-accent-foreground",
        secondary: "bg-secondary text-secondary-foreground shadow-sm hover:bg-secondary/80",
        ghost: "hover:bg-accent hover:text-accent-foreground",
        link: "text-primary underline-offset-4 hover:underline",
        // カスタムバリアント
        sexy: "bg-gradient-to-r from-indigo-500 to-pink-500 text-white shadow-md hover:from-indigo-600 hover:to-pink-600",
        orange: "bg-gradient-to-r from-amber-500 to-orange-500 text-white shadow-md hover:from-amber-600 hover:to-orange-600"
      },
      size: {
        default: "h-9 px-4 py-2",
        sm: "h-8 rounded-md px-3 text-xs",
        lg: "h-10 rounded-md px-8",
        icon: "h-9 w-9"
      }
    }
  }
)
```

**特徴**:
- `class-variance-authority`（CVA）によるバリアント管理
- カスタムグラデーションバリアント（sexy, orange）
- `@radix-ui/react-slot`による柔軟なレンダリング
- TypeScriptによる型安全性

#### Card コンポーネント
**ファイル**: `/frontend/src/components/ui/card.tsx`

```typescript
const Card = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn("rounded-xl bg-card text-card-foreground shadow-lg", className)}
      {...props}
    />
  )
)
```

**構成要素**:
- `Card`: メインコンテナ
- `CardHeader`: ヘッダー部分
- `CardTitle`: タイトル
- `CardDescription`: 説明文
- `CardContent`: メインコンテンツ
- `CardFooter`: フッター部分

#### Toast システム
**ファイル**: `/frontend/src/components/ui/toast.tsx`

```typescript
const toastVariants = cva(
  "group pointer-events-auto relative flex w-full items-center justify-between space-x-2 overflow-hidden rounded-md border p-4 pr-6 shadow-lg transition-all data-[swipe=cancel]:translate-x-0 data-[swipe=end]:translate-x-[var(--radix-toast-swipe-end-x)] data-[swipe=move]:translate-x-[var(--radix-toast-swipe-move-x)] data-[swipe=move]:transition-none data-[state=open]:animate-in data-[state=closed]:animate-out data-[swipe=end]:animate-out data-[state=closed]:fade-out-80 data-[state=closed]:slide-out-to-right-full data-[state=open]:slide-in-from-top-full data-[state=open]:sm:slide-in-from-bottom-full",
  {
    variants: {
      variant: {
        default: "border bg-background text-foreground",
        destructive: "destructive group border-destructive bg-destructive text-destructive-foreground"
      }
    }
  }
)
```

**追加通知ライブラリ**: 
- **Sonner** (`sonner: ^2.0.5`): よりシンプルなトースト通知
- 使用例: `import { toast } from 'sonner'`

## 2. スタイリングシステム

### 2.1 Tailwind CSS設定

#### 設定ファイル
**ファイル**: `/frontend/tailwind.config.ts`

```typescript
const config: Config = {
  darkMode: ['class'],
  content: ['./src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // デザインシステムカラー
        'custom-orange': '#E5581C',
        'custom-orange-light': '#FFF2ED',
        'sidebar-bg': '#F9F9F9',
        'sidebar-icon-muted': '#757575',
        'sidebar-text-muted': '#616161',
        'sidebar-border': '#E0E0E0',
        
        // shadcn/ui カラーシステム
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        primary: {
          DEFAULT: 'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))'
        }
      },
      keyframes: {
        'accordion-down': {
          from: { height: '0' },
          to: { height: 'var(--radix-accordion-content-height)' }
        },
        'spin-slow': {
          '0%': { rotate: '0deg' },
          '100%': { rotate: '360deg' }
        }
      },
      animation: {
        'accordion-down': 'accordion-down 0.2s ease-out',
        'spin-slow': 'spin 10s linear infinite'
      }
    }
  },
  plugins: [
    require('tailwindcss-animate'),
    require('@tailwindcss/typography')
  ]
}
```

#### グローバルスタイル
**ファイル**: `/frontend/src/styles/globals.css`

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --background: 0 0% 98%;         /* #fafafa */
    --foreground: 215 18% 17%;      /* #2e2e2e */
    --muted: 210 16% 93%;           /* #eef2f7 */
    --muted-foreground: 215 18% 60%;/* #7a7a7a */
    --primary: 215 31% 45%;         /* purple 600 */
    --secondary: 214 100% 51%;      /* blue 500 */
    --accent: 174 79% 39%;          /* teal 600 */
    --destructive: 358 79% 66%;     /* red 500 */
    --radius: 0.5rem;
  }
}
```

### 2.2 ユーティリティライブラリ

#### clsx + tailwind-merge統合
**ファイル**: `/frontend/src/utils/cn.ts`

```typescript
import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

**利用パッケージ**:
- `clsx`: 条件付きクラス名の構築
- `tailwind-merge`: 重複するTailwindクラスの競合解決
- `class-variance-authority`: バリアントベースのスタイルシステム

## 3. アニメーションライブラリ

### 3.1 Framer Motion

**パッケージ**: `framer-motion: ^12.16.0`

#### 使用例
```typescript
import { motion } from 'framer-motion';

export default function EnhancedArticleGeneration() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ duration: 0.3 }}
    >
      {/* コンテンツ */}
    </motion.div>
  );
}
```

#### 主要機能
- **Layout Animations**: 自動レイアウトアニメーション
- **Gesture Recognition**: ドラッグ、ホバー、タップジェスチャー
- **SVG Animations**: SVGパスアニメーション
- **Scroll Animations**: スクロール連動アニメーション

### 3.2 CSS Animations

#### Tailwind CSS Animation
```css
/* カスタムアニメーション */
@keyframes spin-slow {
  0% { rotate: 0deg; }
  100% { rotate: 360deg; }
}

.animate-spin-slow {
  animation: spin 10s linear infinite;
}
```

**プリセットアニメーション**:
- `tailwindcss-animate`: Radix UIとの統合アニメーション

## 4. アイコンライブラリ

### 4.1 Lucide React

**パッケージ**: `lucide-react: ^0.474.0`

#### 使用例
```typescript
import { AlertCircle, CheckCircle, Info, RefreshCw } from 'lucide-react';

function StatusIcon({ status }: { status: string }) {
  switch (status) {
    case 'error': return <AlertCircle className="h-4 w-4 text-red-500" />;
    case 'success': return <CheckCircle className="h-4 w-4 text-green-500" />;
    case 'info': return <Info className="h-4 w-4 text-blue-500" />;
    case 'loading': return <RefreshCw className="h-4 w-4 animate-spin" />;
    default: return null;
  }
}
```

#### 特徴
- **豊富なアイコンセット**: 1000+ アイコン
- **TypeScript対応**: 完全な型サポート
- **軽量**: Tree-shakingサポート
- **カスタマイズ**: className、size、color属性

### 4.2 その他のアイコンライブラリ

#### Radix UI Icons
**パッケージ**: `@radix-ui/react-icons: ^1.3.2`

```typescript
import { Cross2Icon } from "@radix-ui/react-icons";

const ToastClose = () => (
  <Cross2Icon className="h-4 w-4" />
);
```

#### React Icons
**パッケージ**: `react-icons: ^5.4.0`

```typescript
import { FaGithub, FaTwitter } from 'react-icons/fa';
```

## 5. 認証・フォーム関連パッケージ

### 5.1 Clerk認証UI

**パッケージ**: `@clerk/nextjs: ^6.19.3`

#### 多言語対応
```typescript
import { jaJP } from '@clerk/localizations';

// 設定で日本語を指定
{
  localization: jaJP
}
```

### 5.2 フォームバリデーション

#### Zod
**パッケージ**: `zod: ^3.24.1`

```typescript
import { z } from 'zod';

const articleSchema = z.object({
  title: z.string().min(1, '必須項目です').max(100, '100文字以内で入力してください'),
  description: z.string().min(10, '10文字以上で入力してください'),
  keywords: z.array(z.string()).min(1, '最低1つのキーワードを入力してください')
});

type ArticleFormData = z.infer<typeof articleSchema>;
```

## 6. 追加機能パッケージ

### 6.1 決済システム

#### Stripe
```json
{
  "@stripe/stripe-js": "^2.4.0",
  "stripe": "^18.0.0"
}
```

### 6.2 メール機能

#### React Email
```json
{
  "@react-email/components": "^0.0.36",
  "@react-email/tailwind": "^1.0.4"
}
```

### 6.3 追加UIライブラリ

#### Geist UI
```json
{
  "@geist-ui/core": "^2.3.8",
  "geist-ui": "^0.0.102"
}
```

#### Vaul (Drawer)
```json
{
  "vaul": "^1.1.2"
}
```

## 7. 開発・ビルドツール

### 7.1 TypeScript関連
```json
{
  "typescript": "^5.7.3",
  "@types/react": "19.0.4",
  "@types/react-dom": "19.0.2"
}
```

### 7.2 ESLint・Prettier
```json
{
  "eslint": "^8.57.1",
  "eslint-config-next": "^15.1.4",
  "eslint-config-prettier": "^8.10.0",
  "eslint-plugin-react": "^7.37.3",
  "eslint-plugin-simple-import-sort": "^10.0.0",
  "eslint-plugin-tailwindcss": "^3.17.5",
  "prettier": "^2.8.8",
  "prettier-plugin-tailwindcss": "^0.3.0"
}
```

### 7.3 フォントシステム

#### Geist Font
**パッケージ**: `geist: ^1.3.1`

```typescript
// tailwind.config.ts
fontFamily: {
  sans: ['var(--font-montserrat)', ...fontFamily.sans],
  alt: ['var(--font-montserrat-alternates)']
}
```

## 8. パッケージ利用箇所マッピング

### 8.1 コンポーネント別利用状況

| コンポーネント | 主要パッケージ | 場所 |
|---------------|----------------|------|
| Button | CVA, Radix Slot | `/components/ui/button.tsx` |
| Card | Tailwind CSS | `/components/ui/card.tsx` |
| Toast | Radix Toast, CVA | `/components/ui/toast.tsx` |
| Dialog | Radix Dialog | `/components/ui/dialog.tsx` |
| Form | Zod, React Hook Form | カスタムフック |
| Animation | Framer Motion | `/components/article-generation/` |
| Icons | Lucide React | 全体で使用 |

### 8.2 機能別パッケージマッピング

| 機能 | パッケージ | 実装場所 |
|------|-----------|----------|
| 認証 | @clerk/nextjs | `/middleware.ts`, 認証フック |
| 決済 | Stripe | `/api/webhooks`, Stripe関連 |
| データベース | Supabase | 全体のデータアクセス |
| 通知 | Sonner | カスタムフック |
| フォーム | Zod | バリデーションスキーマ |
| アニメーション | Framer Motion | 記事生成ページ |

## 9. パフォーマンス最適化

### 9.1 Tree Shaking対応

```typescript
// ❌ 悪い例: 全体インポート
import * as LucideIcons from 'lucide-react';

// ✅ 良い例: 必要なもののみインポート
import { AlertCircle, CheckCircle } from 'lucide-react';
```

### 9.2 動的インポート

```typescript
// 重いコンポーネントの遅延読み込み
const HeavyComponent = dynamic(() => import('./HeavyComponent'), {
  loading: () => <div>Loading...</div>
});
```

### 9.3 バンドルサイズ管理

- **分析**: `@vercel/analytics`でバンドルサイズを監視
- **最適化**: 不要パッケージの削除、動的インポートの活用
- **Code Splitting**: Next.jsの自動コード分割を活用

## 10. 今後の拡張計画

### 10.1 追加予定パッケージ

- **React Hook Form**: より複雑なフォーム管理
- **React Query/SWR**: サーバー状態管理の強化
- **Headless UI**: 追加のアクセシブルコンポーネント

### 10.2 カスタムコンポーネント拡充

- **データテーブル**: `@tanstack/react-table`統合
- **チャート**: `recharts`または`Chart.js`統合
- **ファイルアップロード**: ドラッグ&ドロップ対応

この仕様書により、プロジェクトで使用されているUIコンポーネントとパッケージの全容を把握し、統一的で保守性の高いフロントエンド開発を推進することができます。