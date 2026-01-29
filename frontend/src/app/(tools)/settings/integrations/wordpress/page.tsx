"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  Building2,
  CheckCircle2,
  ExternalLink,
  Globe,
  Loader2,
  RefreshCw,
  Share2,
  Star,
  Trash2,
  User,
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
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth, useUser } from "@clerk/nextjs";

interface WordPressSite {
  id: string;
  site_url: string;
  site_name: string | null;
  mcp_endpoint: string;
  connection_status: "connected" | "disconnected" | "error";
  is_active: boolean;
  user_id: string | null;
  organization_id: string | null;
  organization_name: string | null;
  last_connected_at: string | null;
  last_used_at: string | null;
  last_error: string | null;
  created_at: string;
  updated_at: string;
}

interface Organization {
  id: string;
  name: string;
}

interface SiteGroup {
  key: string;
  label: string;
  icon: "personal" | "org";
  sites: WordPressSite[];
}

export default function WordPressIntegrationPage() {
  const { getToken } = useAuth();
  const { user } = useUser();
  const [sites, setSites] = useState<WordPressSite[]>([]);
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [loading, setLoading] = useState(true);
  const [testingId, setTestingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [updatingOrgId, setUpdatingOrgId] = useState<string | null>(null);

  const currentUserId = user?.id ?? null;

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

  const fetchOrganizations = useCallback(async () => {
    try {
      const response = await fetch("/api/organizations");
      if (response.ok) {
        const data = await response.json();
        setOrganizations(data);
      }
    } catch (error) {
      console.error("Failed to fetch organizations:", error);
    }
  }, []);

  useEffect(() => {
    fetchSites();
    fetchOrganizations();
  }, [fetchSites, fetchOrganizations]);

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

  const handleUpdateOrganization = async (
    siteId: string,
    organizationId: string | null
  ) => {
    setUpdatingOrgId(siteId);
    try {
      const token = await getToken();
      const response = await fetch(
        `/api/proxy/blog/sites/${siteId}/organization`,
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ organization_id: organizationId }),
        }
      );
      if (response.ok) {
        await fetchSites();
      }
    } catch (error) {
      console.error("Organization update failed:", error);
    } finally {
      setUpdatingOrgId(null);
    }
  };

  const siteGroups = useMemo((): SiteGroup[] => {
    const personalSites: WordPressSite[] = [];
    const orgMap = new Map<string, WordPressSite[]>();

    for (const site of sites) {
      if (site.organization_id) {
        const existing = orgMap.get(site.organization_id) || [];
        existing.push(site);
        orgMap.set(site.organization_id, existing);
      } else {
        personalSites.push(site);
      }
    }

    const groups: SiteGroup[] = [];

    if (personalSites.length > 0) {
      groups.push({
        key: "personal",
        label: "個人のサイト",
        icon: "personal",
        sites: personalSites,
      });
    }

    for (const [orgId, orgSites] of orgMap) {
      const orgName =
        orgSites[0]?.organization_name ||
        organizations.find((o) => o.id === orgId)?.name ||
        "不明な組織";
      groups.push({
        key: orgId,
        label: orgName,
        icon: "org",
        sites: orgSites,
      });
    }

    return groups;
  }, [sites, organizations]);

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
    if (!dateString) return "\u2014";
    return new Date(dateString).toLocaleString("ja-JP");
  };

  const isOwnSite = (site: WordPressSite) => {
    return currentUserId && site.user_id === currentUserId;
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
              <li>
                このページに自動的にリダイレクトされ、連携が完了します
              </li>
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
            ブログAIで使用できるWordPressサイトの一覧です。組織に共有すると、メンバー全員がそのサイトを使えます。
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="space-y-6">
              {[1, 2].map((i) => (
                <div key={i} className="space-y-3">
                  <Skeleton className="h-5 w-32" />
                  <div className="flex items-center justify-between p-4 border rounded-lg">
                    <div className="space-y-2">
                      <Skeleton className="h-5 w-48" />
                      <Skeleton className="h-4 w-64" />
                    </div>
                    <Skeleton className="h-9 w-24" />
                  </div>
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
            <div className="space-y-8">
              {siteGroups.map((group) => (
                <div key={group.key} className="space-y-3">
                  {/* Group Header */}
                  <div className="flex items-center gap-2 pb-1 border-b">
                    {group.icon === "personal" ? (
                      <User className="w-4 h-4 text-muted-foreground" />
                    ) : (
                      <Building2 className="w-4 h-4 text-blue-500" />
                    )}
                    <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
                      {group.label}
                    </h3>
                    <Badge variant="secondary" className="text-xs">
                      {group.sites.length}
                    </Badge>
                  </div>

                  {/* Sites in Group */}
                  <div className="space-y-3">
                    {group.sites.map((site) => (
                      <div
                        key={site.id}
                        className={`flex items-center justify-between p-4 border rounded-lg transition-colors ${
                          site.is_active
                            ? "border-primary bg-primary/5"
                            : "hover:bg-muted/30"
                        }`}
                      >
                        <div className="space-y-1 min-w-0 flex-1">
                          <div className="flex items-center gap-2 flex-wrap">
                            <h3 className="font-medium truncate">
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
                            {!isOwnSite(site) && (
                              <Badge variant="secondary" className="text-xs">
                                共有サイト
                              </Badge>
                            )}
                          </div>
                          <p className="text-sm text-muted-foreground truncate">
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
                        <div className="flex items-center gap-2 ml-4 flex-shrink-0">
                          {/* Organization Sharing Dropdown - only for site owners */}
                          {isOwnSite(site) && organizations.length > 0 && (
                            <DropdownMenu>
                              <DropdownMenuTrigger asChild>
                                <Button
                                  variant="outline"
                                  size="sm"
                                  disabled={updatingOrgId === site.id}
                                >
                                  {updatingOrgId === site.id ? (
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                  ) : (
                                    <Share2 className="w-4 h-4" />
                                  )}
                                  <span className="ml-1 hidden sm:inline">共有先</span>
                                </Button>
                              </DropdownMenuTrigger>
                              <DropdownMenuContent align="end">
                                <DropdownMenuLabel>
                                  共有先を変更
                                </DropdownMenuLabel>
                                <DropdownMenuSeparator />
                                <DropdownMenuItem
                                  onClick={() =>
                                    handleUpdateOrganization(site.id, null)
                                  }
                                >
                                  <User className="w-4 h-4 mr-2" />
                                  個人（共有しない）
                                  {!site.organization_id && (
                                    <CheckCircle2 className="w-3 h-3 ml-auto text-green-500" />
                                  )}
                                </DropdownMenuItem>
                                <DropdownMenuSeparator />
                                {organizations.map((org) => (
                                  <DropdownMenuItem
                                    key={org.id}
                                    onClick={() =>
                                      handleUpdateOrganization(
                                        site.id,
                                        org.id
                                      )
                                    }
                                  >
                                    <Building2 className="w-4 h-4 mr-2" />
                                    {org.name}
                                    {site.organization_id === org.id && (
                                      <CheckCircle2 className="w-3 h-3 ml-auto text-green-500" />
                                    )}
                                  </DropdownMenuItem>
                                ))}
                              </DropdownMenuContent>
                            </DropdownMenu>
                          )}

                          {!site.is_active && (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleActivateSite(site.id)}
                            >
                              <Star className="w-4 h-4 mr-1" />
                              <span className="hidden sm:inline">アクティブに設定</span>
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
                            <span className="ml-1 hidden sm:inline">接続テスト</span>
                          </Button>
                          {isOwnSite(site) && (
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
                                  <AlertDialogTitle>
                                    連携を解除しますか？
                                  </AlertDialogTitle>
                                  <AlertDialogDescription>
                                    {site.site_name || site.site_url}
                                    との連携を解除します。この操作は取り消せません。
                                    {site.organization_id && (
                                      <>
                                        <br />
                                        このサイトは組織に共有されています。解除すると組織メンバーも使用できなくなります。
                                      </>
                                    )}
                                  </AlertDialogDescription>
                                </AlertDialogHeader>
                                <AlertDialogFooter>
                                  <AlertDialogCancel>
                                    キャンセル
                                  </AlertDialogCancel>
                                  <AlertDialogAction
                                    onClick={() => handleDeleteSite(site.id)}
                                    className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                                  >
                                    連携を解除
                                  </AlertDialogAction>
                                </AlertDialogFooter>
                              </AlertDialogContent>
                            </AlertDialog>
                          )}
                        </div>
                      </div>
                    ))}
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
