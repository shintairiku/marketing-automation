# フロントエンドの共通設計（Hooks, 型定義, スタイル）

## 概要

このドキュメントでは、Next.jsフロントエンドにおける共通設計パターンについて詳細に解説します。カスタムフックによるロジックのカプセル化、TypeScriptによる堅牢な型定義、そしてTailwind CSSを活用したユーティリティファーストなスタイリング手法について説明します。

## カスタムフックの設計パターン

### 1. データ取得フック（Data Fetching Hooks）

#### useArticles

**ファイル**: `/frontend/src/hooks/useArticles.ts`

**機能**:
- 記事データの取得、作成、更新、削除
- 楽観的更新（Optimistic Updates）
- エラーハンドリングとローディング状態管理

**使用例**:
```typescript
const { articles, isLoading, error, createArticle, updateArticle, deleteArticle } = useArticles();
```

**特徴**:
- SWRまたはReact Queryパターンの実装
- キャッシュ管理とデータ同期
- 型安全なAPI呼び出し

#### useDefaultCompany

**ファイル**: `/frontend/src/hooks/useDefaultCompany.ts`

**機能**:
- ユーザーのデフォルト会社情報の管理
- 会社情報の取得と設定
- リアルタイム更新対応

**使用例**:
```typescript
const { company, isLoading, setDefaultCompany } = useDefaultCompany();
```

### 2. リアルタイム通信フック

#### useSupabaseRealtime

**ファイル**: `/frontend/src/hooks/useSupabaseRealtime.ts`

**機能**:
- Supabase Realtimeとの接続管理
- イベント購読とデータ同期
- 接続状態の監視と自動再接続

**実装詳細**:
```typescript
export const useSupabaseRealtime = ({
  processId,
  userId,
  onEvent,
  onError,
  onStatusChange,
  onDataSync,
  onConnectionStateChange,
  autoConnect = true,
  enableDataSync = true,
  syncInterval = 30,
}: UseSupabaseRealtimeOptions) => {
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // 接続管理ロジック
  // データ検証ロジック
  // エラーハンドリング
  
  return {
    isConnected,
    isConnecting,
    error,
    connect,
    disconnect,
    fetchProcessData,
    queueAction,
  };
};
```

#### useArticleGenerationRealtime

**ファイル**: `/frontend/src/hooks/useArticleGenerationRealtime.ts`

**機能**:
- 記事生成プロセスの状態管理
- リアルタイムイベントの処理
- ユーザーインタラクション管理

**状態管理構造**:
```typescript
interface GenerationState {
  currentStep: string;
  steps: GenerationStep[];
  personas?: PersonaOption[];
  themes?: ThemeOption[];
  researchPlan?: any;
  outline?: any;
  generatedContent?: string;
  finalArticle?: {
    title: string;
    content: string;
  };
  isWaitingForInput: boolean;
  inputType?: string;
  error?: string;
  // ... その他の状態
}
```

### 3. UIインタラクションフック

#### useApiTest

**ファイル**: `/frontend/src/hooks/useApiTest.ts`

**機能**:
- API接続テスト
- ヘルスチェック機能
- デバッグ支援

#### useRecoverableProcesses

**ファイル**: `/frontend/src/hooks/useRecoverableProcesses.ts`

**機能**:
- 復帰可能なプロセスの検索
- プロセス復旧機能
- エラーからの回復処理

### フックの共通設計原則

1. **Single Responsibility**: 各フックは単一の責任を持つ
2. **Reusability**: 複数のコンポーネントで再利用可能
3. **Type Safety**: TypeScriptによる型安全性の確保
4. **Error Handling**: 一貫したエラーハンドリング
5. **Testing**: テスト可能な設計

## TypeScript型定義システム

### 1. 記事生成関連の型定義

**ファイル**: `/frontend/src/types/article-generation.ts`

