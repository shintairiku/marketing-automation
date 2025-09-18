'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

interface UseAutoSaveOptions {
  delay: number; // デバウンス遅延時間（ミリ秒）
  enabled: boolean; // 自動保存を有効にするか
  excludeConditions?: string[]; // 除外条件のキー
  maxRetries?: number; // 最大リトライ回数
  retryDelay?: number; // リトライ間隔（ミリ秒）
  excludeKeys?: string[]; // 比較から除外するキー（UI状態など）
  contentExtractor?: (data: any) => string; // コンテンツの抽出関数
}

interface UseAutoSaveReturn {
  isAutoSaving: boolean;
  lastSaved: Date | null;
  error: string | null;
  saveCount: number;
  retryCount: number;
  isRetrying: boolean;
  clearError: () => void;
  retryNow: () => void;
}

// ユーティリティ関数: オブジェクトから指定されたキーを除外
function excludeKeysFromObject(obj: any, keysToExclude: string[]): any {
  if (typeof obj !== 'object' || obj === null) return obj;
  
  if (Array.isArray(obj)) {
    return obj.map(item => excludeKeysFromObject(item, keysToExclude));
  }
  
  const result: any = {};
  for (const [key, value] of Object.entries(obj)) {
    if (!keysToExclude.includes(key)) {
      result[key] = excludeKeysFromObject(value, keysToExclude);
    }
  }
  return result;
}

// ユーティリティ関数: コンテンツハッシュを生成
function generateContentHash(content: string): string {
  let hash = 0;
  for (let i = 0; i < content.length; i++) {
    const char = content.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash; // 32bit integer
  }
  return hash.toString();
}

