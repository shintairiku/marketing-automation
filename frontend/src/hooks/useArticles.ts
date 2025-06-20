import { useCallback, useEffect, useState } from "react";

import { useAuth } from "@clerk/nextjs";

export interface Article {
  id: string;
  title: string;
  shortdescription: string;
  postdate: string;
  status: string;
  keywords: string[];
  target_audience: string;
  updated_at: string;
}

export interface Process {
  id: string;
  process_id?: string;
  title: string;
  shortdescription: string;
  postdate: string;
  status: string;
  process_type: 'article' | 'generation';
  keywords: string[];
  target_audience: string;
  updated_at: string;
  current_step?: string;
  progress_percentage?: number;
  can_resume?: boolean;
  is_recoverable?: boolean;
  error_message?: string;
}

export interface ArticleDetail extends Article {
  content: string;
  created_at: string;
  generation_process_id?: string;
}

interface UseArticlesResult {
  articles: Article[];
  loading: boolean;
  error: string | null;
  total: number;
  currentPage: number;
  totalPages: number;
  setPage: (page: number) => void;
  refetch: () => Promise<void>;
}

interface UseArticleDetailResult {
  article: ArticleDetail | null;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

interface UseAllProcessesResult {
  processes: Process[];
  loading: boolean;
  error: string | null;
  total: number;
  currentPage: number;
  totalPages: number;
  setPage: (page: number) => void;
  refetch: () => Promise<void>;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export function useArticles(pageSize: number = 20, statusFilter?: string): UseArticlesResult {
  const [articles, setArticles] = useState<Article[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [total, setTotal] = useState(0);
  const { getToken } = useAuth();

  const fetchArticles = useCallback(async (page: number) => {
    try {
      setLoading(true);
      setError(null);

      const offset = (page - 1) * pageSize;
      const params = new URLSearchParams({
        limit: pageSize.toString(),
        offset: offset.toString(),
      });

      if (statusFilter) {
        params.append("status_filter", statusFilter);
      }

      // Get auth token from Clerk
      const token = await getToken();
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
      };
      
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }

      const response = await fetch(`${API_BASE_URL}/articles/?${params}`, {
        method: "GET",
        headers,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      setArticles(data);
      
      // For now, we'll estimate total from returned data
      // In a real implementation, the API should return total count
      setTotal(data.length === pageSize ? page * pageSize + 1 : (page - 1) * pageSize + data.length);
    } catch (err) {
      setError(err instanceof Error ? err.message : "記事の取得に失敗しました");
      setArticles([]);
    } finally {
      setLoading(false);
    }
  }, [pageSize, statusFilter, getToken]);

  const setPage = (page: number) => {
    setCurrentPage(page);
  };

  const refetch = useCallback(async () => {
    await fetchArticles(currentPage);
  }, [fetchArticles, currentPage]);

  useEffect(() => {
    fetchArticles(currentPage);
  }, [currentPage, fetchArticles]);

  const totalPages = Math.ceil(total / pageSize);

  return {
    articles,
    loading,
    error,
    total,
    currentPage,
    totalPages,
    setPage,
    refetch,
  };
}

export function useArticleDetail(articleId: string | null): UseArticleDetailResult {
  const [article, setArticle] = useState<ArticleDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { getToken } = useAuth();

  const fetchArticle = useCallback(async (id: string) => {
    try {
      setLoading(true);
      setError(null);

      // Get auth token from Clerk
      const token = await getToken();
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
      };
      
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }

      const response = await fetch(`${API_BASE_URL}/articles/${id}`, {
        method: "GET",
        headers,
      });

      if (!response.ok) {
        if (response.status === 404) {
          throw new Error("記事が見つかりません");
        }
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      setArticle(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "記事の取得に失敗しました");
      setArticle(null);
    } finally {
      setLoading(false);
    }
  }, [getToken]);

  const refetch = useCallback(async () => {
    if (articleId) {
      await fetchArticle(articleId);
    }
  }, [articleId, fetchArticle]);

  useEffect(() => {
    if (articleId) {
      fetchArticle(articleId);
    } else {
      setArticle(null);
      setLoading(false);
      setError(null);
    }
  }, [articleId, fetchArticle]);

  return {
    article,
    loading,
    error,
    refetch,
  };
}

export function useAllProcesses(pageSize: number = 20, statusFilter?: string): UseAllProcessesResult {
  const [processes, setProcesses] = useState<Process[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [total, setTotal] = useState(0);
  const { getToken } = useAuth();

  const fetchProcesses = useCallback(async (page: number) => {
    try {
      setLoading(true);
      setError(null);

      const offset = (page - 1) * pageSize;
      const params = new URLSearchParams({
        limit: pageSize.toString(),
        offset: offset.toString(),
      });

      if (statusFilter) {
        params.append("status_filter", statusFilter);
      }

      // Get auth token from Clerk
      const token = await getToken();
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
      };
      
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }

      const response = await fetch(`${API_BASE_URL}/articles/all-processes?${params}`, {
        method: "GET",
        headers,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      setProcesses(data);
      
      // For now, we'll estimate total from returned data
      // In a real implementation, the API should return total count
      setTotal(data.length === pageSize ? page * pageSize + 1 : (page - 1) * pageSize + data.length);
    } catch (err) {
      setError(err instanceof Error ? err.message : "プロセスの取得に失敗しました");
      setProcesses([]);
    } finally {
      setLoading(false);
    }
  }, [pageSize, statusFilter, getToken]);

  const setPage = (page: number) => {
    setCurrentPage(page);
  };

  const refetch = useCallback(async () => {
    await fetchProcesses(currentPage);
  }, [fetchProcesses, currentPage]);

  useEffect(() => {
    fetchProcesses(currentPage);
  }, [currentPage, fetchProcesses]);

  const totalPages = Math.ceil(total / pageSize);

  return {
    processes,
    loading,
    error,
    total,
    currentPage,
    totalPages,
    setPage,
    refetch,
  };
} 