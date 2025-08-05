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
  updateArticleStatus: (articleId: string, status: 'draft' | 'published') => Promise<boolean>;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export interface ArticleStats {
  total_generated: number;
  total_published: number;
  total_draft: number;
  this_month_count: number;
}

interface UseArticleStatsResult {
  stats: ArticleStats | null;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

export function useArticleStats(): UseArticleStatsResult {
  const [stats, setStats] = useState<ArticleStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { getToken } = useAuth();

  const fetchStats = useCallback(async () => {
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

      // 全プロセスを取得して統計を計算
      const response = await fetch(`${API_BASE_URL}/articles/all-processes?limit=1000`, {
        method: "GET",
        headers,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const processes = await response.json();
      
      // 統計を計算
      const articles = processes.filter((p: any) => p.process_type === 'article');
      const totalGenerated = articles.length;
      const totalPublished = articles.filter((a: any) => a.status === 'published').length;
      const totalDraft = articles.filter((a: any) => a.status === 'draft').length;
      
      // 今月の記事数を計算
      const currentMonth = new Date().getMonth();
      const currentYear = new Date().getFullYear();
      const thisMonthCount = articles.filter((a: any) => {
        const createdDate = new Date(a.postdate);
        return createdDate.getMonth() === currentMonth && createdDate.getFullYear() === currentYear;
      }).length;

      const calculatedStats: ArticleStats = {
        total_generated: totalGenerated,
        total_published: totalPublished,
        total_draft: totalDraft,
        this_month_count: thisMonthCount
      };

      setStats(calculatedStats);
    } catch (err) {
      setError(err instanceof Error ? err.message : "統計の取得に失敗しました");
      setStats(null);
    } finally {
      setLoading(false);
    }
  }, [getToken]);

  const refetch = useCallback(async () => {
    await fetchStats();
  }, [fetchStats]);

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  return {
    stats,
    loading,
    error,
    refetch,
  };
}

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

  const updateArticleStatus = useCallback(async (articleId: string, status: 'draft' | 'published'): Promise<boolean> => {
    try {
      const token = await getToken();
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
      };
      
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }

      const response = await fetch(`${API_BASE_URL}/articles/${articleId}/status`, {
        method: "PATCH",
        headers,
        body: JSON.stringify({ status }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      // 成功したらプロセスリストを再取得
      await refetch();
      return true;
    } catch (err) {
      console.error(`Failed to update article status: ${err}`);
      return false;
    }
  }, [getToken, refetch]);

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
    updateArticleStatus,
  };
} 