```typescript
// 基本的なステップ定義
export interface GenerationStep {
  id: string;
  name?: string;
  title?: string;
  status: 'pending' | 'in_progress' | 'completed' | 'error';
  message?: string;
  data?: any;
}

// ペルソナ定義
export interface PersonaOption {
  id: number;
  description: string;
}

// テーマ定義
export interface ThemeOption {
  title: string;
  description: string;
  keywords: string[];
}

// 進捗情報
export interface ResearchProgress {
  currentQuery: number;
  totalQueries: number;
  query: string;
}

export interface SectionsProgress {
  currentSection: number;
  totalSections: number;
  sectionHeading: string;
}

// 画像プレースホルダー
export interface ImagePlaceholder {
  placeholder_id: string;
  description_jp: string;
  prompt_en: string;
  alt_text: string;
}

// 完了セクション
export interface CompletedSection {
  index: number;
  heading: string;
  content: string;
  imagePlaceholders?: ImagePlaceholder[];
}

// メイン状態インターフェース
export interface GenerationState {
  currentStep: string;
  steps: GenerationStep[];
  personas?: PersonaOption[];
  themes?: ThemeOption[];
  researchPlan?: any;
  outline?: any;
  generatedContent?: string;
  finalArticle?: {
    title: string;
    content: string;
  };
  articleId?: string;
  isWaitingForInput: boolean;
  inputType?: string;
  error?: string;
  researchProgress?: ResearchProgress;
  sectionsProgress?: SectionsProgress;
  imageMode?: boolean;
  imagePlaceholders?: ImagePlaceholder[];
  completedSections?: CompletedSection[];
}

// ユーザー入力タイプ
export type UserInputType = 
  | 'select_persona'
  | 'select_theme'
  | 'approve_plan'
  | 'approve_outline';

// ステップステータス
export type StepStatus = 'pending' | 'in_progress' | 'completed' | 'error';
```

### 2. API応答型定義

**ファイル**: `/frontend/src/types/action-response.ts`

```typescript
export interface ActionResponse<T = unknown> {
  success: boolean;
  data?: T;
  error?: string;
  code?: string;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  pageSize: number;
  hasMore: boolean;
}
```

### 3. 機能固有の型定義

#### Pricing関連

**ファイル**: `/frontend/src/features/pricing/types.ts`

```typescript
export interface ProductMetadata {
  features: string[];
  popular?: boolean;
  tier: 'basic' | 'pro' | 'enterprise';
}

export interface PriceWithProduct {
  id: string;
  product: {
    id: string;
    name: string;
    description: string;
    metadata: ProductMetadata;
  };
  unit_amount: number;
  currency: string;
  interval?: 'month' | 'year';
}
```

### 型定義のベストプラクティス

1. **Interface vs Type**: オブジェクト形状はInterface、ユニオン型はType
2. **Generic Types**: 再利用可能な汎用型の活用
3. **Strict Typing**: `any`の使用を最小限に抑制
4. **Documentation**: JSDocコメントによる型の説明
5. **Export Strategy**: 必要な型のみをエクスポート

## スタイリングシステム

### 1. Tailwind CSS設定

**ファイル**: `/frontend/tailwind.config.ts`

```typescript
const config: Config = {
  darkMode: ['class'],
  content: ['./src/**/*.{ts,tsx}'],
  theme: {
    container: {
      center: true,
      padding: '2rem',
      screens: {
        '2xl': '1440px',
      },
    },
    extend: {
      colors: {
        // カスタムカラーパレット
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        primary: {
          DEFAULT: 'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))',
        },
        // ... その他のカラー定義
        'custom-orange': '#E5581C',
        'custom-orange-light': '#FFF2ED',
        'sidebar-bg': '#F9F9F9',
        'sidebar-icon-muted': '#757575',
        'sidebar-text-muted': '#616161',
        'sidebar-border': '#E0E0E0',
      },
      borderRadius: {
        lg: `var(--radius)`,
        md: `calc(var(--radius) - 2px)`,
        sm: 'calc(var(--radius) - 4px)',
      },
      fontFamily: {
        sans: ['var(--font-montserrat)', ...fontFamily.sans],
        alt: ['var(--font-montserrat-alternates)'],
      },
      keyframes: {
        'accordion-down': {
          from: { height: '0' },
          to: { height: 'var(--radix-accordion-content-height)' },
        },
        'accordion-up': {
          from: { height: 'var(--radix-accordion-content-height)' },
          to: { height: '0' },
        },
        'spin-slow': {
          '0%': { rotate: '0deg' },
          '100%': { rotate: '360deg' },
        },
      },
      animation: {
        'accordion-down': 'accordion-down 0.2s ease-out',
        'accordion-up': 'accordion-up 0.2s ease-out',
        'spin-slow': 'spin 10s linear infinite',
      },
    },
  },
  plugins: [require('tailwindcss-animate'), require('@tailwindcss/typography')],
};
```

