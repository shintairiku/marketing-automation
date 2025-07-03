"use client"

import { useState } from "react";
import { useRouter } from "next/navigation";
import { AlertCircle, BarChart3, Calendar, CheckCircle,Clock, Edit, Eye, Play, User } from "lucide-react";

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
  Drawer,
  DrawerClose,
  DrawerContent,
  DrawerHeader,
  DrawerTitle,
} from "@/components/ui/drawer";
import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useAllProcesses,useArticleDetail, useArticles } from "@/hooks/useArticles";

const PAGE_SIZE = 20;

export default function IndexPage() {
  const router = useRouter();
  const [selectedArticleId, setSelectedArticleId] = useState<string | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>("");

  // 全プロセス（記事+未完成プロセス）を取得
  const {
    processes,
    loading: processesLoading,
    error: processesError,
    currentPage,
    totalPages,
    setPage,
    refetch
  } = useAllProcesses(PAGE_SIZE, statusFilter || undefined);

  // 選択された記事の詳細を取得
  const {
    article: selectedArticle,
    loading: articleLoading,
    error: articleError
  } = useArticleDetail(selectedArticleId);

  const handleRowClick = (articleId: string) => {
    setSelectedArticleId(articleId);
    setDrawerOpen(true);
  };

  const handleFilterApply = (filter: string) => {
    setStatusFilter(filter);
    setPage(1); // Reset to first page when applying filter
  };

  const handleClearFilter = () => {
    setStatusFilter("");
    setPage(1); // Reset to first page when clearing filter
  };

  const handleEditClick = (processItem: any, e: React.MouseEvent) => {
    e.stopPropagation(); // カードクリックイベントを防ぐ
    if (processItem.process_type === 'article') {
      router.push(`/seo/generate/edit-article/${processItem.id}`);
    } else {
      // Generation process - redirect to generation page
      router.push(`/seo/generate/new-article/${processItem.process_id}`);
    }
  };

  const handleResumeClick = (processId: string, e: React.MouseEvent) => {
    e.stopPropagation(); // カードクリックイベントを防ぐ
    router.push(`/seo/generate/new-article/${processId}`);
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
      case 'user_input_required': return '入力待ち';
      case 'paused': return '一時停止';
      case 'error': return 'エラー';
      case 'cancelled': return 'キャンセル';
      case 'resuming': return '再開中';
      default: return status;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'bg-green-100 text-green-800';
      case 'in_progress': return 'bg-blue-100 text-blue-800';
      case 'user_input_required': return 'bg-yellow-100 text-yellow-800';
      case 'paused': return 'bg-gray-100 text-gray-800';
      case 'error': return 'bg-red-100 text-red-800';
      case 'cancelled': return 'bg-gray-100 text-gray-600';
      case 'resuming': return 'bg-purple-100 text-purple-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusIcon = (status: string, processType: string) => {
    if (processType === 'article') {
      return <CheckCircle className="w-4 h-4" />;
    }
    
    switch (status) {
      case 'completed': return <CheckCircle className="w-4 h-4" />;
      case 'in_progress': return <Clock className="w-4 h-4 animate-pulse" />;
      case 'user_input_required': return <AlertCircle className="w-4 h-4" />;
      case 'paused': return <Clock className="w-4 h-4" />;
      case 'error': return <AlertCircle className="w-4 h-4" />;
      case 'resuming': return <Play className="w-4 h-4" />;
      default: return <Clock className="w-4 h-4" />;
    }
  };

  if (processesError) {
    return (
      <div className="space-y-6">
        <Card className="p-4">
          <div className="text-center text-red-600">
            <p>プロセスの読み込み中にエラーが発生しました: {processesError}</p>
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
                    <option value="user_input_required">入力待ち</option>
                    <option value="paused">一時停止</option>
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
      {processesLoading ? (
        <div className="flex justify-center items-center py-16">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900 mx-auto"></div>
            <p className="mt-4 text-lg text-gray-600">プロセスを読み込み中...</p>
          </div>
        </div>
      ) : processes.length === 0 ? (
        <div className="text-center py-16">
          <div className="max-w-md mx-auto">
            <div className="bg-gray-100 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4">
              <Edit className="w-8 h-8 text-gray-600" />
            </div>
            <h3 className="text-xl font-semibold text-gray-900 mb-2">プロセスがありません</h3>
            <p className="text-gray-600">
              {statusFilter ? `「${getStatusDisplay(statusFilter)}」ステータスのプロセスが見つかりません` : "まだプロセスが生成されていません"}
            </p>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {processes.map((process) => (
            <Card 
              key={process.id} 
              className="overflow-hidden hover:shadow-lg transition-shadow duration-200 cursor-pointer bg-white"
              onClick={() => handleRowClick(process.id)}
            >
              {/* カードヘッダー画像風エリア */}
              <div className={`h-48 relative ${process.process_type === 'article' ? 'bg-gradient-to-br from-green-50 to-emerald-100' : 'bg-gradient-to-br from-blue-50 to-indigo-100'}`}>
                <div className="absolute top-4 left-4 flex items-center gap-2">
                  <span className={`px-3 py-1 text-xs font-medium rounded-full flex items-center gap-1 ${getStatusColor(process.status)}`}>
                    {getStatusIcon(process.status, process.process_type)}
                    {getStatusDisplay(process.status)}
                  </span>
                  {process.process_type === 'generation' && (
                    <span className="px-2 py-1 text-xs bg-purple-100 text-purple-700 rounded">
                      プロセス
                    </span>
                  )}
                </div>
                {process.process_type === 'generation' && process.progress_percentage !== undefined && (
                  <div className="absolute top-4 right-4">
                    <div className="text-xs text-gray-600 bg-white/80 px-2 py-1 rounded">
                      {process.progress_percentage}%
                    </div>
                  </div>
                )}
                <div className="absolute bottom-4 left-4 right-4">
                  <h3 className="text-lg font-bold text-gray-900 line-clamp-2 leading-tight">
                    {process.title}
                  </h3>
                </div>
              </div>
              
              {/* カードコンテンツ */}
              <div className="p-6">
                <p className="text-gray-600 text-sm line-clamp-3 mb-4">
                  {process.shortdescription || "概要が設定されていません"}
                </p>
                
                {/* メタ情報 */}
                <div className="space-y-2 mb-4">
                  <div className="flex items-center text-sm text-gray-500">
                    <Calendar className="w-4 h-4 mr-2" />
                    <span>{formatDate(process.postdate)}</span>
                  </div>
                  {process.target_audience && (
                    <div className="flex items-center text-sm text-gray-500">
                      <User className="w-4 h-4 mr-2" />
                      <span className="line-clamp-1">{process.target_audience}</span>
                    </div>
                  )}
                  {process.current_step && process.process_type === 'generation' && (
                    <div className="flex items-center text-sm text-gray-500">
                      <Clock className="w-4 h-4 mr-2" />
                      <span className="line-clamp-1">ステップ: {process.current_step}</span>
                    </div>
                  )}
                </div>
                
                {/* アクションボタン */}
                <div className="flex gap-2">
                  {process.process_type === 'article' ? (
                    <>
                      <Button 
                        size="sm" 
                        className="flex-1 bg-secondary hover:bg-secondary/90"
                        onClick={(e) => handleEditClick(process, e)}
                      >
                        <Edit className="w-4 h-4 mr-1" />
                        編集
                      </Button>
                      <Button 
                        size="sm" 
                        variant="outline" 
                        className="flex-1"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleRowClick(process.id);
                        }}
                      >
                        <Eye className="w-4 h-4 mr-1" />
                        表示
                      </Button>
                    </>
                  ) : (
                    <>
                      {process.is_recoverable ? (
                        <Button 
                          size="sm" 
                          className="flex-1 bg-blue-600 hover:bg-blue-700 text-white"
                          onClick={(e) => handleResumeClick(process.process_id!, e)}
                        >
                          <Play className="w-4 h-4 mr-1" />
                          再開
                        </Button>
                      ) : (
                        <Button 
                          size="sm" 
                          variant="outline" 
                          className="flex-1"
                          onClick={(e) => handleEditClick(process, e)}
                        >
                          <Eye className="w-4 h-4 mr-1" />
                          詳細
                        </Button>
                      )}
                      {process.status === 'error' && (
                        <Button 
                          size="sm" 
                          variant="outline" 
                          className="flex-1 border-red-200 text-red-600 hover:bg-red-50"
                          onClick={(e) => {
                            e.stopPropagation();
                            // エラー詳細を表示するためのアクション
                            handleRowClick(process.id);
                          }}
                        >
                          <AlertCircle className="w-4 h-4 mr-1" />
                          エラー
                        </Button>
                      )}
                    </>
                  )}
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* 下部：ページネーション */}
      {processes.length > 0 && (
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

      {/* ボトムドロワー（記事プレビュー） */}
      <Drawer open={drawerOpen} onOpenChange={setDrawerOpen}>
        <DrawerContent className="h-[90vh] flex flex-col">
          <DrawerHeader className="border-b pb-4">
            <DrawerTitle>記事プレビュー</DrawerTitle>
          </DrawerHeader>
          
          <div className="flex-1 overflow-hidden p-6">
            {articleLoading ? (
              <div className="flex justify-center items-center h-full">
                <div className="text-center">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900 mx-auto"></div>
                  <p className="mt-4 text-lg text-gray-600">記事を読み込み中...</p>
                </div>
              </div>
            ) : articleError ? (
              <div className="flex justify-center items-center h-full">
                <div className="text-center text-red-600">
                  <p className="text-lg">記事の読み込みに失敗しました</p>
                  <p className="text-sm mt-2">{articleError}</p>
                </div>
              </div>
            ) : selectedArticle ? (
              <div className="h-full overflow-y-auto">
                <div className="max-w-4xl mx-auto space-y-6">
                  {/* 記事ヘッダー情報 */}
                  <div className="bg-gray-50 rounded-lg p-6">
                    <h1 className="text-2xl font-bold text-gray-900 mb-3">{selectedArticle.title}</h1>
                    <div className="flex flex-wrap gap-4 text-sm text-gray-600">
                      <span>投稿日: {selectedArticle.postdate}</span>
                      <span>ステータス: {selectedArticle.status}</span>
                      {selectedArticle.target_audience && (
                        <span>ターゲット: {selectedArticle.target_audience}</span>
                      )}
                    </div>
                  </div>
                  
                  {/* キーワード */}
                  {selectedArticle.keywords && selectedArticle.keywords.length > 0 && (
                    <div className="bg-white border rounded-lg p-4">
                      <h4 className="text-sm font-semibold mb-3 text-gray-900">キーワード</h4>
                      <div className="flex flex-wrap gap-2">
                        {selectedArticle.keywords.map((keyword, index) => (
                          <span key={index} className="px-3 py-1 bg-blue-100 text-blue-800 text-sm rounded-full">
                            {keyword}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {/* 記事コンテンツ */}
                  <div className="bg-white border rounded-lg p-6">
                    <h4 className="text-lg font-semibold mb-4 text-gray-900">記事コンテンツ</h4>
                    <div className="prose prose-lg max-w-none">
                      <div 
                        dangerouslySetInnerHTML={{ __html: selectedArticle.content }} 
                        className="leading-relaxed"
                      />
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex justify-center items-center h-full">
                <p className="text-gray-600 text-lg">記事を選択してください</p>
              </div>
            )}
          </div>
          
          {/* フッター */}
          <div className="border-t p-6 bg-gray-50">
            <div className="max-w-4xl mx-auto flex justify-between items-center">
              <div className="text-sm text-gray-600">
                {selectedArticle && (
                  <span>最終更新: {new Date(selectedArticle.postdate).toLocaleDateString('ja-JP')}</span>
                )}
              </div>
              <div className="flex gap-3">
                {selectedArticle && (
                  <Button
                    onClick={() => {
                      // 記事編集ページに遷移
                      const editUrl = `/seo/generate/edit-article/${selectedArticle.id}`;
                      window.open(editUrl, '_blank');
                    }}
                    className="bg-blue-600 hover:bg-blue-700 text-white"
                  >
                    <Edit className="h-4 w-4 mr-2" />
                    編集
                  </Button>
                )}
                <DrawerClose asChild>
                  <Button variant="outline">
                    閉じる
                  </Button>
                </DrawerClose>
              </div>
            </div>
          </div>
        </DrawerContent>
      </Drawer>
    </div>
  );
}
