'use client';

import { FormEvent, useState } from 'react';
import Image from 'next/image';
import Link from 'next/link';
import { IoLogoGoogle } from 'react-icons/io5';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { toast } from '@/components/ui/use-toast';
import { ActionResponse } from '@/types/action-response';

const titleMap = {
  login: 'ログイン',
  signup: '登録して無料でバナー生成を始めましょう',
} as const;

export function AuthUI({
  mode,
  signInWithOAuth,
  signInWithEmailAndPassword,
  signUpWithEmailAndPassword,
}: {
  mode: 'login' | 'signup';
  signInWithOAuth: (provider: 'google') => Promise<ActionResponse>;
  signInWithEmailAndPassword?: (email: string, password: string) => Promise<ActionResponse>;
  signUpWithEmailAndPassword?: (email: string, password: string) => Promise<ActionResponse>;
}) {
  const [pending, setPending] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setError('');
    
    try {
      if (mode === 'login' && signInWithEmailAndPassword) {
        const response = await signInWithEmailAndPassword(email, password);
        if (response?.error) {
          setError('ログインに失敗しました。メールアドレスとパスワードを確認してください。');
          toast({
            variant: 'destructive',
            description: 'ログインに失敗しました。メールアドレスとパスワードを確認してください。',
          });
        }
      } else if (mode === 'signup' && signUpWithEmailAndPassword) {
        const response = await signUpWithEmailAndPassword(email, password);
        if (response?.error) {
          setError('登録に失敗しました。既に使用されているメールアドレスか、パスワードが条件を満たしていません。');
          toast({
            variant: 'destructive',
            description: '登録に失敗しました。既に使用されているメールアドレスか、パスワードが条件を満たしていません。',
          });
        } else {
          toast({
            description: '確認メールを送信しました。メールを確認して登録を完了してください。',
          });
        }
      }
    } catch (err) {
      console.error(err);
      setError('エラーが発生しました。もう一度お試しください。');
      toast({
        variant: 'destructive',
        description: 'エラーが発生しました。もう一度お試しください。',
      });
    } finally {
      setPending(false);
    }
  }

  async function handleOAuthClick(provider: 'google') {
    setPending(true);
    const response = await signInWithOAuth(provider);

    if (response?.error) {
      toast({
        variant: 'destructive',
        description: '認証中にエラーが発生しました。もう一度お試しください。',
      });
      setPending(false);
    }
  }

  return (
    <section className='mt-16 flex w-full flex-col gap-8 rounded-lg bg-black p-10 px-4 text-center'>
      <div className='flex flex-col gap-4'>
        <Image src='/logo.png' width={80} height={80} alt='' className='m-auto' />
        <h1 className='text-lg'>{titleMap[mode]}</h1>
      </div>
      
      <div className='flex flex-col gap-6'>
        {/* メールとパスワードのフォーム */}
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
              disabled={pending}
            />
          </div>
          
          <div className='space-y-2'>
            <div className='flex items-center justify-between'>
              <label htmlFor='password' className='block text-sm font-medium'>
                パスワード
              </label>
              {mode === 'login' && (
                <Link href='/forgot-password' className='text-xs text-indigo-400 hover:underline'>
                  パスワードをお忘れですか？
                </Link>
              )}
            </div>
            <Input
              id='password'
              type='password'
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder='パスワードを入力'
              required
              minLength={6}
              disabled={pending}
            />
          </div>
          
          {error && (
            <p className='mt-2 text-sm text-red-500'>{error}</p>
          )}
          
          <Button
            type='submit'
            className='mt-2'
            disabled={pending}
            variant='sexy'
          >
            {pending ? '処理中...' : mode === 'login' ? 'ログイン' : 'アカウント作成'}
          </Button>
        </form>
        
        <div className='relative flex items-center justify-center'>
          <div className='absolute inset-0 flex items-center'>
            <div className='w-full border-t border-gray-700'></div>
          </div>
          <div className='relative bg-black px-4 text-xs text-gray-400'>または</div>
        </div>
        
        {/* Googleでの認証ボタン */}
        <button
          className='flex items-center justify-center gap-2 rounded-md bg-cyan-500 py-4 font-medium text-black transition-all hover:bg-cyan-400 disabled:bg-neutral-700'
          onClick={() => handleOAuthClick('google')}
          disabled={pending}
        >
          <IoLogoGoogle size={20} />
          Googleで{mode === 'login' ? 'ログイン' : '登録'}
        </button>
        
        {/* アカウント作成またはログインへのリンク */}
        <div className='mt-4 text-sm'>
          {mode === 'login' ? (
            <p>
              アカウントをお持ちでない場合は{' '}
              <Link href='/signup' className='text-indigo-400 hover:underline'>
                無料登録
              </Link>
            </p>
          ) : (
            <p>
              すでにアカウントをお持ちの場合は{' '}
              <Link href='/login' className='text-indigo-400 hover:underline'>
                ログイン
              </Link>
            </p>
          )}
        </div>
      </div>
      
      {mode === 'signup' && (
        <span className='text-neutral5 m-auto max-w-sm text-sm'>
          続けるをクリックすると、{' '}
          <Link href='/terms' className='underline'>
            利用規約
          </Link>{' '}
          および{' '}
          <Link href='/privacy' className='underline'>
            プライバシーポリシー
          </Link>
          に同意したことになります。
        </span>
      )}
    </section>
  );
}
