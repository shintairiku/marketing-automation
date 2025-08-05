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

// Define routes that should be public (accessible without authentication)
const isPublicRoute = createRouteMatcher([
  '/', // Landing page
  '/pricing',
  '/sign-in(.*)', // Clerk sign-in routes
  '/sign-up(.*)', // Clerk sign-up routes
  '/api/webhooks(.*)', // Stripe webhook (usually public, but ensure security)
  // 他に公開したいルートがあればここに追加
]);


export default clerkMiddleware(async (authObject, req) => {
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
