import { NextResponse } from 'next/server';
import { jwtVerify } from 'jose';

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
  '/offline',
  '/legal(.*)',
  '/sign-in(.*)',
  '/sign-up(.*)',
  '/invitation(.*)',
  '/api/webhooks/clerk(.*)',
]);

/**
 * JWT sessionClaims からロールを取得。
 *
 * Clerk Dashboard の Sessions → Customize session token で設定:
 * {
 *   "role": "authenticated",
 *   "metadata": "{{user.public_metadata}}",
 *   "twoFactorEnabled": "{{user.two_factor_enabled}}"
 * }
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

/**
 * カスタム TOTP セッション JWT を検証 (Edge Runtime 対応)
 */
async function verifyMfaSession(token: string, userId: string): Promise<boolean> {
  try {
    const secret = new TextEncoder().encode(
      process.env.ADMIN_MFA_SESSION_SECRET || 'dev-mfa-secret-change-in-production'
    );
    const { payload } = await jwtVerify(token, secret);
    return payload.sub === userId;
  } catch {
    return false;
  }
}

// ルートパス `/` のマッチャー
const isRootRoute = createRouteMatcher(['/']);

// MFA 検証ページ自体のマッチャー（無限リダイレクト防止）
const isMfaVerifyRoute = createRouteMatcher(['/admin/mfa-verify']);

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
      // admin ルートは admin ロールのみ + カスタム TOTP MFA 必須
      if (isAdminRoute(req)) {
        if (!isAdmin(sessionClaims)) {
          return NextResponse.redirect(new URL('/blog/new', req.url));
        }

        // MFA 検証ページ自体は MFA チェック不要（無限ループ防止）
        if (!isMfaVerifyRoute(req)) {
          // カスタム TOTP セッションクッキーを確認
          const mfaCookie = req.cookies.get('admin_mfa_session')?.value;
          let mfaVerified = false;
          if (mfaCookie) {
            mfaVerified = await verifyMfaSession(mfaCookie, userId);
          }

          if (!mfaVerified) {
            // TOTP 設定済みかのヒントクッキーを確認
            const totpConfigured =
              req.cookies.get('admin_totp_configured')?.value === 'true';
            if (totpConfigured) {
              // 設定済み → 検証ページへ
              const verifyUrl = new URL('/admin/mfa-verify', req.url);
              verifyUrl.searchParams.set('redirect', req.nextUrl.pathname);
              return NextResponse.redirect(verifyUrl);
            } else {
              // 未設定 → セットアップページへ
              return NextResponse.redirect(
                new URL('/settings/account/mfa-setup', req.url)
              );
            }
          }
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
