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

// アドオン価格ID
export const ADDON_PRICE_ID = process.env.STRIPE_PRICE_ADDON_ARTICLES || '';

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

// デフォルト管理者ドメイン（常に許可）
const DEFAULT_ADMIN_DOMAIN = '@shintairiku.jp';

/**
 * 管理者アクセス許可チェック
 *
 * 以下の条件のいずれかに合致すれば true:
 * 1. @shintairiku.jp ドメイン（デフォルト常時許可）
 * 2. ADMIN_ALLOWED_DOMAINS 環境変数に含まれるドメイン
 * 3. ADMIN_ALLOWED_EMAILS 環境変数に含まれる個別メールアドレス
 *
 * NOTE: 環境変数は NEXT_PUBLIC_ を付けない（サーバーサイドのみで読み取り）
 */
export function isPrivilegedEmail(email: string | null | undefined): boolean {
  if (!email) return false;
  const emailLower = email.toLowerCase();

  // 1. 個別メール許可リスト
  const allowedEmails = (process.env.ADMIN_ALLOWED_EMAILS || '')
    .split(',')
    .map((e) => e.trim().toLowerCase())
    .filter(Boolean);
  if (allowedEmails.includes(emailLower)) return true;

  // 2. ドメイン許可リスト（デフォルト + 環境変数）
  const extraDomains = (process.env.ADMIN_ALLOWED_DOMAINS || '')
    .split(',')
    .map((d) => {
      let domain = d.trim().toLowerCase();
      if (domain && !domain.startsWith('@')) domain = `@${domain}`;
      return domain;
    })
    .filter(Boolean);
  const allowedDomains = [DEFAULT_ADMIN_DOMAIN, ...extraDomains];

  return allowedDomains.some((domain) => emailLower.endsWith(domain));
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

// 使用量情報
export interface UsageInfo {
  articles_generated: number;
  articles_limit: number;
  addon_articles_limit: number;
  total_limit: number;
  remaining: number;
  billing_period_start: string | null;
  billing_period_end: string | null;
  plan_tier: string | null;
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
