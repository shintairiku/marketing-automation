# メンバー・組織管理システム 実装計画

## 現状分析サマリー

| レイヤー | 現状 | 完成度 | 致命的問題 |
|---------|------|--------|-----------|
| **DB スキーマ** | テーブル4つ存在。RLS ポリシー定義済み | **30%** | `user_id` が `uuid references auth.users` → Clerk ID (text) と型不一致。RLS が `auth.uid()` 依存で Clerk 環境では常に NULL |
| **バックエンド API** | `organization/service.py` に CRUD 実装済み | **60%** | `service_role` 使用で RLS バイパスするため動作はする。`get_current_user_email()` がプレースホルダー |
| **Stripe 課金** | 個人ユーザー向けのみ | **30%** | `quantity: 1` 固定。`organization_id` なし |
| **WordPress 連携** | `wordpress_sites.user_id` で個人紐付け | **0%** | `organization_id` カラムなし |
| **フロントエンド** | メンバーページはスタブ（「準備中」表示） | **5%** | 組織 API の呼び出しゼロ |

---

## 監査結果: 既存コードの致命的問題

### 問題1: DB スキーマと Clerk ID の型不一致

既存マイグレーション `20250605152002_organizations.sql` で:

```sql
-- organizations.owner_user_id が UUID 型で auth.users を参照
owner_user_id uuid references auth.users not null

-- organization_members.user_id も同様
user_id uuid references auth.users on delete cascade

-- invitations.invited_by_user_id も同様
invited_by_user_id uuid references auth.users not null
```

**問題:** Clerk のユーザーID は `user_2y2DRx...` のような TEXT 文字列。UUID 型カラムには格納できない。

**修正:** 新しいマイグレーションで `auth.users` への FK を削除し、カラム型を TEXT に変更。

### 問題2: RLS ポリシーが完全に機能しない

全ての RLS ポリシーが `auth.uid()` に依存:

```sql
-- 例: organizations の RLS
auth.uid() = owner_user_id
```

**問題:** このシステムは Supabase Auth を使わず Clerk で認証している。`auth.uid()` は常に NULL を返すため、RLS は全行をブロックする。

**影響:** バックエンドは `service_role_key` を使用するため RLS をバイパスし動作するが、フロントエンドからの直接アクセスは不可能。

**修正:** バックエンドが `service_role` で全操作するため、RLS ポリシーは削除して簡潔にする。

### 問題3: `get_current_user_email()` プレースホルダー

```python
# backend/app/domains/organization/endpoints.py
async def get_current_user_email() -> str:
    """Get current user email from authentication token"""
    return "user@example.com"  # ← ハードコード
```

**影響:** `GET /invitations` エンドポイント（ユーザーのメール宛招待一覧）が機能しない。

**修正:** Clerk JWT からメールを取得する実装に変更。

### 問題4: service.py の `users` テーブル参照

```python
# get_organization_members() 内
result = self.supabase.table("organization_members").select(
    "*, users:user_id(email, full_name)"
).eq("organization_id", organization_id).execute()
```

**問題:** `users` テーブルは `auth.users` を指すが、Clerk ユーザーのデータはそこにない。JOIN が失敗する。

**修正:** メンバー情報は `organization_members` から取得し、ユーザー詳細（名前・メール）は Clerk API から取得するか、`organization_members` に `display_name`, `email` カラムを追加。

---

## 全体アーキテクチャ

```
オーナーがシート数を選んでチェックアウト
          ↓
 Stripe Checkout (quantity = シート数)
          ↓
 Webhook → organization_subscriptions 更新
          ↓
 オーナーがメンバーを招待（シート数以内）
          ↓
 招待メール → トークン → アカウント作成 → org_member になる
          ↓
 メンバーは組織のWordPressサイト・ブログ機能を共有利用
```

---

## Phase 0: DB マイグレーション（Clerk 互換性修正）

**目的:** 既存の組織テーブルを Clerk ID（TEXT）に対応させる

### 0-1. 新規マイグレーション

**ファイル:** `shared/supabase/migrations/20260129_fix_org_clerk_compat.sql`

