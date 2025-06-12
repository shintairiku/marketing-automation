import Link from 'next/link';

import { Container } from '@/components/container';
import { Button } from '@/components/ui/button';
import { PricingSection } from '@/features/pricing/components/pricing-section';

export default async function HomePage() {
  return (
    <div className='flex flex-col gap-8 lg:gap-32'>
      <HeroSection />
      <FeaturesSection />
      <HowItWorksSection />
      <TestimonialsSection />
      <PricingSection />
      <FAQSection />
      <CTASection />
    </div>
  );
}

function HeroSection() {
  return (
    <section className='relative overflow-hidden lg:overflow-visible'>
      <Container className='relative rounded-lg bg-background py-20 lg:py-[140px]'>
        <div className='relative z-10 flex flex-col gap-5 lg:max-w-2xl lg:pl-8'>
          <div className='w-fit rounded-full bg-gradient-to-r from-[#616571] via-[#7782A9] to-[#826674] px-4 py-1 '>
            <span className='font-alt text-sm font-semibold text-black mix-blend-soft-light'>
              AI搭載SEO記事自動生成
            </span>
          </div>
          <h1>（仮）高品質なSEO記事を<br/>わずか数分で自動生成</h1>
          <p className='text-lg text-muted-foreground mb-2'>
            キーワードを入力するだけで、AIが検索上位表示を狙えるSEO最適化された記事を自動作成。
            チャットベースの編集機能で簡単カスタマイズ。
          </p>
          <div className='flex flex-col gap-4 sm:flex-row'>
            <Button asChild variant='sexy' size='lg'>
              <Link href='/signup'>無料ではじめる</Link>
            </Button>
            <Button asChild variant='outline' size='lg'>
              <Link href='/features'>機能詳細を見る</Link>
            </Button>
          </div>
        </div>
      </Container>
    </section>
  );
}

function FeaturesSection() {
  const features = [
    {
      title: 'SEO最適化された記事生成',
      description: 'キーワード分析、競合調査、最新トレンドを考慮したSEO記事を自動生成します。検索エンジンで上位表示を狙えるコンテンツを簡単に作成できます。',
      icon: '/icons/seo-icon.svg',
    },
    {
      title: 'AIチャット編集機能',
      description: '生成された記事をチャット形式で手軽に編集。「もっと簡潔に」「事例を追加して」などの指示だけで、AIが記事を最適化します。',
      icon: '/icons/chat-icon.svg',
    },
    {
      title: '豊富なエクスポート機能',
      description: '生成された記事はHTML、Markdown形式でエクスポート可能。WordPressなど様々なCMSにシームレスに取り込めます。',
      icon: '/icons/export-icon.svg',
    },
    {
      title: '高度なキーワード分析',
      description: '関連キーワード、検索ボリューム、競合性などを自動分析。SEOに効果的なコンテンツ構成を提案します。',
      icon: '/icons/keyword-icon.svg',
    },
    {
      title: '複数の文体とトーン',
      description: 'フォーマル、カジュアル、専門的など、目的に合わせた文体を選択可能。ターゲット読者に最適な表現で記事を生成します。',
      icon: '/icons/style-icon.svg',
    },
    {
      title: '定期的なアップデート',
      description: '最新のSEOトレンドやAIモデルの更新を常に反映。常に高品質な記事生成を維持します。',
      icon: '/icons/update-icon.svg',
    },
  ];

  return (
    <section className='py-16 lg:py-24'>
      <Container>
        <div className='text-center mb-16'>
          <h2 className='text-3xl font-bold mb-4'>すべての機能</h2>
          <p className='text-xl text-muted-foreground max-w-2xl mx-auto'>
            新大陸は、記事作成のプロセスを効率化し、高品質なコンテンツを簡単に生成できる機能を提供します。
          </p>
        </div>

        <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8'>
          {features.map((feature, index) => (
            <div key={index} className='bg-muted/50 rounded-lg p-6 border border-border transition-all hover:border-indigo-500/50 hover:bg-muted/80'>
              <div className='w-12 h-12 bg-indigo-600/20 rounded-md flex items-center justify-center mb-4'>
                <div className='w-6 h-6 text-indigo-500'>
                  {/* 実際のアイコンは、実装時に追加 */}
                  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                </div>
              </div>
              <h3 className='text-xl font-semibold mb-2'>{feature.title}</h3>
              <p className='text-muted-foreground'>{feature.description}</p>
            </div>
          ))}
        </div>
      </Container>
    </section>
  );
}

