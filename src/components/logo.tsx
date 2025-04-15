import Link from 'next/link';

export function Logo() {
  return (
    <Link href='/' className='flex w-fit items-center gap-2'>
      <span className='font-alt text-xl text-white'>SEO記事くん</span>
    </Link>
  );
}