```sql
-- 1. RLS ポリシーを全て削除（service_role で操作するため不要）
DROP POLICY IF EXISTS "Organization owners can manage their organizations" ON organizations;
DROP POLICY IF EXISTS "Organization members can view their organizations" ON organizations;
DROP POLICY IF EXISTS "Organization owners and admins can manage members" ON organization_members;
DROP POLICY IF EXISTS "Members can view organization memberships" ON organization_members;
DROP POLICY IF EXISTS "Organization owners and admins can manage invitations" ON invitations;
DROP POLICY IF EXISTS "Users can view invitations sent to them" ON invitations;
DROP POLICY IF EXISTS "Organization owners and admins can view subscriptions" ON organization_subscriptions;

-- 2. organization_members の FK と型を変更
ALTER TABLE organization_members DROP CONSTRAINT IF EXISTS organization_members_user_id_fkey;
ALTER TABLE organization_members ALTER COLUMN user_id TYPE text USING user_id::text;

-- 3. organizations の FK と型を変更
ALTER TABLE organizations DROP CONSTRAINT IF EXISTS organizations_owner_user_id_fkey;
ALTER TABLE organizations ALTER COLUMN owner_user_id TYPE text USING owner_user_id::text;
ALTER TABLE organizations ALTER COLUMN owner_user_id SET NOT NULL;

-- 4. invitations の FK と型を変更
ALTER TABLE invitations DROP CONSTRAINT IF EXISTS invitations_invited_by_user_id_fkey;
ALTER TABLE invitations ALTER COLUMN invited_by_user_id TYPE text USING invited_by_user_id::text;
ALTER TABLE invitations ALTER COLUMN invited_by_user_id SET NOT NULL;

-- 5. organization_members に表示用カラム追加
ALTER TABLE organization_members ADD COLUMN IF NOT EXISTS display_name text;
ALTER TABLE organization_members ADD COLUMN IF NOT EXISTS email text;

-- 6. organization_subscriptions の price_id FK を削除（prices テーブル依存を解消）
ALTER TABLE organization_subscriptions DROP CONSTRAINT IF EXISTS organization_subscriptions_price_id_fkey;

-- 7. トリガー関数を更新（owner_user_id の型変更に対応）
CREATE OR REPLACE FUNCTION handle_new_organization()
RETURNS trigger AS $$
BEGIN
  INSERT INTO organization_members (organization_id, user_id, role)
  VALUES (new.id, new.owner_user_id, 'owner');
  RETURN new;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

---

## Phase 1: Stripe シート課金の組織対応

**目的:** 「3シート分課金 → 3人分使える」を実現

### 1-1. チェックアウトの組織対応

**ファイル:** `frontend/src/app/api/subscription/checkout/route.ts`

**変更内容:**
- リクエストボディに `organizationId` と `quantity`（シート数）を追加
- `metadata` に `organization_id` を付与
- `line_items.quantity` にシート数を設定
- `organizationId` 未指定の場合は組織を自動作成

```typescript
// リクエスト
POST /api/subscription/checkout
Body: {
  organizationId?: string,  // 既存組織のID（省略時は自動作成）
  organizationName?: string, // 自動作成時の組織名
  quantity?: number,         // シート数（デフォルト: 1）
  successUrl?: string,
  cancelUrl?: string
}
```

### 1-2. Webhook の組織対応

**ファイル:** `frontend/src/app/api/subscription/webhook/route.ts`

**変更内容:**
- `metadata.organization_id` の有無で個人/組織を分岐
- 組織の場合: `organization_subscriptions` テーブルに upsert
- `quantity`（シート数）を保存

```
分岐ロジック:
if metadata.organization_id:
    → organization_subscriptions に upsert (quantity 含む)
    → organizations.stripe_customer_id を更新
else:
    → user_subscriptions に upsert (従来通り)
```

### 1-3. サブスクリプション状態APIの組織対応

**ファイル:** `frontend/src/app/api/subscription/status/route.ts`

**変更内容:**
- ユーザーの所属組織を `organization_members` から検索
- 組織の `organization_subscriptions` を取得
- レスポンスに `orgSubscription` を追加

```typescript
// レスポンス（変更後）
{
  subscription: UserSubscription,       // 個人サブスク（従来通り）
  orgSubscription: OrgSubscription | null, // 組織サブスク（NEW）
  hasAccess: boolean                    // 個人 OR 組織のいずれかで判定
}
```

### 1-4. アクセス権判定の組織対応

**ファイル:** `frontend/src/lib/subscription/index.ts`

```typescript
// NEW: 組織サブスクリプション型
export interface OrgSubscription {
  id: string;
  organization_id: string;
  status: SubscriptionStatus;
  quantity: number;
  current_period_end: string | null;
  cancel_at_period_end: boolean;
}

// NEW: 組織アクセス判定
export function hasActiveOrgAccess(orgSub: OrgSubscription | null): boolean {
  if (!orgSub) return false;
  // hasActiveAccess と同じロジック（active, canceled期間内, past_due猶予）
}
```

**ファイル:** `frontend/src/components/subscription/subscription-guard.tsx`

```typescript
// 変更後のアクセス判定
hasAccess = isPrivilegedEmail(email)
         || hasActiveAccess(userSubscription)
         || hasActiveOrgAccess(orgSubscription)  // NEW
