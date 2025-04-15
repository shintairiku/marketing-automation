'use client';

import { useState } from 'react';
import Link from 'next/link';
import { 
  IoAdd, 
  IoBarChart,
  IoCalendarOutline,
  IoCheckmarkCircleOutline,
  IoDocument, 
  IoEllipsisVertical, 
  IoEyeOutline,
  IoPencil, 
  IoTimeOutline,
  IoTrash,
  IoTrendingDown,
  IoTrendingUp} from 'react-icons/io5';

import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
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

export default function ImprovedDashboardPage() {
  const [articles] = useState<GeneratedArticle[]>(generateMockArticles());

  // 記事の状態によってバッジの色とテキストを変更
  const getStatusBadge = (status: string) => {
    if (status === 'published') {
      return (
        <span className="inline-flex items-center rounded-full bg-green-500/20 px-2.5 py-1 text-xs font-medium text-green-400">
          <IoCheckmarkCircleOutline className="mr-1" />
          公開済
        </span>
      );
    }
    return (
      <span className="inline-flex items-center rounded-full bg-amber-500/20 px-2.5 py-1 text-xs font-medium text-amber-400">
        <IoTimeOutline className="mr-1" />
        下書き
      </span>
    );
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
    <div className="space-y-8">
      {/* ウェルカムセクション */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold mb-1">こんにちは、ユーザーさん</h1>
          <p className="text-gray-400">効果的なSEO記事を作成して、あなたのビジネスを成長させましょう。</p>
        </div>
        <Button variant="sexy" asChild>
          <Link href="/generate">
            <IoAdd className="mr-2" size={18} /> 新しい記事を生成
          </Link>
        </Button>
      </div>

      {/* 使用状況サマリー */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-gray-400">今月の生成記事数</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-end justify-between">
              <div className="text-2xl font-bold">5 / 10</div>
              <IoDocument className="text-indigo-400" size={24} />
            </div>
            <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-gray-700">
              <div className="h-full w-1/2 bg-indigo-500"></div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-gray-400">公開済み記事</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-end justify-between">
              <div className="text-2xl font-bold">2</div>
              <IoCheckmarkCircleOutline className="text-green-400" size={24} />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-gray-400">下書き</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-end justify-between">
              <div className="text-2xl font-bold">3</div>
              <IoTimeOutline className="text-amber-400" size={24} />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-gray-400">アクセス状況</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-end justify-between">
              <div className="text-2xl font-bold">257</div>
              <div className="flex items-center text-green-400">
                <IoTrendingUp size={24} />
                <span className="text-xs ml-1">+12%</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* アクティビティグラフ */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>記事パフォーマンス</CardTitle>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="sm">今週</Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem>今日</DropdownMenuItem>
                <DropdownMenuItem>今週</DropdownMenuItem>
                <DropdownMenuItem>今月</DropdownMenuItem>
                <DropdownMenuItem>過去3ヶ月</DropdownMenuItem>
                <DropdownMenuItem>過去1年</DropdownMenuItem>
                <DropdownMenuItem>すべての期間</DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
          <CardDescription>公開記事のアクセス数とエンゲージメント</CardDescription>
        </CardHeader>
        <CardContent>
          {/* グラフの代わりにプレースホルダー */}
          <div className="h-[300px] w-full rounded-md bg-zinc-900 flex items-center justify-center">
            <div className="text-center">
              <IoBarChart size={60} className="mx-auto text-indigo-500/40" />
              <p className="mt-4 text-gray-400">グラフコンポーネントがここに表示されます</p>
              <p className="mt-2 text-sm text-gray-500">実際の実装ではチャートライブラリを使用してください</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 最近の記事 */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle>最近の記事</CardTitle>
          <Button variant="outline" asChild>
            <Link href="/dashboard/articles">すべて表示</Link>
          </Button>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-zinc-800">
                  <th className="pb-2 text-left text-xs font-normal text-gray-400">タイトル</th>
                  <th className="pb-2 text-left text-xs font-normal text-gray-400">ステータス</th>
                  <th className="pb-2 text-left text-xs font-normal text-gray-400">更新日</th>
                  <th className="pb-2 text-left text-xs font-normal text-gray-400">作成日</th>
                  <th className="pb-2 text-right text-xs font-normal text-gray-400">アクション</th>
                </tr>
              </thead>
              <tbody>
                {articles.map((article) => (
                  <tr key={article.id} className="border-b border-zinc-800/50 hover:bg-zinc-900/30">
                    <td className="py-3">
                      <div className="flex items-center">
                        <div className="flex h-8 w-8 items-center justify-center rounded-md border border-zinc-700 bg-zinc-800 text-gray-400 mr-3">
                          <IoDocument size={18} />
                        </div>
                        <Link 
                          href={`/edit?id=${article.id}`}
                          className="line-clamp-1 font-medium hover:text-indigo-400 hover:underline"
                        >
                          {article.title}
                        </Link>
                      </div>
                    </td>
                    <td className="py-3">{getStatusBadge(article.status)}</td>
                    <td className="py-3 text-sm text-gray-400">
                      <div className="flex items-center">
                        <IoCalendarOutline className="mr-1" size={14} />
                        {formatDate(article.updatedAt)}
                      </div>
                    </td>
                    <td className="py-3 text-sm text-gray-400">{formatDate(article.createdAt)}</td>
                    <td className="py-3 text-right">
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                            <IoEllipsisVertical size={16} />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem asChild>
                            <Link href={`/edit?id=${article.id}`} className="flex w-full items-center">
                              <IoPencil className="mr-2" size={14} /> 編集
                            </Link>
                          </DropdownMenuItem>
                          <DropdownMenuItem asChild>
                            <Link href={`/view?id=${article.id}`} className="flex w-full items-center">
                              <IoEyeOutline className="mr-2" size={14} /> プレビュー
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
        </CardContent>
        <CardFooter className="border-t border-zinc-800 pt-4">
          <p className="text-sm text-gray-400">過去30日間で合計5件の記事が作成されました。</p>
        </CardFooter>
      </Card>

      {/* ヒントカード */}
      <Card className="bg-gradient-to-br from-indigo-900/20 to-pink-900/20 border-indigo-800/30">
        <CardHeader>
          <CardTitle>SEO記事作成のヒント</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <p className="text-gray-300">より効果的なSEO記事を作成するためのヒント：</p>
            <ul className="list-disc pl-5 space-y-1 text-gray-300">
              <li>ターゲットキーワードを明確にし、記事のタイトルと最初の段落に含めましょう</li>
              <li>読者のニーズに合わせた充実したコンテンツを作成しましょう</li>
              <li>適切な見出し（H2、H3）を使用して、記事の構造を明確にしましょう</li>
              <li>適切な内部リンクを追加して、サイト内のナビゲーションを改善しましょう</li>
            </ul>
          </div>
        </CardContent>
        <CardFooter>
          <Button variant="outline" asChild>
            <Link href="/help/seo-tips">詳細なヒントを見る</Link>
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
}