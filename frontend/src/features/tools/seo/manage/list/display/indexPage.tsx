"use client"

import { useState } from "react";

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
import { useArticles, useArticleDetail } from "@/hooks/useArticles";

const PAGE_SIZE = 20;

export default function IndexPage() {
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
      {/* 上部：ボタン群 */}
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

      {/* 中部：カードで囲まれたテーブル */}
      <Card className="p-4">
        {articlesLoading ? (
          <div className="flex justify-center items-center py-8">
            <div className="text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 mx-auto"></div>
              <p className="mt-2 text-sm text-gray-600">記事を読み込み中...</p>
            </div>
          </div>
        ) : articles.length === 0 ? (
          <div className="text-center py-8">
            <p className="text-gray-600">
              {statusFilter ? `「${statusFilter}」ステータスの記事が見つかりません` : "記事がまだありません"}
            </p>
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="py-2 px-2">タイトル</TableHead>
                <TableHead className="py-2 px-2">概要</TableHead>
                <TableHead className="py-2 px-2">投稿日</TableHead>
                <TableHead className="py-2 px-2">ステータス</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {articles.map((article) => (
                <TableRow
                  key={article.id}
                  className="cursor-pointer hover:bg-muted"
                  onClick={() => handleRowClick(article.id)}
                >
                  <TableCell className="py-2 px-2 font-medium">{article.title}</TableCell>
                  <TableCell className="py-2 px-2">{article.shortdescription}</TableCell>
                  <TableCell className="py-2 px-2">{article.postdate}</TableCell>
                  <TableCell className="py-2 px-2">
                    <span className={`px-2 py-1 text-xs rounded-full ${
                      article.status === 'completed' ? 'bg-green-100 text-green-800' :
                      article.status === 'in_progress' ? 'bg-blue-100 text-blue-800' :
                      article.status === 'error' ? 'bg-red-100 text-red-800' :
                      'bg-gray-100 text-gray-800'
                    }`}>
                      {article.status === 'completed' ? '完了' :
                       article.status === 'in_progress' ? '進行中' :
                       article.status === 'error' ? 'エラー' :
                       article.status}
                    </span>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </Card>

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
