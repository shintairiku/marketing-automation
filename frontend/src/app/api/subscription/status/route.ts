/**
 * サブスクリプション状態取得 API
 *
 * GET /api/subscription/status
 *
 * 現在のユーザーのサブスクリプション状態を返す
 * 個人サブスクと組織サブスクの両方をチェック
 */

import { NextResponse } from 'next/server';

import { hasActiveAccess, hasActiveOrgAccess, hasPrivilegedRole, isPrivilegedEmail, type OrgSubscription, type SubscriptionStatus, type UserSubscription } from '@/lib/subscription';
import { supabaseAdminClient } from '@/libs/supabase/supabase-admin';
import { auth, clerkClient } from '@clerk/nextjs/server';

export async function GET() {
  try {
    // 1. 認証チェック
    const authData = await auth();
    const userId = authData.userId;

    if (!userId) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    // 2. ユーザーメールを取得（Clerk APIから）
    const client = await clerkClient();
    const user = await client.users.getUser(userId);
    const userEmail = user.emailAddresses?.[0]?.emailAddress;

    // 3. 個人サブスクリプション情報を取得
    const supabase = supabaseAdminClient;
    const { data: subscription, error } = await supabase
      .from('user_subscriptions')
      .select('*')
      .eq('user_id', userId)
      .single();

    // 4. レコードが存在しない場合は作成
    let userSub: UserSubscription;

    if (error?.code === 'PGRST116' || !subscription) {
      // publicMetadata.role を第一優先、メールドメインをフォールバック
      const isPrivileged = hasPrivilegedRole(user.publicMetadata as Record<string, unknown>) || isPrivilegedEmail(userEmail);

      // 新規ユーザーはフリープラン（status: 'active', plan_tier_id: 'free'）
      const { data: newSubscription, error: insertError } = await supabase
        .from('user_subscriptions')
        .insert({
          user_id: userId,
          email: userEmail || null,
          is_privileged: isPrivileged,
          status: 'active',
          plan_tier_id: isPrivileged ? null : 'free',
        })
        .select()
        .single();

      if (insertError) {
        console.error('Error creating subscription record:', insertError);
        userSub = {
          user_id: userId,
          stripe_customer_id: null,
          stripe_subscription_id: null,
          status: 'active',
          current_period_end: null,
          cancel_at_period_end: false,
          is_privileged: isPrivileged,
          email: userEmail || null,
        };
      } else {
        userSub = newSubscription as UserSubscription;
      }
    } else if (error) {
      console.error('Error fetching subscription:', error);
      return NextResponse.json(
        { error: 'Failed to fetch subscription' },
        { status: 500 }
      );
    } else {
      userSub = subscription as UserSubscription;
    }

    // 5. 組織サブスクリプション情報を取得
    let orgSubscription: OrgSubscription | null = null;

    try {
      // ユーザーが所属する組織を取得
      const { data: memberships } = await supabase
        .from('organization_members')
        .select('organization_id')
        .eq('user_id', userId);

      if (memberships && memberships.length > 0) {
        const orgIds = memberships.map((m) => m.organization_id);

        // 組織のサブスクリプションを取得（active なものを優先）
        const { data: orgSubs } = await supabase
          .from('organization_subscriptions')
          .select('*')
          .in('organization_id', orgIds)
          .order('status', { ascending: true }); // active が先

        if (orgSubs && orgSubs.length > 0) {
          // active なサブスクを優先
          const activeSub = orgSubs.find((s) => s.status === 'active')
            || orgSubs.find((s) => s.status === 'past_due')
            || orgSubs[0];

          // subscription_status enum を SubscriptionStatus にマッピング
          let orgStatus: SubscriptionStatus = 'none';
          switch (activeSub.status) {
            case 'active':
            case 'trialing':
              orgStatus = 'active';
              break;
            case 'past_due':
              orgStatus = 'past_due';
              break;
            case 'canceled':
              orgStatus = 'canceled';
              break;
            case 'unpaid':
            case 'incomplete_expired':
              orgStatus = 'expired';
              break;
            default:
              orgStatus = 'none';
          }

          orgSubscription = {
            id: activeSub.id,
            organization_id: activeSub.organization_id,
            status: orgStatus,
            quantity: activeSub.quantity || 1,
            current_period_end: activeSub.current_period_end,
            cancel_at_period_end: activeSub.cancel_at_period_end || false,
          };
        }
      }
    } catch (orgError) {
      console.error('Error fetching org subscription:', orgError);
      // 組織サブスクの取得失敗は致命的ではない
    }

    // 6. 使用量情報を取得
    let usage = null;
    try {
      const now = new Date().toISOString();

      // まず個人の使用量を検索
      // Note: usage_tracking は型生成前のため any キャストを使用
      let usageTracking = null;
      const { data: personalUsage } = await supabase
        .from('usage_tracking')
        .select('*')
        .eq('user_id', userId)
        .gte('billing_period_end', now)
        .lte('billing_period_start', now)
        .maybeSingle();

      usageTracking = personalUsage;

      // 個人の使用量がない場合、組織の使用量を検索
      if (!usageTracking && orgSubscription) {
        const { data: orgUsage } = await supabase
          .from('usage_tracking')
          .select('*')
          .eq('organization_id', orgSubscription.organization_id)
          .gte('billing_period_end', now)
          .lte('billing_period_start', now)
          .maybeSingle();

        usageTracking = orgUsage;
      }

      // それでもない場合、organization_members から所属組織の使用量を検索
      if (!usageTracking) {
        const { data: memberOrgs } = await supabase
          .from('organization_members')
          .select('organization_id')
          .eq('user_id', userId);

        if (memberOrgs && memberOrgs.length > 0) {
          const orgIds = memberOrgs.map((m) => m.organization_id);
          const { data: orgUsage } = await supabase
            .from('usage_tracking')
            .select('*')
            .in('organization_id', orgIds)
            .gte('billing_period_end', now)
            .lte('billing_period_start', now)
            .limit(1)
            .maybeSingle();

          usageTracking = orgUsage;
        }
      }

      if (usageTracking) {
        const ut = usageTracking as Record<string, unknown>;
        const articlesLimit = (ut.articles_limit as number) || 0;
        const addonLimit = (ut.addon_articles_limit as number) || 0;
        const adminGranted = (ut.admin_granted_articles as number) || 0;
        const articlesGenerated = (ut.articles_generated as number) || 0;
        const totalLimit = articlesLimit + addonLimit + adminGranted;
        usage = {
          articles_generated: articlesGenerated,
          articles_limit: articlesLimit,
          addon_articles_limit: addonLimit,
          admin_granted_articles: adminGranted,
          total_limit: totalLimit,
          remaining: Math.max(0, totalLimit - articlesGenerated),
          billing_period_start: ut.billing_period_start as string | null,
          billing_period_end: ut.billing_period_end as string | null,
          plan_tier: ut.plan_tier_id as string | null,
        };
      } else if (hasActiveAccess(userSub) || hasActiveOrgAccess(orgSubscription)) {
        // usage_tracking レコードがないがサブスクリプションはアクティブな場合
        // plan_tier_id からフォールバック表示を提供
        const planTierId = (userSub as unknown as Record<string, unknown>).plan_tier_id as string || 'free';
        try {
          const { data: tierData } = await supabase
            .from('plan_tiers')
            .select('monthly_article_limit, addon_unit_amount')
            .eq('id', planTierId)
            .maybeSingle();

          const fallbackLimit = tierData?.monthly_article_limit || 10;
          usage = {
            articles_generated: 0,
            articles_limit: fallbackLimit,
            addon_articles_limit: 0,
            admin_granted_articles: 0,
            total_limit: fallbackLimit,
            remaining: fallbackLimit,
            billing_period_start: null,
            billing_period_end: null,
            plan_tier: planTierId,
          };
        } catch {
          // plan_tiers テーブルが存在しない場合もフォールバック
          usage = {
            articles_generated: 0,
            articles_limit: 10,
            addon_articles_limit: 0,
            admin_granted_articles: 0,
            total_limit: 10,
            remaining: 10,
            billing_period_start: null,
            billing_period_end: null,
            plan_tier: 'free',
          };
        }
      }
    } catch (usageError) {
      console.error('Error fetching usage:', usageError);
      // 使用量取得失敗は致命的ではない
    }

    // 7. アクセス権を判定して返す（publicMetadata.role を第一優先）
    const isPrivilegedAccess = hasPrivilegedRole(user.publicMetadata as Record<string, unknown>) || isPrivilegedEmail(userEmail);
    const hasAccess =
      isPrivilegedAccess ||
      hasActiveAccess(userSub) ||
      hasActiveOrgAccess(orgSubscription);

    return NextResponse.json({
      subscription: userSub,
      orgSubscription,
      hasAccess,
      usage,
    });
  } catch (error) {
    console.error('Error in subscription status:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
