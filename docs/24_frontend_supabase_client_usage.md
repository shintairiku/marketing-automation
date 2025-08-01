# フロントエンドにおけるSupabaseクライアントの利用仕様

## 概要

このドキュメントでは、Next.jsフロントエンドにおけるSupabaseクライアントの設定方法と利用パターンについて詳細に解説します。`@supabase/ssr`ライブラリを活用して、環境ごとに最適化されたクライアント実装を提供し、認証状態を一貫して管理するアーキテクチャを説明します。

## Supabaseクライアントの種類と用途

### 1. ブラウザ用クライアント（Browser Client）

**ファイル**: `/frontend/src/libs/supabase/supabase-client.ts`

```typescript
import { Database } from '@/libs/supabase/types';
import { getEnvVar } from '@/utils/get-env-var';
import { createBrowserClient } from '@supabase/ssr';

// Create a single instance that can be reused across the app
export const supabase = createBrowserClient<Database>(
  getEnvVar(process.env.NEXT_PUBLIC_SUPABASE_URL, 'NEXT_PUBLIC_SUPABASE_URL'),
  getEnvVar(process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY, 'NEXT_PUBLIC_SUPABASE_ANON_KEY')
);
```

**特徴**:
- クライアントサイドでのみ実行される
- ブラウザのセッションストレージとクッキーを利用
- リアルタイム機能（Supabase Realtime）に対応
- RLS（Row Level Security）ポリシーを自動適用
- 単一インスタンスパターンでアプリ全体での再利用を可能にする

**使用場面**:
- クライアントコンポーネント内でのデータ操作
- リアルタイム購読（WebSocket接続）
- ユーザー認証状態の確認

### 2. サーバー用クライアント（Server Client）

**ファイル**: `/frontend/src/libs/supabase/supabase-server-client.ts`

```typescript
import { cookies } from 'next/headers';
import { Database } from '@/libs/supabase/types';
import { getEnvVar } from '@/utils/get-env-var';
import { type CookieOptions, createServerClient } from '@supabase/ssr';

export async function createSupabaseServerClient() {
  const cookieStore = await cookies();

  return createServerClient<Database>(
    getEnvVar(process.env.NEXT_PUBLIC_SUPABASE_URL, 'NEXT_PUBLIC_SUPABASE_URL'),
    getEnvVar(process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY, 'NEXT_PUBLIC_SUPABASE_ANON_KEY'),
    {
      cookies: {
        get(name: string) {
          return cookieStore.get(name)?.value;
        },
        set(name: string, value: string, options: CookieOptions) {
          cookieStore.set({ name, value, ...options });
        },
        remove(name: string, options: CookieOptions) {
          cookieStore.set({ name, value: '', ...options });
        },
      },
    }
  );
}
```

**特徴**:
- サーバーサイドレンダリング（SSR）とサーバーコンポーネントで実行
- Next.js 15のクッキー管理システムと統合
- 認証情報をHTTPヘッダーとして送信
- 関数型インターフェースでインスタンス管理を最適化
- RLSポリシーを適用した安全なデータアクセス

**使用場面**:
- サーバーコンポーネント内でのデータフェッチ
- 初期ページレンダリング時の認証状態確認
- SEOが重要なページでのデータ取得

### 3. ミドルウェア用クライアント（Middleware Client）

**ファイル**: `/frontend/src/libs/supabase/supabase-middleware-client.ts`

```typescript
import { type NextRequest, NextResponse } from 'next/server';
import { getEnvVar } from '@/utils/get-env-var';
import { createServerClient } from '@supabase/ssr';

export async function updateSession(request: NextRequest) {
  let supabaseResponse = NextResponse.next({
    request,
  });

  const supabase = createServerClient(
    getEnvVar(process.env.NEXT_PUBLIC_SUPABASE_URL, 'NEXT_PUBLIC_SUPABASE_URL'),
    getEnvVar(process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY, 'NEXT_PUBLIC_SUPABASE_URL'),
    {
      cookies: {
        getAll() {
          return request.cookies.getAll();
        },
        setAll(cookiesToSet) {
          for (const { name, value, options } of cookiesToSet) {
            request.cookies.set(name, value);
          }

          supabaseResponse = NextResponse.next({
            request,
          });

          for (const { name, value, options } of cookiesToSet) {
            supabaseResponse.cookies.set(name, value, options);
          }
        },
      },
    }
  );

  // IMPORTANT: DO NOT REMOVE auth.getUser()
  const {
    data: { user },
  } = await supabase.auth.getUser();

  return supabaseResponse;
}
```

**特徴**:
- Next.jsミドルウェア内で実行される
- リクエスト/レスポンスのクッキー管理を直接操作
- 認証セッションの自動更新
- ルートガード機能との連携（コメントアウト状態）

**使用場面**:
- リクエスト前の認証状態確認
- セッションの自動リフレッシュ
- ルーティング前の認証チェック

## 型定義とスキーマ管理

### データベース型定義

**ファイル**: `/frontend/src/libs/supabase/types.ts`

```typescript
export type Database = {
  public: {
    Tables: {
      customers: {
        Row: {
          id: string
          stripe_customer_id: string | null
        }
        Insert: {
          id: string
          stripe_customer_id?: string | null
        }
        Update: {
          id?: string
          stripe_customer_id?: string | null
        }
        Relationships: []
      }
      // ... 他のテーブル定義
    }
  }
}
```

