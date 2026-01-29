/**
 * サブスクリプション管理モジュール
 *
 * シンプルな1プラン構成のサブスクリプションシステム
 * - 月額プラン（Stripeで事前設定）
 * - @shintairiku.jp ユーザーは特権アクセス
 */

import Stripe from 'stripe';

// Stripe クライアント（サーバーサイド用）
let stripeClient: Stripe | null = null;

export function getStripe(): Stripe {
  if (!stripeClient) {
    const secretKey = process.env.STRIPE_SECRET_KEY;
    if (!secretKey) {
      throw new Error('STRIPE_SECRET_KEY is not set');
    }
    stripeClient = new Stripe(secretKey, {
      apiVersion: '2025-08-27.basil',
      appInfo: {
        name: 'Marketing Automation Platform',
        version: '2.0.0',
      },
    });
  }
  return stripeClient;
}

// 価格ID（Stripeダッシュボードで作成したものを環境変数で設定）
export const SUBSCRIPTION_PRICE_ID = process.env.STRIPE_PRICE_ID || '';

// サブスクリプションの状態
export type SubscriptionStatus = 'active' | 'past_due' | 'canceled' | 'expired' | 'none';

// ユーザーサブスクリプション情報
export interface UserSubscription {
  user_id: string;
  stripe_customer_id: string | null;
  stripe_subscription_id: string | null;
  status: SubscriptionStatus;
  current_period_end: string | null;
  cancel_at_period_end: boolean;
  is_privileged: boolean;
  email: string | null;
}

// アクセス権の判定
export function hasActiveAccess(subscription: UserSubscription | null): boolean {
  if (!subscription) return false;

  // @shintairiku.jp 特権ユーザー
  if (subscription.is_privileged) return true;

  // アクティブなサブスクリプション
  if (subscription.status === 'active') return true;

  // キャンセル済みでも期間内
  if (subscription.status === 'canceled' && subscription.current_period_end) {
    const periodEnd = new Date(subscription.current_period_end);
    if (periodEnd > new Date()) return true;
  }

  // 支払い遅延でも3日間の猶予
  if (subscription.status === 'past_due' && subscription.current_period_end) {
    const periodEnd = new Date(subscription.current_period_end);
    const gracePeriod = new Date(periodEnd.getTime() + 3 * 24 * 60 * 60 * 1000);
    if (gracePeriod > new Date()) return true;
  }

  return false;
}

// @shintairiku.jp ドメインかどうかをチェック
export function isPrivilegedEmail(email: string | null | undefined): boolean {
  if (!email) return false;
  return email.toLowerCase().endsWith('@shintairiku.jp');
}

// 組織サブスクリプション情報
export interface OrgSubscription {
  id: string;
  organization_id: string;
  status: SubscriptionStatus;
  quantity: number;
  current_period_end: string | null;
  cancel_at_period_end: boolean;
}

// 組織アクセス権の判定
export function hasActiveOrgAccess(orgSubscription: OrgSubscription | null | undefined): boolean {
  if (!orgSubscription) return false;

  // アクティブなサブスクリプション
  if (orgSubscription.status === 'active') return true;

  // キャンセル済みでも期間内
  if (orgSubscription.status === 'canceled' && orgSubscription.current_period_end) {
    const periodEnd = new Date(orgSubscription.current_period_end);
    if (periodEnd > new Date()) return true;
  }

  // 支払い遅延でも3日間の猶予
  if (orgSubscription.status === 'past_due' && orgSubscription.current_period_end) {
    const periodEnd = new Date(orgSubscription.current_period_end);
    const gracePeriod = new Date(periodEnd.getTime() + 3 * 24 * 60 * 60 * 1000);
    if (gracePeriod > new Date()) return true;
  }

  return false;
}

// Stripe Checkout Session作成のパラメータ
export interface CreateCheckoutSessionParams {
  userId: string;
  userEmail: string;
  successUrl: string;
  cancelUrl: string;
}

// Stripe Customer Portal Session作成のパラメータ
export interface CreatePortalSessionParams {
  customerId: string;
  returnUrl: string;
}
