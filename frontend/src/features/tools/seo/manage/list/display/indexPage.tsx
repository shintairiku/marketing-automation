"use client"

import { useState } from "react";
import { useRouter } from "next/navigation";
import { BarChart3, Calendar, Edit, Eye,User } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination";
import {
  Sheet,
  SheetClose,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useArticleDetail,useArticles } from "@/hooks/useArticles";

const PAGE_SIZE = 20;

export default function IndexPage() {
  const router = useRouter();
  const [selectedArticleId, setSelectedArticleId] = useState<string | null>(null);
  const [sheetOpen, setSheetOpen] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>("");

  // 記事一覧を取得
  const {
    articles,
    loading: articlesLoading,
    error: articlesError,
    currentPage,
    totalPages,
    setPage,
    refetch
  } = useArticles(PAGE_SIZE, statusFilter || undefined);

  // 選択された記事の詳細を取得
  const {
    article: selectedArticle,
    loading: articleLoading,
    error: articleError
  } = useArticleDetail(selectedArticleId);

  const handleRowClick = (articleId: string) => {
    setSelectedArticleId(articleId);
    setSheetOpen(true);
  };

  const handleFilterApply = (filter: string) => {
    setStatusFilter(filter);
    setPage(1); // Reset to first page when applying filter
  };

  const handleClearFilter = () => {
    setStatusFilter("");
    setPage(1); // Reset to first page when clearing filter
  };

  const handleEditClick = (articleId: string, e: React.MouseEvent) => {
    e.stopPropagation(); // カードクリックイベントを防ぐ
    router.push(`/seo/generate/edit-article/${articleId}`);
  };

  const formatDate = (dateString: string) => {
    try {
      return new Date(dateString).toLocaleDateString('ja-JP', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
      });
    } catch {
      return dateString;
    }
  };

  const getStatusDisplay = (status: string) => {
    switch (status) {
      case 'completed': return '完了';
      case 'in_progress': return '進行中';
      case 'error': return 'エラー';
      case 'cancelled': return 'キャンセル';
      default: return status;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'bg-green-100 text-green-800';
      case 'in_progress': return 'bg-blue-100 text-blue-800';
      case 'error': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  if (articlesError) {
    return (
      <div className="space-y-6">
        <Card className="p-4">
          <div className="text-center text-red-600">
            <p>記事の読み込み中にエラーが発生しました: {articlesError}</p>
            <Button onClick={refetch} className="mt-2">
              再試行
            </Button>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* ヘッダー */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">記事管理</h1>
          <p className="text-gray-600 mt-1">生成された記事の管理と編集</p>
        </div>
        <div className="flex items-center gap-2">
          <Dialog>
            <DialogTrigger asChild>
              <Button variant="outline">フィルター</Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>記事をフィルター</DialogTitle>
              </DialogHeader>
              <div className="flex flex-col gap-4 py-2">
                <div>
                  <label className="block text-sm mb-1">ステータス</label>
                  <select 
                    className="border rounded px-2 py-1 w-full"
                    value={statusFilter}
                    onChange={(e) => setStatusFilter(e.target.value)}
                  >
                    <option value="">すべて</option>
                    <option value="completed">完了</option>
                    <option value="in_progress">進行中</option>
                    <option value="error">エラー</option>
                    <option value="cancelled">キャンセル</option>
                  </select>
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={handleClearFilter}>クリア</Button>
                <Button onClick={() => handleFilterApply(statusFilter)}>適用</Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
          <Button variant="outline" onClick={refetch}>
            更新
          </Button>
        </div>
      </div>

      {/* メインコンテンツエリア */}
      {articlesLoading ? (
        <div className="flex justify-center items-center py-16">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900 mx-auto"></div>
            <p className="mt-4 text-lg text-gray-600">記事を読み込み中...</p>
          </div>
        </div>
      ) : articles.length === 0 ? (
        <div className="text-center py-16">
          <div className="max-w-md mx-auto">
            <div className="bg-gray-100 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4">
              <Edit className="w-8 h-8 text-gray-600" />
            </div>
            <h3 className="text-xl font-semibold text-gray-900 mb-2">記事がありません</h3>
            <p className="text-gray-600">
              {statusFilter ? `「${getStatusDisplay(statusFilter)}」ステータスの記事が見つかりません` : "まだ記事が生成されていません"}
            </p>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {articles.map((article) => (
            <Card 
              key={article.id} 
              className="overflow-hidden hover:shadow-lg transition-shadow duration-200 cursor-pointer bg-white"
              onClick={() => handleRowClick(article.id)}
            >
              {/* カードヘッダー画像風エリア */}
              <div className="h-48 bg-gradient-to-br from-blue-50 to-indigo-100 relative">
                <div className="absolute top-4 left-4">
                  <span className={`px-3 py-1 text-xs font-medium rounded-full ${getStatusColor(article.status)}`}>
                    {getStatusDisplay(article.status)}
                  </span>
                </div>
                <div className="absolute bottom-4 left-4 right-4">
                  <h3 className="text-lg font-bold text-gray-900 line-clamp-2 leading-tight">
                    {article.title}
                  </h3>
                </div>
              </div>
              
              {/* カードコンテンツ */}
              <div className="p-6">
                <p className="text-gray-600 text-sm line-clamp-3 mb-4">
                  {article.shortdescription || "記事の概要が設定されていません"}
                </p>
                
                {/* メタ情報 */}
                <div className="space-y-2 mb-4">
                  <div className="flex items-center text-sm text-gray-500">
                    <Calendar className="w-4 h-4 mr-2" />
                    <span>{formatDate(article.postdate)}</span>
                  </div>
                  {article.target_audience && (
                    <div className="flex items-center text-sm text-gray-500">
                      <User className="w-4 h-4 mr-2" />
                      <span className="line-clamp-1">{article.target_audience}</span>
                    </div>
                  )}
                </div>
                
                {/* アクションボタン */}
                <div className="flex gap-2">
                  <Button 
                    size="sm" 
                    className="flex-1 bg-secondary hover:bg-secondary/90"
                    onClick={(e) => handleEditClick(article.id, e)}
                  >
                    <Edit className="w-4 h-4 mr-1" />
                    修正
                  </Button>
                  <Button 
                    size="sm" 
                    variant="outline" 
                    className="flex-1"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleRowClick(article.id);
                    }}
                  >
                    <Eye className="w-4 h-4 mr-1" />
                    分析
                  </Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* 下部：ページネーション */}
      {articles.length > 0 && (
        <div className="flex justify-center items-center gap-2">
          <Pagination>
            <PaginationContent>
              <PaginationItem>
                <PaginationPrevious
                  onClick={() => setPage(Math.max(1, currentPage - 1))}
                  aria-disabled={currentPage === 1}
                  className={currentPage === 1 ? "pointer-events-none opacity-50" : ""}
                />
              </PaginationItem>
              <span>
                {currentPage} / {totalPages}
              </span>
              <PaginationItem>
                <PaginationNext
                  onClick={() => setPage(Math.min(totalPages, currentPage + 1))}
                  aria-disabled={currentPage === totalPages}
                  className={currentPage === totalPages ? "pointer-events-none opacity-50" : ""}
                />
              </PaginationItem>
            </PaginationContent>
          </Pagination>
        </div>
      )}

      {/* サイドシート（記事プレビュー） */}
      <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
        <SheetContent side="right" className="max-w-xl w-full">
          <SheetHeader>
            <SheetTitle>記事プレビュー</SheetTitle>
          </SheetHeader>
          <div className="mt-4">
            {articleLoading ? (
              <div className="flex justify-center items-center py-8">
                <div className="text-center">
                  <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-gray-900 mx-auto"></div>
                  <p className="mt-2 text-sm text-gray-600">記事を読み込み中...</p>
                </div>
              </div>
            ) : articleError ? (
              <div className="text-center text-red-600 py-4">
                <p>記事の読み込みに失敗しました: {articleError}</p>
              </div>
            ) : selectedArticle ? (
              <div className="space-y-4">
                <div>
                  <h3 className="text-lg font-semibold">{selectedArticle.title}</h3>
                  <p className="text-sm text-gray-600 mt-1">
                    投稿日: {selectedArticle.postdate} | ステータス: {selectedArticle.status}
                  </p>
                </div>
                
                <div className="prose prose-sm max-w-none">
                  <div dangerouslySetInnerHTML={{ __html: selectedArticle.content }} />
                </div>
                
                {selectedArticle.keywords && selectedArticle.keywords.length > 0 && (
                  <div>
                    <h4 className="text-sm font-medium mb-2">キーワード:</h4>
                    <div className="flex flex-wrap gap-1">
                      {selectedArticle.keywords.map((keyword, index) => (
                        <span key={index} className="px-2 py-1 bg-gray-100 text-xs rounded">
                          {keyword}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                
                {selectedArticle.target_audience && (
                  <div>
                    <h4 className="text-sm font-medium mb-2">ターゲット:</h4>
                    <p className="text-sm text-gray-700">{selectedArticle.target_audience}</p>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-gray-600">記事を選択してください</p>
            )}
          </div>
          <SheetClose asChild>
            <Button className="mt-6 w-full" variant="outline">
              閉じる
            </Button>
          </SheetClose>
        </SheetContent>
      </Sheet>
    </div>
  );
}
