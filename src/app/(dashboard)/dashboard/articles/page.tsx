'use client';

import { useState } from 'react';
import Link from 'next/link';
import { 
  IoAdd, 
  IoSearchOutline, 
  IoFilterOutline, 
  IoEllipsisVertical,
  IoTrashOutline,
  IoPencilOutline,
  IoDocumentOutline,
  IoCheckmarkCircleOutline,
  IoTimeOutline,
  IoChevronDownOutline
} from 'react-icons/io5';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { 
  DropdownMenu, 
  DropdownMenuContent, 
  DropdownMenuItem, 
  DropdownMenuTrigger 
} from '@/components/ui/dropdown-menu';
import { 
  Dialog, 
  DialogContent, 
  DialogHeader, 
  DialogTitle, 
  DialogDescription, 
  DialogFooter
} from '@/components/ui/dialog';
import { toast } from '@/components/ui/use-toast';
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
    {
      id: '4',
      title: 'Google検索アルゴリズムの最新アップデート解説',
      metaDescription: 'Googleの検索アルゴリズムの最新アップデートとその影響について解説します。',
      sections: [
        { id: '4-1', level: 'h2', title: '2025年のアルゴリズム変更点' },
        { id: '4-2', level: 'h2', title: 'コアウェブバイタルの重要性' },
      ],
      createdAt: '2025-04-10T08:30:00.000Z',
      updatedAt: '2025-04-10T08:30:00.000Z',
      status: 'draft',
    },
    {
      id: '5',
      title: 'BtoBマーケティングの成功戦略とリード獲得術',
      metaDescription: 'BtoB企業のためのマーケティング戦略とリード獲得方法を解説します。',
      sections: [
        { id: '5-1', level: 'h2', title: 'BtoBマーケティングの特徴と課題' },
        { id: '5-2', level: 'h2', title: '効果的なリード獲得のための5つの方法' },
      ],
      createdAt: '2025-04-09T14:15:30.000Z',
      updatedAt: '2025-04-09T16:45:12.000Z',
      status: 'published',
    },
  ];
};

