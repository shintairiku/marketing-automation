import { NextRequest, NextResponse } from 'next/server';

import { auth } from '@clerk/nextjs/server';
import { createClient } from '@supabase/supabase-js';

function getSupabase() {
  return createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!
  );
}

interface RouteParams {
  params: Promise<{
    processId: string;
  }>;
}

export async function GET(request: NextRequest, { params }: RouteParams) {
  try {
    // Clerk認証を確認
    const { userId } = await auth();
    if (!userId) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    const { processId } = await params;

    // プロセス情報を取得
    const { data, error } = await getSupabase()
      .from('generated_articles_state')
      .select('*')
      .eq('id', processId)
      .eq('user_id', userId)  // ユーザーのアクセス権を確認
      .single();

    if (error || !data) {
      return NextResponse.json(
        { error: 'Process not found or access denied' },
        { status: 404 }
      );
    }

    // プロセス復帰情報を取得
    const { data: recoveryInfo } = await getSupabase()
      .rpc('get_process_recovery_info', { process_id: processId });

    return NextResponse.json({
      ...data,
      recovery_info: recoveryInfo?.[0] || null,
    });

  } catch (error) {
    console.error('API error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

export async function PATCH(request: NextRequest, { params }: RouteParams) {
  try {
    // Clerk認証を確認
    const { userId } = await auth();
    if (!userId) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    const { processId } = await params;
    const body = await request.json();

    // 更新可能なフィールドのみを抽出
    const allowedFields = [
      'status',
      'current_step_name',
      'progress_percentage',
      'is_waiting_for_input',
      'input_type',
      'auto_resume_eligible',
      'resume_from_step',
      'error_message',
      'image_mode',
      'generated_content',
      'process_metadata',
    ];

    const updateData: any = {};
    for (const field of allowedFields) {
      if (body[field] !== undefined) {
        updateData[field] = body[field];
      }
    }

    // last_activity_atは自動更新されるため、明示的に設定
    updateData.updated_at = new Date().toISOString();

    const { data, error } = await getSupabase()
      .from('generated_articles_state')
      .update(updateData)
      .eq('id', processId)
      .eq('user_id', userId)  // ユーザーのアクセス権を確認
      .select()
      .single();

    if (error || !data) {
      return NextResponse.json(
        { error: 'Process not found or access denied' },
        { status: 404 }
      );
    }

    return NextResponse.json(data);

  } catch (error) {
    console.error('API error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

export async function DELETE(request: NextRequest, { params }: RouteParams) {
  try {
    // Clerk認証を確認
    const { userId } = await auth();
    if (!userId) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    const { processId } = await params;

    const { error } = await getSupabase()
      .from('generated_articles_state')
      .delete()
      .eq('id', processId)
      .eq('user_id', userId);  // ユーザーのアクセス権を確認

    if (error) {
      return NextResponse.json(
        { error: 'Failed to delete process or access denied' },
        { status: 404 }
      );
    }

    return NextResponse.json({ message: 'Process deleted successfully' });

  } catch (error) {
    console.error('API error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}