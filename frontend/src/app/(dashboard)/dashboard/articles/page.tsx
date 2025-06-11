'use client';

import { useState } from 'react';
import Link from 'next/link';
import { 
  IoAdd, 
  IoCalendarOutline,
  IoCheckmarkCircleOutline,
  IoChevronDownOutline,
  IoDocumentOutline,
  IoDownloadOutline,
  IoEllipsisVertical,
  IoEyeOutline,
  IoFilterOutline, 
  IoPencilOutline,
  IoSearchOutline, 
  IoTimeOutline,
  IoTrashOutline} from 'react-icons/io5';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { 
  Dialog, 
  DialogContent, 
  DialogDescription, 
  DialogFooter,
  DialogHeader, 
  DialogTitle} from '@/components/ui/dialog';
import { 
  DropdownMenu, 
  DropdownMenuContent, 
  DropdownMenuItem, 
  DropdownMenuTrigger 
} from '@/components/ui/dropdown-menu';
import { Input } from '@/components/ui/input';
import { toast } from '@/components/ui/use-toast';
import { GeneratedArticle } from '@/features/article-generation/types';

// ダミーデータを生成
const generateMockArticles = (): GeneratedArticle[] => {
  return [
    {
      id: '1',
      title: 'SEO対策の完全ガイド：初心者から上級者まで',
      content: '<p>SEO対策に関する完全ガイド。基礎知識から実践テクニックまで詳しく解説します。</p><h2>SEO対策とは何か？基本的な解説</h2><p>テキスト...</p><h2>SEO対策の主要なメリット</h2><p>テキスト...</p>',
      status: 'published',
      category: 'SEO',
      tags: ['ガイド', '初心者向け'],
      slug: 'seo-complete-guide',
      createdAt: '2025-04-05T09:12:44.123Z',
      updatedAt: '2025-04-07T16:23:15.456Z',
    },
    {
      id: '2',
      title: 'コンテンツマーケティングの最新トレンドと成功事例',
      content: '<p>コンテンツマーケティングの最新トレンドと成功事例を紹介します。</p><h2>コンテンツマーケティング市場の現状分析</h2><p>テキスト...</p><h2>2025年に注目すべき主要トレンド</h2><p>テキスト...</p>',
      status: 'draft',
      category: 'マーケティング',
      tags: ['トレンド', '事例'],
      slug: 'content-marketing-trends',
      createdAt: '2025-03-28T11:45:22.789Z',
      updatedAt: '2025-03-28T11:45:22.789Z',
    },
    {
      id: '3',
      title: 'ソーシャルメディアマーケティングの効果的な戦略',
      content: '<p>ソーシャルメディアマーケティングの効果的な戦略を解説します。</p><h2>ソーシャルメディアマーケティングの基礎</h2><p>テキスト...</p><h2>各プラットフォームの特性と活用法</h2><p>テキスト...</p>',
      status: 'published',
      category: 'SNS',
      tags: ['戦略', 'Facebook', 'Instagram'],
      slug: 'social-media-strategy',
      createdAt: '2025-04-01T15:37:10.123Z',
      updatedAt: '2025-04-03T09:18:42.456Z',
    },
    {
      id: '4',
      title: 'Google検索アルゴリズムの最新アップデート解説',
      content: '<p>Googleの検索アルゴリズムの最新アップデートとその影響について解説します。</p><h2>2025年のアルゴリズム変更点</h2><p>テキスト...</p><h2>コアウェブバイタルの重要性</h2><p>テキスト...</p>',
      status: 'draft',
      category: 'SEO',
      tags: ['Google', 'アルゴリズム'],
      slug: 'google-algorithm-update',
      createdAt: '2025-04-10T08:30:00.000Z',
      updatedAt: '2025-04-10T08:30:00.000Z',
    },
    {
      id: '5',
      title: 'BtoBマーケティングの成功戦略とリード獲得術',
      content: '<p>BtoB企業のためのマーケティング戦略とリード獲得方法を解説します。</p><h2>BtoBマーケティングの特徴と課題</h2><p>テキスト...</p><h2>効果的なリード獲得のための5つの方法</h2><p>テキスト...</p>',
      status: 'published',
      category: 'マーケティング',
      tags: ['BtoB', 'リード獲得'],
      slug: 'btob-marketing-strategy',
      createdAt: '2025-04-09T14:15:30.000Z',
      updatedAt: '2025-04-09T16:45:12.000Z',
    },
  ];
};

