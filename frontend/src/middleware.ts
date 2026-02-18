import { NextResponse } from 'next/server';

import { clerkClient, clerkMiddleware, createRouteMatcher } from '@clerk/nextjs/server';

// Define routes that should be protected (認証必須)
const isProtectedRoute = createRouteMatcher([
  '/admin(.*)',
  '/dashboard(.*)',
  '/account(.*)',
  '/generate(.*)',
  '/edit(.*)',
  '/tools(.*)',
  '/seo(.*)',
  '/instagram(.*)',
  '/line(.*)',
  '/blog(.*)',
  '/settings(.*)',
  '/company-settings(.*)',
  '/help(.*)',
]);

// 特権ユーザー(@shintairiku.jp)のみアクセス可能なルート
// 非特権ユーザーは /blog/new にリダイレクトされる
const isPrivilegedOnlyRoute = createRouteMatcher([
  '/admin(.*)',
  '/dashboard(.*)',
  '/seo(.*)',
  '/instagram(.*)',
  '/line(.*)',
  '/company-settings(.*)',
]);

// Define routes that should be public (accessible without authentication)
const isPublicRoute = createRouteMatcher([
  '/pricing',
  '/auth',
  '/sign-in(.*)',
  '/sign-up(.*)',
  '/invitation(.*)',
  '/api/webhooks/clerk(.*)',
]);

const PRIVILEGED_EMAIL_DOMAIN = '@shintairiku.jp';

function isPrivilegedEmail(email: string | undefined | null): boolean {
  if (!email) return false;
  return email.toLowerCase().endsWith(PRIVILEGED_EMAIL_DOMAIN);
}

/**
 * Clerk APIからユーザーのメールアドレスを取得する
 * sessionClaimsにはデフォルトでメールが含まれないため、APIで取得する
 */
async function getUserEmail(userId: string): Promise<string | undefined> {
  try {
    const client = await clerkClient();
    const user = await client.users.getUser(userId);
    return user.emailAddresses?.[0]?.emailAddress;
  } catch (e) {
    console.error('[MIDDLEWARE] Failed to fetch user email:', e);
    return undefined;
  }
}

// ルートパス `/` のマッチャー
const isRootRoute = createRouteMatcher(['/']);

export default clerkMiddleware(async (authObject, req) => {
  // ルート `/` へのアクセス: 認証状態に応じてリダイレクト
  if (isRootRoute(req)) {
    const { userId } = await authObject();
    if (userId) {
      // ログイン済み → /blog/new（SubscriptionGuardが課金チェックを行う）
      return NextResponse.redirect(new URL('/blog/new', req.url));
    }
    // 未ログイン → /auth（サインイン/サインアップ選択画面）
    return NextResponse.redirect(new URL('/auth', req.url));
  }

  // Protected route check (認証 + 特権ルート制御)
  if (!isPublicRoute(req) && isProtectedRoute(req)) {
    const { userId } = await authObject();
    if (!userId) {
      const signInUrl = new URL('/sign-in', req.url);
      signInUrl.searchParams.set('redirect_url', req.url);
      return NextResponse.redirect(signInUrl);
    }

    // 特権ユーザー専用ルートのチェック
    // 非特権ユーザーがアクセスした場合は /blog/new にリダイレクト
    if (isPrivilegedOnlyRoute(req)) {
      const userEmail = await getUserEmail(userId);
      if (!isPrivilegedEmail(userEmail)) {
        return NextResponse.redirect(new URL('/blog/new', req.url));
      }
    }
  }
  return NextResponse.next();
});

export const config = {
  matcher: [
    // Skip Next.js internals and all static files, unless found in search params
    '/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)',
    // Always run for API routes
    '/(api|trpc)(.*)',
  ],
};
