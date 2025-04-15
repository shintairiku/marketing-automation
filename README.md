# SEO記事 - セットアップガイド

このガイドでは、新大陸アプリケーションをローカル環境で構築・実行するための手順を説明する。

## 目次

1. [前提条件](#前提条件)
2. [リポジトリのクローン](#リポジトリのクローン)
3. [環境変数の設定](#環境変数の設定)
4. [Supabaseのセットアップ](#supabaseのセットアップ)
5. [Stripeのセットアップ](#stripeのセットアップ)
6. [Resendのセットアップ](#resendのセットアップ)
7. [アプリケーションの実行](#アプリケーションの実行)
8. [Stripeウェブフックの設定](#stripeウェブフックの設定)
9. [トラブルシューティング](#トラブルシューティング)

## 前提条件

以下のツールがインストールされていることを確認してください：

- [Node.js](https://nodejs.org/) (v20以上)
- [Bun](https://bun.sh/) (最新版推奨)
- [Git](https://git-scm.com/)
- [Stripe CLI](https://stripe.com/docs/stripe-cli)

## リポジトリのクローン

まず、GitHubからリポジトリをクローンします

## 環境変数の設定

アプリケーションを実行するには、環境変数を設定する必要があります。

1. プロジェクトのルートディレクトリに`.env.local`ファイルを作成します：

```bash
touch .env.local
```

2. `.env.local.example`ファイルを参考に、`.env.local`ファイルを編集します：

```
# Supabaseの設定
NEXT_PUBLIC_SUPABASE_URL=あなたのSupabase URLを入力
NEXT_PUBLIC_SUPABASE_ANON_KEY=あなたのSupabase匿名キーを入力
SUPABASE_SERVICE_ROLE_KEY=あなたのSupabaseサービスロールキーを入力
SUPABASE_DB_PASSWORD=あなたのSupabaseデータベースパスワードを入力

# Stripeの設定
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=あなたのStripe公開可能キーを入力
STRIPE_SECRET_KEY=あなたのStripeシークレットキーを入力
STRIPE_WEBHOOK_SECRET=あなたのStripeウェブフックシークレットを入力

# Resendの設定
RESEND_API_KEY=あなたのResend APIキーを入力

# サイトURL
NEXT_PUBLIC_SITE_URL=http://localhost:3000
```

各項目の値は、それぞれのサービス（Supabase、Stripe、Resend）から取得する必要があります。以下のセクションで取得方法を説明します。

## Supabaseのセットアップ

1. [Supabase](https://supabase.com)にアクセスしてアカウントを作成し、新しいプロジェクトを作成します。

2. プロジェクト作成後、「Project Settings」→「API」からSupabase URLと匿名キーを取得します。

3. 「Project Settings」→「Database」→「Database Password」から「Reset Database Password」をクリックし、新しいパスワードを生成します（特殊文字を含まないパスワードが推奨）。

4. これらの値を`.env.local`ファイルの対応する箇所に記入します。

## Stripeのセットアップ

1. [Stripe](https://stripe.com)にアクセスしてアカウントを作成します。

2. ダッシュボードの「Developers」→「API keys」から公開可能キーとシークレットキーを取得します。

3. テストモードであることを確認してください（右上に「Test mode」と表示されています）。

4. [顧客ポータル設定](https://dashboard.stripe.com/test/settings/billing/portal)にアクセスし、「Active test link」ボタンをクリックして顧客ポータルを有効化します。

5. これらの値を`.env.local`ファイルの対応する箇所に記入します。

## Resendのセットアップ

1. [Resend](https://resend.com)にアクセスしてアカウントを作成します。

2. 「API Keys」ページからAPIキーを作成します。

3. 作成したAPIキーを`.env.local`ファイルの`RESEND_API_KEY`に記入します。

4. Supabase Resend統合を有効にするには、Supabaseダッシュボードの「Integrations」から「Resend」を選択し、指示に従って設定します。

## アプリケーションの実行

環境変数の設定が完了したら、アプリケーションを実行する準備が整いました。

1. プロジェクトの依存関係をインストールします：

```bash
bun install
```

2. Supabaseデータベースマイグレーションを実行します：

まず、Supabase CLIにログインします：

```bash
bunx supabase login
```

Supabaseを初期化します：

```bash
bunx supabase init
```

`package.json`ファイルを開き、`supabase:link`コマンドの中の`UPDATE_THIS_WITH_YOUR_SUPABASE_PROJECT_ID`を実際のSupabaseプロジェクトIDに置き換えます。プロジェクトIDはSupabaseダッシュボードのプロジェクト設定で確認できます。

次に、Supabaseプロジェクトをリンクし、マイグレーションを実行します：

```bash
bun run supabase:link
bun run migration:up
```

3. Stripeの商品データをセットアップします：

`stripe-fixtures.json`ファイルが提供する商品構成を使って、Stripeに初期データを登録します：

```bash
stripe fixtures ./stripe-fixtures.json --api-key あなたのStripeシークレットキー
```

4. 開発サーバーを起動します：

```bash
bun run dev
```

これで、ブラウザで[http://localhost:3000](http://localhost:3000)にアクセスすると、アプリケーションが表示されます。

## Stripeウェブフックの設定

ローカル開発環境では、Stripeからのイベント通知を受け取るためにStripe CLIを使用します。これは、実際のStripeウェブフックをシミュレートするために必要です。

**重要**: 以下のコマンドは、アプリケーションサーバー（`bun run dev`）とは別のターミナルで実行してください。

1. まず、Stripe CLIにログインします（初回のみ）：

```bash
stripe login
```

2. ウェブフックリスナーを起動します：

```bash
stripe listen --forward-to=localhost:3000/api/webhooks
```

コマンドを実行すると、ウェブフックシークレットが表示されます。このシークレットをコピーして、`.env.local`ファイルの`STRIPE_WEBHOOK_SECRET`に設定してください。

```
> Ready! Your webhook signing secret is whsec_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

3. 別のターミナルでStripeのイベントをテストするには、以下のようなコマンドを使用できます：

```bash
stripe trigger payment_intent.succeeded
```

これにより、支払い成功イベントがシミュレートされ、アプリケーションのウェブフックエンドポイントに送信されます。

## トラブルシューティング

### Supabase接続エラー

- `NEXT_PUBLIC_SUPABASE_URL`と`NEXT_PUBLIC_SUPABASE_ANON_KEY`が正しく設定されていることを確認してください。
- Supabaseプロジェクトが正常に稼働していることを確認してください。

### Stripe接続エラー

- Stripeキーがテストモードのキーであることを確認してください。
- `STRIPE_WEBHOOK_SECRET`が正しく設定されていることを確認してください。
- Stripe CLIが正常に動作していることを確認してください。

### マイグレーションエラー

- Supabase CLIが正しくインストールされていることを確認してください。
- Supabaseプロジェクトへの正しい権限があることを確認してください。
- データベースパスワードに特殊文字が含まれている場合、問題が発生することがあります。その場合はパスワードをリセットして、特殊文字を含まないパスワードを使用してください。

----------

----------

# 開発者ガイド

このガイドでは、開発者向けにどのように開発を進めていくかについてのドキュメントになります。

## 目次

1. [プロジェクト概要](#プロジェクト概要)
2. [ディレクトリ構成](#ディレクトリ構成)
3. [App Router の基本と活用法](#app-router-の基本と活用法)
4. [新しいページの作成方法](#新しいページの作成方法)
5. [APIルートの作成と活用](#apiルートの作成と活用)
6. [認証フローの仕組み](#認証フローの仕組み)
7. [決済機能の実装](#決済機能の実装)
8. [Supabaseとのデータ連携](#supabaseとのデータ連携)
9. [UIコンポーネントの活用](#uiコンポーネントの活用)
10. [スタイリングの方法](#スタイリングの方法)
11. [機能拡張の実践例](#機能拡張の実践例)

## プロジェクト概要

本テンプレートは、AIを活用してSEO最適化された記事を自動生成するサービスです。Next.js 15、Supabase、Stripe、Tailwind CSSなどを採用しており、サブスクリプションモデルのSaaSアプリケーションのテンプレートとして設計されています。

このプロジェクトは以下の主要な機能を持っています：

- ユーザー認証システム（Supabase Auth）
- サブスクリプション管理（Stripe）

## ディレクトリ構成

プロジェクトは機能ごとにディレクトリを分割する「Feature-based」構造を採用しています。主要なディレクトリとその役割は以下の通りです：

```
/src
  /app                  # Next.js App Router ページ
    /(account)          # アカウント関連ページ
    /(article-generation) # 記事生成関連ページ
    /(auth)             # 認証関連ページ
    /(dashboard)        # ダッシュボード関連ページ
    /api                # APIエンドポイント
      /webhooks         # Stripe Webhookなど
  /components           # 共通UIコンポーネント
    /ui                 # shadcn/uiコンポーネント
  /features             # 機能別モジュール
    /account            # アカウント管理機能
    /article-editing    # 記事編集機能
    /article-generation # 記事生成機能
    /emails             # メールテンプレート
    /pricing            # 料金プラン機能
  /libs                 # 外部サービス連携
    /resend             # メール送信
    /stripe             # 決済処理
    /supabase           # データベース
  /styles               # グローバルスタイル
  /types                # 型定義
  /utils                # ユーティリティ関数
```

この構造の最大の利点は、関連する機能を一つの場所にまとめることで、コードの見通しが良くなり、メンテナンス性が向上することです。

## App Router の基本と活用法

Next.js 15のApp Routerは、ファイルシステムベースのルーティングを提供します。`src/app`ディレクトリ内のフォルダ構造がそのままURLパスになります。

### グループルーティング

カッコで囲まれたディレクトリ（例：`(account)`）はグループルーティングを表し、URLパスには影響しません。これにより、関連する機能を論理的にグループ化できます。

```
/src/app/(account)/account/page.tsx → /account
/src/app/(account)/manage-subscription/route.ts → /manage-subscription
```

### レイアウト共有

`layout.tsx`ファイルを配置することで、複数のページ間でレイアウトを共有できます。例えば、`/src/app/(dashboard)/layout.tsx`はダッシュボード関連のすべてのページで共通のレイアウトを提供します。

```tsx
// src/app/(dashboard)/layout.tsx
export default function DashboardLayout({ children }: PropsWithChildren) {
  return (
    <div className="flex h-screen w-full overflow-hidden bg-black">
      {/* サイドバー */}
      <Sidebar />
      
      {/* メインコンテンツエリア */}
      <div className="flex-1 overflow-auto">
        {children}
      </div>
    </div>
  );
}
```

### ページの基本構造

基本的な`page.tsx`は以下のような構造になります：

```tsx
// Client Componentの場合
'use client';

import { useState } from 'react';

export default function MyPage() {
  const [data, setData] = useState(null);
  
  return (
    <div>
      {/* ページコンテンツ */}
    </div>
  );
}

// Server Componentの場合
export default async function MyServerPage() {
  const data = await fetchSomeData();
  
  return (
    <div>
      {/* サーバーでレンダリングされるコンテンツ */}
    </div>
  );
}
```

## 新しいページの作成方法

新しいページを追加するプロセスを見ていきましょう。例として、よくある質問（FAQ）ページを作成します。

### 1. ページファイルの作成

```tsx
// src/app/faq/page.tsx
import { Container } from '@/components/container';

export default function FAQPage() {
  return (
    <Container className="py-16">
      <h1 className="mb-8">よくある質問</h1>
      
      <div className="space-y-8">
        <div className="rounded-lg border border-zinc-800 bg-black p-6">
          <h2 className="text-xl font-semibold mb-4">サービスについて</h2>
          <div className="space-y-4">
            <div>
              <h3 className="font-medium mb-2">Q: AI生成記事はSEOに効果がありますか？</h3>
              <p className="text-gray-400">
                A: はい、新大陸が生成する記事は最新のSEOベストプラクティスに基づいて最適化されています。
              </p>
            </div>
            {/* 他のQ&A */}
          </div>
        </div>
      </div>
    </Container>
  );
}
```

### 2. ナビゲーションへの追加

新しいページをヘッダーナビゲーションに追加したい場合は、`src/app/navigation.tsx`を編集します。

```tsx
// src/app/navigation.tsx内のリンク追加
<Link href="/faq" className="hover:text-white">
  よくある質問
</Link>
```

### 3. 動的ルーティング

IDやスラッグに基づいた動的ページを作成する場合：

```
/src/app/articles/[id]/page.tsx → /articles/123
```

```tsx
// src/app/articles/[id]/page.tsx
export default function ArticlePage({ params }: { params: { id: string } }) {
  return (
    <div>
      <h1>記事ID: {params.id}</h1>
      {/* 記事の詳細コンテンツ */}
    </div>
  );
}
```

## APIルートの作成と活用

Next.js 13以降、APIルートは`app`ディレクトリ内の`route.ts`ファイルで定義します。

### 基本的なAPIルート

```tsx
// src/app/api/example/route.ts
import { NextResponse } from 'next/server';

export async function GET(request: Request) {
  // クエリパラメータの取得
  const { searchParams } = new URL(request.url);
  const id = searchParams.get('id');
  
  // データ処理
  const data = { message: `Hello ${id || 'World'}` };
  
  // レスポンス返却
  return NextResponse.json(data);
}

export async function POST(request: Request) {
  const body = await request.json();
  
  // データ処理
  const result = await processData(body);
  
  return NextResponse.json(result);
}
```

### Server Actionsの活用

Next.js 14以降、フォーム送信などにはServer Actionsが推奨されています。

```tsx
// src/app/contact/actions.ts
'use server';

import { resendClient } from '@/libs/resend/resend-client';
import ContactEmail from '@/features/emails/contact';

export async function submitContactForm(formData: FormData) {
  const name = formData.get('name') as string;
  const email = formData.get('email') as string;
  const message = formData.get('message') as string;
  
  try {
    await resendClient.emails.send({
      from: 'no-reply@yourdomain.com',
      to: 'support@yourdomain.com',
      subject: 'お問い合わせが届きました',
      react: <ContactEmail name={name} email={email} message={message} />,
    });
    
    return { success: true };
  } catch (error) {
    console.error('メール送信エラー:', error);
    return { success: false, error: 'メール送信に失敗しました' };
  }
}
```

```tsx
// src/app/contact/page.tsx
'use client';

import { useFormState } from 'react-dom';
import { submitContactForm } from './actions';

export default function ContactPage() {
  const [state, formAction] = useFormState(submitContactForm, null);
  
  return (
    <form action={formAction}>
      {/* フォーム要素 */}
      <button type="submit">送信</button>
      {state?.error && <p className="text-red-500">{state.error}</p>}
    </form>
  );
}
```

### WebhookエンドポイントとStripe連携

Stripeなどの外部サービスからのWebhookを処理するAPIルートもあります：

```tsx
// src/app/api/webhooks/route.ts
import Stripe from 'stripe';
import { NextResponse } from 'next/server';
import { stripeAdmin } from '@/libs/stripe/stripe-admin';

export async function POST(req: Request) {
  const body = await req.text();
  const sig = req.headers.get('stripe-signature') as string;
  const webhookSecret = process.env.STRIPE_WEBHOOK_SECRET!;
  
  try {
    const event = stripeAdmin.webhooks.constructEvent(body, sig, webhookSecret);
    
    // イベントタイプに応じた処理
    switch (event.type) {
      case 'customer.subscription.created':
        // サブスクリプション作成時の処理
        await handleSubscriptionCreated(event.data.object);
        break;
      // 他のイベント処理
    }
    
    return NextResponse.json({ received: true });
  } catch (error) {
    console.error('Webhook error:', error);
    return NextResponse.json({ error: 'Webhook処理エラー' }, { status: 400 });
  }
}
```

## 認証フローの仕組み

新大陸の認証はSupabase Authを使用しています。認証フローは主に以下のファイルで管理されています：

- `src/app/(auth)/auth-actions.ts` - サインイン、サインアウトなどのアクション
- `src/app/(auth)/auth-ui.tsx` - 認証UI
- `src/app/(auth)/login/page.tsx` - ログインページ
- `src/app/(auth)/signup/page.tsx` - サインアップページ
- `src/app/(auth)/auth/callback/route.ts` - OAuth/メール認証のコールバック処理

### 認証アクションの実装

```tsx
// src/app/(auth)/auth-actions.ts
'use server';

import { createSupabaseServerClient } from '@/libs/supabase/supabase-server-client';

export async function signInWithEmail(email: string) {
  const supabase = await createSupabaseServerClient();

  const { error } = await supabase.auth.signInWithOtp({
    email,
    options: {
      emailRedirectTo: `${origin}/auth/callback`,
    },
  });

  return { error };
}
```

### 認証状態の取得

```tsx
// src/features/account/controllers/get-session.ts
import { createSupabaseServerClient } from '@/libs/supabase/supabase-server-client';

export async function getSession() {
  const supabase = await createSupabaseServerClient();
  const { data, error } = await supabase.auth.getSession();
  
  if (error) {
    console.error(error);
  }
  
  return data.session;
}
```

### ミドルウェアでの認証状態管理

`src/middleware.ts`ファイルは、リクエスト間でSupabaseのセッション状態を維持する役割を果たします。

## 決済機能の実装

Stripe連携の主要な部分は以下のディレクトリとファイルにあります：

- `src/libs/stripe/stripe-admin.ts` - Stripe APIクライアント
- `src/features/pricing/actions/create-checkout-action.ts` - 決済フロー開始
- `src/features/pricing/components/price-card.tsx` - 料金プラン表示
- `src/app/api/webhooks/route.ts` - Stripe Webhook処理

### 新しい決済プランの追加

新しい料金プランを追加するには、以下の手順を踏みます：

1. `stripe-fixtures.json`に新しいプランを追加
2. Stripe CLIで更新を適用：`stripe fixtures ./stripe-fixtures.json --api-key YOUR_STRIPE_SK`
3. Webhookを通じてデータがSupabaseに同期されるのを確認

## Supabaseとのデータ連携

Supabaseとの連携は以下のファイルで管理されています：

- `src/libs/supabase/supabase-server-client.ts` - サーバーサイドでのSupabase接続
- `src/libs/supabase/supabase-admin.ts` - 管理者権限でのSupabase操作
- `src/libs/supabase/types.ts` - データベース型定義

### データの取得例

```tsx
// src/features/account/controllers/get-subscription.ts
import { createSupabaseServerClient } from '@/libs/supabase/supabase-server-client';

export async function getSubscription() {
  const supabase = await createSupabaseServerClient();

  const { data, error } = await supabase
    .from('subscriptions')
    .select('*, prices(*, products(*))')
    .in('status', ['trialing', 'active'])
    .maybeSingle();

  if (error) {
    console.error(error);
  }

  return data;
}
```

### データベーススキーマの更新

データベーススキーマを変更するには、マイグレーションを使用します：

1. 新しいマイグレーションファイルを作成：`bun run migration:new add_new_table`
2. `supabase/migrations`ディレクトリに生成されたSQLファイルを編集
3. マイグレーションを適用：`bun run migration:up`

## UIコンポーネントの活用

プロジェクトはshadcn/uiを使用し、再利用可能なコンポーネントを提供しています。

### 標準コンポーネントの利用

```tsx
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';

export function MyForm() {
  return (
    <form className="space-y-4">
      <div>
        <label htmlFor="name">名前</label>
        <Input id="name" name="name" />
      </div>
      <div>
        <label htmlFor="message">メッセージ</label>
        <Textarea id="message" name="message" />
      </div>
      <Button type="submit">送信</Button>
    </form>
  );
}
```

### 新しいコンポーネントの作成

機能ごとに新しいコンポーネントを作成する場合：

```tsx
// src/features/my-feature/components/my-component.tsx
'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';

interface MyComponentProps {
  initialValue: string;
  onSubmit: (value: string) => void;
}

export function MyComponent({ initialValue, onSubmit }: MyComponentProps) {
  const [value, setValue] = useState(initialValue);
  
  return (
    <div className="p-4 border rounded-md">
      <input
        value={value}
        onChange={(e) => setValue(e.target.value)}
        className="border p-2 w-full mb-4"
      />
      <Button onClick={() => onSubmit(value)}>
        保存
      </Button>
    </div>
  );
}
```

## スタイリングの方法

プロジェクトはTailwind CSSを使用しています。

### グローバルスタイル

グローバルスタイルは`src/styles/globals.css`で定義されています。

### テーマのカスタマイズ

テーマの色やその他の設定は`tailwind.config.ts`で調整できます：

```tsx
// tailwind.config.ts
import type { Config } from 'tailwindcss';

const config: Config = {
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#5046e4',
          dark: '#4039b5',
        },
        // 他の色
      },
      // その他のカスタマイズ
    },
  },
  // プラグインなど
};

export default config;
```

### ユーティリティ関数

`cn`関数を使用して条件付きクラス名を適用します：

```tsx
import { cn } from '@/utils/cn';

function MyButton({ variant = 'default', className, ...props }) {
  return (
    <button
      className={cn(
        "px-4 py-2 rounded-md",
        variant === 'primary' && "bg-blue-500 text-white",
        variant === 'secondary' && "bg-gray-200 text-gray-800",
        className
      )}
      {...props}
    />
  );
}
```

## 機能拡張の実践例

このセクションでは、既存のテンプレートを拡張して新機能を追加する例を紹介します。

### 例: 記事のエクスポート機能の追加

1. まず、必要な型定義を追加します：

```tsx
// src/features/article-generation/types/index.ts に追加
export type ExportFormat = 'html' | 'markdown' | 'pdf' | 'word';

export interface ExportOptions {
  format: ExportFormat;
  includeMetadata: boolean;
}
```

2. エクスポート用のコントローラーを作成します：

```tsx
// src/features/article-generation/controllers/export-article.ts
import { GeneratedArticle, ExportFormat } from '../types';

export async function exportArticle(article: GeneratedArticle, format: ExportFormat) {
  switch (format) {
    case 'html':
      return generateHtml(article);
    case 'markdown':
      return generateMarkdown(article);
    case 'pdf':
      return await generatePdf(article);
    case 'word':
      return await generateWord(article);
    default:
      throw new Error(`未対応のフォーマット: ${format}`);
  }
}

// HTMLの生成
function generateHtml(article: GeneratedArticle) {
  let html = `<!DOCTYPE html>\n<html lang="ja">\n<head>\n...`;
  // HTMLの生成ロジック
  return html;
}

// その他のフォーマット生成関数
```

3. UIコンポーネントを作成します：

```tsx
// src/features/article-generation/components/export-dialog.tsx
'use client';

import { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { ExportFormat, GeneratedArticle } from '../types';
import { exportArticle } from '../controllers/export-article';

interface ExportDialogProps {
  article: GeneratedArticle;
  isOpen: boolean;
  onClose: () => void;
}

export function ExportDialog({ article, isOpen, onClose }: ExportDialogProps) {
  const [format, setFormat] = useState<ExportFormat>('html');
  const [isLoading, setIsLoading] = useState(false);
  
  async function handleExport() {
    setIsLoading(true);
    try {
      const content = await exportArticle(article, format);
      
      // ダウンロード処理
      const blob = new Blob([content], { type: getContentType(format) });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${article.title.replace(/\s+/g, '-').toLowerCase()}.${getFileExtension(format)}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      
      onClose();
    } catch (error) {
      console.error('エクスポートエラー:', error);
    } finally {
      setIsLoading(false);
    }
  }
  
  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>記事のエクスポート</DialogTitle>
        </DialogHeader>
        
        <div className="py-4">
          <div className="space-y-4">
            <div>
              <label className="block mb-2">フォーマット</label>
              <select
                value={format}
                onChange={(e) => setFormat(e.target.value as ExportFormat)}
                className="w-full p-2 border rounded"
              >
                <option value="html">HTML</option>
                <option value="markdown">Markdown</option>
                <option value="pdf">PDF</option>
                <option value="word">Word</option>
              </select>
            </div>
          </div>
        </div>
        
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={onClose}>
            キャンセル
          </Button>
          <Button onClick={handleExport} disabled={isLoading}>
            {isLoading ? 'エクスポート中...' : 'エクスポート'}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

// ヘルパー関数
function getContentType(format: ExportFormat) {
  switch (format) {
    case 'html': return 'text/html';
    case 'markdown': return 'text/markdown';
    case 'pdf': return 'application/pdf';
    case 'word': return 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';
    default: return 'text/plain';
  }
}

function getFileExtension(format: ExportFormat) {
  switch (format) {
    case 'html': return 'html';
    case 'markdown': return 'md';
    case 'pdf': return 'pdf';
    case 'word': return 'docx';
    default: return 'txt';
  }
}
```

4. この機能を記事プレビューコンポーネントに統合します：

```tsx
// src/features/article-generation/components/article-preview.tsx を編集
import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { ExportDialog } from './export-dialog';

export function ArticlePreview({ article, onStartChat }: ArticlePreviewProps) {
  const [isExportDialogOpen, setIsExportDialogOpen] = useState(false);
  
  // 既存のコード...
  
  return (
    <div className="w-full space-y-6">
      <div className="flex items-center justify-between">
        {/* 既存のコントロール */}
        <Button variant="outline" onClick={() => setIsExportDialogOpen(true)}>
          エクスポート
        </Button>
      </div>
      
      {/* 既存のプレビュー表示 */}
      
      {/* エクスポートダイアログ */}
      <ExportDialog
        article={article}
        isOpen={isExportDialogOpen}
        onClose={() => setIsExportDialogOpen(false)}
      />
    </div>
  );
}
```

---
