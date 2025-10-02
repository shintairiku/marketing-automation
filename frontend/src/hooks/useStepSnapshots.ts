'use client';

import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@clerk/nextjs';
import { apiClient } from '@/lib/api';

export interface StepSnapshot {
  snapshot_id: string;
  step_name: string;
  step_index: number;
  step_category?: string;
  step_description: string;
  created_at: string;
  can_restore: boolean;
  branch_id?: string;
  branch_name?: string;
  is_active_branch?: boolean;
  parent_snapshot_id?: string;
  is_current?: boolean;  // NEW: indicates current position (like git HEAD)
}

export interface RestoreResult {
  success: boolean;
  process_id: string;
  restored_step: string;
  snapshot_id: string;
  message: string;
}

interface UseStepSnapshotsOptions {
  processId: string | null;
  autoFetch?: boolean;
}

export function useStepSnapshots({ processId, autoFetch = true }: UseStepSnapshotsOptions) {
  const { getToken } = useAuth();
  const [snapshots, setSnapshots] = useState<StepSnapshot[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isRestoring, setIsRestoring] = useState(false);

  // スナップショット一覧を取得
  const fetchSnapshots = useCallback(async () => {
    if (!processId) return;

    setIsLoading(true);
    setError(null);

    try {
      const token = await getToken();
      const response = await apiClient.getProcessSnapshots(processId, token || undefined);

      if (response.error) {
        setError(response.error);
        setSnapshots([]);
      } else if (response.data) {
        setSnapshots(response.data);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch snapshots');
      setSnapshots([]);
    } finally {
      setIsLoading(false);
    }
  }, [processId, getToken]);

  // スナップショットから復元
  const restoreFromSnapshot = useCallback(async (snapshotId: string): Promise<RestoreResult | null> => {
    if (!processId) return null;

    setIsRestoring(true);
    setError(null);

    try {
      const token = await getToken();
      const response = await apiClient.restoreFromSnapshot(processId, snapshotId, token || undefined);

      if (response.error) {
        setError(response.error);
        return null;
      }

      // 復元後、スナップショット一覧を再取得
      await fetchSnapshots();

      return response.data || null;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to restore from snapshot');
      return null;
    } finally {
      setIsRestoring(false);
    }
  }, [processId, getToken, fetchSnapshots]);

  // 自動取得
  useEffect(() => {
    if (autoFetch && processId) {
      fetchSnapshots();
    }
  }, [autoFetch, processId, fetchSnapshots]);

  // Realtime更新の購読
  useEffect(() => {
    if (!processId) return;

    // Supabaseクライアントのインポート
    const setupRealtimeSubscription = async () => {
      try {
        const { createClient } = await import('@/lib/supabase/client');
        const supabase = createClient();

        const channel = supabase
          .channel(`snapshots_${processId}`)
          .on(
            'postgres_changes',
            {
              event: 'INSERT',
              schema: 'public',
              table: 'article_generation_step_snapshots',
              filter: `process_id=eq.${processId}`
            },
            (payload) => {
              console.log('📸 New snapshot detected:', payload);
              // 新しいスナップショットが追加されたら再取得
              fetchSnapshots();
            }
          )
          .subscribe();

        return () => {
          supabase.removeChannel(channel);
        };
      } catch (err) {
        console.error('Failed to setup realtime subscription for snapshots:', err);
      }
    };

    const cleanup = setupRealtimeSubscription();

    return () => {
      cleanup.then(fn => fn?.());
    };
  }, [processId, fetchSnapshots]);

  return {
    snapshots,
    isLoading,
    error,
    isRestoring,
    fetchSnapshots,
    restoreFromSnapshot,
  };
}
