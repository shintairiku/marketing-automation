import { headers } from 'next/headers';
import { NextRequest, NextResponse } from 'next/server';
import { Webhook } from 'svix';

import { supabaseAdminClient } from '@/libs/supabase/supabase-admin';

const webhookSecret = process.env.CLERK_WEBHOOK_SECRET || '';

export async function POST(req: NextRequest) {
  const headerPayload = await headers();
  const svix_id = headerPayload.get('svix-id');
  const svix_timestamp = headerPayload.get('svix-timestamp');
  const svix_signature = headerPayload.get('svix-signature');

  if (!svix_id || !svix_timestamp || !svix_signature) {
    return new Response('Error occured -- no svix headers', {
      status: 400,
    });
  }

  if (!webhookSecret) {
    console.error('CLERK_WEBHOOK_SECRET is not configured');
    return new Response('Webhook secret not configured', {
      status: 500,
    });
  }

  const payload = await req.json();
  const body = JSON.stringify(payload);

  const wh = new Webhook(webhookSecret);

  let evt;

  try {
    evt = wh.verify(body, {
      'svix-id': svix_id,
      'svix-timestamp': svix_timestamp,
      'svix-signature': svix_signature,
    });
  } catch (err) {
    console.error('Error verifying Clerk webhook:', err);
    return new Response('Error occured', {
      status: 400,
    });
  }

  const { type, data } = evt as { type: string; data: any };
  console.log(`Received Clerk webhook: ${type}`, data);

  try {
    switch (type) {
      case 'organization.created':
        await handleOrganizationCreated(data);
        break;
      case 'organization.updated':
        await handleOrganizationUpdated(data);
        break;
      case 'organization.deleted':
        await handleOrganizationDeleted(data);
        break;
      case 'organizationMembership.created':
        await handleMembershipCreated(data);
        break;
      case 'organizationMembership.updated':
        await handleMembershipUpdated(data);
        break;
      case 'organizationMembership.deleted':
        await handleMembershipDeleted(data);
        break;
      case 'organizationInvitation.created':
        await handleInvitationCreated(data);
        break;
      case 'organizationInvitation.accepted':
        await handleInvitationAccepted(data);
        break;
      case 'organizationInvitation.revoked':
        await handleInvitationRevoked(data);
        break;
      default:
        console.log(`Unhandled Clerk webhook type: ${type}`);
    }
  } catch (error) {
    console.error(`Error handling Clerk webhook ${type}:`, error);
    return new Response(`Error handling ${type}`, { status: 500 });
  }

  return NextResponse.json({ received: true });
}

async function handleOrganizationCreated(data: any) {
  const { id, name, slug, created_by } = data;
  
  console.log(`Creating organization: ${name} (${id})`);
  
  // Supabaseに組織を作成
  const { error: orgError } = await supabaseAdminClient
    .from('organizations')
    .insert({
      id,
      name,
      slug,
      owner_user_id: created_by,
      max_seats: 2, // デフォルト最小シート数
      used_seats: 1, // オーナー分
      subscription_status: 'inactive', // 初期状態
    });

  if (orgError) {
    console.error('Failed to create organization in Supabase:', orgError);
    throw orgError;
  }

  // オーナーのメンバーシップを作成
  const { error: membershipError } = await supabaseAdminClient
    .from('organization_memberships')
    .insert({
      id: `mem_${id}_${created_by}`,
      organization_id: id,
      user_id: created_by,
      role: 'owner',
      status: 'active',
    });

  if (membershipError) {
    console.error('Failed to create owner membership:', membershipError);
    throw membershipError;
  }

  // 組織設定のデフォルト値を作成
  const { error: settingsError } = await supabaseAdminClient
    .from('organization_settings')
    .insert({
      organization_id: id,
      default_company_name: name,
      default_company_description: `${name}の記事生成プロジェクト`,
    });

  if (settingsError) {
    console.error('Failed to create organization settings:', settingsError);
    // 設定は必須ではないのでエラーをスローしない
  }

  console.log(`Successfully created organization: ${id}`);
}

