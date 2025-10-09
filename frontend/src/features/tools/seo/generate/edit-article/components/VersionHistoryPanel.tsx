'use client';

import React, { useState } from 'react';
import { formatDistance } from 'date-fns';
import { ja } from 'date-fns/locale';
import { Check, ChevronLeft, ChevronRight, Clock, Eye, RotateCcw, Trash2 } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useToast } from '@/hooks/use-toast';
import { ArticleVersion, ArticleVersionDetail, useArticleVersions } from '@/hooks/useArticleVersions';

interface VersionHistoryPanelProps {
  articleId: string;
  onVersionRestore?: () => void;
}

export default function VersionHistoryPanel({ articleId, onVersionRestore }: VersionHistoryPanelProps) {
  const { versions, currentVersion, loading, error, restoreVersion, navigateVersion, deleteVersion, refreshVersions } =
    useArticleVersions(articleId);

  const { toast } = useToast();

  const [selectedVersion, setSelectedVersion] = useState<ArticleVersionDetail | null>(null);
  const [previewDialogOpen, setPreviewDialogOpen] = useState(false);
  const [restoreDialogOpen, setRestoreDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);

  const currentVersionNumber = currentVersion?.version_number;
  const maxVersionNumber = versions.length > 0 ? Math.max(...versions.map(v => v.version_number)) : 0;
  const canGoBack = currentVersionNumber ? currentVersionNumber > 1 : false;
  const canGoForward = currentVersionNumber ? currentVersionNumber < maxVersionNumber : false;

  const handleNavigate = async (direction: 'next' | 'previous') => {
    try {
      setActionLoading(true);
      await navigateVersion(direction);
      toast({
        title: '成功',
        description: `${direction === 'next' ? '次' : '前'}のバージョンに移動しました`,
      });
      onVersionRestore?.();
    } catch (err) {
      toast({
        title: 'エラー',
        description: err instanceof Error ? err.message : 'ナビゲーションに失敗しました',
        variant: 'destructive',
      });
    } finally {
      setActionLoading(false);
    }
  };

  const handleRestore = async (versionId: string) => {
    try {
      setActionLoading(true);
      await restoreVersion(versionId, true);
      setRestoreDialogOpen(false);
      toast({
        title: '成功',
        description: 'バージョンを復元しました',
      });
      onVersionRestore?.();
    } catch (err) {
      toast({
        title: 'エラー',
        description: err instanceof Error ? err.message : '復元に失敗しました',
        variant: 'destructive',
      });
    } finally {
      setActionLoading(false);
    }
  };

  const handleDelete = async (versionId: string) => {
    try {
      setActionLoading(true);
      await deleteVersion(versionId);
      setDeleteDialogOpen(false);
      toast({
        title: '成功',
        description: 'バージョンを削除しました',
      });
    } catch (err) {
      toast({
        title: 'エラー',
        description: err instanceof Error ? err.message : '削除に失敗しました',
        variant: 'destructive',
      });
    } finally {
      setActionLoading(false);
    }
  };

  const formatDate = (dateString: string) => {
    try {
      const date = new Date(dateString);
      return formatDistance(date, new Date(), { addSuffix: true, locale: ja });
    } catch {
      return dateString;
    }
  };

  return (
    <>
      <Card className="w-full">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Clock className="h-5 w-5" />
                バージョン履歴
              </CardTitle>
              <CardDescription>
                {currentVersion && (
                  <span>
                    現在: バージョン {currentVersion.version_number} / {versions.length}
                  </span>
                )}
              </CardDescription>
            </div>

            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleNavigate('previous')}
                disabled={!canGoBack || actionLoading}
              >
                <ChevronLeft className="h-4 w-4" />
                前へ
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleNavigate('next')}
                disabled={!canGoForward || actionLoading}
              >
                次へ
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </CardHeader>

        <CardContent>
          {loading && !actionLoading ? (
            <div className="flex justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900" />
            </div>
          ) : error ? (
            <div className="text-center py-8 text-red-500">
              <p>{error}</p>
              <Button variant="outline" size="sm" onClick={refreshVersions} className="mt-4">
                再読み込み
              </Button>
            </div>
          ) : versions.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <p>バージョン履歴がありません</p>
            </div>
          ) : (
            <ScrollArea className="h-[400px] pr-4">
              <div className="space-y-2">
                {versions.map((version) => (
                  <div
                    key={version.version_id}
                    className={`p-4 rounded-lg border ${
                      version.is_current
                        ? 'bg-blue-50 border-blue-300'
                        : 'bg-white border-gray-200 hover:border-gray-300'
                    } transition-colors`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-semibold text-sm">
                            バージョン {version.version_number}
                          </span>
                          {version.is_current && (
                            <Badge variant="default" className="text-xs">
                              <Check className="h-3 w-3 mr-1" />
                              現在
                            </Badge>
                          )}
                        </div>
                        <p className="text-xs text-gray-600 mb-2">
                          {version.change_description || '変更なし'}
                        </p>
                        <div className="text-xs text-gray-500">
                          {formatDate(version.created_at)}
                        </div>
                        {version.metadata && (
                          <div className="text-xs text-gray-400 mt-1">
                            {version.metadata.content_length && (
                              <span>{version.metadata.content_length.toLocaleString()} 文字</span>
                            )}
                          </div>
                        )}
                      </div>

                      <div className="flex gap-1 ml-4">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            // プレビュー機能は後で実装
                            toast({
                              title: '開発中',
                              description: 'プレビュー機能は開発中です',
                            });
                          }}
                          disabled={actionLoading}
                        >
                          <Eye className="h-4 w-4" />
                        </Button>

                        {!version.is_current && (
                          <>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => {
                                setSelectedVersion(version as ArticleVersionDetail);
                                setRestoreDialogOpen(true);
                              }}
                              disabled={actionLoading}
                            >
                              <RotateCcw className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => {
                                setSelectedVersion(version as ArticleVersionDetail);
                                setDeleteDialogOpen(true);
                              }}
                              disabled={actionLoading}
                            >
                              <Trash2 className="h-4 w-4 text-red-500" />
                            </Button>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </ScrollArea>
          )}
        </CardContent>
      </Card>

      {/* Restore Confirmation Dialog */}
      <Dialog open={restoreDialogOpen} onOpenChange={setRestoreDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>バージョンを復元</DialogTitle>
            <DialogDescription>
              {selectedVersion && (
                <>
                  バージョン {selectedVersion.version_number} に復元しますか？
                  <br />
                  現在の状態は新しいバージョンとして保存されます。
                </>
              )}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRestoreDialogOpen(false)} disabled={actionLoading}>
              キャンセル
            </Button>
            <Button
              onClick={() => selectedVersion && handleRestore(selectedVersion.version_id)}
              disabled={actionLoading}
            >
              {actionLoading ? '復元中...' : '復元'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>バージョンを削除</DialogTitle>
            <DialogDescription>
              {selectedVersion && (
                <>
                  バージョン {selectedVersion.version_number} を削除しますか？
                  <br />
                  この操作は取り消せません。
                </>
              )}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteDialogOpen(false)} disabled={actionLoading}>
              キャンセル
            </Button>
            <Button
              variant="destructive"
              onClick={() => selectedVersion && handleDelete(selectedVersion.version_id)}
              disabled={actionLoading}
            >
              {actionLoading ? '削除中...' : '削除'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
