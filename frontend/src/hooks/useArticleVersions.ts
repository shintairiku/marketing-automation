'use client';

import { useCallback, useEffect, useState } from 'react';

import { useAuth } from '@clerk/nextjs';

export interface ArticleVersion {
  version_id: string;
  version_number: number;
  title: string;
  change_description: string | null;
  is_current: boolean;
  created_at: string;
  user_id: string;
  metadata: Record<string, any> | null;
}

export interface ArticleVersionDetail extends ArticleVersion {
  article_id: string;
  content: string;
}

interface UseArticleVersionsReturn {
  versions: ArticleVersion[];
  currentVersion: ArticleVersionDetail | null;
  loading: boolean;
  error: string | null;
  saveVersion: (
    title: string,
    content: string,
    changeDescription?: string,
    maxVersions?: number
  ) => Promise<void>;
  getVersion: (versionId: string) => Promise<ArticleVersionDetail | null>;
  restoreVersion: (versionId: string, createNewVersion?: boolean) => Promise<void>;
  navigateVersion: (direction: 'next' | 'previous') => Promise<void>;
  deleteVersion: (versionId: string) => Promise<void>;
  refreshVersions: () => Promise<void>;
}

export function useArticleVersions(articleId: string): UseArticleVersionsReturn {
  const { getToken } = useAuth();
  const [versions, setVersions] = useState<ArticleVersion[]>([]);
  const [currentVersion, setCurrentVersion] = useState<ArticleVersionDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const getHeaders = useCallback(async () => {
    const token = await getToken();
    return {
      'Content-Type': 'application/json',
      ...(token && { Authorization: `Bearer ${token}` }),
    };
  }, [getToken]);

  const refreshVersions = useCallback(async () => {
    if (!articleId) return;

    try {
      setLoading(true);
      setError(null);

      const headers = await getHeaders();

      // Get version history
      const versionsResponse = await fetch(`/api/proxy/articles/${articleId}/versions`, {
        headers,
      });

      if (!versionsResponse.ok) {
        throw new Error('バージョン履歴の取得に失敗しました');
      }

      const versionsData = await versionsResponse.json();
      setVersions(versionsData);

      // Get current version
      const currentResponse = await fetch(`/api/proxy/articles/${articleId}/versions/current`, {
        headers,
      });

      if (currentResponse.ok) {
        const currentData = await currentResponse.json();
        setCurrentVersion(currentData);
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'エラーが発生しました';
      setError(errorMessage);
      console.error('Error fetching versions:', err);
    } finally {
      setLoading(false);
    }
  }, [articleId, getHeaders]);

  const saveVersion = useCallback(
    async (
      title: string,
      content: string,
      changeDescription?: string,
      maxVersions: number = 50
    ) => {
      if (!articleId) return;

      try {
        setError(null);

        const headers = await getHeaders();

        const response = await fetch(`/api/proxy/articles/${articleId}/versions`, {
          method: 'POST',
          headers,
          body: JSON.stringify({
            title,
            content,
            change_description: changeDescription,
            max_versions: maxVersions,
          }),
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({ detail: 'バージョンの保存に失敗しました' }));
          throw new Error(errorData.detail || 'バージョンの保存に失敗しました');
        }

        await refreshVersions();
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'バージョンの保存に失敗しました';
        setError(errorMessage);
        throw err;
      }
    },
    [articleId, getHeaders, refreshVersions]
  );

  const getVersion = useCallback(
    async (versionId: string): Promise<ArticleVersionDetail | null> => {
      if (!articleId) return null;

      try {
        setError(null);

        const headers = await getHeaders();

        const response = await fetch(`/api/proxy/articles/${articleId}/versions/${versionId}`, {
          headers,
        });

        if (!response.ok) {
          throw new Error('バージョンの取得に失敗しました');
        }

        const data = await response.json();
        return data;
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'バージョンの取得に失敗しました';
        setError(errorMessage);
        console.error('Error fetching version:', err);
        return null;
      }
    },
    [articleId, getHeaders]
  );

  const restoreVersion = useCallback(
    async (versionId: string, createNewVersion: boolean = true) => {
      if (!articleId) return;

      try {
        setError(null);

        const headers = await getHeaders();

        const response = await fetch(`/api/proxy/articles/${articleId}/versions/${versionId}/restore`, {
          method: 'POST',
          headers,
          body: JSON.stringify({
            create_new_version: createNewVersion,
          }),
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({ detail: 'バージョンの復元に失敗しました' }));
          throw new Error(errorData.detail || 'バージョンの復元に失敗しました');
        }

        await refreshVersions();
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'バージョンの復元に失敗しました';
        setError(errorMessage);
        throw err;
      }
    },
    [articleId, getHeaders, refreshVersions]
  );

  const navigateVersion = useCallback(
    async (direction: 'next' | 'previous') => {
      if (!articleId) return;

      try {
        setError(null);

        const headers = await getHeaders();

        const response = await fetch(`/api/proxy/articles/${articleId}/versions/navigate`, {
          method: 'POST',
          headers,
          body: JSON.stringify({
            direction,
          }),
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({ detail: 'バージョンのナビゲーションに失敗しました' }));
          throw new Error(errorData.detail || 'バージョンのナビゲーションに失敗しました');
        }

        await refreshVersions();
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'バージョンのナビゲーションに失敗しました';
        setError(errorMessage);
        throw err;
      }
    },
    [articleId, getHeaders, refreshVersions]
  );

  const deleteVersion = useCallback(
    async (versionId: string) => {
      if (!articleId) return;

      try {
        setError(null);

        const headers = await getHeaders();

        const response = await fetch(`/api/proxy/articles/${articleId}/versions/${versionId}`, {
          method: 'DELETE',
          headers,
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({ detail: 'バージョンの削除に失敗しました' }));
          throw new Error(errorData.detail || 'バージョンの削除に失敗しました');
        }

        await refreshVersions();
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'バージョンの削除に失敗しました';
        setError(errorMessage);
        throw err;
      }
    },
    [articleId, getHeaders, refreshVersions]
  );

  // Initial load
  useEffect(() => {
    refreshVersions();
  }, [refreshVersions]);

  return {
    versions,
    currentVersion,
    loading,
    error,
    saveVersion,
    getVersion,
    restoreVersion,
    navigateVersion,
    deleteVersion,
    refreshVersions,
  };
}
