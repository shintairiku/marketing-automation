# Agent-08: Frontend Subscription API Routes Security Report

**調査完了**: 2026-02-04
**発見数**: Critical:0, High:1, Medium:3, Low:2

---

## 調査対象ファイル

| ファイル | 行数 |
|---------|------|
| frontend/src/app/api/subscription/checkout/route.ts | 203 |
| frontend/src/app/api/subscription/status/route.ts | 193 |
| frontend/src/app/api/subscription/portal/route.ts | 61 |
| frontend/src/app/api/subscription/webhook/route.ts | 475 |
| frontend/src/app/api/subscription/upgrade-to-team/route.ts | 172 |
| frontend/src/app/api/subscription/update-seats/route.ts | 133 |
| frontend/src/app/api/subscription/preview-upgrade/route.ts | 135 |
| frontend/src/app/api/subscription/addon/route.ts | 143 |

---

## 発見事項

### [HIGH] SUB-001: STRIPE_WEBHOOK_SECRET 未設定時の不適切な処理

- **ファイル**: `frontend/src/app/api/subscription/webhook/route.ts`
- **行番号**: 34-41
- **問題**: webhookSecretが未設定の場合、「Missing signature」エラーを返すが、リクエストボディは既に読み込まれている。より根本的に、webhookSecretがないとサービス起動時にエラーとすべき

```typescript
const webhookSecret = process.env.STRIPE_WEBHOOK_SECRET;
...
if (!signature || !webhookSecret) {
  console.error('Missing signature or webhook secret');
  return NextResponse.json({ error: 'Missing signature' }, { status: 400 });
}
```

- **影響**: 設定ミスで本番環境にデプロイされた場合、全Webhookが処理されずサブスク状態の同期が壊れる
- **推奨修正**: アプリ起動時にSTRIPE_WEBHOOK_SECRETの存在を検証するか、明確なエラーログとアラートを追加

---

### [MEDIUM] SUB-002: 組織権限チェックの不整合 - update-seats

- **ファイル**: `frontend/src/app/api/subscription/update-seats/route.ts`
- **行番号**: 45-60
- **問題**: owner/adminロールのチェックは行っているが、最初に見つかった組織のサブスクを変更対象としている

```typescript
const adminMembership = memberships.find((m) => m.role === 'owner' || m.role === 'admin');
if (!adminMembership) {
  return NextResponse.json({ error: 'Only organization owners or admins can change seats' }, { status: 403 });
}
const orgId = adminMembership.organization_id;
```

- **影響**: ユーザーが複数組織に所属している場合、意図しない組織のシート数が変更される可能性
- **推奨修正**: リクエストボディでorganizationIdを明示的に指定させ、そのorgに対する権限を検証

---

### [MEDIUM] SUB-003: 組織サブスク取得ロジックの不整合 - preview-upgrade

- **ファイル**: `frontend/src/app/api/subscription/preview-upgrade/route.ts`
- **行番号**: 44-65
- **問題**: ユーザーが所属するすべての組織を取得し、最初のアクティブサブスクをプレビュー対象にしている

```typescript
const { data: memberships } = await supabase
  .from('organization_members')
  .select('organization_id')
  .eq('user_id', userId);
// ...
const { data: orgSub } = await supabase
  .from('organization_subscriptions')
  .in('organization_id', orgIds)
  .eq('status', 'active')
  .limit(1)
  .single();
```

- **影響**: マルチ組織所属時、意図しない組織のプレビューが返される可能性
- **推奨修正**: リクエストでorganizationIdを指定させ、その組織への権限を検証

---

### [MEDIUM] SUB-004: Stripe Customer ID の所有権検証なし - portal

- **ファイル**: `frontend/src/app/api/subscription/portal/route.ts`
- **行番号**: 32-38
- **問題**: DBからstripe_customer_idを取得してPortalを作成するが、そのcustomer_idが本当にこのユーザーのものかStripe側で再検証していない

```typescript
const { data: subscription } = await supabase
  .from('user_subscriptions')
  .select('stripe_customer_id')
  .eq('user_id', userId)
  .single();
// → stripe_customer_id をそのまま使用
```

- **影響**: DBが汚染された場合、他ユーザーのStripe Portalにアクセス可能になる（低リスク - DBアクセス前提）
- **現状評価**: RLS適用済みのuser_subscriptionsテーブルから取得しているため実質的リスクは低い
- **推奨修正**: portal作成前にStripe APIでcustomer.metadataのuser_idを確認、または監査ログを追加

