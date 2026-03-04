import type { Metadata } from 'next';

import PublicHeader from '@/components/display/public-header';

export const metadata: Metadata = {
  robots: 'index, follow',
};

export default function LegalLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-stone-50">
      <PublicHeader />

      <main className="mx-auto max-w-3xl px-4 py-10 sm:px-6 sm:py-14">
        {children}
      </main>

      <footer className="border-t border-stone-200 bg-white">
        <div className="mx-auto max-w-3xl px-4 py-6 sm:px-6">
          <p className="text-center text-xs text-stone-400">
            &copy; {new Date().getFullYear()} 株式会社新大陸. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  );
}
