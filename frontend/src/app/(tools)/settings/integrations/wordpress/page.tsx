"use client";

import { useCallback, useEffect, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  ExternalLink,
  Globe,
  Loader2,
  RefreshCw,
  Star,
  Trash2,
  XCircle,
} from "lucide-react";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@clerk/nextjs";

interface WordPressSite {
  id: string;
  site_url: string;
  site_name: string | null;
  mcp_endpoint: string;
  connection_status: "connected" | "disconnected" | "error";
  is_active: boolean;
  last_connected_at: string | null;
  last_used_at: string | null;
  last_error: string | null;
  created_at: string;
  updated_at: string;
}

export default function WordPressIntegrationPage() {
  const { getToken } = useAuth();
  const [sites, setSites] = useState<WordPressSite[]>([]);
  const [loading, setLoading] = useState(true);
  const [testingId, setTestingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const fetchSites = useCallback(async () => {
    try {
      const token = await getToken();
      const response = await fetch("/api/proxy/blog/sites", {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (response.ok) {
        const data = await response.json();
        setSites(data.sites);
      }
    } catch (error) {
      console.error("Failed to fetch sites:", error);
    } finally {
      setLoading(false);
    }
  }, [getToken]);

  useEffect(() => {
    fetchSites();
  }, [fetchSites]);

  const handleTestConnection = async (siteId: string) => {
    setTestingId(siteId);
    try {
      const token = await getToken();
      const response = await fetch(`/api/proxy/blog/sites/${siteId}/test`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (response.ok) {
        await fetchSites();
      }
    } catch (error) {
      console.error("Connection test failed:", error);
    } finally {
      setTestingId(null);
    }
  };

  const handleDeleteSite = async (siteId: string) => {
    setDeletingId(siteId);
    try {
      const token = await getToken();
      const response = await fetch(`/api/proxy/blog/sites/${siteId}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (response.ok) {
        setSites(sites.filter((site) => site.id !== siteId));
      }
    } catch (error) {
      console.error("Delete failed:", error);
    } finally {
      setDeletingId(null);
    }
  };

  const handleActivateSite = async (siteId: string) => {
    try {
      const token = await getToken();
      const response = await fetch(`/api/proxy/blog/sites/${siteId}/activate`, {
        method: "PATCH",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (response.ok) {
        await fetchSites();
      }
    } catch (error) {
      console.error("Activate failed:", error);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "connected":
        return (
          <Badge variant="default" className="bg-green-500">
            <CheckCircle2 className="w-3 h-3 mr-1" />
            接続済み
          </Badge>
        );
      case "error":
        return (
          <Badge variant="destructive">
            <XCircle className="w-3 h-3 mr-1" />
            エラー
          </Badge>
        );
      default:
        return (
          <Badge variant="secondary">
            <AlertCircle className="w-3 h-3 mr-1" />
            未接続
          </Badge>
        );
    }
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return "—";
    return new Date(dateString).toLocaleString("ja-JP");
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="space-y-2">
        <h1 className="text-3xl font-bold flex items-center gap-2">
          WordPress連携設定
        </h1>
        <p className="text-muted-foreground">
          WordPressサイトとMCPプラグインを連携して、ブログAI機能を利用できます。
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Globe className="w-5 h-5" />
            連携方法
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="bg-muted/50 p-4 rounded-lg space-y-3">
            <h3 className="font-semibold">WordPress MCPプラグインの設定手順</h3>
            <ol className="list-decimal list-inside space-y-2 text-sm text-muted-foreground">
              <li>WordPressの管理画面にログインします</li>
              <li>「プラグイン」→「新規追加」からMCPプラグインをインストール</li>
              <li>プラグインを有効化後、「設定」→「MCP連携」を開きます</li>
              <li>「外部サービスと連携する」ボタンをクリック</li>
              <li>このページに自動的にリダイレクトされ、連携が完了します</li>
            </ol>
          </div>
          <Button variant="outline" asChild>
            <a
              href="https://example.com/wp-mcp-plugin"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2"
            >
              <ExternalLink className="w-4 h-4" />
              MCPプラグインのダウンロード
            </a>
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>連携済みサイト</CardTitle>
          <CardDescription>
            ブログAIで使用できるWordPressサイトの一覧です
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="space-y-4">
              {[1, 2].map((i) => (
                <div
                  key={i}
                  className="flex items-center justify-between p-4 border rounded-lg"
                >
                  <div className="space-y-2">
                    <Skeleton className="h-5 w-48" />
                    <Skeleton className="h-4 w-64" />
                  </div>
                  <Skeleton className="h-9 w-24" />
                </div>
              ))}
            </div>
          ) : sites.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <Globe className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p>連携済みのWordPressサイトはありません</p>
              <p className="text-sm mt-2">
                上記の手順に従ってWordPressサイトを連携してください
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {sites.map((site) => (
                <div
                  key={site.id}
                  className={`flex items-center justify-between p-4 border rounded-lg ${
                    site.is_active ? "border-primary bg-primary/5" : ""
                  }`}
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <h3 className="font-medium">
                        {site.site_name || site.site_url}
                      </h3>
                      {getStatusBadge(site.connection_status)}
                      {site.is_active && (
                        <Badge
                          variant="outline"
                          className="border-primary text-primary"
                        >
                          <Star className="w-3 h-3 mr-1 fill-current" />
                          アクティブ
                        </Badge>
                      )}
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {site.site_url}
                    </p>
                    {site.last_error && (
                      <p className="text-sm text-destructive">
                        エラー: {site.last_error}
                      </p>
                    )}
                    <p className="text-xs text-muted-foreground">
                      最終接続: {formatDate(site.last_connected_at)}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    {!site.is_active && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleActivateSite(site.id)}
                      >
                        <Star className="w-4 h-4 mr-1" />
                        アクティブに設定
                      </Button>
                    )}
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleTestConnection(site.id)}
                      disabled={testingId === site.id}
                    >
                      {testingId === site.id ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <RefreshCw className="w-4 h-4" />
                      )}
                      <span className="ml-1">接続テスト</span>
                    </Button>
                    <AlertDialog>
                      <AlertDialogTrigger asChild>
                        <Button
                          variant="outline"
                          size="sm"
                          className="text-destructive hover:text-destructive"
                          disabled={deletingId === site.id}
                        >
                          {deletingId === site.id ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            <Trash2 className="w-4 h-4" />
                          )}
                        </Button>
                      </AlertDialogTrigger>
                      <AlertDialogContent>
                        <AlertDialogHeader>
                          <AlertDialogTitle>連携を解除しますか？</AlertDialogTitle>
                          <AlertDialogDescription>
                            {site.site_name || site.site_url}
                            との連携を解除します。この操作は取り消せません。
                          </AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                          <AlertDialogCancel>キャンセル</AlertDialogCancel>
                          <AlertDialogAction
                            onClick={() => handleDeleteSite(site.id)}
                            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                          >
                            連携を解除
                          </AlertDialogAction>
                        </AlertDialogFooter>
                      </AlertDialogContent>
                    </AlertDialog>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
