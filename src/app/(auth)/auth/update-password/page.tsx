'use client';

import { FormEvent, useState } from 'react';
import Image from 'next/image';
import Link from 'next/link';
import { useRouter } from 'next/navigation';

import { updateUserPassword } from '@/app/(auth)/auth-actions';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { toast } from '@/components/ui/use-toast';

export default function UpdatePasswordPage() {
  const [isLoading, setIsLoading] = useState(false);
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const router = useRouter();

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    
    // パスワードのバリデーション
    if (password.length < 6) {
      toast({
        variant: 'destructive',
        description: 'パスワードは6文字以上である必要があります。',
      });
      return;
    }
    
    if (password !== confirmPassword) {
      toast({
        variant: 'destructive',
        description: 'パスワードが一致しません。',
      });
      return;
    }
    
    setIsLoading(true);
    
    try {
      const response = await updateUserPassword(password);
      
      if (response?.error) {
        toast({
          variant: 'destructive',
          description: 'パスワードの更新中にエラーが発生しました。もう一度お試しください。',
        });
      } else {
        toast({
          description: 'パスワードが正常に更新されました。',
        });
        // ダッシュボードまたはアカウントページにリダイレクト
        router.push('/account');
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
      <div className='mt-16 flex w-full flex-col gap-8 rounded-lg bg-black p-10 px-4 text-center'>
        <div className='flex flex-col gap-4'>
          <Image src='/logo.png' width={80} height={80} alt='' className='m-auto' />
          <h1 className='text-lg'>新しいパスワードを設定</h1>
        </div>
        
        <form onSubmit={handleSubmit} className='flex flex-col gap-4'>
          <div className='space-y-2'>
            <label htmlFor='password' className='block text-left text-sm font-medium'>
              新しいパスワード
            </label>
            <Input
              id='password'
              type='password'
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder='新しいパスワード'
              required
              minLength={6}
              disabled={isLoading}
            />
          </div>
          
          <div className='space-y-2'>
            <label htmlFor='confirmPassword' className='block text-left text-sm font-medium'>
              パスワードの確認
            </label>
            <Input
              id='confirmPassword'
              type='password'
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder='パスワードの確認'
              required
              minLength={6}
              disabled={isLoading}
            />
          </div>
          
          <Button
            type='submit'
            className='mt-2 w-full'
            disabled={isLoading}
            variant='sexy'
          >
            {isLoading ? '処理中...' : 'パスワードを更新'}
          </Button>
          
          <div className='mt-4 text-sm'>
            <Link href='/login' className='text-indigo-400 hover:underline'>
              ログインページに戻る
            </Link>
          </div>
        </form>
      </div>
    </section>
  );
}
