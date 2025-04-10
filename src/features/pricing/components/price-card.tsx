'use client';

import { useMemo, useState } from 'react';
import Link from 'next/link';
import { IoCheckmark } from 'react-icons/io5';

import { SexyBoarder } from '@/components/sexy-boarder';
import { Button } from '@/components/ui/button';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';

import { PriceCardVariant, productMetadataSchema } from '../models/product-metadata';
import { BillingInterval, Price, ProductWithPrices } from '../types';

export function PricingCard({
  product,
  price,
  createCheckoutAction,
}: {
  product: ProductWithPrices;
  price?: Price;
  createCheckoutAction?: ({ price }: { price: Price }) => void;
}) {
  const [billingInterval, setBillingInterval] = useState<BillingInterval>(
    price ? (price.interval as BillingInterval) : 'month'
  );

  // Determine the price to render
  const currentPrice = useMemo(() => {
    // If price is passed in we use that one. This is used on the account page when showing the user their current subscription.
    if (price) return price;

    // If no price provided we need to find the right one to render for the product.
    // First check if the product has a price - in the case of our enterprise product, no price is included.
    // We'll return null and handle that case when rendering.
    if (product.prices.length === 0) return null;

    // Next determine if the product is a one time purchase - in these cases it will only have a single price.
    if (product.prices.length === 1) return product.prices[0];

    // Lastly we can assume the product is a subscription one with a month and year price, so we get the price according to the select billingInterval
    return product.prices.find((price) => price.interval === billingInterval);
  }, [billingInterval, price, product.prices]);

  const monthPrice = product.prices.find((price) => price.interval === 'month')?.unit_amount;
  const yearPrice = product.prices.find((price) => price.interval === 'year')?.unit_amount;
  const isBillingIntervalYearly = billingInterval === 'year';
  const metadata = productMetadataSchema.parse(product.metadata);
  const buttonVariantMap = {
    basic: 'default',
    pro: 'sexy',
    enterprise: 'orange',
  } as const;

  function handleBillingIntervalChange(billingInterval: BillingInterval) {
    setBillingInterval(billingInterval);
  }

  return (
    <WithSexyBorder variant={metadata.priceCardVariant} className='w-full flex-1'>
      <div className='flex w-full flex-col rounded-md border border-zinc-800 bg-black p-4 lg:p-8'>
        <div className='p-4'>
          <div className='mb-1 text-center font-alt text-xl font-bold'>{product.name}</div>
          <div className='flex justify-center gap-0.5 text-zinc-400'>
            <span className='font-semibold'>
              {yearPrice && isBillingIntervalYearly
                ? '¥' + yearPrice
                : monthPrice
                ? '¥' + monthPrice
                : 'カスタム'}
            </span>
            <span>{yearPrice && isBillingIntervalYearly ? '/年' : monthPrice ? '/月' : null}</span>
          </div>
        </div>

        {!Boolean(price) && product.prices.length > 1 && <PricingSwitch onChange={handleBillingIntervalChange} />}

        <div className='m-auto flex w-fit flex-1 flex-col gap-2 px-8 py-4'>
          {/* 記事数 */}
          {typeof metadata.generatedArticles === 'string' && (
            <CheckItem text={`${metadata.generatedArticles === '無制限' ? '無制限の記事' : `${metadata.generatedArticles}記事/月`}`} />
          )}
          {typeof metadata.generatedArticles === 'number' && metadata.generatedArticles > 0 && (
            <CheckItem text={`${metadata.generatedArticles}記事/月`} />
          )}
          
          {/* 記事の長さ */}
          {metadata.articleLength && <CheckItem text={`${metadata.articleLength}`} />}
          
          {/* 画像編集機能(後方互換性) */}
          {metadata.imageEditor && <CheckItem text={`${metadata.imageEditor === 'basic' ? '基本' : '高度'}な編集機能`} />}
          
          {/* SEO最適化 */}
          {metadata.seoOptimization && <CheckItem text={`SEO最適化: ${metadata.seoOptimization}`} />}
          
          {/* チャット編集 */}
          {metadata.chatEdits && <CheckItem text={`編集モード: ${metadata.chatEdits}`} />}
          
          {/* エクスポート形式 */}
          {metadata.exportFormats && <CheckItem text={`エクスポート: ${metadata.exportFormats}`} />}
          
          {/* API連携 */}
          {metadata.apiAccess && <CheckItem text={`API連携: ${metadata.apiAccess}`} />}
          
          {/* カスタムブランディング */}
          {metadata.customBranding && <CheckItem text={`カスタムブランディング: ${metadata.customBranding}`} />}
          
          {/* サポートレベル（必須） */}
          {metadata.supportLevel && <CheckItem text={`${metadata.supportLevel}サポート`} />}
        </div>

        {createCheckoutAction && (
          <div className='py-4'>
            {currentPrice && (
              <Button
                variant={buttonVariantMap[metadata.priceCardVariant]}
                className='w-full'
                onClick={() => createCheckoutAction({ price: currentPrice })}
              >
                はじめる
              </Button>
            )}
            {!currentPrice && (
              <Button variant={buttonVariantMap[metadata.priceCardVariant]} className='w-full' asChild>
                <Link href='/contact'>お問い合わせ</Link>
              </Button>
            )}
          </div>
        )}
      </div>
    </WithSexyBorder>
  );
}

function CheckItem({ text }: { text: string }) {
  return (
    <div className='flex items-center gap-2'>
      <IoCheckmark className='my-auto flex-shrink-0 text-slate-500' />
      <p className='text-sm font-medium text-white first-letter:capitalize'>{text}</p>
    </div>
  );
}

export function WithSexyBorder({
  variant,
  className,
  children,
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant: PriceCardVariant }) {
  if (variant === 'pro') {
    return (
      <SexyBoarder className={className} offset={100}>
        {children}
      </SexyBoarder>
    );
  } else {
    return <div className={className}>{children}</div>;
  }
}

function PricingSwitch({ onChange }: { onChange: (value: BillingInterval) => void }) {
  return (
    <Tabs
      defaultValue='month'
      className='flex items-center'
      onValueChange={(newBillingInterval) => onChange(newBillingInterval as BillingInterval)}
    >
      <TabsList className='m-auto'>
        <TabsTrigger value='month'>月額</TabsTrigger>
        <TabsTrigger value='year'>年額</TabsTrigger>
      </TabsList>
    </Tabs>
  );
}
