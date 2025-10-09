import Link from 'next/link';

import { CloudShape } from '@/features/landing/components/background/cloud-shape';
import { CloudShapeThree } from '@/features/landing/components/background/cloud-shape-three';
import { CloudShapeTwo } from '@/features/landing/components/background/cloud-shape-two';
import { GridBackground } from '@/features/landing/components/background/grid-background';

const pricingPlans = [
  {
    name: 'シンプルプラン',
    price: '¥4,980',
    period: '/月',
    description: '個人・小規模サイト向け',
    features: ['月5記事まで生成', '基本的なSEO最適化', 'メールサポート', '記事テンプレート利用'],
    ctaLabel: 'シンプルプランを始める',
    isPopular: false,
  },
  {
    name: 'スタンダードプラン',
    price: '¥9,800',
    period: '/月',
    description: '中小企業・ブログ運営者向け',
    features: ['月20記事まで生成', '高度なSEO最適化', '画像自動生成', 'チャットサポート', '分析レポート機能', 'カスタムテンプレート'],
    ctaLabel: 'スタンダードプランを始める',
    isPopular: true,
  },
  {
    name: 'プレミアムプラン',
    price: '¥19,800',
    period: '/月',
    description: '企業・代理店向け',
    features: ['月50記事まで生成', 'プレミアムSEO最適化', '高品質画像生成', '優先サポート', '詳細分析ダッシュボード', 'API連携', '専用アカウントマネージャー'],
    ctaLabel: 'プレミアムプランを始める',
    isPopular: false,
  },
];

export function PricingSection() {
  return (
    <section className='relative overflow-hidden bg-primary-beige py-24 sm:py-28 lg:py-32'>
      <GridBackground />

      <CloudShape variant='beige' className='left-0 top-0 opacity-20' />
      <CloudShapeTwo variant='orange' className='right-10 top-1/4 opacity-35' />
      <CloudShapeThree variant='dark' className='left-1/3 bottom-10 opacity-40' />
      <CloudShape variant='light' className='right-0 bottom-0 opacity-30' />
      <CloudShapeTwo variant='green' className='left-10 top-1/2 opacity-40' />
      <CloudShapeThree variant='light' className='right-20 bottom-1/3 opacity-25' />
      <CloudShape variant='orange' className='left-1/3 top-3/4 opacity-35' />
      <CloudShapeTwo variant='beige' className='left-5 bottom-10 opacity-50' />

      <div className='mx-auto max-w-6xl px-4 sm:px-6 lg:px-8'>
        <div className='mb-16 text-center sm:mb-20'>
          <h2 className='mb-6 text-3xl font-bold text-primary-dark sm:text-4xl lg:text-5xl'>料金プラン</h2>
          <div className='mx-auto mb-8 h-1 w-16 bg-primary-orange' />
          <p className='mx-auto max-w-3xl text-base leading-relaxed text-gray-600 sm:text-lg'>
            あなたのニーズに合わせた柔軟な料金体系をご用意しています。
            <span className='hidden sm:inline'>
              <br />
              全プラン30日間無料でお試しいただけます。
            </span>
          </p>
        </div>

        <div className='grid grid-cols-1 gap-8 md:grid-cols-2 xl:grid-cols-3 lg:gap-10'>
          {pricingPlans.map((plan) => (
            <div key={plan.name} className={`relative ${plan.isPopular ? 'transform lg:scale-105' : ''}`}>
              {plan.isPopular && (
                <div className='absolute -top-3 left-1/2 z-10 -translate-x-1/2'>
                  <div className='rounded-full bg-primary-orange px-4 py-1 text-xs font-bold text-white'>人気</div>
                </div>
              )}

              <div
                className={`flex h-full flex-col overflow-hidden rounded-2xl bg-white ${
                  plan.isPopular ? 'border-2 border-primary-green shadow-xl' : 'border border-gray-200 shadow-lg'
                }`}
              >
                <div className='p-8 text-center'>
                  <h3 className='mb-2 text-xl font-bold text-primary-dark sm:text-2xl'>{plan.name}</h3>
                  <p className='mb-6 text-sm text-gray-600'>{plan.description}</p>
                  <div className='mb-6'>
                    <span className={`text-4xl font-bold sm:text-5xl ${plan.isPopular ? 'text-primary-green' : 'text-primary-dark'}`}>
                      {plan.price}
                    </span>
                    <span className='ml-1 text-lg text-gray-600'>{plan.period}</span>
                  </div>
                </div>

                <div className='flex flex-grow flex-col p-8 pt-0'>
                  <ul className='mb-8 flex-grow space-y-3 text-sm leading-relaxed text-gray-700 sm:space-y-4'>
                    {plan.features.map((feature) => (
                      <li key={feature} className='flex items-start'>
                        <span
                          className={`mr-3 mt-0.5 flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full ${
                            plan.isPopular ? 'bg-primary-green' : 'bg-gray-400'
                          }`}
                        >
                          <svg className='h-3 w-3 text-white' fill='none' stroke='currentColor' viewBox='0 0 24 24'>
                            <path strokeLinecap='round' strokeLinejoin='round' strokeWidth={2} d='M5 13l4 4L19 7' />
                          </svg>
                        </span>
                        <span>{feature}</span>
                      </li>
                    ))}
                  </ul>

                  <Link
                    href='/sign-up'
                    className={`block rounded-lg px-6 py-3.5 text-center text-sm font-semibold transition-colors sm:py-4 sm:text-base ${
                      plan.isPopular
                        ? 'bg-primary-green text-white hover:bg-primary-green/90'
                        : 'border border-gray-300 bg-gray-100 text-primary-dark hover:bg-gray-200'
                    }`}
                  >
                    {plan.ctaLabel}
                  </Link>
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className='mt-14 text-center sm:mt-16'>
          <p className='mb-6 text-gray-600'>全プラン共通特典</p>
          <div className='flex flex-wrap justify-center gap-6 text-sm text-gray-700 sm:gap-8'>
            {['30日間無料トライアル', 'いつでもプラン変更可能', '解約手数料なし'].map((item) => (
              <div key={item} className='flex items-center'>
                <svg className='mr-2 h-5 w-5 text-primary-green' fill='none' stroke='currentColor' viewBox='0 0 24 24'>
                  <path strokeLinecap='round' strokeLinejoin='round' strokeWidth={2} d='M5 13l4 4L19 7' />
                </svg>
                {item}
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