export default function ImprovedArticlesPage() {
  const [articles, setArticles] = useState<GeneratedArticle[]>(generateMockArticles());
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'published' | 'draft'>('all');
  const [sortBy, setSortBy] = useState<'updated' | 'created' | 'title'>('updated');
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [articleToDelete, setArticleToDelete] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'table' | 'grid'>('table');

  // 検索、フィルタリング、ソート
  const filteredArticles = articles
    .filter(article =>
      article.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (article.content && article.content.toLowerCase().includes(searchTerm.toLowerCase()))
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
        <span className="inline-flex items-center rounded-full bg-green-500/20 px-2.5 py-0.5 text-xs font-medium text-green-400">
          <IoCheckmarkCircleOutline className="mr-1" />
          公開済み
        </span>
      );
    }
    return (
      <span className="inline-flex items-center rounded-full bg-amber-500/20 px-2.5 py-0.5 text-xs font-medium text-amber-400">
        <IoTimeOutline className="mr-1" />
        下書き
      </span>
    );
  };

  return (
    <div className="space-y-6">
      {/* ヘッダー */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold mb-1">記事一覧</h1>
          <p className="text-muted-foreground">あなたが作成したすべての記事を管理します</p>
        </div>
        <Button variant="sexy" asChild>
          <Link href="/generate">
            <IoAdd className="mr-2" size={18} /> 新規作成
          </Link>
        </Button>
      </div>

      {/* フィルター・検索エリア */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-col gap-4 sm:flex-row">
            <div className="relative flex-1">
              <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
                <IoSearchOutline className="text-muted-foreground" />
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

              <div className="flex rounded-md border border-border overflow-hidden">
                <Button 
                  variant={viewMode === 'table' ? 'default' : 'ghost'} 
                  size="sm" 
                  onClick={() => setViewMode('table')}
                  className="rounded-none border-0"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                    <line x1="3" y1="9" x2="21" y2="9"></line>
                    <line x1="3" y1="15" x2="21" y2="15"></line>
                    <line x1="9" y1="3" x2="9" y2="21"></line>
                    <line x1="15" y1="3" x2="15" y2="21"></line>
                  </svg>
                </Button>
                <Button 
                  variant={viewMode === 'grid' ? 'default' : 'ghost'} 
                  size="sm"
                  onClick={() => setViewMode('grid')}
                  className="rounded-none border-0"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <rect x="3" y="3" width="7" height="7"></rect>
                    <rect x="14" y="3" width="7" height="7"></rect>
                    <rect x="14" y="14" width="7" height="7"></rect>
                    <rect x="3" y="14" width="7" height="7"></rect>
                  </svg>
                </Button>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 記事一覧表示エリア */}
      {filteredArticles.length === 0 ? (
        <Card className="py-16">
          <CardContent className="flex flex-col items-center justify-center">
            <IoDocumentOutline size={48} className="mb-4 text-gray-500" />
            <h3 className="text-xl font-medium mb-2">記事が見つかりません</h3>
            <p className="text-gray-500 text-center max-w-md">
              {searchTerm 
                ? '検索条件に一致する記事がありません。検索語を変更するか、フィルターをクリアしてみてください。' 
                : '記事がまだありません。「新規作成」ボタンから最初の記事を作成しましょう。'}
            </p>
            {searchTerm && (
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
            )}
          </CardContent>
        </Card>
      ) : viewMode === 'table' ? (
        <Card>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-border">
                    <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground">
                      タイトル
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground">
                      ステータス
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground">
                      更新日
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground">
                      作成日
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-muted-foreground">
                      <span className="sr-only">アクション</span>
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {filteredArticles.map((article) => (
                    <tr 
                      key={article.id} 
                      className="group cursor-pointer hover:bg-muted/50"
                      onClick={() => window.location.href = `/edit?id=${article.id}`}
                    >
                      <td className="whitespace-normal px-6 py-4">
                        <div className="flex items-start">
                          <div className="mr-3 flex-shrink-0 pt-1">
                            <div className="flex h-10 w-10 items-center justify-center rounded-md border border-border bg-muted text-muted-foreground group-hover:border-indigo-500 group-hover:bg-indigo-500/10 group-hover:text-indigo-400 transition-colors">
                              <IoDocumentOutline size={20} />
                            </div>
                          </div>
                          <div className="max-w-md">
                            <div className="font-medium text-foreground group-hover:text-indigo-400 transition-colors">{article.title}</div>
                            <div className="mt-1 hidden text-sm text-muted-foreground line-clamp-1 sm:block">{article.content}</div>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">{getStatusBadge(article.status)}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-muted-foreground">
                        <div className="flex items-center">
                          <IoCalendarOutline className="mr-1" size={14} />
                          {formatDate(article.updatedAt)}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-muted-foreground">{formatDate(article.createdAt)}</td>
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
                            <DropdownMenuItem asChild>
                              <Link href={`/view?id=${article.id}`} className="flex w-full items-center">
                                <IoEyeOutline className="mr-2" size={14} /> プレビュー
                              </Link>
                            </DropdownMenuItem>
                            <DropdownMenuItem asChild>
                              <Link href={`#`} className="flex w-full items-center">
                                <IoDownloadOutline className="mr-2" size={14} /> エクスポート
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
          </CardContent>
          <CardFooter className="border-t border-border py-3 px-6">
            <p className="text-sm text-muted-foreground">全 {filteredArticles.length} 件の記事</p>
          </CardFooter>
        </Card>
      ) : (
        // グリッドビュー
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredArticles.map((article) => (
            <Card 
              key={article.id} 
              className="overflow-hidden hover:border-indigo-500/50 transition-colors cursor-pointer group"
              onClick={() => window.location.href = `/edit?id=${article.id}`}
            >
              <CardHeader className="p-0">
                <div className="h-3 bg-gradient-to-r from-indigo-500 to-pink-500"></div>
              </CardHeader>
              <CardContent className="p-6">
                <div className="flex justify-between items-start mb-4">
                  <div className="flex items-center justify-center h-10 w-10 rounded-md border border-border bg-muted text-muted-foreground group-hover:border-indigo-500 group-hover:bg-indigo-500/10 group-hover:text-indigo-400 transition-colors">
                    <IoDocumentOutline size={20} />
                  </div>
                  <div className="flex items-center" onClick={(e) => e.stopPropagation()}>
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
                        <DropdownMenuItem asChild>
                          <Link href={`/view?id=${article.id}`} className="flex w-full items-center">
                            <IoEyeOutline className="mr-2" size={14} /> プレビュー
                          </Link>
                        </DropdownMenuItem>
                        <DropdownMenuItem asChild>
                          <Link href={`#`} className="flex w-full items-center">
                            <IoDownloadOutline className="mr-2" size={14} /> エクスポート
                          </Link>
                        </DropdownMenuItem>
                        <DropdownMenuItem 
                          className="text-red-500 focus:text-red-500" 
                          onClick={() => {
                            setArticleToDelete(article.id);
                            setIsDeleteDialogOpen(true);
                          }}
                        >
                          <IoTrashOutline className="mr-2" size={14} /> 削除
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                </div>
                
                <h3 className="text-lg font-medium mb-2 group-hover:text-indigo-400 transition-colors line-clamp-2">{article.title}</h3>
                <p className="text-sm text-muted-foreground mb-4 line-clamp-2">{article.content}</p>
                
                <div className="flex justify-between items-center">
                  {getStatusBadge(article.status)}
                  <div className="text-xs text-muted-foreground flex items-center">
                    <IoCalendarOutline className="mr-1" size={12} />
                    {formatDate(article.updatedAt)}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

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