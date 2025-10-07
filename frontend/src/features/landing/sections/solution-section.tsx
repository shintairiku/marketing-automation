import Image from 'next/image';

import { CloudShape } from '@/features/landing/components/background/cloud-shape';
import { CloudShapeThree } from '@/features/landing/components/background/cloud-shape-three';
import { CloudShapeTwo } from '@/features/landing/components/background/cloud-shape-two';
import { GridBackground } from '@/features/landing/components/background/grid-background';

export function SolutionSection() {
  return (
    <section className='relative overflow-hidden bg-primary-beige py-24 sm:py-28 lg:py-32'>
      <GridBackground />

      <CloudShape variant='orange' className='left-16 top-20 opacity-25' />
      <CloudShapeTwo variant='beige' className='right-0 top-1/2 opacity-40' />
      <CloudShapeThree variant='dark' className='left-1/3 bottom-10 opacity-35' />
      <CloudShape variant='light' className='right-20 bottom-32 opacity-30' />
      <CloudShapeTwo variant='green' className='right-5 top-5 opacity-25' />
      <CloudShapeThree variant='light' className='left-10 bottom-1/2 opacity-40' />
      <CloudShape variant='beige' className='right-1/3 top-3/4 opacity-35' />
      <CloudShapeTwo variant='orange' className='left-1/2 bottom-5 opacity-20' />

      <div className='mx-auto max-w-6xl px-4 sm:px-6 lg:px-8'>
        <div className='mb-16 text-center sm:mb-20'>
          <h2 className='mb-6 text-3xl font-bold text-primary-dark sm:text-4xl lg:text-5xl'>SEO Tigerなら、全て解決</h2>
          <p className='mx-auto max-w-3xl text-base leading-relaxed text-gray-600 sm:text-lg'>
            SEOに特化した高品質な記事をAIが自動生成。コンテンツ作成の業務効率を改善し、集客できるWebページの作成をサポートします。
          </p>
        </div>

        <div className='grid grid-cols-1 items-center gap-12 lg:grid-cols-2 lg:gap-16'>
          <div className='relative'>
            <div className='absolute -inset-4 -z-10 rounded-3xl border border-primary-green/20 sm:-inset-6' />
            <Image
              src='https://images.unsplash.com/photo-1551434678-e076c223a692?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80'
              alt='AI Content Generation'
              width={600}
              height={400}
              sizes='(max-width: 1024px) 100vw, 540px'
              className='h-auto w-full rounded-3xl shadow-xl'
            />
          </div>

          <div className='space-y-8'>
            <div className='space-y-4'>
              <div className='h-0.5 w-12 bg-primary-orange' />
              <h3 className='text-2xl font-bold text-primary-dark sm:text-3xl'>主な特徴</h3>
            </div>
            <div className='space-y-4 text-base leading-relaxed text-gray-700 sm:text-lg'>
              <p>SEOに強い高品質な記事生成がほぼ自動で作成できる</p>
              <p>生成記事の検索順位の推移をチェック、PDCAが回せる</p>
              <p>記事画像も生成できる</p>
              <p>直感的に使いやすいUI/UX</p>
              <p>670社以上の中小企業のWebマーケティング支援実績</p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
