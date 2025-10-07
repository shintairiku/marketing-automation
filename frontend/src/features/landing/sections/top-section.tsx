import Image from 'next/image';
import Link from 'next/link';

import { CloudShape } from '@/features/landing/components/background/cloud-shape';
import { CloudShapeThree } from '@/features/landing/components/background/cloud-shape-three';
import { CloudShapeTwo } from '@/features/landing/components/background/cloud-shape-two';
import { GridBackground } from '@/features/landing/components/background/grid-background';

export function TopSection() {
  return (
    <section
      className='relative min-h-screen overflow-hidden bg-cover bg-center bg-no-repeat py-24 sm:py-28 lg:py-32'
      style={{
        backgroundImage: "url('/lp/bg-pattern-1.png')",
      }}
    >
      <GridBackground />

      <CloudShape variant='light' className='right-10 top-0 opacity-30' />
      <CloudShapeTwo variant='orange' className='left-20 top-1/4 opacity-40' />
      <CloudShapeThree variant='beige' className='right-1/3 bottom-10 opacity-50' />
      <CloudShape variant='beige' className='left-10 bottom-0 opacity-25' />
      <CloudShapeTwo variant='green' className='right-5 top-1/3 max-w-[60vw] opacity-35' />
      <CloudShapeThree variant='dark' className='left-1/3 bottom-1/4 max-w-[55vw] opacity-40' />
      <CloudShape variant='orange' className='left-5 top-1/2 max-w-[52vw] opacity-20' />
      <CloudShapeTwo variant='beige' className='right-1/4 bottom-1/3 max-w-[58vw] opacity-45' />

      <div className='relative z-10 mx-auto max-w-7xl px-4 pb-20 pt-28 sm:px-6 sm:pt-32 lg:px-8 lg:pt-40'>
        <div className='grid grid-cols-1 items-center gap-12 xl:grid-cols-[minmax(0,1fr)_minmax(0,520px)] xl:gap-16'>
          <div className='space-y-8 text-center xl:text-left'>
            <Image
              src='/lp/seo-tiger.svg'
              alt='SEO Tiger by jungle AI'
              width={495}
              height={107}
              className='mx-auto h-auto w-full max-w-[22rem] sm:max-w-[26rem] lg:max-w-[28rem] xl:mx-0'
              priority
            />

            <div>
              <h1 className='mb-6 text-3xl font-bold leading-tight tracking-tight text-white sm:text-4xl lg:text-5xl'>
                高品質な
                <span className='font-sans uppercase'>SEO</span>
                記事を
                <br className='hidden sm:block' />
                わずか数分で自動生成
              </h1>
              <p className='mb-2 max-w-xl text-base leading-relaxed text-white opacity-90 sm:text-lg xl:mx-0 xl:text-left'>
                キーワードを入力するだけで、AIが検索上位表示を狙えるSEO最適化された記事を自動作成。
                <span className='hidden sm:inline'>チャットベースの編集機能で簡単カスタマイズ。</span>
              </p>
            </div>

            <div className='flex flex-col gap-4 sm:flex-row sm:justify-center xl:justify-start'>
              <Link
                href='/sign-up'
                className='w-full rounded-lg bg-primary-green px-8 py-3 text-center font-semibold text-white transition-colors hover:bg-primary-green/90 sm:w-auto'
              >
                無料で始める
              </Link>
              <Link
                href='/pricing'
                className='w-full rounded-lg border-2 border-white px-8 py-3 text-center font-semibold text-white transition-colors hover:bg-white hover:text-primary-dark sm:w-auto'
              >
                料金プランを見る
              </Link>
            </div>
          </div>

          <div className='flex justify-center xl:justify-end'>
            <div className='relative w-full max-w-[520px] sm:max-w-[640px] lg:max-w-[720px] xl:max-w-none'>
              <Image
                src='/lp/imgi_9_mba15-skyblue-select-202503.png'
                alt='MacBook showing SEO Tiger interface'
                width={900}
                height={640}
                className='h-auto w-full drop-shadow-[0_25px_45px_rgba(0,0,0,0.25)]'
                priority
              />
            </div>
          </div>
        </div>

        <div className='absolute inset-x-0 -bottom-10 flex justify-center sm:-bottom-12'>
          <div className='flex flex-col items-center space-y-2 text-white/80'>
            <span className='text-xs tracking-[0.3em]'>SCROLL</span>
            <div className='h-8 w-px bg-white/40 animate-pulse sm:h-10' />
            <svg className='h-5 w-5 animate-bounce sm:h-6 sm:w-6' fill='none' stroke='currentColor' viewBox='0 0 24 24'>
              <path strokeLinecap='round' strokeLinejoin='round' strokeWidth={2} d='M19 14l-7 7m0 0l-7-7m7 7V3' />
            </svg>
          </div>
        </div>
      </div>
    </section>
  );
}
