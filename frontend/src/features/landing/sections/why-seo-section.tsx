import Image from 'next/image';

import { CloudShape } from '@/features/landing/components/background/cloud-shape';
import { CloudShapeThree } from '@/features/landing/components/background/cloud-shape-three';
import { CloudShapeTwo } from '@/features/landing/components/background/cloud-shape-two';
import { GridBackground } from '@/features/landing/components/background/grid-background';

export function WhySeoSection() {
  return (
    <section className='relative overflow-hidden bg-primary-beige py-24 sm:py-28 lg:py-32'>
      <GridBackground />

      <CloudShape variant='beige' className='left-0 top-10 opacity-25' />
      <CloudShapeTwo variant='orange' className='right-10 top-1/4 opacity-35' />
      <CloudShapeThree variant='dark' className='left-1/4 top-2/3 opacity-20' />
      <CloudShape variant='light' className='right-0 bottom-40 opacity-45' />
      <CloudShapeTwo variant='green' className='left-10 top-1/2 opacity-30' />
      <CloudShapeThree variant='light' className='left-1/3 bottom-20 opacity-35' />
      <CloudShape variant='orange' className='right-1/3 top-5 opacity-25' />
      <CloudShapeTwo variant='beige' className='right-20 bottom-1/2 opacity-40' />

      <div className='mx-auto max-w-6xl px-4 sm:px-6 lg:px-8'>
        <div className='mb-16 text-center sm:mb-20'>
          <h2 className='mb-4 text-3xl font-bold text-primary-dark sm:text-4xl lg:text-5xl'>なぜ今SEOが重要なのか</h2>
          <div className='mx-auto h-1 w-24 bg-primary-orange' />
        </div>

        <div className='mb-24 grid grid-cols-1 items-center gap-12 lg:grid-cols-2 lg:gap-16'>
          <div>
            <h3 className='mb-4 text-2xl font-bold text-primary-dark sm:text-3xl'>そもそもSEOとは？</h3>
            <div className='space-y-4 text-base leading-relaxed text-gray-700 sm:text-lg'>
              <p>
                SEOとは「Search Engine Optimization（検索エンジン最適化）」の略称です。これは、GoogleやYahoo!といった検索エンジンの検索結果において、自社のWebサイトやコンテンツを上位に表示させるための施策全般を指します。
              </p>
              <p>
                今日のビジネス環境において、顧客は何かを検討する際にまず検索エンジンを利用します。この初期段階でのタッチポイントを最大化することが、SEO目的です。
              </p>
            </div>
          </div>
          <div className='order-first lg:order-last'>
            <Image
              src='https://images.unsplash.com/photo-1460925895917-afdab827c52f?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80'
              alt='SEO Analytics Dashboard'
              width={600}
              height={400}
              className='shadow-lg'
            />
          </div>
        </div>

        <div className='mb-20 sm:mb-24'>
          <h3 className='mb-12 text-center text-3xl font-bold text-primary-dark sm:text-4xl'>SEOが重要な4つの理由</h3>
          <div className='grid grid-cols-1 gap-6 lg:gap-8 sm:grid-cols-2 xl:grid-cols-4'>
            {[
              {
                title: '圧倒的な集客力と\n認知度向上',
                description:
                  '検索エンジンの検索結果で上位に表示されることで、ターゲット顧客の目に触れる機会が格段に増加します。これは、実店舗が「一等地の路面店」に位置するのと同義であり、効果的なオンライン上での見込み客の創出に直結します。',
                image:
                  'https://images.unsplash.com/photo-1460925895917-afdab827c52f?ixlib=rb-4.0.3&auto=format&fit=crop&w=400&q=80',
                imageAlt: 'マーケティング分析の画面',
                accentClass: 'bg-primary-orange',
              },
              {
                title: '高い費用対効果\n（ROI）',
                description:
                  'リスティング広告のような有料広告とは異なり、SEOは基本的に広告費がかかりません。一度上位表示されれば、持続的に自然検索からのアクセスを獲得できるため、長期的に見て非常に高い投資対効果（ROI）を実現します。',
                image:
                  'https://images.unsplash.com/photo-1554224155-6726b3ff858f?ixlib=rb-4.0.3&auto=format&fit=crop&w=400&q=80',
                imageAlt: '積み上がるコインとグラフ',
                accentClass: 'bg-primary-green',
              },
              {
                title: 'ブランドの\n信頼性構築',
                description:
                  '検索エンジンの上位に表示されることは、Googleなどの検索エンジンがその情報を「信頼できる、質の高い情報源」と評価していることを意味します。これにより、ユーザーからのブランド信頼度や権威性が向上します。',
                image:
                  'https://images.unsplash.com/photo-1556742049-0cfed4f6a45d?ixlib=rb-4.0.3&auto=format&fit=crop&w=400&q=80',
                imageAlt: 'チームで戦略を練る様子',
                accentClass: 'bg-primary-dark',
              },
              {
                title: '質の高い\nリード獲得',
                description:
                  '検索行動は、ユーザーが特定の課題やニーズを抱えている状態で行われます。そのため、SEOによって獲得する訪問者は、すでに解決策を検討している「見込み度の高いリード」である可能性が高く、効率的なコンバージョンに繋がりやすいというメリットがあります。',
                image:
                  'https://images.unsplash.com/photo-1551288049-bebda4e38f71?ixlib=rb-4.0.3&auto=format&fit=crop&w=400&q=80',
                imageAlt: '握手するビジネスパーソン',
                accentClass: 'bg-blue-500',
              },
            ].map(({ title, description, image, imageAlt, accentClass }, index) => (
              <div
                key={index}
                className='group overflow-hidden bg-white/80 shadow-lg transition-all duration-300 hover:shadow-xl'
              >
                <div className='relative flex h-48 items-center justify-center bg-gradient-to-br'>
                  <div className='absolute inset-0 opacity-80'>
                    <Image
                      src={image}
                      alt={imageAlt}
                      fill
                      sizes='(max-width: 768px) 100vw, 25vw'
                      className='object-cover'
                    />
                  </div>
                  <div className='relative hidden text-3xl sm:block'>📈</div>
                </div>
                <div className='p-6'>
                  <div className={`mb-4 h-0.5 w-8 ${accentClass}`} />
                  <h4 className='mb-3 text-lg font-bold leading-tight text-primary-dark whitespace-pre-line'>{title}</h4>
                  <p className='text-sm leading-relaxed text-gray-600'>{description}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className='relative overflow-hidden py-28 sm:py-32'>
        <div className='absolute bottom-0 left-0 top-0 w-1/2 opacity-30'>
          <div className='relative h-full w-full'>
            <Image
              src='https://images.unsplash.com/photo-1677442136019-21780ecad995?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80'
              alt='AI Technology'
              fill
              sizes='(max-width: 1024px) 50vw, 600px'
              className='object-cover'
            />
          </div>
        </div>

        <div className='relative z-10 mx-auto max-w-6xl px-4 sm:px-6 lg:px-8'>
          <div className='ml-auto mr-0 max-w-3xl text-left lg:mr-8 lg:max-w-4xl'>
            <h3 className='mb-12 text-3xl font-bold leading-tight text-primary-dark sm:text-4xl lg:text-5xl'>
              SEO対策は
              <br />
              AIO対策へと進化する
            </h3>

            <div className='space-y-6 text-base leading-relaxed text-gray-700 sm:text-lg'>
              <p>
                これまでのSEO対策は、Google検索での上位表示を目指すものでした。もちろん今後も重要な施策ですが、生成AIの登場により、最近の視点が「AIO（AI Optimization）」へと広がっていきます。
              </p>
              <div className='relative'>
                <div className='absolute bottom-0 left-0 top-0 w-1 bg-primary-orange' />
                <p className='pl-6 text-sm font-semibold text-primary-dark sm:pl-8 sm:text-base'>
                  重要なのは、キーワードを詰め込むことではなく、AIが理解しやすい構造、信頼性・専門性のある中身を備えること。本質的な価値のある情報発信を発信し続けることが、あらゆるチャネルでの成果につながるのです。
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