export default function ArticlesPage() {
  const [articles, setArticles] = useState<GeneratedArticle[]>(generateMockArticles());
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'published' | 'draft'>('all');
  const [sortBy, setSortBy] = useState<'updated' | 'created' | 'title'>('updated');
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [articleToDelete, setArticleToDelete] = useState<string | null>(null);

  // 検索、フィルタリング、ソート
  const filteredArticles = articles
    .filter(article => 
      article.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      article.metaDescription.toLowerCase().includes(searchTerm.toLowerCase())
    )
    .filter(article => 
      statusFilter === 'all' ? true : article.status === statusFilter
    )
    .sort((a, b) => {
      if (sortBy === 'updated') {
        return new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime();
      } else if (sortBy === 'created') {
        return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime();
      } else {
        return a.title.localeCompare(b.title);
      }
    });

  // 記事の削除
  const handleDeleteArticle = () => {
    if (articleToDelete) {
      setArticles(articles.filter(article => article.id !== articleToDelete));
      toast({
        description: '記事を削除しました',
      });
      setArticleToDelete(null);
      setIsDeleteDialogOpen(false);
    }
  };

  // 日付フォーマット
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('ja-JP', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  // ステータスバッジ
  const getStatusBadge = (status: string) => {
    if (status === 'published') {
      return (
        <span className="inline-flex items-center rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-medium text-green-800">
          <IoCheckmarkCircleOutline className="mr-1" />
          公開済み
        </span>
      );
    }
    return (
      <span className="inline-flex items-center rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-medium text-amber-800">
        <IoTimeOutline className="mr-1" />
        下書き
      </span>
    );
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">記事一覧</h1>
        <Button variant="sexy" asChild>
          <Link href="/generate">
            <IoAdd className="mr-2" size={18} /> 新規作成
          </Link>
        </Button>
      </div>

      <div className="rounded-md border border-zinc-800 bg-zinc-900 p-4">
        <div className="flex flex-col gap-4 sm:flex-row">
          <div className="relative flex-1">
            <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
              <IoSearchOutline className="text-gray-400" />
            </div>
            <Input
              type="text"
              placeholder="タイトルや内容で検索..."
              className="pl-10"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          <div className="flex gap-2">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" className="flex items-center gap-1">
                  <IoFilterOutline className="mr-1" size={16} />
                  {statusFilter === 'all' 
                    ? 'すべて' 
                    : statusFilter === 'published' 
                      ? '公開済み' 
                      : '下書き'}
                  <IoChevronDownOutline size={14} />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={() => setStatusFilter('all')}>
                  すべて
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => setStatusFilter('published')}>
                  公開済み
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => setStatusFilter('draft')}>
                  下書き
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>

            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" className="flex items-center gap-1">
                  並び替え
                  <IoChevronDownOutline size={14} />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={() => setSortBy('updated')}>
                  更新日（新しい順）
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => setSortBy('created')}>
                  作成日（新しい順）
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => setSortBy('title')}>
                  タイトル（A-Z）
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </div>

      <div className="rounded-md border border-zinc-800 bg-zinc-900">
        {filteredArticles.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16">
            <IoDocumentOutline size={48} className="mb-4 text-gray-500" />
            <p className="text-gray-500">記事が見つかりません</p>
            {searchTerm && (
              <p className="mt-2 text-sm text-gray-600">
                検索条件を変更するか、新しい記事を作成してください
              </p>
            )}
            <Button 
              variant="outline" 
              className="mt-4" 
              onClick={() => {
                setSearchTerm('');
                setStatusFilter('all');
              }}
            >
              フィルターをクリア
            </Button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-zinc-800">
              <thead className="bg-zinc-900">
                <tr>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-400">
                    タイトル
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-400">
                    ステータス
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-400">
                    更新日
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-400">
                    作成日
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-400">
                    <span className="sr-only">アクション</span>
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800 bg-zinc-900">
                {filteredArticles.map((article) => (
                  <tr 
                    key={article.id} 
                    className="group cursor-pointer hover:bg-zinc-800/50"
                    onClick={() => window.location.href = `/edit?id=${article.id}`}
                  >
                    <td className="whitespace-normal px-6 py-4">
                      <div className="flex items-start">
                        <div className="mr-3 flex-shrink-0 pt-1">
                          <div className="flex h-8 w-8 items-center justify-center rounded-md border border-zinc-700 bg-zinc-800 text-gray-400">
                            <IoDocumentOutline size={18} />
                          </div>
                        </div>
                        <div className="max-w-md">
                          <div className="font-medium text-white">{article.title}</div>
                          <div className="mt-1 hidden text-sm text-gray-400 line-clamp-1 sm:block">{article.metaDescription}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">{getStatusBadge(article.status)}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-400">{formatDate(article.updatedAt)}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-400">{formatDate(article.createdAt)}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium" onClick={(e) => e.stopPropagation()}>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                            <IoEllipsisVertical size={16} />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem asChild>
                            <Link href={`/edit?id=${article.id}`} className="flex w-full items-center">
                              <IoPencilOutline className="mr-2" size={14} /> 編集
                            </Link>
                          </DropdownMenuItem>
                          <DropdownMenuItem className="text-red-500 focus:text-red-500" onClick={() => {
                            setArticleToDelete(article.id);
                            setIsDeleteDialogOpen(true);
                          }}>
                            <IoTrashOutline className="mr-2" size={14} /> 削除
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* 削除確認ダイアログ */}
      <Dialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>記事を削除しますか？</DialogTitle>
            <DialogDescription>
              この操作は元に戻せません。本当にこの記事を削除してもよろしいですか？
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="flex justify-end gap-2 sm:space-x-0">
            <Button variant="outline" onClick={() => setIsDeleteDialogOpen(false)}>
              キャンセル
            </Button>
            <Button variant="destructive" onClick={handleDeleteArticle}>
              <IoTrashOutline className="mr-2" size={14} /> 削除
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
