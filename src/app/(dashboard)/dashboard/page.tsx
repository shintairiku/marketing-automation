'use client';

import { useState } from 'react';
import Link from 'next/link';
import { redirect } from 'next/navigation';
import { IoAdd, IoDocument, IoEllipsisVertical, IoPencil, IoTrash } from 'react-icons/io5';

import { Container } from '@/components/container';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { getSession } from '@/features/account/controllers/get-session';
import { GeneratedArticle } from '@/features/article-generation/types';

// ダミーデータを生成
const generateMockArticles = (): GeneratedArticle[] => {
  return [
    {
      id: '1',
      title: 'SEO対策の完全ガイド：初心者から上級者まで',
      metaDescription: 'SEO対策に関する完全ガイド。基礎知識から実践テクニックまで詳しく解説します。',
      sections: [
        { id: '1-1', level: 'h2', title: 'SEO対策とは何か？基本的な解説' },
        { id: '1-2', level: 'h2', title: 'SEO対策の主要なメリット' },
      ],
      createdAt: '2025-04-05T09:12:44.123Z',
      updatedAt: '2025-04-07T16:23:15.456Z',
      status: 'published',
    },
    {
      id: '2',
      title: 'コンテンツマーケティングの最新トレンドと成功事例',
      metaDescription: 'コンテンツマーケティングの最新トレンドと成功事例を紹介します。',
      sections: [
        { id: '2-1', level: 'h2', title: 'コンテンツマーケティング市場の現状分析' },
        { id: '2-2', level: 'h2', title: '2025年に注目すべき主要トレンド' },
      ],
      createdAt: '2025-03-28T11:45:22.789Z',
      updatedAt: '2025-03-28T11:45:22.789Z',
      status: 'draft',
    },
    {
      id: '3',
      title: 'ソーシャルメディアマーケティングの効果的な戦略',
      metaDescription: 'ソーシャルメディアマーケティングの効果的な戦略を解説します。',
      sections: [
        { id: '3-1', level: 'h2', title: 'ソーシャルメディアマーケティングの基礎' },
        { id: '3-2', level: 'h2', title: '各プラットフォームの特性と活用法' },
      ],
      createdAt: '2025-04-01T15:37:10.123Z',
      updatedAt: '2025-04-03T09:18:42.456Z',
      status: 'published',
    },
  ];
};

export default function DashboardPage() {
  const [articles] = useState<GeneratedArticle[]>(generateMockArticles());

  // 記事の状態によってバッジの色とテキストを変更
  const getStatusBadge = (status: string) => {
    if (status === 'published') {
      return <span className="rounded-full bg-green-500/20 px-2 py-1 text-xs text-green-400">公開済</span>;
    }
    return <span className="rounded-full bg-amber-500/20 px-2 py-1 text-xs text-amber-400">下書き</span>;
  };

  // 日付をフォーマット
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('ja-JP', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  return (
    <Container className="py-10">
      <div className="mx-auto max-w-4xl">
        <div className="mb-8 flex items-center justify-between">
          <h1 className="text-2xl font-bold">ダッシュボード</h1>
          <Button variant="sexy" asChild>
            <Link href="/generate">
              <IoAdd className="mr-2" size={18} /> 新しい記事を生成
            </Link>
          </Button>
        </div>

        <div className="mb-6 rounded-md border border-gray-700 bg-black p-6">
          <h2 className="mb-4 text-lg font-semibold">使用状況</h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div className="rounded-md bg-gray-800/50 p-4">
              <p className="text-sm text-gray-400">今月の生成記事数</p>
              <p className="mt-1 text-2xl font-bold">5 / 10</p>
              <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-gray-700">
                <div className="h-full w-1/2 bg-indigo-500"></div>
              </div>
            </div>
            <div className="rounded-md bg-gray-800/50 p-4">
              <p className="text-sm text-gray-400">公開済み記事</p>
              <p className="mt-1 text-2xl font-bold">2</p>
            </div>
            <div className="rounded-md bg-gray-800/50 p-4">
              <p className="text-sm text-gray-400">下書き</p>
              <p className="mt-1 text-2xl font-bold">3</p>
            </div>
          </div>
        </div>

        <div className="mb-6 rounded-md border border-gray-700 bg-black p-6">
          <h2 className="mb-4 text-lg font-semibold">最近の記事</h2>
          <div className="overflow-hidden sm:rounded-md">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-700">
                <thead>
                  <tr>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium uppercase text-gray-400">
                      タイトル
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium uppercase text-gray-400">
                      ステータス
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium uppercase text-gray-400">
                      更新日
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium uppercase text-gray-400">
                      作成日
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium uppercase text-gray-400">
                      <span className="sr-only">アクション</span>
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-700">
                  {articles.map((article) => (
                    <tr key={article.id} className="hover:bg-gray-800/30">
                      <td className="whitespace-nowrap px-6 py-4">
                        <div className="flex items-center">
                          <IoDocument className="mr-2 text-gray-400" size={18} />
                          <span className="font-medium">{article.title}</span>
                        </div>
                      </td>
                      <td className="whitespace-nowrap px-6 py-4">{getStatusBadge(article.status)}</td>
                      <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-300">
                        {formatDate(article.updatedAt)}
                      </td>
                      <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-300">
                        {formatDate(article.createdAt)}
                      </td>
                      <td className="whitespace-nowrap px-6 py-4 text-right text-sm">
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                              <IoEllipsisVertical size={16} />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem>
                              <Link href="/edit" className="flex w-full items-center">
                                <IoPencil className="mr-2" size={14} /> 編集
                              </Link>
                            </DropdownMenuItem>
                            <DropdownMenuItem className="text-red-500 focus:text-red-500">
                              <IoTrash className="mr-2" size={14} /> 削除
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </Container>
  );
}
