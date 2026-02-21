import { NextResponse } from 'next/server';

import { clerkMiddleware, createRouteMatcher } from '@clerk/nextjs/server';

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

// 管理者ルート (admin ロールのみ)
const isAdminRoute = createRouteMatcher([
  '/admin(.*)',
]);

// 特権ユーザー (admin or privileged) のみアクセス可能なルート
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

/**
 * JWT sessionClaims からロールを取得。
 *
 * Clerk Dashboard の Sessions → Customize session token で設定:
 * { "metadata": "{{user.public_metadata}}" }
 *
 * これにより sessionClaims.metadata.role でロールにアクセス可能。
 */
function getUserRole(sessionClaims: CustomJwtSessionClaims | null | undefined): string | null {
  if (!sessionClaims?.metadata?.role) return null;
  const role = sessionClaims.metadata.role;
  if (role === 'admin' || role === 'privileged') return role;
  return null;
}

function isAdminOrPrivileged(sessionClaims: CustomJwtSessionClaims | null | undefined): boolean {
  const role = getUserRole(sessionClaims);
  return role === 'admin' || role === 'privileged';
}

function isAdmin(sessionClaims: CustomJwtSessionClaims | null | undefined): boolean {
  return getUserRole(sessionClaims) === 'admin';
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

  // Protected route check (認証 + ロールベースルート制御)
  if (!isPublicRoute(req) && isProtectedRoute(req)) {
    const { userId, sessionClaims } = await authObject();
    if (!userId) {
      const signInUrl = new URL('/sign-in', req.url);
      signInUrl.searchParams.set('redirect_url', req.url);
      return NextResponse.redirect(signInUrl);
    }

    // ロールベースのアクセス制御
    if (isPrivilegedOnlyRoute(req)) {
      // admin ルートは admin ロールのみ
      if (isAdminRoute(req)) {
        if (!isAdmin(sessionClaims)) {
          return NextResponse.redirect(new URL('/blog/new', req.url));
        }
      } else {
        // その他の特権ルートは admin or privileged
        if (!isAdminOrPrivileged(sessionClaims)) {
          return NextResponse.redirect(new URL('/blog/new', req.url));
        }
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