function HowItWorksSection() {
  const steps = [
    {
      number: '01',
      title: 'キーワードと主題を入力',
      description: 'ターゲットキーワードと記事の主題を入力するだけ。オプションで記事の文体やターゲット読者層も設定できます。',
    },
    {
      number: '02',
      title: 'AIが記事構成を提案',
      description: 'AIがSEO分析を行い、効果的な記事構成を複数提案。お好みの構成を選んだり、編集したりできます。',
    },
    {
      number: '03',
      title: '記事本文を自動生成',
      description: '選んだ構成に基づき、AIが高品質な記事本文を生成。SEO最適化されたコンテンツがすぐに完成します。',
    },
    {
      number: '04',
      title: 'チャットで記事を編集',
      description: '生成された記事をチャット形式で簡単に編集。自然な指示だけで記事を最適化できます。',
    },
  ];

  return (
    <section className='py-16 lg:py-24 bg-muted/30'>
      <Container>
        <div className='text-center mb-16'>
          <h2 className='text-3xl font-bold mb-4'>使い方</h2>
          <p className='text-xl text-muted-foreground max-w-2xl mx-auto'>
            4つの簡単なステップで、SEO最適化された高品質な記事を数分で作成できます。
          </p>
        </div>

        <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8'>
          {steps.map((step, index) => (
            <div key={index} className='relative'>
              <div className='mb-4 text-4xl font-bold text-indigo-500/40'>{step.number}</div>
              <h3 className='text-xl font-semibold mb-2'>{step.title}</h3>
              <p className='text-muted-foreground'>{step.description}</p>
              
              {index < steps.length - 1 && (
                <div className='hidden lg:block absolute top-8 right-0 w-[calc(100%-50px)] h-[2px] bg-gradient-to-r from-indigo-500/50 to-transparent'></div>
              )}
            </div>
          ))}
        </div>
      </Container>
    </section>
  );
}

function TestimonialsSection() {
  const testimonials = [
    {
      quote: "新大陸を導入してから、記事作成の効率が格段に上がりました。以前は1記事に4-5時間かかっていましたが、今は30分程度で高品質な記事を作成できています。",
      author: "田中 誠",
      position: "マーケティングディレクター",
      company: "テックスタートアップ株式会社",
    },
    {
      quote: "チャット編集機能が特に便利です。生成された記事に対して「もっと具体例を加えて」と指示するだけで、自然な形で内容が充実します。記事作成の負担が大幅に減りました。",
      author: "佐藤 美咲",
      position: "コンテンツマネージャー",
      company: "デジタルマーケティング企業",
    },
    {
      quote: "専門知識がなくても高品質なSEO記事が作れるのが革新的です。弊社のブログのオーガニックトラフィックが3ヶ月で40%増加しました。",
      author: "鈴木 健太",
      position: "中小企業オーナー",
      company: "健康食品販売会社",
    },
  ];

  return (
    <section className='py-16 lg:py-24'>
      <Container>
        <div className='text-center mb-16'>
          <h2 className='text-3xl font-bold mb-4'>お客様の声</h2>
          <p className='text-xl text-muted-foreground max-w-2xl mx-auto'>
            多くの企業や個人の方々に新大陸をご利用いただいています。
          </p>
        </div>

        <div className='grid grid-cols-1 md:grid-cols-3 gap-8'>
          {testimonials.map((testimonial, index) => (
            <div key={index} className='bg-muted/50 rounded-lg p-6 border border-border'>
              <div className='mb-4 text-3xl text-indigo-500'>&quot;</div>
              <p className='mb-6 text-muted-foreground'>{testimonial.quote}</p>
              <div>
                <p className='font-semibold'>{testimonial.author}</p>
                <p className='text-sm text-muted-foreground'>{testimonial.position}, {testimonial.company}</p>
              </div>
            </div>
          ))}
        </div>
      </Container>
    </section>
  );
}

