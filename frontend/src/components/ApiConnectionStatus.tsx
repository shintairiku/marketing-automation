'use client';

import { 
  IoCheckmarkCircle, 
  IoInformationCircle, 
  IoRefresh, 
  IoWarning} from 'react-icons/io5';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useApiTest } from '@/hooks/useApiTest';

export function ApiConnectionStatus() {
  const { isConnected, isLoading, error, apiInfo, testConnection } = useApiTest();

  const getStatusColor = () => {
    if (isLoading) return 'text-blue-600';
    if (isConnected) return 'text-green-600';
    return 'text-red-600';
  };

  const getStatusIcon = () => {
    if (isLoading) return <IoRefresh className="animate-spin" size={20} />;
    if (isConnected) return <IoCheckmarkCircle size={20} />;
    return <IoWarning size={20} />;
  };

  const getStatusText = () => {
    if (isLoading) return 'API接続を確認中...';
    if (isConnected) return 'API接続正常';
    return 'API接続エラー';
  };

  return (
    <Card className="bg-white shadow-lg">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <IoInformationCircle className="text-blue-500" size={24} />
            API接続状況
          </CardTitle>
          <Button
            variant="outline"
            size="sm"
            onClick={testConnection}
            disabled={isLoading}
          >
            <IoRefresh className={isLoading ? 'animate-spin mr-2' : 'mr-2'} size={16} />
            再テスト
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center gap-3">
          <div className={getStatusColor()}>
            {getStatusIcon()}
          </div>
          <span className={`font-medium ${getStatusColor()}`}>
            {getStatusText()}
          </span>
        </div>

        {apiInfo && (
          <div className="bg-green-50 border border-green-200 rounded-lg p-3">
            <h4 className="font-medium text-green-800 mb-2">API情報</h4>
            <div className="space-y-1 text-sm text-green-700">
              {apiInfo.message && (
                <p><span className="font-medium">メッセージ:</span> {apiInfo.message}</p>
              )}
              {apiInfo.version && (
                <p><span className="font-medium">バージョン:</span> {apiInfo.version}</p>
              )}
              {apiInfo.status && (
                <p><span className="font-medium">ステータス:</span> {apiInfo.status}</p>
              )}
            </div>
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3">
            <h4 className="font-medium text-red-800 mb-2">エラー詳細</h4>
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        <div className="text-xs text-gray-500">
          <p>API URL: {process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8080'}</p>
        </div>
      </CardContent>
    </Card>
  );
}