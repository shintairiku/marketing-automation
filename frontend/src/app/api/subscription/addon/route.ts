/**
 * アドオン管理 API
 *
 * POST /api/subscription/addon
 *
 * 記事追加アドオンの追加/変更/削除を行う
 * quantity: 0 → 削除, 1+ → 追加/変更
 */

import { NextResponse } from 'next/server';
import Stripe from 'stripe';

import { getStripe, SUBSCRIPTION_PRICE_ID } from '@/lib/subscription';
import { supabaseAdminClient } from '@/libs/supabase/supabase-admin';
import { auth } from '@clerk/nextjs/server';

const ADDON_PRICE_ID = process.env.STRIPE_PRICE_ADDON_ARTICLES || '';

export async function POST(request: Request) {
  try {
    const authData = await auth();
    const userId = authData.userId;
    if (!userId) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const { quantity } = await request.json();
    if (typeof quantity !== 'number' || quantity < 0 || quantity > 100) {
      return NextResponse.json(
        { error: 'Invalid quantity (0-100)' },
        { status: 400 }
      );
    }

    if (!ADDON_PRICE_ID) {
      return NextResponse.json(
        { error: 'Addon price not configured' },
        { status: 500 }
      );
    }

    const supabase = supabaseAdminClient;
    const stripe = getStripe();

    // ユーザーのサブスクリプションを取得
    // Note: upgraded_to_org_id, plan_tier_id は型生成前のためアサーション使用
    const { data: userSub } = await supabase
      .from('user_subscriptions')
      .select('stripe_subscription_id, upgraded_to_org_id, plan_tier_id')
      .eq('user_id', userId)
      .single() as { data: Record<string, unknown> | null };

    if (!userSub?.stripe_subscription_id) {
      return NextResponse.json(
        { error: 'No active subscription found' },
        { status: 404 }
      );
    }

    // 現在のサブスクリプションを取得
    const subscription = await stripe.subscriptions.retrieve(
      userSub.stripe_subscription_id as string
    );

    if (subscription.status !== 'active') {
      return NextResponse.json(
        { error: 'Subscription is not active' },
        { status: 400 }
      );
    }

    // ベースプランアイテムを特定
    const baseItem = subscription.items.data.find(
      (item) => item.price.id !== ADDON_PRICE_ID
    );
    // 既存のアドオンアイテムを検索
    const existingAddon = subscription.items.data.find(
      (item) => item.price.id === ADDON_PRICE_ID
    );

    // items 配列を構築
    const items: Stripe.SubscriptionUpdateParams.Item[] = [];

    // ベースアイテムは維持
    if (baseItem) {
      items.push({ id: baseItem.id });
    }

    if (quantity === 0 && existingAddon) {
      // アドオン削除
      items.push({ id: existingAddon.id, deleted: true });
    } else if (quantity > 0) {
      if (existingAddon) {
        // 既存アドオンの数量変更
        items.push({ id: existingAddon.id, quantity });
      } else {
        // 新規アドオン追加
        items.push({ price: ADDON_PRICE_ID, quantity });
      }
    } else {
      // quantity=0 でアドオンが存在しない場合は何もしない
      return NextResponse.json({ success: true, message: 'No changes needed' });
    }

    // サブスクリプション更新
    await stripe.subscriptions.update(subscription.id, {
      items,
      proration_behavior: 'always_invoice',
    });

    // DBのaddon_quantityを更新
    const orgId = userSub.upgraded_to_org_id as string | null;
    if (orgId) {
      // 組織サブスクのaddon_quantityを更新
      await supabase
        .from('organization_subscriptions')
        .update({ addon_quantity: quantity } as Record<string, unknown>)
        .eq('organization_id', orgId);
    } else {
      // 個人サブスクのaddon_quantityを更新
      await supabase
        .from('user_subscriptions')
        .update({ addon_quantity: quantity } as Record<string, unknown>)
        .eq('user_id', userId);
    }

    // ユーザーの plan_tier_id を使って正しいティアから値を参照
    const tierIdToUse = (userSub.plan_tier_id as string) || 'default';

    // usage_tracking の addon_articles_limit を即時更新
    const now = new Date().toISOString();
    // Note: plan_tiers は型生成前のため any キャストを使用
    const { data: tier } = await (supabase as any)
      .from('plan_tiers')
      .select('addon_unit_amount')
      .eq('id', tierIdToUse)
      .single();
    const addonUnitAmount = tier?.addon_unit_amount as number || 20;
    const newAddonLimit = addonUnitAmount * quantity;

    // Note: usage_tracking は型生成前のため any キャストを使用
    if (orgId) {
      await (supabase as any)
        .from('usage_tracking')
        .update({ addon_articles_limit: newAddonLimit })
        .eq('organization_id', orgId)
        .lte('billing_period_start', now)
        .gte('billing_period_end', now);
    } else {
      await (supabase as any)
        .from('usage_tracking')
        .update({ addon_articles_limit: newAddonLimit })
        .eq('user_id', userId)
        .lte('billing_period_start', now)
        .gte('billing_period_end', now);
    }

    return NextResponse.json({
      success: true,
      addon_quantity: quantity,
      message: quantity > 0
        ? `アドオンを${quantity}ユニットに変更しました`
        : 'アドオンを削除しました',
    });
  } catch (error) {
    console.error('Error managing addon:', error);
    const message = error instanceof Error ? error.message : 'Unknown error';
    return NextResponse.json(
      { error: `Failed to manage addon: ${message}` },
      { status: 500 }
    );
  }
}
