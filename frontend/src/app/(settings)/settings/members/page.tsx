"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  AlertTriangle,
  ExternalLink,
  Loader2,
  Mail,
  Plus,
  RefreshCw,
  Trash2,
  Users,
  X,
} from "lucide-react";
import { toast } from "sonner";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { hasPrivilegedRole } from "@/lib/subscription";
import { useUser } from "@clerk/nextjs";

// ============================================
// 型定義
// ============================================
interface Organization {
  id: string;
  name: string;
  owner_user_id: string;
  stripe_customer_id: string | null;
  created_at: string;
  updated_at: string;
}

interface OrgMember {
  organization_id: string;
  user_id: string;
  role: "owner" | "admin" | "member";
  display_name: string | null;
  email: string | null;
  joined_at: string;
}

interface Invitation {
  id: string;
  organization_id: string;
  email: string;
  role: string;
  status: string;
  token?: string;
  expires_at: string | null;
  created_at: string | null;
}

interface OrgSubscriptionInfo {
  id: string;
  organization_id: string;
  status: string;
  quantity: number;
  current_period_end: string | null;
}

// ============================================
// API ヘルパー
// ============================================
async function apiFetch(path: string, options?: RequestInit) {
  const res = await fetch(`/api/organizations${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(err.detail || err.error || `HTTP ${res.status}`);
  }
  return res.json();
}

// ============================================
// ロールのバッジ色
// ============================================
function roleBadgeVariant(role: string): "default" | "secondary" | "outline" {
  switch (role) {
    case "owner":
      return "default";
    case "admin":
      return "secondary";
    default:
      return "outline";
  }
}

function roleLabel(role: string): string {
  switch (role) {
    case "owner":
      return "オーナー";
    case "admin":
      return "管理者";
    case "member":
      return "メンバー";
    default:
      return role;
  }
}

// ============================================
// メイン コンポーネント
// ============================================
export default function MembersSettingsPage() {
  const { user } = useUser();
  const router = useRouter();

  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [selectedOrg, setSelectedOrg] = useState<Organization | null>(null);
  const [members, setMembers] = useState<OrgMember[]>([]);
  const [invitations, setInvitations] = useState<Invitation[]>([]);
  const [orgSubscription, setOrgSubscription] = useState<OrgSubscriptionInfo | null>(null);
  const [loading, setLoading] = useState(true);

  // 招待フォーム
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState<string>("member");
  const [inviting, setInviting] = useState(false);

  // 組織作成（特権ユーザー用）
  const [orgName, setOrgName] = useState("");
  const [creatingOrg, setCreatingOrg] = useState(false);

  const isPrivileged = hasPrivilegedRole(user?.publicMetadata as Record<string, unknown>);

  // ============================================
  // データ取得
  // ============================================
  const fetchOrganizations = useCallback(async () => {
    try {
      const data: Organization[] = await apiFetch("");
      setOrganizations(data);
      if (data.length > 0 && !selectedOrg) {
        setSelectedOrg(data[0]);
      }
    } catch (e) {
      console.error("Failed to fetch organizations:", e);
    }
  }, [selectedOrg]);

  const fetchOrgDetails = useCallback(async () => {
    if (!selectedOrg) return;
    try {
      const [membersData, subData] = await Promise.all([
        apiFetch(`/${selectedOrg.id}/members`),
        apiFetch(`/${selectedOrg.id}/subscription`).catch(() => null),
      ]);

      setMembers(membersData);
      setOrgSubscription(subData);
    } catch (e) {
      console.error("Failed to fetch org details:", e);
    }
  }, [selectedOrg]);

  const fetchInvitations = useCallback(async () => {
    if (!selectedOrg) return;
    try {
      const data: Invitation[] = await apiFetch(`/${selectedOrg.id}/invitations`);
      setInvitations(data);
    } catch (e) {
      console.error("Failed to fetch invitations:", e);
    }
  }, [selectedOrg]);

  useEffect(() => {
    setLoading(true);
    fetchOrganizations().finally(() => setLoading(false));
  }, [fetchOrganizations]);

  useEffect(() => {
    if (selectedOrg) {
      fetchOrgDetails();
      fetchInvitations();
    }
  }, [selectedOrg, fetchOrgDetails, fetchInvitations]);

  // ============================================
  // アクション
  // ============================================
  const handleInvite = async () => {
    if (!inviteEmail.trim() || !selectedOrg) return;
    setInviting(true);
    try {
      await apiFetch(`/${selectedOrg.id}/invitations`, {
        method: "POST",
        body: JSON.stringify({ email: inviteEmail.trim(), role: inviteRole }),
      });
      setInviteEmail("");
      toast.success(`${inviteEmail} に招待メールを送信しました`);
      fetchInvitations();
    } catch (e: unknown) {
      toast.error(`招待の送信に失敗しました: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setInviting(false);
    }
  };

  const handleCreateOrg = async () => {
    if (!orgName.trim()) return;
    setCreatingOrg(true);
    try {
      const res = await fetch("/api/organizations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: orgName.trim() }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ error: "Failed" }));
        throw new Error(err.error || err.detail || `HTTP ${res.status}`);
      }
      setOrgName("");
      toast.success("組織を作成しました");
      fetchOrganizations();
    } catch (e: unknown) {
      toast.error(`組織の作成に失敗しました: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setCreatingOrg(false);
    }
  };

  const [resending, setResending] = useState<string | null>(null);
  const [revoking, setRevoking] = useState<string | null>(null);

  const handleResendInvitation = async (invitationId: string) => {
    if (!selectedOrg) return;
    setResending(invitationId);
    try {
      await fetch(`/api/organizations/${selectedOrg.id}/invitations/${invitationId}`, {
        method: "POST",
      }).then(async (res) => {
        if (!res.ok) {
          const err = await res.json().catch(() => ({ error: "Failed" }));
          throw new Error(err.error || `HTTP ${res.status}`);
        }
      });
      toast.success("招待メールを再送しました");
      fetchInvitations();
    } catch (e: unknown) {
      toast.error(`再送に失敗しました: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setResending(null);
    }
  };

  const handleRevokeInvitation = async (invitationId: string) => {
    if (!selectedOrg) return;
    setRevoking(invitationId);
    try {
      await fetch(`/api/organizations/${selectedOrg.id}/invitations/${invitationId}`, {
        method: "DELETE",
      }).then(async (res) => {
        if (!res.ok) {
          const err = await res.json().catch(() => ({ error: "Failed" }));
          throw new Error(err.error || `HTTP ${res.status}`);
        }
      });
      toast.success("招待を取り消しました");
      fetchInvitations();
    } catch (e: unknown) {
      toast.error(`取り消しに失敗しました: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setRevoking(null);
    }
  };

  const handleRemoveMember = async (memberId: string) => {
    if (!selectedOrg) return;
    try {
      await apiFetch(`/${selectedOrg.id}/members/${memberId}`, {
        method: "DELETE",
      });
      setMembers((prev) => prev.filter((m) => m.user_id !== memberId));
      toast.success("メンバーを削除しました");
    } catch (e: unknown) {
      toast.error(`メンバーの削除に失敗しました: ${e instanceof Error ? e.message : String(e)}`);
    }
  };

  // ============================================
  // 算出値
  // ============================================
  const currentUserId = user?.id;
  const isOwner = selectedOrg?.owner_user_id === currentUserId;
  const isAdmin = members.some(
    (m) => m.user_id === currentUserId && (m.role === "owner" || m.role === "admin")
  );
  const canManage = isOwner || isAdmin;

  const hasActiveTeamPlan = orgSubscription?.status === "active";
  const totalSeats = orgSubscription?.quantity || 0;
  const usedSeats = members.length;
  const remainingSeats = Math.max(0, totalSeats - usedSeats);

  // ============================================
  // レンダリング
  // ============================================
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-4 md:p-6 space-y-4 md:space-y-6 max-w-4xl">
      <div className="space-y-2">
        <h1 className="text-3xl font-bold">メンバー設定</h1>
        <p className="text-muted-foreground">
          チームメンバーの管理と招待を行えます。
        </p>
      </div>

      {/* 状態A: 組織なし */}
      {organizations.length === 0 ? (
        isPrivileged ? (
          /* 特権ユーザー: 組織作成フォーム */
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Users className="h-5 w-5" />
                組織を作成
              </CardTitle>
              <CardDescription>
                組織を作成して、メンバーを招待したりWordPressサイトを共有できます。
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex flex-col gap-2 sm:flex-row sm:gap-3">
                <Input
                  type="text"
                  placeholder="組織名"
                  value={orgName}
                  onChange={(e) => setOrgName(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && orgName.trim() && handleCreateOrg()}
                  className="flex-1"
                />
                <Button
                  onClick={handleCreateOrg}
                  disabled={creatingOrg || !orgName.trim()}
                >
                  {creatingOrg ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <>
                      <Plus className="h-4 w-4 mr-1" />
                      作成
                    </>
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>
        ) : (
          /* 一般ユーザー: チームプラン購入を促す */
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Users className="h-5 w-5" />
                チームプラン
              </CardTitle>
              <CardDescription>
                チームでBlogAIを利用するには、チームプランの購入が必要です。
                チームプランを購入すると、組織が自動的に作成され、メンバーを招待できるようになります。
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button onClick={() => router.push("/settings/billing")} className="gap-2">
                <ExternalLink className="h-4 w-4" />
                チームプランを購入する
              </Button>
            </CardContent>
          </Card>
        )
      ) : (
        <>
          {/* 組織選択（複数所属の場合） */}
          {organizations.length > 1 && (
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center gap-3">
                  <label className="text-sm font-medium">組織:</label>
                  <Select
                    value={selectedOrg?.id || ""}
                    onValueChange={(id) => {
                      const org = organizations.find((o) => o.id === id);
                      if (org) setSelectedOrg(org);
                    }}
                  >
                    <SelectTrigger className="w-full sm:w-[300px]">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {organizations.map((org) => (
                        <SelectItem key={org.id} value={org.id}>
                          {org.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </CardContent>
            </Card>
          )}

          {/* プラン状況 */}
          <Card>
            <CardHeader>
              <CardTitle>プラン状況</CardTitle>
            </CardHeader>
            <CardContent>
              {hasActiveTeamPlan ? (
                <>
                  <div className="grid grid-cols-3 gap-4">
                    <div className="text-center p-4 rounded-lg bg-muted/50">
                      <div className="text-3xl font-bold">{totalSeats}</div>
                      <div className="text-sm text-muted-foreground mt-1">シート数</div>
                    </div>
                    <div className="text-center p-4 rounded-lg bg-muted/50">
                      <div className="text-3xl font-bold">{usedSeats}</div>
                      <div className="text-sm text-muted-foreground mt-1">使用中</div>
                    </div>
                    <div className="text-center p-4 rounded-lg bg-muted/50">
                      <div className="text-3xl font-bold text-green-600">{remainingSeats}</div>
                      <div className="text-sm text-muted-foreground mt-1">残り</div>
                    </div>
                  </div>
                  {orgSubscription?.current_period_end && (
                    <p className="text-sm text-muted-foreground mt-3">
                      次回更新日: {new Date(orgSubscription.current_period_end).toLocaleDateString("ja-JP")}
                    </p>
                  )}
                </>
              ) : (
                <div className="flex items-center gap-3 p-4 rounded-lg bg-yellow-50 border border-yellow-200">
                  <AlertTriangle className="h-5 w-5 text-yellow-600 shrink-0" />
                  <div className="flex-1">
                    <p className="font-medium text-yellow-800">
                      {orgSubscription
                        ? `チームプランのステータス: ${orgSubscription.status}`
                        : "チームプランが有効ではありません"}
                    </p>
                    <p className="text-sm text-yellow-700 mt-1">
                      メンバーの招待にはアクティブなチームプランが必要です。
                    </p>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => router.push("/settings/billing")}
                    className="shrink-0 gap-1"
                  >
                    <ExternalLink className="h-3.5 w-3.5" />
                    プランを更新
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>

          {/* メンバー一覧 */}
          <Card>
            <CardHeader>
              <CardTitle>メンバー一覧</CardTitle>
              <CardDescription>
                {selectedOrg?.name} のメンバー ({members.length}人)
              </CardDescription>
            </CardHeader>
            <CardContent>
              {members.length === 0 ? (
                <p className="text-muted-foreground text-center py-8">メンバーはまだいません</p>
              ) : (
                <div className="overflow-x-auto -mx-4 px-4 sm:mx-0 sm:px-0">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>メンバー</TableHead>
                      <TableHead>ロール</TableHead>
                      <TableHead>参加日</TableHead>
                      {canManage && <TableHead className="w-[80px]" />}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {members.map((member) => (
                      <TableRow key={member.user_id}>
                        <TableCell>
                          <div className="flex items-center gap-3">
                            <Avatar className="h-8 w-8">
                              <AvatarFallback className="text-xs">
                                {(member.display_name || member.email || "?")[0].toUpperCase()}
                              </AvatarFallback>
                            </Avatar>
                            <div>
                              <div className="font-medium">
                                {member.display_name || "名前未設定"}
                                {member.user_id === currentUserId && (
                                  <span className="text-muted-foreground ml-1">(あなた)</span>
                                )}
                              </div>
                              <div className="text-sm text-muted-foreground">
                                {member.email || "メール未設定"}
                              </div>
                            </div>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant={roleBadgeVariant(member.role)}>
                            {roleLabel(member.role)}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground">
                          {new Date(member.joined_at).toLocaleDateString("ja-JP")}
                        </TableCell>
                        {canManage && (
                          <TableCell>
                            {member.role !== "owner" && member.user_id !== currentUserId && (
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-8 w-8 text-destructive hover:text-destructive"
                                onClick={() => handleRemoveMember(member.user_id)}
                              >
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            )}
                          </TableCell>
                        )}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
                </div>
              )}
            </CardContent>
          </Card>

          {/* 招待フォーム — アクティブなチームプランが必要 */}
          {canManage && (
            <Card>
              <CardHeader>
                <CardTitle>メンバーを招待</CardTitle>
                <CardDescription>
                  {hasActiveTeamPlan ? (
                    remainingSeats === 0 ? (
                      <span className="text-yellow-600">
                        シートに空きがありません。シートの追加購入が必要です。
                      </span>
                    ) : (
                      `メールアドレスを入力して招待メールを送信します。残り${remainingSeats}シート`
                    )
                  ) : (
                    <span className="text-muted-foreground">
                      メンバーの招待にはアクティブなチームプランが必要です。
                    </span>
                  )}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex flex-col gap-2 sm:flex-row sm:gap-3">
                  <Input
                    type="email"
                    placeholder="メールアドレス"
                    value={inviteEmail}
                    onChange={(e) => setInviteEmail(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && hasActiveTeamPlan && remainingSeats > 0 && handleInvite()}
                    className="flex-1"
                    disabled={!hasActiveTeamPlan}
                  />
                  <Select value={inviteRole} onValueChange={setInviteRole} disabled={!hasActiveTeamPlan}>
                    <SelectTrigger className="w-[120px]">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="member">メンバー</SelectItem>
                      <SelectItem value="admin">管理者</SelectItem>
                    </SelectContent>
                  </Select>
                  <Button
                    onClick={handleInvite}
                    disabled={inviting || !inviteEmail.trim() || !hasActiveTeamPlan || remainingSeats === 0}
                  >
                    {inviting ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <>
                        <Plus className="h-4 w-4 mr-1" />
                        招待
                      </>
                    )}
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}

          {/* 保留中の招待 */}
          {invitations.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>保留中の招待</CardTitle>
                <CardDescription>
                  招待メールが届いていない場合は再送できます
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto -mx-4 px-4 sm:mx-0 sm:px-0">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>メールアドレス</TableHead>
                      <TableHead>ロール</TableHead>
                      <TableHead>有効期限</TableHead>
                      <TableHead className="w-[120px]" />
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {invitations.map((inv) => (
                      <TableRow key={inv.id}>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <Mail className="h-4 w-4 text-muted-foreground shrink-0" />
                            {inv.email}
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline">{roleLabel(inv.role)}</Badge>
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground">
                          {inv.expires_at
                            ? new Date(inv.expires_at).toLocaleDateString("ja-JP")
                            : "-"}
                        </TableCell>
                        <TableCell>
                          {canManage && (
                            <div className="flex items-center gap-1">
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-8 w-8"
                                title="招待を再送"
                                disabled={resending === inv.id}
                                onClick={() => handleResendInvitation(inv.id)}
                              >
                                {resending === inv.id ? (
                                  <Loader2 className="h-4 w-4 animate-spin" />
                                ) : (
                                  <RefreshCw className="h-4 w-4" />
                                )}
                              </Button>
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-8 w-8 text-destructive hover:text-destructive"
                                title="招待を取り消し"
                                disabled={revoking === inv.id}
                                onClick={() => handleRevokeInvitation(inv.id)}
                              >
                                {revoking === inv.id ? (
                                  <Loader2 className="h-4 w-4 animate-spin" />
                                ) : (
                                  <X className="h-4 w-4" />
                                )}
                              </Button>
                            </div>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
                </div>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
