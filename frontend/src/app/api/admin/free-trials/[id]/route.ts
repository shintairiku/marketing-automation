/**
 * Admin Free Trial Grant Detail API
 *
 * DELETE /api/admin/free-trials/[id] — トライアル取り消し (Stripe Coupon 削除 + DB 更新)
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

export async function DELETE(
  _request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const adminCheck = await requireAdmin();
    if ('error' in adminCheck && adminCheck.error instanceof NextResponse) {
      return adminCheck.error;
    }

    const { id } = await params;
    const supabase = supabaseAdminClient;

    // Grant を取得
    const { data: grant, error: fetchError } = await (supabase as any)
      .from('free_trial_grants')
      .select('*')
      .eq('id', id)
      .maybeSingle();

    if (fetchError || !grant) {
      return NextResponse.json(
        { error: 'Grant not found' },
        { status: 404 }
      );
    }

    // active なサブスクに使用済みのクーポンは削除しない（Stripe側で自然失効させる）
    if (grant.status === 'pending') {
      // Stripe Coupon を削除
      const stripe = getStripe();
      await stripe.coupons.del(grant.stripe_coupon_id).catch((err: Error) => {
        console.warn('Failed to delete Stripe coupon:', err.message);
      });
    }

    // DB ステータスを revoked に更新
    const { error: updateError } = await (supabase as any)
      .from('free_trial_grants')
      .update({ status: 'revoked' })
      .eq('id', id);

    if (updateError) {
      console.error('Failed to revoke grant:', updateError);
      return NextResponse.json(
        { error: 'Failed to revoke grant' },
        { status: 500 }
      );
    }

    return new NextResponse(null, { status: 204 });
  } catch (error) {
    console.error('Error revoking free trial grant:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
