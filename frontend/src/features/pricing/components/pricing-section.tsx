import Image from 'next/image';

import { PricingCard } from '@/features/pricing/components/price-card';
import { TeamPricingCard } from '@/features/pricing/components/team-pricing-card';
import { getProducts } from '@/features/pricing/controllers/get-products';

import { createCheckoutAction } from '../actions/create-checkout-action';

export async function PricingSection({ isPricingPage }: { isPricingPage?: boolean }) {
  const products = await getProducts();

  const HeadingLevel = isPricingPage ? 'h1' : 'h2';

  return (
    <section className='relative rounded-lg bg-background py-8'>
      <div className='relative z-10 m-auto flex max-w-[1200px] flex-col items-center gap-8 px-4 pt-8 lg:pt-[140px]'>
        <HeadingLevel className='max-w-4xl bg-gradient-to-br from-white to-neutral-200 bg-clip-text text-center text-4xl font-bold text-transparent lg:text-6xl'>
          あらゆる用途に対応する明確な料金プラン。
        </HeadingLevel>
        <p className='text-center text-xl'>
          あなたに合ったプランを見つけましょう。いつでもアップグレードして機能を追加できます。
        </p>
        
        {/* プランタブ */}
        <div className="flex justify-center mb-8">
          <div className="bg-gray-100 rounded-lg p-1">
            <button className="px-4 py-2 rounded-md bg-white text-gray-900 font-medium shadow-sm">
              個人プラン
            </button>
            <button className="px-4 py-2 rounded-md text-gray-600 font-medium">
              チームプラン
            </button>
          </div>
        </div>

        {/* 個人プラン */}
        <div className='flex w-full flex-col items-center justify-center gap-2 lg:flex-row lg:gap-8 mb-12'>
          {products.map((product) => {
            return <PricingCard key={product.id} product={product} createCheckoutAction={createCheckoutAction} />;
          })}
        </div>

        {/* チームプラン */}
        <div className="w-full max-w-md mx-auto">
          <h3 className="text-2xl font-bold text-center mb-6 text-gray-900">
            チーム・組織向けプラン
          </h3>
          <TeamPricingCard />
        </div>
      </div>
      <Image
        src='/section-bg.png'
        width={1440}
        height={462}
        alt=''
        className='absolute left-0 top-0 rounded-t-lg'
        priority={isPricingPage}
        quality={100}
      />
    </section>
  );
}
