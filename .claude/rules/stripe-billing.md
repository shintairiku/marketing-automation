---
paths: frontend/src/app/api/subscription/**/*,frontend/src/app/(settings)/settings/billing/**/*
---

# Stripe サブスクリプション設計知見

> 情報ソース: Stripe公式ドキュメント (2026-02時点)

## 核心ルール
1. **Stripe Checkout は新規サブスク作成専用**。既存サブスクの変更はできない
2. **プラン変更は `stripe.subscriptions.update()`**。同一 Customer 上で items を更新 → 日割り自動
3. **同一 Stripe Customer を使う**。分けると日割りクレジットが別Customer に滞留

## `proration_behavior` (subscriptions.update)
| 値 | 動作 |
|---|---|
| `create_prorations` (デフォルト) | 日割りアイテム作成、次回請求に加算 |
| `always_invoice` | 日割り + 即時請求/クレジット |
| `none` | 日割りなし |

## `payment_behavior`
| 値 | 動作 |
|---|---|
| `allow_incomplete` (デフォルト) | 支払い失敗 → `past_due` |
| `pending_if_incomplete` | 支払い失敗 → 変更を保留 (23h期限) |
| `error_if_incomplete` | 支払い失敗 → HTTP 402 |

## `pending_if_incomplete` の制限
- `metadata` は同時更新不可 → 2回に分けて `subscriptions.update()` を呼ぶ
- サポートされないパラメータを渡すと `StripeInvalidRequestError`

## キャンセル方式
| 方式 | 動作 |
|---|---|
| `cancel_at_period_end: true` | 期末キャンセル。取り消し可能 |
| `stripe.subscriptions.cancel()` | 即時キャンセル。返金は手動 |

## 本プロジェクトでの適用
- **個人→チーム移行**: `subscriptions.update()` で quantity 変更。`always_invoice` + `pending_if_incomplete`
- **2段階更新**: items 更新 → metadata 更新 (別呼び出し)
- **料金プレビュー**: `invoices.createPreview()` で差額表示 → 確認モーダル → 実行
- **Stripe Customer**: 個人もチームも同一 Customer。`organizations.billing_user_id` で課金者追跡

## フリープラン + アドオン設計
- フリープラン: 月10記事、Stripe不要 (`plan_tier_id: 'free'`)
- 管理者記事付与: `admin_granted_articles` カラム
- total_limit: `articles_limit + addon_articles_limit + admin_granted_articles`
- アドオン: Stripe サブスクに追加ラインアイテム。`STRIPE_PRICE_ADDON_ARTICLES` で Price ID 設定

## orgオーナー離脱時
- Stripe はサブスクの Customer 変更を許可していない
- 旧オーナー: `cancel_at_period_end: true` → 新オーナー: 新 sub を `trial_end: 旧期末` で作成
- 初期は管理者手動対応

## Stripe v18→v20 破壊的変更
- `current_period_start/end` が `Subscription` → `subscription.items.data[0]` に移動
- `@stripe/stripe-js` v2→v8: TypeScript型更新のみ