### 2. グローバルスタイル

**ファイル**: `/frontend/src/styles/globals.css`

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  /* ライトモードカラーパレット */
  :root {
    --background: 0 0% 98%;         /* #fafafa */
    --foreground: 215 18% 17%;      /* #2e2e2e */
    --muted: 210 16% 93%;           /* #eef2f7 */
    --muted-foreground: 215 18% 60%;/* #7a7a7a */
    --popover: 0 0% 100%;           /* #ffffff */
    --popover-foreground: 215 18% 17%;/* #2e2e2e */
    --border: 210 14% 87%;          /* #e2e8f0 */
    --input: 210 14% 96%;           /* #f3f4f6 */
    --card: 0 0% 100%;              /* #ffffff */
    --card-foreground: 215 18% 17%; /* #2e2e2e */
    --primary: 215 31% 45%;         /* purple 600 */
    --primary-foreground: 0 0% 100%;/* #ffffff */
    --secondary: 214 100% 51%;      /* blue 500 */
    --secondary-foreground: 0 0% 100%;/* #ffffff */
    --accent: 174 79% 39%;          /* teal 600 */
    --accent-foreground: 0 0% 100%; /* #ffffff */
    --destructive: 358 79% 66%;     /* red 500 */
    --destructive-foreground: 0 0% 100%;/* #ffffff */
    --ring: 233 48% 48%;            /* match primary */
    --radius: 0.5rem;
  }

  /* ダークモード（同じパレットを使用） */
  .dark {
    --background: 0 0% 98%;
    --foreground: 215 18% 17%;
    /* ... 同じ値を継承 */
  }

  /* グローバルスタイル */
  ::selection {
    @apply text-black bg-cyan-400;
  }

  *:focus-visible {
    @apply outline outline-2 outline-offset-2 outline-pink-500;
  }

  * {
    @apply border-border min-w-0;
  }

  body {
    @apply bg-background text-foreground h-full;
    font-feature-settings: 'rlig' 1, 'calt' 1;
  }

  html {
    @apply h-full;
  }

  h1 {
    @apply font-alt font-bold text-4xl text-foreground lg:text-6xl;
  }
  
  /* 記事プレビューリンクスタイル */
  .article-preview-content a {
    color: #667eea !important;
    text-decoration: none !important;
    font-weight: 600 !important;
    border-bottom: 2px solid transparent !important;
    transition: all 0.3s ease !important;
  }
  
  .article-preview-content a:hover {
    border-bottom: 2px solid #667eea !important;
    transform: translateY(-1px) !important;
  }
}
```

### 3. ユーティリティクラスとヘルパー

**ファイル**: `/frontend/src/utils/cn.ts`

```typescript
import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

**使用例**:
```typescript
// 条件付きクラス適用
const buttonClassName = cn(
  "px-4 py-2 rounded-md font-medium transition-colors",
  variant === 'primary' && "bg-primary text-primary-foreground",
  variant === 'secondary' && "bg-secondary text-secondary-foreground",
  disabled && "opacity-50 cursor-not-allowed"
);
```

### 4. shadcn/ui コンポーネントシステム

#### 基本UIコンポーネント

**利用可能なコンポーネント**:
- `Button` - `/frontend/src/components/ui/button.tsx`
- `Card` - `/frontend/src/components/ui/card.tsx`
- `Input` - `/frontend/src/components/ui/input.tsx`
- `Dialog` - `/frontend/src/components/ui/dialog.tsx`
- `Tabs` - `/frontend/src/components/ui/tabs.tsx`
- `Progress` - `/frontend/src/components/ui/progress.tsx`
- `Badge` - `/frontend/src/components/ui/badge.tsx`
- `Alert` - `/frontend/src/components/ui/alert.tsx`

#### カスタムコンポーネント

**ファイル**: `/frontend/src/components/ui/connection-status.tsx`

```typescript
interface ConnectionStatusProps {
  isConnected: boolean;
  isConnecting: boolean;
  error?: string;
}

export function ConnectionStatus({ isConnected, isConnecting, error }: ConnectionStatusProps) {
  return (
    <div className={cn(
      "flex items-center space-x-2 px-3 py-1 rounded-full text-sm",
      isConnected && "bg-green-100 text-green-800",
      isConnecting && "bg-yellow-100 text-yellow-800",
      error && "bg-red-100 text-red-800"
    )}>
      {/* ステータス表示ロジック */}
    </div>
  );
}
```

