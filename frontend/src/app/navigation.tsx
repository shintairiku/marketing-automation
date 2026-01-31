import Link from 'next/link';
import { IoMenu, IoSpeedometer } from 'react-icons/io5';

import { Logo } from '@/components/logo';
import { Button } from '@/components/ui/button';
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle, SheetTrigger } from '@/components/ui/sheet';
import { SignedIn, SignedOut, SignInButton, SignUpButton, UserButton } from '@clerk/nextjs';

export function Navigation() {
  return (
    <div className='relative flex items-center gap-6'>
      <SignedIn>
        <Button variant='outline' size='sm' className='hidden mr-2 flex-shrink-0 md:flex' asChild>
          <Link href='/dashboard'>
            <IoSpeedometer size={16} className="mr-2" /> ダッシュボード
          </Link>
        </Button>
        <UserButton afterSignOutUrl="/" />
      </SignedIn>
      <SignedOut>
        <div className="hidden lg:flex items-center gap-2">
          <SignInButton mode="modal">
            <Button variant='outline' size='sm'>サインイン</Button>
          </SignInButton>
          <SignUpButton mode="modal">
            <Button variant='sexy' className='flex-shrink-0'>無料ではじめる</Button>
          </SignUpButton>
        </div>
        <Sheet>
          <SheetTrigger className='block lg:hidden'>
            <IoMenu size={28} />
          </SheetTrigger>
          <SheetContent className="w-full bg-background">
            <SheetHeader>
              <SheetTitle>メニュー</SheetTitle>
              <Logo />
              <SheetDescription className='py-8 space-y-4'>
                <SignInButton mode="modal">
                  <Button variant='outline' className='w-full'>サインイン</Button>
                </SignInButton>
                <SignUpButton mode="modal">
                  <Button variant='sexy' className='w-full'>無料ではじめる</Button>
                </SignUpButton>
                <Button variant='ghost' asChild className='w-full'>
                  <Link href='/settings/billing'>料金プラン</Link>
                </Button>
                <Button variant='ghost' asChild className='w-full'>
                  <Link href='/features'>機能紹介</Link>
                </Button>
              </SheetDescription>
            </SheetHeader>
          </SheetContent>
        </Sheet>
      </SignedOut>
    </div>
  );
}