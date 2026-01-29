/**
 * サブスクリプション状態取得 API
 *
 * GET /api/subscription/status
 *
 * 現在のユーザーのサブスクリプション状態を返す
 * 個人サブスクと組織サブスクの両方をチェック
 */

import { NextResponse } from 'next/server';

import { hasActiveAccess, hasActiveOrgAccess, isPrivilegedEmail, type OrgSubscription, type SubscriptionStatus, type UserSubscription } from '@/lib/subscription';
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
      const isPrivileged = isPrivilegedEmail(userEmail);

      const { data: newSubscription, error: insertError } = await supabase
        .from('user_subscriptions')
        .insert({
          user_id: userId,
          email: userEmail || null,
          is_privileged: isPrivileged,
          status: 'none',
        })
        .select()
        .single();

      if (insertError) {
        console.error('Error creating subscription record:', insertError);
        userSub = {
          user_id: userId,
          stripe_customer_id: null,
          stripe_subscription_id: null,
          status: 'none',
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

    // 6. アクセス権を判定して返す
    const isPrivileged = isPrivilegedEmail(userEmail);
    const hasAccess =
      isPrivileged ||
      hasActiveAccess(userSub) ||
      hasActiveOrgAccess(orgSubscription);

    return NextResponse.json({
      subscription: userSub,
      orgSubscription,
      hasAccess,
    });
  } catch (error) {
    console.error('Error in subscription status:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
