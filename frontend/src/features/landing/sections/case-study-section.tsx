import Link from 'next/link';

import { FadeInUp } from '@/features/landing/components/animations/fade-in-up';
import { RevealText } from '@/features/landing/components/animations/reveal-text';
import { StaggerChildren, StaggerItem } from '@/features/landing/components/animations/stagger-children';
import { CloudShape } from '@/features/landing/components/background/cloud-shape';
import { CloudShapeThree } from '@/features/landing/components/background/cloud-shape-three';
import { CloudShapeTwo } from '@/features/landing/components/background/cloud-shape-two';
import { GridBackground } from '@/features/landing/components/background/grid-background';

const caseStudies = [
  {
    title: '不動産会社A社',
    result: '運用開始から約半年間で10件のモデル来場予約を獲得',
    industry: '不動産業界',
    challenges: ['チラシやDMを配布しているが効果が薄い', '資料請求はあるが来場まで繋がらない', '担当者が忙しくて新たな施策が打てない'],
    improvements: [
      'HPの平均セッション数/月が200％以上UP',
      'ブログから資料請求/来場予約の導線を確保',
      '自社で最小工数でブログ運用可能に',
    ],
  },
  {
    title: 'ECサイト運営B社',
    result: 'SEO記事経由での売上が3ヶ月で150%向上',
    industry: 'Eコマース',
    challenges: ['広告費が高騰しROASが悪化', 'オーガニック検索での流入が少ない', '記事作成に多くの時間とコストがかかる'],
    improvements: [
      'オーガニック検索流入が月間300%増加',
      '商品関連キーワードでの上位表示を多数達成',
      '記事作成時間を90%短縮、品質は向上',
    ],
  },
  {
    title: 'IT企業C社',
    result: 'リード獲得数が6ヶ月で250%増加し受注単価も向上',
    industry: 'IT・SaaS',
    challenges: ['技術的な内容の記事作成が困難', '競合他社との差別化ができていない', '見込み客へのリーチが限定的'],
    improvements: [
      '専門性の高い記事で業界での認知度向上',
      '問い合わせ質の向上と商談化率アップ',
      '検索上位表示により継続的な集客を実現',
    ],
  },
];

export function CaseStudySection() {
  return (
    <section className='relative overflow-hidden bg-primary-beige py-24 sm:py-28 lg:py-32'>
      <GridBackground />

      <CloudShape variant='light' className='left-16 top-10 opacity-35' />
      <CloudShapeTwo variant='green' className='right-0 top-1/3 opacity-45' />
      <CloudShapeThree variant='beige' className='left-1/4 bottom-20 opacity-30' />
      <CloudShape variant='orange' className='right-20 bottom-0 opacity-25' />
      <CloudShapeTwo variant='beige' className='left-0 top-2/3 opacity-20' />
      <CloudShapeThree variant='orange' className='left-1/2 top-1/2 opacity-35' />
      <CloudShape variant='light' className='right-1/3 top-5 opacity-40' />
      <CloudShapeTwo variant='orange' className='right-10 bottom-1/3 opacity-30' />

      <div className='relative z-10 mx-auto max-w-6xl px-4 sm:px-6 lg:px-8'>
        <div className='mb-16 text-center sm:mb-20'>
          <RevealText
            text='導入事例'
            className='mb-4 text-3xl font-bold text-primary-dark sm:text-4xl lg:text-5xl'
            delay={0.2}
          />
          <div className='mx-auto mb-8 h-1 w-16 bg-primary-orange' />
          <FadeInUp delay={0.6}>
            <p className='mx-auto max-w-3xl text-base leading-relaxed text-gray-600 sm:text-lg'>
              様々な業界のお客様にSEO Tigerをご活用いただき、
              <span className='hidden sm:inline'>
                <br />
                確かな成果を上げています
              </span>
            </p>
          </FadeInUp>
        </div>

        <div className='grid grid-cols-1 gap-8 md:grid-cols-2 xl:grid-cols-3 lg:gap-10'>
          {caseStudies.map((study, index) => (
            <StaggerChildren key={study.title} delay={0.8 + index * 0.2} className='h-full'>
              <StaggerItem direction='up' className='h-full'>
                <div className='flex h-full flex-col overflow-hidden rounded-2xl bg-white/90 backdrop-blur shadow-lg'>
                  <div className='flex h-40 items-center justify-center bg-gray-100 sm:h-44'>
                    <div className='text-center text-gray-500'>
                      <div className='mb-2 text-3xl'>🏢</div>
                      <div className='text-xs sm:text-sm'>企業イメージ</div>
                    </div>
                  </div>

                  <div className='flex flex-grow flex-col p-6'>
                    <div className='mb-6'>
                      <span className='mb-3 inline-block rounded-full bg-primary-green/10 px-3 py-1 text-xs font-medium text-primary-green'>
                        {study.industry}
                      </span>
                      <h3 className='text-lg font-bold leading-snug text-primary-dark sm:text-xl'>{study.title}</h3>
                    </div>

                    <div className='mb-6 rounded-lg bg-primary-green/5 p-4'>
                      <div className='mb-2 text-xs font-semibold uppercase tracking-wide text-primary-green sm:text-sm'>導入成果</div>
                      <div className='text-sm font-bold leading-tight text-primary-dark sm:text-base'>{study.result}</div>
                    </div>

                    <div className='flex-grow space-y-6'>
                      <div>
                        <div className='mb-4 flex items-center'>
                          <div className='mr-3 flex h-6 w-6 items-center justify-center rounded-full bg-red-100'>
                            <div className='h-2.5 w-2.5 rounded-full bg-red-500 animate-pulse' />
                          </div>
                          <h4 className='text-sm font-bold text-primary-dark sm:text-base'>課題</h4>
                        </div>
                        <ul className='ml-9 space-y-3 text-sm leading-relaxed text-gray-700'>
                          {study.challenges.slice(0, 2).map((challenge) => (
                            <li key={challenge}>{challenge}</li>
                          ))}
                        </ul>
                      </div>

                      <div>
                        <div className='mb-4 flex items-center'>
                          <div className='mr-3 flex h-6 w-6 items-center justify-center rounded-full bg-green-100'>
                            <div className='h-2.5 w-2.5 rounded-full bg-green-500 animate-pulse' />
                          </div>
                          <h4 className='text-sm font-bold text-primary-dark sm:text-base'>改善</h4>
                        </div>
                        <ul className='ml-9 space-y-3 text-sm leading-relaxed text-gray-700'>
                          {study.improvements.slice(0, 2).map((improvement) => (
                            <li key={improvement}>{improvement}</li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  </div>
                </div>
              </StaggerItem>
            </StaggerChildren>
          ))}
        </div>

        <FadeInUp delay={1.8} className='mt-14 text-center sm:mt-16'>
          <Link
            href='/sign-up'
            className='inline-block rounded-lg bg-primary-green px-10 py-3.5 text-base font-semibold text-white shadow-lg transition-colors hover:bg-primary-green/90 sm:px-12 sm:py-4 sm:text-lg'
          >
            無料で始める
          </Link>
        </FadeInUp>
      </div>
    </section>
  );
}