export function useAutoSave<T>(
  data: T,
  saveFunction: () => Promise<void>,
  options: UseAutoSaveOptions
): UseAutoSaveReturn {
  const {
    delay,
    enabled,
    excludeConditions = [],
    maxRetries = 3,
    retryDelay = 1000,
    excludeKeys = ['isEditing', 'isSelected', 'isHovered'],
    contentExtractor
  } = options;

  const [isAutoSaving, setIsAutoSaving] = useState(false);
  const [lastSaved, setLastSaved] = useState<Date | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saveCount, setSaveCount] = useState(0);
  const [retryCount, setRetryCount] = useState(0);
  const [isRetrying, setIsRetrying] = useState(false);

  // デバウンスタイマーのref
  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);
  // リトライタイマーのref
  const retryTimerRef = useRef<NodeJS.Timeout | null>(null);
  // 前回のデータを保存するref（変更検知用）
  const previousDataRef = useRef<T>(data);
  // 前回のコンテンツハッシュを保存
  const previousContentHashRef = useRef<string>('');
  // 初回実行を防ぐためのref
  const isInitializedRef = useRef(false);
  // 最後に失敗したデータを保存（リトライ用）
  const lastFailedDataRef = useRef<T | null>(null);

  const clearError = useCallback(() => {
    setError(null);
    setRetryCount(0);
    lastFailedDataRef.current = null;
  }, []);

  // 実際の保存処理（リトライ対応）
  const performSave = useCallback(async (currentRetryCount: number = 0): Promise<void> => {
    if (!enabled) return;

    try {
      setIsAutoSaving(true);
      if (currentRetryCount > 0) {
        setIsRetrying(true);
      }
      
      console.log(`自動保存を実行中... ${currentRetryCount > 0 ? `(リトライ ${currentRetryCount}/${maxRetries})` : ''}`);
      await saveFunction();
      
      // 成功した場合、エラー状態をクリア
      setLastSaved(new Date());
      setSaveCount(prev => prev + 1);
      setError(null);
      setRetryCount(0);
      lastFailedDataRef.current = null;
      console.log('自動保存が完了しました');
      
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '自動保存中にエラーが発生しました';
      console.error('自動保存エラー:', errorMessage, `(試行回数: ${currentRetryCount + 1})`);
      
      if (currentRetryCount < maxRetries) {
        // リトライ可能な場合
        setRetryCount(currentRetryCount + 1);
        lastFailedDataRef.current = data;
        
        // エクスポネンシャルバックオフでリトライ
        const backoffDelay = retryDelay * Math.pow(2, currentRetryCount);
        console.log(`${backoffDelay}ms後にリトライします...`);
        
        retryTimerRef.current = setTimeout(() => {
          performSave(currentRetryCount + 1);
        }, backoffDelay);
      } else {
        // 最大リトライ回数に達した場合
        setError(`${errorMessage} (${maxRetries + 1}回試行後も失敗)`);
        setRetryCount(currentRetryCount + 1);
        lastFailedDataRef.current = data;
      }
    } finally {
      setIsAutoSaving(false);
      setIsRetrying(false);
    }
  }, [enabled, saveFunction, maxRetries, retryDelay, data]);

  // データの変更を検知して自動保存をトリガーする関数
  const triggerAutoSave = useCallback(async () => {
    // 既存のリトライタイマーをクリア
    if (retryTimerRef.current) {
      clearTimeout(retryTimerRef.current);
      retryTimerRef.current = null;
    }
    
    // エラー状態をリセット（新しい変更があった場合）
    setError(null);
    setRetryCount(0);
    
    await performSave(0);
  }, [performSave]);

  // 手動リトライ関数
  const retryNow = useCallback(async () => {
    if (!lastFailedDataRef.current) return;
    
    console.log('手動リトライを実行します...');
    
    // 既存のリトライタイマーをクリア
    if (retryTimerRef.current) {
      clearTimeout(retryTimerRef.current);
      retryTimerRef.current = null;
    }
    
    await performSave(0);
  }, [performSave]);

  // データの変更を監視
  useEffect(() => {
    // 初回実行時はスキップ
    if (!isInitializedRef.current) {
      isInitializedRef.current = true;
      previousDataRef.current = data;
      
      // 初回のコンテンツハッシュを計算
      const initialContent = contentExtractor ? contentExtractor(data) : JSON.stringify(excludeKeysFromObject(data, excludeKeys));
      previousContentHashRef.current = generateContentHash(initialContent);
      return;
    }

    // 自動保存が無効な場合はスキップ
    if (!enabled) {
      previousDataRef.current = data;
      return;
    }

    // より効率的な変更検知：UI状態を除外してコンテンツのみを比較
    let hasChanged = false;
    let changeDescription = '';
    
    if (contentExtractor) {
      // カスタムコンテンツ抽出関数がある場合
      const currentContent = contentExtractor(data);
      const previousContent = contentExtractor(previousDataRef.current);
      const currentHash = generateContentHash(currentContent);
      
      if (currentHash !== previousContentHashRef.current) {
        hasChanged = true;
        changeDescription = 'コンテンツの変更';
        previousContentHashRef.current = currentHash;
      }
    } else {
      // デフォルト：UI状態を除外した比較
      const currentDataFiltered = excludeKeysFromObject(data, excludeKeys);
      const previousDataFiltered = excludeKeysFromObject(previousDataRef.current, excludeKeys);
      
      const currentContent = JSON.stringify(currentDataFiltered);
      const previousContent = JSON.stringify(previousDataFiltered);
      const currentHash = generateContentHash(currentContent);
      
      if (currentHash !== previousContentHashRef.current) {
        hasChanged = true;
        changeDescription = 'データの変更';
        previousContentHashRef.current = currentHash;
      }
    }
    
    if (hasChanged) {
      
      // 既存のタイマーをクリア
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }

      // 新しいデバウンスタイマーを設定
      debounceTimerRef.current = setTimeout(() => {
        triggerAutoSave();
      }, delay);
    }

    // 前回のデータを更新（UI状態含む）
    previousDataRef.current = data;

    // クリーンアップ関数
    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
      if (retryTimerRef.current) {
        clearTimeout(retryTimerRef.current);
      }
    };
  }, [data, enabled, delay, triggerAutoSave, contentExtractor, excludeKeys]);

  // コンポーネントがアンマウントされる時のクリーンアップ
  useEffect(() => {
    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
      if (retryTimerRef.current) {
        clearTimeout(retryTimerRef.current);
      }
    };
  }, []);

  return {
    isAutoSaving,
    lastSaved,
    error,
    saveCount,
    retryCount,
    isRetrying,
    clearError,
    retryNow
  };
}
