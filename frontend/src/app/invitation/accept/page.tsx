'use client';

import { useCallback, useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Building2, CheckCircle2, Loader2, LogIn, UserPlus } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { useAuth, useOrganizationList } from '@clerk/nextjs';

type InvitationItem = {
  id: string;
  publicOrganizationData: {
    id: string;
    name: string;
    slug: string | null;
  };
  role: string;
  status: string;
  createdAt: Date;
  accept: () => Promise<unknown>;
};

export default function InvitationAcceptPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { isLoaded: isAuthLoaded, isSignedIn } = useAuth();
  const { userInvitations, isLoaded: isOrgListLoaded } = useOrganizationList({
    userInvitations: { status: ['pending'] },
  });

  const [accepting, setAccepting] = useState<string | null>(null);
  const [accepted, setAccepted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Clerk が渡す __clerk_ticket パラメータ
  const ticket = searchParams.get('__clerk_ticket');

  const handleAccept = useCallback(async (invitation: InvitationItem) => {
    setAccepting(invitation.id);
    setError(null);
    try {
      await invitation.accept();
      setAccepted(true);
      setTimeout(() => {
        router.push('/blog/new');
      }, 2000);
    } catch (e) {
      console.error('Failed to accept invitation:', e);
      setError('招待の受諾に失敗しました。もう一度お試しください。');
    } finally {
      setAccepting(null);
    }
  }, [router]);

  // 自動受諾: 招待が1件のみの場合は自動的に受諾
  useEffect(() => {
    if (!isOrgListLoaded || !isSignedIn || accepted) return;
    const invitations = (userInvitations?.data || []) as InvitationItem[];
    if (invitations.length === 1 && ticket) {
      handleAccept(invitations[0]);
    }
  }, [isOrgListLoaded, isSignedIn, userInvitations?.data, ticket, accepted, handleAccept]);

  // ローディング中
  if (!isAuthLoaded) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-slate-900 to-slate-800">
        <Loader2 className="h-8 w-8 animate-spin text-white" />
      </div>
    );
  }

  // 未ログイン: サインイン/サインアップへ誘導
  if (!isSignedIn) {
    const ticketParam = ticket ? `?__clerk_ticket=${ticket}` : '';
    const redirectParam = ticket
      ? `?redirect_url=${encodeURIComponent(`/invitation/accept?__clerk_ticket=${ticket}`)}`
      : `?redirect_url=${encodeURIComponent('/invitation/accept')}`;

    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-gradient-to-br from-slate-900 to-slate-800 p-4">
        <Card className="w-full max-w-md">
          <CardHeader className="text-center">
            <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
              <Building2 className="h-8 w-8 text-primary" />
            </div>
            <CardTitle className="text-2xl">組織への招待</CardTitle>
            <CardDescription>
              招待を受けるには、ログインまたはアカウント作成が必要です。
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <Button
              className="w-full gap-2"
              onClick={() => router.push(`/sign-in${redirectParam}`)}
            >
              <LogIn className="h-4 w-4" />
              ログインして招待を受ける
            </Button>
            <Button
              variant="outline"
              className="w-full gap-2"
              onClick={() => router.push(`/sign-up${ticketParam}`)}
            >
              <UserPlus className="h-4 w-4" />
              アカウントを作成して招待を受ける
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  // ログイン済み: 招待の読み込み中
  if (!isOrgListLoaded) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-slate-900 to-slate-800">
        <Card className="w-full max-w-md">
          <CardContent className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
            <span className="ml-3 text-muted-foreground">招待情報を読み込み中...</span>
          </CardContent>
        </Card>
      </div>
    );
  }

  // 受諾完了
  if (accepted) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-gradient-to-br from-slate-900 to-slate-800 p-4">
        <Card className="w-full max-w-md">
          <CardContent className="flex flex-col items-center py-12">
            <CheckCircle2 className="h-16 w-16 text-green-500 mb-4" />
            <h2 className="text-xl font-bold mb-2">招待を受諾しました</h2>
            <p className="text-muted-foreground text-center">
              組織に参加しました。アプリにリダイレクトしています...
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const invitations = (userInvitations?.data || []) as InvitationItem[];

  // 招待がない場合
  if (invitations.length === 0) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-gradient-to-br from-slate-900 to-slate-800 p-4">
        <Card className="w-full max-w-md">
          <CardHeader className="text-center">
            <CardTitle>招待がありません</CardTitle>
            <CardDescription>
              現在、保留中の招待はありません。既に受諾済みか、招待が期限切れの可能性があります。
            </CardDescription>
          </CardHeader>
          <CardContent className="flex justify-center">
            <Button onClick={() => router.push('/blog/new')}>
              アプリに戻る
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  // 招待一覧を表示
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gradient-to-br from-slate-900 to-slate-800 p-4">
      <div className="w-full max-w-md space-y-4">
        <div className="text-center mb-6">
          <h1 className="text-2xl font-bold text-white">組織への招待</h1>
          <p className="text-slate-400 mt-2">
            以下の組織からの招待が届いています
          </p>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {invitations.map((invitation) => {
          const roleLabel = invitation.role === 'org:admin' ? '管理者' : 'メンバー';

          return (
            <Card key={invitation.id}>
              <CardHeader>
                <div className="flex items-center gap-3">
                  <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
                    <Building2 className="h-6 w-6 text-primary" />
                  </div>
                  <div>
                    <CardTitle className="text-lg">
                      {invitation.publicOrganizationData.name}
                    </CardTitle>
                    <CardDescription>
                      {roleLabel}として招待されています
                    </CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <Button
                  className="w-full"
                  onClick={() => handleAccept(invitation)}
                  disabled={accepting === invitation.id}
                >
                  {accepting === invitation.id ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin mr-2" />
                      受諾中...
                    </>
                  ) : (
                    '招待を受ける'
                  )}
                </Button>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
