'use client';

import { useEffect,useState } from 'react';
import { 
  AlertCircle,
  BarChart3, 
  CreditCard, 
  Crown,
  Mail,
  Plus, 
  Settings, 
  Shield,
  Trash2, 
  TrendingUp,
  User,
  Users} from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { calculatePlanUsage, PRICING_PLANS } from '@/config/pricing-plans';
import { createSeatChangeCheckoutAction } from '@/features/pricing/actions/create-team-checkout-action';
import { useOrganizationContext, useOrganizationRole, useSubscriptionStatus } from '@/hooks/use-organization-context';
import { useToast } from '@/hooks/use-toast';

export function SeatManagementDashboard() {
  const {
    currentOrganization,
    organizationData,
    subscriptionData,
    isLoading,
    refreshOrganizationData,
  } = useOrganizationContext();
  
  const { isOwner, isAdmin } = useOrganizationRole();
  const { articleLimit, articlesUsed, articlesRemaining } = useSubscriptionStatus();
  const { toast } = useToast();

  const [members, setMembers] = useState<any[]>([]);
  const [invitations, setInvitations] = useState<any[]>([]);
  const [isInviteDialogOpen, setIsInviteDialogOpen] = useState(false);
  const [isSeatChangeDialogOpen, setIsSeatChangeDialogOpen] = useState(false);
  const [inviteEmail, setInviteEmail] = useState('');
  const [newSeatCount, setNewSeatCount] = useState(organizationData?.max_seats || 2);
  const [isProcessing, setIsProcessing] = useState(false);

  // 使用量計算
  const usage = calculatePlanUsage(
    'team',
    null,
    organizationData?.max_seats || 2,
    articlesUsed
  );

  // メンバー・招待データの取得
  useEffect(() => {
    if (currentOrganization?.id) {
      fetchMembersAndInvitations();
    }
  }, [currentOrganization?.id]);

  const fetchMembersAndInvitations = async () => {
    // TODO: APIエンドポイントを実装してメンバー・招待情報を取得
    // 今はモックデータ
    setMembers([
      {
        id: 'mem_1',
        user_id: 'user_1',
        role: 'owner',
        status: 'active',
        email: 'owner@example.com',
        full_name: 'オーナー太郎',
        joined_at: '2024-01-01',
      },
      {
        id: 'mem_2',
        user_id: 'user_2',
        role: 'member',
        status: 'active',
        email: 'member@example.com',
        full_name: 'メンバー花子',
        joined_at: '2024-01-15',
      },
    ]);

    setInvitations([
      {
        id: 'inv_1',
        email: 'pending@example.com',
        role: 'member',
        status: 'pending',
        expires_at: '2024-02-01',
      },
    ]);
  };

  const handleInviteMember = async () => {
    if (!inviteEmail.trim()) {
      toast({
        title: 'エラー',
        description: 'メールアドレスを入力してください',
        variant: 'destructive',
      });
      return;
    }

    setIsProcessing(true);
    try {
      // TODO: 招待API呼び出し
      toast({
        title: '成功',
        description: `${inviteEmail} に招待を送信しました`,
      });
      setInviteEmail('');
      setIsInviteDialogOpen(false);
      await fetchMembersAndInvitations();
    } catch (error) {
      toast({
        title: 'エラー',
        description: '招待の送信に失敗しました',
        variant: 'destructive',
      });
    } finally {
      setIsProcessing(false);
    }
  };

  const handleSeatCountChange = async () => {
    if (newSeatCount < (organizationData?.used_seats || 1)) {
      toast({
        title: 'エラー',
        description: `使用中のシート数(${organizationData?.used_seats})より少なく設定できません`,
        variant: 'destructive',
      });
      return;
    }

    setIsProcessing(true);
    try {
      await createSeatChangeCheckoutAction({
        organizationId: currentOrganization?.id || '',
        currentSeatQuantity: organizationData?.max_seats || 2,
        newSeatQuantity: newSeatCount,
        teamPriceId: PRICING_PLANS.team.priceId,
      });
      
      toast({
        title: '成功',
        description: 'シート数を変更しました',
      });
      setIsSeatChangeDialogOpen(false);
      await refreshOrganizationData();
    } catch (error) {
      toast({
        title: 'エラー',
        description: 'シート数の変更に失敗しました',
        variant: 'destructive',
      });
    } finally {
      setIsProcessing(false);
    }
  };

  const getRoleIcon = (role: string) => {
    switch (role) {
      case 'owner':
        return <Crown className="w-4 h-4 text-yellow-600" />;
      case 'admin':
        return <Shield className="w-4 h-4 text-blue-600" />;
      default:
        return <User className="w-4 h-4 text-gray-600" />;
    }
  };

  const getRoleLabel = (role: string) => {
    switch (role) {
      case 'owner':
        return 'オーナー';
      case 'admin':
        return '管理者';
      default:
        return 'メンバー';
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-center">
          <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p>読み込み中...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* ヘッダー */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">シート管理</h1>
        {isOwner && (
          <Button 
            onClick={() => setIsSeatChangeDialogOpen(true)}
            className="bg-blue-600 hover:bg-blue-700"
          >
            <Settings className="w-4 h-4 mr-2" />
            シート数変更
          </Button>
        )}
      </div>

      {/* 概要カード */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* シート使用状況 */}
        <Card className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-gray-900">シート使用状況</h3>
            <Users className="w-5 h-5 text-blue-600" />
          </div>
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span>使用中</span>
              <span>{organizationData?.used_seats || 0} / {organizationData?.max_seats || 0}</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-blue-600 h-2 rounded-full"
                style={{
                  width: `${Math.min(100, ((organizationData?.used_seats || 0) / (organizationData?.max_seats || 1)) * 100)}%`
                }}
              />
            </div>
            <p className="text-xs text-gray-600">
              残り {(organizationData?.max_seats || 0) - (organizationData?.used_seats || 0)} シート利用可能
            </p>
          </div>
        </Card>

        {/* 記事生成使用量 */}
        <Card className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-gray-900">記事生成使用量</h3>
            <BarChart3 className="w-5 h-5 text-green-600" />
          </div>
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span>今月の使用量</span>
              <span>{usage.articlesUsed} / {usage.articleLimit}</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className={`h-2 rounded-full ${usage.isOverLimit ? 'bg-red-600' : 'bg-green-600'}`}
                style={{ width: `${Math.min(100, usage.usagePercentage)}%` }}
              />
            </div>
            <p className="text-xs text-gray-600">
              残り {usage.articlesRemaining} 記事生成可能
            </p>
          </div>
        </Card>

        {/* 料金情報 */}
        <Card className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-gray-900">今月の料金</h3>
            <CreditCard className="w-5 h-5 text-purple-600" />
          </div>
          <div className="space-y-2">
            <div className="text-2xl font-bold text-gray-900">
              ¥{((organizationData?.max_seats || 0) * PRICING_PLANS.team.pricePerSeat).toLocaleString()}
            </div>
            <p className="text-sm text-gray-600">
              ¥{PRICING_PLANS.team.pricePerSeat.toLocaleString()} × {organizationData?.max_seats || 0} シート
            </p>
            <div className="flex items-center text-xs text-gray-500">
              <TrendingUp className="w-3 h-3 mr-1" />
              次回課金: {subscriptionData?.current_period_end ? new Date(subscriptionData.current_period_end).toLocaleDateString('ja-JP') : '未設定'}
            </div>
          </div>
        </Card>
      </div>

      {/* メンバー一覧 */}
      <Card className="p-6">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-semibold text-gray-900">メンバー一覧</h3>
          {isAdmin && (
            <Button 
              onClick={() => setIsInviteDialogOpen(true)}
              variant="outline"
              disabled={organizationData?.used_seats >= organizationData?.max_seats}
            >
              <Plus className="w-4 h-4 mr-2" />
              メンバー招待
            </Button>
          )}
        </div>

        {/* シート上限警告 */}
        {organizationData?.used_seats >= organizationData?.max_seats && (
          <div className="mb-4 p-3 bg-orange-50 border border-orange-200 rounded-lg">
            <div className="flex items-center">
              <AlertCircle className="w-4 h-4 text-orange-600 mr-2" />
              <span className="text-sm text-orange-800">
                シート上限に達しています。新しいメンバーを招待するには、シート数を増やしてください。
              </span>
            </div>
          </div>
        )}

        <div className="space-y-4">
          {members.map((member) => (
            <div key={member.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
              <div className="flex items-center space-x-3">
                {getRoleIcon(member.role)}
                <div>
                  <p className="font-medium text-gray-900">{member.full_name || member.email}</p>
                  <p className="text-sm text-gray-600">{member.email}</p>
                </div>
              </div>
              <div className="flex items-center space-x-3">
                <span className="text-sm text-gray-600">{getRoleLabel(member.role)}</span>
                {isOwner && member.role !== 'owner' && (
                  <Button variant="outline" size="sm">
                    <Trash2 className="w-4 h-4" />
                  </Button>
                )}
              </div>
            </div>
          ))}

          {/* 招待中のメンバー */}
          {invitations.map((invitation) => (
            <div key={invitation.id} className="flex items-center justify-between p-3 bg-yellow-50 rounded-lg border border-yellow-200">
              <div className="flex items-center space-x-3">
                <Mail className="w-4 h-4 text-yellow-600" />
                <div>
                  <p className="font-medium text-gray-900">{invitation.email}</p>
                  <p className="text-sm text-gray-600">招待中 • 期限: {new Date(invitation.expires_at).toLocaleDateString('ja-JP')}</p>
                </div>
              </div>
              <div className="flex items-center space-x-3">
                <span className="text-sm text-yellow-700">招待中</span>
                {isAdmin && (
                  <Button variant="outline" size="sm">
                    <Trash2 className="w-4 h-4" />
                  </Button>
                )}
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* メンバー招待ダイアログ */}
      <Dialog open={isInviteDialogOpen} onOpenChange={setIsInviteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>メンバーを招待</DialogTitle>
            <DialogDescription>
              新しいメンバーをチームに招待します。招待されたメンバーは1シートを使用します。
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div>
              <Label htmlFor="email">メールアドレス</Label>
              <Input
                id="email"
                type="email"
                placeholder="example@company.com"
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
                disabled={isProcessing}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsInviteDialogOpen(false)}>
              キャンセル
            </Button>
            <Button onClick={handleInviteMember} disabled={isProcessing}>
              {isProcessing ? '送信中...' : '招待を送信'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* シート数変更ダイアログ */}
      <Dialog open={isSeatChangeDialogOpen} onOpenChange={setIsSeatChangeDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>シート数の変更</DialogTitle>
            <DialogDescription>
              チームのシート数を変更します。変更は即座に反映され、料金も調整されます。
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div>
              <Label htmlFor="seatCount">新しいシート数</Label>
              <Input
                id="seatCount"
                type="number"
                min={organizationData?.used_seats || 1}
                max={1000}
                value={newSeatCount}
                onChange={(e) => setNewSeatCount(parseInt(e.target.value) || 0)}
                disabled={isProcessing}
              />
              <p className="text-sm text-gray-600 mt-1">
                現在の使用中シート: {organizationData?.used_seats || 0}
              </p>
            </div>
            <div className="p-3 bg-blue-50 rounded-lg">
              <p className="text-sm text-blue-800">
                新しい月額料金: ¥{(newSeatCount * PRICING_PLANS.team.pricePerSeat).toLocaleString()}
                <br />
                (¥{PRICING_PLANS.team.pricePerSeat.toLocaleString()} × {newSeatCount} シート)
              </p>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsSeatChangeDialogOpen(false)}>
              キャンセル
            </Button>
            <Button onClick={handleSeatCountChange} disabled={isProcessing}>
              {isProcessing ? '変更中...' : 'シート数を変更'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}