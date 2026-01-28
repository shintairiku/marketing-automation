# メンバー・組織管理システム 実装計画

## 現状分析サマリー

| レイヤー | 現状 | 完成度 |
|---------|------|--------|
| **DB スキーマ** | `organizations`, `organization_members`, `invitations`, `organization_subscriptions` テーブルが既に存在。RLS ポリシーも定義済み | **80%** |
| **バックエンド API** | `organization/service.py` に CRUD, メンバー管理, 招待, サブスクリプション取得が実装済み | **70%** |
| **Stripe 課金** | 個人ユーザー向けのみ。`user_subscriptions` テーブルのみ更新。シート数(`quantity`)の概念なし | **30%** |
| **WordPress 連携** | `wordpress_sites.user_id` で個人紐付け。組織共有なし | **0%** |
| **フロントエンド** | メンバーページはスタブ（「準備中」表示）。請求ページは個人のみ | **15%** |

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

## Phase 1: Stripe シート課金の組織対応

**目的:** 「3シート分課金 → 3人分使える」を実現

### 1-1. チェックアウトの組織対応

**ファイル:** `frontend/src/app/api/subscription/checkout/route.ts`

- リクエストに `organizationId` と `quantity`（シート数）を追加
- `metadata` に `organization_id` を付与
- `line_items.quantity` にシート数を設定
- 新規の場合は `organizations` テーブルに自動作成

```
POST /api/subscription/checkout
Body: { organizationId?: string, quantity: number, successUrl, cancelUrl }
```

### 1-2. Webhook の組織対応

**ファイル:** `frontend/src/app/api/subscription/webhook/route.ts`

- `metadata.organization_id` の有無で個人/組織を分岐
- 組織の場合: `organization_subscriptions` テーブルに upsert
- `quantity`（シート数）を保存
- 組織の全メンバーのアクセス権に反映

```
# 分岐ロジック
if metadata.organization_id:
    → organization_subscriptions に upsert (quantity 含む)
else:
    → user_subscriptions に upsert (従来通り)
```

### 1-3. アクセス権判定の組織対応

**ファイル:** `frontend/src/lib/subscription/index.ts`, `frontend/src/components/subscription/subscription-guard.tsx`

- `hasActiveAccess()` に組織サブスクリプションチェックを追加
- ユーザーが所属する組織のサブスクが active なら access = true
- `GET /api/subscription/status` を拡張し、組織サブスクも返す

```typescript
// 現在
hasAccess = isPrivilegedEmail(email) || hasActiveAccess(userSubscription)

// 変更後
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
| **シート追加** | 足りない場合 → Stripe で quantity 変更（アップグレード） |

### 2-2. バックエンド API 呼び出し

既存の backend API を frontend の proxy 経由で呼び出す:

```
GET    /api/proxy/organizations                    → 自分の組織一覧
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
メール送信（将来的に。まずは招待リンクコピー）
    ↓
招待された人がサインアップ → /settings/invitations で承認
    ↓
Backend が organization_members に追加
    ↓
シート数チェック: members.count <= subscription.quantity
    ↓
超過の場合はエラー「シートが不足しています」
```

---

## Phase 3: WordPress サイトの組織共有

**目的:** オーナーが接続した WordPress サイトをメンバー全員が使える

### 3-1. DB マイグレーション

```sql
ALTER TABLE wordpress_sites
  ADD COLUMN organization_id UUID REFERENCES organizations(id);

-- organization_id がある場合、そのorgのメンバー全員がアクセス可能
CREATE POLICY "Org members can access org WordPress sites" ON wordpress_sites
  FOR SELECT USING (
    user_id = auth.uid()::text
    OR organization_id IN (
      SELECT organization_id FROM organization_members
      WHERE user_id = auth.uid()
    )
  );
```

### 3-2. バックエンド変更

**ファイル:** `backend/app/domains/blog/endpoints.py`

- `GET /blog/sites` → ユーザー個人のサイト + 所属組織のサイトを両方返す
- `POST /blog/sites` → 作成時に `organization_id` を指定可能
- WordPress 連携設定ページで「組織で共有」トグルを追加

### 3-3. ブログ生成の共有

- `blog_generation_states` にも `organization_id` を追加（将来）
- メンバーが生成した記事も組織の履歴として閲覧可能に

---

## Phase 4: 初回登録フロー統合

**目的:** 新規ユーザーが自然に組織を作成してシート課金できる

### 4-1. サインアップ後の導線

```
サインアップ → /blog/new にリダイレクト
    ↓
