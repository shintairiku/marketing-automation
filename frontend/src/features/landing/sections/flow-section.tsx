import Link from 'next/link';

import { CloudShape } from '@/features/landing/components/background/cloud-shape';
import { CloudShapeThree } from '@/features/landing/components/background/cloud-shape-three';
import { CloudShapeTwo } from '@/features/landing/components/background/cloud-shape-two';
import { GridBackground } from '@/features/landing/components/background/grid-background';

const flowSteps = [
  {
    step: '01',
    title: '無料ではじめる',
    description: 'まずは無料ではじめるをクリック。簡単な登録で、すぐにSEO Tigerの機能をお試しいただけます。',
  },
  {
    step: '02',
    title: 'ログイン情報の設定',
    description: 'ログインID・パスワードを設定。安全で使いやすいアカウントを作成し、パーソナライズされた体験を開始します。',
  },
  {
    step: '03',
    title: '記事を生成する',
    description:
      '新規記事作成をクリックし、狙いたいキーワードで記事生成をしてみましょう。AIが自動でSEOに最適化された高品質な記事を作成します。',
  },
];

export function FlowSection() {
  return (
    <section className='relative overflow-hidden bg-primary-beige py-24 sm:py-28 lg:py-32'>
      <GridBackground />

      <CloudShape variant='orange' className='right-10 top-0 opacity-30' />
      <CloudShapeTwo variant='beige' className='left-0 top-1/2 opacity-40' />
      <CloudShapeThree variant='dark' className='right-1/3 bottom-0 opacity-25' />
      <CloudShape variant='orange' className='right-20 top-1/3 opacity-35' />
      <CloudShapeTwo variant='green' className='left-10 bottom-1/3 opacity-50' />
      <CloudShapeThree variant='orange' className='left-1/2 top-3/4 opacity-30' />
      <CloudShape variant='beige' className='right-0 bottom-10 opacity-40' />
      <CloudShapeTwo variant='orange' className='left-1/4 top-10 opacity-25' />

      <div className='mx-auto max-w-6xl px-4 sm:px-6 lg:px-8'>
        <div className='mb-16 text-center sm:mb-20'>
          <h2 className='mb-6 text-3xl font-bold text-primary-dark sm:text-4xl lg:text-5xl'>ご利用の流れ</h2>
          <p className='mx-auto max-w-2xl text-base leading-relaxed text-gray-600 sm:text-lg'>
            わずか3ステップで高品質なSEO記事が完成
          </p>
        </div>

        <div className='grid grid-cols-1 gap-10 md:grid-cols-3 lg:gap-12'>
          {flowSteps.map((step) => (
            <div key={step.step} className='relative'>
              <div className='mb-6 text-left sm:mb-8'>
                <div className='text-xs font-bold uppercase tracking-[0.3em] text-primary-green sm:text-sm sm:tracking-wider'>
                  Step
                </div>
                <div className='text-4xl font-bold leading-none text-primary-green sm:text-5xl'>{step.step}</div>
                <div className='mt-2 h-1 w-12 bg-primary-orange' />
              </div>

              <div className='mb-8 flex h-56 items-center justify-center rounded-2xl border-2 border-dashed border-gray-200 bg-white/70 backdrop-blur sm:h-64'>
                <div className='text-center text-gray-500'>
                  <div className='mb-2 text-3xl sm:text-4xl'>🎯</div>
                  <div className='text-xs sm:text-sm'>イメージ</div>
                </div>
              </div>

              <h3 className='mb-3 text-center text-xl font-bold leading-snug text-primary-green sm:mb-4 sm:text-2xl'>
                {step.title}
              </h3>
              <p className='text-center text-sm leading-relaxed text-gray-700 sm:text-base'>{step.description}</p>
            </div>
          ))}
        </div>

        <div className='mt-14 text-center sm:mt-16'>
          <Link
            href='/sign-up'
            className='inline-block rounded-lg bg-primary-green px-10 py-3.5 text-base font-semibold text-white shadow-lg transition-colors hover:bg-primary-green/90 sm:px-12 sm:py-4 sm:text-lg'
          >
            無料で始める
          </Link>
        </div>
      </div>
    </section>
  );
}
