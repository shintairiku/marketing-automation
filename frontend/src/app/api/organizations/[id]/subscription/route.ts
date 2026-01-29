import { NextRequest, NextResponse } from 'next/server';

import { supabaseAdminClient } from '@/libs/supabase/supabase-admin';
import { auth } from '@clerk/nextjs/server';

/**
 * GET /api/organizations/[id]/subscription
 * 組織のサブスクリプション情報を取得（Supabaseから直接）
 */
export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { userId } = await auth();

    if (!userId) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const { id } = await params;
    const supabase = supabaseAdminClient;

    // ユーザーが組織のメンバーであることを確認
    const { data: membership } = await supabase
      .from('organization_members')
      .select('role')
      .eq('organization_id', id)
      .eq('user_id', userId)
      .single();

    if (!membership) {
      return NextResponse.json({ error: 'Not a member of this organization' }, { status: 403 });
    }

    // 組織のサブスクリプションを取得（activeを優先）
    const { data: orgSubs } = await supabase
      .from('organization_subscriptions')
      .select('*')
      .eq('organization_id', id)
      .order('status', { ascending: true });

    if (!orgSubs || orgSubs.length === 0) {
      return NextResponse.json(null, { status: 200 });
    }

    // active なサブスクを優先
    const activeSub = orgSubs.find((s) => s.status === 'active')
      || orgSubs.find((s) => s.status === 'past_due')
      || orgSubs[0];

    return NextResponse.json({
      id: activeSub.id,
      organization_id: activeSub.organization_id,
      status: activeSub.status,
      quantity: activeSub.quantity || 1,
      current_period_end: activeSub.current_period_end,
      cancel_at_period_end: activeSub.cancel_at_period_end || false,
    });
  } catch (error) {
    console.error('Failed to fetch organization subscription:', error);
    return NextResponse.json(
      { error: 'Failed to fetch organization subscription' },
      { status: 500 }
    );
  }
}
