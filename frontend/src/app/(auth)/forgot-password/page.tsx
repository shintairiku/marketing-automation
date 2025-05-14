'use client';

import { FormEvent, useState } from 'react';
import Image from 'next/image';
import Link from 'next/link';

import { resetPassword } from '@/app/(auth)/auth-actions';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { toast } from '@/components/ui/use-toast';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setIsLoading(true);
    
    try {
      const response = await resetPassword(email);
      
      if (response?.error) {
        toast({
          variant: 'destructive',
          description: 'エラーが発生しました。もう一度お試しください。',
        });
      } else {
        setIsSuccess(true);
        toast({
          description: 'パスワードリセットのメールが送信されました。メールボックスを確認してください。',
        });
      }
    } catch (error) {
      toast({
        variant: 'destructive',
        description: 'エラーが発生しました。もう一度お試しください。',
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <section className='py-xl m-auto flex h-full max-w-lg items-center'>
      <div className='mt-16 flex w-full flex-col gap-8 rounded-lg bg-background p-10 px-4 text-center'>
        <div className='flex flex-col gap-4'>
          <Image src='/logo.png' width={80} height={80} alt='' className='m-auto' />
          <h1 className='text-lg'>パスワードをリセット</h1>
        </div>
        
        {isSuccess ? (
          <div className='space-y-4'>
            <p className='text-sm text-muted-foreground'>
              パスワードリセットリンクを {email} に送信しました。
              メールを確認し、リンクをクリックしてパスワードの再設定を完了してください。
            </p>
            <Button variant='secondary' asChild className='mt-4'>
              <Link href='/login'>ログインに戻る</Link>
            </Button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className='flex flex-col gap-4'>
            <div className='space-y-2'>
              <label htmlFor='email' className='block text-left text-sm font-medium'>
                メールアドレス
              </label>
              <Input
                id='email'
                type='email'
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder='メールアドレスを入力'
                required
                disabled={isLoading}
              />
            </div>
            
            <Button
              type='submit'
              className='mt-2 w-full'
              disabled={isLoading}
              variant='sexy'
            >
              {isLoading ? '処理中...' : 'リセットリンクを送信'}
            </Button>
            
            <div className='mt-4 text-sm'>
              <Link href='/login' className='text-indigo-400 hover:underline'>
                ログインページに戻る
              </Link>
            </div>
          </form>
        )}
      </div>
    </section>
  );
}
