/**
 * Admin Free Trial Grants API
 *
 * POST /api/admin/free-trials — 新規トライアル付与 (Stripe Coupon 作成 + DB 保存)
 * GET  /api/admin/free-trials — 一覧取得
 */

import { NextResponse } from 'next/server';

import { getStripe, isPrivilegedEmail } from '@/lib/subscription';
import { supabaseAdminClient } from '@/libs/supabase/supabase-admin';
import { auth, clerkClient } from '@clerk/nextjs/server';

async function requireAdmin() {
  const authData = await auth();
  const userId = authData.userId;
  if (!userId) {
    return { error: NextResponse.json({ error: 'Unauthorized' }, { status: 401 }) };
  }

  const client = await clerkClient();
  const user = await client.users.getUser(userId);
  const email = user.emailAddresses?.[0]?.emailAddress;

  if (!isPrivilegedEmail(email)) {
    return { error: NextResponse.json({ error: 'Forbidden' }, { status: 403 }) };
  }

  return { userId, email: email! };
}

export async function POST(request: Request) {
  try {
    const adminCheck = await requireAdmin();
    if ('error' in adminCheck && adminCheck.error instanceof NextResponse) {
      return adminCheck.error;
    }
    const { userId: adminUserId, email: adminEmail } = adminCheck as { userId: string; email: string };

    const body = await request.json();
    const { user_id, duration_months, note } = body;

    if (!user_id || !duration_months || duration_months < 1 || duration_months > 24) {
      return NextResponse.json(
        { error: 'user_id and duration_months (1-24) are required' },
        { status: 400 }
      );
    }

    // 対象ユーザーに既に pending な grant がないか確認
    const supabase = supabaseAdminClient;
    const { data: existingGrant } = await (supabase as any)
      .from('free_trial_grants')
      .select('id')
      .eq('user_id', user_id)
      .eq('status', 'pending')
      .maybeSingle();

    if (existingGrant) {
      return NextResponse.json(
        { error: 'このユーザーには既に未使用のトライアルがあります' },
        { status: 409 }
      );
    }

    // Stripe Coupon 作成
    const stripe = getStripe();
    const coupon = await stripe.coupons.create({
      percent_off: 100,
      duration: duration_months === 1 ? 'once' : 'repeating',
      ...(duration_months > 1 && { duration_in_months: duration_months }),
      name: `無料トライアル ${duration_months}ヶ月`,
      metadata: {
        granted_by: adminEmail,
        granted_to: user_id,
        type: 'free_trial_grant',
      },
    });

    // DB に保存
    const { data: grant, error: insertError } = await (supabase as any)
      .from('free_trial_grants')
      .insert({
        user_id,
        stripe_coupon_id: coupon.id,
        duration_months,
        status: 'pending',
        granted_by: adminUserId,
        note: note || null,
      })
      .select()
      .single();

    if (insertError) {
      // ロールバック: Stripe Coupon を削除
      await stripe.coupons.del(coupon.id).catch(() => {});
      console.error('Failed to insert free trial grant:', insertError);
      return NextResponse.json(
        { error: 'Failed to create free trial grant' },
        { status: 500 }
      );
    }

    return NextResponse.json(grant, { status: 201 });
  } catch (error) {
    console.error('Error creating free trial grant:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

export async function GET() {
  try {
    const adminCheck = await requireAdmin();
    if ('error' in adminCheck && adminCheck.error instanceof NextResponse) {
      return adminCheck.error;
    }

    const supabase = supabaseAdminClient;
    const { data: grants, error } = await (supabase as any)
      .from('free_trial_grants')
      .select('*')
      .order('created_at', { ascending: false });

    if (error) {
      console.error('Failed to fetch free trial grants:', error);
      return NextResponse.json(
        { error: 'Failed to fetch grants' },
        { status: 500 }
      );
    }

    return NextResponse.json({ grants: grants || [] });
  } catch (error) {
    console.error('Error fetching free trial grants:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
