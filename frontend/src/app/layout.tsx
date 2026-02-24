import type { Metadata, Viewport } from 'next';
import { Toaster as SonnerToaster } from 'sonner';

import { ServiceWorkerRegister } from '@/components/pwa/service-worker-register';
import { Toaster } from '@/components/ui/toaster';
import { jaJP } from "@clerk/localizations";
import { ClerkProvider } from '@clerk/nextjs';
import { Analytics } from '@vercel/analytics/react';

import '@/styles/globals.css';

export const dynamic = 'force-dynamic';

const APP_NAME = 'BlogAI';
const APP_DESCRIPTION =
  'AIを活用したブログ記事自動生成サービス。あなたのWordPressサイトに最適な記事を生成します。';

export const metadata: Metadata = {
  applicationName: APP_NAME,
  title: {
    default: APP_NAME,
    template: `%s | ${APP_NAME}`,
  },
  description: APP_DESCRIPTION,
  icons: {
    icon: '/favicon.png',
    apple: '/apple-touch-icon.png',
  },
  appleWebApp: {
    capable: true,
    statusBarStyle: 'default',
    title: APP_NAME,
  },
  formatDetection: {
    telephone: false,
  },
  openGraph: {
    type: 'website',
    siteName: APP_NAME,
    title: {
      default: APP_NAME,
      template: `%s | ${APP_NAME}`,
    },
    description: APP_DESCRIPTION,
  },
  twitter: {
    card: 'summary',
    title: {
      default: APP_NAME,
      template: `%s | ${APP_NAME}`,
    },
    description: APP_DESCRIPTION,
  },
};

export const viewport: Viewport = {
  themeColor: '#0f172a',
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <ClerkProvider localization={jaJP}>
      <html lang='ja' dir='ltr'>
        <body className="font-sans antialiased">
          {children}
          <Toaster />
          <SonnerToaster position="top-right" />
          <Analytics />
          <ServiceWorkerRegister />
        </body>
      </html>
    </ClerkProvider>
  );
}
