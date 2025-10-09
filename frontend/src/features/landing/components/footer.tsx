import Link from 'next/link';

export function LandingFooter() {
  return (
    <footer className='bg-primary-dark py-16 text-white'>
      <div className='mx-auto grid max-w-7xl grid-cols-1 gap-12 px-4 sm:px-6 lg:grid-cols-3 lg:px-8'>
        <div className='lg:col-span-2'>
          <h3 className='mb-8 text-2xl font-bold'>会社情報</h3>
          <div className='grid grid-cols-1 gap-8 md:grid-cols-2'>
            <dl className='space-y-4 text-sm leading-relaxed text-white'>
              <div>
                <dt className='mb-1 text-gray-300'>会社名</dt>
                <dd>株式会社新大陸</dd>
              </div>
              <div>
                <dt className='mb-1 text-gray-300'>設立</dt>
                <dd>1989年04月</dd>
              </div>
              <div>
                <dt className='mb-1 text-gray-300'>資本金</dt>
                <dd>1,000万円</dd>
              </div>
              <div>
                <dt className='mb-1 text-gray-300'>代表者</dt>
                <dd>代表取締役 鈴木 宏佳</dd>
              </div>
              <div>
                <dt className='mb-1 text-gray-300'>スタッフ数</dt>
                <dd>50名</dd>
              </div>
              <div>
                <dt className='mb-1 text-gray-300'>売上高</dt>
                <dd>9億円 / グループ売上高 12億円（2024年度実績）</dd>
              </div>
            </dl>

            <div className='space-y-6 text-sm leading-relaxed text-white'>
              <div>
                <dt className='mb-3 text-gray-300'>運営事業</dt>
                <dd className='space-y-1'>
                  <p>・Webマーケティング事業</p>
                  <p>・SNS運用サービス</p>
                  <p>・ホームページ制作</p>
                  <p>・インターネット広告の戦略的運用</p>
                  <p>・マーケティングAIエージェント開発</p>
                </dd>
              </div>
              <div>
                <dt className='mb-3 text-gray-300'>グループ会社</dt>
                <dd className='space-y-1'>
                  <p>ワビサビ株式会社</p>
                  <p>Off Beat株式会社</p>
                  <p>株式会社＋1℃</p>
                </dd>
              </div>
            </div>
          </div>
        </div>

        <div>
          <h3 className='mb-6 text-2xl font-bold text-primary-orange'>SEO Tiger</h3>
          <p className='mb-6 leading-relaxed text-gray-300'>
            AIが自動生成する高品質なSEO記事で、
            <br />
            あなたのWebマーケティングを次のレベルへ。
          </p>

          <div className='space-y-3'>
            <Link
              href='/sign-up'
              className='block rounded-lg bg-primary-green px-6 py-3 text-center font-semibold text-white transition-colors hover:bg-primary-green/90'
            >
              無料で始める
            </Link>
            <Link
              href='mailto:info@shintairiku.jp'
              className='block rounded-lg border border-white px-6 py-3 text-center font-semibold text-white transition-colors hover:bg-white hover:text-primary-dark'
            >
              お問い合わせ
            </Link>
          </div>
        </div>
      </div>

      <div className='mt-12 border-t border-white/20 pt-8 text-center text-sm text-gray-300'>
        © {new Date().getFullYear()} 株式会社新大陸. All rights reserved.
      </div>
    </footer>
  );
}
