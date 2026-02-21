import { NextRequest, NextResponse } from 'next/server';

import { hasPrivilegedRole } from '@/lib/subscription';
import { supabaseAdminClient } from '@/libs/supabase/supabase-admin';
import { auth, clerkClient } from '@clerk/nextjs/server';

const BACKEND_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8080';

/**
 * GET /api/organizations
 * ユーザーが所属する組織一覧を取得
 */
export async function GET() {
  try {
    const { userId } = await auth();

    if (!userId) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const supabase = supabaseAdminClient;

    // ユーザーが所属する組織を取得
    const { data: memberships } = await supabase
      .from('organization_members')
      .select('organization_id')
      .eq('user_id', userId);

    if (!memberships || memberships.length === 0) {
      return NextResponse.json([]);
    }

    const orgIds = memberships.map((m) => m.organization_id);
    const { data: organizations } = await supabase
      .from('organizations')
      .select('*')
      .in('id', orgIds)
      .order('created_at', { ascending: false });

    return NextResponse.json(organizations || []);
  } catch (error) {
    console.error('Failed to fetch organizations:', error);
    return NextResponse.json(
      { error: 'Failed to fetch organizations' },
      { status: 500 }
    );
  }
}

/**
 * POST /api/organizations
 * 新しい組織を作成
 *
 * 特権ユーザー: Supabaseに直接作成 + 仮想サブスクリプション自動挿入
 * 一般ユーザー: バックエンド経由（チームプラン購入フローから呼ばれる想定）
 */
export async function POST(request: NextRequest) {
  try {
    const { getToken, userId } = await auth();
    const token = await getToken();

    if (!token || !userId) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const body = await request.json();
    const orgName = body.name;

    if (!orgName || typeof orgName !== 'string' || orgName.trim().length === 0) {
      return NextResponse.json({ error: 'Organization name is required' }, { status: 400 });
    }

    // ユーザー情報を取得
    const client = await clerkClient();
    const user = await client.users.getUser(userId);
    const userEmail = user.emailAddresses?.[0]?.emailAddress;
    const userFullName = `${user.firstName || ''} ${user.lastName || ''}`.trim();
    const isPrivileged = hasPrivilegedRole(user.publicMetadata as Record<string, unknown>);

    // 非特権ユーザーは直接組織作成不可（チームプラン購入フローで作成される）
    if (!isPrivileged) {
      return NextResponse.json(
        { error: 'チームプランの購入が必要です。Pricingページからチームプランを購入してください。' },
        { status: 403 }
      );
    }

    // 特権ユーザー: Clerk Organization + Supabase直接作成
    const clerkOrg = await client.organizations.createOrganization({
      name: orgName.trim(),
      createdBy: userId,
    });

    const supabase = supabaseAdminClient;

    const { data: newOrg, error: orgError } = await supabase
      .from('organizations')
      .insert({
        name: orgName.trim(),
        owner_user_id: userId,
        clerk_organization_id: clerkOrg.id,
      })
      .select()
      .single();

    if (orgError) {
      console.error('Error creating organization:', orgError);
      return NextResponse.json({ error: 'Failed to create organization' }, { status: 500 });
    }

    // オーナーをメンバーテーブルに追加（トリガーがない場合の安全策）
    await supabase
      .from('organization_members')
      .upsert({
        organization_id: newOrg.id,
        user_id: userId,
        role: 'owner',
        email: userEmail || null,
        display_name: userFullName || null,
      }, { onConflict: 'organization_id,user_id' });

    // 特権ユーザー用の仮想サブスクリプションを作成
    // 既存のサブスクチェックロジックがそのまま動作するようにする
    const virtualSubId = `privileged_${newOrg.id}`;
    await supabase
      .from('organization_subscriptions')
      .upsert({
        id: virtualSubId,
        organization_id: newOrg.id,
        status: 'active',
        quantity: 50,
        current_period_start: new Date().toISOString(),
        current_period_end: new Date(Date.now() + 100 * 365 * 24 * 60 * 60 * 1000).toISOString(), // 100年後
        metadata: { privileged: true, created_by: userId },
      }, { onConflict: 'id' });

    console.log(`Privileged org created: ${newOrg.id} by ${userEmail}`);

    return NextResponse.json(newOrg, { status: 201 });
  } catch (error) {
    console.error('Failed to create organization:', error);
    return NextResponse.json(
      { error: 'Failed to create organization' },
      { status: 500 }
    );
  }
}
