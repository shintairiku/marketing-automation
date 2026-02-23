import { NextRequest, NextResponse } from 'next/server';

import { supabaseAdminClient } from '@/libs/supabase/supabase-admin';
import { auth, clerkClient } from '@clerk/nextjs/server';

/**
 * POST /api/organizations/[id]/invitations/[invitationId]
 * 招待を再送（既存の招待を取り消して新しい招待を作成）
 */
export async function POST(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string; invitationId: string }> }
) {
  try {
    const { userId } = await auth();

    if (!userId) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const { id, invitationId } = await params;
    const supabase = supabaseAdminClient;

    // 組織の clerk_organization_id を取得
    const { data: org } = await supabase
      .from('organizations')
      .select('clerk_organization_id, owner_user_id')
      .eq('id', id)
      .single();

    if (!org?.clerk_organization_id) {
      return NextResponse.json({ error: 'Organization not found' }, { status: 404 });
    }

    const client = await clerkClient();

    // 既存の招待を取得してメール・ロール情報を保存
    let email: string;
    let role: string;

    try {
      const existingInvitation = await client.organizations.getOrganizationInvitation({
        organizationId: org.clerk_organization_id,
        invitationId,
      });
      email = existingInvitation.emailAddress;
      role = existingInvitation.role;

      // 既存の招待を取り消し
      await client.organizations.revokeOrganizationInvitation({
        organizationId: org.clerk_organization_id,
        invitationId,
        requestingUserId: userId,
      });
    } catch (e) {
      console.error('Failed to revoke existing invitation:', e);
      return NextResponse.json(
        { error: '既存の招待の取り消しに失敗しました' },
        { status: 500 }
      );
    }

    // 新しい招待を作成（再送）
    const appUrl = process.env.NEXT_PUBLIC_APP_URL || process.env.VERCEL_URL;
    if (!appUrl) {
      return NextResponse.json(
        { error: 'サーバー設定エラー: サイトURLが設定されていません' },
        { status: 500 }
      );
    }
    const baseUrl = appUrl.startsWith('http') ? appUrl : `https://${appUrl}`;
    const redirectUrl = `${baseUrl.replace(/\/+$/, '')}/invitation/accept`;

    const newInvitation = await client.organizations.createOrganizationInvitation({
      organizationId: org.clerk_organization_id,
      emailAddress: email,
      role,
      inviterUserId: userId,
      redirectUrl,
    });

    return NextResponse.json({
      id: newInvitation.id,
      organization_id: id,
      email: newInvitation.emailAddress,
      role: role === 'org:admin' ? 'admin' : 'member',
      status: newInvitation.status,
    });
  } catch (error) {
    console.error('Failed to resend invitation:', error);
    const message = error instanceof Error ? error.message : 'Failed to resend invitation';
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

/**
 * DELETE /api/organizations/[id]/invitations/[invitationId]
 * 招待を取り消し
 */
export async function DELETE(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string; invitationId: string }> }
) {
  try {
    const { userId } = await auth();

    if (!userId) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const { id, invitationId } = await params;
    const supabase = supabaseAdminClient;

    const { data: org } = await supabase
      .from('organizations')
      .select('clerk_organization_id')
      .eq('id', id)
      .single();

    if (!org?.clerk_organization_id) {
      return NextResponse.json({ error: 'Organization not found' }, { status: 404 });
    }

    const client = await clerkClient();
    await client.organizations.revokeOrganizationInvitation({
      organizationId: org.clerk_organization_id,
      invitationId,
      requestingUserId: userId,
    });

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('Failed to revoke invitation:', error);
    const message = error instanceof Error ? error.message : 'Failed to revoke invitation';
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
