'use client';

import { useState } from 'react';
import { AlertTriangle, RotateCcw, Loader2 } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { useStepSnapshots, StepSnapshot } from '@/hooks/useStepSnapshots';

interface RestoreConfirmDialogProps {
  isOpen: boolean;
  snapshot: StepSnapshot;
  processId: string;
  onSuccess: () => void;
  onCancel: () => void;
}

export default function RestoreConfirmDialog({
  isOpen,
  snapshot,
  processId,
  onSuccess,
  onCancel,
}: RestoreConfirmDialogProps) {
  const [error, setError] = useState<string | null>(null);
  const { restoreFromSnapshot, isRestoring } = useStepSnapshots({
    processId,
    autoFetch: false,
  });

  const handleRestore = async () => {
    setError(null);

    try {
      const result = await restoreFromSnapshot(snapshot.snapshot_id);

      if (result?.success) {
        onSuccess();
      } else {
        setError('復元に失敗しました。もう一度お試しください。');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '予期しないエラーが発生しました');
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onCancel()}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <RotateCcw className="h-5 w-5" />
            ステップに戻る
          </DialogTitle>
          <DialogDescription>
            このステップに戻ってもよろしいですか？
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Snapshot information */}
          <div className="rounded-lg bg-muted p-4 space-y-2">
            <div className="font-medium">{snapshot.step_description}</div>
            <div className="text-sm text-muted-foreground">
              作成日時: {new Date(snapshot.created_at).toLocaleString('ja-JP')}
            </div>
            {snapshot.step_index > 1 && (
              <div className="text-sm text-muted-foreground">
                このステップは{snapshot.step_index}回目の実行です
              </div>
            )}
          </div>

          {/* Warning message */}
          <Alert>
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription className="space-y-2">
              <p className="font-medium">復元の影響:</p>
              <ul className="list-disc list-inside space-y-1 text-sm">
                <li>プロセスがこのステップの状態に戻ります</li>
                <li>このステップから再度処理が開始されます</li>
                <li>後続のステップのデータは保持されます（参照可能）</li>
                <li>異なる選択をすることで、新しい結果を試せます</li>
              </ul>
            </AlertDescription>
          </Alert>

          {/* Step-specific instructions */}
          {snapshot.step_category === 'user_input' && (
            <div className="text-sm text-muted-foreground bg-blue-50 dark:bg-blue-950 p-3 rounded-lg">
              💡 このステップでは、選択画面が再表示されます。異なる選択をして、結果を比較できます。
            </div>
          )}

          {snapshot.step_category === 'autonomous' && (
            <div className="text-sm text-muted-foreground bg-green-50 dark:bg-green-950 p-3 rounded-lg">
              ⚙️ このステップに戻ると、自動的に処理が再実行されます。
            </div>
          )}

          {/* Error message */}
          {error && (
            <Alert variant="destructive">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={onCancel}
            disabled={isRestoring}
          >
            キャンセル
          </Button>
          <Button
            onClick={handleRestore}
            disabled={isRestoring}
          >
            {isRestoring ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                復元中...
              </>
            ) : (
              <>
                <RotateCcw className="mr-2 h-4 w-4" />
                このステップに戻る
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
