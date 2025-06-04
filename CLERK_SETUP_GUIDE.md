# Clerk組織機能設定ガイド

## 1. Clerkダッシュボードでの組織機能有効化

### ステップ1: Clerkダッシュボードにアクセス
1. [Clerk Dashboard](https://dashboard.clerk.com/) にログイン
2. 対象プロジェクトを選択

### ステップ2: 組織機能を有効化
1. 左サイドバーの **Configure** → **Settings** をクリック
2. **Features** セクションで **Organizations** を有効化
3. **Save** をクリック

### ステップ3: 組織設定の詳細設定
1. 左サイドバーの **Configure** → **Organizations** をクリック
2. 以下の設定を行う：

#### 基本設定
- **Maximum allowed organizations per user**: `10` (デフォルト)
- **Maximum allowed memberships per organization**: `無制限` (Pro plan)
- **Enable organization domains**: `無効` (今回は不要)

#### 権限設定
- **Default role for new members**: `member`
- **Allow admins to delete organization**: `有効`
- **Allow members to leave organization**: `有効`

#### 招待設定
- **Enable organization invitations**: `有効`
- **Invitation expiration**: `7日`
- **Allow domain-based auto-join**: `無効`

### ステップ4: Webhook設定（組織イベント用）
1. 左サイドバーの **Configure** → **Webhooks** をクリック
2. **Add Endpoint** をクリック
3. 以下を設定：
   - **Endpoint URL**: `https://your-domain.com/api/clerk-webhooks`
   - **Events**: 以下をすべて選択
     - `organization.created`
     - `organization.updated`
     - `organization.deleted`
     - `organizationMembership.created`
     - `organizationMembership.updated`
     - `organizationMembership.deleted`
     - `organizationInvitation.created`
     - `organizationInvitation.accepted`
     - `organizationInvitation.revoked`

### ステップ5: 環境変数の設定
以下の環境変数を `.env` と `.env.local` に追加：

```bash
# Clerk 設定
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_xxx
CLERK_SECRET_KEY=sk_test_xxx
CLERK_WEBHOOK_SECRET=whsec_xxx

# Clerk 組織機能用
NEXT_PUBLIC_CLERK_ORGANIZATION_PROFILE_URL="/organization-profile"
NEXT_PUBLIC_CLERK_CREATE_ORGANIZATION_URL="/create-organization"
```

## 2. フロントエンド設定の確認

### middleware.ts の確認
```typescript
import { clerkMiddleware, createRouteMatcher } from '@clerk/nextjs/server';

const isProtectedRoute = createRouteMatcher([
  '/dashboard(.*)',
  '/generate(.*)',
  '/account(.*)',
  '/organization(.*)', // 組織関連ページを保護
]);

export default clerkMiddleware((auth, req) => {
  if (isProtectedRoute(req)) auth().protect();
});

export const config = {
  matcher: ["/((?!.+\\.[\\w]+$|_next).*)", "/", "/(api|trpc)(.*)"],
};
```

### Clerk Provider設定の確認
layout.tsx で以下が設定されていることを確認：

```typescript
import { ClerkProvider } from '@clerk/nextjs';
import { jaJP } from "@clerk/localizations";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <ClerkProvider localization={jaJP}>
      {/* ... */}
    </ClerkProvider>
  );
}
```

## 3. 組織関連ページの作成

### 組織プロフィールページ
`src/app/organization-profile/[[...organization-profile]]/page.tsx`:
```typescript
import { OrganizationProfile } from "@clerk/nextjs";

export default function OrganizationProfilePage() {
  return (
    <div className="flex justify-center py-8">
      <OrganizationProfile />
    </div>
  );
}
```

### 組織作成ページ
`src/app/create-organization/[[...create-organization]]/page.tsx`:
```typescript
import { CreateOrganization } from "@clerk/nextjs";

export default function CreateOrganizationPage() {
  return (
    <div className="flex justify-center py-8">
      <CreateOrganization />
    </div>
  );
}
```

## 4. ClerkのWebhook処理実装

### Webhookエンドポイントの作成
`src/app/api/clerk-webhooks/route.ts`:
```typescript
import { headers } from 'next/headers';
import { NextRequest, NextResponse } from 'next/server';
import { Webhook } from 'svix';
import { supabaseAdminClient } from '@/libs/supabase/supabase-admin';

const webhookSecret = process.env.CLERK_WEBHOOK_SECRET;

export async function POST(req: NextRequest) {
  if (!webhookSecret) {
    throw new Error('CLERK_WEBHOOK_SECRET is required');
  }

  const headerPayload = headers();
  const svix_id = headerPayload.get('svix-id');
  const svix_timestamp = headerPayload.get('svix-timestamp');
  const svix_signature = headerPayload.get('svix-signature');

  if (!svix_id || !svix_timestamp || !svix_signature) {
    return new Response('Error occured -- no svix headers', {
      status: 400,
    });
  }

  const payload = await req.json();
  const body = JSON.stringify(payload);

  const wh = new Webhook(webhookSecret);

  let evt;

  try {
    evt = wh.verify(body, {
      'svix-id': svix_id,
      'svix-timestamp': svix_timestamp,
      'svix-signature': svix_signature,
    });
  } catch (err) {
    console.error('Error verifying webhook:', err);
    return new Response('Error occured', {
      status: 400,
    });
  }

  const { type, data } = evt;

  switch (type) {
    case 'organization.created':
      await handleOrganizationCreated(data);
      break;
    case 'organization.updated':
      await handleOrganizationUpdated(data);
      break;
    case 'organization.deleted':
      await handleOrganizationDeleted(data);
      break;
    case 'organizationMembership.created':
      await handleMembershipCreated(data);
      break;
    case 'organizationMembership.updated':
      await handleMembershipUpdated(data);
      break;
    case 'organizationMembership.deleted':
      await handleMembershipDeleted(data);
      break;
    // ... その他のイベント
  }

  return NextResponse.json({ received: true });
}

async function handleOrganizationCreated(data: any) {
  const { id, name, slug, created_by } = data;
  
  // Supabaseに組織を作成
  const { error } = await supabaseAdminClient
    .from('organizations')
    .insert({
      id,
      name,
      slug,
      owner_user_id: created_by,
      max_seats: 2, // デフォルト最小シート数
      used_seats: 1, // オーナー分
    });

  if (error) {
    console.error('Failed to create organization in Supabase:', error);
  }
}

// ... その他のハンドラー関数
```

## 5. 次のステップ

1. ✅ Clerkダッシュボードで組織機能を有効化
2. ⏳ Stripe商品・価格設定
3. ⏳ Supabaseマイグレーション実行
4. ⏳ テスト実行

この設定完了後、組織の作成・管理・招待機能が利用可能になります。