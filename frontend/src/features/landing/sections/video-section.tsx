import { CloudShape } from '@/features/landing/components/background/cloud-shape';
import { CloudShapeThree } from '@/features/landing/components/background/cloud-shape-three';
import { CloudShapeTwo } from '@/features/landing/components/background/cloud-shape-two';
import { GridBackground } from '@/features/landing/components/background/grid-background';

export function VideoSection() {
  return (
    <section className='relative overflow-hidden bg-primary-beige py-24 sm:py-28 lg:py-32'>
      <GridBackground />

      <CloudShape variant='light' className='right-20 top-10 opacity-70' />
      <CloudShapeTwo variant='orange' className='left-16 top-1/3 opacity-60' />
      <CloudShapeThree variant='beige' className='right-32 bottom-20 opacity-50' />
      <CloudShape variant='beige' className='left-10 bottom-10 opacity-40' />
      <CloudShapeTwo variant='green' className='left-1/2 top-20 opacity-30' />
      <CloudShapeThree variant='dark' className='right-10 top-1/2 opacity-25' />
      <CloudShape variant='light' className='left-20 bottom-1/3 opacity-35' />
      <CloudShapeTwo variant='beige' className='right-1/4 top-3/4 opacity-20' />

      <div className='mx-auto max-w-6xl px-4 sm:px-6 lg:px-8'>
        <div className='mb-14 text-center sm:mb-16'>
          <h2 className='text-3xl font-bold text-primary-dark sm:text-4xl lg:text-5xl'>1分でわかるSEO Tiger</h2>
        </div>

        <div className='mx-auto max-w-4xl'>
          <div className='group relative aspect-video overflow-hidden rounded-2xl bg-black shadow-2xl transition-all duration-300 hover:shadow-3xl'>
            <div className='absolute inset-0 bg-gradient-to-br from-primary-dark via-primary-dark/90 to-black' />
            <div className='absolute inset-0 flex items-center justify-center'>
              <div className='flex h-24 w-24 items-center justify-center rounded-full bg-primary-orange shadow-lg transition-transform duration-300 group-hover:scale-110'>
                <div className='ml-1 h-0 w-0 border-b-[12px] border-l-[20px] border-t-[12px] border-b-transparent border-l-white border-t-transparent' />
              </div>
            </div>
            <div className='absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/80 to-transparent px-6 py-6 sm:px-8 sm:py-8'>
              <h3 className='mb-2 text-xl font-semibold text-white sm:text-2xl'>SEO Tiger 機能紹介</h3>
              <p className='text-sm text-white/80 sm:text-base'>AIによる自動記事生成からカスタマイズまで</p>
            </div>
            <div className='absolute right-4 top-4 rounded-full bg-black/70 px-3 py-1 text-sm font-medium text-white'>
              1:00
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
