'use client';

import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@clerk/nextjs';
import { apiClient } from '@/lib/api';

export interface RecoverableProcess {
  id: string;
  title?: string;
  description?: string;
  status: string;
  current_step_name: string;
  progress_percentage: number;
  updated_at: string;
  created_at: string;
  error_message?: string;
  resume_step: string;
  auto_resume_possible: boolean;
  time_since_last_activity: number;
  recovery_notes: string;
  requires_user_input: boolean;
  initial_keywords?: string[];
  target_age_group?: string;
  target_length?: number;
}

interface UseRecoverableProcessesResult {
  recoverableProcesses: RecoverableProcess[];
  isLoading: boolean;
  error: string | null;
  refreshProcesses: () => Promise<void>;
  hasRecoverableProcesses: boolean;
  getMostRecentProcess: () => RecoverableProcess | null;
  getAutoResumableProcesses: () => RecoverableProcess[];
  getUserInputRequiredProcesses: () => RecoverableProcess[];
}

export const useRecoverableProcesses = (): UseRecoverableProcessesResult => {
  const [recoverableProcesses, setRecoverableProcesses] = useState<RecoverableProcess[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { getToken } = useAuth();

  const refreshProcesses = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);

      const token = await getToken();
      if (!token) {
        throw new Error('認証トークンが取得できませんでした');
      }

      const response = await apiClient.getRecoverableProcesses(10, token);
      
      if (response.error) {
        throw new Error(response.error);
      }

      setRecoverableProcesses(response.data || []);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '復帰可能プロセスの取得に失敗しました';
      setError(errorMessage);
      console.error('Failed to fetch recoverable processes:', err);
    } finally {
      setIsLoading(false);
    }
  }, [getToken]);

  // 初回ロード
  useEffect(() => {
    refreshProcesses();
  }, [refreshProcesses]);

  // 最新のプロセスを取得
  const getMostRecentProcess = useCallback((): RecoverableProcess | null => {
    if (recoverableProcesses.length === 0) return null;
    
    // updated_at の降順でソート済みなので、最初の要素を返す
    return recoverableProcesses[0];
  }, [recoverableProcesses]);

  // 自動復帰可能なプロセスを取得
  const getAutoResumableProcesses = useCallback((): RecoverableProcess[] => {
    return recoverableProcesses.filter(process => process.auto_resume_possible);
  }, [recoverableProcesses]);

  // ユーザー入力が必要なプロセスを取得
  const getUserInputRequiredProcesses = useCallback((): RecoverableProcess[] => {
    return recoverableProcesses.filter(process => process.requires_user_input);
  }, [recoverableProcesses]);

  const hasRecoverableProcesses = recoverableProcesses.length > 0;

  return {
    recoverableProcesses,
    isLoading,
    error,
    refreshProcesses,
    hasRecoverableProcesses,
    getMostRecentProcess,
    getAutoResumableProcesses,
    getUserInputRequiredProcesses,
  };
};