'use client';

import { useCallback } from 'react';
import { motion } from 'framer-motion';
import { AlertCircle, CheckCircle, Clock, RefreshCw, Wifi, WifiOff } from 'lucide-react';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

interface ConnectionStatusProps {
  isConnected: boolean;
  isConnecting: boolean;
  isSyncing: boolean;
  lastSyncTime?: Date | null;
  error?: string;
  canPerformActions: boolean;
  pendingActionsCount?: number;
  queuedActionsCount?: number;
  onRetry?: () => void;
  onRefresh?: () => void;
  debugMode?: boolean;
  debugInfo?: any;
}

export default function ConnectionStatus({
  isConnected,
  isConnecting,
  isSyncing,
  lastSyncTime,
  error,
  canPerformActions,
  pendingActionsCount = 0,
  queuedActionsCount = 0,
  onRetry,
  onRefresh,
  debugMode = false,
  debugInfo,
}: ConnectionStatusProps) {
  const getConnectionIcon = useCallback(() => {
    if (isConnecting) {
      return <RefreshCw className="w-4 h-4 animate-spin text-blue-500" />;
    }
    if (isConnected) {
      return <Wifi className="w-4 h-4 text-green-500" />;
    }
    return <WifiOff className="w-4 h-4 text-red-500" />;
  }, [isConnected, isConnecting]);

  const getConnectionStatus = useCallback(() => {
    if (isConnecting) return { text: '接続中...', variant: 'secondary' as const };
    if (isConnected && canPerformActions) return { text: '接続済み', variant: 'default' as const };
    if (isConnected && !canPerformActions) return { text: '同期中', variant: 'secondary' as const };
    return { text: '切断', variant: 'destructive' as const };
  }, [isConnected, isConnecting, canPerformActions]);

  const getSyncStatus = useCallback(() => {
    if (isSyncing) return '同期中...';
    if (lastSyncTime) {
      const timeDiff = Date.now() - lastSyncTime.getTime();
      const minutes = Math.floor(timeDiff / 60000);
      const seconds = Math.floor((timeDiff % 60000) / 1000);
      
      if (minutes > 0) {
        return `${minutes}分前に同期`;
      } else {
        return `${seconds}秒前に同期`;
      }
    }
    return '未同期';
  }, [isSyncing, lastSyncTime]);

  const connectionStatus = getConnectionStatus();

  return (
    <div className="space-y-4">
      {/* Main Connection Status */}
      <Card className="border-l-4 border-l-blue-500">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-sm">
            {getConnectionIcon()}
            リアルタイム接続状態
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm">接続状態:</span>
            <Badge variant={connectionStatus.variant}>{connectionStatus.text}</Badge>
          </div>
          
          <div className="flex items-center justify-between">
            <span className="text-sm">データ同期:</span>
            <div className="flex items-center gap-2">
              {isSyncing && <RefreshCw className="w-3 h-3 animate-spin" />}
              <span className="text-xs text-gray-600">{getSyncStatus()}</span>
            </div>
          </div>

          {(pendingActionsCount > 0 || queuedActionsCount > 0) && (
            <div className="flex items-center justify-between">
              <span className="text-sm">待機中の操作:</span>
              <Badge variant="outline">
                {pendingActionsCount + queuedActionsCount}件
              </Badge>
            </div>
          )}

          {(onRetry || onRefresh) && (
            <div className="flex gap-2 pt-2">
              {onRetry && !isConnected && (
                <Button size="sm" variant="outline" onClick={onRetry} disabled={isConnecting}>
                  {isConnecting ? (
                    <>
                      <RefreshCw className="w-3 h-3 mr-1 animate-spin" />
                      再接続中...
                    </>
                  ) : (
                    '再接続'
                  )}
                </Button>
              )}
              {onRefresh && isConnected && (
                <Button size="sm" variant="outline" onClick={onRefresh} disabled={isSyncing}>
                  {isSyncing ? (
                    <>
                      <RefreshCw className="w-3 h-3 mr-1 animate-spin" />
                      同期中...
                    </>
                  ) : (
                    'データ更新'
                  )}
                </Button>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Error Alert */}
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            {error}
          </AlertDescription>
        </Alert>
      )}

      {/* Action Blocking Warning */}
      {!canPerformActions && isConnected && (
        <Alert>
          <Clock className="h-4 w-4" />
          <AlertDescription>
            データ同期中です。操作は同期完了後に実行されます。
          </AlertDescription>
        </Alert>
      )}

      {/* Connection Issue Warning */}
      {!isConnected && !isConnecting && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-4 bg-orange-50 border border-orange-200 rounded-lg"
        >
          <div className="flex items-center gap-2 text-orange-800">
            <WifiOff className="w-4 h-4" />
            <span className="font-medium">接続が切断されました</span>
          </div>
          <p className="text-sm text-orange-700 mt-1">
            リアルタイム機能が利用できません。自動で再接続を試行しています。
          </p>
        </motion.div>
      )}

      {/* Success State */}
      {isConnected && canPerformActions && !error && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-4 bg-green-50 border border-green-200 rounded-lg"
        >
          <div className="flex items-center gap-2 text-green-800">
            <CheckCircle className="w-4 h-4" />
            <span className="font-medium">すべてのシステムが正常に動作しています</span>
          </div>
          <p className="text-sm text-green-700 mt-1">
            リアルタイム機能とデータ同期が有効です。
          </p>
        </motion.div>
      )}

      {/* Debug Information */}
      {debugMode && debugInfo && (
        <Card className="border-dashed">
          <CardHeader>
            <CardTitle className="text-sm">デバッグ情報</CardTitle>
            <CardDescription>開発者向け接続詳細</CardDescription>
          </CardHeader>
          <CardContent>
            <pre className="text-xs bg-gray-100 p-2 rounded overflow-auto">
              {JSON.stringify(debugInfo, null, 2)}
            </pre>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// Utility component for inline status display
export function InlineConnectionStatus({
  isConnected,
  isConnecting,
  canPerformActions,
  compact = false,
}: {
  isConnected: boolean;
  isConnecting: boolean;
  canPerformActions: boolean;
  compact?: boolean;
}) {
  if (compact) {
    return (
      <div className="flex items-center gap-1">
        {isConnecting ? (
          <RefreshCw className="w-3 h-3 animate-spin text-blue-500" />
        ) : isConnected && canPerformActions ? (
          <CheckCircle className="w-3 h-3 text-green-500" />
        ) : (
          <AlertCircle className="w-3 h-3 text-red-500" />
        )}
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2">
      {isConnecting ? (
        <>
          <RefreshCw className="w-4 h-4 animate-spin text-blue-500" />
          <span className="text-sm text-blue-600">接続中...</span>
        </>
      ) : isConnected && canPerformActions ? (
        <>
          <CheckCircle className="w-4 h-4 text-green-500" />
          <span className="text-sm text-green-600">接続済み</span>
        </>
      ) : (
        <>
          <AlertCircle className="w-4 h-4 text-red-500" />
          <span className="text-sm text-red-600">接続エラー</span>
        </>
      )}
    </div>
  );
}