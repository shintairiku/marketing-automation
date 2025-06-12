import { useEffect,useState } from 'react';

import { apiClient, ApiResponse } from '@/lib/api';

interface ApiStatus {
  isConnected: boolean;
  isLoading: boolean;
  error: string | null;
  apiInfo: {
    message?: string;
    version?: string;
    status?: string;
  } | null;
}

export function useApiTest() {
  const [status, setStatus] = useState<ApiStatus>({
    isConnected: false,
    isLoading: true,
    error: null,
    apiInfo: null,
  });

  const testConnection = async () => {
    setStatus(prev => ({ ...prev, isLoading: true, error: null }));

    try {
      // まずヘルスチェックを試行
      const healthResponse = await apiClient.healthCheck();
      
      if (healthResponse.data) {
        setStatus({
          isConnected: true,
          isLoading: false,
          error: null,
          apiInfo: {
            message: healthResponse.data.message,
            version: healthResponse.data.version,
            status: healthResponse.data.status,
          },
        });
        return;
      }

      // ヘルスチェックが失敗した場合、ルートエンドポイントを試行
      const rootResponse = await apiClient.getRoot();
      
      if (rootResponse.data) {
        setStatus({
          isConnected: true,
          isLoading: false,
          error: null,
          apiInfo: {
            message: rootResponse.data.message,
          },
        });
        return;
      }

      // 両方失敗した場合
      setStatus({
        isConnected: false,
        isLoading: false,
        error: healthResponse.error || rootResponse.error || 'API接続に失敗しました',
        apiInfo: null,
      });

    } catch (error) {
      setStatus({
        isConnected: false,
        isLoading: false,
        error: error instanceof Error ? error.message : 'Unknown error occurred',
        apiInfo: null,
      });
    }
  };

  useEffect(() => {
    testConnection();
  }, []);

  return {
    ...status,
    testConnection,
  };
}