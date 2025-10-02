'use client';

import { useState, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { History, ChevronDown, ChevronUp, RotateCcw, Clock, MapPin, GitBranch } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { useStepSnapshots, StepSnapshot } from '@/hooks/useStepSnapshots';
import RestoreConfirmDialog from './RestoreConfirmDialog';

interface StepHistoryPanelProps {
  processId: string;
  currentStep?: string;
  onRestoreSuccess?: () => void;
}

// ブランチ構造を表現する型
interface BranchNode {
  branchId: string;
  branchName: string;
  snapshots: StepSnapshot[];
  parentSnapshotId?: string;
  isActive: boolean;
}

export default function StepHistoryPanel({
  processId,
  currentStep,
  onRestoreSuccess
}: StepHistoryPanelProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [selectedSnapshot, setSelectedSnapshot] = useState<StepSnapshot | null>(null);
  const [showRestoreDialog, setShowRestoreDialog] = useState(false);

  const { snapshots, isLoading, error, fetchSnapshots } = useStepSnapshots({
    processId,
    autoFetch: true,
  });

  // ブランチごとにグループ化
  const branches = useMemo(() => {
    const branchMap = new Map<string, BranchNode>();

    snapshots.forEach(snapshot => {
      const branchId = snapshot.branch_id || 'unknown';

      if (!branchMap.has(branchId)) {
        branchMap.set(branchId, {
          branchId,
          branchName: snapshot.branch_name || '不明',
          snapshots: [],
          parentSnapshotId: snapshot.parent_snapshot_id,
          isActive: snapshot.is_active_branch || false
        });
      }

      branchMap.get(branchId)!.snapshots.push(snapshot);
    });

    // 各ブランチのスナップショットを作成日時順にソート
    branchMap.forEach(branch => {
      branch.snapshots.sort((a, b) =>
        new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
      );
    });

    // ブランチを並び替え：メインブランチが最初、その後作成日時順
    return Array.from(branchMap.values()).sort((a, b) => {
      if (a.branchName === 'メインブランチ') return -1;
      if (b.branchName === 'メインブランチ') return 1;

      // 作成日時でソート（最初のスナップショットの作成日時を比較）
      const aTime = new Date(a.snapshots[0]?.created_at || 0).getTime();
      const bTime = new Date(b.snapshots[0]?.created_at || 0).getTime();
      return aTime - bTime;
    });
  }, [snapshots]);

  // スナップショットIDからスナップショットを検索
  const findSnapshotById = (snapshotId: string | undefined): StepSnapshot | undefined => {
    if (!snapshotId) return undefined;
    return snapshots.find(s => s.snapshot_id === snapshotId);
  };

  // 現在地の判定（ステップ名の許容範囲を考慮）
  const isCurrentPosition = (snapshot: StepSnapshot): boolean => {
    if (snapshot.is_current) return true;

    // ステップ名の許容範囲チェック（_ing と _ed の差を許容）
    if (!currentStep) return false;

    const normalizeStep = (step: string) => {
      return step
        .replace(/ing$/, 'ed')
        .replace(/generating$/, 'generated')
        .replace(/proposing$/, 'proposed');
    };

    const normalizedCurrent = normalizeStep(currentStep);
    const normalizedSnapshot = normalizeStep(snapshot.step_name);

    return normalizedCurrent === normalizedSnapshot && snapshot.is_active_branch;
  };

  const handleRestoreClick = (snapshot: StepSnapshot) => {
    setSelectedSnapshot(snapshot);
    setShowRestoreDialog(true);
  };

  const handleRestoreSuccess = () => {
    setShowRestoreDialog(false);
    setSelectedSnapshot(null);
    fetchSnapshots();
    onRestoreSuccess?.();
  };

  const handleRestoreCancel = () => {
    setShowRestoreDialog(false);
    setSelectedSnapshot(null);
  };

  // 日付フォーマット
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffInMinutes = Math.floor((now.getTime() - date.getTime()) / (1000 * 60));

    if (diffInMinutes < 1) return 'たった今';
    if (diffInMinutes < 60) return `${diffInMinutes}分前`;
    if (diffInMinutes < 1440) return `${Math.floor(diffInMinutes / 60)}時間前`;

    return date.toLocaleDateString('ja-JP', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <>
      <Card className="w-full">
        <CardHeader
          className="cursor-pointer hover:bg-accent/50 transition-colors"
          onClick={() => setIsExpanded(!isExpanded)}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <History className="h-5 w-5 text-muted-foreground" />
              <CardTitle className="text-lg">ステップ履歴</CardTitle>
              {snapshots.length > 0 && (
                <Badge variant="secondary" className="ml-2">
                  {snapshots.length}件
                </Badge>
              )}
            </div>
            <Button variant="ghost" size="sm">
              {isExpanded ? (
                <ChevronUp className="h-4 w-4" />
              ) : (
                <ChevronDown className="h-4 w-4" />
              )}
            </Button>
          </div>
        </CardHeader>

        <AnimatePresence>
          {isExpanded && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
            >
              <CardContent className="pt-4">
                {isLoading && (
                  <div className="text-center py-8 text-muted-foreground">
                    読み込み中...
                  </div>
                )}

                {error && (
                  <div className="text-center py-8 text-destructive">
                    {error}
                  </div>
                )}

                {!isLoading && !error && snapshots.length === 0 && (
                  <div className="text-center py-8 text-muted-foreground">
                    まだステップ履歴がありません
                  </div>
                )}

                {!isLoading && !error && branches.length > 0 && (
                  <div className="space-y-6">
                    <div className="text-sm text-muted-foreground mb-4">
                      過去のステップに戻って、異なる選択を試すことができます（ペルソナ・テーマ・アウトラインの3つで分岐可能）
                    </div>

                    {/* ブランチごとに表示 */}
                    {branches.map((branch, branchIndex) => (
                      <div key={branch.branchId} className="space-y-2">
                        {/* ブランチヘッダー */}
                        <div className="flex items-center gap-2 mb-3">
                          <GitBranch className="h-4 w-4 text-muted-foreground" />
                          <span className="font-medium text-sm">
                            {branch.branchName}
                          </span>
                          {branch.isActive && (
                            <Badge variant="default" className="text-xs">
                              進行中
                            </Badge>
                          )}
                        </div>

                        {/* 分岐元の表示 */}
                        {branch.parentSnapshotId && branchIndex > 0 && (() => {
                          const parentSnapshot = findSnapshotById(branch.parentSnapshotId);
                          return (
                            <div className="text-xs text-muted-foreground ml-6 mb-2 flex items-center gap-1.5">
                              <div className="w-3 h-3 border-l-2 border-b-2 border-muted-foreground/30 rounded-bl" />
                              <span>
                                {parentSnapshot
                                  ? `「${parentSnapshot.step_description}」から分岐`
                                  : '上のステップから分岐'}
                              </span>
                            </div>
                          );
                        })()}

                        {/* スナップショット一覧 */}
                        <div className="space-y-2 ml-6">
                          {branch.snapshots.map((snapshot, index) => {
                            const isCurrent = isCurrentPosition(snapshot);

                            return (
                              <motion.div
                                key={snapshot.snapshot_id}
                                initial={{ opacity: 0, x: -10 }}
                                animate={{ opacity: 1, x: 0 }}
                                transition={{ delay: index * 0.03 }}
                                className={`
                                  relative p-3 rounded-lg border transition-all
                                  ${isCurrent
                                    ? 'bg-primary/10 border-primary shadow-md'
                                    : 'bg-card hover:bg-accent/30 border-border'
                                  }
                                `}
                              >
                                <div className="flex items-start justify-between gap-3">
                                  <div className="flex-1 space-y-1.5">
                                    {/* ステップ情報 */}
                                    <div className="flex items-center gap-2 flex-wrap">
                                      {isCurrent && (
                                        <MapPin className="h-4 w-4 text-primary flex-shrink-0" />
                                      )}
                                      <h4 className="font-medium text-sm">
                                        {snapshot.step_description}
                                      </h4>
                                      {isCurrent && (
                                        <Badge variant="default" className="text-xs">
                                          現在地
                                        </Badge>
                                      )}
                                    </div>

                                    {/* タイムスタンプ */}
                                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                      <Clock className="h-3 w-3" />
                                      {formatDate(snapshot.created_at)}
                                    </div>
                                  </div>

                                  {/* 戻るボタン */}
                                  {snapshot.can_restore && !isCurrent && (
                                    <Button
                                      size="sm"
                                      variant="outline"
                                      className="flex-shrink-0"
                                      onClick={() => handleRestoreClick(snapshot)}
                                    >
                                      <RotateCcw className="h-3.5 w-3.5 mr-1" />
                                      戻る
                                    </Button>
                                  )}
                                </div>
                              </motion.div>
                            );
                          })}
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                <Separator className="my-4" />

                <div className="text-xs text-muted-foreground text-center space-y-1">
                  <div>💡 過去のステップに戻って、そこから別の選択をすることができます</div>
                  <div>📝 異なる選択をした場合、元の進行状況も保存されたままになります</div>
                </div>
              </CardContent>
            </motion.div>
          )}
        </AnimatePresence>
      </Card>

      {/* 復元確認ダイアログ */}
      {selectedSnapshot && (
        <RestoreConfirmDialog
          isOpen={showRestoreDialog}
          snapshot={selectedSnapshot}
          processId={processId}
          onSuccess={handleRestoreSuccess}
          onCancel={handleRestoreCancel}
        />
      )}
    </>
  );
}