WordPress 未連携の場合 → WordPress 連携設定に誘導
    ↓
サブスク未加入の場合 → 料金ページに誘導
    ↓
料金ページでシート数を選択 → チェックアウト
    ↓
チェックアウト完了 → 組織自動作成 + サブスク紐付け
    ↓
/settings/members でメンバー招待可能に
```

### 4-2. 料金ページの更新

**ファイル:** `frontend/src/app/(marketing)/pricing/page.tsx`

- シート数選択UI追加（1〜10人のスライダーまたはドロップダウン）
- 「月額 ¥29,800 × シート数」の表示
- チェックアウト時に `quantity` を渡す

---

## Phase 5: ミドルウェア・アクセス制御の統合

### 5-1. サイドバー

**ファイル:** `frontend/src/components/display/sidebar.tsx`

- 組織のサブスクが active → 全メンバーがブログAI + 設定を利用可能
- 既存の `isPrivilegedEmail` チェックに加え、組織メンバーかどうかもチェック

### 5-2. SubscriptionGuard

**ファイル:** `frontend/src/components/subscription/subscription-guard.tsx`

```typescript
// 現在
hasAccess = isPrivilegedEmail(email) || hasActiveAccess(userSubscription)

// 変更後
hasAccess = isPrivilegedEmail(email)
         || hasActiveAccess(userSubscription)
         || hasActiveOrgAccess(orgSubscription)  // NEW
```

---

## 実装順序と依存関係

```
Phase 1 (Stripe シート課金)
  ├── 1-1. チェックアウト組織対応
  ├── 1-2. Webhook 組織対応
  └── 1-3. アクセス権判定の組織対応
        ↓
Phase 2 (メンバー管理UI)
  ├── 2-1. メンバー設定ページ
  ├── 2-2. API 呼び出し
  └── 2-3. 招待フロー
        ↓
Phase 3 (WordPress 共有)
  ├── 3-1. DB マイグレーション
  ├── 3-2. バックエンド変更
  └── 3-3. ブログ生成共有
        ↓
Phase 4 (初回登録フロー)
  ├── 4-1. サインアップ導線
  └── 4-2. 料金ページ更新
        ↓
Phase 5 (アクセス制御統合)
  ├── 5-1. サイドバー
  └── 5-2. SubscriptionGuard
```

---

## 変更対象ファイル一覧

| Phase | ファイル | 変更内容 |
|-------|---------|---------|
| 1 | `frontend/src/app/api/subscription/checkout/route.ts` | quantity, organization_id 対応 |
| 1 | `frontend/src/app/api/subscription/webhook/route.ts` | 組織サブスク分岐 |
| 1 | `frontend/src/app/api/subscription/status/route.ts` | 組織サブスク情報追加 |
| 1 | `frontend/src/lib/subscription/index.ts` | `hasActiveOrgAccess()` 追加 |
| 1 | `frontend/src/components/subscription/subscription-guard.tsx` | 組織アクセス判定 |
| 2 | `frontend/src/app/(tools)/settings/members/page.tsx` | 全面実装 |
| 2 | `frontend/src/app/api/proxy/[...path]/route.ts` | 既存proxy で対応済み（確認） |
| 3 | `shared/supabase/migrations/YYYYMMDD_wordpress_org.sql` | 新規マイグレーション |
| 3 | `backend/app/domains/blog/endpoints.py` | org サイト取得 |
| 4 | `frontend/src/app/(marketing)/pricing/page.tsx` | シート数選択UI |
| 5 | `frontend/src/components/display/sidebar.tsx` | org アクセス判定追加 |

---

## 前提条件

- バックエンドの `organization/service.py` と `organization/endpoints.py` は既に実装済み → そのまま活用
- DB テーブル (`organizations`, `organization_members`, `invitations`, `organization_subscriptions`) は既に存在 → マイグレーション不要（WordPress の `organization_id` 追加のみ必要）
- Clerk の Organization 機能は使わず、Supabase + 自前で管理する方針（Clerk org sync は将来検討）

---

## 既存コードベース 詳細リファレンス

### DB スキーマ（既存）

**ファイル:** `shared/supabase/migrations/20250605152002_organizations.sql`

```sql
-- organizations テーブル
create table organizations (
  id uuid default gen_random_uuid() primary key,
  name text not null,
  owner_user_id uuid references auth.users not null,
  clerk_organization_id text unique,
  stripe_customer_id text,
  created_at timestamptz,
  updated_at timestamptz
);