## パッケージ依存関係と統合

### 主要なUIライブラリ

**package.json抜粋**:
```json
{
  "dependencies": {
    "@radix-ui/react-alert-dialog": "^1.1.14",
    "@radix-ui/react-avatar": "^1.1.10",
    "@radix-ui/react-checkbox": "^1.3.2",
    "@radix-ui/react-collapsible": "^1.1.4",
    "@radix-ui/react-dialog": "^1.1.14",
    "@radix-ui/react-dropdown-menu": "^2.1.7",
    "@radix-ui/react-icons": "^1.3.2",
    "framer-motion": "^12.16.0",
    "lucide-react": "^0.474.0",
    "tailwindcss": "^3.4.17",
    "tailwindcss-animate": "^1.0.7"
  }
}
```

### アニメーションライブラリ

#### Framer Motion統合

```typescript
import { AnimatePresence, motion } from 'framer-motion';

// アニメーション付きコンポーネント
<AnimatePresence>
  {isVisible && (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ duration: 0.3 }}
    >
      Content
    </motion.div>
  )}
</AnimatePresence>
```

### アイコンシステム

#### Lucide React

```typescript
import { 
  Check, 
  ChevronRight, 
  Clock, 
  AlertCircle,
  Lightbulb 
} from 'lucide-react';

// 使用例
<Button>
  <Check className="h-4 w-4 mr-2" />
  完了
</Button>
```

## レスポンシブデザインとアクセシビリティ

### 1. レスポンシブ対応

```typescript
// Tailwindのレスポンシブクラス
<div className="
  grid grid-cols-1 
  md:grid-cols-2 
  lg:grid-cols-3 
  xl:grid-cols-4 
  gap-4
">
  {/* コンテンツ */}
</div>
```

### 2. アクセシビリティ対応

```typescript
// ARIA属性とキーボードナビゲーション
<button
  aria-label="記事を削除"
  aria-describedby="delete-description"
  className="focus:ring-2 focus:ring-primary focus:ring-offset-2"
  onKeyDown={(e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      handleDelete();
    }
  }}
>
  削除
</button>
```

## パフォーマンス最適化

### 1. コンポーネントの最適化

```typescript
import { memo, useCallback, useMemo } from 'react';

// メモ化されたコンポーネント
const OptimizedComponent = memo(({ data, onAction }: Props) => {
  const processedData = useMemo(() => {
    return data.map(processItem);
  }, [data]);

  const handleAction = useCallback((id: string) => {
    onAction(id);
  }, [onAction]);

  return (
    <div>
      {processedData.map(item => (
        <Item key={item.id} data={item} onAction={handleAction} />
      ))}
    </div>
  );
});
```

### 2. 動的インポート

```typescript
import dynamic from 'next/dynamic';

// 重いコンポーネントの遅延読み込み
const HeavyComponent = dynamic(() => import('./HeavyComponent'), {
  loading: () => <div>Loading...</div>,
  ssr: false
});
```

## テスト戦略

### 1. 型テスト

```typescript
// 型の正確性をテスト
type TestGenerationState = GenerationState;
const testState: TestGenerationState = {
  currentStep: 'keyword_analyzing',
  steps: [],
  isWaitingForInput: false,
};
```

### 2. フックのテスト

```typescript
import { renderHook, act } from '@testing-library/react';
import { useArticles } from '@/hooks/useArticles';

test('should fetch articles on mount', async () => {
  const { result } = renderHook(() => useArticles());
  
  expect(result.current.isLoading).toBe(true);
  
  await act(async () => {
    await new Promise(resolve => setTimeout(resolve, 100));
  });
  
  expect(result.current.isLoading).toBe(false);
  expect(result.current.articles).toBeDefined();
});
```

## 結論

このフロントエンド共通設計により、以下の利点を実現しています：

1. **保守性**: 一貫したパターンによる予測可能なコード
2. **再利用性**: コンポーネントとフックの高い再利用性
3. **型安全性**: TypeScriptによる実行時エラーの予防
4. **パフォーマンス**: 最適化されたレンダリングとバンドルサイズ
5. **開発体験**: 優れたDXとデバッグ機能
6. **アクセシビリティ**: インクルーシブなユーザー体験

この設計パターンは、スケーラブルで保守可能なNext.jsアプリケーションの構築を支援します。