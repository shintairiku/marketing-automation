// パスワードリセット用ルートハンドラ

import type { NextRequest } from 'next/server';
import { NextResponse } from 'next/server';

import { createSupabaseServerClient } from '@/libs/supabase/supabase-server-client';
import { getURL } from '@/utils/get-url';

const siteUrl = getURL();

export async function GET(request: NextRequest) {
  // URLからリセットコードとタイプを取得
  const requestUrl = new URL(request.url);
  const code = requestUrl.searchParams.get('code');
  
  if (code) {
    const supabase = await createSupabaseServerClient();
    
    // セッションを設定
    await supabase.auth.exchangeCodeForSession(code);
    
    // パスワード変更ページへリダイレクト
    return NextResponse.redirect(`${siteUrl}/auth/update-password`);
  }

  // コードがない場合はログインページへ
  return NextResponse.redirect(`${siteUrl}/login?error=invalid_reset_code`);
}
