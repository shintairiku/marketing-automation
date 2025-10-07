import Image from 'next/image';

import { CloudShape } from '@/features/landing/components/background/cloud-shape';
import { CloudShapeThree } from '@/features/landing/components/background/cloud-shape-three';
import { CloudShapeTwo } from '@/features/landing/components/background/cloud-shape-two';
import { GridBackground } from '@/features/landing/components/background/grid-background';

const problems = [
  {
    title: 'SEOに強い記事の書き方がわからない',
    subtitle: '検索しても上位に表示されない',
    description: '記事を書いてみたものの、上位表示されない。どうやったら上位表示できるかもあまりわからない。',
    image: '/lp/problem-1.svg',
  },
  {
    title: '分析・改善ができない',
    subtitle: '効果測定の方法がわからない',
    description: 'どこが原因で何を改善すればアクセスが増えるのかわからない。データはあっても活用方法が不明。',
    image: '/lp/problem-2.svg',
  },
  {
    title: '記事を書く時間も人手も足りない',
    subtitle: 'リソース不足で継続が困難',
    description: '担当者不在で現場仕事も忙しく、必要とわかっていても書く時間もない。',
    image: '/lp/problem-3.svg',
  },
];

export function ProblemSection() {
  return (
    <section className='relative overflow-hidden bg-primary-beige py-24 sm:py-28 lg:py-32'>
      <GridBackground />

      <CloudShape variant='beige' className='right-0 top-16 opacity-20' />
      <CloudShapeTwo variant='green' className='left-0 top-1/3 opacity-35' />
      <CloudShapeThree variant='orange' className='right-1/4 bottom-20 opacity-45' />
      <CloudShape variant='light' className='left-1/4 top-5 opacity-30' />
      <CloudShapeTwo variant='orange' className='left-20 bottom-1/3 opacity-25' />
      <CloudShapeThree variant='dark' className='right-10 top-1/2 opacity-35' />
      <CloudShape variant='orange' className='right-1/2 bottom-5 opacity-20' />
      <CloudShapeTwo variant='beige' className='left-5 top-2/3 opacity-45' />

      <div className='mx-auto max-w-6xl px-4 sm:px-6 lg:px-8'>
        <div className='mb-16 text-center sm:mb-20'>
          <p className='mb-4 text-xs uppercase tracking-wide text-gray-600 sm:text-sm'>集客力UPが課題の社長様・ご担当者様へ</p>
          <h2 className='text-3xl font-bold leading-tight text-primary-dark sm:text-4xl lg:text-5xl'>
            SEO対策でホームページへの流入を増やしたいけれど・・・
          </h2>
        </div>

        <div className='grid grid-cols-1 gap-10 md:grid-cols-2 xl:grid-cols-3 xl:gap-12'>
          {problems.map((problem) => (
            <div
              key={problem.title}
              className='rounded-2xl bg-white/80 px-6 py-10 text-center shadow-sm backdrop-blur transition-shadow hover:shadow-lg'
            >
              <div className='mb-6 flex h-36 items-center justify-center sm:h-40'>
                <Image
                  src={problem.image}
                  alt={problem.title}
                  width={200}
                  height={150}
                  className='h-auto max-h-full w-auto'
                />
              </div>
              <h3 className='mb-3 text-lg font-bold leading-snug text-primary-dark sm:text-xl'>{problem.title}</h3>
              <p className='mb-3 text-xs text-gray-600 sm:text-sm'>{problem.subtitle}</p>
              <p className='text-sm leading-relaxed text-gray-600'>{problem.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
