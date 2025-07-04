import { NextRequest, NextResponse } from 'next/server';

import { auth } from '@clerk/nextjs/server';
import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
);

export async function POST(request: NextRequest) {
  try {
    // Clerk認証を確認
    const { userId } = await auth();
    if (!userId) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    const body = await request.json();
    const {
      initial_keywords,
      target_age_group,
      persona_type,
      custom_persona,
      target_length,
      company_name,
      company_description,
      company_style_guide,
      organization_id,
      image_mode,
      image_settings,
    } = body;

    // 初期コンテキストの作成
    const initialContext = {
      initial_keywords: initial_keywords || [],
      target_age_group,
      persona_type,
      custom_persona,
      target_length,
      company_name,
      company_description,
      company_style_guide,
      image_mode,
      image_settings,
      current_step: 'start',
      generated_detailed_personas: [],
      research_query_results: [],
      generated_sections_html: [],
      section_writer_history: [],
    };

    // プロセス作成
    const { data, error } = await supabase
      .from('generated_articles_state')
      .insert({
        flow_id: null, // 従来の記事生成ではフローを使用しない
        user_id: userId,
        organization_id,
        image_mode: image_mode ?? false,
        status: 'in_progress',
        current_step_name: 'start',
        progress_percentage: 0,
        is_waiting_for_input: false,
        auto_resume_eligible: true,
        article_context: initialContext,
        generated_content: {},
        step_history: [],
        process_metadata: {
          created_from: 'new_article_page',
          initial_request: body,
        },
      })
      .select('id')
      .single();

    if (error) {
      console.error('Database error:', error);
      return NextResponse.json(
        { error: 'Failed to create generation process' },
        { status: 500 }
      );
    }

    return NextResponse.json({
      process_id: data.id,
      message: 'Generation process created successfully',
    });

  } catch (error) {
    console.error('API error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}