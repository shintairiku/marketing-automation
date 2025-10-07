'use client';

import { useState } from 'react';

import { CloudShape } from '@/features/landing/components/background/cloud-shape';
import { CloudShapeThree } from '@/features/landing/components/background/cloud-shape-three';
import { CloudShapeTwo } from '@/features/landing/components/background/cloud-shape-two';
import { GridBackground } from '@/features/landing/components/background/grid-background';

const faqs = [
  {
    question: 'SEO Tigerの料金プランはどのようになっていますか？',
    answer:
      'SEO Tigerは月額制のサービスで、スタンダードプラン（月額9,800円）とプレミアムプラン（月額19,800円）をご用意しています。スタンダードプランでは月20記事まで、プレミアムプランでは月50記事まで生成可能です。初回30日間は無料でお試しいただけます。',
  },
  {
    question: '生成される記事の品質はどの程度ですか？',
    answer:
      'SEO Tigerは最新のAI技術を使用し、SEOに最適化された高品質な記事を生成します。生成された記事は検索上位表示を狙える構造になっており、実際に多くのお客様が検索順位の向上を実現されています。ただし、生成後の校正・編集をお勧めしています。',
  },
  {
    question: 'どのような業界・ジャンルに対応していますか？',
    answer:
      'SEO TigerはBtoB、BtoC問わず幅広い業界に対応しています。IT、不動産、医療、教育、美容、飲食など様々な分野での記事生成が可能です。専門性の高い分野については、事前にキーワードや業界情報を詳しく設定していただくことで、より精度の高い記事を生成できます。',
  },
  {
    question: '記事生成にはどのくらい時間がかかりますか？',
    answer:
      '1記事あたりの生成時間は約2〜3分です。キーワードを入力してから、構成案の作成、本文の生成、画像の選定まで全自動で行われます。従来の手動での記事作成と比較して、約90%の時間短縮を実現できます。',
  },
  {
    question: '生成した記事の著作権はどうなりますか？',
    answer:
      'SEO Tigerで生成された記事の著作権は、お客様に帰属します。生成された記事は自由に編集・公開・商用利用していただけます。ただし、他社の商標権や著作権を侵害する内容が含まれる場合は、お客様の責任において修正をお願いします。',
  },
  {
    question: 'サポート体制について教えてください',
    answer:
      '専属のカスタマーサポートチームが、平日9:00〜18:00でお客様をサポートします。チャット、メール、電話でのお問い合わせに対応しており、操作方法から効果的な活用方法まで丁寧にご案内します。また、定期的にオンラインセミナーも開催しています。',
  },
];

export function FaqSection() {
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  return (
    <section className='relative overflow-hidden bg-primary-beige py-24 sm:py-28 lg:py-32'>
      <GridBackground />

      <CloudShape variant='light' className='right-0 top-0 opacity-25' />
      <CloudShapeTwo variant='beige' className='left-0 top-1/3 opacity-40' />
      <CloudShapeThree variant='orange' className='right-1/4 bottom-20 opacity-35' />
      <CloudShape variant='beige' className='left-1/3 bottom-0 opacity-20' />
      <CloudShapeTwo variant='green' className='right-1/3 top-1/4 opacity-25' />
      <CloudShapeThree variant='dark' className='left-10 bottom-1/2 opacity-40' />
      <CloudShape variant='orange' className='right-5 top-3/4 opacity-35' />

      <div className='mx-auto max-w-4xl px-4 sm:px-6 lg:px-8'>
        <div className='mb-12 text-center sm:mb-14'>
          <h2 className='text-3xl font-bold text-primary-dark sm:text-4xl'>よくあるご質問</h2>
        </div>

        <div className='space-y-2'>
          {faqs.map((faq, index) => {
            const isOpen = openIndex === index;
            return (
              <div key={faq.question} className='border-b border-gray-200 bg-white'>
                <button
                  type='button'
                  onClick={() => setOpenIndex(isOpen ? null : index)}
                  className='flex w-full items-center justify-between px-6 py-5 text-left transition-colors hover:bg-gray-50 sm:px-8 sm:py-6'
                >
                  <div className='flex items-start space-x-4'>
                    <span className='mt-1 flex-shrink-0 text-base font-bold text-primary-green sm:text-lg'>Q</span>
                    <span className='text-sm font-medium leading-relaxed text-primary-dark sm:text-base'>{faq.question}</span>
                  </div>
                  <svg
                    className={`h-5 w-5 flex-shrink-0 text-gray-400 transition-transform duration-200 ${
                      isOpen ? 'rotate-180' : ''
                    }`}
                    fill='none'
                    stroke='currentColor'
                    viewBox='0 0 24 24'
                  >
                    <path strokeLinecap='round' strokeLinejoin='round' strokeWidth={2} d='M19 9l-7 7-7-7' />
                  </svg>
                </button>

                {isOpen && (
                  <div className='px-6 pb-6 sm:px-8 sm:pb-8'>
                    <div className='flex items-start space-x-4 pt-2'>
                      <span className='flex-shrink-0 text-base font-bold text-primary-orange sm:text-lg'>A</span>
                      <p className='text-sm leading-relaxed text-gray-700 sm:text-base'>{faq.answer}</p>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
