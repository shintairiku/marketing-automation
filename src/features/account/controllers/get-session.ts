import { createSupabaseServerClient } from '@/libs/supabase/supabase-server-client';

export async function getSession() {
  try {
    const supabase = await createSupabaseServerClient();
    
    // より安全なgetUser()メソッドを使用
    const { data: userData, error: userError } = await supabase.auth.getUser();
    
    if (userError) {
      // 認証されていない状態はエラーとして扱わない
      // AuthSessionMissingErrorを含む全ての認証関連エラーをサイレントに処理
      if (userError.status === 401 || 
          (userError as any).__isAuthError === true || 
          userError.message?.includes('Auth session missing')) {
        return null;
      }
      
      // その他の認証エラーのみログに記録
      console.error('User authentication error:', userError);
      return null;
    }
    
    if (userData?.user) {
      return {
        user: userData.user
      };
    }
    
    return null;
  } catch (error) {
    console.error('Session retrieval error:', error);
    return null;
  }
}