-- organization_members テーブル
create type organization_role as enum ('owner', 'admin', 'member');
create table organization_members (
  organization_id uuid references organizations(id) on delete cascade,
  user_id uuid references auth.users on delete cascade,
  primary key (organization_id, user_id),
  role organization_role not null default 'member',
  clerk_membership_id text,
  joined_at timestamptz
);

-- invitations テーブル
create type invitation_status as enum ('pending', 'accepted', 'declined', 'expired');
create table invitations (
  id uuid primary key,
  organization_id uuid references organizations(id) on delete cascade,
  email text not null,
  role organization_role default 'member',
  status invitation_status default 'pending',
  invited_by_user_id uuid references auth.users,
  token text unique not null,
  expires_at timestamptz,  -- 7日間
  created_at timestamptz
);

-- organization_subscriptions テーブル
create table organization_subscriptions (
  id text primary key,            -- Stripe subscription ID
  organization_id uuid references organizations(id) on delete cascade,
  status subscription_status,
  metadata jsonb,
  price_id text,
  quantity integer default 1,     -- シート数
  cancel_at_period_end boolean,
  current_period_start timestamptz,
  current_period_end timestamptz,
  -- ...その他タイムスタンプ
);
```

**RLS ポリシー:** オーナー/管理者はフル操作、メンバーは閲覧のみ。トリガーで組織作成時にオーナーを自動追加。

### バックエンド API（既存）

**ファイル:** `backend/app/domains/organization/service.py`

```
OrganizationService:
  create_organization(user_id, data)         → 組織作成
  get_organization(org_id, user_id)          → 組織取得
  get_user_organizations(user_id)            → ユーザーの組織一覧
  update_organization(org_id, user_id, data) → 組織更新
  delete_organization(org_id, user_id)       → 組織削除
  get_organization_members(org_id, user_id)  → メンバー一覧
  update_member_role(org_id, mid, role, req) → ロール変更
  remove_member(org_id, mid, req)            → メンバー削除
  create_invitation(org_id, data, inviter)   → 招待作成
  get_user_invitations(email)                → 招待一覧
  respond_to_invitation(token, resp, uid)    → 招待承諾/拒否
  get_organization_subscription(org_id, uid) → 組織サブスク取得
```

**ファイル:** `backend/app/domains/organization/endpoints.py`

```
POST   /organizations
GET    /organizations
GET    /organizations/{id}
PUT    /organizations/{id}
DELETE /organizations/{id}
GET    /organizations/{id}/members
PUT    /organizations/{id}/members/{user_id}/role
DELETE /organizations/{id}/members/{user_id}
POST   /organizations/{id}/invitations
GET    /invitations
POST   /invitations/respond
GET    /organizations/{id}/subscription
```

### Stripe 課金（既存・個人のみ）

**チェックアウト:** `frontend/src/app/api/subscription/checkout/route.ts`
- `metadata.user_id` のみ。`organization_id` なし
- `quantity: 1` 固定

**Webhook:** `frontend/src/app/api/subscription/webhook/route.ts`
- `user_subscriptions` テーブルのみ更新
- 6イベント処理（checkout完了, subscription作成/更新/削除, 支払い成功/失敗）
- 重複チェック済み（stripe_event_id）

**アクセス判定:** `frontend/src/lib/subscription/index.ts`
- `isPrivilegedEmail()` → `@shintairiku.jp` チェック
- `hasActiveAccess()` → active / canceled期間内 / past_due猶予3日

### WordPress 連携（既存・個人のみ）

**テーブル:** `wordpress_sites`
- `user_id TEXT` で個人紐付け
- `organization_id` カラムなし

**エンドポイント:** `backend/app/domains/blog/endpoints.py`
- `GET /blog/sites` → `user_id` でフィルタ（組織考慮なし）
