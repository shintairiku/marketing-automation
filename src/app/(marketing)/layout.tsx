import { PropsWithChildren } from 'react';
import Link from 'next/link';
import { IoLogoFacebook, IoLogoInstagram, IoLogoTwitter } from 'react-icons/io5';

import { Logo } from '@/components/logo';
import { Navigation } from '../navigation';

export default function MarketingLayout({ children }: PropsWithChildren) {
  return (
    <div className='m-auto flex h-full max-w-[1440px] flex-col px-4'>
      <AppBar />
      <main className='relative flex-1'>
        <div className='relative h-full'>{children}</div>
      </main>
      <Footer />
    </div>
  );
}

async function AppBar() {
  return (
    <header className='flex items-center justify-between py-8'>
      <Logo />
      <Navigation />
    </header>
  );
}

function Footer() {
  return (
    <footer className='mt-8 flex flex-col gap-8 text-neutral-400 lg:mt-32'>
      <div className='flex flex-col justify-between gap-8 lg:flex-row'>
        <div>
          <Logo />
        </div>
        <div className='grid grid-cols-2 gap-8 sm:grid-cols-4 lg:grid-cols-4 lg:gap-16'>
          <div className='flex flex-col gap-2 lg:gap-6'>
            <div className='font-semibold text-neutral-100'>サービス</div>
            <nav className='flex flex-col gap-2 lg:gap-6'>
              <Link href='/pricing'>料金プラン</Link>
              <Link href='/features'>機能紹介</Link>
            </nav>
          </div>
          <div className='flex flex-col gap-2 lg:gap-6'>
            <div className='font-semibold text-neutral-100'>会社情報</div>
            <nav className='flex flex-col gap-2 lg:gap-6'>
              <Link href='/about-us'>会社概要</Link>
              <Link href='/privacy'>プライバシーポリシー</Link>
              <Link href='/terms'>利用規約</Link>
            </nav>
          </div>
          <div className='flex flex-col gap-2 lg:gap-6'>
            <div className='font-semibold text-neutral-100'>サポート</div>
            <nav className='flex flex-col gap-2 lg:gap-6'>
              <Link href='/support'>お問い合わせ</Link>
              <Link href='/faq'>よくある質問</Link>
            </nav>
          </div>
          <div className='flex flex-col gap-2 lg:gap-6'>
            <div className='font-semibold text-neutral-100'>SNS</div>
            <nav className='flex flex-col gap-2 lg:gap-6'>
              <Link href='#'>
                <span className='flex items-center gap-2'>
                  <IoLogoTwitter size={22} /> <span>Twitter</span>
                </span>
              </Link>
              <Link href='#'>
                <span className='flex items-center gap-2'>
                  <IoLogoFacebook size={22} /> <span>Facebook</span>
                </span>
              </Link>
              <Link href='#'>
                <span className='flex items-center gap-2'>
                  <IoLogoInstagram size={22} /> <span>Instagram</span>
                </span>
              </Link>
            </nav>
          </div>
        </div>
      </div>
      <div className='border-t border-zinc-800 py-6 text-center'>
        <span className='text-neutral4 text-xs'>
          Copyright {new Date().getFullYear()} © SEO記事くん
        </span>
      </div>
    </footer>
  );
}