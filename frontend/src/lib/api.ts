const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
const USE_PROXY = process.env.NODE_ENV === 'production';

export interface ApiResponse<T> {
  data?: T;
  error?: string;
  status: number;
}

export class ApiClient {
  private baseURL: string;

  constructor() {
    this.baseURL = USE_PROXY ? '/api/proxy' : API_BASE_URL;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    const url = `${this.baseURL}${endpoint}`;
    
    const config: RequestInit = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    };

    try {
      const response = await fetch(url, config);
      
      if (!response.ok) {
        return {
          error: `HTTP error! status: ${response.status}`,
          status: response.status,
        };
      }
      
      const data = await response.json();
      return {
        data,
        status: response.status,
      };
    } catch (error) {
      console.error('API request failed:', error);
      return {
        error: error instanceof Error ? error.message : 'Unknown error occurred',
        status: 0,
      };
    }
  }

  async healthCheck() {
    return this.request<{ status: string; message: string; version: string }>('/health');
  }

  async getRoot() {
    return this.request<{ message: string }>('/');
  }

  // 記事関連のAPI（将来の拡張用）
  async getArticles(limit: number = 20, offset: number = 0, token?: string) {
    const headers = token ? { 'Authorization': `Bearer ${token}` } : undefined;
    return this.request<any[]>(`/articles/?limit=${limit}&offset=${offset}`, { headers });
  }

  // 全プロセス取得（完了済み記事 + 進行中プロセス）
  async getAllProcesses(limit: number = 20, offset: number = 0, token?: string, statusFilter?: string) {
    const headers = token ? { 'Authorization': `Bearer ${token}` } : undefined;
    const query = new URLSearchParams();
    query.append('limit', limit.toString());
    query.append('offset', offset.toString());
    if (statusFilter) query.append('status_filter', statusFilter);
    
    return this.request<any[]>(`/articles/all-processes?${query.toString()}`, { headers });
  }

  // 復帰可能プロセス取得
  async getRecoverableProcesses(limit: number = 10, token?: string) {
    const headers = token ? { 'Authorization': `Bearer ${token}` } : undefined;
    return this.request<any[]>(`/articles/recoverable-processes?limit=${limit}`, { headers });
  }

  // 組織関連のAPI
  async getOrganizations() {
    return this.request<any[]>('/organizations/');
  }

  // 記事フロー関連のAPI
  async getArticleFlows() {
    return this.request<any[]>('/article-flows/');
  }
}

export const apiClient = new ApiClient();