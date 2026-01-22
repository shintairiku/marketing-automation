/**
 * サブスクリプション状態取得 API
 *
 * GET /api/subscription/status
 *
 * 現在のユーザーのサブスクリプション状態を返す
 */

import { NextResponse } from 'next/server';

import { hasActiveAccess, isPrivilegedEmail, type UserSubscription } from '@/lib/subscription';
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

    // 3. サブスクリプション情報を取得
    const supabase = supabaseAdminClient;
    const { data: subscription, error } = await supabase
      .from('user_subscriptions')
      .select('*')
      .eq('user_id', userId)
      .single();

    // 4. レコードが存在しない場合は作成
    if (error?.code === 'PGRST116' || !subscription) {
      // 新規ユーザー - レコードを作成
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
        // エラーでもデフォルト値を返す
        const defaultSubscription: UserSubscription = {
          user_id: userId,
          stripe_customer_id: null,
          stripe_subscription_id: null,
          status: 'none',
          current_period_end: null,
          cancel_at_period_end: false,
          is_privileged: isPrivileged,
          email: userEmail || null,
        };

        return NextResponse.json({
          subscription: defaultSubscription,
          hasAccess: isPrivileged,
        });
      }

      return NextResponse.json({
        subscription: newSubscription as UserSubscription,
        hasAccess: hasActiveAccess(newSubscription as UserSubscription),
      });
    }

    if (error) {
      console.error('Error fetching subscription:', error);
      return NextResponse.json(
        { error: 'Failed to fetch subscription' },
        { status: 500 }
      );
    }

    // 5. アクセス権を判定して返す
    return NextResponse.json({
      subscription: subscription as UserSubscription,
      hasAccess: hasActiveAccess(subscription as UserSubscription),
    });
  } catch (error) {
    console.error('Error in subscription status:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
