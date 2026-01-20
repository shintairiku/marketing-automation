import { NextResponse } from 'next/server';

import { clerkMiddleware, createRouteMatcher } from '@clerk/nextjs/server';

// Define routes that should be protected
const isProtectedRoute = createRouteMatcher([
  '/dashboard(.*)', // Protects all routes under /dashboard
  '/account(.*)',   // Protects /account
  '/generate(.*)',  // Protects /generate and its sub-routes
  '/edit(.*)',      // Protects /edit and its sub-routes
  '/tools(.*)',     // Protects /tools and its sub-routes
  '/seo(.*)',       // Protects /seo and its sub-routes
  '/instagram(.*)', // Protects /instagram and its sub-routes
  '/line(.*)',      // Protects /line and its sub-routes
  // 他に保護したいルートがあればここに追加
]);

// Define admin routes that require @shintairiku.jp email
const isAdminRoute = createRouteMatcher([
  '/admin(.*)', // Protects all routes under /admin
]);

// Define routes that should be public (accessible without authentication)
const isPublicRoute = createRouteMatcher([
  '/', // Landing page
  '/pricing',
  '/sign-in(.*)', // Clerk sign-in routes
  '/sign-up(.*)', // Clerk sign-up routes
  '/api/webhooks(.*)', // Stripe webhook (usually public, but ensure security)
  // 他に公開したいルートがあればここに追加
]);

// Admin email domain check
const ADMIN_EMAIL_DOMAIN = '@shintairiku.jp';

function isAdminEmail(email: string | undefined | null): boolean {
  if (!email) return false;
  return email.toLowerCase().endsWith(ADMIN_EMAIL_DOMAIN);
}

// ClerkのsessionClaimsは環境や設定でフィールド名が異なる場合があるため、代表的なキーを総当たりで取得
function resolveAdminEmail(sessionClaims: Record<string, unknown> | null | undefined): string | undefined {
  if (!sessionClaims) return undefined;
  const candidates = [
    sessionClaims['email'],
    sessionClaims['email_address'],
    // Clerkのemail_addresses配列
    Array.isArray((sessionClaims as any)['email_addresses'])
      ? (sessionClaims as any)['email_addresses']?.[0]?.email_address
      : undefined,
    // primaryEmailAddress?.emailAddress が claims に含まれる場合
    (sessionClaims as any)['primary_email_address'],
    (sessionClaims as any)['primaryEmailAddress'],
  ];
  const email = candidates.find((v) => typeof v === 'string') as string | undefined;
  return email;
}

export default clerkMiddleware(async (authObject, req) => {
  // Admin route protection
  if (isAdminRoute(req)) {
    const authData = await authObject();
    const { userId, sessionClaims } = authData;

    if (!userId) {
      const signInUrl = new URL('/sign-in', req.url);
      signInUrl.searchParams.set('redirect_url', req.url);
      return NextResponse.redirect(signInUrl);
    }

    // Try to get email from sessionClaims
    // Note: Clerk may need to be configured to include email in sessionClaims
    let userEmail: string | undefined;
    
    // Method 1: Try to get from sessionClaims
    userEmail = resolveAdminEmail(sessionClaims as Record<string, unknown> | null | undefined);
    
    // Debug logging
    /*
    console.log('[ADMIN_MIDDLEWARE] userId:', userId);
    console.log('[ADMIN_MIDDLEWARE] sessionClaims keys:', sessionClaims ? Object.keys(sessionClaims) : 'null');
    console.log('[ADMIN_MIDDLEWARE] sessionClaims full:', JSON.stringify(sessionClaims, null, 2));
    console.log('[ADMIN_MIDDLEWARE] resolved email:', userEmail);
    */
   
    // If email is not in sessionClaims, we'll check it at the page level
    // For now, allow access if userId exists and let the page handle email check
    // This is a temporary solution - ideally Clerk should be configured to include email in sessionClaims

    /*
    if (!userEmail) {
      console.log('[ADMIN_MIDDLEWARE] Email not found in sessionClaims - allowing access, page will check');
      // Allow access for now - page-level check will handle email validation
      // This is not ideal but necessary if Clerk doesn't include email in sessionClaims
    } else if (!isAdminEmail(userEmail)) {
      // Redirect to unauthorized page if email is found and doesn't match
      console.log('[ADMIN_MIDDLEWARE] Access denied - email does not match admin domain');
      return NextResponse.redirect(new URL('/', req.url));
    } else {
      console.log('[ADMIN_MIDDLEWARE] Access granted - email matches admin domain');
    }
    */
  }
  
  // Regular protected route check
  if (!isPublicRoute(req) && isProtectedRoute(req)) {
    const { userId } = await authObject();
    if (!userId) {
      const signInUrl = new URL('/sign-in', req.url)
      signInUrl.searchParams.set('redirect_url', req.url)
      return NextResponse.redirect(signInUrl)
    }
  }
  return NextResponse.next();
});

export const config = {
  matcher: [
    // Skip Next.js internals and all static files, unless found in search params
    '/((?!_next|[^?]*\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)',
    // Always run for API routes
    '/(api|trpc)(.*)',
  ],
};