async function handleOrganizationUpdated(data: any) {
  const { id, name, slug } = data;
  
  console.log(`Updating organization: ${name} (${id})`);
  
  const { error } = await supabaseAdminClient
    .from('organizations')
    .update({
      name,
      slug,
      updated_at: new Date().toISOString(),
    })
    .eq('id', id);

  if (error) {
    console.error('Failed to update organization in Supabase:', error);
    throw error;
  }

  console.log(`Successfully updated organization: ${id}`);
}

async function handleOrganizationDeleted(data: any) {
  const { id } = data;
  
  console.log(`Deleting organization: ${id}`);
  
  // CASCADE設定により関連データも自動削除される
  const { error } = await supabaseAdminClient
    .from('organizations')
    .delete()
    .eq('id', id);

  if (error) {
    console.error('Failed to delete organization from Supabase:', error);
    throw error;
  }

  console.log(`Successfully deleted organization: ${id}`);
}

async function handleMembershipCreated(data: any) {
  const { id, organization_id, public_user_data, role } = data;
  const user_id = public_user_data?.user_id;
  
  if (!user_id) {
    console.error('No user_id found in membership data');
    return;
  }

  console.log(`Creating membership: ${user_id} -> ${organization_id} (${role})`);
  
  const { error } = await supabaseAdminClient
    .from('organization_memberships')
    .insert({
      id,
      organization_id,
      user_id,
      role,
      status: 'active',
    });

  if (error) {
    console.error('Failed to create membership in Supabase:', error);
    throw error;
  }

  console.log(`Successfully created membership: ${id}`);
}

async function handleMembershipUpdated(data: any) {
  const { id, role } = data;
  
  console.log(`Updating membership: ${id} -> ${role}`);
  
  const { error } = await supabaseAdminClient
    .from('organization_memberships')
    .update({
      role,
    })
    .eq('id', id);

  if (error) {
    console.error('Failed to update membership in Supabase:', error);
    throw error;
  }

  console.log(`Successfully updated membership: ${id}`);
}

async function handleMembershipDeleted(data: any) {
  const { id } = data;
  
  console.log(`Deleting membership: ${id}`);
  
  const { error } = await supabaseAdminClient
    .from('organization_memberships')
    .delete()
    .eq('id', id);

  if (error) {
    console.error('Failed to delete membership from Supabase:', error);
    throw error;
  }

  console.log(`Successfully deleted membership: ${id}`);
}

async function handleInvitationCreated(data: any) {
  const { id, organization_id, email_address, role, created_by } = data;
  
  console.log(`Creating invitation: ${email_address} -> ${organization_id}`);
  
  // 招待トークンを生成（簡単なUUID）
  const invitationToken = `inv_${id}`;
  
  const { error } = await supabaseAdminClient
    .from('organization_invitations')
    .insert({
      organization_id,
      email: email_address,
      role,
      invited_by: created_by,
      invitation_token: invitationToken,
      status: 'pending',
      expires_at: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(), // 7日後
    });

  if (error) {
    console.error('Failed to create invitation in Supabase:', error);
    // Clerkの招待は既に作成されているので、エラーをスローしない
  }

  console.log(`Successfully created invitation: ${id}`);
}

async function handleInvitationAccepted(data: any) {
  const { id, organization_id, email_address } = data;
  
  console.log(`Invitation accepted: ${email_address} -> ${organization_id}`);
  
  // 招待ステータスを更新
  const { error } = await supabaseAdminClient
    .from('organization_invitations')
    .update({
      status: 'accepted',
      accepted_at: new Date().toISOString(),
    })
    .eq('organization_id', organization_id)
    .eq('email', email_address)
    .eq('status', 'pending');

  if (error) {
    console.error('Failed to update invitation status:', error);
  }

  console.log(`Successfully updated invitation status: ${id}`);
}

async function handleInvitationRevoked(data: any) {
  const { id, organization_id, email_address } = data;
  
  console.log(`Invitation revoked: ${email_address} -> ${organization_id}`);
  
  // 招待ステータスを更新
  const { error } = await supabaseAdminClient
    .from('organization_invitations')
    .update({
      status: 'cancelled',
    })
    .eq('organization_id', organization_id)
    .eq('email', email_address)
    .eq('status', 'pending');

  if (error) {
    console.error('Failed to update invitation status:', error);
  }

  console.log(`Successfully cancelled invitation: ${id}`);
}