---

### [LOW] SUB-005: 入力バリデーションの一貫性不足

- **ファイル**: 全ファイル
- **問題**: quantityの範囲チェックがファイルごとに異なる

| ファイル | バリデーション |
|---------|--------------|
| checkout | Math.max(1, Math.min(50, body.quantity \|\| 1)) |
| upgrade-to-team | Math.max(2, Math.min(50, body.quantity \|\| 2)) |
| update-seats | Math.max(2, Math.min(50, body.quantity \|\| 2)) |
| preview-upgrade | Math.max(1, Math.min(50, body.quantity \|\| 2)) |
| addon | quantity < 0 \|\| quantity > 100 |

- **影響**: ビジネスロジックの不整合、エッジケースでの予期しない動作
- **推奨修正**: 共通のバリデーション関数を`lib/subscription/validation.ts`に作成し一貫性を確保

---

### [LOW] SUB-006: エラーメッセージの詳細露出

- **ファイル**: `frontend/src/app/api/subscription/addon/route.ts`
- **行番号**: 138-140
- **問題**: 内部エラーメッセージをそのままレスポンスに含む

```typescript
const message = error instanceof Error ? error.message : 'Unknown error';
return NextResponse.json({ error: `Failed to manage addon: ${message}` }, { status: 500 });
```

- **影響**: Stripeの内部エラーや実装詳細が露出する可能性
- **推奨修正**: 本番環境では一般的なエラーメッセージを返し、開発環境でのみ詳細を表示

---

## 良い実装（セキュリティ観点）

### 1. Webhook署名検証
- **ファイル**: webhook/route.ts
- Stripe署名検証を正しく実装:
```typescript
event = stripe.webhooks.constructEvent(body, signature, webhookSecret);
```

### 2. イベント重複チェック
- **ファイル**: webhook/route.ts
- subscription_eventsテーブルでイベントIDの重複を防止:
```typescript
const { data: existingEvent } = await supabase
  .from('subscription_events')
  .select('id')
  .eq('stripe_event_id', event.id)
  .single();
if (existingEvent) {
  return NextResponse.json({ received: true });
}
```

### 3. Clerk認証の統合
- 全ファイルで `@clerk/nextjs/server` の `auth()` を使用して認証を確認
- userIdなしの場合は401を返す

### 4. 特権ユーザーの除外
- checkout, upgrade-to-team, update-seats, preview-upgradeで特権ユーザーをチェック
- `isPrivilegedEmail(userEmail)` でサブスク不要ユーザーを識別

### 5. Stripe APIの適切な使用
- `proration_behavior: 'always_invoice'` で日割り計算
- `payment_behavior: 'pending_if_incomplete'` で支払い失敗時の保留
- `invoices.createPreview()` でプレビュー

---

## 推奨修正アクション（優先順位付き）

### 優先度: HIGH
1. **STRIPE_WEBHOOK_SECRETの存在チェックを強化**
   - 起動時検証またはミドルウェアでの検証
   - 未設定時は明確なエラーログとアラート
   - 本番デプロイ前のCI/CDでの検証

### 優先度: MEDIUM
2. **組織関連APIでorganizationIdを必須パラメータに**
   - update-seats: `body.organizationId` を必須化
   - preview-upgrade: `body.organizationId` を必須化（組織プレビューの場合）
   - 指定されたorgに対するユーザーの権限を検証

3. **Customer ID検証の強化**
   - portal作成前にStripe APIで`customer.metadata.user_id`を確認
   - またはDBのRLSを信頼しつつ、監査ログを追加

### 優先度: LOW
4. **バリデーション共通化**
   - `lib/subscription/validation.ts` を作成
   - quantityの範囲、organizationIdのUUID形式などを統一

5. **エラーメッセージの抽象化**
   - 本番環境では詳細を隠す
   - 開発環境でのみ詳細を表示

---

## 参考: 調査項目チェックリスト

| 調査項目 | 結果 |
|---------|------|
| Stripe Webhook署名検証の実装 | OK - constructEvent()で正しく実装 |
| Checkout Session作成時のユーザー検証 | OK - Clerk auth()で認証済み |
| サブスク変更の認可チェック（owner/admin） | 要改善 - マルチ組織時の問題あり |
| 料金プレビューでの情報漏洩 | OK - 認証ユーザーの情報のみ返却 |
| Webhookシークレット未設定時の動作 | 要改善 - 起動時検証が必要 |
| Customer ID の検証 | 要検討 - RLS依存、追加検証推奨 |
