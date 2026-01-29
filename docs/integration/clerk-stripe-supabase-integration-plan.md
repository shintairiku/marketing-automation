# Clerk Organization + Stripe + Supabase 統合再設計プラン

## 概要

現在のカスタム組織・招待システムを、Clerk の native Organization/Invitation API を活用した構成に再設計する。Stripe のシートベース課金と連携し、WordPress サイト共有を組織単位で実現する。

## 現状の問題

- `clerk_organization_id` / `clerk_membership_id` フィールドが DB にあるが未使用
- 招待はカスタムトークン方式で、メール送信機能なし
- WordPress サイトは `user_id` のみでクエリ（組織共有なし）
- Pricing ページにチームプラン UI なし

---

## 実装フェーズ

### Phase 1: Clerk Webhook ハンドラ作成

**新規作成**: `frontend/src/app/api/clerk-webhooks/route.ts`

Clerk からの Organization イベントを受信し、Supabase に同期する。

処理するイベント:
- `organizationMembership.created` → `organization_members` に INSERT（`clerk_membership_id`, `user_id`, `role`, `email` を保存）
- `organizationMembership.updated` → role 更新
- `organizationMembership.deleted` → メンバー削除
- `organizationInvitation.accepted` → `invitations.status` を `accepted` に更新
- `organizationInvitation.revoked` → `invitations.status` を `declined` に更新

Webhook 検証: `svix` パッケージで署名検証。`CLERK_WEBHOOK_SECRET` 環境変数を追加。

**変更**: `frontend/src/middleware.ts`
- `isPublicRoute` に `/api/clerk-webhooks(.*)` を追加

---

### Phase 2: 組織作成に Clerk API を統合

**変更**: `frontend/src/app/api/organizations/route.ts` (POST)

```
1. clerkClient().organizations.createOrganization({ name, createdBy: userId })
2. 返された clerk_organization_id を body に含めてバックエンドへ転送
3. バックエンドが Supabase に保存（既存の create_organization がそのまま使える）
```

**変更**: `frontend/src/app/api/subscription/checkout/route.ts`
- チーム課金時の自動組織作成でも Clerk API を呼び出す
- `clerk_organization_id` を Supabase の organizations レコードに保存

---

### Phase 3: 招待フローを Clerk Invitation API に変更

**変更**: `frontend/src/app/api/organizations/[id]/invitations/route.ts` (POST)

```
1. Supabase から organizations の clerk_organization_id を取得
2. clerkClient().organizations.createOrganizationInvitation({
     organizationId: clerkOrgId,
     emailAddress: email,
     role: mapToClerkRole(role)  // owner/admin → "admin", member → "basic_member"
   })
3. Clerk がメールを自動送信
4. バックエンドにも invitations レコードを作成（UI 表示用）
```

**変更**: `backend/app/domains/organization/service.py` - `create_invitation()`
- シート上限チェックを追加:
  - `organization_subscriptions.quantity` を取得
  - `members数 + pending招待数 >= quantity` なら 403 エラー

**変更**: `frontend/src/app/(tools)/settings/members/page.tsx`
- 「リンクをコピー」ボタンを削除（Clerk がメール送信するため不要）
- 「招待メール送信済み」ステータス表示に変更
- 招待一覧を GET `/api/organizations/[id]/invitations` から取得

**新規作成**: `frontend/src/app/api/organizations/[id]/invitations/route.ts` に GET ハンドラ追加
- バックエンドから pending 招待一覧を取得

---

### Phase 4: Pricing ページにチームプラン追加

**変更**: `frontend/src/app/(marketing)/pricing/page.tsx`

- 2カラムレイアウトに変更: 個人プラン + チームプラン
- チームプランカード:
  - シート数セレクター（2〜50）
  - `¥29,800 × N席 = 合計金額` 表示
  - 組織名入力フィールド
- checkout 呼び出し時に `{ quantity: seatCount, organizationName }` を送信

---

### Phase 5: WordPress サイト共有（組織単位）

**変更**: `backend/app/domains/blog/endpoints.py`

`list_wordpress_sites` を変更:
```python
# ユーザーの所属組織を取得
org_ids = get_user_organization_ids(user_id)

# ユーザー所有 OR 組織所有のサイトを取得
query = supabase.table("wordpress_sites").select("*")
if org_ids:
    query = query.or_(f"user_id.eq.{user_id},organization_id.in.({','.join(org_ids)})")
else:
    query = query.eq("user_id", user_id)
```

同様に `start_blog_generation` のサイト取得クエリも更新。

`register_wordpress_site` に `organization_id` オプションパラメータ追加。

---

### Phase 6: サブスクリプションアクセスチェック強化

**変更**: `frontend/src/app/api/subscription/status/route.ts`

組織サブスクリプションも確認:
```
1. 個人サブスク確認（既存）
2. ユーザーの所属組織を取得
3. 組織サブスクに active なものがあるか確認
4. hasAccess = privileged OR userActive OR orgActive
```

---

## 実装順序

| 順序 | Phase | 依存関係 |
|------|-------|---------|
| 1 | Phase 1: Clerk Webhook | なし（基盤） |
| 2 | Phase 2: 組織作成 Clerk 統合 | Phase 1 |
| 3 | Phase 3: 招待 Clerk 統合 | Phase 2 |
| 4 | Phase 4: Pricing チームプラン | Phase 2 |
| 5 | Phase 6: アクセスチェック強化 | Phase 4 |
| 6 | Phase 5: WordPress 共有 | Phase 2 |

## 変更対象ファイル一覧

| ファイル | 操作 |
|---------|------|
| `frontend/src/app/api/clerk-webhooks/route.ts` | 新規作成 |
| `frontend/src/middleware.ts` | 修正（public route 追加） |
| `frontend/src/app/api/organizations/route.ts` | 修正（Clerk API 追加） |
| `frontend/src/app/api/organizations/[id]/invitations/route.ts` | 修正（Clerk Invitation + GET 追加） |
| `frontend/src/app/api/subscription/checkout/route.ts` | 修正（Clerk org 作成追加） |
| `frontend/src/app/api/subscription/status/route.ts` | 修正（org sub チェック追加） |
| `frontend/src/app/(marketing)/pricing/page.tsx` | 修正（チームプラン UI） |
| `frontend/src/app/(tools)/settings/members/page.tsx` | 修正（招待 UI 変更） |
| `backend/app/domains/organization/service.py` | 修正（シート上限チェック） |
| `backend/app/domains/blog/endpoints.py` | 修正（組織共有クエリ） |

## 必要な環境変数

- `CLERK_WEBHOOK_SECRET` — Clerk Webhook の署名検証用シークレット

## パッケージ追加

- `svix` — Clerk Webhook の署名検証

## 検証方法

1. **Clerk Webhook**: Clerk Dashboard で webhook URL を設定 → org 作成でイベント受信確認
2. **組織作成**: Members ページで組織作成 → Clerk Dashboard に組織が作成されること確認
3. **招待**: メンバー招待 → 招待先にメールが届くこと確認
4. **チームプラン**: Pricing ページからチームプラン購入 → Stripe + Clerk + Supabase に反映確認
5. **WordPress 共有**: 組織メンバー全員が同じ WordPress サイトを閲覧・使用できること確認
6. **アクセスチェック**: 組織サブスクのみのメンバーがツールにアクセスできること確認