function FAQSection() {
  const faqs = [
    {
      question: "AI生成記事はSEOに効果がありますか？",
      answer: "はい、新大陸が生成する記事は最新のSEOベストプラクティスに基づいて最適化されています。キーワード分析、競合分析、検索意図の理解を踏まえた記事構成と内容を提案するため、効果的なSEO記事作成を支援します。",
    },
    {
      question: "どのような文体や形式で記事を生成できますか？",
      answer: "フォーマル（丁寧語）、カジュアル、プロフェッショナル（専門的）、フレンドリーなど、様々な文体から選択可能です。また、ブログ記事、ハウツーガイド、リスト記事など多様な形式に対応しています。",
    },
    {
      question: "生成された記事の修正や編集はできますか？",
      answer: "はい、チャットベースの編集機能を使って簡単に記事を修正できます。「このセクションをもっと詳しく」「事例を追加して」など、自然な指示で記事を編集できます。また、HTMLやMarkdown形式でエクスポートして外部ツールで編集することも可能です。",
    },
    {
      question: "利用制限はありますか？",
      answer: "各プランによって月間生成可能な記事数が異なります。詳細は料金プランをご確認ください。記事の長さや編集回数に制限はありません。",
    },
    {
      question: "どのようなジャンルの記事に対応していますか？",
      answer: "ビジネス、マーケティング、テクノロジー、健康、ライフスタイルなど、幅広いジャンルに対応しています。専門的な用語や情報が必要な場合は、参考URLを入力することで、より正確な記事生成が可能です。",
    },
    {
      question: "独自のブランドトーンを反映することはできますか？",
      answer: "はい。企業情報や好みの表現スタイルをフォームに入力することで、ブランドの雰囲気に合った記事が生成できます。また、チャット編集機能を使って細かい調整も可能です。",
    },
  ];

  return (
    <section className='py-16 lg:py-24 bg-muted/30'>
      <Container>
        <div className='text-center mb-16'>
          <h2 className='text-3xl font-bold mb-4'>よくある質問</h2>
          <p className='text-xl text-muted-foreground max-w-2xl mx-auto'>
            新大陸についてよくいただく質問にお答えします。
          </p>
        </div>

        <div className='grid grid-cols-1 md:grid-cols-2 gap-8 max-w-5xl mx-auto'>
          {faqs.map((faq, index) => (
            <div key={index} className='rounded-lg p-6 border border-border'>
              <h3 className='text-lg font-semibold mb-2'>{faq.question}</h3>
              <p className='text-muted-foreground'>{faq.answer}</p>
            </div>
          ))}
        </div>
      </Container>
    </section>
  );
}

function CTASection() {
  return (
    <section className='py-16 lg:py-24'>
      <Container>
        <div className='rounded-lg bg-indigo-600/20 p-12 border border-indigo-500/30 text-center max-w-4xl mx-auto'>
          <h2 className='text-3xl font-bold mb-4'>今すぐ新大陸を試してみませんか？</h2>
          <p className='text-xl text-muted-foreground mb-8 max-w-2xl mx-auto'>
            会員登録後、すぐに無料で記事生成を始められます。クレジットカードは必要ありません。
          </p>
          <div className='flex flex-col sm:flex-row gap-4 justify-center'>
            <Button asChild variant='sexy' size='lg'>
              <Link href='/signup'>無料ではじめる</Link>
            </Button>
            <Button asChild variant='outline' size='lg'>
              <Link href='/pricing'>料金プランを見る</Link>
            </Button>
          </div>
        </div>
      </Container>
    </section>
  );
}