**特徴**:
- Supabase CLIによる自動生成
- TypeScriptの型安全性を保証
- テーブル操作（Row, Insert, Update）ごとの型定義
- リレーションシップの型情報も含む

### 型生成コマンド

```bash
# package.jsonで定義されているコマンド
npm run generate-types
# 実際の実行内容
npx supabase gen types typescript --project-id wptklzekgtduiluwzhap --schema public > src/libs/supabase/types.ts
```

## 環境変数とConfiguration

### 必要な環境変数

```bash
# Supabase設定
NEXT_PUBLIC_SUPABASE_URL=https://your-project-id.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# バックエンドAPI設定
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

### 環境変数検証

**ファイル**: `/frontend/src/utils/get-env-var.ts`

```typescript
export function getEnvVar(value: string | undefined, name: string): string {
  if (!value) {
    throw new Error(`Missing required environment variable: ${name}`);
  }
  return value;
}
```

**特徴**:
- 実行時環境変数検証
- 明確なエラーメッセージ
- TypeScriptの型安全性を保証

## 認証フローとセッション管理

### クライアントサイド認証

```typescript
// useSupabaseRealtime.tsでの認証情報取得例
import { useAuth } from '@clerk/nextjs';

const { getToken } = useAuth();

// APIコール時の認証ヘッダー設定
const token = await getToken();
const response = await fetch('/api/proxy/articles/generation/start', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`,
  },
  body: JSON.stringify(requestData),
});
```

### サーバーサイド認証

```typescript
// サーバーコンポーネントでの認証状態確認
export default async function ProtectedPage() {
  const supabase = await createSupabaseServerClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect('/sign-in');
  }

  return <div>Protected content</div>;
}
```

## リアルタイム機能の実装

### Realtime購読の基本パターン

```typescript
import { supabase } from '@/libs/supabase/supabase-client';

// プロセスイベントの購読
const channel = supabase
  .channel(`process_events:process_id=eq.${processId}`)
  .on(
    'postgres_changes',
    {
      event: 'INSERT',
      schema: 'public',
      table: 'process_events',
      filter: `process_id=eq.${processId}`,
    },
    (payload) => {
      console.log('New event received:', payload);
      handleRealtimeEvent(payload.new);
    }
  )
  .subscribe();
```

### 購読の管理とクリーンアップ

```typescript
useEffect(() => {
  if (autoConnect && processId && !channelRef.current) {
    connect();
  }
  
  // クリーンアップ
  return () => {
    if (channelRef.current) {
      channelRef.current.unsubscribe();
      channelRef.current = null;
    }
  };
}, [autoConnect, processId]);
```

## パフォーマンス最適化

### 接続管理の最適化

1. **単一インスタンスパターン**
   - ブラウザクライアントは単一インスタンスを再利用
   - メモリ使用量の削減とパフォーマンス向上

2. **接続プール管理**
   - 不要な接続の自動切断
   - 再接続ロジックの実装

3. **データキャッシュ戦略**
   - フェッチしたデータの適切なキャッシュ
   - 無駄なネットワークリクエストの削減

### エラーハンドリング

```typescript
// 接続エラーの処理
const handleConnectionError = (error: Error) => {
  console.error('Supabase connection error:', error);
  
  // 再接続の試行
  if (reconnectAttempts.current < maxReconnectAttempts) {
    scheduleReconnect();
  } else {
    console.error('Max reconnection attempts reached');
  }
};
```

## ベストプラクティス

### 1. クライアント選択のガイドライン

- **ブラウザクライアント**: ユーザーインタラクション、リアルタイム機能
- **サーバークライアント**: 初期データ取得、SEO重要ページ
- **ミドルウェアクライアント**: 認証チェック、セッション管理

### 2. セキュリティ考慮事項

- RLSポリシーによるデータアクセス制御
- 環境変数の適切な管理
- 認証トークンの安全な取り扱い

### 3. デバッグとモニタリング

```typescript
// デバッグ用ログ設定
console.log('Supabase connection state:', {
  isConnected,
  isConnecting,
  processId,
  userId,
  connectionAttempts: connectionMetrics.current.connectionAttempts,
});
```

### 4. マイグレーション管理

```bash
# マイグレーション実行
npm run migration:up

# 新しいマイグレーション作成
npm run migration:new "add_new_table"

# マイグレーションの統合
npm run migration:squash
```

## トラブルシューティング

### よくある問題と解決方法

1. **認証エラー**
   - 環境変数の確認
   - トークンの有効期限チェック
   - RLSポリシーの設定確認

2. **リアルタイム接続エラー**
   - WebSocket接続の状態確認
   - プロキシ設定の確認
   - ファイアウォール設定の確認

3. **型エラー**
   - 型定義の再生成
   - スキーマ変更の反映確認

## 結論

このSupabaseクライアント設計により、Next.jsアプリケーションは環境に応じた最適化されたデータベースアクセスを実現できます。特に、SSRとクライアントサイドレンダリングの両方に対応し、リアルタイム機能も含めた包括的なソリューションを提供しています。