```

---

## Phase 2: メンバー招待・管理フロントエンド

**目的:** オーナーがメンバーを招待・管理できるUI

### 2-1. メンバー設定ページ

**ファイル:** `frontend/src/app/(tools)/settings/members/page.tsx` (スタブ → 本実装)

**画面構成:**

| セクション | 内容 |
|-----------|------|
| **プラン状況** | 現在のシート数 / 使用中シート数 / 残りシート数 |
| **メンバー一覧** | 名前, メール, ロール(owner/admin/member), 参加日, 削除ボタン |
| **招待フォーム** | メールアドレス入力 + ロール選択 + 招待ボタン |
| **保留中の招待** | 送信済み招待の一覧（メール, 状態, 有効期限, キャンセル） |

### 2-2. バックエンド API 呼び出し

既存の backend API を frontend の proxy 経由で呼び出す:

```
GET    /api/proxy/organizations                    → 自分の組織一覧
POST   /api/proxy/organizations                    → 組織作成
GET    /api/proxy/organizations/{id}/members        → メンバー一覧
POST   /api/proxy/organizations/{id}/invitations    → 招待送信
PUT    /api/proxy/organizations/{id}/members/{uid}/role → ロール変更
DELETE /api/proxy/organizations/{id}/members/{uid}  → メンバー削除
GET    /api/proxy/organizations/{id}/subscription   → 組織サブスク情報
```

### 2-3. 招待フロー

```
オーナーが招待  →  Backend が invitation レコード作成（token 生成）
    ↓
招待リンクをコピー（メール送信は将来実装）
    ↓
招待された人がサインアップ → /settings/invitations で承認
    ↓
Backend が organization_members に追加（display_name, email 含む）
    ↓
シート数チェック: members.count <= subscription.quantity
    ↓
超過の場合はエラー「シートが不足しています」
```

---

## Phase 3: WordPress サイトの組織共有（後日実装）

**目的:** オーナーが接続した WordPress サイトをメンバー全員が使える

> Phase 1-2 完了後に実装。詳細は別途計画。

---

## Phase 4: 初回登録フロー統合（後日実装）

**目的:** 新規ユーザーが自然に組織を作成してシート課金できる

> Phase 1-2 完了後に実装。詳細は別途計画。

---

## 実装順序と依存関係

```
Phase 0 (DB マイグレーション) ← 最優先
  └── Clerk ID 互換性修正
        ↓
Phase 1 (Stripe シート課金)
  ├── 1-1. チェックアウト組織対応
  ├── 1-2. Webhook 組織対応
  ├── 1-3. Status API 組織対応
  └── 1-4. アクセス権判定の組織対応
        ↓
Phase 2 (メンバー管理UI)
  ├── 2-1. メンバー設定ページ
  ├── 2-2. API 呼び出し
  └── 2-3. 招待フロー
```

---

## 変更対象ファイル一覧

| Phase | ファイル | 変更内容 |
|-------|---------|---------|
| 0 | `shared/supabase/migrations/20260129_fix_org_clerk_compat.sql` | Clerk互換マイグレーション（新規） |
| 0 | `backend/app/domains/organization/endpoints.py` | `get_current_user_email()` 修正 |
| 0 | `backend/app/domains/organization/service.py` | `users` JOIN 削除、`display_name`/`email` 対応 |
| 1 | `frontend/src/app/api/subscription/checkout/route.ts` | quantity, organization_id 対応 |
| 1 | `frontend/src/app/api/subscription/webhook/route.ts` | 組織サブスク分岐 |
| 1 | `frontend/src/app/api/subscription/status/route.ts` | 組織サブスク情報追加 |
| 1 | `frontend/src/lib/subscription/index.ts` | `OrgSubscription`, `hasActiveOrgAccess()` 追加 |
| 1 | `frontend/src/components/subscription/subscription-guard.tsx` | 組織アクセス判定 |
| 2 | `frontend/src/app/(tools)/settings/members/page.tsx` | 全面実装 |

---

## 前提条件

- バックエンドの `organization/service.py` はロジック的には使えるが、`users` テーブル JOIN の修正が必要
- DB テーブルは存在するが、型変更のマイグレーションが必要
- Clerk の Organization 機能は使わず、Supabase + 自前で管理
- バックエンドは `service_role_key` で操作するため RLS は不要
- フロントエンドは proxy 経由でバックエンド API を呼び出す（既存 proxy ルートで対応済み）
