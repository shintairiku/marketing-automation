/**
 * 管理者: 追加記事付与 API
 *
 * POST /api/admin/grant-articles
 * - 管理者が任意のユーザーに追加記事を付与
 * - Stripe不要、DB直接更新
 *
 * Body: { user_id: string, additional_articles: number }
 */

import { NextResponse } from 'next/server';

import { isPrivilegedEmail } from '@/lib/subscription';
import { supabaseAdminClient } from '@/libs/supabase/supabase-admin';
import { auth, clerkClient } from '@clerk/nextjs/server';

export async function POST(request: Request) {
  try {
    // 1. 管理者認証
    const authData = await auth();
    const adminUserId = authData.userId;
    if (!adminUserId) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const client = await clerkClient();
    const adminUser = await client.users.getUser(adminUserId);
    const adminEmail = adminUser.emailAddresses?.[0]?.emailAddress;
    if (!isPrivilegedEmail(adminEmail)) {
      return NextResponse.json({ error: 'Forbidden: admin only' }, { status: 403 });
    }

    // 2. リクエストの取得
    const body = await request.json();
    const { user_id, additional_articles } = body;

    if (!user_id || typeof additional_articles !== 'number') {
      return NextResponse.json(
        { error: 'user_id と additional_articles (number) が必要です' },
        { status: 400 }
      );
    }

    if (additional_articles < 0) {
      return NextResponse.json(
        { error: '追加記事数は0以上で指定してください' },
        { status: 400 }
      );
    }

    const supabase = supabaseAdminClient;
    const now = new Date().toISOString();

    // 3. 対象ユーザーの現在の usage_tracking を取得
    const { data: usageTracking } = await supabase
      .from('usage_tracking')
      .select('*')
      .eq('user_id', user_id)
      .lte('billing_period_start', now)
      .gte('billing_period_end', now)
      .maybeSingle();

    if (!usageTracking) {
      // usage_tracking がない場合は作成（フリープランの月初〜月末）
      const periodStart = new Date();
      periodStart.setDate(1);
      periodStart.setHours(0, 0, 0, 0);
      const periodEnd = new Date(periodStart);
      periodEnd.setMonth(periodEnd.getMonth() + 1);

      const { data: freeTier } = await supabase
        .from('plan_tiers')
        .select('monthly_article_limit')
        .eq('id', 'free')
        .maybeSingle();

      const baseLimit = freeTier?.monthly_article_limit || 10;

      const { error: insertError } = await supabase.from('usage_tracking').insert({
        user_id,
        billing_period_start: periodStart.toISOString(),
        billing_period_end: periodEnd.toISOString(),
        articles_generated: 0,
        articles_limit: baseLimit,
        addon_articles_limit: additional_articles,
        plan_tier_id: 'free',
      });

      if (insertError) {
        console.error('Error creating usage tracking:', insertError);
        return NextResponse.json(
          { error: 'usage_tracking の作成に失敗しました' },
          { status: 500 }
        );
      }

      return NextResponse.json({
        success: true,
        message: `${additional_articles}記事を付与しました`,
        addon_articles_limit: additional_articles,
      });
    }

    // 4. 既存レコードの addon_articles_limit を更新
    const { error: updateError } = await supabase
      .from('usage_tracking')
      .update({ addon_articles_limit: additional_articles })
      .eq('id', usageTracking.id);

    if (updateError) {
      console.error('Error updating usage tracking:', updateError);
      return NextResponse.json(
        { error: '追加記事の更新に失敗しました' },
        { status: 500 }
      );
    }

    return NextResponse.json({
      success: true,
      message: `追加記事を${additional_articles}記事に設定しました`,
      addon_articles_limit: additional_articles,
      previous_addon: (usageTracking as Record<string, unknown>).addon_articles_limit || 0,
    });
  } catch (error) {
    console.error('Error in grant-articles:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
