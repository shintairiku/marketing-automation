import { NextRequest, NextResponse } from 'next/server';

import { backendFetch } from '@/lib/backend-fetch';
import { supabaseAdminClient } from '@/libs/supabase/supabase-admin';
import { auth, clerkClient } from '@clerk/nextjs/server';

/**
 * GET /api/organizations/[id]/invitations
 * 組織の保留中招待一覧を取得（Clerk API経由）
 */
export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { getToken } = await auth();
    const token = await getToken();

    if (!token) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const { id } = await params;
    const supabase = supabaseAdminClient;

    // Supabaseから clerk_organization_id を取得
    const { data: org } = await supabase
      .from('organizations')
      .select('clerk_organization_id')
      .eq('id', id)
      .single();

    if (!org?.clerk_organization_id) {
      return NextResponse.json([], { status: 200 });
    }

    // Clerk APIから保留中招待を取得
    const client = await clerkClient();
    const invitationList = await client.organizations.getOrganizationInvitationList({
      organizationId: org.clerk_organization_id,
      status: ['pending'],
    });

    const invitations = invitationList.data.map((inv) => ({
      id: inv.id,
      organization_id: id,
      email: inv.emailAddress,
      role: inv.role === 'org:admin' ? 'admin' : 'member',
      status: inv.status,
      expires_at: inv.createdAt ? new Date(inv.createdAt + 7 * 24 * 60 * 60 * 1000).toISOString() : null,
      created_at: inv.createdAt ? new Date(inv.createdAt).toISOString() : null,
    }));

    return NextResponse.json(invitations);
  } catch (error) {
    console.error('Failed to fetch invitations:', error);
    return NextResponse.json(
      { error: 'Failed to fetch invitations' },
      { status: 500 }
    );
  }
}

/**
 * POST /api/organizations/[id]/invitations
 * メンバーを組織に招待（Clerk API経由で招待メール送信）
 */
export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { getToken, userId } = await auth();
    const token = await getToken();

    if (!token || !userId) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const { id } = await params;
    const body = await request.json();
    const { email, role = 'member' } = body;

    const supabase = supabaseAdminClient;

    // Supabaseから組織情報を取得
    const { data: org } = await supabase
      .from('organizations')
      .select('clerk_organization_id')
      .eq('id', id)
      .single();

    if (!org?.clerk_organization_id) {
      return NextResponse.json(
        { error: 'Organization not found or Clerk organization not linked' },
        { status: 404 }
      );
    }

    // シート制限チェック
    const [memberResult, pendingInvResult, subResult] = await Promise.all([
      supabase
        .from('organization_members')
        .select('user_id', { count: 'exact' })
        .eq('organization_id', id),
      supabase
        .from('invitations')
        .select('id', { count: 'exact' })
        .eq('organization_id', id)
        .eq('status', 'pending'),
      supabase
        .from('organization_subscriptions')
        .select('quantity')
        .eq('organization_id', id)
        .single(),
    ]);

    const memberCount = memberResult.count || 0;
    const pendingCount = pendingInvResult.count || 0;
    const maxSeats = subResult.data?.quantity || 0;

    // チームプラン未購入の場合は招待不可
    if (!subResult.data || maxSeats === 0) {
      return NextResponse.json(
        { error: 'チームプランが必要です。Pricingページからチームプランを購入してください。' },
        { status: 403 }
      );
    }

    if ((memberCount + pendingCount) >= maxSeats) {
      return NextResponse.json(
        { error: 'シートに空きがありません。追加購入が必要です。' },
        { status: 400 }
      );
    }

    // Clerk Organization Invitation を作成（自動でメール送信される）
    const client = await clerkClient();
    const clerkRole = role === 'admin' ? 'org:admin' : 'org:member';

    const appUrl = process.env.NEXT_PUBLIC_SITE_URL || process.env.NEXT_PUBLIC_APP_URL || process.env.VERCEL_URL;
    if (!appUrl) {
      console.error('No site URL configured. Set NEXT_PUBLIC_SITE_URL or NEXT_PUBLIC_APP_URL.');
      return NextResponse.json(
        { error: 'サーバー設定エラー: サイトURLが設定されていません' },
        { status: 500 }
      );
    }
    const baseUrl = appUrl.startsWith('http') ? appUrl : `https://${appUrl}`;
    const redirectUrl = `${baseUrl.replace(/\/+$/, '')}/invitation/accept`;

    console.log('[Invitation] Creating invitation with redirectUrl:', redirectUrl);

    const clerkInvitation = await client.organizations.createOrganizationInvitation({
      organizationId: org.clerk_organization_id,
      emailAddress: email,
      role: clerkRole,
      inviterUserId: userId,
      redirectUrl,
    });

    // バックエンドにも記録（追跡用）
    try {
      await backendFetch(`/organizations/${id}/invitations`, token, {
        method: 'POST',
        body: JSON.stringify({ email, role }),
      });
    } catch (backendError) {
      // バックエンド記録の失敗はClerk招待には影響させない
      console.warn('Failed to record invitation in backend:', backendError);
    }

    return NextResponse.json({
      id: clerkInvitation.id,
      organization_id: id,
      email: clerkInvitation.emailAddress,
      role,
      status: clerkInvitation.status,
    }, { status: 201 });
  } catch (error: unknown) {
    console.error('Failed to create invitation:', error);

    // Clerk APIエラーの詳細をログ出力
    if (error && typeof error === 'object' && 'errors' in error) {
      const clerkErr = error as { errors: Array<{ message: string; longMessage?: string; code: string }> };
      console.error('Clerk API error details:', JSON.stringify(clerkErr.errors, null, 2));
    }

    const message = error instanceof Error ? error.message : 'Failed to create invitation';
    return NextResponse.json(
      { error: message },
      { status: 500 }
    );
  }
}
