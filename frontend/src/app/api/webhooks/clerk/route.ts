/**
 * Clerk Webhook Handler
 *
 * Clerkイベントを受信してSupabaseに同期するWebhookエンドポイント
 *
 * 処理するイベント:
 * - user.created → user_subscriptions に初期レコード作成
 * - organizationMembership.created → organization_members にinsert
 * - organizationMembership.deleted → organization_members から削除
 * - organizationInvitation.accepted → invitations テーブルのstatus更新
 */

import { NextRequest, NextResponse } from 'next/server';
import { Webhook } from 'svix';

import { supabaseAdminClient } from '@/libs/supabase/supabase-admin';

const CLERK_WEBHOOK_SECRET = process.env.CLERK_WEBHOOK_SECRET;

interface WebhookEvent {
  type: string;
  data: Record<string, unknown>;
}

async function verifyWebhook(req: NextRequest): Promise<WebhookEvent> {
  if (!CLERK_WEBHOOK_SECRET) {
    throw new Error('CLERK_WEBHOOK_SECRET is not configured');
  }

  const body = await req.text();
  const svixId = req.headers.get('svix-id');
  const svixTimestamp = req.headers.get('svix-timestamp');
  const svixSignature = req.headers.get('svix-signature');

  if (!svixId || !svixTimestamp || !svixSignature) {
    throw new Error('Missing svix headers');
  }

  const wh = new Webhook(CLERK_WEBHOOK_SECRET);
  const evt = wh.verify(body, {
    'svix-id': svixId,
    'svix-timestamp': svixTimestamp,
    'svix-signature': svixSignature,
  }) as WebhookEvent;

  return evt;
}

function isPrivilegedEmail(email: string | null | undefined): boolean {
  if (!email) return false;
  const emailLower = email.toLowerCase();

  // 個別メール許可リスト
  const allowedEmails = (process.env.ADMIN_ALLOWED_EMAILS || '')
    .split(',')
    .map((e) => e.trim().toLowerCase())
    .filter(Boolean);
  if (allowedEmails.includes(emailLower)) return true;

  // ドメイン許可リスト（デフォルト @shintairiku.jp + 環境変数追加分）
  const extraDomains = (process.env.ADMIN_ALLOWED_DOMAINS || '')
    .split(',')
    .map((d) => {
      let domain = d.trim().toLowerCase();
      if (domain && !domain.startsWith('@')) domain = `@${domain}`;
      return domain;
    })
    .filter(Boolean);
  const allowedDomains = ['@shintairiku.jp', ...extraDomains];

  return allowedDomains.some((domain) => emailLower.endsWith(domain));
}

export async function POST(req: NextRequest) {
  try {
    const evt = await verifyWebhook(req);
    const supabase = supabaseAdminClient;

    console.log(`[Clerk Webhook] Received event: ${evt.type}`);

    switch (evt.type) {
      case 'user.created': {
        const data = evt.data as {
          id: string;
          email_addresses?: Array<{ email_address: string }>;
        };
        const userId = data.id;
        const email = data.email_addresses?.[0]?.email_address || null;

        // user_subscriptions に初期レコード作成
        const { error } = await supabase
          .from('user_subscriptions')
          .upsert({
            user_id: userId,
            email,
            status: 'none',
            is_privileged: isPrivilegedEmail(email),
          }, { onConflict: 'user_id' });

        if (error) {
          console.error('[Clerk Webhook] Error creating user_subscription:', error);
        } else {
          console.log(`[Clerk Webhook] Created user_subscription for ${userId}`);
        }
        break;
      }

      case 'organizationMembership.created': {
        const data = evt.data as {
          id: string;
          organization: { id: string };
          public_user_data: {
            user_id: string;
            identifier?: string;
            first_name?: string;
            last_name?: string;
          };
          role: string;
        };

        const clerkOrgId = data.organization.id;
        const userId = data.public_user_data.user_id;
        const email = data.public_user_data.identifier || null;
        const displayName = [
          data.public_user_data.first_name,
          data.public_user_data.last_name,
        ].filter(Boolean).join(' ') || null;
        const role = data.role === 'org:admin' ? 'admin' : 'member';

        // clerk_organization_id → organizations.id 検索
        const { data: orgData } = await supabase
          .from('organizations')
          .select('id, owner_user_id')
          .eq('clerk_organization_id', clerkOrgId)
          .single();

        if (!orgData) {
          console.warn(`[Clerk Webhook] Organization not found for clerk_org_id: ${clerkOrgId}`);
          break;
        }

        // オーナーの場合はDBトリガーで既にinsert済みなのでスキップ
        if (orgData.owner_user_id === userId) {
          console.log(`[Clerk Webhook] Skipping owner membership for org ${orgData.id}`);
          break;
        }

        // organization_members に insert
        const { error } = await supabase
          .from('organization_members')
          .upsert({
            organization_id: orgData.id,
            user_id: userId,
            role,
            email,
            display_name: displayName,
            clerk_membership_id: data.id,
          }, { onConflict: 'organization_id,user_id' });

        if (error) {
          console.error('[Clerk Webhook] Error adding org member:', error);
        } else {
          console.log(`[Clerk Webhook] Added member ${userId} to org ${orgData.id}`);
        }
        break;
      }

      case 'organizationMembership.deleted': {
        const data = evt.data as {
          organization: { id: string };
          public_user_data: { user_id: string };
        };

        const clerkOrgId = data.organization.id;
        const userId = data.public_user_data.user_id;

        // clerk_organization_id → organizations.id 検索
        const { data: orgData } = await supabase
          .from('organizations')
          .select('id')
          .eq('clerk_organization_id', clerkOrgId)
          .single();

        if (!orgData) {
          console.warn(`[Clerk Webhook] Organization not found for clerk_org_id: ${clerkOrgId}`);
          break;
        }

        // organization_members から削除
        const { error } = await supabase
          .from('organization_members')
          .delete()
          .eq('organization_id', orgData.id)
          .eq('user_id', userId);

        if (error) {
          console.error('[Clerk Webhook] Error removing org member:', error);
        } else {
          console.log(`[Clerk Webhook] Removed member ${userId} from org ${orgData.id}`);
        }
        break;
      }

      case 'organizationInvitation.accepted': {
        const data = evt.data as {
          organization_id: string;
          email_address: string;
          status: string;
        };

        const clerkOrgId = data.organization_id;
        const email = data.email_address;

        // clerk_organization_id → organizations.id 検索
        const { data: orgData } = await supabase
          .from('organizations')
          .select('id')
          .eq('clerk_organization_id', clerkOrgId)
          .single();

        if (!orgData) {
          console.warn(`[Clerk Webhook] Organization not found for clerk_org_id: ${clerkOrgId}`);
          break;
        }

        // invitations テーブルのstatus更新（追跡用）
        const { error } = await supabase
          .from('invitations')
          .update({ status: 'accepted' })
          .eq('organization_id', orgData.id)
          .eq('email', email)
          .eq('status', 'pending');

        if (error) {
          console.error('[Clerk Webhook] Error updating invitation status:', error);
        } else {
          console.log(`[Clerk Webhook] Updated invitation status for ${email} in org ${orgData.id}`);
        }
        break;
      }

      default:
        console.log(`[Clerk Webhook] Unhandled event type: ${evt.type}`);
    }

    return NextResponse.json({ received: true });
  } catch (error) {
    console.error('[Clerk Webhook] Error processing webhook:', error);
    return NextResponse.json(
      { error: 'Webhook processing failed' },
      { status: 400 }
    );
  }
}
